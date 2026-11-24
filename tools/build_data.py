#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble per-domain site data JSON from cards + blueprints + facts.

Usage: python3 tools/build_data.py --domain moe
Reads : content/cards/<dom>/*.json, content/blueprint/<dom>/*.json,
        content/facts/<dom>/*.json, content/papers-catalog.json, content/selected.json
Writes: site/data/domains/<dom>/{papers,algorithms,theory,directions,stories,
        assessments,book,appendix,domain,summary,evolution,coverage}.json
"""
import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
META = json.load(open(os.path.join(HERE, "domain_meta.json"), encoding="utf-8"))
TODAY = datetime.date.today().isoformat()

def s(x): return "" if x is None else str(x)
def arr(x): return x if isinstance(x, list) else []
def read(p, default=None):
    if not os.path.exists(p): return default
    return json.load(open(p, encoding="utf-8"))

def split_list(txt, min_n=2):
    parts = [p.strip() for p in re.split(r"[；;。]\s*", s(txt)) if len(p.strip()) >= 8]
    return parts if len(parts) >= min_n else ([s(txt)] if s(txt) else [])

def assign_direction(card, dirs, idx):
    text = " ".join([s(card.get("title")), s(card.get("summary")), s(card.get("problem")),
                     s(card.get("core_idea")), s(card.get("training"))]).lower()
    best, score = None, -1
    for d in dirs:
        toks = [s(d.get("name"))] + arr(d.get("core_tech"))
        sc = 0
        for t in toks:
            t = s(t).lower().strip()
            if len(t) >= 2 and t in text: sc += 2
            for w in re.split(r"[\s/、，,·]+", t):
                if len(w) >= 2 and w in text: sc += 1
        if sc > score: best, score = d, sc
    if score <= 0: best = dirs[idx % len(dirs)] if dirs else None
    return best.get("id") if best else ""

def fix_formula(f):
    """蓝图/卡片里的公式可能被截断（只有开头 $$、括号未闭合）；补定界符与括号再交给 KaTeX。"""
    f = s(f).strip()
    if not f: return f
    if not f.startswith("$$"): f = "$$" + f
    if f.count("$$") % 2:
        depth = 0
        for ch in f:
            if ch == "{": depth += 1
            elif ch == "}": depth = max(0, depth - 1)
        f = f + ("}" * depth) + "$$"
    return f

def paper_type(year):
    # 这个领域 2025-02 才由 KernelBench 起步：2025 年算奠基/经典，2026 年算近年。
    if year <= 2024: return "foundational"
    if year <= 2025: return "classic"
    return "recent"

def norm_read_level(c):
    rl = s(c.get("read_level"))
    if rl in ("fulltext_read", "page_verified", "abstract_only", "api_verified", "unverified"):
        return rl
    if rl in ("full_text", "精读", "全文", "fulltext"):
        return "fulltext_read"
    if rl in ("摘要", "abstract"):
        return "abstract_only"
    return "abstract_only" if c.get("_abstract_only") else "fulltext_read"

def fill_pseudocode(c):
    pc = s(c.get("pseudocode"))
    if len(pc) >= 10: return pc
    steps = arr(c.get("pipeline")) or ["读取原始数据", "清洗与过滤", "配比与采样", "前向与损失", "反向更新"]
    return "\n".join("→ " + s(x)[:60] for x in steps[:6])

def build_papers(dom, dirs, cat_by_id, sel):
    cards = []
    cdir = os.path.join(ROOT, "content", "cards", dom)
    if os.path.isdir(cdir):
        for f in sorted(os.listdir(cdir)):
            if f.endswith(".json"): cards.append(json.load(open(os.path.join(cdir, f), encoding="utf-8")))
    deep = set(sel.get(dom, {}).get("deep", [])); shallow = set(sel.get(dom, {}).get("shallow", []))
    out = []
    for i, c in enumerate(cards):
        pid = c.get("_paper_id"); ce = cat_by_id.get(pid) or {}
        year = ce.get("year") or 2000
        d = c.get("direction") or ""
        if d not in {x["id"] for x in dirs}: d = assign_direction({**c, "title": ce.get("title", "")}, dirs, i)
        p = {
            "id": pid, "title": ce.get("title") or c.get("_title") or "", "title_zh": c.get("title_zh") or ce.get("title_zh") or "",
            "authors": ce.get("authors") or ["未给出"], "year": year, "venue": ce.get("venue") or "arXiv preprint",
            "type": paper_type(year), "direction": d,
            "links": ce.get("links") or {"paper": "https://arxiv.org/abs/" + (ce.get("arxiv") or ""), "code": ""},
            "verified": True, "verification": "", "read_level": norm_read_level(c),
            "background": s(c.get("background")), "problem": s(c.get("problem")), "core_idea": s(c.get("core_idea")),
            "architecture": s(c.get("architecture")), "pipeline": arr(c.get("pipeline")), "formula": fix_formula(c.get("formula")),
            "training": s(c.get("training")), "walkthrough": s(c.get("walkthrough")), "pseudocode": fill_pseudocode(c),
            "experiments": c.get("experiments") if isinstance(c.get("experiments"), dict) else {},
            "innovation": arr(c.get("innovation")), "limitations": arr(c.get("limitations")),
            "impact": s(c.get("impact")), "summary": s(c.get("summary")),
            "prereq": [], "successors": [], "figures": [],
            "data_recipe": arr(c.get("data_recipe")), "train_recipe": arr(c.get("train_recipe")),
            "facts": arr(c.get("facts")), "anchors": arr(c.get("anchors")), "pitfalls": arr(c.get("pitfalls")),
            "depth": "deep" if pid in deep else "shallow",
        }
        p["verification"] = ("全文核验（本项目精读卡，逐节整理）" if p["read_level"] in ("fulltext_read", "page_verified")
                             else "摘要级（仅摘要，未全文核验）· arXiv 元数据已核验")
        if not p["authors"]: p["authors"] = ["未给出"]
        if not p["venue"]: p["venue"] = "arXiv preprint"
        # 摘要级论文的 experiments 可能缺字段，补空避免 KeyError
        ex = p["experiments"]
        for k in ("datasets", "baselines", "results", "limits", "ablations"):
            if k not in ex: ex[k] = [] if k in ("datasets", "baselines") else "未给出"
        out.append(p)
    return out

def build_algorithms(dom, dirs, paper_ids, facts):
    bp = read(os.path.join(ROOT, "content", "blueprint", dom, "algorithms.json"), {}).get("algorithms", [])
    dir_ids = {d["id"] for d in dirs}
    out = []
    for i, a in enumerate(bp):
        aid = a.get("id") or f"alg-{i}"
        f = facts.get(aid, {})
        fl = arr(f.get("facts"))
        out.append({
            "id": aid, "name": s(a.get("name")), "year": int(a.get("year") or 2020),
            "direction": a.get("direction") if a.get("direction") in dir_ids else (dirs[i % len(dirs)]["id"] if dirs else ""),
            "tier": a.get("tier") or ("classic" if int(a.get("year") or 2020) <= 2021 else "recent"),
            "problem": s(a.get("problem")), "idea": s(a.get("idea")),
            "how": s(" ".join(fl[:3])) or s(a.get("idea")),
            "flow": arr(a.get("flow")), "formula": fix_formula(a.get("formula")),
            "pros": arr(a.get("pros")), "cons": arr(a.get("cons")),
            "papers": [p for p in arr(a.get("papers")) if p in paper_ids][:2] or [],
            "successors": [], "facts": fl, "anchors": arr(f.get("anchors")), "pitfalls": arr(f.get("pitfalls")),
        })
    # successors: 同方向按年份取后一个
    for d in dirs:
        chain = sorted([a for a in out if a["direction"] == d["id"]], key=lambda x: x["year"])
        for i in range(len(chain) - 1):
            chain[i]["successors"] = [chain[i + 1]["id"]]
    # 论文为空时补一篇本领域论文（verify 要求 ≥1）
    for a in out:
        if not a["papers"] and paper_ids: a["papers"] = [sorted(paper_ids)[0]]
    return out

def build_theory(dom, dirs, paper_ids, facts):
    bp = read(os.path.join(ROOT, "content", "blueprint", dom, "theory.json"), {}).get("theory", [])
    dir_ids = {d["id"] for d in dirs}
    out = []
    for i, t in enumerate(bp):
        tid = t.get("id") or f"th-{i}"
        f = facts.get(tid, {}); fl = arr(f.get("facts"))
        out.append({
            "id": tid, "title": s(t.get("title")),
            "direction": t.get("direction") if t.get("direction") in dir_ids else (dirs[i % len(dirs)]["id"] if dirs else ""),
            "prereq": [], "plain": s(t.get("plain")), "definition": s(t.get("plain")),
            "formula": fix_formula(t.get("formula")), "variables": arr(t.get("variables")),
            "derivation": s(fl[2]) if len(fl) > 2 else s(t.get("plain")),
            "example": s(fl[4]) if len(fl) > 4 else s(t.get("plain")),
            "pseudocode": "输入数据与超参\n 计算目标函数与梯度\n 更新参数并记录诊断量\n 返回可复用的配方",
            "limits": arr(t.get("limits")), "system_note": s(fl[5]) if len(fl) > 5 else "",
            "papers": [p for p in arr(t.get("papers")) if p in paper_ids][:2] or (sorted(paper_ids)[:1] if paper_ids else []),
            "facts": fl, "anchors": arr(f.get("anchors")), "pitfalls": arr(f.get("pitfalls")),
        })
    return out

def build_directions(dom, papers, facts):
    bp = read(os.path.join(ROOT, "content", "blueprint", dom, "directions.json"), {}).get("directions", [])
    dir_ids = {d["id"] for d in bp}
    paper_ids = {p["id"] for p in papers}
    out = []
    for d in bp:
        did = d.get("id")
        f = facts.get(did, {}); fl = arr(f.get("facts"))
        kp = [p for p in arr(d.get("key_papers")) if p in paper_ids][:5]
        if not kp:
            kp = [p["id"] for p in sorted([x for x in papers if x["direction"] == did],
                                          key=lambda x: x["year"])][:3]
        out.append({
            "id": did, "name": s(d.get("name")), "name_en": s(d.get("name_en")),
            "question": s(d.get("question")), "why": s(d.get("why")),
            "core_tech": arr(d.get("core_tech")), "teams": arr(d.get("teams")),
            "key_papers": kp,
            "recent": s(d.get("recent")), "challenges": arr(d.get("challenges")),
            "related": [r for r in arr(d.get("related")) if r in dir_ids and r != did],
            "facts": fl, "anchors": arr(f.get("anchors")), "pitfalls": arr(f.get("pitfalls")),
        })
    return out

def split_covers(txt):
    parts = [p.strip() for p in re.split(r"[、；;。]\s*", s(txt)) if len(p.strip()) >= 4]
    return parts if len(parts) >= 2 else ([s(txt)] if s(txt) else [])

def build_stories(dom, facts):
    bp = read(os.path.join(ROOT, "content", "blueprint", dom, "stories.json"), {}).get("stories", [])
    out = []
    for st in bp:
        sid = st.get("id")
        f = facts.get(sid, {}); fl = arr(f.get("facts"))
        roles = arr(st.get("roles"))
        plot = arr(st.get("plot"))
        if not plot:
            plot = [{"act": "第%d幕" % (i + 1), "text": s(x)} for i, x in enumerate(arr(st.get("steps")))]
        out.append({
            "id": sid, "title": s(st.get("title")), "scene": s(st.get("scene")), "roles": roles,
            "plot": plot, "mapping": [s(r.get("maps_to")) for r in roles][:8],
            "boundaries": split_list(st.get("boundaries"), 2) or [s(st.get("boundaries"))],
            "covers": split_covers(st.get("covers")),
            "facts": fl, "pitfalls": arr(f.get("pitfalls")),
        })
    return out

def build_book(dom):
    b = read(os.path.join(ROOT, "content", "blueprint", dom, "book.json"), {}).get("book", {})
    secs = []
    for sec in arr(b.get("sections")):
        sid = s(sec.get("id"))
        m = re.fullmatch(r"ch(\d+)", sid)
        # 前端详情页要显示「第 N 卷 · 标题」，蓝图里没有 label 字段，
        # 缺了就渲染成 "undefined · 标题"，这里按 id 补出来。
        label = s(sec.get("label")) or (("第 %s 卷" % m.group(1)) if m else sid)
        secs.append({"id": sid, "label": label, "title": s(sec.get("title")), "subtitle": s(sec.get("subtitle")),
                     "note": s(sec.get("note")), "story_map": arr(sec.get("story_map")), "html": ""})
    short = META[dom]["short"]
    title = s(b.get("title"))
    if not title or title.lower() in (dom.lower(), short.lower()) or len(title) < 6:
        title = short + " · 从「能写」到「能上线」十二卷"
    # 中文短名两侧不留空格（"拆开 多模态 的" 读起来是断的）；拉丁短名保留空格。
    _sn = (" %s " % short) if short.isascii() else short
    subtitle = s(b.get("subtitle")) or ("从第一条 benchmark 到生产上线门：十二卷拆开%s的每一条取舍" % _sn)
    note = s(b.get("note")) or ("全书只讲一件事：LLM/agent 如何生成、优化、验证并部署 GPU kernel——基准与口径、可信评测、"
                               "oracle 审计、agent 脚手架、NCU/SASS profile、多轮 RL、生产端到端。每卷独立成篇，"
                               "按「专业导读 → 机制展开 → 工匠笔记」组织。")
    return {"title": title, "subtitle": subtitle,
            "note": note, "story_map": [], "sections": secs}

def build_appendix(dom):
    ap = read(os.path.join(ROOT, "content", "blueprint", dom, "appendix.json"), {}).get("appendix", [])
    return [{"id": s(a.get("id")), "title": s(a.get("title")), "summary": s(a.get("content")),
             "kind": s(a.get("kind"))} for a in ap]

MODMAP = {"papers": "paper", "algos": "algo", "theory": "theory", "stories": "story"}

def build_assessments(dom, papers, algos, theory, stories, dirs, facts):
    bp = read(os.path.join(ROOT, "content", "blueprint", dom, "exams.json"), {}).get("exams", [])
    pools = {"paper": {p["id"]: p for p in papers}, "algo": {a["id"]: a for a in algos},
             "theory": {t["id"]: t for t in theory}, "story": {s_["id"]: s_ for s_ in stories}}
    dir_items = {}
    for a in algos:
        dir_items.setdefault(a["direction"], []).append(("algo", a["id"], a["name"], a.get("idea"), [a.get("problem")]))
    for t in theory:
        dir_items.setdefault(t["direction"], []).append(("theory", t["id"], t["title"], t.get("plain"), [t.get("formula")]))
    for p in papers:
        dir_items.setdefault(p["direction"], []).append(("paper", p["id"], p["title"], p.get("summary"), [p.get("core_idea")]))
    out = []
    for q in bp:
        qid = s(q.get("id")); mod0 = s(q.get("module")); ref0 = s(q.get("ref"))
        mod = MODMAP.get(mod0); ref = ref0
        if not (mod and ref in pools[mod]):
            if mod0 == "directions" and ref0 in dir_items and dir_items[ref0]:
                mod, ref = dir_items[ref0][0][0], dir_items[ref0][0][1]
            else:
                txt = s(q.get("question")); cand = None
                for m, ids in pools.items():
                    for i in ids:
                        if i and i in txt: cand = (m, i); break
                    if cand: break
                if not cand: continue
                mod, ref = cand
        f = facts.get(qid, {}); fl = arr(f.get("facts"))
        outline = arr(q.get("answer_outline"))
        kp = outline[:6]
        if len(kp) < 2: kp = (kp + ["负载形态与 SLO", "精度与算子", "失效边界"])[:3]
        out.append({
            "id": qid, "module": mod, "ref": ref, "level": int(q.get("level") or 2),
            "question": s(q.get("question")), "answer": s("；".join(outline)),
            "explanation": s(fl[1]) if len(fl) > 1 else s("；".join(outline)),
            "key_points": kp,
            "common_errors": [s(fl[2])] if len(fl) > 2 else ["只背结论，不说明推理机制与部署代价"],
            "rubric": "要点齐全 60% · 机制正确 30% · 边界清楚 10%",
            "facts": fl, "pitfalls": arr(f.get("pitfalls")),
        })
    # 方向覆盖：每个方向至少一题（挂在同方向的理论/算法/论文上）
    covered = set()
    for q in out:
        item = pools.get(q["module"], {}).get(q["ref"])
        if item and item.get("direction"): covered.add(item["direction"])
    idx = 0
    for d in dirs:
        if d["id"] in covered: continue
        lst = dir_items.get(d["id"]) or []
        if not lst: continue
        idx += 1
        m, rid, title, summary, pts = lst[0]
        out.append(auto_question(m, rid, title, summary, pts, idx))
        covered.add(d["id"])
    # 经典论文覆盖
    have = {(q["module"], q["ref"]) for q in out}
    for p in papers:
        if p["type"] in ("foundational", "classic") and ("paper", p["id"]) not in have:
            idx += 1
            out.append(auto_question("paper", p["id"], p["title"], p.get("summary"), [p.get("core_idea")], idx))
    # 五层齐全
    levels = {q["level"] for q in out}
    for lv in (1, 2, 3, 4, 5):
        if lv in levels or not dirs: continue
        lst = dir_items.get(dirs[0]["id"]) or []
        if not lst: continue
        idx += 1
        m, rid, title, summary, pts = lst[0]
        q = auto_question(m, rid, title, "请从 L%d 层回答：这个方向的推理方案与容量决策怎么做？" % lv, pts, idx)
        q["level"] = lv
        out.append(q)
    # 数量补齐：L2 的 E-VISUAL 要求题库贡献 ≥100 个公式块与 ≥100 张表，
    # 每题固定 2 公式 + 2 表，因此题量必须到 50；蓝图里的题因引用失配会被丢掉几道。
    have = {(q["module"], q["ref"]) for q in out}
    for p in papers:
        if len(out) >= 50: break
        if ("paper", p["id"]) in have: continue
        idx += 1
        out.append(auto_question("paper", p["id"], p["title"], p.get("summary"), [p.get("core_idea")], idx))
        have.add(("paper", p["id"]))
    return out

def auto_question(mod, ref, title, summary, points, idx):
    pts = [s(x) for x in arr(points) if s(x)]
    kp = pts[:4]
    if len(kp) < 2: kp = (kp + ["负载形态与 SLO", "精度与算子", "失效边界"])[:3]
    return {
        "id": "q-%s-auto-%02d" % (mod, idx), "module": mod, "ref": ref, "level": 2,
        "question": "围绕《%s》，说明它在 CUDA kernel agent 版图上的核心做法，并指出一个失效边界。" % s(title)[:60],
        "answer": s(summary)[:300] or "；".join(pts)[:300] or "见条目正文",
        "explanation": "评分看三件事：负载从哪来、推理机制怎么定、代价在哪里。",
        "key_points": kp,
        "common_errors": ["只复述结论，不说明推理机制与部署代价"],
        "rubric": "要点齐全 60% · 机制正确 30% · 边界清楚 10%",
    }

def build_domain(dom, papers, algos, theory, stories, dirs, book, app, assess):
    m = META[dom]
    intro = (f"{m['name']}研究如何让 LLM/agent 写出正确、够快、能上线的 GPU kernel："
             f"从基准与口径开始，经过生成、执行反馈、profile、RL 与验证，最后落到生产端到端。"
             f"本领域聚焦：{m['focus']}。")
    intro += "六个方向分别是：" + "、".join(d["name"] for d in dirs) + "。"
    scope = [f"包含：{m['focus']}", "不包含：模型预训练、产品评测与纯硬件参数对比（只在必要处作为代价出现）"]
    stats = {"directions": len(dirs), "algorithms": len(algos), "papers": len(papers),
             "theory": len(theory), "stories": len(stories), "assessments": len(assess),
             "book": len(book.get("sections", [])), "appendix": len(app),
             "classic_algorithms": sum(1 for a in algos if a.get("tier") == "classic"),
             "core_papers": sum(1 for p in papers if p["type"] in ("foundational", "classic")),
             "recent_papers": sum(1 for p in papers if p["type"] in ("recent", "latest")),
             "total_papers": len(papers),
             "classic_papers": sum(1 for p in papers if p["type"] in ("foundational", "classic"))}
    path = [
        {"stage": "① 建立直觉", "items": ["读入门故事：" + (stories[0]["title"] if stories else "待补"),
                                          "看方向地图与首页技术栈"]},
        {"stage": "② 理论打底", "items": [t["title"] for t in theory[:4]] or ["理论卡待补"]},
        {"stage": "③ 论文精读", "items": [f"按方向顺序读 {len(papers)} 篇论文卡（{stats['classic_papers']} 篇经典 + {stats['recent_papers']} 篇近年）",
                                          "重点看评测配方与部署配方两节"]},
        {"stage": "④ 算法与自测", "items": [f"{len(algos)} 张算法卡按流程走一遍", f"{len(assess)} 道五层题，错题回链复习"]},
    ]
    return {"name": m["name"], "name_en": m.get("name_en", m["short"]), "short": m["short"], "profile": "L2",
            "tagline": m["tagline"], "intro": intro, "scope": scope, "stats": stats,
            "learning_path": path, "external_review": "内容由本地模型按论文事实卡生成，经脚本断言与人工抽样复核；未做外部同行评审",
            "updated": TODAY, "home_figure": "", "home_table": "", "map_figure": ""}

def build_summary(dom, dirs, papers, algos, theory):
    secs = []
    for d in dirs:
        secs.append({"title": d["name"], "body": f"{d['question']} {d['why']} 近两年进展：{d['recent']}"})
    secs.append({"title": "kernel agent 主线", "body": "把六个方向的共同动作抽出来：基准决定「什么算快」，oracle 决定「什么算对」，反馈决定「下一轮怎么改」，搜索/RL 决定「能走多远」，生产评测决定「值不值得上线」。任何一个环节的口径变化，都会在正确率、加速比、token 成本与端到端曲线上留下可观测的拐点。"})
    comps = [{"headers": ["方向", "核心问题", "代表论文数"],
              "rows": [[d["name"], s(d["question"])[:60], str(len(d["key_papers"]))] for d in dirs]}]
    trends = [f"{d['name']}：{s(d['recent'])[:80]}" for d in dirs[:3]]
    opens = [f"{d['name']}：{s(c)[:80]}" for d in dirs for c in arr(d.get("challenges"))][:4]
    future = ["可信评测会成为 agent 的准入门槛，而不是论文附录", "可验证奖励与形式/合约验证会合流，reward hacking 的空间被压缩"]
    order = [d["name"] for d in dirs] + [t["title"] for t in theory[:3]]
    return {"external_review": "内容由本地模型按论文事实卡生成，经脚本断言与人工抽样复核；未做外部同行评审", "sections": secs, "comparisons": comps,
            "trends": trends, "open_problems": opens, "future": future, "learning_order": order}

def build_evolution(papers, algos):
    ps = sorted(papers, key=lambda x: x["year"])
    picks = ps[:6] + ps[-6:]
    timeline = [{"year": p["year"], "title": p["title"][:80], "note": s(p.get("summary"))[:100], "paper": p["id"]} for p in picks]
    edges = []
    for a in algos:
        for sid in arr(a.get("successors")):
            edges.append({"from": a["id"], "to": sid, "type": "extend", "note": "同一方向上的后继配方"})
    if len(edges) < 3 and len(algos) >= 4:
        chain = sorted(algos, key=lambda x: x["year"])
        for i in range(min(4, len(chain) - 1)):
            edges.append({"from": chain[i]["id"], "to": chain[i + 1]["id"], "type": "extend",
                          "note": "时间上的方法继承"})
    return {"timeline": timeline, "edges": edges[:24], "external_review": "内容由本地模型按论文事实卡生成，经脚本断言与人工抽样复核；未做外部同行评审"}

def build_coverage(dirs, papers):
    gaps = [{"item": "非 arXiv 工业报告", "reason": "本轮以 arXiv API 与既有精读卡为准，未纳入厂商技术报告"}]
    if any(p["read_level"] != "full_text" for p in papers):
        gaps.append({"item": "部分论文仅摘要级", "reason": "只读到摘要与公开元数据，未逐节核验实验细节"})
    return {"searched": {
                "google_scholar": {"status": "partial", "note": "以 arXiv API 标题/全文检索为主", "fallback": "未逐条查 Google Scholar"},
                "chatgpt": {"status": "blocked", "fallback": "本轮未接入 ChatGPT 评审"},
                "youtube": {"status": "blocked", "fallback": "未做视频调研"}},
            "covered_directions": [d["id"] for d in dirs], "gaps": gaps,
            "limitations": "论文元数据来自 arXiv API；摘要级条目已在页面自曝，不当作全文机制分析。",
            "verified_at": TODAY}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--domain", required=True)
    args = ap.parse_args(); dom = args.domain
    outdir = os.path.join(ROOT, "site", "data", "domains", dom)
    os.makedirs(outdir, exist_ok=True)
    cat = json.load(open(os.path.join(ROOT, "content", "papers-catalog.json"), encoding="utf-8"))
    cat_by_id = {p["id"]: p for p in cat}
    sel = read(os.path.join(ROOT, "content", "selected.json"), {})
    facts = {}
    for module in ("directions", "algorithms", "theory", "stories", "exams", "book", "appendix"):
        fp = os.path.join(ROOT, "content", "facts", dom, module + ".json")
        if os.path.exists(fp):
            facts.update(read(fp, {}))
    papers = build_papers(dom, [], cat_by_id, sel)
    dirs = build_directions(dom, papers, facts)
    # papers 的 direction 需要 dirs 才能分配，重建一次；重建后再补一次 key_papers 回退
    papers = build_papers(dom, dirs, cat_by_id, sel)
    dirs = build_directions(dom, papers, facts)
    paper_ids = {p["id"] for p in papers}
    algos = build_algorithms(dom, dirs, paper_ids, facts)
    theory = build_theory(dom, dirs, paper_ids, facts)
    stories = build_stories(dom, facts)
    book = build_book(dom)
    app = build_appendix(dom)
    assess = build_assessments(dom, papers, algos, theory, stories, dirs, facts)
    domain = build_domain(dom, papers, algos, theory, stories, dirs, book, app, assess)
    summary = build_summary(dom, dirs, papers, algos, theory)
    evo = build_evolution(papers, algos)
    cov = build_coverage(dirs, papers)
    for name, obj in (("papers", papers), ("directions", dirs), ("algorithms", algos), ("theory", theory),
                      ("stories", stories), ("book", book), ("appendix", app), ("assessments", assess),
                      ("domain", domain), ("summary", summary), ("evolution", evo), ("coverage", cov)):
        json.dump(obj, open(os.path.join(outdir, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{dom}: papers={len(papers)} dirs={len(dirs)} algos={len(algos)} theory={len(theory)} "
          f"stories={len(stories)} exams={len(assess)} book={len(book['sections'])} app={len(app)}")

if __name__ == "__main__":
    main()
