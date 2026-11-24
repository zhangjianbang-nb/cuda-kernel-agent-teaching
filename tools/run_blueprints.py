#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run all 7 domains x 8 modules blueprints with 4-way concurrency, merging batches."""
import concurrent.futures, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_blueprint as MB
import llm

OUT = os.path.join(ROOT, "content", "blueprint")
DOMAINS = list(MB.META.keys())
PHASE1 = [(d, "directions", 0, 0) for d in DOMAINS]
PHASE2 = []
for dom in DOMAINS:
    PHASE2.append((dom, "algorithms", 0, 10))
    PHASE2.append((dom, "algorithms", 10, 10))
    PHASE2.append((dom, "theory", 0, 7))
    PHASE2.append((dom, "theory", 7, 7))
    PHASE2.append((dom, "stories", 0, 0))
    PHASE2.append((dom, "book", 0, 0))
    PHASE2.append((dom, "appendix", 0, 0))
PHASE3 = [(d, "exams", 0, 25) for d in DOMAINS] + [(d, "exams", 25, 25) for d in DOMAINS]

def refs_for(dom):
    import json as _j, os as _os, re as _re
    refs = []
    dp = _os.path.join(OUT, dom, "directions.json")
    if _os.path.exists(dp):
        refs += [("directions", d["id"]) for d in _j.load(open(dp, encoding="utf-8")).get("directions", [])]
    cat = _j.load(open(_os.path.join(ROOT, "content", "papers-catalog.json"), encoding="utf-8"))
    for p in cat:
        if dom in p.get("domains", []):
            y = p.get("year") or 0
            kind = "classic" if y <= 2021 else "recent"
            refs.append(("papers", p["id"], kind))
    for module in ("algorithms-0", "theory-0"):
        fp = _os.path.join(OUT, dom, module + ".json")
        if _os.path.exists(fp):
            key = "algorithms" if module.startswith("algorithms") else "theory"
            refs += [(key, it["id"]) for it in _j.load(open(fp, encoding="utf-8")).get(key, [])]
    lines = []
    for r in refs:
        lines.append("  ".join(str(x) for x in r))
    return "\n".join(lines)

def prompt_for(dom, module, start, n):
    if module == "directions": return MB.prompt_dirs(dom)
    if module == "algorithms": return MB.prompt_algos(dom, start, n)
    if module == "theory": return MB.prompt_theory(dom, start, n)
    if module == "stories": return MB.prompt_stories(dom)
    if module == "book": return MB.prompt_book(dom)
    if module == "appendix": return MB.prompt_appendix(dom)
    if module == "exams": return MB.prompt_exams(dom, start, n, refs_for(dom))
    raise ValueError(module)

def key_of(module):
    return {"book": "sections"}.get(module, module)

def run(task):
    dom, module, start, n = task
    try:
        txt, fin, usage = llm.call(prompt_for(dom, module, start, n), temperature=0.5, json_mode=True)
        d = llm.parse_json(txt)
        items = d.get("book", {}).get("sections", []) if module == "book" else d.get(key_of(module), [])
        return ("ok", dom, module, start, items)
    except Exception as e:
        return ("fail", dom, module, start, str(e)[:200])

def merge():
    for dom in DOMAINS:
        for module in ("directions", "algorithms", "theory", "stories", "book", "appendix", "exams"):
            import re as _re
            paths = sorted([f for f in os.listdir(os.path.join(OUT, dom)) if _re.match(r"^%s-\d+\.json$" % module, f)])
            if not paths: continue
            items = []
            for p in paths:
                d = json.load(open(os.path.join(OUT, dom, p), encoding="utf-8"))
                if module == "book":
                    items.extend(d.get("book", {}).get("sections", []))
                else:
                    items.extend(d.get(module, []))
            # dedupe ids
            seen = set(); out = []
            for it in items:
                i = it.get("id") or ""
                if i in seen:
                    k = 2
                    while f"{i}-{k}" in seen: k += 1
                    it["id"] = f"{i}-{k}"; i = it["id"]
                seen.add(i); out.append(it)
            if module == "exams":
                out.sort(key=lambda x: str(x.get("id")))
            if module == "book":
                json.dump({"book": {"title": dom, "sections": out}}, open(os.path.join(OUT, dom, "book.json"), "w"), ensure_ascii=False, indent=1)
            else:
                json.dump({module: out}, open(os.path.join(OUT, dom, module + ".json"), "w"), ensure_ascii=False, indent=1)
            print(dom, module, len(out), flush=True)

def run_phase(tasks, t0):
    todo = [t for t in tasks if not os.path.exists(os.path.join(OUT, t[0], f"{t[1]}-{t[2]}.json"))]
    print(f"phase todo={len(todo)}/{len(tasks)}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(run, t): t for t in todo}
        for fut in concurrent.futures.as_completed(futs):
            st, dom, module, start, info = fut.result()
            if st == "ok":
                json.dump({("book" if module == "book" else module): ({"title": dom, "sections": info} if module == "book" else info)},
                          open(os.path.join(OUT, dom, f"{module}-{start}.json"), "w"), ensure_ascii=False, indent=1)
                print(f"OK {dom}/{module}#{start} n={len(info)} {time.time()-t0:.0f}s", flush=True)
            else:
                print(f"FAIL {dom}/{module}#{start} {info} {time.time()-t0:.0f}s", flush=True)

def main():
    os.makedirs(OUT, exist_ok=True)
    for dom in DOMAINS: os.makedirs(os.path.join(OUT, dom), exist_ok=True)
    t0 = time.time()
    run_phase(PHASE1, t0)
    merge()
    run_phase(PHASE2, t0)
    merge()
    run_phase(PHASE3, t0)
    merge()

if __name__ == "__main__":
    main()
