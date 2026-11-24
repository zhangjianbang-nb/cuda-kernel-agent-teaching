#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构修复：把片段里错配/未闭合的标签按栈改写，直到 tag_stack.scan() 干净为止。

判据来自 2026-11-16 全量体检（3039 个片段里 56 个真错配，另有 499 个是公式里的
`x_{<t}` 造成的假阳性 —— 扫描器已先掩掉公式再判）：
  1. `<span class="sym">…</p>`  → 输出 `</span></p>`（先关 inline，再关 block）
  2. `<table>…</tbody>` 缺 `</table>` → 补 `</table>`；多余的 tbody/tr/td/th 直接丢弃
     （HTML 允许省略这些闭合标签，浏览器自行补全）
  3. `<p>…<p>` 嵌套 → 开新 <p> 之前先关掉内层
  4. 结尾残留开标签 → 按栈逆序补闭合
只改结构，不动正文文字；修复后必须通过 scan() 才写盘，否则跳过并报文件名。

用法：python3 -I tools/repair_tags.py [--dry] [--domain moe]
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import tag_stack as TS

BLOCK = {"p","h3","h4","div","table","ul","ol","li","figure","figcaption"}
INLINE = {"span","strong","em","b","code"}
OPTIONAL_CLOSE = {"tbody","thead","tr","td","th","li"}
TOKEN = re.compile(r"<[^>]*>")

def masked_spans(s):
    """返回公式所占的 (start,end) 区间，修复时跳过这些区间里的"标签"。"""
    spans = []
    for rx in TS.MATH:
        for m in rx.finditer(s):
            spans.append((m.start(), m.end()))
    return spans

def inside(pos, spans):
    return any(a <= pos < b for a, b in spans)

def repair(s):
    spans = masked_spans(s)
    stack = []
    out = []
    last = 0
    for m in TOKEN.finditer(s):
        if inside(m.start(), spans):
            continue
        tag = m.group(0)
        if tag.startswith("<!") or tag.endswith("/>"):
            continue
        mm = re.match(r"</\s*([a-zA-Z0-9]+)", tag)
        if mm:
            name = mm.group(1).lower()
            if name not in TS.TAGS:
                continue
            if stack and stack[-1] == name:
                stack.pop()
                out.append((m.start(), m.end(), tag))
            elif name in stack:
                i = len(stack) - 1 - stack[::-1].index(name)
                for t in reversed(stack[i+1:]):
                    out.append((m.start(), m.start(), "</%s>" % t))
                out.append((m.start(), m.end(), tag))
                stack = stack[:i]
            elif name in OPTIONAL_CLOSE:
                out.append((m.start(), m.end(), ""))
            else:
                closed = []
                while stack and stack[-1] in INLINE:
                    closed.append("</%s>" % stack.pop())
                if stack and stack[-1] == name:
                    stack.pop()
                    out.append((m.start(), m.end(), "".join(closed) + tag))
                else:
                    out.append((m.start(), m.end(), "".join(closed)))
        else:
            mo = re.match(r"<\s*([a-zA-Z0-9]+)", tag)
            if not mo:
                continue
            name = mo.group(1).lower()
            if name in TS.VOID or name not in TS.TAGS:
                continue
            if name in BLOCK and stack and stack[-1] == "p":
                out.append((m.start(), m.start(), "</p>"))
                stack.pop()
            stack.append(name)
            out.append((m.start(), m.end(), tag))
    tail = "".join("</%s>" % t for t in reversed(stack))
    # 按位置重写
    res = []
    cur = 0
    for a, b, txt in out:
        res.append(s[cur:a]); res.append(txt); cur = b
    res.append(s[cur:]); res.append(tail)
    return "".join(res)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    doms = [a.domain] if a.domain else ["moe","multimodal","coding","rl","video","image","audio"]
    fixed = skipped = 0
    for d in doms:
        tp = os.path.join(ROOT, "content", "tasks", d + ".json")
        if not os.path.exists(tp):
            continue
        for t in json.load(open(tp, encoding="utf-8")):
            f = os.path.join(ROOT, t["out"])
            if not os.path.exists(f):
                continue
            s = open(f, encoding="utf-8").read()
            if not TS.scan(s):
                continue
            r = s
            for _ in range(6):
                if not TS.scan(r):
                    break
                r = repair(r)
                if r.count("$$") % 2:
                    j = r.rfind("$$")
                    r = r[:j] + r[j+2:]
            if TS.scan(r):
                skipped += 1
                print("SKIP %s/%s %s" % (d, t["id"], TS.scan(r)[:1]))
                continue
            fixed += 1
            print("FIX  %s/%s" % (d, t["id"]))
            if not a.dry:
                open(f, "w", encoding="utf-8").write(r)
    print("FIXED %d SKIPPED %d" % (fixed, skipped))
    sys.exit(1 if skipped else 0)

if __name__ == "__main__":
    main()
