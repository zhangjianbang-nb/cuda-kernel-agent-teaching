#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""块公式定界符修补：`<div class="formula">$$…</div>` 缺尾 `$$` 时补上。

背景（2026-11-20 rl 实测）：模型偶尔漏写块公式的收尾 `$$`，build_long 会把这段 `$$`
与后面别的 `$$` 配对，跨标签吞掉 `</div>` 等，finalize 报 ESCAPED_TAGS_FAILED（rl 54 处）。
formula_check 只数单 `$`，漏掉这种"两个 `$` 但没闭合"的形态，所以单独做这道闸。

用法：python3 -I tools/fix_dollar.py [--domain rl] [--dry]
"""
import argparse, glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIV = re.compile(r'(<div class="formula">)([\s\S]*?)(</div>)')


def fix(path, dry=False):
    s = open(path, encoding="utf-8").read()
    orig = s

    def repl(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        if body.count("$$") % 2:
            return head + body.rstrip() + "$$" + tail
        return m.group(0)

    s = DIV.sub(repl, s)
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
        if fix(f, args.dry):
            n += 1
            print("fixed", os.path.relpath(f, ROOT))
    print("files", len(files), "changed", n)


if __name__ == "__main__":
    main()
