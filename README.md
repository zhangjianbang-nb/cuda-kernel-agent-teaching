# CUDA Kernel Agent 工程全书

一个**纯静态、零后端、零外部请求**的教学站：讲清楚「可信的 GPU kernel agent」是怎么被造出来、
怎么被评测、怎么被反馈修正、怎么被验证、又怎么被送上线的。

- 内容规模：**约 325 万可见字符**（`site/data/totals.js` 为准，随生成持续增长）
- 页面：**221 页**，覆盖论文、算法、理论、工程方向、长篇故事、考题、全书、附录 8 大模块
- 图表：**179 张内联静态 SVG**（无 Mermaid 运行时、无外链图片）
- 公式：KaTeX **本地 vendor**（`site/vendor/katex/`），离线可用
- 路由：hash 路由（`#/cuda/...`），任何静态托管都能直接打开

## 目录结构

```
site/                 发布目录（直接部署这一个目录即可）
  index.html          单页入口
  data/manifest.js    页面清单与分片索引
  data/totals.js      全站字数统计
  data/domains/cuda/  按条目拆分的数据（论文/算法/理论/方向/故事/考题/全书/附录）
  data/core.js        运行时
  data/sec-*.js       目录分片（懒加载）
  data/body-*.js      正文分片（懒加载）
  vendor/katex/       本地公式渲染器
tools/                内容生成与装配流水线（Python + Node）
  gen_long.py         长文生成器（本地 OpenAI 兼容端点）
  build_data.py       数据装配
  build_long.py       长文注入
  bundle_split.py     分片打包
  assert_all.py       可编程断言（21 项）
  e2e_site.js         端到端路由与字数校验
  figs.py / svgkit.py 静态 SVG 图表生成
content/              生成过程的中间产物（蓝图/卡片/任务/长文片段）
```

## 本地预览

```bash
cd site
python3 -m http.server 8899
# 打开 http://127.0.0.1:8899/
```

（`file://` 直开也可用，因为所有资源都是相对路径且无外部请求。）

## 重建

```bash
bash tools/build_all.sh
```

依次执行：数据装配 → 长文注入 → 分片打包 → manifest/totals → 断言 → 端到端测试。

## 内容原则

- 所有结论给出**失效条件**与**适用边界**，不写「大概/可能」式糊弄。
- 论文条目为**摘要级**（页面内已自曝），算法与理论条目给出可复现的步骤与验收口径。
- 图表全部为手写 SVG 生成器产出，不依赖任何前端图表库。

## 许可

内容为学习与研究用途整理，引用论文版权归原作者。代码部分 MIT。
