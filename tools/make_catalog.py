#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge prior-project paper pool + arXiv-resolved papers into one catalog with ids."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
POOL = os.path.join(ROOT, "content", "paper-pool.json")
META = os.path.join(ROOT, "content", "paper-meta.json")
OUT = os.path.join(ROOT, "content", "papers-catalog.json")
SRC_DOM = {"moe": "moe", "video": "video", "mopd": "rl", "coding": "coding"}

def norm(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = t.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def slug(t, year):
    s = re.sub(r"[^a-z0-9]+", "-", norm(t)).strip("-")[:36].strip("-")
    return f"paper-{s}-{year}" if s else f"paper-{year}"

def arx(links):
    s = json.dumps(links or {})
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", s)
    return m.group(1) if m else ""

def main():
    pool = json.load(open(POOL, encoding="utf-8"))
    meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
    by_title = {}
    cat = []
    for p in pool:
        t = p["title"]
        # 2026-11-18：跨领域共享论文在 pool 里会出现多次（同一篇挂多个 src），
        # 先按标题合并 domains，否则 catalog 会出现 -2/-3 后缀的重复条目。
        if norm(t) in by_title:
            d = SRC_DOM.get(p["src"], p["src"])
            if d not in by_title[norm(t)]["domains"]:
                by_title[norm(t)]["domains"].append(d)
            continue
        e = {"id": slug(t, p.get("year") or 0), "title": t, "title_zh": p.get("title_zh", ""),
             "year": p.get("year"), "venue": p.get("venue", ""), "authors": p.get("authors", []),
             "links": p.get("links", {}), "arxiv": arx(p.get("links")), "domains": [SRC_DOM.get(p["src"], p["src"])],
             "summary": p.get("summary", ""), "problem": p.get("problem", ""), "core_idea": p.get("core_idea", ""),
             "training": p.get("training", ""), "experiments": p.get("experiments", ""), "formula": p.get("formula", ""),
             "read_level": "full_text" if len(p.get("training", "") or "") > 300 else "abstract_only",
             "source": "pool:" + p["src"]}
        cat.append(e); by_title[norm(t)] = e
    added = 0
    for dom, ps in meta.items():
        for p in ps:
            if not p.get("id"):
                continue
            t = p.get("title") or p.get("query_title") or ""
            k = norm(t)
            if k in by_title:
                if dom not in by_title[k]["domains"]:
                    by_title[k]["domains"].append(dom)
                continue
            y = int((p.get("published") or "2020")[:4])
            e = {"id": slug(t, y), "title": t, "title_zh": "", "year": y, "venue": p.get("journal_ref", ""),
                 "authors": [a.strip() for a in (p.get("authors") or "").split(",") if a.strip()][:12],
                 "links": {"paper": "https://arxiv.org/abs/" + p["id"], "code": ""}, "arxiv": p["id"],
                 "domains": [dom], "summary": "", "problem": "", "core_idea": "",
                 "training": "", "experiments": "", "formula": "", "abstract": p.get("abstract", ""),
                 "read_level": "abstract_only", "source": "arxiv"}
            cat.append(e); by_title[k] = e; added += 1
    # dedupe ids
    seen = {}
    for e in cat:
        if e["id"] in seen:
            seen[e["id"]] += 1; e["id"] = e["id"] + "-%d" % seen[e["id"]]
        else:
            seen[e["id"]] = 1
    json.dump(cat, open(OUT, "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(d for e in cat for d in e["domains"])
    print("catalog", len(cat), "added_from_arxiv", added)
    print("per-domain:", dict(c))

if __name__ == "__main__":
    main()
