#!/usr/bin/env bash
# 终装配：数据 → 长文注入 → 分片打包 → manifest/totals → 断言 → e2e
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -I tools/build_data.py --domain cuda
python3 -I tools/build_long.py --domain cuda
python3 -I tools/bundle_split.py --domains cuda
python3 -I - <<'PY'
import sys
sys.path.insert(0, "tools")
import bundle_data as B
B.build_manifest("site", ["cuda"], quiet=False)
print("totals:", B.write_totals("site", ["cuda"]))
PY
python3 -I tools/assert_all.py
node tools/e2e_site.js
