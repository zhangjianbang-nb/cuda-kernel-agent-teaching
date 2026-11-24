#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pick 40 deep-read papers per domain (9 parts each) + rest shallow (2 parts).

Deep = 400 parts per domain, matching the previous project's paper budget.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(ROOT, "content", "cards")
OUT = os.path.join(ROOT, "content", "selected.json")


def main():
    sel = {}
    for dom in sorted(os.listdir(CARDS)):
        d = os.path.join(CARDS, dom)
        if not os.path.isdir(d):
            continue
        items = []
        for f in os.listdir(d):
            if not f.endswith(".json"):
                continue
            try:
                c = json.load(open(os.path.join(d, f), encoding="utf-8"))
            except Exception:
                continue
            pid = c.get("_paper_id")
            y = 0
            m = re.search(r"-(\d{4})$", pid or "")
            if m:
                y = int(m.group(1))
            items.append((y, pid))
        items.sort()
        deep = [p for _, p in items[:40] if p]
        sel[dom] = {"deep": deep, "papers": [p for _, p in items if p]}
        print(dom, "cards", len(items), "deep", len(deep))
    json.dump(sel, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
