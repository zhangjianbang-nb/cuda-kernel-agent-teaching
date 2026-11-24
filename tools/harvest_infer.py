#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harvest inference-focused arXiv papers per domain -> content/paper-pool.json.

Only metadata + abstract; cards (LLM-written) come later. Dedupe by arXiv id.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "content", "paper-pool.json")
UA = "Mozilla/5.0 (research-teaching-site; contact whdx072018@foxmail.com)"
NS = {"a": "http://www.w3.org/2005/Atom"}

QUERIES = {
 "moe": [
  'abs:"mixture of experts" AND abs:"inference"',
  'abs:"mixture-of-experts" AND abs:"serving"',
  'abs:"expert parallelism" AND abs:"inference"',
  'abs:"grouped gemm"',
  'abs:"MoE" AND abs:"kernel"',
  'abs:"sparse activation" AND abs:"inference"',
 ],
 "multimodal": [
  'abs:"multimodal" AND abs:"inference"',
  'abs:"vision-language model" AND abs:"serving"',
  'abs:"vision encoder" AND abs:"efficient"',
  'abs:"visual token" AND abs:"compression"',
  'abs:"multimodal" AND abs:"quantization"',
  'abs:"vision-language" AND abs:"latency"',
 ],
 "coding": [
  'abs:"code generation" AND abs:"inference"',
  'abs:"code completion" AND abs:"latency"',
  'abs:"speculative decoding" AND abs:"code"',
  'abs:"repository-level" AND abs:"context"',
  'abs:"constrained decoding" AND abs:"structured"',
  'abs:"code LLM" AND abs:"serving"',
 ],
 "rl": [
  'abs:"reinforcement learning" AND abs:"rollout"',
  'abs:"RLHF" AND abs:"inference"',
  'abs:"policy optimization" AND abs:"throughput"',
  'abs:"reward model" AND abs:"inference"',
  'abs:"asynchronous" AND abs:"reinforcement learning" AND abs:"training"',
  'abs:"LLM" AND abs:"rollout" AND abs:"engine"',
 ],
 "video": [
  'abs:"video generation" AND abs:"inference"',
  'abs:"video diffusion" AND abs:"acceleration"',
  'abs:"autoregressive video" AND abs:"generation"',
  'abs:"video generation" AND abs:"distillation"',
  'abs:"temporal attention" AND abs:"efficient"',
  'abs:"video generation" AND abs:"latency"',
 ],
 "image": [
  'abs:"diffusion" AND abs:"inference acceleration"',
  'abs:"text-to-image" AND abs:"latency"',
  'abs:"diffusion transformer" AND abs:"quantization"',
  'abs:"consistency model" AND abs:"sampling"',
  'abs:"image generation" AND abs:"serving"',
  'abs:"diffusion" AND abs:"few-step"',
 ],
 "audio": [
  'abs:"text-to-speech" AND abs:"latency"',
  'abs:"speech" AND abs:"inference"',
  'abs:"neural audio codec"',
  'abs:"streaming" AND abs:"speech synthesis"',
  'abs:"speech recognition" AND abs:"quantization"',
  'abs:"audio generation" AND abs:"efficient"',
 ],
}
GENERIC = [
 'abs:"Blackwell" AND abs:"GPU"',
 'abs:"NVFP4"',
 'abs:"FP4" AND abs:"inference"',
 'abs:"TensorRT-LLM"',
 'abs:"tcgen05"',
]
KEY = {
 "moe": ("mixture", "expert", "routing", "sparse", "moe"),
 "multimodal": ("multimodal", "vision-language", "vision encoder", "visual token", "vlm"),
 "coding": ("code", "program", "repository", "compiler", "software"),
 "rl": ("reinforcement", "reward", "policy", "rollout", "rlhf"),
 "video": ("video", "temporal", "frame"),
 "image": ("image", "diffusion", "text-to-image", "visual"),
 "audio": ("speech", "audio", "voice", "music", "tts", "codec"),
}
SERVE = ("inference", "serving", "latency", "throughput", "quantization", "kernel",
         "memory", "cache", "batch", "scheduling", "deployment", "gpu", "fp4", "fp8",
         "acceleration", "distillation", "efficient", "cost")


def norm(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def fetch(q, max_results=60):
    url = ("https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q)
           + "&start=0&max_results=%d&sortBy=relevance" % max_results)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
            return ET.fromstring(data)
        except Exception as e:
            print("retry", attempt, q, e, file=sys.stderr)
            time.sleep(5)
    return None


def parse(root):
    out = []
    for e in root.findall("a:entry", NS):
        aid = (e.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1]
        aid = re.sub(r"v\d+$", "", aid)
        title = re.sub(r"\s+", " ", e.findtext("a:title", "", NS) or "").strip()
        summ = re.sub(r"\s+", " ", e.findtext("a:summary", "", NS) or "").strip()
        pub = e.findtext("a:published", "", NS) or ""
        jr = e.findtext("a:journal_ref", "", NS) or ""
        authors = [a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)]
        out.append({"id": aid, "title": title, "abstract": summ, "year": int(pub[:4] or 0),
                    "venue": jr.strip(), "authors": [a for a in authors if a][:12]})
    return out


def score(p, dom):
    t = norm(p["title"] + " " + p["abstract"])
    ks = sum(1 for k in KEY[dom] if k in t)
    ss = sum(1 for k in SERVE if k in t)
    return ks * 3 + ss


def main():
    pool = []
    seen = set()
    per = {}
    for dom, qs in QUERIES.items():
        cands = {}
        for q in qs:
            root = fetch(q)
            if root is None:
                continue
            for p in parse(root):
                if p["id"] in cands:
                    continue
                t = norm(p["title"] + " " + p["abstract"])
                if not any(k in t for k in KEY[dom]):
                    continue
                cands[p["id"]] = p
            time.sleep(3)
        ranked = sorted(cands.values(), key=lambda p: (score(p, dom), p["year"]), reverse=True)
        # 至少保留 12 篇近三年，其余按分数
        recent = [p for p in ranked if p["year"] >= 2023][:20]
        pick = []
        for p in recent:
            pick.append(p)
        for p in ranked:
            if len(pick) >= 70:
                break
            if p not in pick:
                pick.append(p)
        per[dom] = len(pick)
        for p in pick:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            pool.append({"src": dom, "id": p["id"], "title": p["title"], "year": p["year"],
                         "venue": p["venue"], "authors": p["authors"],
                         "links": {"paper": "https://arxiv.org/abs/" + p["id"], "code": ""},
                         "abstract": p["abstract"], "summary": ""})
        print(dom, len(pick), "pool", len(pool), flush=True)
    # generic Blackwell/kernel papers: assign to domains by keyword match, else moe
    for q in GENERIC:
        root = fetch(q)
        if root is None:
            continue
        for p in parse(root):
            if p["id"] in seen:
                continue
            t = norm(p["title"] + " " + p["abstract"])
            doms = [d for d in QUERIES if any(k in t for k in KEY[d])]
            dom = doms[0] if doms else "moe"
            seen.add(p["id"])
            pool.append({"src": dom, "id": p["id"], "title": p["title"], "year": p["year"],
                         "venue": p["venue"], "authors": p["authors"],
                         "links": {"paper": "https://arxiv.org/abs/" + p["id"], "code": ""},
                         "abstract": p["abstract"], "summary": ""})
        time.sleep(3)
    json.dump(pool, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("total", len(pool), per)


if __name__ == "__main__":
    main()
