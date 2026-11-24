#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公式定界符体检：单美元符必须成对、$$ 必须成对、\\( \\) 必须成对。

奇数个单 `$` 会让 KaTeX 自动渲染把后续正文吞进公式（2026-11-14 实见一处）。
默认只报告；--fix 会把形如 `$xxx</span>` 的漏尾补成 `$xxx$</span>`。
用法：python3 -I tools/formula_check.py [--fix]
"""
import argparse, glob, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMS = ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fix", action="store_true")
    ap.add_argument("--domain", default="", help="只查一个领域（finalize 时用，避免半成品领域阻断）")
    a = ap.parse_args(); bad = 0; fixed = 0
    for dom in ([a.domain] if a.domain else DOMS):
        for f in glob.glob(os.path.join(ROOT, "content", "long", dom, "*", "*.html")):
            s = open(f, encoding="utf-8").read(); orig = s
            # <code>$ref</code> 这类正文里的代码字面量是合法 $，先剔除再计数
            # （2026-11-20 coding 实测：JSON Schema 的 $ref 被误报成奇数 $）
            s2 = re.sub(r"<code>[\s\S]*?</code>", "", s)
            s2 = re.sub(r"\$\$[\s\S]*?\$\$", "", s2)
            if s2.count("$") % 2:
                bad += 1
                print("ODD$ %s" % os.path.relpath(f, ROOT))
                if a.fix:
                    # 漏尾形态：<span class="inline-math">$x</span>（x 内无 $）
                    def rep(m):
                        global fixed
                        body = m.group(2)
                        if "$" in body: return m.group(0)
                        fixed += 1
                        return m.group(1) + "$" + body + "$</span>"
                    s = re.sub(r'(<span class="inline-math">)(\$[^$<>]+)</span>', rep, s)
                    if s != orig: open(f, "w", encoding="utf-8").write(s)
            if s.count("\\(") != s.count("\\)"):
                bad += 1; print("ODD\\() %s" % os.path.relpath(f, ROOT))
    print("检查完毕：问题 %d 个，自动补尾 %d 处" % (bad, fixed))

if __name__ == "__main__":
    main()
