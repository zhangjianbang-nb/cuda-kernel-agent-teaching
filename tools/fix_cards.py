#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理不合格论文卡：含占位符标记（待填/占位符/TODO/未完成/XXX）的卡删除，交给 make_cards 重生成。

用法：python3 -I tools/fix_cards.py [--dry]
"""
import argparse, glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKS = ("待补充", "TODO", "lorem ipsum", "示例论文", "XXX")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    bad = []
    for f in glob.glob(os.path.join(ROOT, "content", "cards", "*", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            bad.append(f); continue
        s = json.dumps(d, ensure_ascii=False)
        if any(m in s for m in MARKS): bad.append(f)
    print("bad", len(bad), flush=True)
    for f in bad:
        print(" ", os.path.relpath(f, ROOT), flush=True)
        if not args.dry: os.remove(f)
    print("removed" if not args.dry else "dry-run", len(bad), flush=True)

if __name__ == "__main__":
    main()
