#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站正文口径统计：与 verify_site.vis_len 同口径（去标签不插空格、空白折叠）。

口径：只数正文——bundle 里所有字符串值 + book 各节 html + appendix long_html，
不数 JSON 字段名。逐领域给出可见字符与汉字数，最后给全站合计与 3000 万目标进度。

用法：python3 -I tools/count_volume.py [--json]
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DOMS = ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
TAG_BLOCK = re.compile(r"<(script|style)[\s\S]*?</\1>", re.I)
TAG_ANY = re.compile(r"<[^>]+>")

def vis_len(html):
    if not isinstance(html, str):
        return 0
    h = TAG_BLOCK.sub(" ", html)
    h = TAG_ANY.sub("", h)
    return len(re.sub(r"\s+", " ", h).strip())

def cjk_len(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))

def load_bundle(dom):
    """懒加载拆分后不再有 bundle.js：直接合并该领域目录下全部 *.json。"""
    d = os.path.join(SITE, "data", "domains", dom)
    if not os.path.isdir(d):
        return None
    out = {}
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        try:
            out[name[:-5]] = json.load(open(os.path.join(d, name), encoding="utf-8"))
        except Exception:
            pass
    return out or None

def walk(node, acc):
    if isinstance(node, str):
        acc[0] += vis_len(node)
        acc[1] += cjk_len(node)
    elif isinstance(node, list):
        for x in node: walk(x, acc)
    elif isinstance(node, dict):
        for v in node.values(): walk(v, acc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = []
    total_v = total_c = 0
    for dom in DOMS:
        data = load_bundle(dom)
        if data is None:
            rows.append((dom, 0, 0)); continue
        acc = [0, 0]
        walk(data, acc)
        rows.append((dom, acc[0], acc[1]))
        total_v += acc[0]; total_c += acc[1]
    if args.json:
        print(json.dumps({"domains": rows, "total_visible": total_v, "total_cjk": total_c}, ensure_ascii=False))
        return
    for dom, v, c in rows:
        print("%-12s 可见 %10d  汉字 %9d" % (dom, v, c))
    print("-" * 44)
    print("全站合计      可见 %10d  汉字 %9d" % (total_v, total_c))
    print("3000 万目标   完成 %6.2f%%  还差 %d" % (total_v / 30_000_000 * 100, max(0, 30_000_000 - total_v)))

if __name__ == "__main__":
    main()
