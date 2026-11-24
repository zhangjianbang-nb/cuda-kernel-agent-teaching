#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build papers-catalog.json + selected.json for the CUDA kernel agent site.

Input : the survey project's raw/arxiv_hits.json and raw/abstracts.json
Output: content/papers-catalog.json, content/selected.json
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SURVEY = "/home/whu/workspace/ai_workspace/cuda-kernel-agent-survey-20261122"

DEEP = [
    "2502.10517", "2507.11948", "2507.14111", "2507.23194", "2511.01884",
    "2512.02551", "2602.05885", "2602.24286", "2603.21331", "2603.29010",
    "2604.01489", "2605.04956", "2605.16819", "2605.23215", "2607.24762",
    "2606.20128", "2606.26453", "2607.16241", "2607.14541", "2609.22220",
    "2609.21058", "2609.30059", "2610.36623", "2610.36434", "2611.04331",
    "2611.15506", "2608.02611", "2611.03517", "2510.03760", "2512.16465",
    "2603.19173", "2602.11000",
]
SHALLOW = [
    "2506.09092", "2509.07506", "2603.07169", "2603.10085", "2603.12440",
    "2608.14560", "2608.01804", "2608.12004", "2608.17071", "2608.17379",
    "2608.21836", "2609.29067", "2609.33074", "2610.03226", "2610.05014",
    "2607.20908", "2611.14604", "2605.26720",
]

FALLBACK_TITLES = {
    "2502.10517": "KernelBench: Can LLMs Write Efficient GPU Kernels?",
    "2506.09092": "CUDA-LLM: LLMs Can Write Efficient CUDA Kernels",
    "2507.11948": "Kevin: Multi-Turn RL for Generating CUDA Kernels",
    "2507.14111": "CUDA-L1: Improving CUDA Optimization via Contrastive RL",
    "2507.23194": "GEAK: Introducing Triton Kernel AI Agent & Evaluation Benchmarks",
    "2509.07506": "Astra: A Multi-Agent System for GPU Kernel Performance Optimization",
    "2510.03760": "EvoEngineer: Mastering Automated CUDA Kernel Code Evolution",
    "2511.01884": "CudaForge: An Agent Framework with Hardware Feedback",
    "2512.02551": "CUDA-L2: Surpassing cuBLAS Performance for Matmul through RL",
    "2512.16465": "cuPilot: A Strategy-Coordinated Multi-agent Framework",
    "2602.05885": "Dr. Kernel: RL Done Right for Triton Kernel Generations",
    "2602.11000": "Fine-Tuning GPT-5 for GPU Kernel Generation",
    "2602.24286": "CUDA Agent: Large-Scale Agentic RL",
    "2603.07169": "Making LLMs Optimize Multi-Scenario CUDA Kernels Like Experts",
    "2603.10085": "KernelClaw: Multi-Agent Framework with Dual-Memory",
    "2603.12440": "KernelFoundry: Hardware-aware evolutionary GPU kernel optimization",
    "2603.19173": "SOL-ExecBench: Speed-of-Light Benchmarking",
    "2603.21331": "AutoKernel: Autonomous GPU Kernel Optimization",
    "2603.29010": "DSL and Speed-of-Light Guidance for Kernel Optimization Agents",
    "2604.01489": "CuTeGen: LLM-Based Agentic Framework using CuTe",
    "2605.04956": "KernelBenchX: Comprehensive Benchmark",
    "2605.16819": "AgentKernelArena: Generalization-Aware Benchmarking",
    "2605.23215": "FastKernels: Benchmarking GPU Kernel Generation in Production",
    "2608.14560": "Agentic Kernel Optimization: State-of-the-Art without Hand-Written CUDA",
    "2607.24762": "Kernel Forge: An Agent Harness",
    "2606.20128": "The Correctness Illusion in LLM-Generated GPU Kernels",
    "2606.26453": "Optimizing CUDA like a Human: Micro-Profiling Tools",
    "2607.16241": "KernelBench-Verified: Do LLM-Generated Kernels Actually Beat PyTorch?",
    "2607.14541": "Are LLM-Generated GPU Kernels Production-Ready? (Atrex-Bench)",
    "2607.20908": "Multi-turn RL with Structural and Performance Aware Rewards",
    "2608.01804": "LEAP: Lean Environment-Feedback via Adaptive Pruning",
    "2608.12004": "RealisticTritonBench",
    "2608.17071": "KernelArc: A Multi-Agent Framework",
    "2608.17379": "PTXBench: Architecture-specific PTX",
    "2608.21836": "LLM4LLM: Bridging Kernel Benchmarks and Real Deployment",
    "2609.22220": "Measuring the Checker: Mutation Analysis for GPU-Kernel Oracles",
    "2609.21058": "How Much of a Real Workload Can LLM-Generated Kernels Reach?",
    "2609.29067": "TileBench: Controlled Benchmark for Tile-Based Models",
    "2609.30059": "KernelOPT: Dispatch-Aware Agentic Search",
    "2609.33074": "KernelZero: Co-Evolving Proposer and Coder",
    "2610.03226": "D2K-Bench: Expert Designs to Efficient GPU Kernels",
    "2610.05014": "MetaKernelBench: GPU Kernel Knowledge Transfer",
    "2610.36434": "JustGoal: With Only a Goal, the AI Baseline Is Above the Expert Kernels",
    "2610.36623": "God Does Not Play Dice: Enforcing Batch Invariance",
    "2611.03517": "Ask, Don't Equip: Question-Driven Coding Agents",
    "2611.04331": "Warpline: Binary-Level Tracing for Agentic Kernel Optimization",
    "2611.14604": "KernelMosaic: Open Dataset and Agentic Framework",
    "2611.15506": "KernelAudit: Contract-Aware Auditing of Validators",
    "2605.26720": "CUDAnalyst",
}


def base_id(s):
    return re.split(r"v\d+$", s)[0]


def main():
    hits = json.load(open(os.path.join(SURVEY, "raw/arxiv_hits.json"), encoding="utf-8"))
    abstracts = json.load(open(os.path.join(SURVEY, "raw/abstracts.json"), encoding="utf-8"))
    by_id = {}
    for e in hits + abstracts:
        by_id.setdefault(base_id(e["id"]), e)
    cat = []
    selected = {"cuda": {"deep": [], "shallow": []}}
    for group, ids in (("deep", DEEP), ("shallow", SHALLOW)):
        for aid in ids:
            e = by_id.get(aid, {})
            pid = "paper-" + aid.replace(".", "-")
            title = e.get("title") or FALLBACK_TITLES.get(aid) or aid
            year = int((e.get("published") or "2025-01-01")[:4])
            cat.append({
                "id": pid,
                "title": title,
                "title_zh": "",
                "year": year,
                "venue": "",
                "authors": e.get("authors") or ["未给出"],
                "links": {"paper": "https://arxiv.org/abs/" + aid, "code": ""},
                "arxiv": aid,
                "domains": ["cuda"],
                "summary": e.get("summary") or "",
                "problem": "",
                "core_idea": "",
                "training": "",
                "experiments": "",
                "formula": "",
                "read_level": "abstract_only",
                "source": "survey:arxiv",
            })
            selected["cuda"][group].append(pid)
    os.makedirs(os.path.join(ROOT, "content"), exist_ok=True)
    json.dump(cat, open(os.path.join(ROOT, "content/papers-catalog.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(selected, open(os.path.join(ROOT, "content/selected.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for name, val in (("paper-pool.json", []), ("paper-meta.json", {})):
        p = os.path.join(ROOT, "content", name)
        if not os.path.exists(p):
            json.dump(val, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print("catalog", len(cat), "deep", len(DEEP), "shallow", len(SHALLOW))


if __name__ == "__main__":
    main()
