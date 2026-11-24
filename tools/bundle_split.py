#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 site/data/domains/<id>/*.json 拆成「核心包 + 按页懒加载分片」，替代单个 16MB bundle.js。

core.js           domain / directions / stories / summary / evolution / coverage
                  + counts（各页条目数，首页统计用）+ track（已学进度用的 id 清单）
sec-papers.js     papers
sec-theory.js     theory
sec-algorithms.js algorithms
sec-exam.js       assessments
sec-book.js       book
sec-appendix.js   appendix

每个分片只写自己那一个键：
  (window.SITE_DATA_BY_DOMAIN=window.SITE_DATA_BY_DOMAIN||{})["<id>"] =
      Object.assign(existing||{}, {"<key>": ...})
file:// 下同样是 <script> 加载，不触发 fetch/CORS。
"""
import argparse, datetime, json, os, re, sys

DOMAIN_ORDER = ["cuda"]

CORE_KEYS = ["domain", "directions", "stories", "summary", "evolution", "coverage"]
CHUNKS = {
    "papers": ("sec-papers.js", ["papers"]),
    "theory": ("sec-theory.js", ["theory"]),
    "algorithms": ("sec-algorithms.js", ["algorithms"]),
    "assessments": ("sec-exam.js", ["assessments"]),
    "book": ("sec-book.js", ["book"]),
    "appendix": ("sec-appendix.js", ["appendix"]),
}

# 这些模块的 long_html 是详情页正文，拆成 body-<key>-<id>.js 单条按需加载
BODY_KEYS = {"papers", "theory", "algorithms", "appendix"}


def _load(data_dir, key):
    p = os.path.join(data_dir, key + ".json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def _counts(data):
    algs = data.get("algorithms") or []
    papers = data.get("papers") or []
    book = data.get("book") or {}
    book_sections = len(book.get("sections") or []) if isinstance(book, dict) else len(book)
    return {
        "directions": len(data.get("directions") or []),
        "stories": len(data.get("stories") or []),
        "algorithms": len(algs),
        "classic_algorithms": sum(1 for a in algs if a.get("tier") == "classic"),
        "papers": len(papers),
        "core_papers": sum(1 for p in papers if p.get("type") in ("foundational", "classic")),
        "recent_papers": sum(1 for p in papers if p.get("type") in ("recent", "latest")),
        "theory": len(data.get("theory") or []),
        "assessments": len(data.get("assessments") or []),
        "book": book_sections,
        "appendix": len(data.get("appendix") or []),
    }


def _track(data):
    return {
        "theory": [x.get("id") for x in (data.get("theory") or []) if x.get("id")],
        "papers": [x.get("id") for x in (data.get("papers") or []) if x.get("id")],
    }


def _write(path, dom, payload):
    with open(path, "w", encoding="utf-8") as f:
        f.write('(function(){var m=window.SITE_DATA_BY_DOMAIN=window.SITE_DATA_BY_DOMAIN||{};'
                'var d=m[%s]=m[%s]||{};' % (json.dumps(dom), json.dumps(dom)))
        for k, v in payload.items():
            f.write('d[%s]=%s;' % (json.dumps(k), json.dumps(v, ensure_ascii=False, separators=(",", ":"))))
        f.write('})();\n')


def _write_body(data_dir, dom, key, item):
    """详情页正文单独成文件：只把 long_html 补回对应条目（列表页不下载正文）。"""
    item_id = item.get("id")
    if not item_id:
        return 0
    body = item.get("long_html") or ""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", item_id)
    path = os.path.join(data_dir, "body-%s-%s.js" % (key, safe))
    with open(path, "w", encoding="utf-8") as f:
        f.write('(function(){var m=window.SITE_DATA_BY_DOMAIN||{};var d=m[%s]||{};'
                'var a=d[%s]||[];' % (json.dumps(dom), json.dumps(key)))
        f.write('for(var i=0;i<a.length;i++){if(a[i].id==%s){a[i][%s]=%s;break;}}'
                % (json.dumps(item_id), json.dumps("long_html"),
                   json.dumps(body, ensure_ascii=False, separators=(",", ":"))))
        f.write('})();\n')
    return os.path.getsize(path)


def build_domain(site, dom, quiet=True):
    data_dir = os.path.join(site, "data", "domains", dom)
    for name in os.listdir(data_dir):
        if name.startswith("body-") and name.endswith(".js"):
            os.remove(os.path.join(data_dir, name))
    data = {}
    for k in CORE_KEYS + list(CHUNKS) + ["papers", "theory"]:
        v = _load(data_dir, k)
        if v is not None:
            data[k] = v
    core = {k: data[k] for k in CORE_KEYS if k in data}
    core["counts"] = _counts(data)
    core["track"] = _track(data)
    _write(os.path.join(data_dir, "core.js"), dom, core)
    with open(os.path.join(data_dir, "core.js"), "a", encoding="utf-8") as f:
        f.write('window.SITE_DATA_GENERATED=%s;\n'
                % json.dumps(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    for key, (fname, keys) in CHUNKS.items():
        if key not in data:
            continue
        items = data[key]
        if key in BODY_KEYS and isinstance(items, list):
            # 正文 long_html 拆成 body-<key>-<id>.js，列表分片只留元数据
            for it in items:
                if isinstance(it, dict):
                    _write_body(data_dir, dom, key, it)
            stripped = []
            for it in items:
                if isinstance(it, dict) and "long_html" in it:
                    it = {k: v for k, v in it.items() if k != "long_html"}
                stripped.append(it)
            items = stripped
        _write(os.path.join(data_dir, fname), dom, {key: items})
    old = os.path.join(data_dir, "bundle.js")
    if os.path.exists(old):
        os.remove(old)
    if not quiet:
        print("  split %s: core %.2f MB" % (dom, os.path.getsize(os.path.join(data_dir, "core.js")) / 1048576))
        for key, (fname, _) in CHUNKS.items():
            p = os.path.join(data_dir, fname)
            if os.path.exists(p):
                print("    %-22s %.2f MB" % (fname, os.path.getsize(p) / 1048576))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))
    ap.add_argument("--domains", default="")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    doms = [d for d in a.domains.split(",") if d] or [
        d for d in DOMAIN_ORDER if os.path.isdir(os.path.join(a.site, "data", "domains", d))]
    for d in doms:
        build_domain(a.site, d, quiet=a.quiet)
    print("bundle_split done:", ",".join(doms))


if __name__ == "__main__":
    main()
