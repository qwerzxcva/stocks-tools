#!/bin/bash
# Multi-repo monitor loop: every 15 min during A-share session (13:00-15:00 CST).
# Refreshes pools/snapshot, runs monitor, commits+pushes live repo + hub.
set -u
HUB="${STOCKS_HUB:-$HOME/workspace/stocks}"
LIVE="$HUB/data-live"
TOOLS="$HUB/tools-repo"
export STOCKS_ROOT="$TOOLS" STOCKS_LIVE="$LIVE/data" STOCKS_ANA="$HUB/analysis"
LOG=/tmp/monitor.log

cycle() {
  local tag; tag=$(TZ=Asia/Shanghai date +%H:%M)
  echo "[$tag] refresh pools + snapshot" | tee -a "$LOG"
  python3 "$TOOLS/tools/refresh_pool.py" >> "$LOG" 2>&1
  echo "[$tag] monitor snapshot" | tee -a "$LOG"
  python3 "$TOOLS/tools/monitor.py" >> "$LOG" 2>&1
  # live repo
  cd "$LIVE" && git add -A >> "$LOG" 2>&1
  git commit -m "monitor $(TZ=Asia/Shanghai date +%H:%M) snapshot" -q >> "$LOG" 2>&1 || true
  git -c http.version=HTTP/1.1 push origin main >> "$LOG" 2>&1 || true
  # hub repo
  cd "$HUB" && git add analysis >> "$LOG" 2>&1
  git commit -m "monitor $(TZ=Asia/Shanghai date +%H:%M) report" -q >> "$LOG" 2>&1 || true
  git -c http.version=HTTP/1.1 push origin main >> "$LOG" 2>&1 || true
}

while :; do
  NOW=$(TZ=Asia/Shanghai date +%H%M)
  [ "$NOW" -ge "1510" ] && break
  if [ "$NOW" -lt "1300" ]; then sleep 600; continue; fi
  cycle
  sleep 900
done
echo "[$(date)] final snapshot + push"
cycle
echo "MONITOR LOOP COMPLETE"
