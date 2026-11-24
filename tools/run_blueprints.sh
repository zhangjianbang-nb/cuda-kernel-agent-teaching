#!/usr/bin/env bash
set -u
cd /home/whu/workspace/ai_workspace/cuda-kernel-agent-teaching-20261122
LOG=content/blueprint-run.log
: > "$LOG"
run() {
  echo "=== $(date '+%H:%M:%S') $* ===" | tee -a "$LOG"
  python3 -I tools/make_blueprint.py "$@" >> "$LOG" 2>&1
  echo "exit=$?" | tee -a "$LOG"
}
run --domain cuda --module directions
run --domain cuda --module algorithms --start 0 --count 14
run --domain cuda --module algorithms --start 14 --count 14
run --domain cuda --module theory --start 0 --count 8
run --domain cuda --module theory --start 8 --count 7
run --domain cuda --module stories
run --domain cuda --module book
run --domain cuda --module appendix
echo "=== DONE $(date '+%H:%M:%S') ===" | tee -a "$LOG"
