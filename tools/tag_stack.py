#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标签栈体检：逐个片段按栈检查闭合是否正确（不只数数量）。

为什么需要：`balanced()` 只比"<div class='formula'> 与 </div> 的数量"，模型把
`<span class="formula">…</div>` 写错配对时数量仍可能相等（另一个 div 多开一次），
计数式检查漏过；浏览器会自动闭合，页面看着正常但 DOM 结构错位，KaTeX 可能吞正文。
2026-11-16 coding 最后一段 `theory-th-rate-distortion-dedup-2-p5` 就是这么卡住的。

用法：python3 -I tools/tag_stack.py [--domain coding] [--limit 5]
退出码：0=无错配；1=有错配（gate_all.sh 可据此阻断）
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGS = {"p","h3","h4","ul","ol","li","table","thead","tbody","tr","td","th","div","span","strong","em","b","code","figure","figcaption"}
VOID = {"br","hr","img","input","meta","link"}

MATH = [re.compile(r"\$\$[\s\S]*?\$\$"), re.compile(r"\$[^$\n]{1,300}\$"), re.compile(r"\\\([\s\S]*?\\\)")]

def mask_math(s):
    """把公式内容替换成等长空格：`x_{<t}`、`a<b` 这类数学里的尖括号会被当成标签起始，
    造成大量假错配（2026-11-16 实测 555 个"错配"里绝大多数是这个原因）。"""
    for rx in MATH:
        def blank(m):
            return re.sub(r"[^\n]", " ", m.group(0))
        s = rx.sub(blank, s)
    return s

def scan(s):
    """返回 (问题列表, 栈深度)。问题列表元素形如 ('mismatch', 期望, 实际, 位置)。"""
    probs = []
    stack = []
    s = mask_math(s)
    for m in re.finditer(r"<[^>]*>", s):
        tag = m.group(0)
        if tag.startswith("<!") or tag.endswith("/>"):
            continue
        mm = re.match(r"</\s*([a-zA-Z0-9]+)", tag)
        if mm:
            name = mm.group(1).lower()
            if name not in TAGS:
                continue
            if stack and stack[-1] == name:
                stack.pop()
            else:
                probs.append(("mismatch", stack[-1] if stack else "-", name, m.start()))
        else:
            mo = re.match(r"<\s*([a-zA-Z0-9]+)", tag)
            if not mo:
                continue
            name = mo.group(1).lower()
            if name in VOID or name not in TAGS:
                continue
            stack.append(name)
    if stack:
        probs.append(("unclosed", ",".join(stack[-3:]), "-", len(s)))
    if s.count("$$") % 2:
        probs.append(("odd_dollar", "$$", "-", len(s)))
    return probs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    doms = [a.domain] if a.domain else ["moe","multimodal","coding","rl","video","image","audio"]
    total_bad = 0
    for d in doms:
        tp = os.path.join(ROOT, "content", "tasks", d + ".json")
        if not os.path.exists(tp):
            continue
        bad = []
        n = 0
        for t in json.load(open(tp, encoding="utf-8")):
            f = os.path.join(ROOT, t["out"])
            if not os.path.exists(f):
                continue
            n += 1
            s = open(f, encoding="utf-8").read()
            probs = scan(s)
            if probs:
                bad.append((t["id"], probs[:2]))
        print("%-11s 扫描 %4d 文件，错配 %d" % (d, n, len(bad)))
        for tid, p in bad[:a.limit]:
            print("   %-56s %s" % (tid, p))
        total_bad += len(bad)
    print("TOTAL_BAD %d" % total_bad)
    sys.exit(1 if total_bad else 0)

if __name__ == "__main__":
    main()
