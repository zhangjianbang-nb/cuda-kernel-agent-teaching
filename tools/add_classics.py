#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补录 RL 后训练经典论文（arXiv 元数据核验），写入 catalog 并加入 rl deep 选择。

用法：python3 -I tools/add_classics.py
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "content", "papers-catalog.json")
SEL = os.path.join(ROOT, "content", "selected.json")
UA = "Mozilla/5.0 (research-teaching-site; contact whdx072018@foxmail.com)"

IDS = {
    "1707.06347": "rl",   # PPO
    "1706.03741": "rl",   # Deep RL from human preferences
    "2203.02155": "rl",   # InstructGPT
    "2212.08073": "rl",   # Constitutional AI
    "2305.18290": "rl",   # DPO
    "2310.10505": "rl",   # ReMax
}

def fetch(ids):
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"id_list": ",".join(ids), "max_results": len(ids)})
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print("retry", i, str(e)[:100], flush=True); time.sleep(4 + 5 * i)
    raise SystemExit("arXiv 拉取失败")

def parse(xml):
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        def g(tag):
            mm = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), e, re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""
        idm = g("id"); arx = re.sub(r"v\d+$", "", idm.rsplit("/", 1)[-1]) if "arxiv.org" in idm else ""
        authors = [a.strip() for a in re.findall(r"<name>(.*?)</name>", e) if a.strip()]
        out.append({"arxiv": arx, "title": g("title"), "abstract": g("summary"),
                    "published": g("published"), "authors": authors,
                    "journal_ref": g("arxiv:journal_ref")})
    return out

def slug(t):
    t = re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")
    return t[:44].strip("-")

def main():
    cat = json.load(open(CAT, encoding="utf-8"))
    have = {p.get("arxiv") for p in cat if p.get("arxiv")}
    xml = fetch([i for i in IDS if i not in have])
    entries = parse(xml)
    print("fetched", len(entries), flush=True)
    added = []
    for e in entries:
        dom = IDS.get(e["arxiv"])
        if not dom or e["arxiv"] in have: continue
        year = int((e["published"] or "2020")[:4])
        pid = "paper-%s-%d" % (slug(e["title"]), year)
        if any(p["id"] == pid for p in cat):
            pid += "-%s" % e["arxiv"].replace(".", "")
        venue = e["journal_ref"] or "arXiv preprint"
        cat.append({
            "id": pid, "title": e["title"], "title_zh": "", "year": year, "venue": venue,
            "authors": e["authors"] or ["未给出"], "links": {"paper": "https://arxiv.org/abs/" + e["arxiv"], "code": ""},
            "arxiv": e["arxiv"], "domains": [dom], "summary": e["abstract"],
            "problem": "", "core_idea": "", "training": "", "formula": "",
            "experiments": {"datasets": [], "baselines": [], "results": "", "limits": "", "ablations": ""},
        })
        added.append(pid)
        have.add(e["arxiv"])
    json.dump(cat, open(CAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sel = json.load(open(SEL, encoding="utf-8"))
    for pid in added:
        if pid not in sel["rl"]["deep"]:
            sel["rl"]["deep"].append(pid)
    json.dump(sel, open(SEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("added", len(added), "rl deep", len(sel["rl"]["deep"]), added, flush=True)

if __name__ == "__main__":
    main()
