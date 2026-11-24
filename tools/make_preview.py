#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成一份「样章预览」页面：用站点真实 CSS 渲染若干已生成的长文片段。

用法：python3 -I tools/make_preview.py [--domain moe] [--n 3]
输出：preview/index.html（需在项目根目录起静态服务，KaTeX 走 ../site/vendor）
"""
import argparse, glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="moe")
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()

    idx = open(os.path.join(ROOT, "site", "index.html"), encoding="utf-8").read()
    m = re.search(r"<style>([\s\S]*?)</style>", idx)
    css = m.group(1) if m else ""

    files = sorted(glob.glob(os.path.join(ROOT, "content", "long", args.domain, "**", "*.html"), recursive=True))
    pick = files[-args.n:] if len(files) >= args.n else files
    body = []
    for f in pick:
        s = open(f, encoding="utf-8").read()
        rel = os.path.relpath(f, ROOT)
        body.append('<section class="section"><p class="note muted">样章来源：' + rel + '</p>' + s + '</section>')

    name = json.load(open(os.path.join(ROOT, "tools", "domain_meta.json"), encoding="utf-8"))[args.domain]["name"]

    head = (
        '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>样章预览 · ' + name + '</title>\n'
        '<link rel="stylesheet" href="../site/vendor/katex/katex.min.css">\n'
        '<style>' + css + '\n'
        '.preview-wrap{max-width:820px;margin:0 auto;padding:24px 20px 80px}\n'
        '.preview-wrap .katex-display{max-width:100%;overflow-x:auto;overflow-y:hidden;margin:8px 0}\n'
        '.preview-wrap .katex-display>.katex{max-width:100%}\n'
        '</style></head>\n<body>\n<div class="preview-wrap">\n'
        '<header class="hero"><div class="kicker">样章预览 · 生成中</div>\n'
        '<h1>' + name + '</h1>\n'
        '<p class="lede">以下为已生成片段，使用站点正式样式渲染；完整站点在七个领域生成并收尾后发布。</p></header>\n'
    )
    tail = (
        '\n</div>\n'
        '<script defer src="../site/vendor/katex/katex.min.js"></script>\n'
        '<script defer src="../site/vendor/katex/contrib/auto-render.min.js"></script>\n'
        "<script>\n"
        "window.addEventListener('load',function(){\n"
        "  if(!window.renderMathInElement) return;\n"
        "  try{renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});}catch(e){}\n"
        "  setTimeout(function(){try{renderMathInElement(document.body,{delimiters:[{left:'\\\\(',right:'\\\\)',display:false},{left:'\\\\[',right:'\\\\]',display:true}],throwOnError:false});}catch(e){}},300);\n"
        "});\n"
        "</script>\n"
        '</body></html>'
    )

    os.makedirs(os.path.join(ROOT, "preview"), exist_ok=True)
    out = os.path.join(ROOT, "preview", "index.html")
    open(out, "w", encoding="utf-8").write(head + "\n".join(body) + tail)
    print("wrote", out, "fragments", len(pick))


if __name__ == "__main__":
    main()
