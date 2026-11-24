#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量生成长文 HTML 片段（本地 18891 API，断点续跑，3 路并发）。"""
import argparse, concurrent.futures, json, os, re, time, urllib.request
MIN_CJK=int(os.environ.get("GEN_MIN_CJK","2900"))
# 目标长度与下限都可用环境变量覆盖：引擎只有 4 个并发槽（实测 requests_running 恒为 4），
# 吞吐被 decode 卡死，缩短每段目标长度是唯一能提速的杠杆（2026-11-16 用户抱怨太慢）。
TARGET_CJK=int(os.environ.get("GEN_TARGET_CJK","3200"))
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS=os.path.join(ROOT,"content","tasks","cuda.json")
API="http://127.0.0.1:18891/v1/chat/completions"; MODEL="DeepSeek-V4.1-Flash-1017-TF"
STYLE="""你是《CUDA Kernel Agent 工程全书》的技术作者，读者是有工程背景的中文读者。这套书只讲一件事：**LLM/agent 如何生成、优化、验证并部署 GPU kernel（CUDA C++ / Triton / CuTe / PTX），以及如何可信地评测它**——KernelBench 系基准、执行反馈与 NCU/SASS profile、多轮 RL 与可验证奖励、正确性 oracle 与形式验证、生产端到端收益、Triton/CuTe/PTX 与 roofline/SOL。不写训练配方、不写产品评测、不堆砌硬件参数。写作要求：
1. 只输出 HTML 片段，不要 markdown 围栏，不要 <html>/<body>/<script>/<style>。
2. 用 <h3>一 · 小标题</h3> 组织 4–6 节；正文用 <p>；列表用 <ul><li>；表格用 <table class="mini"><thead>…</thead><tbody>…</tbody></table>；公式用 <div class="formula">$$…$$</div>；禁止 <pre>。
3. 目标 3200 个汉字，不得少于 2900 字。信息密度高，不写套话，不重复开头，不重复其他部分已经讲过的内容。
4. 每个部分至少出现：一个具体机制、一个公式或伪代码思路、一个性能/正确性代价（时延/带宽/显存/编译时间/token）、一个具体例子。
5. 不编造实验数字、引用页码、年份；只使用给定事实中的数字，没有就定性表述。禁止“大概/可能/一般来说”糊过去。
6. 不要写“总结”“结语”式收尾；最后一段落在具体机制或工程判断上。
7. 末尾加 <p class="paper-line">对应：{module}/{item_id} · 第 {part}/{parts} 部分</p>。
8. 同条目其他片段、同模块其他条目共享同一批读者：禁止复述它们会讲的基础定义与常识。某个概念若是别的片段的主题，用一句话指路即可，把篇幅留给本片段的角度。开头不要写“上一部分我们……”。"""
STORY_STYLE="""你是《CUDA Kernel Agent 工程全书》的故事作者，读者是有工程背景、但想先建立直觉的中文读者。写作要求：
1. 只输出 HTML 片段，不要 markdown 围栏，不要 <html>/<body>/<script>/<style>。
2. 用 <h3>一 · 场景名</h3> 组织 3–5 幕。每一幕先写具体场景、人物动作与对话，让冲突自己说话；不要写成论文或产品说明。
3. 目标 3200 个汉字，不得少于 2900 字。故事要有推进：旧秩序 → 危机 → 抉择 → 新秩序 → 新问题；人物要有欲望、误判与代价。
4. 每一幕至少包含：一个可感知的细节（声音、气味、时间压力）、一次角色抉择、一个技术机制的“翻译”（让角色用行话或比喻说出 benchmark/checker/profile/reward/verifier/serving）。
5. 每个部分末尾加一小节 <h3>工匠笔记</h3>：用 3–5 条把本幕的场景逐条映射到技术概念，并写一条“这个类比哪里不像”。
6. 不编造实验数字、引用页码、年份；只使用给定事实中的数字，没有就定性表述。
7. 末尾加 <p class="paper-line">对应：{module}/{item_id} · 第 {part}/{parts} 部分</p>。
8. 每一幕只推进本幕的新冲突；前情用一两句带过，不要重演上一幕已经演过的场面。"""
def cjk(s): return len(re.findall(r"[\u4e00-\u9fff]",s))
def clean(s):
 s=s.strip(); s=re.sub(r"^```(?:html)?\s*","",s); s=re.sub(r"\s*```$","",s)
 s=re.sub(r"<script[\s\S]*?</script>","",s,flags=re.I); s=re.sub(r"<style[\s\S]*?</style>","",s,flags=re.I)
 if "<html" in s.lower():
  m=re.search(r"<body[^>]*>([\s\S]*?)</body>",s,re.I); s=m.group(1) if m else re.sub(r"<[^>]+>","",s)
 return s.strip()
def balanced(s):
 checks=[("<p","</p>"),("<h3","</h3>"),("<table","</table>"),("<ul","</ul>"),("<div class=\"formula\"","</div>")]
 for a,b in checks:
  if s.count(a)!=s.count(b): return False, a
 if s.count("$$")%2: return False,"$$"
 return True,""
_TAGS={"p","h3","h4","ul","ol","li","table","thead","tbody","tr","td","th","div","span","strong","em","b","code","figure","figcaption"}
_VOID={"br","hr","img","input","meta","link"}
def autoclose(s):
 """模型写完（finish_reason=stop）但忘了收尾标签时，按栈把缺的闭合标签补在末尾。

 只在「栈非空、且全程无错配/无多余闭合」时修补；错配、奇数 $$、标签被截在中间一律返回 None
 （交给重试）。补出来的嵌套与浏览器自动闭合的结果一致，不会吞掉后续内容。
 """
 if s.count("$$")%2: return None
 stack=[]; last_end=0
 for m in re.finditer(r"<[^>]*>",s):
  tag=m.group(0); last_end=m.end()
  if tag.startswith("<!") or tag.endswith("/>"): continue
  mm=re.match(r"</\s*([a-zA-Z0-9]+)",tag)
  if mm:
   name=mm.group(1).lower()
   if name not in _TAGS: continue
   if stack and stack[-1]==name: stack.pop()
   else: return None          # 错配或多出来的闭合标签
  else:
   mo=re.match(r"<\s*([a-zA-Z0-9]+)",tag)
   if not mo: continue
   name=mo.group(1).lower()
   if name in _VOID or name not in _TAGS: continue
   stack.append(name)
 if not stack: return None
 return s+"".join("</%s>"%t for t in reversed(stack))
def call(prompt,max_tokens=12288,pad=0):
 # 8192 会把"目标 3200 字"偶尔写超的片段截断（2026-11-16 实测 coding 有 4% 段落在 3 次尝试里
 # 全是 finish_reason=length），放宽到 12288 让长文一次写完，减少无效重试。
 prompt=prompt.replace("→"," 到 ")
 if pad: prompt=prompt+"\n请开始写作。"+"。"*pad
 body={"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.65,"chat_template_kwargs":{"enable_thinking":False}}
 req=urllib.request.Request(API,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
 # 2026-11-23：引擎被多客户端占满时单请求可排到 1.5h 以上；900s 超时会抛弃仍在
 # 计算的请求（引擎不取消），僵尸请求继续占 lane，形成"超时→重试→队列更长"的正反馈。
 # 改成 4h 兜底：宁可慢，也不抛弃已烧掉的算力。
 with urllib.request.urlopen(req,timeout=14400) as r: d=json.loads(r.read())
 ch=d["choices"][0]
 return ch["message"]["content"],ch.get("finish_reason")
def style_text(t):
 """按当前 TARGET_CJK/MIN_CJK 改写风格模板里的字数要求（默认 3200/2900 原样保留）。"""
 s=STORY_STYLE if t.get("module")=="stories" else STYLE
 if TARGET_CJK!=3200 or MIN_CJK!=2900:
  s=s.replace("目标 3200 个汉字，不得少于 2900 字",f"目标 {TARGET_CJK} 个汉字，不得少于 {MIN_CJK} 字")
 return s

def build_prompt(t):
 style=style_text(t)
 return style.format(module=t["module"],item_id=t["item_id"],part=t["part"],parts=t["parts"])+f"""

本次任务：为《{t['title']}》写深读的第 {t['part']}/{t['parts']} 部分。
本部分主题：{t['angle']}
只写这一部分，不要写导语式总结，不要预告其他部分。
前文已经写过的主题（不要重复，也不要换词重讲）：
{t.get('avoid','（无）')}

可用事实（不得超出这些事实编造数字）：
{t['facts']}
"""
def expand_append(t,s):
 """整篇写不够字数时的兜底：追加一节补齐。
 模型整篇常常收在 2700 字左右（2026-11-16 实测 coding 有 20 段三次重写都卡在 2742 附近），
 但单写一节能稳定写到 700–900 汉字，而且不会破坏已有结构与目录。"""
 m=re.search(r'<p class="paper-line">[\s\S]*?</p>\s*$',s)
 tail=m.group(0) if m else ""
 base=s[:m.start()] if m else s
 # 按缺口定量补：整篇常停在 2600–2900 字，缺口只有 100–300 字，
 # 固定写 700–900 字会白烧 40% 的 token（2026-11-18 实测 53 段/h 时的主要浪费）。
 need=max(400,min(1200,MIN_CJK-cjk(base)+60))
 prompt=(style_text(t)
  +f"\n\n本次任务：为《{t['title']}》第 {t['part']}/{t['parts']} 部分【补写一节】。"
  +f"\n本部分主题：{t['angle']}"
  +f"\n只输出一个 <h3> 小节（用具体小标题，不要数字编号），下面 2–4 个 <p>，合计约 {need} 个汉字（不少于 {max(300,need-80)} 字）。"
  +"内容必须与前文不重复，聚焦这个方案的边界、失效条件与系统代价；可含一个公式或一张小表。"
  +"\n不要写导语，不要写总结，不要重复已有段落。"
  +"\n可用事实（不得超出这些事实编造数字）：\n"+t["facts"])
 out=""
 for _ in range(2):
  try:
   frag,fin=call(prompt,max_tokens=4096); frag=clean(frag)
   ok,bad=balanced(frag)
   if not ok:
    fixed=autoclose(frag)
    if fixed and balanced(fixed)[0]: frag=fixed; ok=True
   if not ok: continue
   mo=re.search(r"(<h3[\s\S]*)",frag)
   if mo: frag=mo.group(1)
   frag=re.sub(r'<p class="paper-line">[\s\S]*?</p>\s*','',frag)
   out=base+"\n"+frag.strip()+"\n"+tail
   if cjk(out)>=MIN_CJK: return out
  except Exception:
   time.sleep(3)
 return out or s
def expand_until(t,s,rounds=4):
 """反复补节直到达到 MIN_CJK。实测整篇常在 1700–2600 字收尾（模型自停，非截断），
 与其三次整篇重写（每次 ~1900 token，全部作废），不如每次补一节（~800 字）稳定收敛。"""
 cur=s
 for _ in range(rounds):
  if cjk(cur)>=MIN_CJK: break
  nxt=expand_append(t,cur)
  if cjk(nxt)<=cjk(cur): break
  cur=nxt
 return cur
def gen_one(t,force=False):
 out=os.path.join(ROOT,t["out"])
 if not force and os.path.exists(out):
  s=open(out,encoding="utf-8").read()
  if cjk(s)>=MIN_CJK: return ("skip",t["id"],cjk(s))
 prompt=build_prompt(t); last=""
 for attempt in range(2):
  try:
   s,fin=call(prompt); s=clean(s); n=cjk(s); ok,bad=balanced(s); tag=""
   if n<MIN_CJK:
    # 已经写到一个像样的骨架（>=1700 字）就不再整篇重写：交给补节路径，
    # 否则每段要白烧 2–3 次 1900 token 的整篇生成（实测 4.5 请求/段，吞吐掉 4 倍）。
    last=s
    if n>=1700 and ok: break
    if n>=1700 and fin!="length": break
    prompt=build_prompt(t)+f"\n\n上一版只有 {n} 个汉字，明显偏短。请扩写到 {TARGET_CJK} 字左右，增加具体机制、公式解释、系统代价与例子，不要重复已有句子。"; continue
   if not ok and fin!="length" and os.environ.get("GEN_AUTOCLOSE","1")=="1":
    # 写完却忘收尾标签：按栈补闭合标签收下，省掉一整轮重生成（域末补缺口尤其费时）
    fixed=autoclose(s)
    if fixed and balanced(fixed)[0]: s=fixed; ok=True; n=cjk(s); tag="*"
   if fin=="length" or not ok:
    prompt=build_prompt(t)+f"\n\n上一版被截断或标签不闭合（"+bad+"）。请压缩到 {TARGET_CJK+200} 字左右，确保所有标签闭合、公式 $$ 成对，再输出完整片段。"; last=s; continue
   if "<pre" in s.lower():
    s=re.sub(r"<pre[\s\S]*?</pre>",lambda m:'<div class="formula">'+re.sub(r"<[^>]+>","",m.group(0)).strip()+"</div>",s,flags=re.I)
   if "<h3" not in s: s="<h3>一 · "+t["angle"]+"</h3>\n"+s
   os.makedirs(os.path.dirname(out),exist_ok=True); open(out,"w",encoding="utf-8").write(s.strip()+"\n")
   return ("ok",t["id"],str(n)+tag)
  except Exception as e:
   last=f"ERR {e}"; time.sleep(2+attempt*3)
   # 引擎在特定 token 长度上缺 _topk_sel Triton 变体（MissingTritonVariant→500）；
   # 追加几个 token 把长度推离边界再试。
   prompt=prompt+"\n请开始写作。"+"。"*(attempt+1)
 # 整篇偏短：改用"追加一节"补齐（不要求整篇闭合——先按栈补标签再追加）
 if isinstance(last,str) and "<h3" in last and cjk(last)>=1700:
  base=last
  if not balanced(base)[0]:
   fx=autoclose(base)
   if fx: base=fx
  s2=expand_until(t,base)
  if cjk(s2)>=MIN_CJK:
   os.makedirs(os.path.dirname(out),exist_ok=True); open(out,"w",encoding="utf-8").write(s2.strip()+"\n")
   return ("ok",t["id"],str(cjk(s2))+"+")
 if isinstance(last,str) and "<h3" in last:
  return ("fail",t["id"],"cjk=%d bal=%s %s"%(cjk(last),balanced(last)[0],str(last)[:80]))
 return ("fail",t["id"],str(last)[:200])
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--workers",type=int,default=3); ap.add_argument("--limit",type=int,default=0); ap.add_argument("--module",default=""); ap.add_argument("--force",action="store_true"); ap.add_argument("--tasks",default=""); ap.add_argument("--domain",default="")
 args=ap.parse_args()
 tp=args.tasks or (os.path.join(ROOT,"content","tasks",args.domain+".json") if args.domain else TASKS)
 if not os.path.exists(tp): raise SystemExit("缺少任务表："+tp)
 tasks=json.load(open(tp,encoding="utf-8"))
 if args.module: tasks=[t for t in tasks if t["module"]==args.module]
 todo=[]
 for t in tasks:
  out=os.path.join(ROOT,t["out"])
  if args.force or not os.path.exists(out) or cjk(open(out,encoding="utf-8").read())<MIN_CJK: todo.append(t)
 if args.limit: todo=todo[:args.limit]
 print(f"todo={len(todo)} workers={args.workers}",flush=True)
 done=ok=fail=skip=0; t0=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
  futs={ex.submit(gen_one,t,args.force):t for t in todo}
  for fut in concurrent.futures.as_completed(futs):
   st,tid,info=fut.result(); done+=1
   if st=="ok": ok+=1
   elif st=="fail": fail+=1
   else: skip+=1
   el=time.time()-t0; rate=done/el*3600 if el else 0
   print(f"[{done}/{len(todo)}] {st} {tid} cjk={info} elapsed={el/60:.1f}m rate={rate:.0f}/h",flush=True)
   with open(os.path.join(ROOT,"content","gen-progress.jsonl"),"a",encoding="utf-8") as f:
    f.write(json.dumps({"ts":time.strftime("%Y-%m-%d %H:%M:%S"),"status":st,"id":tid,"info":str(info)},ensure_ascii=False)+"\n")
 print(f"DONE ok={ok} fail={fail} skip={skip} elapsed={(time.time()-t0)/60:.1f}m",flush=True)
if __name__=="__main__": main()
