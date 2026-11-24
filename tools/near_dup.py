#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""近重复段落扫描：同一领域内跨条目的段落级 MinHash-LSH，报告 Jaccard ≥ 阈值的段落对。

背景（2026-11-14 ChatGPT 评审）：精确 dup_scan 只能抓复制粘贴；6700 个片段真正的
风险是「同一知识换角度扩写」。这里用 8-gram + MinHash + LSH 找候选，再算精确
Jaccard，输出报告供抽样复核（默认只报告，不阻断）。

用法：python3 -I tools/near_dup.py [--domain moe] [--threshold 0.35] [--top 20]
输出：content/near-dup-report.json
"""
import argparse, glob, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r"[\u4e00-\u9fff]")
TAG = re.compile(r"<[^>]+>")
SEEDS = [b"nd%d" % i for i in range(12)]
BANDS = 4

def paragraphs(html):
    txt = TAG.sub("\n", html or "")
    out = []
    for p in re.split(r"\n+", txt):
        p = re.sub(r"\s+", "", p)
        if len(p) < 150: continue
        if len(CJK.findall(p)) / max(1, len(p)) < 0.45: continue
        out.append(p)
    return out

def shingles(p):
    return {p[i:i + 8] for i in range(0, len(p) - 7, 2)}

def signature(sh):
    return tuple(min(hashlib.blake2b(s, digest_size=8).digest() for s in sh) for _ in [0]) if False else tuple(
        min(int.from_bytes(hashlib.blake2b(seed + s.encode(), digest_size=8).digest(), "big") for s in sh)
        for seed in SEEDS)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    doms = [args.domain] if args.domain else ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
    report = {}
    for dom in doms:
        base = os.path.join(ROOT, "content", "long", dom)
        if not os.path.isdir(base):
            continue
        paras = []
        for f in glob.glob(os.path.join(base, "*", "*.html")):
            mod = os.path.basename(os.path.dirname(f))
            item = os.path.basename(f)[:-5].rsplit("-p", 1)[0]
            html = open(f, encoding="utf-8").read()
            for i, p in enumerate(paragraphs(html)):
                sh = shingles(p)
                if len(sh) < 30: continue
                sig = signature(sh)
                paras.append({"key": "%s/%s#%d" % (mod, item, i), "sh": sh, "sig": sig, "p": p[:90]})
        buckets = {}
        for idx, x in enumerate(paras):
            for b in range(BANDS):
                key = tuple(x["sig"][b * 3:(b + 1) * 3])
                buckets.setdefault(key, []).append(idx)
        seen = set(); pairs = []
        for ids in buckets.values():
            if len(ids) < 2: continue
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    if (a, b) in seen: continue
                    seen.add((a, b))
                    inter = len(paras[a]["sh"] & paras[b]["sh"])
                    if not inter: continue
                    jac = inter / len(paras[a]["sh"] | paras[b]["sh"])
                    if jac >= args.threshold:
                        pairs.append({"a": paras[a]["key"], "b": paras[b]["key"], "j": round(jac, 3),
                                      "a_text": paras[a]["p"], "b_text": paras[b]["p"]})
        pairs.sort(key=lambda x: -x["j"])
        report[dom] = pairs
        print("%s: paragraphs=%d near-dup pairs=%d" % (dom, len(paras), len(pairs)), flush=True)
        for x in pairs[:args.top]:
            print("  %.3f  %s  ~  %s" % (x["j"], x["a"], x["b"]), flush=True)
    json.dump(report, open(os.path.join(ROOT, "content", "near-dup-report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
