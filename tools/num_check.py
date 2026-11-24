#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数字白名单扫描：正文里的阿拉伯数字必须能在任务事实/论文卡锚点里找到。

背景（2026-11-14 ChatGPT 评审）：LLM 整理论文时最容易出的错不是全编，而是把
「训练数据规模 / 评测规模」「参数量 / 激活参数量」「步数 / epoch」讲串。生成后
把正文数字与允许集合比对，输出报告供抽样复核；默认只报告不阻断（避免年份、
序数等误报拖死流水线）。

用法：python3 -I tools/num_check.py [--domain moe] [--module papers] [--top 30]
输出：content/num-report.json
"""
import argparse, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?")

def nums(s):
    out = set()
    for m in NUM.finditer(s or ""):
        t = m.group(0).replace(",", "")
        out.add(t)
        # 1.2T / 70B / 128K 这类带单位的数字，允许基数本身
        base = re.match(r"\d+(?:\.\d+)?", t)
        if base: out.add(base.group(0))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="")
    ap.add_argument("--module", default="")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()
    doms = [args.domain] if args.domain else ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
    report = {}
    for dom in doms:
        tp = os.path.join(ROOT, "content", "tasks", dom + ".json")
        if not os.path.exists(tp): continue
        tasks = json.load(open(tp, encoding="utf-8"))
        allow = {}
        for t in tasks:
            allow[t["id"]] = nums(t.get("facts", ""))
        files = glob.glob(os.path.join(ROOT, "content", "long", dom, "*", "*.html"))
        bad = []
        for f in files:
            if args.module and ("/%s/" % args.module) not in f.replace("\\", "/"): continue
            tid = os.path.basename(f)[:-5]
            # 片段文件名 <item>-pN，任务 id 是 <module>-<item>-pN
            cand = [k for k in allow if k.endswith("-" + tid)]
            if not cand: continue
            a = allow[cand[0]]
            text = open(f, encoding="utf-8").read()
            text = re.sub(r"<[^>]+>", " ", text)
            # 假设句里的数字是教学示例（"设想 2048 卡集群""把专家数从 64 改成 128"），
            # 不是对论文结果的断言；先按句剔除，剩下的才是需要核对的事实数字。
            keep = [x for x in re.split(r"(?<=[。；！？])", text)
                    if not re.search(r"设想|假设|举例|比如|例如|如果|若|打个比方|想象|假设性", x)]
            seen = nums("".join(keep))
            # 年份与个位数（「三步」「两种」）不算事实数字，避免误报淹没报告。
            unknown = [x for x in seen - a
                       if not re.fullmatch(r"(?:19|20)\d\d", x) and not re.fullmatch(r"\d", x)]
            unknown.sort(key=lambda x: (-len(x), x))
            if unknown:
                bad.append({"file": os.path.relpath(f, ROOT), "unknown": unknown[:20], "n": len(unknown)})
        bad.sort(key=lambda x: -x["n"])
        report[dom] = bad
        print("%s: files=%d flagged=%d" % (dom, len(files), len(bad)), flush=True)
        for b in bad[:args.top]:
            print("  %s  %d 个未授权数字：%s" % (b["file"], b["n"], "、".join(b["unknown"][:10])), flush=True)
    json.dump(report, open(os.path.join(ROOT, "content", "num-report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
