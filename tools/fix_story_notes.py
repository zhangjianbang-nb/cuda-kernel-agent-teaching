#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix malformed 工匠笔记 blocks and duplicated </p> closers in long fragments.

Model occasionally emits `<h3>工匠笔记` without closing it, swallowing the
following bullet lines into the heading (renders as one giant bold block).
Also occasionally emits `</p> </p><div ...>` (two closers for one paragraph).
"""
import argparse
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fix_notes(s):
    m = re.search(r"<h3>工匠笔记(?!</h3>)([\s\S]*?)(?=<h3|$)", s)
    if not m:
        return s, 0
    body = m.group(1)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if not lines:
        return s.replace(m.group(0), "<h3>工匠笔记</h3>", 1), 1
    paras = "\n".join("<p>" + ln + "</p>" for ln in lines)
    return s[:m.start()] + "<h3>工匠笔记</h3>\n" + paras + "\n" + s[m.end():], 1


def fix_dup_p(s):
    n = len(re.findall(r"</p>\s*</p>", s))
    return re.sub(r"</p>\s*</p>", "</p>", s), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="cuda")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, "content", "long", args.domain, "*", "*.html")))
    notes = dups = 0
    for f in files:
        s = open(f, encoding="utf-8").read()
        t, a = fix_notes(s)
        t, b = fix_dup_p(t)
        if t != s:
            open(f, "w", encoding="utf-8").write(t)
        notes += a
        dups += b
    print(f"fix: files={len(files)} notes={notes} dup_p={dups}")


if __name__ == "__main__":
    main()
