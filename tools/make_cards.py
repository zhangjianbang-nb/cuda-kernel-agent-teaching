#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Complete per-paper cards (site fields + facts) for every catalog paper.

Input : content/papers-catalog.json, content/paper-pool.json, content/paper-meta.json
Output: content/cards/<domain>/<paper_id>.json
"""
import argparse, concurrent.futures, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import llm

META = json.load(open(os.path.join(HERE, "domain_meta.json"), encoding="utf-8"))
CAT = os.path.join(ROOT, "content", "papers-catalog.json")
POOL = os.path.join(ROOT, "content", "paper-pool.json")
LEGACY = os.path.join(ROOT, "content", "legacy-cards.json")
SEL = os.path.join(ROOT, "content", "selected.json")
OUT = os.path.join(ROOT, "content", "cards")

HEAD = """你是《CUDA Kernel Agent 工程全书》的论文卡整理员。本书只关心四条线：
- **评测**：基准、基线、输入分布、指标口径、防作弊；
- **生成/优化**：单轮提示、agent 脚手架、执行反馈、NCU/SASS profile、搜索/进化；
- **训练**：多轮 RL、可验证奖励、数据合成、轨迹 SFT；
- **验证/部署**：正确性 oracle、形式/合约验证、batch invariance、端到端收益、维护成本。
不写模型预训练配方、不写产品评测、不堆砌硬件参数。所有判断必须落到具体机制、数字口径或工程代价上。
领域：{name}（{focus}）
写作语言：简体中文。
"""

REQ = """
任务：为下面这篇论文整理一张"论文卡"，输出严格 JSON（不要任何解释、不要 markdown 围栏）。
硬约束：
1. 只使用给定材料；不得编造论文、作者、数字、年份、机构。材料里没有的数字写"未给出"。
2. 所有字段必须非空且达到字数下限；用中文全角标点。
3. 公式必须是 KaTeX display math（$$...$$ 包裹），不得用 Unicode 符号冒充。
4. pseudocode 用纯文本缩进 + 箭头，不要 markdown 围栏，不要 <pre>。
5. direction 必须从给定方向 id 列表里选一个；选不出就选最接近的。
6. facts 是给后续写作的"可用事实"，每条 60–120 字，必须具体（基准规模、基线、指标、搜索轮数、token 成本、失败模式），不许写"效果很好""非常重要"。
7. anchors 只收材料里真实出现的数字（如 250 题、7,384 个变异、19 亿 token、1.43×），没有就给 []。

JSON 结构：
{{"title_zh":"≤24字","background":"≥60字","problem":"≥30字","core_idea":"≥30字","architecture":"≥60字",
"pipeline":["4–6条，每条≥20字，按一次 kernel 生成—编译—运行—评测的流动顺序"],"formula":"$$...$$","training":"≥60字，写训练/优化配方（RL、SFT、搜索、奖励）","walkthrough":"≥120字，写一次完整的生成—反馈—验证流程","pseudocode":"≥60字",
"experiments":{{"datasets":["≥1"],"baselines":["≥1"],"results":"≥40字","limits":"≥40字","ablations":"≥30字"}},
"innovation":["3条，每条≥15字"],"limitations":["3条，每条≥15字"],"impact":"≥40字","summary":"≥80字",
"data_recipe":["3–5条，每条≥20字，写评测负载形态：模型/算子/shape/硬件/基线/输入分布"],"train_recipe":["3–5条，每条≥20字，写部署配方：工具链/profile 工具/编译环境/CI/上线门"],
"facts":["6–8条，每条60–120字，必须是评测机制、优化机制或工程代价"],"anchors":["..."],"pitfalls":["2–3条，每条≥20字"],"direction":"<方向id>"}}
"""

def norm(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

def pool_material(p):
    parts = []
    for k, lab in (("summary", "摘要/概述"), ("problem", "问题"), ("core_idea", "核心思想"),
                   ("training", "训练"), ("formula", "公式")):
        if p.get(k): parts.append(f"{lab}：{p[k]}")
    ex = p.get("experiments") or {}
    if isinstance(ex, dict):
        s = []
        if ex.get("datasets"): s.append("数据集：" + "、".join(ex["datasets"]))
        if ex.get("baselines"): s.append("基线：" + "、".join(ex["baselines"]))
        if ex.get("results"): s.append("结果：" + ex["results"])
        if ex.get("ablations"): s.append("消融：" + ex["ablations"])
        if ex.get("limits"): s.append("局限：" + ex["limits"])
        if s: parts.append("实验：\n" + "\n".join(s))
    return "\n".join(parts)

def abstract_material(p):
    return "arXiv 摘要（仅摘要级，未读全文）：\n" + (p.get("abstract") or "")

def build_prompt(dom, cat, pool, meta, dirs):
    title = cat["title"]
    lines = [HEAD.format(**META[dom])]
    lines.append(f"论文：{title}（{cat.get('year','')}，{cat.get('venue','') or 'venue 未给出'}）")
    if pool:
        lines.append("可核验材料（来自本项目已精读的论文卡）：\n" + pool_material(pool))
    else:
        lines.append(abstract_material(meta or {}))
    lines.append("可选方向 id：" + "、".join(dirs))
    lines.append(REQ)
    return "\n".join(lines)

def from_legacy(legacy, cat, dom):
    q = dict(legacy)
    facts = []
    for k, lab in (("background", "背景"), ("problem", "问题"), ("core_idea", "核心思想"),
                   ("architecture", "结构"), ("training", "训练"), ("formula", "公式"),
                   ("walkthrough", "训练流程"), ("impact", "影响")):
        if q.get(k): facts.append(f"{lab}：{q[k]}")
    ex = q.get("experiments") or {}
    if isinstance(ex, dict) and ex.get("results"): facts.append("结果：" + ex["results"])
    if isinstance(ex, dict) and ex.get("limits"): facts.append("局限：" + ex["limits"])
    if q.get("limitations"): facts.append("局限清单：" + "；".join(q["limitations"]))
    q["facts"] = facts
    q["anchors"] = []
    q["pitfalls"] = (q.get("limitations") or [])[:3]
    q["data_recipe"] = []
    q["train_recipe"] = []
    q["direction"] = ""
    q["_paper_id"] = cat["id"]; q["_domain"] = dom; q["_title"] = cat["title"]
    q["_abstract_only"] = q.get("read_level") in ("abstract_only", "api_verified", "unverified")
    q["_legacy"] = True
    return q

def gen_one(job):
    dom, cat, pool, meta, dirs, legacy = job
    pid = cat["id"]
    out = os.path.join(OUT, dom, pid + ".json")
    if os.path.exists(out):
        try:
            d = json.load(open(out, encoding="utf-8"))
            if d.get("facts") and len(d.get("facts", [])) >= 4: return ("skip", pid, len(d.get("facts", [])))
        except Exception:
            pass
    if legacy:
        d = from_legacy(legacy, cat, dom)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return ("legacy", pid, len(d.get("facts", [])))
    prompt = build_prompt(dom, cat, pool, meta, dirs)
    last = ""
    for attempt in range(3):
        try:
            txt, fin, usage = llm.call(prompt, max_tokens=8192, temperature=0.5, json_mode=True)
            d = llm.parse_json(txt)
            if len(d.get("facts", [])) < 4:
                raise ValueError("facts too few")
            d["_paper_id"] = pid; d["_domain"] = dom; d["_title"] = cat["title"]
            d["_abstract_only"] = not bool(pool)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return ("ok", pid, len(d.get("facts", [])))
        except Exception as e:
            last = str(e)[:160]
            prompt = build_prompt(dom, cat, pool, meta, dirs) + f"\n\n上一次输出不合格（{last}）。请只输出合法 JSON，facts 至少 6 条。"
            time.sleep(2 + attempt * 3)
    return ("fail", pid, last)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default=""); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    cat = json.load(open(CAT, encoding="utf-8"))
    pool = {norm(p["title"]): p for p in json.load(open(POOL, encoding="utf-8"))}
    legacy = {norm(p["title"]): p for p in json.load(open(LEGACY, encoding="utf-8")).values()} if os.path.exists(LEGACY) else {}
    sel = json.load(open(SEL, encoding="utf-8")) if os.path.exists(SEL) else {}
    meta = json.load(open(os.path.join(ROOT, "content", "paper-meta.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "content", "paper-meta.json")) else {}
    meta_by_title = {}
    for dom, ps in meta.items():
        for p in ps: meta_by_title[norm(p.get("query_title") or p.get("title"))] = p
    dirs_by_dom = {}
    for dom in META:
        bp = os.path.join(ROOT, "content", "blueprint", dom, "directions.json")
        if os.path.exists(bp):
            dirs_by_dom[dom] = [d["id"] for d in json.load(open(bp, encoding="utf-8")).get("directions", [])]
    jobs = []
    for c in cat:
        for dom in c.get("domains", []):
            if args.domain and dom != args.domain: continue
            if dom not in dirs_by_dom: continue
            if sel.get(dom) and c["id"] not in sel[dom].get("deep", []) + sel[dom].get("shallow", []): continue
            jobs.append((dom, c, pool.get(norm(c["title"])), meta_by_title.get(norm(c["title"])), dirs_by_dom[dom], legacy.get(norm(c["title"]))))
    if args.limit: jobs = jobs[:args.limit]
    print(f"jobs={len(jobs)} workers={args.workers}", flush=True)
    ok = fail = skip = 0; t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(gen_one, j): j for j in jobs}
        for fut in concurrent.futures.as_completed(futs):
            st, pid, info = fut.result()
            if st in ("ok", "legacy"): ok += 1
            elif st == "fail": fail += 1
            else: skip += 1
            el = time.time() - t0
            print(f"[{ok+fail+skip}/{len(jobs)}] {st} {pid} {info} {el/60:.1f}m", flush=True)
    print(f"DONE ok={ok} fail={fail} skip={skip} elapsed={(time.time()-t0)/60:.1f}m", flush=True)

if __name__ == "__main__":
    main()
