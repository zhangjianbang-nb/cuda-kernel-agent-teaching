#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escape raw < and > inside <code> blocks so the HTML tag stack stays balanced.

The long-form model sometimes writes `mask = offs < N` inside <code>; the browser
treats `< N</code>` as a tag start and the block swallows following paragraphs.
Unescape-then-escape normalizes entities without double-escaping.
"""
import argparse
import glob
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = re.compile(r"(<code[^>]*>)([\s\S]*?)(</code>)", re.I)


def fix(s):
    def rep(m):
        inner = html.unescape(m.group(2))
        return m.group(1) + html.escape(inner, quote=False) + m.group(3)
    return CODE.sub(rep, s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="cuda")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, "content", "long", args.domain, "*", "*.html")))
    changed = 0
    for f in files:
        s = open(f, encoding="utf-8").read()
        t = fix(s)
        if t != s:
            changed += 1
            if not args.dry:
                open(f, "w", encoding="utf-8").write(t)
    print(f"code-escape: files={len(files)} changed={changed} dry={args.dry}")


if __name__ == "__main__":
    main()
