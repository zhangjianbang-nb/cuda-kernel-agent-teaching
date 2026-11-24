#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蓝图去重：同一模块里 id 重复的条目只保留第一条（首条为完整字段版本）。

背景（2026-11-19）：make_blueprint 的 --start>0 合并逻辑在补跑时把已有条目又追加了一遍，
导致 algorithms/theory 出现重复 id，L2 结构闸门报 E-ID 且重复条目缺速查表/流程图。

用法：python3 -I tools/dedupe_blueprint.py [--dry]
"""
import argparse, glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    total = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "content", "blueprint", "*", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        changed = False
        for key, lst in d.items():
            if not isinstance(lst, list):
                continue
            seen, keep, drop = set(), [], []
            for x in lst:
                i = x.get("id") if isinstance(x, dict) else None
                if i and i in seen:
                    drop.append(i)
                    continue
                if i:
                    seen.add(i)
                keep.append(x)
            if drop:
                d[key] = keep
                changed = True
                print(os.path.relpath(f, ROOT), key, "drop", drop, len(lst), "->", len(keep))
                total += len(drop)
        if changed and not args.dry:
            json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("dropped", total)


if __name__ == "__main__":
    main()
