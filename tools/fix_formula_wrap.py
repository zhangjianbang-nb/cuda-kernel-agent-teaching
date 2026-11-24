#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公式容器内定界符补尾：`<span class="formula">$$…</span>` 缺尾 `$$` 时补上。

为什么单看总数不够（2026-11-16 事故）：模型漏写一个 `$$`，文件里 `$$` 总数仍是偶数
（漏掉的那个与下一段公式的开头配了对），于是 `fix_formulas` 的非贪婪匹配跨过整段 HTML，
把 `<p>`/`<h3>` 转义成文本 —— coding 线上 49 处 `&lt;p&gt;` 就是这么来的。
判据改为：逐个公式容器看内部 `$$` 是否成对。

用法：python3 -I tools/fix_formula_wrap.py [--dry] [--domain coding]
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTAINERS = [(re.compile(r'<span class="formula">'), "</span>"),
              (re.compile(r'<div class="formula">'), "</div>")]

def fix(s):
    changed = 0
    for rx, closer in CONTAINERS:
        pos = 0
        while True:
            m = rx.search(s, pos)
            if not m:
                break
            end = s.find(closer, m.end())
            if end == -1:
                break
            body = s[m.end():end]
            if body.count("$$") % 2:
                s = s[:end] + "$$" + s[end:]
                changed += 1
                end += 2
            pos = end + len(closer)
    return s, changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    doms = [a.domain] if a.domain else ["moe","multimodal","coding","rl","video","image","audio"]
    tot = files = 0
    for d in doms:
        tp = os.path.join(ROOT, "content", "tasks", d + ".json")
        if not os.path.exists(tp):
            continue
        for t in json.load(open(tp, encoding="utf-8")):
            f = os.path.join(ROOT, t["out"])
            if not os.path.exists(f):
                continue
            s = open(f, encoding="utf-8").read()
            s2, n = fix(s)
            if n:
                files += 1; tot += n
                print("FIX %s/%s +%d $$" % (d, t["id"], n))
                if not a.dry:
                    open(f, "w", encoding="utf-8").write(s2)
    print("FIXED %d 处 / %d 文件" % (tot, files))

if __name__ == "__main__":
    main()
