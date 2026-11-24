#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 7 个领域的所有图渲成一张测试页，供 fig_probe.js 做几何断言。

用法：python3 -I tools/fig_dump.py [输出路径]
默认输出 shots/figtest.html（必须在 /home/whu/workspace 下，snap chromium 读不了 /tmp）。
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RUN = os.path.dirname(HERE)
import figs

CSS = """
body{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:#fbfaf7;margin:0;padding:20px}
figure.diagram{margin:20px 0;border:1px solid #d8d3c6;border-radius:10px;overflow:hidden;background:#fff}
figure.diagram svg{display:block;width:100%;height:auto}
figure.diagram figcaption{padding:8px 14px;font-size:12px;color:#68727d;border-top:1px solid #d8d3c6}
h2{font-size:14px;color:#163a5a;margin:28px 0 6px}
"""

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RUN, "shots", "figtest.html")
    parts = []
    doms = sorted(os.listdir(os.path.join(RUN, "site", "data", "domains")))
    for dom in doms:
        data_dir = os.path.join(RUN, "site", "data", "domains", dom)
        if not os.path.exists(os.path.join(data_dir, "papers.json")): continue
        figs.set_data(data_dir)
        def load(n):
            return json.load(open(os.path.join(data_dir, n + ".json"), encoding="utf-8"))
        parts.append("<h2>%s · 首屏/地图</h2>" % dom)
        for name, svg in (("home-map", figs.home_map()), ("map", figs.map_overview())):
            parts.append('<figure class="diagram" data-fig="%s-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, name, svg, name))
        parts.append("<h2>%s · 论文</h2>" % dom)
        for p in load("papers"):
            parts.append('<figure class="diagram" data-fig="%s-tl-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, p["id"], figs.paper_pipeline(p), p["id"]))
            parts.append('<figure class="diagram" data-fig="%s-fam-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, p["id"], figs.paper_family(p), p["id"]))
        parts.append("<h2>%s · 算法</h2>" % dom)
        for a in load("algorithms"):
            parts.append('<figure class="diagram" data-fig="%s-alg-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, a["id"], figs.algo_flow(a), a.get("name", a["id"])))
        parts.append("<h2>%s · 理论</h2>" % dom)
        for t in load("theory"):
            parts.append('<figure class="diagram" data-fig="%s-th-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, t["id"], figs.theory_map(t), t.get("title", t["id"])))
        parts.append("<h2>%s · 方向</h2>" % dom)
        for d in load("directions"):
            parts.append('<figure class="diagram" data-fig="%s-dir-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, d["id"], figs.dir_map(d), d.get("name", d["id"])))
        parts.append("<h2>%s · 故事</h2>" % dom)
        for s in load("stories"):
            parts.append('<figure class="diagram" data-fig="%s-st-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, s["id"], figs.story_map(s), s.get("title", s["id"])))
            parts.append('<figure class="diagram" data-fig="%s-art-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, s["id"], figs.story_art(s), s.get("title", s["id"])))
        parts.append("<h2>%s · 全书</h2>" % dom)
        bk = load("book")
        for sec in bk.get("sections", []):
            parts.append('<figure class="diagram" data-fig="%s-bk-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, sec["id"], figs.book_map(sec), sec.get("title", sec["id"])))
        parts.append("<h2>%s · 附录</h2>" % dom)
        for e in load("appendix"):
            parts.append('<figure class="diagram" data-fig="%s-ap-%s">%s<figcaption>%s</figcaption></figure>'
                         % (dom, e["id"], figs.appendix_entry_fig(e), e.get("title", e["id"])))
    html = ("<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body>%s</body></html>" % (CSS, "".join(parts)))
    d = os.path.dirname(out)
    if d and not os.path.isdir(d): os.makedirs(d)
    io.open(out, "w", encoding="utf-8").write(html)
    print("写出 %s（%.1f KB）" % (out, len(html) / 1024.0))

if __name__ == "__main__":
    main()
