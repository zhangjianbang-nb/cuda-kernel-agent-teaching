#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve paper titles to arXiv IDs via the arXiv API, with cache + retries."""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "content", "domains-seed.json")
CACHE = os.path.join(ROOT, "content", "arxiv-cache.json")
OUT = os.path.join(ROOT, "content", "paper-meta.json")
UA = "Mozilla/5.0 (research-teaching-site; contact whdx072018@foxmail.com)"

def norm(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def toks(t):
    return set(norm(t).split())

def jacc(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / max(1, len(A | B))

def fetch(query, tries=4):
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": query, "start": 0, "max_results": 5})
    last = ""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = str(e)[:120]
            time.sleep(4 + 5 * i)
    return "ERR:" + last

def parse(xml):
    entries = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        def g(tag):
            mm = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), e, re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""
        idm = g("id")
        arx = re.sub(r"v\d+$", "", idm.rsplit("/", 1)[-1]) if "arxiv.org" in idm else ""
        entries.append({"id": arx, "title": g("title"), "abstract": g("summary"),
                        "published": g("published"), "updated": g("updated"),
                        "authors": re.sub(r"<[^>]+>", ", ", g("author"))[:300],
                        "journal_ref": g("arxiv:journal_ref"),
                        "primary": g("arxiv:primary_category").split('"')[0]})
    return entries

def main():
    seed = json.load(open(SEED, encoding="utf-8"))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [(d, t) for d, ts in seed.items() for t in ts if t not in cache]
    print(f"todo={len(todo)} cached={len(cache)}", flush=True)
    for i, (dom, title) in enumerate(todo, 1):
        q = 'ti:"%s"' % re.sub(r"[^A-Za-z0-9 \-:,'()]", " ", title)
        xml = fetch(q)
        if xml.startswith("ERR:"):
            print(f"[{i}/{len(todo)}] FETCH_ERR {title[:60]} {xml[:80]}", flush=True)
            continue
        ents = parse(xml)
        best, score = None, 0.0
        for e in ents:
            s = jacc(title, e["title"])
            if s > score:
                best, score = e, s
        if best and score >= 0.55:
            best["match_score"] = round(score, 3)
            cache[title] = best
            print(f"[{i}/{len(todo)}] OK {score:.2f} {best['id']} {title[:50]}", flush=True)
        else:
            cache[title] = {"id": "", "title": (ents[0]["title"] if ents else ""), "match_score": round(score, 3)}
            print(f"[{i}/{len(todo)}] MISS {title[:60]} best={score:.2f}", flush=True)
        json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)
        time.sleep(3)
    # regroup by domain
    for dom, ts in seed.items():
        out[dom] = [dict(cache[t], query_title=t) for t in ts if t in cache]
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for d in out.values() for p in d if p.get("id"))
    tot = sum(len(v) for v in out.values())
    print(f"DONE resolved={ok}/{tot}", flush=True)

if __name__ == "__main__":
    main()
