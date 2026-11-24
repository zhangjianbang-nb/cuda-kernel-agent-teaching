#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select 40 deep-read + 20 shallow papers per domain from the catalog."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "content", "papers-catalog.json")
POOL = os.path.join(ROOT, "content", "paper-pool.json")
OUT = os.path.join(ROOT, "content", "selected.json")

def norm(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

def main():
    cat = json.load(open(CAT, encoding="utf-8"))
    pool = {norm(p["title"]) for p in json.load(open(POOL, encoding="utf-8"))}
    sel = {}
    for dom in ("moe", "multimodal", "coding", "rl", "video", "image", "audio"):
        ps = [p for p in cat if dom in p.get("domains", [])]
        def score(p):
            in_pool = norm(p["title"]) in pool
            venue = bool((p.get("venue") or "").strip())
            y = p.get("year") or 0
            return (in_pool, venue, y)
        ps.sort(key=score, reverse=True)
        deep = [p["id"] for p in ps[:40]]
        shallow = [p["id"] for p in ps[40:60]]
        sel[dom] = {"deep": deep, "shallow": shallow}
        print(dom, "deep", len(deep), "shallow", len(shallow),
              "pool_in_deep", sum(1 for p in ps[:40] if norm(p["title"]) in pool))
    json.dump(sel, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("total deep", sum(len(v["deep"]) for v in sel.values()),
          "shallow", sum(len(v["shallow"]) for v in sel.values()))

if __name__ == "__main__":
    main()
