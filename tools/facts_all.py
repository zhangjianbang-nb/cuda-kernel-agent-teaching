#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全领域 facts 抽取：7 领域 × 7 模块的所有批次共用一个 4 并发池，结束时按模块合并。

用法：python3 -I tools/facts_all.py [--workers 4] [--batch 3] [--domains moe,...]
"""
import argparse, concurrent.futures, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_facts as MF

DOMS = ["moe", "multimodal", "coding", "rl", "video", "image", "audio"]
MODS = ["directions", "algorithms", "theory", "stories", "exams", "book", "appendix"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", type=int, default=3)
    ap.add_argument("--domains", default="")
    args = ap.parse_args()
    doms = [d for d in (args.domains.split(",") if args.domains else DOMS) if d]
    jobs = []
    for dom in doms:
        for module in MODS:
            bp = os.path.join(ROOT, "content", "blueprint", dom, module + ".json")
            if not os.path.exists(bp):
                print(f"SKIP {dom}/{module}: 缺蓝图", flush=True); continue
            data = json.load(open(bp, encoding="utf-8"))
            items = data.get("book", {}).get("sections", []) if module == "book" else data.get(module, [])
            for i in range(0, len(items), args.batch):
                jobs.append((dom, module, items[i:i + args.batch]))
    print(f"jobs={len(jobs)} workers={args.workers}", flush=True)
    ok = fail = 0; t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(MF.gen_batch, d, m, b): (d, m, b) for d, m, b in jobs}
        for fut in concurrent.futures.as_completed(futs):
            d, m, b = futs[fut]
            try:
                st, info = fut.result()
            except Exception as e:
                st, info = "fail", str(e)[:160]
            if st in ("ok", "skip"): ok += 1
            elif st == "part": ok += 1
            else: fail += 1
            print(f"[{ok+fail}/{len(jobs)}] {st} {d}/{m} {info} {time.time()-t0:.0f}s", flush=True)
    # 合并
    for dom in doms:
        d = os.path.join(MF.OUT, dom)
        if not os.path.isdir(d): continue
        for module in MODS:
            merged = {}
            pat = re.compile(r"^%s-.+\.json$" % re.escape(module))
            for f in sorted(os.listdir(d)):
                if not pat.match(f): continue
                try:
                    for k, v in json.load(open(os.path.join(d, f), encoding="utf-8")).items(): merged[k] = v
                except Exception: pass
            if merged:
                json.dump(merged, open(os.path.join(d, module + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(f"merged {dom}/{module} {len(merged)}", flush=True)
    print(f"DONE ok={ok} fail={fail} elapsed={(time.time()-t0)/60:.1f}m", flush=True)

if __name__ == "__main__":
    main()
