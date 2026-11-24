#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对单个片段复跑一次生成，打印长度/闭合/finish_reason 诊断，不写文件。"""
import importlib.util, json, os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec=importlib.util.spec_from_file_location("gl",os.path.join(ROOT,"tools","gen_long.py"))
gl=importlib.util.module_from_spec(spec); spec.loader.exec_module(gl)
dom=sys.argv[1]; tid=sys.argv[2]
tasks=json.load(open(os.path.join(ROOT,"content","tasks",dom+".json"),encoding="utf-8"))
t=next(x for x in tasks if x["id"]==tid)
s,fin=gl.call(gl.build_prompt(t))
s=gl.clean(s); ok,bad=gl.balanced(s)
print("finish=%s cjk=%d ok=%s bad=%s len=%d"%(fin,gl.cjk(s),ok,bad,len(s)))
print("---head---"); print(s[:600])
print("---tail---"); print(s[-400:])
open(os.path.join(ROOT,"shots","diag-%s.html"%tid),"w",encoding="utf-8").write(s)
