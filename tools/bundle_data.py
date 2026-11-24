#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 site/data/domains/<id>/*.json 打包成按领域懒加载的 bundle.js，并生成 manifest.js。

index.html 只读 manifest.js（领域清单），进入某个领域时才动态加载
data/domains/<id>/bundle.js —— file:// 下也不触发 fetch/CORS。
"""
import argparse, datetime, json, os, re, sys

DATA_KEYS = ["domain", "directions", "algorithms", "papers", "stories",
             "theory", "assessments", "evolution", "summary", "coverage"]
OPTIONAL_KEYS = ["book", "appendix"]

def load_dir(data_dir):
    data, missing = {}, []
    for key in DATA_KEYS:
        p = os.path.join(data_dir, key + ".json")
        if not os.path.exists(p): missing.append(p); continue
        data[key] = json.load(open(p, encoding="utf-8"))
    for key in OPTIONAL_KEYS:
        p = os.path.join(data_dir, key + ".json")
        if os.path.exists(p): data[key] = json.load(open(p, encoding="utf-8"))
    if missing:
        raise SystemExit("缺少数据文件：\n  " + "\n  ".join(missing))
    return data

def build_domain(site, dom, quiet=True):
    data_dir = os.path.join(site, "data", "domains", dom)
    data = load_dir(data_dir)
    # 2026-11-22 懒加载拆分：不再写单个 16MB bundle.js，改由 bundle_split 生成
    # core.js（<1MB）+ sec-papers/theory/algorithms/exam/book/appendix.js 分片。
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import bundle_split
    bundle_split.build_domain(site, dom, quiet=quiet)
    if not quiet:
        print(f"  core {dom}: papers={len(data['papers'])}, "
              f"long_chars≈{sum(len(p.get('long_html') or '') for p in data['papers'])/10000:.0f}万")
    return os.path.join(data_dir, "core.js")

DOMAIN_ORDER = ["cuda"]

_TAG_BLOCK = re.compile(r"<(script|style)[\s\S]*?</\1>", re.I)
_TAG_ANY = re.compile(r"<[^>]+>")

def _vis(s):
    if not isinstance(s, str): return 0
    h = _TAG_BLOCK.sub(" ", s); h = _TAG_ANY.sub("", h)
    return len(re.sub(r"\s+", " ", h).strip())

def _walk(node, acc):
    if isinstance(node, str):
        acc[0] += _vis(node); acc[1] += len(re.findall(r"[\u4e00-\u9fff]", node))
    elif isinstance(node, list):
        for x in node: _walk(x, acc)
    elif isinstance(node, dict):
        for v in node.values(): _walk(v, acc)

def write_totals(site, domains=None):
    """全站正文规模写进 data/totals.js，落地页据此显示"多少万字符"。

    口径与 verify_site.vis_len 一致（去标签不插空格、空白折叠）；跨全部领域目录统计，
    单领域重建也不会把总数写小。domains 给定时只统计这些领域（验收版只放已完工领域）。
    """
    root = os.path.join(site, "data", "domains")
    doms = domains or [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    doms = [d for d in doms if os.path.isdir(os.path.join(root, d))]
    acc = [0, 0]
    for dom in doms:
        for name in os.listdir(os.path.join(root, dom)):
            if not name.endswith(".json"): continue
            try: data = json.load(open(os.path.join(root, dom, name), encoding="utf-8"))
            except Exception: continue
            _walk(data, acc)
    out = os.path.join(site, "data", "totals.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write("window.SITE_TOTAL = " + json.dumps(
            {"visible": acc[0], "cjk": acc[1], "domains": len(doms),
             "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")},
            ensure_ascii=False) + ";\n")
    return out

def build_manifest(site, domains, quiet=True):
    # 领域栏按用户给定的顺序排（MoE → 多模态 → Coding → RL → 视频 → 图像 → 音频），
    # 不要用目录名的字典序，否则落地页会把「音频」排在第一位。
    ordered = [d for d in DOMAIN_ORDER if d in domains] + [d for d in domains if d not in DOMAIN_ORDER]
    rows = []
    for dom in ordered:
        p = os.path.join(site, "data", "domains", dom, "domain.json")
        if not os.path.exists(p): continue
        d = json.load(open(p, encoding="utf-8"))
        st = d.get("stats") or {}
        rows.append({"id": dom, "name": d.get("name", dom), "name_en": d.get("name_en", ""),
                     "short": d.get("short", dom), "tagline": d.get("tagline", ""), "stats": st})
    out = os.path.join(site, "data", "manifest.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write("window.SITE_DOMAINS = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n")
    if not quiet:
        print(f"manifest: {len(rows)} domains -> {out}")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="site")
    ap.add_argument("--domain", default="")
    ap.add_argument("--only", default="",
                    help="逗号分隔的领域列表：只重建这些领域并只把它们写进 manifest/totals")
    args = ap.parse_args()
    site = os.path.abspath(args.site)
    domains = ([x.strip() for x in args.only.split(",") if x.strip()] if args.only
               else ([args.domain] if args.domain else sorted(os.listdir(os.path.join(site, "data", "domains")))))
    for dom in domains:
        build_domain(site, dom, quiet=False)
    build_manifest(site, domains, quiet=False)
    print("totals:", write_totals(site, domains))

if __name__ == "__main__":
    main()
