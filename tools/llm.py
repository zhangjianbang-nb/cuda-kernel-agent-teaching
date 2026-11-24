#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared local-LLM call helper (18891, DeepSeek-V4.1-Flash)."""
import json, re, time, urllib.request
API = "http://127.0.0.1:18891/v1/chat/completions"
MODEL = "DeepSeek-V4.1-Flash-1017-TF"

def cjk(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))

def call(prompt, max_tokens=8192, temperature=0.55, tries=4, json_mode=False):
    prompt = prompt.replace("→", " 到 ")
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": False}}
    # 2026-11-14 实测：本引擎不支持 structured output（response_format / guided_*），
    # 传了会直接 400。JSON 模式只靠 prompt 约束，解析端负责兜底。
    _ = json_mode
    last = ""
    for i in range(tries):
        try:
            req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.loads(r.read())
            ch = d["choices"][0]
            return ch["message"]["content"], ch.get("finish_reason"), d.get("usage", {})
        except Exception as e:
            last = str(e)[:200]
            # token-length boundary bug: pad prompt to move off the boundary
            body["messages"][0]["content"] = prompt + "\n请开始。" + "。" * (i + 1)
            time.sleep(3 + 4 * i)
    raise RuntimeError("call failed: " + last)

def parse_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("no json object")
    return json.loads(s[i:j+1])
