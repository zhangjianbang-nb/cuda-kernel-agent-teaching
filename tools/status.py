#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""24/7 生成进度报告：逐领域逐模块的完成数、字数、速率、ETA。

用法：python3 -I tools/status.py [--json]
数据源：content/tasks/<dom>.json（任务表）+ content/long/<dom>/<module>/*.html（产出）
+ content/gen-progress.jsonl（最近速率）。
"""
import argparse, json, os, re, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMS = ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
MODS = ["papers", "algorithms", "theory", "directions", "stories", "exams", "book", "appendix"]

def cjk(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))

def read_cjk(p):
    try:
        return cjk(open(p, encoding="utf-8").read())
    except Exception:
        return 0

def rate_recent(minutes=90):
    p = os.path.join(ROOT, "content", "gen-progress.jsonl")
    if not os.path.exists(p): return 0.0, 0
    now = time.time(); n = 0
    for line in open(p, encoding="utf-8"):
        try:
            d = json.loads(line)
            ts = time.mktime(time.strptime(d["ts"], "%Y-%m-%d %H:%M:%S"))
            if now - ts <= minutes * 60 and d.get("status") == "ok":
                n += 1
        except Exception:
            pass
    return n / (minutes / 60.0), n

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = []; grand_tasks = grand_done = grand_cjk = 0
    for dom in DOMS:
        tp = os.path.join(ROOT, "content", "tasks", dom + ".json")
        if not os.path.exists(tp):
            rows.append({"dom": dom, "tasks": 0, "done": 0, "cjk": 0, "mods": {}})
            continue
        tasks = json.load(open(tp, encoding="utf-8"))
        mods = {}
        dt = dd = dc = 0
        for m in MODS:
            ts = [t for t in tasks if t["module"] == m]
            done = 0; cj = 0
            for t in ts:
                c = read_cjk(os.path.join(ROOT, t["out"]))
                cj += c
                if c >= 3000: done += 1
            mods[m] = {"tasks": len(ts), "done": done, "cjk": cj}
            dt += len(ts); dd += done; dc += cj
        rows.append({"dom": dom, "tasks": dt, "done": dd, "cjk": dc, "mods": mods})
        grand_tasks += dt; grand_done += dd; grand_cjk += dc
    r, n = rate_recent()
    left = grand_tasks - grand_done
    eta_h = left / r if r > 0 else 0
    if args.json:
        print(json.dumps({"rows": rows, "tasks": grand_tasks, "done": grand_done,
                          "cjk": grand_cjk, "rate_per_h": round(r, 1), "left": left,
                          "eta_h": round(eta_h, 1)}, ensure_ascii=False))
        return
    print(f"总任务 {grand_tasks}  完成 {grand_done} ({grand_done/max(grand_tasks,1)*100:.1f}%)  "
          f"汉字 {grand_cjk:,}  近90分钟速率 {r:.1f} 段/h  剩余 {left} 段  ETA {eta_h:.1f} h")
    for x in rows:
        if not x["tasks"]: continue
        detail = " ".join(f"{m}:{v['done']}/{v['tasks']}" for m, v in x["mods"].items() if v["tasks"])
        print(f"  {x['dom']:10s} {x['done']:4d}/{x['tasks']:<4d} 汉字 {x['cjk']:>9,}  {detail}")

if __name__ == "__main__":
    main()
