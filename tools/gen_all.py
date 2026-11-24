#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按领域顺序跑 gen_long（4 并发），单进程 24/7 长跑入口。

用法：python3 -I tools/gen_all.py [--workers 4] [--domains moe,rl,...]
日志：content/gen.log（追加），每个领域起止各一行。
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOMS = ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
MIN_CJK = int(os.environ.get("GEN_MIN_CJK", "2900"))


def count_missing(dom):
    """缺口 = 没落盘或汉字数 < MIN_CJK 的片段数（与 gen_long 的 todo 判据一致）。"""
    tp = os.path.join(ROOT, "content", "tasks", dom + ".json")
    if not os.path.exists(tp):
        return 0
    miss = 0
    for t in json.load(open(tp, encoding="utf-8")):
        f = os.path.join(ROOT, t["out"])
        if not os.path.exists(f):
            miss += 1
            continue
        s = open(f, encoding="utf-8").read()
        if len(re.findall(r"[\u4e00-\u9fff]", s)) < MIN_CJK:
            miss += 1
    return miss

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--domains", default="")
    args = ap.parse_args()
    doms = [d for d in (args.domains.split(",") if args.domains else DOMS) if d]
    logp = os.path.join(ROOT, "content", "gen.log")
    for dom in doms:
        tp = os.path.join(ROOT, "content", "tasks", dom + ".json")
        if not os.path.exists(tp):
            with open(logp, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SKIP {dom}: 缺任务表\n")
            continue
        marker = os.path.join(ROOT, "content", "finalized", dom + ".done")
        if os.path.exists(marker):
            # 已 finalize 的领域不能再跑：moe 有 11 段是「内容封顶」条目（2400–2900 字），
            # 重跑会按 2900 门槛把它们重刷掉。finalize_domain.sh 成功时写这个标记。
            with open(logp, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SKIP {dom}: 已 finalize\n")
            continue
        with open(logp, "a", encoding="utf-8") as f:
            f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} START {dom} workers={args.workers} =====\n")
        cmd = [sys.executable, "-I", os.path.join(HERE, "gen_long.py"),
               "--domain", dom, "--workers", str(args.workers)]
        # 每轮跑完再补缺口：3 次尝试里失败/偏短的片段不会落盘，gen_long 下一轮只挑缺口，
        # 最多补 3 轮（2026-11-16 实测 coding 单轮失败率 ~4%，靠补跑收敛）。
        for rnd in range(1, 4):
            with open(logp, "a", encoding="utf-8") as f:
                rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)
            miss = count_missing(dom)
            with open(logp, "a", encoding="utf-8") as f:
                f.write(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} END {dom} round={rnd} rc={rc} 缺口={miss} =====\n")
            if miss == 0:
                break

if __name__ == "__main__":
    main()
