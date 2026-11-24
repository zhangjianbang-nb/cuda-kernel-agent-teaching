#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为七个领域站点生成数据驱动的内联 SVG 图与速查表（不引入外部资源）。"""
import json, os, re, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(os.path.expanduser("~"),".zcode","skills","ai-domain-research-and-teaching","scripts"))
import svgkit as K
DATA=os.path.join(ROOT,"site","data")
P={}; A={}; T={}; D={}; S={}
def set_data(path):
 global DATA,P,A,T,D,S
 DATA=path
 P={p["id"]:p for p in load("papers")}
 A={a["id"]:a for a in load("algorithms")}
 T={t["id"]:t for t in load("theory")}
 D={d["id"]:d for d in load("directions")}
 S={s["id"]:s for s in load("stories")}
def load(n): return json.load(open(os.path.join(DATA,n+".json"),encoding="utf-8"))
def short(s,n=42):
 if isinstance(s,(list,tuple)): s="、".join(str(x) for x in s)
 elif isinstance(s,dict): s="、".join(str(v) for v in s.values())
 s=re.sub(r"<[^>]+>","",str(s or "")); s=re.sub(r"\s+"," ",s).strip()
 return s if len(s)<=n else s[:n-1]+"…"
def fit(svg):
 """把 760 宽的画布裁到实际内容宽度，避免短流程图右侧留一大片空白。"""
 right=0.0
 for m in re.finditer(r'<rect[^>]*\sx="([\d.]+)"[^>]*\swidth="([\d.]+)"',svg):
  right=max(right,float(m.group(1))+float(m.group(2)))
 for m in re.finditer(r'<text[^>]*\bx="([\d.]+)"',svg):
  right=max(right,float(m.group(1)))
 if right<=0: return svg
 w=min(760.0,right+24)
 svg=re.sub(r'viewBox="0 0 760 ([\d.]+)"','viewBox="0 0 %.1f \\1"'%w,svg,count=1)
 svg=svg.replace("<svg ","<svg style=\"max-width:%.0fpx;margin:0 auto\" "%w,1)
 return svg
def fig(svg,label,caption,key):
 return '<figure class="diagram" data-fig="%s">%s<figcaption><b>%s</b> · %s</figcaption></figure>\n'%(key,fit(svg),K.esc(label),K.esc(caption))
def table(headers,rows,caption,key):
 h="".join("<th>"+K.esc(x)+"</th>" for x in headers)
 b="".join("<tr>"+"".join("<td>"+K.esc(str(c))+"</td>" for c in r)+"</tr>" for r in rows)
 return '<table class="mini" data-fig="%s"><caption>%s</caption><thead><tr>%s</tr></thead><tbody>%s</tbody></table>\n'%(key,K.esc(caption),h,b)

# ---------- 首页 ----------
def home_map():
 """首页技术栈：三列——负载与 SLO / 算子与精度 / 调度与并行，内容取自本领域 6 个方向。"""
 dirs=load("directions")
 cols=[("负载与 SLO", dirs[:2]),("算子与精度", dirs[2:4]),("调度与并行", dirs[4:6])]
 body=[]; y=16; w=228; gap=26; x0=(K.W-(w*3+gap*2))/2; maxh=0
 for i,(head,ds) in enumerate(cols):
  x=x0+i*(w+gap)
  body.append(K.txt(x+w/2,y-2,head,fs=11,fill=K.MUTED,anchor="middle",weight="600"))
  lines=[]
  for d in ds:
   # 2026-11-18 视觉验收缺陷 #5：原来把方向名截到 16 字、整块最多 9 行，导致
   # "aux l…" 这类断词截断。改为允许 14 行、方向名放宽到 22 字，盒子高度自适应。
   lines.append("· "+short(d.get("name"),40))
   lines.append("  "+short("、".join((d.get("core_tech") or [])[:3]),200))
  ll=K.wrap("\n".join(lines),(w-24)/11.0)
  if len(ll)>20: ll=ll[:20]; ll[-1]=ll[-1].rstrip("，、；")+"…"
  hh=14+len(ll)*17+10
  body.append(K.rect(x,y+8,w,hh,fill=K.CARD,stroke=K.LINE,rx=8))
  body.append(K.lines_at(x+12,y+26,ll,fs=11.5,fill=K.INK2,lh=17))
  maxh=max(maxh,hh)
 for i in range(2):
  ax=x0+i*(w+gap)+w+3; body.append(K.arrow_h(y+8+maxh/2,ax,ax+gap-6,color=K.LINE))
 return fig(K.svg(y+8+maxh+22,"".join(body)),"技术栈","负载与 SLO → 算子与精度 → 调度与并行三列；每列两个方向，箭头是依赖关系。","home-stack")

def map_overview():
 dirs=load("directions"); body=[]; w=170; gap=18; h=92; x0=13
 for i,d in enumerate(dirs):
  row,col=divmod(i,4); x=x0+col*(w+gap); y=16+row*(h+22)
  body.append(K.rect(x,y,w,h,fill=K.CARD,stroke=K.LINE,rx=8))
  body.append(K.txt(x+12,y+20,"D%d"%(i+1),fs=10.5,fill=K.MUTED,weight="700"))
  body.append(K.txt(x+12,y+40,short(d.get("name"),14),fs=12.5,fill=K.INK,weight="700"))
  ll=K.wrap(short(d.get("question"),60),146/11.0)
  if len(ll)>2: ll=ll[:2]; ll[-1]=ll[-1].rstrip("，、；")+"…"
  body.append(K.lines_at(x+12,y+58,ll,fs=11,fill=K.MUTED,lh=15))
 return fig(K.svg(16+2*(h+22)+2,"".join(body)),"方向地图",str(len(dirs))+" 个方向按「解决什么问题」组织；相邻方向共享技术，不是互斥学科。","map-overview")

def home_table():
 exams=load("assessments"); book=load("book"); app=load("appendix")
 rows=[("研究方向",str(len(D)),"#/map"),("论文条目",str(len(P)),"#/papers"),("算法条目",str(len(A)),"#/algos"),
       ("理论课",str(len(T)),"#/theory"),("考核题",str(len(exams)),"#/exam"),("全书卷数",str(len(book.get("sections",[]))),"#/book"),
       ("附录条目",str(len(app)),"#/appendix"),("入门故事",str(len(S)),"#/story")]
 body="".join("<tr><td>%s</td><td>%s</td><td><a href=\"%s\">%s</a></td></tr>"%(K.esc(a),K.esc(b),K.esc(c),K.esc(c)) for a,b,c in rows)
 return '<table class="mini" data-fig="home-scale"><caption>%s</caption><thead><tr><th>单元</th><th>数量</th><th>入口</th></tr></thead><tbody>%s</tbody></table>\n'%(K.esc("全站规模：每类单元都有独立长文、图示或公式、速查表"),body)

# ---------- 论文 ----------
def paper_pipeline(p):
 steps=p.get("pipeline") or []
 if not steps:
  steps=["输入：原始数据/文本/条件","清洗：过滤、去重、质量分","配比：混合与课程","训练：目标函数与并行","产出：可复用的模型/配方"]
 steps=[short(x,36) for x in steps][:6]
 svg=K.flow_v(steps,kinds=["in"]+["mid"]*(len(steps)-2)+["out"] if len(steps)>2 else ["in"]*len(steps))
 return fig(svg,"流水线","从输入到输出的数据流；每一步的模块与代价在正文展开。","paper-pipeline")
def paper_family(p):
 prev=[P[x]["title"] for x in (p.get("prereq") or []) if x in P][:3] or ["领域入口（无上游）"]
 nxt=[P[x]["title"] for x in (p.get("successors") or []) if x in P][:3] or ["暂无下游记录"]
 cur=short(p.get("title",""),40)
 svg=K.chain3(prev,cur,nxt,cur_sub=f"{p.get('year','')} · {short(p.get('venue',''),26)}")
 return fig(svg,"家谱","%s 的上游问题、本文位置与下游继承；箭头表示方法/问题的传递，不是时间先后。"%short(p.get("title"),24),"paper-family")
def paper_table(p):
 e=p.get("experiments") or {}
 rows=[("数据集",short(e.get("datasets"),38)),("基线",short(e.get("baselines"),38)),("主要结果",short(e.get("results"),38)),("消融",short(e.get("ablations"),38)),("局限",short(e.get("limits"),38))]
 return table(["项","内容"],rows,"实验速查：这篇论文拿什么数据、和谁比、提升来自哪里","paper-exp")
# ---------- 算法 ----------
def algo_flow(a):
 steps=[short(x,38) for x in (a.get("flow") or [])][:6] or ["输入","核心变换","输出"]
 subs=[short(x,46) for x in (a.get("pros") or [])][:len(steps)]
 svg=K.flow_v(steps,subs=subs if len(subs)==len(steps) else None)
 return fig(svg,"执行流程","从输入到输出的关键步骤；每一步的复杂度与坑在正文展开。","algo-flow")
def algo_table(a):
 rows=[("年份 · 方向",f"{a.get('year','')} · {D.get(a.get('direction'),{}).get('name','')}"),("解决什么",short(a.get("problem"),60)),("一句话机制",short(a.get("idea"),60)),("代价与失效",short("；".join(a.get("cons") or []),70)),("后继",short("、".join(A[x]["name"] for x in (a.get("successors") or []) if x in A),60))]
 return table(["项","内容"],rows,"速查：这一页回答的五件事","alg-quick")
# ---------- 理论 ----------
def theory_map(t):
 pre=[T[x]["title"] for x in (t.get("prereq") or []) if x in T][:3]
 steps=["前置：" + ("、".join(pre) if pre else "无（入口卡）"),"定义："+short(t.get("plain"),34),"公式："+short(t.get("formula"),34),"失效："+short("；".join(t.get("limits") or []),34)]
 svg=K.flow_v(steps,kinds=["in","mid","mid","warn"])
 return fig(svg,"先修与边界","这张卡从哪来、核心公式是什么、在哪里失效；先修关系与正文一致。","theory-map")
def theory_table(t):
 rows=[("符号","含义"),]
 for v in (t.get("variables") or [])[:6]:
  rows.append((v.get("sym",""),short(v.get("meaning",""),50)))
 if len(rows)==1: rows.append(("—","见正文公式"))
 return table(["符号","含义"],rows[1:],"符号表：公式里每个字母的含义","theory-sym")
# ---------- 方向 ----------
def dir_map(d):
 papers=[P[x]["title"] for x in (d.get("key_papers") or []) if x in P][:4]
 tech="、".join((d.get("core_tech") or [])[:4])
 # 三列：问题 / 技术 / 论文
 body=[]; y=16; w=220; gap=50; x0=(K.W-(w*3+gap*2))/2
 cols=[("核心问题",short(d.get("question"),60),K.AMBER_SOFT,"#ecd9b8",K.AMBER),
       ("关键技术",tech,K.ACC_SOFT,"#d6e2ec",K.ACC_DEEP),
       ("代表论文","\n".join("· "+short(t,34) for t in papers),K.OK_SOFT,"#cde9d5",K.OK)]
 maxh=0
 for i,(head,text,fill,stroke,col) in enumerate(cols):
  x=x0+i*(w+gap); ll=K.wrap(text,(w-24)/12.0); hh=12+len(ll)*18+10
  body.append(K.txt(x+w/2,y-2,head,fs=11,fill=K.MUTED,anchor="middle",weight="600"))
  body.append(K.rect(x,y+8,w,hh,fill=fill,stroke=stroke,rx=7))
  body.append(K.lines_at(x+12,y+26,ll,fs=12,fill=col,weight="500",lh=18))
  maxh=max(maxh,hh)
 for i in range(2):
  ax=x0+i*(w+gap)+w+3; body.append(K.arrow_h(y+8+maxh/2,ax,ax+gap-6,color=K.LINE))
 return fig(K.svg(y+8+maxh+22,"".join(body)),"问题→技术→论文","这个方向的核心问题、关键技术栈与代表论文；箭头是支撑关系。","dir-map")
def dir_table(d):
 rows=[]
 for pid in (d.get("key_papers") or [])[:8]:
  p=P.get(pid)
  if p: rows.append((p.get("title",""),str(p.get("year","")),p.get("type",""),short(p.get("core_idea",""),60)))
 return table(["论文","年份","类型","一句话贡献"],rows,"代表论文表：按方向收录的关键工作","dir-papers")
# ---------- 故事 ----------
def story_map(s):
 plot=s.get("plot") or []
 steps=[]; subs=[]; kinds=[]
 for i,act in enumerate(plot[:6]):
  steps.append(short(act.get("act"),18))
  subs.append(short(act.get("text"),40))
  kinds.append("in" if i==0 else ("out" if i==len(plot)-1 else ("warn" if i==2 else "mid")))
 if not steps:
  steps=["旧秩序","危机","抉择","新秩序","新问题"]; subs=[short(s.get("scene"),40)]+[""]*4
  kinds=["in","mid","warn","mid","out"]
 svg=K.flow_v(steps,subs=subs,kinds=kinds)
 return fig(svg,"故事地图","主角依次经过的幕与每幕的代价；这张图是读故事的路线图。","story-map")
def story_table(s):
 rows=[("主角",short(s.get("title"),40)),("世界",short(s.get("scene"),90)),("角色映射",short("；".join("%s→%s"%(r.get("role"),r.get("maps_to")) for r in (s.get("roles") or [])[:6]),110)),("技术覆盖",short(s.get("covers"),70)),("边界",short(s.get("boundaries"),90))]
 return table(["项","内容"],rows,"故事速查：谁在演、演的是哪条技术线、哪些地方不能照搬","story-quick")

# ---------- 故事场景图 ----------
def story_art(s):
 """故事场景插画：用故事自己的角色、幕与映射画一张「舞台」图，不引外部资源。"""
 body=[]
 body.append(K.rect(10,10,740,330,fill="#fbf7ef",stroke="#e4dccb",rx=14))
 body.append(K.rect(210,20,340,42,fill="#f6e7c8",stroke="#d9b47a",rx=8))
 body.append(K.txt(380,46,short(s.get("title"),22),fs=14,fill="#7a4a12",anchor="middle",weight="700"))
 roles=(s.get("roles") or [])[:5]
 plot=(s.get("plot") or [])[:6]
 # 左侧：主角
 lead=roles[0] if roles else {"role":"主角","maps_to":"待定"}
 body.append('<circle cx="120" cy="128" r="30" fill="#f0d3b0" stroke="#c9a27a" stroke-width="1.4"/>')
 body.append('<circle cx="110" cy="124" r="2.6" fill="#3a281d"/><circle cx="130" cy="124" r="2.6" fill="#3a281d"/>')
 body.append('<path d="M113 136 Q120 142 127 136" stroke="#3a281d" stroke-width="1.5" fill="none"/>')
 body.append(K.txt(120,172,short(lead.get("role"),12),fs=12,fill=K.INK,anchor="middle",weight="700"))
 body.append(K.txt(120,190,"→ "+short(lead.get("maps_to"),16),fs=10,fill=K.ACC,anchor="middle"))
 body.append(K.txt(120,238,"舞台中央",fs=10,fill=K.MUTED,anchor="middle"))
 # 右侧：幕卡（三列两行；原来两列五幕会压到底部角色映射上）
 for i,act in enumerate(plot):
  row,col=divmod(i,3); x=290+col*150; y=78+row*92
  body.append(K.rect(x,y,142,84,fill=K.CARD,stroke=K.LINE,rx=8))
  body.append(K.txt(x+10,y+18,"第%d幕 · %s"%(i+1,short(act.get("act"),9)),fs=10.5,fill=K.INK,weight="700"))
  ll=K.wrap(short(act.get("text"),80),142/10.5)[:3]
  body.append(K.lines_at(x+10,y+34,ll,fs=9.5,fill=K.MUTED,lh=14))
 # 底部：角色映射（幕卡下留 12px）
 y=268
 body.append(K.txt(290,y,"角色 → 技术概念：",fs=10,fill=K.MUTED))
 for i,r in enumerate(roles[:4]):
  x=290+i*112
  body.append(K.rect(x,y+8,104,36,fill=K.OK_SOFT,stroke="#cde9d5",rx=6))
  body.append(K.txt(x+52,y+22,short(r.get("role"),8),fs=9.5,fill=K.INK,anchor="middle",weight="600"))
  body.append(K.txt(x+52,y+35,short(r.get("maps_to"),9),fs=8.5,fill=K.MUTED,anchor="middle"))
 return fig(K.svg(360,"".join(body)),short(s.get("title"),20),
            short(s.get("scene"),60),"story-art-"+re.sub(r"[^a-z0-9-]","",s.get("id",""))[:24])
# ---------- 书卷 ----------
def book_map(sec):
 steps=[short(sec.get("title"),30),"问题：这一卷要补上什么缺口","机制：核心表示/公式","代价：失败模式与工程边界"]
 svg=K.flow_v(steps,kinds=["in","mid","mid","warn"])
 return fig(svg,"本卷路线","这一卷从哪个问题出发、用什么机制、付出什么代价；与导语一一对应。","book-map")
def book_table(sec):
 rows=[]
 for d in list(D.values()):
  rows.append((d.get("name",""),short(d.get("question"),56),"、".join((d.get("core_tech") or [])[:3])))
 if not rows: rows=[("—","见正文","—")]
 return table(["方向","核心问题","关键技术"],rows,"六方向对照：本卷的取舍落在哪条技术路线上","book-dirs")
def book_formula(sec):
 return ('<div class="formula">$$C_{\\text{train}}\\approx 6\\,N\\,D_{\\text{tok}}$$</div>'
         '<p class="note">本卷算力账本：N 是参数量、D_tok 是训练 token 数。数据配比、并行切分与课程安排，最后都要在这条账本上做取舍。</p>\n')
# ---------- 附录 ----------
def appendix_map():
 steps=["术语表 A–C","公式与数字索引","论文/算法清单","复现/调试/评测","教学与面试","开放问题与阅读路线"]
 svg=K.flow_v(steps,kinds=["in","mid","mid","mid","mid","out"])
 return fig(svg,"附录结构","六组速查材料的索引关系；按「查词→查数→查论文→查工程→查教学」使用。","appendix-map")
# ---------- 考题 ----------
def exam_formula(q):
 ref=q.get("ref","")
 f=""
 for pool in (P,T,A):
  if ref in pool: f=pool[ref].get("formula","") or ""; break
 if not f:
  f=r"\text{核心关系}=f(\text{输入};\theta)"
 f=re.sub(r"^\s*\$\$|\$\$\s*$","",f).strip()
 n=max(1,len(q.get("key_points") or []))
 score=r"S=\sum_{i=1}^{%d} w_i\,\mathbb{1}[\text{要点}_i],\qquad w_i=\frac{1}{%d}"%(n,n)
 return ('<div class="formula" data-fig="exam-formula">$$%s$$</div>\n'%f
        +'<div class="formula" data-fig="exam-score">$$%s$$</div>\n'%score)
def exam_table(q):
 rows=[]
 for i,k in enumerate((q.get("key_points") or [])[:4]):
  rows.append((f"判分点 {i+1}",short(k,46),"必答"))
 for i,e in enumerate((q.get("common_errors") or [])[:2]):
  rows.append((f"常见错误 {i+1}",short(e,46),"扣分"))
 t1=table(["项","内容","判定"],rows,"判分表：答到哪些点给分、哪些错误扣分","exam-rubric")
 erows=[(f"错误 {i+1}",short(e,50),f"−{min(20,100//max(1,len(q.get('common_errors') or [])))} 分") for i,e in enumerate((q.get("common_errors") or [])[:3])]
 t2=table(["项","表现","代价"],erows,"失分表：常见错误与扣分上限","exam-errors")
 return t1+t2
# ---------- 附录条目 ----------
APP_STEPS={
 "glossary":["收录范围","词条组织","交叉引用","常见混淆"],
 "formulas":["公式清单","符号约定","适用条件","失效边界"],
 "numbers":["数字来源","统计口径","对比基准","易错读法"],
 "papers":["入选标准","时间线","贡献分组","阅读顺序"],
 "algos":["算法清单","输入输出","复杂度","实现坑"],
 "recipes":["任务定义","数据准备","训练配置","验收标准"],
 "debug":["症状","根因","排查顺序","修复"],
 "eval":["指标","数据集","评测协议","常见陷阱"],
 "datasets":["规模","许可","下载","清洗"],
 "code":["仓库","入口","依赖","最小复现"],
 "hardware":["显存","吞吐","精度","成本"],
 "myths":["误解","事实","为什么流传","怎么纠正"],
 "interview":["问题","考察点","回答骨架","追问"],
 "teaching":["受众","顺序","练习","评估"],
 "open":["问题","现状","卡点","可行路径"],
 "reading":["入门","进阶","前沿","配套代码"],
 "course":["课时","实验","交付","评分"],
}
def _app_steps(e):
 for k,v in APP_STEPS.items():
  if k in str(e.get("id","")): return v
 return ["范围","关键点","用法","边界"]
def appendix_entry_fig(e):
 labels=_app_steps(e); parts=[x.strip() for x in re.split(r"[；;]",str(e.get("summary") or "")) if x.strip()]
 subs=[short(parts[i],40) if i<len(parts) else None for i in range(len(labels))]
 svg=K.flow_v(["条目："+short(e.get("title"),22)]+labels[1:],subs=subs,kinds=["in","mid","mid","out"])
 return fig(svg,"条目结构","这个附录条目的四段结构；正文按同一顺序展开。","app-"+str(e.get("id")))
def appendix_entry_table(e):
 labels=_app_steps(e); parts=[x.strip() for x in re.split(r"[；;]",str(e.get("summary") or "")) if x.strip()]
 rows=[]
 for i,l in enumerate(labels[:4]):
  rows.append((l,short(parts[i],56) if i<len(parts) else "见正文"))
 return table(["项","内容"],rows,"速查：这一条怎么用","app-t-"+str(e.get("id")))
