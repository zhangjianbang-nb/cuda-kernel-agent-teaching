#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge curated classics (verified via arXiv id_list) in front of harvested pool.

Output: content/paper-pool.json  (per-domain order: classics first, then harvest)
"""
import json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "content", "harvest-raw.json")
OUT = os.path.join(ROOT, "content", "paper-pool.json")
UA = "Mozilla/5.0 (research-teaching-site; contact whdx072018@foxmail.com)"
NS = {"a": "http://www.w3.org/2005/Atom"}

# (arxiv_id, 期望标题关键词) —— 用于校验返回条目确实是我们想要的那篇
CLASSICS = {
 "moe": [
  ("2101.03961", "switch transformers"), ("2006.16668", "gshard"),
  ("2401.06066", "deepseekmoe"), ("2401.04088", "mixtral of experts"),
  ("2211.15841", "megablocks"),
  ("2206.03382", "tutel"), ("2202.09368", "expert choice"),
  ("2112.06905", "glam"), ("2412.19437", "deepseek-v3"),
  ("2405.04434", "deepseek-v2"),
 ],
 "multimodal": [
  ("2103.00020", "transferable visual models"), ("2301.12597", "blip-2"),
  ("2304.08485", "visual instruction tuning"), ("2204.14198", "flamingo"),
  ("2308.12966", "qwen-vl"), ("2303.15343", "sigmoid loss"),
  ("2010.11929", "image is worth 16x16"), ("2312.14238", "internvl"),
  ("2310.03744", "improved baselines with visual instruction"),
 ],
 "coding": [
  ("2107.03374", "trained on code"), ("2305.06161", "starcoder"),
  ("2308.12950", "code llama"), ("2401.14196", "deepseek-coder"),
  ("2207.14255", "fill in the middle"), ("2303.12570", "repocoder"),
  ("2305.07922", "codet5+"), ("2409.12186", "qwen2.5-coder"),
  ("2203.13474", "codegen"), ("2301.03988", "santacoder"),
 ],
 "rl": [
  ("1707.06347", "proximal policy optimization"), ("2203.02155", "follow instructions with human feedback"),
  ("2305.18290", "direct preference optimization"), ("2402.03300", "deepseekmath"),
  ("2310.10505", "remax"), ("2402.14740", "back to basics"),
  ("1506.02438", "generalized advantage estimation"), ("2501.12948", "deepseek-r1"),
  ("2212.08073", "constitutional ai"),
 ],
 "video": [
  ("2204.03458", "video diffusion models"), ("2209.14792", "make-a-video"),
  ("2401.03048", "latte"), ("2408.06072", "cogvideox"),
  ("2412.20404", "open-sora"), ("2212.09748", "scalable diffusion models with transformers"),
  ("2412.03603", "hunyuanvideo"), ("2312.06662", "videopoet"),
  ("2503.20314", "wan"), ("2205.15868", "cogvideo"),
 ],
 "image": [
  ("2006.11239", "denoising diffusion probabilistic"), ("2010.02502", "denoising diffusion implicit"),
  ("2112.10752", "latent diffusion"), ("2403.03206", "rectified flow transformers"),
  ("2205.11487", "photorealistic text-to-image"), ("2204.06125", "hierarchical text-conditional"),
  ("2303.01469", "consistency models"), ("2310.04378", "latent consistency"),
  ("2307.01952", "sdxl"), ("2210.02747", "flow matching"),
  ("2209.14577", "flow straight and fast"),
 ],
 "audio": [
  ("1609.03499", "wavenet"), ("1712.05884", "natural tts synthesis"),
  ("2010.05646", "hifi-gan"), ("2106.06103", "vits"),
  ("2212.04356", "robust speech recognition"), ("2210.13438", "neural audio compression"),
  ("2107.03312", "soundstream"), ("2209.03143", "audiolm"),
  ("2301.11325", "musiclm"), ("2301.02111", "neural codec language models"),
  ("2407.05407", "cosyvoice"), ("2006.04558", "fastspeech 2"),
 ],
}
# 推理系统/精度/注意力核心论文：按相关性挂到多个领域
SHARED = [
 ("2309.06180", "pagedattention", ["moe", "coding", "multimodal", "rl"]),
 ("2211.17192", "speculative decoding", ["coding", "rl", "moe"]),
 ("2401.10774", "medusa", ["coding", "rl"]),
 ("2401.15077", "eagle", ["coding", "rl"]),
 ("2312.07104", "sglang", ["coding", "moe", "rl"]),
 ("2308.16369", "sarathi", ["moe", "rl"]),
 ("2401.09670", "distserve", ["moe", "rl"]),
 ("2311.18677", "splitwise", ["rl", "moe"]),
 ("2407.00079", "mooncake", ["rl", "moe"]),
 ("2401.08671", "deepspeed-fastgen", ["moe"]),
 ("2306.00978", "awq", ["moe", "multimodal", "image", "video"]),
 ("2210.17323", "gptq", ["moe", "multimodal", "image", "video"]),
 ("2211.10438", "smoothquant", ["moe", "multimodal", "audio"]),
 ("2208.07339", "llm.int8", ["moe"]),
 ("2209.05433", "fp8 formats", ["moe", "video", "image"]),
 ("2310.10537", "microscaling", ["moe", "video", "image", "audio"]),
 ("2205.14135", "flashattention", ["moe", "video", "image"]),
 ("2307.08691", "flashattention-2", ["moe", "video", "image"]),
 ("2407.08608", "flashattention-3", ["moe", "video", "image"]),
]


def norm(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def fetch_ids(ids):
    url = ("https://export.arxiv.org/api/query?id_list=" + ",".join(ids)
           + "&max_results=%d" % len(ids))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            return ET.fromstring(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            print("retry", attempt, e, file=sys.stderr)
            time.sleep(5)
    return None


def parse(root):
    out = {}
    for e in root.findall("a:entry", NS):
        aid = (e.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1]
        aid = re.sub(r"v\d+$", "", aid)
        out[aid] = {
            "id": aid,
            "title": re.sub(r"\s+", " ", e.findtext("a:title", "", NS) or "").strip(),
            "abstract": re.sub(r"\s+", " ", e.findtext("a:summary", "", NS) or "").strip(),
            "year": int((e.findtext("a:published", "", NS) or "")[:4] or 0),
            "venue": (e.findtext("a:journal_ref", "", NS) or "").strip(),
            "authors": [a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)][:12],
        }
    return out


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    all_ids = [x[0] for v in CLASSICS.values() for x in v] + [x[0] for x in SHARED]
    all_ids = sorted(set(all_ids))
    meta = {}
    for i in range(0, len(all_ids), 40):
        chunk = all_ids[i:i + 40]
        root = fetch_ids(chunk)
        if root is None:
            print("FETCH FAILED", chunk, file=sys.stderr)
            continue
        meta.update(parse(root))
        time.sleep(3)
    bad = []
    for dom, items in CLASSICS.items():
        for aid, kw in items:
            p = meta.get(aid)
            nt = set(norm(p["title"]).split()) if p else set()
            if not p or not all(t in nt for t in norm(kw).split()):
                bad.append((dom, aid, kw, p["title"] if p else None))
    for aid, kw, doms in SHARED:
        p = meta.get(aid)
        nt = set(norm(p["title"]).split()) if p else set()
        if not p or not all(t in nt for t in norm(kw).split()):
            bad.append(("shared", aid, kw, p["title"] if p else None))
    print("verified", len(meta), "bad", bad, flush=True)

    def entry(p, src):
        return {"src": src, "id": p["id"], "title": p["title"], "year": p["year"],
                "venue": p["venue"], "authors": p["authors"],
                "links": {"paper": "https://arxiv.org/abs/" + p["id"], "code": ""},
                "abstract": p["abstract"], "summary": ""}

    pool = []
    for dom in CLASSICS:
        for aid, kw in CLASSICS[dom]:
            if aid in meta:
                pool.append(entry(meta[aid], dom))
        for aid, kw, doms in SHARED:
            if dom in doms and aid in meta:
                pool.append(entry(meta[aid], dom))
        for p in [x for x in raw if x["src"] == dom]:
            pool.append(p)
    json.dump(pool, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import collections
    print("pool", len(pool), collections.Counter(x["src"] for x in pool))


if __name__ == "__main__":
    main()
