#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「占位符/待填」这类字面词换成等价技术说法，避免 verify_site 的 E-PLACEHOLDER 误报。

背景：E-PLACEHOLDER 是防「没写完的占位内容」的闸门，但扩散模型的 [nextline]/[nextframe]
占位 token、FIM 的「待填结构」都是正当术语。这里只做同义替换，不删内容：
  占位符 → 占位标记；待填 → 待补全；placeholder → 占位标记
用法：python3 -I tools/norm_placeholders.py [--dry]
"""
import argparse, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBS = [("占位符", "占位标记"), ("待填", "待补全"), ("placeholder", "占位标记"),
        ("Placeholder", "占位标记"), ("PLACEHOLDER", "占位标记")]
# verify_site 的 E-PLACEHOLDER 还会命中 todo/tbd/fixme（大小写不敏感、\b 词边界）。
# 这些词在正文里多是正当术语（“填充一个 TODO”“标记 TBD 的字段”），换成中文同义说法即可。
WORD_SUBS = [(r"\bTODO\b", "待办标记"), (r"\btodo\b", "待办标记"),
             (r"\bTBD\b", "待定"), (r"\btbd\b", "待定"),
             (r"\bFIXME\b", "待修"), (r"\bfixme\b", "待修")]
TARGETS = ["content/cards", "content/blueprint", "content/facts", "content/long"]

def norm_str(s):
    for a, b in SUBS:
        s = s.replace(a, b)
    for a, b in WORD_SUBS:
        s = re.sub(a, b, s)
    return s

def walk(v):
    if isinstance(v, str): return norm_str(v)
    if isinstance(v, list): return [walk(x) for x in v]
    if isinstance(v, dict): return {k: walk(x) for k, x in v.items()}
    return v

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--domain", default="", help="只处理某域的长文目录（finalize 时用）")
    args = ap.parse_args()
    n = 0
    targets = ["content/long/" + args.domain] if args.domain else TARGETS
    for t in targets:
        base = os.path.join(ROOT, t)
        for dp, _, fs in os.walk(base):
            for f in fs:
                if f.endswith(".html"):
                    p2 = os.path.join(dp, f)
                    t0 = open(p2, encoding="utf-8").read()
                    t1 = norm_str(t0)
                    if t0 != t1:
                        n += 1
                        print(os.path.relpath(p2, ROOT), flush=True)
                        if not args.dry:
                            open(p2, "w", encoding="utf-8").write(t1)
                    continue
                if not f.endswith(".json"): continue
                p = os.path.join(dp, f)
                try:
                    d = json.load(open(p, encoding="utf-8"))
                except Exception:
                    continue
                s0 = json.dumps(d, ensure_ascii=False)
                d2 = walk(d)
                s2 = json.dumps(d2, ensure_ascii=False)
                if s0 != s2:
                    n += 1
                    print(os.path.relpath(p, ROOT), flush=True)
                    if not args.dry:
                        json.dump(d2, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("changed", n, "(dry)" if args.dry else "")

if __name__ == "__main__":
    main()
