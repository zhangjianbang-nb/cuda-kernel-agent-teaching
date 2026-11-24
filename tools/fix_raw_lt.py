#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escape raw '<' left in prose/math (e.g. `i < n`, `t < t0`).

Why: a raw `<` followed by a letter makes the browser treat the rest as a tag
until the next `>`, swallowing body text; the tag-stack checker also reports
bogus tags like `<t0`. Whitelisted real tags are preserved verbatim.
"""
import argparse
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ["figcaption", "strong", "table", "thead", "tbody", "span", "code", "figure",
         "div", "sup", "sub", "h3", "h4", "tr", "td", "th", "ul", "ol", "li", "em",
         "p", "b", "i", "a", "br", "hr"]
TAG = re.compile(r"</?(?:" + "|".join(NAMES) + r")(?:\s[^>]*?)?/?>", re.I)


def fix(s):
    out, last, n = [], 0, 0
    for m in TAG.finditer(s):
        gap = s[last:m.start()]
        if "<" in gap:
            n += gap.count("<")
            gap = gap.replace("<", "&lt;")
        out.append(gap)
        out.append(m.group(0))
        last = m.end()
    tail = s[last:]
    if "<" in tail:
        n += tail.count("<")
        tail = tail.replace("<", "&lt;")
    out.append(tail)
    return "".join(out), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="cuda")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, "content", "long", args.domain, "*", "*.html")))
    changed = total = 0
    for f in files:
        s = open(f, encoding="utf-8").read()
        t, n = fix(s)
        if n:
            changed += 1
            total += n
            if not args.dry:
                open(f, "w", encoding="utf-8").write(t)
    print(f"raw-lt: files={len(files)} changed={changed} escaped={total} dry={args.dry}")


if __name__ == "__main__":
    main()
