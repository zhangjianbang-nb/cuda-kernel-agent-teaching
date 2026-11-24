#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行内公式 span 修补：把模型写坏的行内公式 span 修成合法的 $…$。

背景（2026-11-19）：moe 与 multimodal 两域都在 finalize 卡在 ESCAPED_TAGS_FAILED。
根因是片段里偶发的坏 span：
  1) `<span class="inline-math">$N_{\\mathrm{vis}}</span>` —— 结尾漏了 `$`，奇数个 $ 让
     build_long.fix_formulas 把后续整段标签转义成 &lt;span&gt;；
  2) `<span class="mathrm{BW}_{\\mathrm{link}}$</span>` —— class 被写成公式内容，缺
     `inline-math">$` 前缀。
本脚本把这两类都修成 `<span class="inline-math">$…$</span>`。

用法：python3 -I tools/fix_spans.py [--domain moe] [--dry]
"""
import argparse, glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPAN = re.compile(r'<span class="([^"]*)">([\s\S]*?)</span>')
GOOD = ("inline-math", "math")


def fix(path, dry=False):
    s = open(path, encoding="utf-8").read()
    orig = s

    def repl(m):
        cls, body = m.group(1), m.group(2)
        if cls in GOOD:
            b = body.strip()
            if not b:
                return m.group(0)
            # 不含 $ 的纯文本公式（如 N_vis、T_enc ≤ T_slo）是合法的，原样保留：
            # 硬加 $ 会让 KaTeX 去解析这些裸文本，反而可能报错。
            if "$" not in b:
                return m.group(0)
            if b.startswith("$") and b.endswith("$") and len(b) > 1:
                return m.group(0)
            b = b.strip("$").strip()
            return '<span class="inline-math">$%s$</span>' % b if b else m.group(0)
        # class 里混进公式内容（如 class="mathrm{BW}_{\mathrm{link}}$"）→ 整体当成公式
        if "$" in cls or "\\" in cls:
            inner = (cls + body).strip()
            inner = inner.strip("$")
            return '<span class="inline-math">$%s$</span>' % inner
        return m.group(0)

    s = SPAN.sub(repl, s)
    if s != orig and not dry:
        open(path, "w", encoding="utf-8").write(s)
    return s != orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    pat = os.path.join(ROOT, "content", "long", args.domain or "*", "**", "*.html")
    files = sorted(glob.glob(pat, recursive=True))
    n = 0
    for f in files:
        if fix(f, args.dry):
            n += 1
            print("fixed", os.path.relpath(f, ROOT))
    print("files", len(files), "changed", n)


if __name__ == "__main__":
    main()
