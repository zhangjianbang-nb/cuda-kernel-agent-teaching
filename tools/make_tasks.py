#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build per-domain generation tasks (content/tasks/<dom>.json).

Each task = one long-form HTML segment. Angles focus on data engineering and
training schemes only; facts come from per-paper cards or per-item fact cards.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
META = json.load(open(os.path.join(HERE, "domain_meta.json"), encoding="utf-8"))

PAPER_ANGLES_DEEP = [
 ("问题现场与旧方案", "这篇论文之前，GPU kernel 工程的主流做法（手写 CUDA、Triton、库调用）是什么？具体痛点：开发周期、性能上限、正确性、可维护性；为什么非改不可。用一个真实推理服务或算子库场景开场，不要写摘要。"),
 ("基准与口径", "论文用什么基准、基线、硬件、dtype、指标（faster rate / speedup / geomean / fast_p / roofline）；哪些数字不可比；隐藏 shape/分布怎么处理；给出可核查的测量口径。"),
 ("方法与机制", "核心方法（单轮提示 / agent 脚手架 / RL / verifier）按一次 kernel 生成—编译—运行—评测的流动拆步骤；每一步的输入、输出、代价。"),
 ("执行反馈与 profile", "编译错误、运行错误、NCU/SASS/warp stall、roofline 诊断怎么回灌；反馈的粒度、延迟与信息量；为什么硬件反馈比裸 speedup 更有效。"),
 ("奖励与激励", "奖励函数、正确性门、speedup 归一化、reward hacking（复制 torch、恒等映射、fallback、计时作弊、自训练分支）；怎么在环境里防住。"),
 ("系统代价与规模", "token 成本、GPU 时、搜索轮数、编译时间、缓存与并发；规模上去以后哪里先崩；中小团队的真实预算。"),
 ("失败模式与诊断", "正确性漏检、shape 特化、batch invariance 违规、OOM、性能回退、静默降级；怎么监控、怎么定位、怎么回滚。"),
 ("生产迁移与端到端", "kernel 级加速怎么映射到端到端；fallback、框架集成、维护成本、跨硬件迁移；什么情况下不值得上线。"),
 ("边界与开放问题", "适用边界、跨 shape/GPU/dtype/框架迁移、与相邻工作的差别；给出判断而不是口号。"),
]
PAPER_ANGLES_SHALLOW = [
 ("论文速览", "问题、核心思想、方法机制、基准口径；一页讲清这篇论文在 CUDA kernel agent 版图上的位置。"),
 ("边界与迁移", "失效模式、适用边界、与相邻工作的差别；什么情况下不该用它。"),
]
ALGO_ANGLES = [
 ("问题与适用边界", "这个方法解决什么具体问题、不解决什么；先用一个线上事故或评测翻车案例说明为什么需要它。"),
 ("机制步骤", "按一次 kernel 生成/优化/验证的流动拆步骤；每一步的输入、输出、代价。"),
 ("公式与推导", "核心评分/时延/显存/误差/奖励公式逐项解释，给出推导的关键一步；伪代码落到可实现。"),
 ("负载与评测配方", "适合什么模型/算子/shape/硬件；基线怎么选、输入分布怎么设、指标怎么算；负载不对时会发生什么。"),
 ("部署配方", "工具链（Triton/CuTe/PTX）、profile 工具、编译/运行环境、CI 门；给出一个可复现的配置思路。"),
 ("系统代价与吞吐", "token、GPU 时、编译时间、搜索轮数、内存/能耗；规模上去以后哪里先崩。"),
 ("失败模式与诊断", "正确性漏检、reward hacking、shape 特化、BI 违规、性能回退；怎么监控、怎么回滚。"),
 ("与相邻方法对照", "同族方法怎么选；给出决策表与适用条件。"),
]
THEORY_ANGLES = [
 ("直觉与定义", "一句话直觉、严格定义、为什么需要、常见误解。"),
 ("公式与推导", "公式逐项含义、推导关键步、离散化/近似在哪。"),
 ("适用边界", "假设、失效条件、规模上限；什么情况下公式不再成立。"),
 ("在 kernel 评测与容量决策中的用法", "这个公式怎么用来定基线、定 roofline、定搜索预算、定上线门；给一个算例。"),
 ("误用与反例", "最常见的误用、后果、怎么识别；给一个反例。"),
]
DIR_ANGLES = [
 ("问题全景", "这个方向要解决什么、边界在哪、为什么其他方向替代不了。"),
 ("三条路线的机制差异", "同一问题的三条技术路线，机制差在哪、代价差在哪。"),
 ("评测侧的具体做法", "基准、基线、输入分布、指标、防作弊；给出可执行的测量与建模方法。"),
 ("部署侧的具体做法", "工具链、profile、CI、上线门、回滚；给出可复现的配方。"),
 ("开放问题与工程判断", "还没解决的问题、未来两年的判断、什么情况下不值得投入。"),
]
STORY_ANGLES = [
 ("第一幕：旧秩序与危机", "场景、人物、冲突；把手写 kernel 的代价写出来，让危机自己说话。"),
 ("第二幕：第一次抉择", "主角选择一条技术路线（agent / RL / verifier），付出代价；把机制翻译成行话或比喻。"),
 ("第三幕：转折", "第一次失败暴露了什么问题（正确性漏检 / 榜单虚高 / reward hacking），主角怎么改方案；冲突升级。"),
 ("第四幕：新秩序", "新方案跑通，代价转移；写清胜利的边界。"),
 ("第五幕：新问题", "旧问题解决后出现的新问题（BI、生产缩水、维护成本）；留下开放结局。"),
 ("工匠笔记合集", "逐幕映射到技术概念，写清每个类比在哪里不像；给出可执行的检查清单。"),
]
EXAM_ANGLES = [
 ("读题与考点拆解", "拆题干、指出考点、给出解题路径与需要调用的公式；不要直接给答案。"),
 ("参考解答与评分", "完整解答、关键步骤、常见错误、评分点；公式与数字口径要一致。"),
]
BOOK_ANGLES = [
 ("卷首：这一卷要回答什么", "这一卷的问题、上一卷留下的缺口、本卷的赌注；用一个具体算子或服务场景开场。"),
 ("基准与口径", "本卷面对的基准、基线、硬件、dtype、指标；怎么把「快」翻译成可复核的数字。"),
 ("可信评测", "TF32/FP32 基线、隐藏 shape/分布、roofline、内存/能耗/BI、anti-cheat；怎么建一套不被骗的 harness。"),
 ("Oracle 审计", "checker 的漏检率、变异测试、fuzz、形式验证、合约验证；怎么证明「正确」。"),
 ("Agent 脚手架", "coder/judge/profiler/search 的分工；执行反馈、NCU/SASS、多轮修正。"),
 ("硬件反馈与 profile", "roofline、warp stall、SASS、二进制插桩；怎么让 agent 看见时间去哪了。"),
 ("RL 与数据", "多轮奖励、robust reward、TRLOO、合成数据、轨迹 SFT、去重防污染。"),
 ("生产落地", "端到端、fallback、框架集成、维护成本；kernel 级加速怎么变成服务收益。"),
 ("可靠性与 BI", "确定性、NaN/Inf、内存峰值、能耗、batch invariance；上线门怎么设。"),
 ("成本与容量", "token 预算、GPU 预算、搜索轮数、编译时间；中小团队怎么选路线。"),
 ("团队路线图", "评测 → agent → SFT → RL → 上线；每一阶段的输入、产出、验收。"),
 ("案例复盘与下一卷的钩子", "一个端到端案例：算子从哪来、怎么压测、哪里崩过、最后怎么修；下一卷接什么。"),
]
APPENDIX_ANGLES = [
 ("定义与分类", "条目的准确定义、分类维度、与相邻概念的区别。"),
 ("速查表", "给出一张可直接照着用的速查表：字段、阈值、口径。"),
 ("工程阈值与经验数字", "常见阈值、经验数字、测量方法；没有数字就写清怎么测。"),
 ("常见坑与检查清单", "踩坑清单、检查顺序、回滚方案。"),
 ("与其他条目的关系", "上游依赖、下游影响、在全书中的位置。"),
]

def s(x): return "" if x is None else str(x)
def arr(x): return x if isinstance(x, list) else []

def fmt_facts_card(c):
    parts = []
    for k, lab in (("background", "背景"), ("problem", "问题"), ("core_idea", "核心思想"),
                   ("architecture", "结构"), ("training", "训练"), ("formula", "公式"),
                   ("walkthrough", "训练流程"), ("impact", "影响"), ("summary", "概述")):
        if c.get(k): parts.append(f"{lab}：{s(c[k])}")
    if arr(c.get("pipeline")): parts.append("数据/训练管线：" + "；".join(arr(c["pipeline"])))
    if arr(c.get("data_recipe")): parts.append("数据配方：" + "；".join(arr(c["data_recipe"])))
    if arr(c.get("train_recipe")): parts.append("训练配方：" + "；".join(arr(c["train_recipe"])))
    ex = c.get("experiments") or {}
    if isinstance(ex, dict):
        if arr(ex.get("datasets")): parts.append("数据集：" + "、".join(arr(ex["datasets"])))
        if arr(ex.get("baselines")): parts.append("基线：" + "、".join(arr(ex["baselines"])))
        for k, lab in (("results", "结果"), ("ablations", "消融"), ("limits", "局限")):
            if ex.get(k): parts.append(f"{lab}：{s(ex[k])}")
    if arr(c.get("innovation")): parts.append("创新点：" + "；".join(arr(c["innovation"])))
    if arr(c.get("limitations")): parts.append("局限：" + "；".join(arr(c["limitations"])))
    if arr(c.get("facts")): parts.append("可用事实：\n" + "\n".join("· " + s(x) for x in arr(c["facts"])))
    if arr(c.get("anchors")): parts.append("数字锚点：" + "；".join(arr(c["anchors"])))
    if arr(c.get("pitfalls")): parts.append("失败模式：" + "；".join(arr(c["pitfalls"])))
    return "\n".join(parts)

def fmt_facts_generic(item, f):
    parts = []
    for k, lab in (("plain", "一句话"), ("definition", "定义"), ("formula", "公式"),
                   ("question", "核心问题"), ("why", "为什么重要"), ("problem", "问题"),
                   ("idea", "机制"), ("how", "做法"), ("note", "本卷内容"),
                   ("content", "条目说明"), ("scene", "世界设定")):
        if item.get(k): parts.append(f"{lab}：{s(item[k])}")
    for k, lab in (("core_tech", "关键技术"), ("challenges", "挑战"), ("flow", "步骤"),
                   ("pros", "优点"), ("cons", "代价"), ("limits", "失效条件"),
                   ("variables", "变量"), ("roles", "角色"), ("plot", "剧情"),
                   ("steps", "节点"), ("story_map", "故事映射"), ("answer_outline", "答案要点")):
        v = item.get(k)
        if not v: continue
        if isinstance(v, list) and v and isinstance(v[0], dict):
            txt = "；".join("、".join(f"{kk}={vv}" for kk, vv in x.items()) for x in v)
        else:
            txt = "；".join(s(x) for x in v) if isinstance(v, list) else s(v)
        parts.append(f"{lab}：{txt}")
    if arr(f.get("facts")): parts.append("可用事实：\n" + "\n".join("· " + s(x) for x in arr(f["facts"])))
    if arr(f.get("anchors")): parts.append("数字锚点：" + "；".join(arr(f["anchors"])))
    if arr(f.get("pitfalls")): parts.append("失败模式：" + "；".join(arr(f["pitfalls"])))
    return "\n".join(parts)

def tasks_for(dom, module, items, angles, facts_map, parts_override=None, siblings=None):
    tasks = []
    sibling = siblings if siblings is not None else [s(it.get("title") or it.get("name")) for it in items]
    for it in items:
        iid = s(it.get("id"))
        title = s(it.get("title") or it.get("name")) or s(it.get("question"))[:40]
        parts = parts_override or len(angles)
        for p, (angle_name, angle_text) in enumerate(angles[:parts], 1):
            avoid = "其他同类条目（不要重复它们的内容）：" + "；".join([x for x in sibling if x and x != title][:12])
            if p > 1:
                avoid += "\n本文前面已经写过的主题：" + "；".join(a[0] for a in angles[:p - 1])
            if module == "papers":
                facts = fmt_facts_card(it)
            else:
                facts = fmt_facts_generic(it, facts_map.get(iid, {}))
            tasks.append({
                "id": f"{module}-{iid}-p{p}", "module": module, "sub": module, "item_id": iid,
                "title": title, "part": p, "parts": parts,
                "angle": f"{angle_name}：{angle_text}", "target": 3600, "facts": facts,
                "avoid": avoid,
                "out": f"content/long/{dom}/{module}/{iid}-p{p}.html",
            })
    return tasks

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--domain", required=True)
    args = ap.parse_args(); dom = args.domain
    bpdir = os.path.join(ROOT, "content", "blueprint", dom)
    cdir = os.path.join(ROOT, "content", "cards", dom)
    sel = json.load(open(os.path.join(ROOT, "content", "selected.json"), encoding="utf-8")).get(dom, {})
    tasks = []
    # papers
    cards = []
    for f in sorted(os.listdir(cdir)):
        if f.endswith(".json"):
            cards.append(json.load(open(os.path.join(cdir, f), encoding="utf-8")))
    deep = set(sel.get("deep", []))
    paper_titles = [c.get("_title") or c.get("title") for c in cards]
    for c in cards:
        pid = c["_paper_id"]
        angles = PAPER_ANGLES_DEEP if pid in deep else PAPER_ANGLES_SHALLOW
        tasks += tasks_for(dom, "papers", [dict(c, id=pid, title=c.get("_title") or c.get("title"))],
                           angles, {}, siblings=paper_titles)
    # other modules
    spec = [("algorithms", "algorithms", ALGO_ANGLES), ("theory", "theory", THEORY_ANGLES),
            ("directions", "directions", DIR_ANGLES), ("stories", "stories", STORY_ANGLES),
            ("exams", "exams", EXAM_ANGLES), ("book", "book", BOOK_ANGLES),
            ("appendix", "appendix", APPENDIX_ANGLES)]
    for module, key, angles in spec:
        if module == "exams":
            # 题库以装配后的 assessments 为准：build_data 会补 auto 题（方向/经典/五层/补齐），
            # 只读蓝图会漏掉这些题，导致它们的 long_html 永远是空的。
            dp = os.path.join(ROOT, "site", "data", "domains", dom, "assessments.json")
            items = json.load(open(dp, encoding="utf-8")) if os.path.exists(dp) else []
            if not items:
                data = json.load(open(os.path.join(bpdir, module + ".json"), encoding="utf-8"))
                items = data.get(key, [])
        else:
            data = json.load(open(os.path.join(bpdir, module + ".json"), encoding="utf-8"))
            items = data.get("book", {}).get("sections", []) if module == "book" else data.get(key, [])
        fp = os.path.join(ROOT, "content", "facts", dom, module + ".json")
        facts = json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else {}
        tasks += tasks_for(dom, module, items, angles, facts)
    out = os.path.join(ROOT, "content", "tasks", dom + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(tasks, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(t["module"] for t in tasks)
    print(dom, "tasks", len(tasks), dict(c))

if __name__ == "__main__":
    main()
