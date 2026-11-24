#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate per-domain module blueprints for the CUDA kernel agent book."""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import llm
META = json.load(open(os.path.join(HERE, "domain_meta.json"), encoding="utf-8"))
CAT = os.path.join(ROOT, "content", "papers-catalog.json")
OUT = os.path.join(ROOT, "content", "blueprint")

def paper_lines(dom, n=60):
    cat = json.load(open(CAT, encoding="utf-8"))
    ps = [p for p in cat if dom in p.get("domains", [])]
    return "\n".join("- %s | %s (%s)" % (p["id"], p["title"][:90], p.get("year", "")) for p in ps[:n]), [p["id"] for p in ps]

HEAD = """你是《CUDA Kernel Agent 工程全书》的研究主编。这套书只讲一件事：**LLM/agent 如何生成、优化、验证并部署 GPU kernel（CUDA C++ / Triton / CuTe / PTX），以及如何可信地评测它**——KernelBench 系基准、执行反馈与 NCU/SASS profile、多轮 RL 与可验证奖励、正确性 oracle 与形式验证、生产端到端收益、Triton/CuTe/PTX 与 roofline/SOL。
领域：{name}
领域焦点：{focus}
写作语言：简体中文。所有判断必须能落到具体机制、数字口径或工程代价上，禁止空话。
"""

def prompt_dirs(dom):
    lines, ids = paper_lines(dom)
    return HEAD.format(**META[dom]) + f"""
任务：为该领域设计 6 个研究方向（方向=一组围绕同一问题的技术路线，不是论文标题分类）。
输出严格 JSON（不要解释）：
{{"directions":[{{"id":"dir-<英文slug>","name":"<中文名，≤18字>","name_en":"<英文名>","question":"<核心问题，≥30字>","why":"<为什么难/为什么重要，≥40字>","core_tech":["<技术1>","<技术2>","<技术3>"],"teams":["<团队或机构1>","<团队或机构2>"],"key_papers":["<论文id>"],"recent":"<近两年进展，≥40字>","challenges":["<挑战1>","<挑战2>"],"related":["<相邻方向id>"]}}]}}
要求：
- 6 个方向必须覆盖：基准与可信评测、agent 脚手架与执行反馈、RL 与数据、正确性 oracle 与形式验证、生产端到端部署、硬件感知 DSL 与 profile。不要互相重叠。
- id 用小写字母/数字/连字符，以 dir- 开头；name/question/why/recent 不得为空。
- key_papers 必须从下面论文清单里选（每条方向 2–5 篇），不得编造。
- teams 只写你确信的真实团队（不确定就给空数组）；related 只能引用本批 6 个方向里的 id。
论文清单：
{lines}
"""

def prompt_algos(dom, start=0, n=20, avoid=None):
    lines, ids = paper_lines(dom)
    return HEAD.format(**META[dom]) + f"""
任务：为该领域写 {n} 个可复用的方法/部署配方卡（第 {start+1}–{start+n} 张；每张卡=一个能落地的评测、反馈、搜索、RL 或验证方法，不是论文摘要）。
输出严格 JSON：
{{"algorithms":[{{"id":"alg-<slug>","name":"<中文名，≤20字>","year":<1950-2026整数>,"direction":"<方向id，形如 dir-...>","tier":"classic|recent","problem":"<解决什么问题，≥25字>","idea":"<一句话机制，≥30字>","flow":["<步骤1>","<步骤2>","<步骤3>","<步骤4>"],"formula":"$$<核心公式>$$","pros":["<优点1>","<优点2>"],"cons":["<代价/失效1>","<代价/失效2>"],"successors":[],"papers":["<论文id>"]}}]}}
要求：
- 覆盖：可信基线（TF32/compile/cuBLAS）、隐藏 shape/分布、roofline/SOL 评分、防作弊 contract、变异测试审计 checker、fuzz + fp64 参考、合约/形式验证、batch invariance 门、NCU 指标回灌、SASS/warp stall profile、二进制插桩 tracing、MCTS/进化/keep-revert 搜索、多 agent、策略 IR、DSL+SOL、CuTe 生成、多轮 RL、robust reward、TRLOO、pairwise ranking、轨迹 SFT、合成数据、预算感知搜索、goal-only、问题驱动、端到端回归。
- flow 4–6 步，必须能看出一次 kernel 生成/优化/验证的流动；pros/cons 各 ≥2 条且具体。
- formula 必须是 KaTeX display math，写清这个方法的评分/时延/显存/误差/奖励公式。
- papers 从给定清单选 1–2 篇；不得编造论文 id。
- id 必须与下列已存在 id 不同（不得重复，也不得换个 slug 讲同一件事）：
{avoid}
论文清单：
{lines}
"""

def prompt_theory(dom, start=0, n=14, avoid=None):
    lines, ids = paper_lines(dom)
    return HEAD.format(**META[dom]) + f"""
任务：为该领域写 {n} 张理论卡（第 {start+1}–{start+n} 张；每张讲清一个公式/定律/界，服务 kernel 性能、正确性与容量决策）。
输出严格 JSON：
{{"theory":[{{"id":"th-<slug>","title":"<中文标题，≤20字>","direction":"<方向id>","plain":"<一句话直觉解释，≥30字>","formula":"$$<LaTeX 公式>$$","limits":["<失效条件1>","<失效条件2>"],"variables":[{{"sym":"<符号>","meaning":"<含义>"}}],"prereq":[]}}]}}
要求：
- 覆盖：roofline 与带宽/算力界、Speed-of-Light、kernel launch 开销、occupancy/latency hiding、warp stall 分类、FP 误差界、batch invariance 定义、计时噪声/置信区间、reward hacking 博弈、多轮信用分配、迁移增益界、端到端 Amdahl、能耗、内存峰值。
- 公式必须是 KaTeX 可渲染的 display math（用 $$...$$ 包裹），不得用 Unicode 符号冒充。
- 每张卡 limits ≥2 条，variables ≥3 个符号；direction 只能取本领域 6 个方向 id 之一。
- id 必须与下列已存在 id 不同（不得重复，也不得换个 slug 讲同一个定理）：
{avoid}
论文清单（仅作背景，不必逐篇引用）：
{lines}
"""

def prompt_stories(dom):
    return HEAD.format(**META[dom]) + f"""
任务：为该领域写 2 个贯穿式故事（不是寓言拼盘：一个主角、一条主线、从旧秩序到新秩序再到新问题）。
输出严格 JSON：
{{"stories":[{{"id":"story-<slug>","title":"<故事名，≤14字>","scene":"<世界设定，≥60字>","roles":[{{"role":"<角色>","maps_to":"<技术概念>"}}],"covers":"<覆盖的技术线，≥40字>","boundaries":"<类比哪里不像，≥40字>","plot":[{{"act":"<幕名，≤10字>","text":"<这一幕发生什么，≥60字>"}}],"steps":["<场景1>","<场景2>","<场景3>","<场景4>","<场景5>"]}}]}}
要求：
- roles 4–8 组，每组 role→maps_to 必须一一对应到本领域的概念（kernel、benchmark、checker、profiler、reward、verifier、serving）。
- plot 5–7 幕，每幕 text ≥60 字，能看出冲突升级与解决；steps 是 plot 的短标签。
"""

def prompt_exams(dom, start, n=25, refs=""):
    return HEAD.format(**META[dom]) + f"""
任务：为该领域出 {n} 道考核题（第 {start+1}–{start+n} 题），五层难度：L1 定义、L2 机制、L3 计算/推导、L4 系统设计、L5 开放判断。
输出严格 JSON：
{{"exams":[{{"id":"q-{dom}-<两位序号>","level":<1-5>,"module":"<papers|theory|algorithms|directions|stories>","ref":"<被考的条目id>","question":"<题干，≥40字，要能考出真实理解>","answer_outline":["<要点1>","<要点2>","<要点3>","<要点4>"]}}]}}
要求：
- 题目必须围绕 GPU kernel agent（基准口径、正确性 oracle、NCU/SASS profile、多轮 RL、reward hacking、生产端到端），不要问"什么是 CUDA"这类泛题。
- 每题 answer_outline 4–6 条，每条 ≥15 字；L3 题必须含可计算/可推导的量。
- id 用 q-{dom}-{start+1:02d} 起的两位序号，不重复。
- ref 必须从下面给出的条目 id 清单里选，且 module 与 ref 的类型一致；每个方向至少 1 题，每篇经典论文至少 1 题。
条目 id 清单：
{refs}
"""

def prompt_book(dom):
    return HEAD.format(**META[dom]) + f"""
任务：为该领域设计一部 12 卷的全书目录（每卷=一条工程主线，从问题定义到上线验收）。
输出严格 JSON：
{{"book":{{"title":"<书名>","subtitle":"<副标题>","note":"<一句话说明>","sections":[{{"id":"ch1","title":"<卷名，≤16字>","subtitle":"<副标题>","note":"<本卷讲什么，≥50字>","story_map":["<与故事的对应>"]}}]}}}}
要求：
- 12 卷按真实工程顺序：问题定义 → 基准演化 → 可信评测 → oracle 审计 → agent 脚手架 → 硬件反馈 → RL → 数据/SFT → 生产落地 → 可靠性/BI → 成本/容量 → 团队路线图。卷与卷之间要有依赖关系。
- 每卷 note ≥50 字，写清输入、产出与关键决策。
"""

def prompt_appendix(dom):
    return HEAD.format(**META[dom]) + f"""
任务：为该领域设计 18 条速查附录（术语、基准、指标口径、工具链、配方、失败模式、检查清单、合规）。
输出严格 JSON：
{{"appendix":[{{"id":"ap-<slug>","title":"<中文标题，≤18字>","kind":"术语|工具|配方|失败模式|清单|合规","content":"<一句话说明，≥40字>"}}]}}
要求：覆盖术语表、基准速查、指标口径、防作弊清单、NCU 指标、RL 配方、验证器清单、工具链选型、失败模式、成本表、论文索引、硬件规格、Triton/CuTe/PTX 对照、BI 检查、评测协议、数据合成、上线门、回滚清单；kind 只能用给定六类。
"""

PROMPTS = {"directions": prompt_dirs, "algorithms": prompt_algos, "theory": prompt_theory,
           "stories": prompt_stories, "book": prompt_book, "appendix": prompt_appendix}

def item_refs(dom):
    rows = []
    bdir = os.path.join(OUT, dom)
    for module, key in (("directions", "directions"), ("algorithms", "algorithms"),
                        ("theory", "theory"), ("stories", "stories"), ("book", "book"),
                        ("appendix", "appendix")):
        p = os.path.join(bdir, module + ".json")
        if not os.path.exists(p): continue
        data = json.load(open(p, encoding="utf-8"))
        items = data.get("book", {}).get("sections", []) if module == "book" else data.get(key, [])
        for it in items:
            iid = it.get("id")
            title = it.get("title") or it.get("name") or ""
            if iid: rows.append(f"- {module}:{iid} | {title[:50]}")
    cdir = os.path.join(ROOT, "content", "cards", dom)
    if os.path.isdir(cdir):
        for f in sorted(os.listdir(cdir)):
            if f.endswith(".json"):
                c = json.load(open(os.path.join(cdir, f), encoding="utf-8"))
                rows.append(f"- papers:{c.get('_paper_id')} | {(c.get('_title') or '')[:50]}")
    return "\n".join(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True); ap.add_argument("--module", required=True)
    ap.add_argument("--start", type=int, default=0); ap.add_argument("--count", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(os.path.join(OUT, args.domain), exist_ok=True)
    path = os.path.join(OUT, args.domain, args.module + ".json")
    if os.path.exists(path) and args.start == 0:
        print("exists:", path); return
    prev = {}
    if os.path.exists(path) and args.start > 0:
        prev = json.load(open(path, encoding="utf-8"))
    n = args.count or (10 if args.module == "algorithms" else 7 if args.module == "theory" else 0)
    avoid = ""
    if prev:
        avoid = ", ".join(str(x.get("id")) for x in (prev.get(args.module) or []) if isinstance(x, dict))
    if args.module == "algorithms" and (args.count or args.start):
        txt, fin, usage = llm.call(prompt_algos(args.domain, args.start, n, avoid), temperature=0.5, json_mode=True)
        data = llm.parse_json(txt)
    elif args.module == "theory" and (args.count or args.start):
        txt, fin, usage = llm.call(prompt_theory(args.domain, args.start, n, avoid), temperature=0.5, json_mode=True)
        data = llm.parse_json(txt)
    elif args.module == "exams":
        data = {"exams": []}
        batches = [(args.start, n)] if (args.count or args.start) else [(0, 25), (25, 25)]
        refs = item_refs(args.domain)
        for start, bn in batches:
            txt, fin, usage = llm.call(prompt_exams(args.domain, start, bn, refs), temperature=0.5, json_mode=True)
            part = llm.parse_json(txt)
            data["exams"].extend(part.get("exams", []))
            print("exams batch", start, len(part.get("exams", [])), "fin", fin, flush=True)
    else:
        txt, fin, usage = llm.call(PROMPTS[args.module](args.domain), temperature=0.5, json_mode=True)
        data = llm.parse_json(txt)
    if prev:
        key = args.module
        seen = set()
        merged = []
        for x in (prev.get(key) or []) + (data.get(key) or []):
            i = x.get("id") if isinstance(x, dict) else None
            if i and i in seen:
                continue
            if i:
                seen.add(i)
            merged.append(x)
        data[key] = merged
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)
    n = len(data.get(args.module) or data.get("book", {}).get("sections", []) or [])
    print("saved", path, "items", n, "fin", fin)

if __name__ == "__main__":
    main()
