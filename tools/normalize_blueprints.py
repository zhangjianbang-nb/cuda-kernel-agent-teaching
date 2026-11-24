#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize blueprint direction ids and replace duplicated theory cards."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "content", "blueprint", "cuda")

CANON = ["dir-bench-trust", "dir-agent-harness", "dir-rl-data",
         "dir-oracle-formal", "dir-prod-e2e", "dir-hw-dsl-profile"]

ALG_MAP = {
    "dir-trustworthy-baseline": "dir-bench-trust",
    "dir-correctness-oracle": "dir-oracle-formal",
    "dir-execution-feedback": "dir-agent-harness",
    "dir-search": "dir-agent-harness",
    "dir-agent-scaffold": "dir-agent-harness",
    "dir-rl": "dir-rl-data",
    "dir-data": "dir-rl-data",
    "dir-eval": "dir-prod-e2e",
}
# 硬件反馈/DSL 类方法归到 profile 方向，避免该方向没有算法卡。
ALG_OVERRIDE = {
    "alg-ncu-metric-feedback": "dir-hw-dsl-profile",
    "alg-sass-warp-stall-profile": "dir-hw-dsl-profile",
    "alg-binary-instr-tracing": "dir-hw-dsl-profile",
    "alg-cute-agent-gen": "dir-hw-dsl-profile",
    "alg-strategy-ir-dsl": "dir-hw-dsl-profile",
}

TH_MAP = {
    "perf-model": "dir-hw-dsl-profile",
    "benchmark": "dir-bench-trust",
    "profiling": "dir-hw-dsl-profile",
    "correctness": "dir-oracle-formal",
    "benchmark-eval": "dir-bench-trust",
    "kernel-perf": "dir-hw-dsl-profile",
    "deployment": "dir-prod-e2e",
}

NEW_THEORY = [
    {
        "id": "th-reward-hacking", "title": "奖励黑客的激励不相容",
        "direction": "dir-rl-data",
        "plain": "当奖励只看加速比、不检查是否真的实现了目标算子时，复制 torch、恒等映射、fallback 或计时作弊就能拿高分；奖励设计必须让作弊的期望收益低于真做。",
        "formula": "$$R_{\\text{true}}=\\begin{cases}r_{\\text{speed}},&\\text{pass}_{\\text{oracle}}\\land\\neg\\text{fallback}\\land\\neg\\text{identity}\\\\-1,&\\text{otherwise}\\end{cases}$$",
        "limits": ["oracle 本身漏检时，pass 门形同虚设", "fallback 检测只能覆盖已知模式，新作弊路径仍可绕过", "奖励尺度随硬件与基线漂移，跨环境不可直接复用"],
        "variables": [{"sym": "R", "meaning": "实际发放的奖励"}, {"sym": "r_speed", "meaning": "按加速比归一化的原始奖励"}, {"sym": "pass", "meaning": "oracle 是否正确性通过"}, {"sym": "fallback", "meaning": "是否退化为调用 PyTorch/库"}, {"sym": "identity", "meaning": "是否用恒等映射等退化实现"}],
        "prereq": [],
    },
    {
        "id": "th-multiturn-credit", "title": "多轮信用分配",
        "direction": "dir-rl-data",
        "plain": "多轮 agent 的最终加速比由每一轮编辑共同决定；若只给最后一轮奖励，前面「修对但没提速」的轮次拿不到信号，策略会退化成保守复制。",
        "formula": "$$R_t=\\sum_{k=t}^{T}\\gamma^{k-t}r_k,\\qquad r_k=\\Delta\\text{speed}_k\\cdot\\mathbb{1}[\\text{pass}_k]$$",
        "limits": ["折扣因子过小只看短期，过大会放大远端噪声", "轮数 T 很大时方差累积，需要 baseline 或 TRLOO 降方差", "中间轮 pass 变化不等于最终 pass，奖励可能误判"],
        "variables": [{"sym": "R_t", "meaning": "第 t 轮拿到的聚合奖励"}, {"sym": "γ", "meaning": "折扣因子"}, {"sym": "r_k", "meaning": "第 k 轮的即时奖励"}, {"sym": "Δspeed", "meaning": "该轮相对上一轮的加速变化"}, {"sym": "pass", "meaning": "该轮是否通过正确性门"}],
        "prereq": [],
    },
    {
        "id": "th-transfer-gain", "title": "跨域迁移增益界",
        "direction": "dir-bench-trust",
        "plain": "在源任务上学到的 kernel 知识迁到目标任务，增益不是单调的；MetaKernelBench 实测双向迁移为 −19%~+29%，且每个模型/方向仍有 16%–45% 的题退化。",
        "formula": "$$G_{\\text{transfer}}=\\frac{s_{\\text{target}}^{\\text{after}}-s_{\\text{target}}^{\\text{before}}}{s_{\\text{target}}^{\\text{before}}},\\qquad G\\in[-1,+\\infty)$$",
        "limits": ["源/目标任务分布差异大时增益为负", "硬件或 dtype 变化会破坏迁移，需要重新验证", "样本量小时置信区间很宽，不能只看均值"],
        "variables": [{"sym": "G", "meaning": "迁移带来的相对增益"}, {"sym": "s_after", "meaning": "迁移后的目标任务得分"}, {"sym": "s_before", "meaning": "迁移前的目标任务得分"}],
        "prereq": [],
    },
    {
        "id": "th-energy-pareto", "title": "能耗-性能帕累托",
        "direction": "dir-hw-dsl-profile",
        "plain": "更快的 kernel 不一定更省电；功耗随 occupancy、频率与访存模式变化，存在「提速但能耗更高」的帕累托前沿。",
        "formula": "$$E=\\int_0^T P(t)\\,dt\\approx\\bar P\\cdot T,\\qquad \\text{Pareto}:\\ \\min\\ (\\text{latency},E)$$",
        "limits": ["瞬时功耗采样成本高，常用平均功耗近似", "DVFS 与温度会让同一 kernel 的能耗漂移", "不同硬件的能效曲线不可直接比较"],
        "variables": [{"sym": "E", "meaning": "一次执行的总能耗"}, {"sym": "P", "meaning": "瞬时功率"}, {"sym": "T", "meaning": "执行时间"}],
        "prereq": [],
    },
    {
        "id": "th-memory-peak", "title": "峰值内存约束",
        "direction": "dir-prod-e2e",
        "plain": "生成的 kernel 可能用更大的中间缓冲换速度；KernelBench-Verified 发现 28% 的核增加峰值内存，生产上会挤压 KV cache 与并发预算。",
        "formula": "$$M_{\\text{peak}}=M_{\\text{in}}+M_{\\text{out}}+\\max_{\\text{stage}}M_{\\text{tmp}}(\\text{stage})\\le M_{\\text{budget}}$$",
        "limits": ["峰值依赖 shape 与 batch，单 shape 测量会低估", "allocator 缓存会掩盖真实峰值，需重置统计", "多流并发时各流峰值叠加，不能只看单流"],
        "variables": [{"sym": "M_peak", "meaning": "执行期间的峰值显存"}, {"sym": "M_in/M_out", "meaning": "输入/输出张量占用"}, {"sym": "M_tmp", "meaning": "各阶段临时缓冲"}, {"sym": "M_budget", "meaning": "线上显存预算"}],
        "prereq": [],
    },
    {
        "id": "th-search-budget", "title": "搜索预算的收益递减",
        "direction": "dir-agent-harness",
        "plain": "采样/搜索轮数增加带来的 best-of-n 提升服从幂律或对数收益；超过某个预算后，边际收益低于 GPU 成本，继续加轮数不划算。",
        "formula": "$$\\mathbb{E}\\left[\\max_{i\\le n}s_i\\right]\\approx s_\\infty-c\\,n^{-\\alpha},\\qquad \\text{marginal}=\\frac{\\partial}{\\partial n}\\mathbb{E}\\left[\\max_{i\\le n}s_i\\right]$$",
        "limits": ["任务难度分布不均匀，单一幂律拟合不够", "采样之间相关，独立同分布假设失效", "best-of-n 会放大 reward hacking，分数越高越要审计"],
        "variables": [{"sym": "n", "meaning": "采样/搜索轮数"}, {"sym": "s_inf", "meaning": "预算无穷大时的渐近得分"}, {"sym": "c,α", "meaning": "拟合常数与衰减指数"}],
        "prereq": [],
    },
    {
        "id": "th-verifier-false-reject", "title": "验证器误拒率",
        "direction": "dir-oracle-formal",
        "plain": "验证器把正确 kernel 判错（false reject）会浪费搜索预算并误导 agent；KernelAudit 发现 6 个 validator 存在不可忽视的 false-reject。",
        "formula": "$$\\text{FRR}=\\frac{\\#\\{\\text{correct}\\to\\text{reject}\\}}{\\#\\{\\text{correct}\\}},\\qquad \\text{FAR}=\\frac{\\#\\{\\text{wrong}\\to\\text{accept}\\}}{\\#\\{\\text{wrong}\\}}$$",
        "limits": ["正确性标签本身依赖参考实现，参考错则 FRR/FAR 都失真", "容差选择会同时改变 FRR 与 FAR", "对抗样本可以同时推高两种错误率"],
        "variables": [{"sym": "FRR", "meaning": "正确实现被误拒的比例"}, {"sym": "FAR", "meaning": "错误实现被误放的比例"}],
        "prereq": [],
    },
]


def main():
    ap = os.path.join(BP, "algorithms.json")
    data = json.load(open(ap, encoding="utf-8"))
    for a in data["algorithms"]:
        a["direction"] = ALG_OVERRIDE.get(a.get("id"), ALG_MAP.get(a.get("direction"), a.get("direction")))
        if a["direction"] not in CANON:
            a["direction"] = "dir-agent-harness"
    json.dump(data, open(ap, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    tp = os.path.join(BP, "theory.json")
    data = json.load(open(tp, encoding="utf-8"))
    keep = data["theory"][:8]
    for t in keep:
        t["direction"] = TH_MAP.get(t.get("direction"), t.get("direction"))
        if t["direction"] not in CANON:
            t["direction"] = "dir-hw-dsl-profile"
    data["theory"] = keep + NEW_THEORY
    json.dump(data, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for name, key in (("directions", "directions"), ("algorithms", "algorithms"), ("theory", "theory")):
        d = json.load(open(os.path.join(BP, name + ".json"), encoding="utf-8"))
        ids = [x.get("id") for x in d[key]]
        print(name, len(ids), "ids ok" if len(ids) == len(set(ids)) else "DUPLICATE IDS")
    alg = json.load(open(ap, encoding="utf-8"))["algorithms"]
    th = json.load(open(tp, encoding="utf-8"))["theory"]
    print("alg directions:", sorted({x["direction"] for x in alg}))
    print("theory directions:", sorted({x["direction"] for x in th}))


if __name__ == "__main__":
    main()
