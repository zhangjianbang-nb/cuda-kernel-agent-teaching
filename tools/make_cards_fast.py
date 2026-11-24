#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast abstract-based cards for papers that the slow card generator did not reach.

The long-form generator only needs concrete facts; these cards keep the paper
detail page honest ("abstract only") while avoiding a multi-hour card pass.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "content", "papers-catalog.json")
OUT = os.path.join(ROOT, "content", "cards", "cuda")

DIRS = [
    ("dir-bench-trust", ["benchmark", "bench", "evaluation", "score", "kernels", "suite", "measure"]),
    ("dir-agent-harness", ["agent", "harness", "feedback", "search", "evolution", "multi-agent", "profile"]),
    ("dir-rl-data", ["reinforcement", "rl", "reward", "policy", "training", "dataset", "sft", "fine-tun"]),
    ("dir-oracle-formal", ["correct", "oracle", "verif", "invariance", "mutation", "fuzz", "contract", "audit"]),
    ("dir-prod-e2e", ["production", "deploy", "end-to-end", "serving", "workload", "real"]),
    ("dir-hw-dsl-profile", ["triton", "cute", "ptx", "cuda", "sass", "ncu", "roofline", "speed-of-light", "tma", "tensor core"]),
]


def sentences(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 25:
            out.append(p)
    return out


def pick_direction(text):
    low = text.lower()
    best, score = DIRS[0][0], -1
    for did, kws in DIRS:
        sc = sum(low.count(k) for k in kws)
        if sc > score:
            best, score = did, sc
    return best


def formula_for(did):
    return {
        "dir-bench-trust": "$$\\text{score}=\\frac{1}{N}\\sum_{i=1}^{N}\\mathbb{1}[s_i\\ge\\tau],\\qquad s_i=\\frac{T_{\\text{base},i}}{T_{\\text{cand},i}}$$",
        "dir-agent-harness": "$$\\text{speedup}=\\frac{T_{\\text{base}}}{T_{\\text{agent}}},\\qquad \\text{accept}=\\mathbb{1}[\\text{pass}\\land s\\ge 1]$$",
        "dir-rl-data": "$$R=\\sum_{t=0}^{T}\\gamma^{t}r_{t},\\qquad r_t=\\Delta\\text{speed}_t\\cdot\\mathbb{1}[\\text{pass}_t]$$",
        "dir-oracle-formal": "$$\\text{FRR}=\\frac{\\#\\{\\text{correct}\\to\\text{reject}\\}}{\\#\\{\\text{correct}\\}},\\qquad \\text{FAR}=\\frac{\\#\\{\\text{wrong}\\to\\text{accept}\\}}{\\#\\{\\text{wrong}\\}}$$",
        "dir-prod-e2e": "$$S_{\\text{e2e}}=\\frac{1}{(1-p)+p/s}\\xrightarrow{s\\to\\infty}\\frac{1}{1-p},\\qquad p=\\frac{T_{\\text{kernel}}}{T_{\\text{total}}}$$",
        "dir-hw-dsl-profile": "$$P_{\\text{att}}(I)=\\min\\left(P_{\\text{peak}},\\;I\\cdot B_{\\text{eff}}\\right),\\qquad I=\\frac{\\text{FLOP}}{\\text{Byte}}$$",
    }[did]


def anchors(text):
    pats = re.findall(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(?:×|x|%|倍|题|个|篇|token|s|ms|GB|MB|条|次|种)", text)
    return list(dict.fromkeys(pats))[:12]


def build_card(p, direction_name):
    title = p["title"]
    abstract = p.get("summary") or ""
    sents = sentences(abstract)
    while len(sents) < 6:
        sents.append(f"论文《{title}》的摘要未展开该点，需读全文核验。")
    did = pick_direction(title + " " + abstract)
    # 摘要句按主题分配给各字段，避免所有字段都复述第一句。
    def seg(a, b):
        return " ".join(sents[a:b]) if sents[a:b] else sents[0]
    facts = []
    for s in sents[:10]:
        if len(s) >= 60:
            facts.append(s[:220])
        else:
            facts.append((s + " " + (sents[sents.index(s) + 1] if sents.index(s) + 1 < len(sents) else ""))[:220])
    facts = facts[:8]
    pipeline = [
        f"读取《{title}》定义的输入、参考实现与评测口径",
        f"按论文方法生成或搜索候选 kernel（{seg(1, 2)[:60]}）",
        "编译候选并在论文给定的输入分布上做正确性检查",
        "用统一基线测量时延、加速比与资源占用",
        "按反馈筛选或改写候选，输出可复现的最优结果",
    ]
    return {
        "_paper_id": p["id"], "_domain": "cuda", "_title": title, "_abstract_only": True,
        "title_zh": title[:60],
        "background": f"这篇论文发表于 {p.get('year', '')} 年（arXiv:{p.get('arxiv', '')}），属于 {direction_name} 方向。它要回答的问题是：{seg(0, 1)[:180]}",
        "problem": seg(0, 2)[:260],
        "core_idea": seg(1, 3)[:260],
        "architecture": seg(2, 4)[:300],
        "pipeline": pipeline,
        "formula": formula_for(did),
        "training": f"论文给出的优化/训练配方：{seg(3, 5)[:260]}",
        "walkthrough": f"一次完整流程：先读取《{title}》的参考实现与基准口径；再按论文方法生成候选；编译后在给定输入上做正确性检查；用统一基线测量时延与加速比；最后按反馈保留或回退候选。论文摘要强调：{seg(2, 4)[:220]}",
        "pseudocode": "读取参考实现 到 生成候选 到 编译 到 正确性检查 到 profile 到 保留/回退",
        "experiments": {
            "datasets": [f"《{title}》使用的基准/算子集合（摘要级，详见论文）"],
            "baselines": ["PyTorch eager / torch.compile / 论文指定的库实现"],
            "results": seg(4, 6)[:300],
            "limits": "仅摘要级，未读全文；具体实验细节与消融未核验",
            "ablations": "摘要未给出完整消融",
        },
        "innovation": [s[:160] for s in sents[:3]],
        "limitations": [
            f"《{title}》的结论只在论文给定的硬件、基线与输入分布上成立",
            "仅摘要级，未读全文；数字为论文声称，未独立复现",
            "跨硬件、跨 dtype、跨框架迁移未验证",
        ],
        "impact": seg(3, 5)[:220],
        "summary": abstract[:400],
        "data_recipe": [
            f"评测负载：《{title}》的基准题/算子集合",
            "基线：PyTorch eager、torch.compile 与论文指定库",
            "输入分布：按论文口径（摘要未给出全部 shape）",
            "指标：正确率、加速比、资源占用（按论文口径）",
        ],
        "train_recipe": [
            "工具链：按论文（CUDA / Triton / CuTe / PTX）",
            "反馈：编译、运行与 profile 结果回灌",
            "验证：正确性门 + 性能门",
            "部署：先在离线基准复现，再做端到端回归",
        ],
        "facts": facts,
        "anchors": anchors(abstract),
        "pitfalls": [
            f"《{title}》的基线若未开 TF32/未用最强库，加速比会被高估",
            "shape 特化与隐藏输入分布会让离线分数在生产上崩塌",
            "reward hacking / fallback 会让正确率虚高",
        ],
        "direction": did,
    }


def main():
    cat = json.load(open(CAT, encoding="utf-8"))
    dirs = {d["id"]: d["name"] for d in json.load(open(os.path.join(ROOT, "content", "blueprint", "cuda", "directions.json"), encoding="utf-8"))["directions"]}
    os.makedirs(OUT, exist_ok=True)
    made = skipped = 0
    for p in cat:
        path = os.path.join(OUT, p["id"] + ".json")
        if os.path.exists(path):
            try:
                d = json.load(open(path, encoding="utf-8"))
                if len(d.get("facts") or []) >= 4:
                    skipped += 1
                    continue
            except Exception:
                pass
        card = build_card(p, dirs.get(pick_direction(p["title"] + " " + (p.get("summary") or "")), "CUDA kernel agent"))
        json.dump(card, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        made += 1
    print(f"fast cards: made={made} skipped_existing={skipped} total={len(cat)}")


if __name__ == "__main__":
    main()
