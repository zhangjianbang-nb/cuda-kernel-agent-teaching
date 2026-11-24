#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽检长文片段：格式、占位词、套话、重复、公式配对。"""
import glob,re,sys,collections
files=sorted(glob.glob("content/long/*/*/*.html"))
issues=collections.Counter(); samples=collections.defaultdict(list)
sents=collections.Counter()
for f in files:
 s=open(f,encoding="utf-8").read()
 for pat,name in [(r"<pre\b","pre"),(r"见正文","placeholder"),(r"大概|可能|一般来说","hedge"),(r"```","fence"),(r"<script","script")]:
  if re.search(pat,s): issues[name]+=1; samples[name].append(f)
 if s.count("$$")%2: issues["odd_dollar"]+=1; samples["odd_dollar"].append(f)
 for a,b in [("<p","</p>"),("<h3","</h3>"),("<table","</table>"),("<ul","</ul>"),("<div class=\"formula\"","</div>")]:
  if s.count(a)!=s.count(b): issues["unbalanced_"+a.strip("<")]+=1; samples["unbalanced_"+a.strip("<")].append(f)
 for x in re.split(r"[。！？]",re.sub(r"<[^>]+>","",s)):
  x=x.strip()
  if len(x)>=40: sents[x]+=1
dups=[(k,v) for k,v in sents.items() if v>=3]
print("files",len(files))
for k,v in issues.items(): print("ISSUE",k,v,samples[k][:3])
print("repeated sentences (>=3):",len(dups))
for k,v in sorted(dups,key=lambda x:-x[1])[:8]: print(" DUP",v,k[:60])
