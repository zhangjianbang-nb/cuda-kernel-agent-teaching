#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公式未闭合补尾（块级启发式）：`$$` 打开后，若在下一个 `$$` 之前先遇到块级标签，
说明公式漏了收尾 `$$`，就在该块级标签前补一个。

为什么需要（2026-11-16 事故）：模型常写 `<div class="formula">$$…</div>` 而漏掉收尾 `$$`，
此时文件里 `$$` 总数仍可能是偶数（两个漏尾的公式互相配对），`fix_formulas` 的非贪婪匹配
跨过整段 HTML，把 `<p>/<h3>/<table>` 转义成文本。coding 线上 135 处 `&lt;p&gt;` 即由此产生。

用法：python3 -I tools/fix_formula_open.py [--dry] [--domain coding]
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK = re.compile(r"</?(?:p|h3|h4|ul|ol|li|table|thead|tbody|tr|td|th|div)\b")

def fix(s):
    n = 0
    pos = 0
    while True:
        i = s.find("$$", pos)
        if i == -1:
            break
        j = s.find("$$", i + 2)
        seg = s[i + 2:j] if j != -1 else s[i + 2:]
        m = BLOCK.search(seg)
        if m:
            s = s[:i + 2 + m.start()] + "$$" + s[i + 2 + m.start():]
            n += 1
            pos = i + 2 + m.start() + 2
        else:
            pos = (j + 2) if j != -1 else len(s)
    return s, n

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
