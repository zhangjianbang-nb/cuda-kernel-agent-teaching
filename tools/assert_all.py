#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""终验断言：数据计数、单元厚度、图/表/公式、链接、bundle 一致性、可见总量。"""
import json, os, re, subprocess, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK=os.path.expanduser("~/.zcode/skills/ai-domain-research-and-teaching/scripts")
sys.path.insert(0,SK); import verify_site as V
DATA=os.path.join(ROOT,"site","data","domains","cuda")
def load(n): return json.load(open(os.path.join(DATA,n+".json"),encoding="utf-8"))
P=[]; F=[]
def ck(name,cond,detail=""):
 (P if cond else F).append(name)
 print(("PASS " if cond else "FAIL ")+name+("  "+detail if detail else ""))
def main():
 papers=load("papers");algs=load("algorithms");theory=load("theory");dirs=load("directions")
 stories=load("stories");assess=load("assessments");book=load("book");app=load("appendix")
 ck("papers=50",len(papers)==50,str(len(papers)))
 ck("algorithms=26",len(algs)==26,str(len(algs)))
 ck("theory=15",len(theory)==15,str(len(theory)))
 ck("directions=6",len(dirs)==6,str(len(dirs)))
 ck("stories=2",len(stories)==2,str(len(stories)))
 ck("assessments=88",len(assess)==88,str(len(assess)))
 ck("book=12",len(book.get("sections",[]))==12,str(len(book.get("sections",[]))))
 ck("appendix=18",len(app)==18,str(len(app)))
 # 单元厚度
 thin=[]
 for name,arr in [("papers",papers),("algos",algs),("theory",theory),("directions",dirs),("appendix",app)]:
  for x in arr:
   lh=x.get("long_html") or ""
   if V.vis_len(lh)<500: thin.append(f"{name}/{x.get('id')}:{V.vis_len(lh)}")
 for q in assess:
  if V.vis_len(q.get("long_html") or "")<500: thin.append(f"exam/{q.get('id')}:{V.vis_len(q.get('long_html') or '')}")
 for s in book["sections"]:
  if V.vis_len(s.get("html") or "")<500: thin.append(f"book/{s.get('id')}:{V.vis_len(s.get('html') or '')}")
 ck("all units >=500 chars",not thin,"; ".join(thin[:6])+(" ..." if len(thin)>6 else ""))
 # 图/表/公式
 bad=[]
 for p in papers:
  lh=p.get("long_html") or ""
  if V._figure_count(lh)<2 or V._table_count(lh)<1: bad.append("paper/"+p["id"])
 for a in algs:
  lh=a.get("long_html") or ""
  if V._figure_count(lh)<1 or V._table_count(lh)<1: bad.append("algo/"+a["id"])
 for t in theory:
  lh=t.get("long_html") or ""
  if V._figure_count(lh)<1 or V._table_count(lh)<1: bad.append("theory/"+t["id"])
 for d in dirs:
  lh=d.get("long_html") or ""
  if V._figure_count(lh)<1 or V._table_count(lh)<1: bad.append("dir/"+d["id"])
 for s in stories:
  if V._figure_count(s.get("long_html") or "")<1: bad.append("story/"+s["id"])
 ck("per-unit visuals",not bad,"; ".join(bad[:8]))
 figs=sum(V._figure_count(x.get("long_html") or "") for x in papers+algs+theory+dirs+stories)
 figs+=sum(V._figure_count(s.get("html") or "") for s in book["sections"])
 figs+=sum(V._figure_count(x.get("long_html") or "") for x in app)
 ck("total figures >=80",figs>=80,str(figs))
 am=sum(V._math_count(q.get("long_html") or "") for q in assess)
 at=sum(V._table_count(q.get("long_html") or "") for q in assess)
 ck("assess math >=100",am>=100,str(am)); ck("assess tables >=100",at>=100,str(at))
 # 公式字段
 badf=[p["id"] for p in papers if V._math_count(p.get("formula"))<1]+[a["id"] for a in algs if V._math_count(a.get("formula"))<1]+[t["id"] for t in theory if V._math_count(t.get("formula"))<1]
 ck("formula fields $$",not badf,"; ".join(badf[:6]))
 # 总量
 total=V.vis_len("".join(str(x) for x in []))  # placeholder
 # 用 verify 的 total_scan 逻辑
 cnt={"n":0}
 def walk(v):
  if isinstance(v,str): cnt["n"]+=V.vis_len(v)
  elif isinstance(v,dict):
   for x in v.values(): walk(x)
  elif isinstance(v,list):
   for x in v: walk(x)
 for n in ["domain","directions","algorithms","papers","evolution","theory","stories","assessments","summary","book","appendix","coverage"]:
  walk(load(n))
 ck("visible chars >=3,000,000",cnt["n"]>=3000000,str(cnt["n"]))
 # 链接
 ids=set()
 for arr in [papers,algs,theory,dirs,stories,assess]: 
  for x in arr: ids.add(({"papers":"papers","algorithms":"algos","theory":"theory","directions":"map","stories":"story","assessments":"exam"}[{id(papers):"papers",id(algs):"algorithms",id(theory):"theory",id(dirs):"directions",id(stories):"stories",id(assess):"assessments"}[id(arr)]],x.get("id")))
 for s in book["sections"]: ids.add(("book",s["id"]))
 for e in app: ids.add(("appendix",e["id"]))
 html="".join(str(x.get("long_html") or "") for x in papers+algs+theory+dirs+stories+app)
 html+="".join(str(s.get("html") or "") for s in book["sections"])
 badl=set()
 for m in re.finditer(r'href="#/([a-z]+)/([^"]+)"',html):
  if (m.group(1),m.group(2)) not in ids: badl.add(m.group(1)+"/"+m.group(2))
 ck("internal links resolve",not badl,"; ".join(list(badl)[:6]))
 # 禁 pre / 外链图片
 ck("no <pre>", "<pre" not in html.lower())
 ck("no external img", not re.search(r'<img[^>]+src="https?://',html))
 ck("no mermaid runtime", "mermaid" not in html.lower() and not os.path.exists(os.path.join(ROOT,"site","vendor","mermaid.min.js")))
 # 数据完整性：本工程用 split 布局（data/domains/<d>/*.json + manifest.js），
 # 技能里的 verify_site 只认老的扁平 data/<key>.json，直接跑会误报"缺少数据文件"。
 # 扁平布局（有 data/bundle.js）时才调 verify_site；split 布局改为校验域数据 JSON 可解析。
 if os.path.exists(os.path.join(ROOT,"site","data","bundle.js")):
  r=subprocess.run([sys.executable,os.path.join(SK,"verify_site.py"),"--site",os.path.join(ROOT,"site"),"--phase","all"],capture_output=True,text=True)
  errs=[l for l in r.stdout.splitlines() if l.startswith("[ERROR]")]
  warns=[l for l in r.stdout.splitlines() if l.startswith("[WARN]")]
  ck("verify_site 0 error",not errs,"%d errors"%len(errs))
  ck("verify_site 0 warning",not warns,"%d warnings"%len(warns))
 else:
  import glob as _g
  badj=[]
  for f in _g.glob(os.path.join(ROOT,"site","data","domains","*","*.json")):
   try: json.load(open(f,encoding="utf-8"))
   except Exception as e: badj.append(os.path.basename(f)+": "+str(e)[:60])
  ck("domain data JSON valid",not badj,"; ".join(badj[:6]))
  ck("manifest exists",os.path.exists(os.path.join(ROOT,"site","data","manifest.js")))
 print("\n== %d PASS / %d FAIL =="%(len(P),len(F)))
 if F: print("FAILED:",F)
 return 0 if not F else 1
if __name__=="__main__": sys.exit(main())
