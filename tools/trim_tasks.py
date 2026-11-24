#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trim the 1059-task plan to a right-sized plan that still covers every item.

Target: >=3,000,000 visible chars (user's "300万字" maps to visible chars in the
two prior projects: 30M/7 = 4.285M per domain). At ~6,000 visible chars per
4200-CJK fragment, 517 fragments give ~3.1-3.4M visible with margin.

Ordering is part-first across modules so a partial run still leaves every item
with at least one section (thin-content gate never sees an empty item).
"""
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "tasks", "cuda.json")
OUT = os.path.join(ROOT, "content", "tasks", "cuda-trim.json")

MODULE_ORDER = ["papers", "algorithms", "theory", "directions", "stories",
                "exams", "book", "appendix"]


def keep_parts(t, item_index):
    mod = t["module"]
    parts = t["parts"]
    if mod == "papers":
        return 3 if parts >= 5 else 2          # deep 3 / shallow 2
    if mod == "algorithms":
        return 4
    if mod == "theory":
        return 3
    if mod == "directions":
        return 3
    if mod == "stories":
        return 6                               # keep all six acts
    if mod == "exams":
        return 1                               # reference answer only
    if mod == "book":
        return 7 if item_index < 4 else 6      # first four volumes one extra
    if mod == "appendix":
        return 3 if item_index < 6 else 2
    return parts


def main():
    tasks = json.load(open(SRC, encoding="utf-8"))
    by_item = defaultdict(list)
    for t in tasks:
        by_item[(t["module"], t["item_id"])].append(t)
    item_index = defaultdict(int)
    kept = []
    for t in tasks:
        key = (t["module"], t["item_id"])
        k = keep_parts(t, item_index[key])
        if t["part"] <= k:
            kept.append(t)
        if t["part"] == t["parts"]:
            item_index[key] += 1
    # part-first ordering: all part 1 across modules, then part 2, ...
    kept.sort(key=lambda t: (t["part"], MODULE_ORDER.index(t["module"]),
                             t["item_id"]))
    json.dump(kept, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("trim tasks", len(kept), dict(Counter(t["module"] for t in kept)))
    print("items", len(by_item), "kept items",
          len({(t["module"], t["item_id"]) for t in kept}))
    print("part-1 tasks", sum(1 for t in kept if t["part"] == 1))


if __name__ == "__main__":
    main()
