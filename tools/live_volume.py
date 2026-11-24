#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按已落盘的 content/long 分片实时估算体积（与 verify_site.vis_len 同口径）。

生成期间 bundle 还没重建，count_volume.py 读到的是旧数据；本脚本直接数分片文件，
给出"若现在装配"的可见字符/汉字与 3000 万进度。
用法：python3 -I tools/live_volume.py [--json]
"""
import argparse, glob, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMS = ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
TAG_BLOCK = re.compile(r"<(script|style)[\s\S]*?</\1>", re.I)
TAG_ANY = re.compile(r"<[^>]+>")

def vis_len(html):
    h = TAG_BLOCK.sub(" ", html)
    h = TAG_ANY.sub("", h)
    return len(re.sub(r"\s+", " ", h).strip())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(); rows = []; tv = tc = tn = 0
    for d in DOMS:
        fs = glob.glob(os.path.join(ROOT, "content", "long", d, "*", "*.html"))
        v = c = 0
        for f in fs:
            s = open(f, encoding="utf-8").read()
            v += vis_len(s); c += len(re.findall(r"[\u4e00-\u9fff]", s))
        rows.append((d, len(fs), v, c)); tv += v; tc += c; tn += len(fs)
    if a.json:
        print(json.dumps({"domains": rows, "files": tn, "visible": tv, "cjk": tc}, ensure_ascii=False)); return
    for d, n, v, c in rows:
        print("%-12s 片段 %4d  可见 %10d  汉字 %9d" % (d, n, v, c))
    print("-" * 50)
    print("合计        片段 %4d  可见 %10d  汉字 %9d" % (tn, tv, tc))
    print("3000 万目标 完成 %6.2f%%（可见口径）  还差 %d" % (tv / 30_000_000 * 100, max(0, 30_000_000 - tv)))

if __name__ == "__main__":
    main()
