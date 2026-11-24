#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把单个条目的长文装配成一个独立静态页，用于生成期间的提前视觉抽检。

不写 site/data，不触碰 book_base（只读分片与已生成的图），因此可在生成过程中安全运行。
用法：python3 -I tools/preview_item.py <domain> <module> <item_id> [out.html]
"""
import importlib.util, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dom, module, item = sys.argv[1], sys.argv[2], sys.argv[3]
out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, "shots", "preview-%s.html" % item)
os.environ["DOMAIN"] = dom
spec = importlib.util.spec_from_file_location("bl", os.path.join(ROOT, "tools", "build_long.py"))
bl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bl)
tasks = json.load(open(os.path.join(ROOT, "content", "tasks", dom + ".json"), encoding="utf-8"))
parts = max(t["parts"] for t in tasks if t["module"] == module and t["item_id"] == item)
lh, n = bl.collect(module, item, parts)
data = json.load(open(os.path.join(ROOT, "site", "data", "domains", dom, {
    "papers": "papers", "algos": "algorithms", "algorithms": "algorithms", "theory": "theory",
    "directions": "directions", "stories": "stories", "exams": "assessments", "book": "book",
    "appendix": "appendix"}[module] + ".json"), encoding="utf-8"))
ent = next(x for x in data if x["id"] == item)
if module == "exams":
    m = re.match(r'(<nav class="long-toc">[\s\S]*?</nav>)', lh)
    if m: body = m.group(1) + bl.figs.exam_formula(ent) + lh[m.end():] + bl.figs.exam_table(ent)
    else: body = bl.figs.exam_formula(ent) + lh + bl.figs.exam_table(ent)
elif module == "book":
    body = lh  # 卷正文在 build 时另拼 base，预览只看看分片
else:
    pre, post = bl.inject(module, ent)
    body = bl.after_toc(lh, pre) + post
site = open(os.path.join(ROOT, "site", "index.html"), encoding="utf-8").read()
style = "\n".join(re.findall(r"<style>[\s\S]*?</style>", site))
html = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>预览 %s</title>
<link rel="stylesheet" href="../site/vendor/katex/katex.min.css">
%s
</head><body><div id="view" class="wrap">%s</div>
<script src="../site/vendor/katex/katex.min.js"></script>
<script src="../site/vendor/katex/contrib/auto-render.min.js"></script>
<script>renderMathInElement(document.getElementById('view'),{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\\\(',right:'\\\\)',display:false}]});</script>
</body></html>""" % (item, style, body)
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(html)
print("写出", out, "parts=%d" % n)
