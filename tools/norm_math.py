#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""长文片段的公式格式归一：把 <span class="math">…</span> 转成 $…$，并修掉偶发的多余 $。

背景（2026-11-19）：模型偶尔用 <span class="math"> 包行内公式（站点没有 .math 样式，
会原样显示 LaTeX），或在 span 里多写一个 $ 让整段公式定界符变奇数，
finalize 的 formula_check 会因此拒绝装配。

用法：python3 -I tools/norm_math.py [--domain moe] [--dry]
"""
import argparse, glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPAN = re.compile(r'<span class="math">([\s\S]*?)</span>')


def fix_span(m):
    x = m.group(1).strip().strip("$").strip()
    return "$" + x + "$" if x else ""


def process(path, dry=False):
    s = open(path, encoding="utf-8").read()
    orig = s
    s = SPAN.sub(fix_span, s)
    # 行内出现奇数个 $ 时，优先删掉紧贴 </span> 或句末的多余 $
    lines = s.split("\n")
    changed = 0
    for i, l in enumerate(lines):
        if l.count("$") % 2 == 0:
            continue
        for pat in (r"\$</span>", r"\$\s*</p>", r"\$\s*$"):
            m = re.search(pat, l)
            if m:
                l = l[:m.start()] + l[m.start() + 1:]
                changed += 1
                break
        lines[i] = l
    s = "\n".join(lines)
    if s != orig and not dry:
        open(path, "w", encoding="utf-8").write(s)
    return s != orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    pat = os.path.join(ROOT, "content", "long", args.domain or "*", "**", "*.html")
    files = sorted(glob.glob(pat, recursive=True))
    n = 0
    for f in files:
        if process(f, args.dry):
            n += 1
            print("fixed", os.path.relpath(f, ROOT))
    print("files", len(files), "changed", n)


if __name__ == "__main__":
    main()
