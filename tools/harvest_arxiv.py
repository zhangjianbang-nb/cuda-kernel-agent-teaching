#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recover MISS titles via all-field search + harvest extra arXiv papers per domain."""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "content", "domains-seed.json")
CACHE = os.path.join(ROOT, "content", "arxiv-cache.json")
OUT = os.path.join(ROOT, "content", "paper-meta.json")
HARVEST = os.path.join(ROOT, "content", "harvest.json")
UA = "Mozilla/5.0 (research-teaching-site; contact whdx072018@foxmail.com)"

QUERIES = {
 "moe": ['abs:"mixture of experts" AND abs:"training"', 'abs:"expert parallelism"', 'abs:"load balancing" AND abs:"mixture-of-experts"'],
 "multimodal": ['abs:"image-text" AND abs:"data curation"', 'abs:"multimodal" AND abs:"pretraining data"', 'abs:"caption" AND abs:"synthetic"'],
 "coding": ['abs:"code" AND abs:"pretraining data"', 'abs:"code generation" AND abs:"reinforcement learning"', 'abs:"fill-in-the-middle"'],
 "rl": ['abs:"preference data"', 'abs:"reward model" AND abs:"training"', 'abs:"verifiable reward"'],
 "video": ['abs:"video generation" AND abs:"training"', 'abs:"video-text" AND abs:"dataset"', 'abs:"temporal compression" AND abs:"video"'],
 "image": ['abs:"text-to-image" AND abs:"data"', 'abs:"diffusion" AND abs:"data filtering"', 'abs:"image caption" AND abs:"synthetic"'],
 "audio": ['abs:"text-to-speech" AND abs:"training"', 'abs:"neural audio codec"', 'abs:"speech" AND abs:"data" AND abs:"synthetic"'],
}
KEY = {
 "moe": ("mixture", "expert", "routing", "sparse"),
 "multimodal": ("multimodal", "image-text", "vision-language", "caption", "clip"),
 "coding": ("code", "program", "repository", "compiler"),
 "rl": ("preference", "reward", "reinforcement", "policy", "rlhf", "dpo"),
 "video": ("video", "temporal", "frame"),
 "image": ("image", "diffusion", "text-to-image", "visual"),
 "audio": ("speech", "audio", "voice", "music", "tts", "codec"),
}

def norm(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

def toks(t): return set(norm(t).split())

def jacc(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / max(1, len(A | B))

def fetch(query, max_results=10, tries=4):
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": query, "start": 0, "max_results": max_results, "sortBy": "relevance"})
    last = ""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = str(e)[:120]; time.sleep(4 + 5 * i)
    return "ERR:" + last

def parse(xml):
    entries = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        def g(tag):
            mm = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), e, re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""
        idm = g("id"); arx = re.sub(r"v\d+$", "", idm.rsplit("/", 1)[-1]) if "arxiv.org" in idm else ""
        entries.append({"id": arx, "title": g("title"), "abstract": g("summary"),
                        "published": g("published"), "updated": g("updated"),
                        "authors": re.sub(r"<[^>]+>", ", ", g("author"))[:300],
                        "journal_ref": g("arxiv:journal_ref"),
                        "primary": g("arxiv:primary_category").split('"')[0]})
    return entries

def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    seed = json.load(open(SEED, encoding="utf-8"))
    # 1) fallback for MISS
    miss = [t for t, v in cache.items() if not v.get("id")]
    print("miss", len(miss), flush=True)
    for i, title in enumerate(miss, 1):
        q = 'all:"%s"' % re.sub(r"[^A-Za-z0-9 \-:,'()]", " ", title)[:120]
        xml = fetch(q, 10)
        if xml.startswith("ERR:"):
            print(f"[{i}/{len(miss)}] ERR {title[:50]}", flush=True); continue
        ents = parse(xml); best, score = None, 0.0
        for e in ents:
            s = jacc(title, e["title"])
            if s > score: best, score = e, s
        if best and score >= 0.42:
            best["match_score"] = round(score, 3); best["query_title"] = title
            cache[title] = best
            print(f"[{i}/{len(miss)}] OK {score:.2f} {best['id']} {title[:44]}", flush=True)
        else:
            print(f"[{i}/{len(miss)}] STILL_MISS {title[:44]} best={score:.2f}", flush=True)
        json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)
        time.sleep(3)
    # 2) harvest per domain
    harvest = json.load(open(HARVEST)) if os.path.exists(HARVEST) else {}
    have_ids = {v.get("id") for v in cache.values() if v.get("id")}
    for dom, qs in QUERIES.items():
        bucket = harvest.setdefault(dom, [])
        known = {p.get("id") for p in bucket}
        for q in qs:
            xml = fetch(q, 12)
            if xml.startswith("ERR:"):
                print("harvest ERR", dom, q[:40], flush=True); continue
            for e in parse(xml):
                if not e["id"] or e["id"] in known or e["id"] in have_ids: continue
                y = int((e.get("published") or "2020")[:4])
                if y < 2019: continue
                tl = e["title"].lower()
                if not any(k in tl or k in e["abstract"].lower() for k in KEY[dom]): continue
                e["match_score"] = 1.0; e["query_title"] = e["title"]; e["source"] = "harvest"
                bucket.append(e); known.add(e["id"])
            print(f"harvest {dom} {q[:34]} -> {len(bucket)}", flush=True)
            time.sleep(3)
        json.dump(harvest, open(HARVEST, "w"), ensure_ascii=False, indent=1)
    print("DONE harvest", {d: len(v) for d, v in harvest.items()}, flush=True)

if __name__ == "__main__":
    main()
