#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic exam bank built from cards/blueprints (no LLM JSON risk).

70 questions: 50 papers (one each), 6 directions, 8 algorithms, 6 theory.
Every question carries concrete anchors from the item itself, so it can be
graded against the same facts the long-form chapters use.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "content", "blueprint", "cuda")
CARDS = os.path.join(ROOT, "content", "cards", "cuda")


def read(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def clip(s, n=160):
    s = (s or "").strip().replace("\n", " ")
    return s[:n]


def bullet(s, n=110):
    s = clip(s, n)
    return s if len(s) >= 15 else ""


def outlines(*groups):
    out = []
    for g in groups:
        if isinstance(g, str):
            b = bullet(g)
            if b:
                out.append(b)
        else:
            for x in (g or []):
                if isinstance(x, dict):
                    sym = x.get("sym") or x.get("name") or ""
                    mean = x.get("meaning") or x.get("desc") or ""
                    x = (f"{sym}：{mean}" if sym else mean)
                b = bullet(x)
                if b:
                    out.append(b)
    seen = []
    for x in out:
        if x not in seen:
            seen.append(x)
    return seen[:6]


def paper_question(c, idx):
    title = c.get("_title") or c.get("title") or c.get("_paper_id")
    lv = (idx % 5) + 1
    ex = c.get("experiments") or {}
    formula = c.get("formula") or ""
    anchors = "、".join((c.get("anchors") or [])[:6]) or "论文给出的口径"
    if lv == 1:
        q = (f"《{title}》把哪一类 GPU kernel 工程问题作为核心？它使用的基准、基线与指标口径分别是什么？"
             f"请给出定义，并说明它和相邻工作的分工。")
        kp = outlines(c.get("background"), c.get("problem"),
                      (ex.get("datasets") or [])[:2], (ex.get("baselines") or [])[:2],
                      c.get("innovation"))
    elif lv == 2:
        q = (f"《{title}》的 pipeline 从输入到评测要经过哪几步？每一步的输入、输出和失败模式是什么？"
             f"请按一次 kernel 生成—编译—运行—评测的顺序回答。")
        kp = outlines(c.get("pipeline"), c.get("pitfalls"), c.get("limitations"))
    elif lv == 3:
        q = (f"《{title}》报告的加速比如何计算？若基线时延为 T0、候选为 T1，写出 speedup 公式；"
             f"并结合论文中的 {anchors} 说明这个数字在什么条件下不可比。")
        kp = outlines(formula, c.get("facts"), ex.get("limits"), c.get("pitfalls"))
    elif lv == 4:
        q = (f"要为《{title}》的方法搭一套可复现的评测 harness：基线、输入分布、正确性门、"
             f"防作弊与上线门分别怎么定？给出可执行的配置与验收口径。")
        kp = outlines(c.get("data_recipe"), c.get("train_recipe"), c.get("pitfalls"),
                      (ex.get("baselines") or [])[:2], c.get("limitations"))
    else:
        q = (f"《{title}》的方法在跨硬件、跨 shape 或跨 dtype 迁移时最可能在哪里失效？"
             f"给出你的判断、验证方案与回退条件，不要只复述摘要。")
        kp = outlines(c.get("limitations"), c.get("pitfalls"), c.get("impact"),
                      c.get("direction"))
    if len(kp) < 3:
        kp = (kp + ["负载形态与 SLO", "精度与算子口径", "失效边界与回退"])[:3]
    return {"id": f"q-cuda-p{idx:02d}", "level": lv, "module": "papers",
            "ref": c.get("_paper_id"), "question": q, "answer_outline": kp}


def direction_questions(dirs):
    out = []
    for i, d in enumerate(dirs):
        lv = 4 if i % 2 == 0 else 5
        if lv == 4:
            q = (f"方向「{d['name']}」要解决的三个具体问题是什么？给出评测侧与部署侧各两条可执行做法，"
                 f"并说明它与相邻方向的分工。")
            kp = outlines(d.get("problem"), d.get("idea"), d.get("eval"), d.get("deploy"),
                          d.get("limits"), d.get("plain"))
        else:
            q = (f"如果团队只有一张 GPU 和两周时间，方向「{d['name']}」应该先做什么、明确不做什么？"
                 f"给出取舍依据与验收口径。")
            kp = outlines(d.get("problem"), d.get("idea"), d.get("limits"), d.get("eval"),
                          d.get("deploy"))
        if len(kp) < 3:
            kp = (kp + ["先建可复核基线", "再压搜索预算", "最后设上线门"])[:3]
        out.append({"id": f"q-cuda-d{i+1:02d}", "level": lv, "module": "directions",
                    "ref": d["id"], "question": q, "answer_outline": kp})
    return out


def algo_questions(algos):
    out = []
    for i, a in enumerate(algos):
        lv = 2 if i % 2 == 0 else 3
        if lv == 2:
            q = (f"算法「{a['name']}」按一次 kernel 生成/优化/验证的流动拆成哪几步？"
                 f"每一步的输入、输出与代价是什么？")
            kp = outlines(a.get("flow"), a.get("problem"), a.get("limits"), a.get("idea"))
        else:
            q = (f"算法「{a['name']}」的核心公式逐项解释；给定一个具体算例，"
                 f"说明它如何影响搜索预算或上线判断。")
            kp = outlines(a.get("formula"), a.get("variables"), a.get("eval"),
                          a.get("limits"), a.get("idea"))
        if len(kp) < 3:
            kp = (kp + ["输入输出口径", "代价与预算", "失效边界"])[:3]
        out.append({"id": f"q-cuda-a{i+1:02d}", "level": lv, "module": "algos",
                    "ref": a["id"], "question": q, "answer_outline": kp})
    return out


def theory_questions(theory):
    out = []
    for i, t in enumerate(theory[:6]):
        lv = 3 if i % 2 == 0 else 5
        if lv == 3:
            q = (f"理论「{t['title']}」的公式逐项含义是什么？推导的关键一步在哪？"
                 f"给出一个可手算的数值算例。")
            kp = outlines(t.get("plain"), t.get("formula"), t.get("variables"),
                          t.get("limits"))
        else:
            q = (f"理论「{t['title']}」在什么假设下失效？如果线上出现相反现象，"
                 f"你怎么判断是公式错了还是负载变了？")
            kp = outlines(t.get("limits"), t.get("plain"), t.get("formula"))
        if len(kp) < 3:
            kp = (kp + ["假设与适用范围", "参数口径", "反例与验证"])[:3]
        out.append({"id": f"q-cuda-t{i+1:02d}", "level": lv, "module": "theory",
                    "ref": t["id"], "question": q, "answer_outline": kp})
    return out


def main():
    cat = read(os.path.join(ROOT, "content", "papers-catalog.json"), [])
    dirs = read(os.path.join(BP, "directions.json"), {}).get("directions", [])
    algos = read(os.path.join(BP, "algorithms.json"), {}).get("algorithms", [])
    theory = read(os.path.join(BP, "theory.json"), {}).get("theory", [])
    exams = []
    idx = 0
    for p in cat:
        c = read(os.path.join(CARDS, p["id"] + ".json"), None)
        if not c:
            continue
        idx += 1
        exams.append(paper_question(c, idx))
    exams += direction_questions(dirs)
    exams += algo_questions(algos)
    exams += theory_questions(theory)
    # id 去重（不同模块前缀已不同，这里兜底）
    seen = set()
    uniq = []
    for q in exams:
        if q["id"] in seen:
            continue
        seen.add(q["id"])
        uniq.append(q)
    json.dump({"exams": uniq}, open(os.path.join(BP, "exams.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print("exams", len(uniq), dict(Counter(q["module"] for q in uniq)),
          dict(Counter(q["level"] for q in uniq)))


if __name__ == "__main__":
    main()
