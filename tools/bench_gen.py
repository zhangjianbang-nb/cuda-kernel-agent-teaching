#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benchmark engine throughput: N concurrent long-form generations."""
import json, re, sys, time, urllib.request, concurrent.futures
API="http://127.0.0.1:18891/v1/chat/completions"; MODEL="DeepSeek-V4.1-Flash-1017-TF"
PROMPT = """你是《训练方法全书》的技术作者，读者是有工程背景的中文读者。只输出 HTML 片段。
用 <h3>一 · 小标题</h3> 组织 4–6 节；正文用 <p>；表格用 <table class="mini"><thead>…</thead><tbody>…</tbody></table>；公式用 <div class="formula">$$…$$</div>。
目标 3600 个汉字，不得少于 3200 字。信息密度高，不写套话。
每个部分至少出现：一个具体机制、一个公式或伪代码思路、一个系统代价或失败模式、一个具体例子。
不编造实验数字；只使用给定事实中的数字，没有就定性表述。
本次任务：写《DeepSeek-V3 训练方案》第 1/6 部分：数据工程——预训练语料配比、清洗、去重、课程安排。
可用事实：DeepSeek-V3 是 671B 总参数、37B 激活的 MoE 模型，14.8T tokens 预训练，采用 FP8 混合精度、MLA、DeepSeekMoE 架构、无辅助损失的负载均衡、多 token 预测（MTP）。语料以中英文为主，代码与数学占比提升；长上下文两阶段扩展（32K→128K）。
末尾加 <p class="paper-line">对应：alg-deepseek-v3-p1 · 第 1/6 部分</p>"""
def one(i):
    body={"model":MODEL,"messages":[{"role":"user","content":PROMPT}],"max_tokens":8192,"temperature":0.65,
          "chat_template_kwargs":{"enable_thinking":False}}
    req=urllib.request.Request(API,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    t0=time.time()
    with urllib.request.urlopen(req,timeout=900) as r: d=json.loads(r.read())
    ch=d["choices"][0]; s=ch["message"]["content"]; fin=ch.get("finish_reason")
    cjk=len(re.findall(r"[\u4e00-\u9fff]",s))
    return i, cjk, len(s), time.time()-t0, fin, d.get("usage",{})
def run(n):
    t0=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        res=list(ex.map(one,range(n)))
    el=time.time()-t0
    print(f"workers={n} elapsed={el:.1f}s")
    for i,cjk,ch,dt,fin,usage in res:
        print(f"  #{i} cjk={cjk} chars={ch} dt={dt:.1f}s fin={fin} usage={usage.get('completion_tokens')}")
    tot=sum(r[1] for r in res); vis=tot*1.386
    print(f"  throughput: {tot/el:.1f} cjk/s = {tot/el*3600:.0f} cjk/h = {vis/el*3600/1e6:.2f}M visible/h")
if __name__=="__main__":
    run(int(sys.argv[1]) if len(sys.argv)>1 else 4)
