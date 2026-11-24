#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract "usable facts" for non-paper modules (directions/algos/theory/stories/exams/book/appendix).

Input : content/blueprint/<domain>/<module>.json
Output: content/facts/<domain>/<module>.json   {item_id: {facts:[...], anchors:[...], pitfalls:[...]}}
"""
import argparse, concurrent.futures, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import llm

META = json.load(open(os.path.join(HERE, "domain_meta.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "content", "facts")

HEAD = """你是《CUDA Kernel Agent 工程全书》的资料整理员。本书只讲**kernel 生成、优化、验证、部署**四条线，不写训练配方与产品评测。
领域：{name}（{focus}）
写作语言：简体中文。所有事实必须具体到机制、数据口径或工程代价；禁止"很重要""效果显著"这类空话。
"""

ASK = {
 "directions": "为每个研究方向整理 8 条事实：①这个方向的历史起点与代表工作；②现有方案的具体不足；③三条技术路线的机制差异；④评测侧的具体做法（基准/基线/输入分布/指标）；⑤部署侧的具体做法（工具链/profile/CI/上线门）；⑥工程代价与规模瓶颈；⑦评测协议与常见指标；⑧仍未解决的开放问题。",
 "algorithms": "为每个方法整理 8 条事实：①它解决的具体问题；②机制步骤（按一次 kernel 生成/优化/验证的流动顺序）；③核心评分/时延/显存/误差/奖励公式与各项含义；④负载与评测配方（模型/算子/shape/基线/输入分布/指标）；⑤部署配方（Triton/CuTe/PTX、profile 工具、编译环境、CI）；⑥稳定性技巧与失败模式；⑦与相邻方法的差别；⑧适用边界与规模上限。",
 "theory": "为每张理论卡整理 6 条事实：①一句话直觉；②公式各项的物理/统计含义；③推导的关键一步；④适用边界与失效条件；⑤它在 kernel 评测或容量决策中的具体用途；⑥常见误用与后果。",
 "stories": "为每个故事整理 5 条事实：①世界设定中可复用的具体细节；②角色与技术概念的一一映射；③冲突升级的四个节点；④每个技术机制的「翻译」说法；⑤类比在哪里不像（边界）。",
 "exams": "为每道题整理 4 条事实：①这道题真正要考的理解点；②正确解法的要点链；③最常见的错误答案与为什么错；④题目里可计算/可推导的量与口径。",
 "book": "为每一卷整理 6 条事实：①本卷的输入与产出；②本卷要做的关键决策；③涉及的评测/生成/验证环节；④涉及的部署配方（工具链/profile/CI/上线门）；⑤与前后卷的依赖关系；⑥本卷最容易讲错的地方。",
 "appendix": "为每个附录条目整理 5 条事实：①条目的准确定义；②分类维度；③速查表应包含的列；④工程阈值或经验数字（没有就写「未给出」）；⑤最常见的踩坑。",
}

REQ = """
输出严格 JSON（不要解释、不要 markdown 围栏）：
{"<item_id>": {"facts": ["每条 60–140 字"], "anchors": ["材料中真实出现的数字，没有就空数组"], "pitfalls": ["2–3 条工程失败模式，每条≥20字"]}}
要求：
1. 每个条目 facts 条数按上面的要求；每条必须能独立支撑一段写作，不许互相重复。
2. 只使用给定材料与领域常识；不得编造论文、作者、年份、机构；数字没有就写"未给出"。
3. 公式用 $$...$$（KaTeX），不得用 Unicode 符号冒充。
4. 材料里的 key_papers 只能原样引用，不得新增不存在的论文 id。
"""

def material(module, item):
    if module == "directions":
        return (f"方向：{item.get('name')}（{item.get('name_en','')}）\n核心问题：{item.get('question')}\n"
                f"为什么重要：{item.get('why')}\n关键技术：{'；'.join(item.get('core_tech') or [])}\n"
                f"关键论文：{'；'.join(item.get('key_papers') or [])}\n近年进展：{item.get('recent')}\n"
                f"挑战：{'；'.join(item.get('challenges') or [])}")
    if module == "algorithms":
        return (f"算法：{item.get('name')}（{item.get('year')}）\n问题：{item.get('problem')}\n"
                f"一句话机制：{item.get('idea')}\n步骤：{'；'.join(item.get('flow') or [])}\n"
                f"优点：{'；'.join(item.get('pros') or [])}\n代价：{'；'.join(item.get('cons') or [])}\n"
                f"论文：{'；'.join(item.get('papers') or [])}")
    if module == "theory":
        return (f"理论：{item.get('title')}\n一句话：{item.get('plain')}\n公式：{item.get('formula')}\n"
                f"变量：{'；'.join('%s=%s' % (v.get('sym'), v.get('meaning')) for v in item.get('variables') or [])}\n"
                f"失效条件：{'；'.join(item.get('limits') or [])}")
    if module == "stories":
        return (f"故事：{item.get('title')}\n场景：{item.get('scene')}\n"
                f"角色：{'；'.join('%s→%s' % (r.get('role'), r.get('maps_to')) for r in item.get('roles') or [])}\n"
                f"剧情节点：{'；'.join(item.get('steps') or [])}\n覆盖：{item.get('covers')}\n边界：{item.get('boundaries')}")
    if module == "exams":
        return (f"题目：{item.get('question')}\n难度层：L{item.get('level')}\n所属模块：{item.get('module')}\n"
                f"答案要点：{'；'.join(item.get('answer_outline') or [])}")
    if module == "book":
        return (f"卷：{item.get('title')}\n副标题：{item.get('subtitle')}\n本卷内容：{item.get('note')}\n"
                f"故事映射：{'；'.join(item.get('story_map') or [])}")
    if module == "appendix":
        return f"附录：{item.get('title')}（{item.get('kind')}）\n说明：{item.get('content')}"
    return json.dumps(item, ensure_ascii=False)

def gen_batch(dom, module, batch):
    ids = [it.get("id") for it in batch]
    out_path = os.path.join(OUT, dom, module + ".json")
    # 每批写自己的文件，避免同一模块多批并发写同一 JSON 丢更新；主进程结束时合并。
    batch_path = os.path.join(OUT, dom, "%s-%s.json" % (module, re.sub(r"[^A-Za-z0-9_-]", "_", str(batch[0].get("id")))))
    done = {}
    for p in (out_path, batch_path):
        if os.path.exists(p):
            try:
                for k, v in json.load(open(p, encoding="utf-8")).items(): done[k] = v
            except Exception: pass
    todo = [it for it in batch if it.get("id") not in done]
    if not todo: return ("skip", ",".join(ids))
    lines = [HEAD.format(**META[dom])]
    lines.append("任务：" + ASK[module])
    for it in todo:
        lines.append("---\n" + material(module, it))
    lines.append("输出条目 id 列表：" + "、".join(it.get("id") for it in todo))
    lines.append(REQ)
    prompt = "\n".join(lines)
    last = ""
    for attempt in range(3):
        try:
            txt, fin, usage = llm.call(prompt, max_tokens=8192, temperature=0.45, json_mode=True)
            d = llm.parse_json(txt)
            got = 0
            for it in todo:
                v = d.get(it.get("id"))
                if isinstance(v, dict) and len(v.get("facts") or []) >= 3:
                    done[it.get("id")] = v; got += 1
            os.makedirs(os.path.dirname(batch_path), exist_ok=True)
            json.dump(done, open(batch_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return ("ok" if got == len(todo) else "part", f"{got}/{len(todo)}")
        except Exception as e:
            last = str(e)[:160]
            prompt = prompt + f"\n\n上一次输出不合格（{last}）。请只输出合法 JSON。"
            time.sleep(2 + attempt * 3)
    return ("fail", last)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True); ap.add_argument("--module", required=True)
    ap.add_argument("--workers", type=int, default=3); ap.add_argument("--batch", type=int, default=3)
    args = ap.parse_args()
    bp = os.path.join(ROOT, "content", "blueprint", args.domain, args.module + ".json")
    data = json.load(open(bp, encoding="utf-8"))
    if args.module == "book":
        items = data.get("book", {}).get("sections", [])
    else:
        items = data.get(args.module, [])
    batches = [items[i:i + args.batch] for i in range(0, len(items), args.batch)]
    print(f"items={len(items)} batches={len(batches)} workers={args.workers}", flush=True)
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(gen_batch, args.domain, args.module, b): b for b in batches}
        for fut in concurrent.futures.as_completed(futs):
            st, info = fut.result()
            print(f"{st} {info} {time.time()-t0:.1f}s", flush=True)
    # 合并本模块所有批次文件
    merged = {}
    d = os.path.join(OUT, args.domain)
    pat = re.compile(r"^%s-.+\.json$" % re.escape(args.module))
    for f in sorted(os.listdir(d)):
        if not pat.match(f): continue
        try:
            for k, v in json.load(open(os.path.join(d, f), encoding="utf-8")).items(): merged[k] = v
        except Exception: pass
    if merged:
        json.dump(merged, open(os.path.join(d, args.module + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"merged {len(merged)} -> {args.module}.json", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
