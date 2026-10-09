#!/bin/bash
# Monitor loop: every 15 min during A-share afternoon session (13:00-15:05 CST)
# Commits each snapshot to GitHub; terminates at 15:10 and notifies the agent.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
GH_CMD='git -c http.version=HTTP/1.1 push origin main'
LAST_SLEEP=900
while true; do
  NOW=$(TZ=Asia/Shanghai date +%H%M)
  if [ "$NOW" -ge "1510" ]; then
    echo "[$(date)] monitor loop exiting (after 15:10)"
    break
  fi
  if [ "$NOW" -lt "1300" ]; then
    echo "[$(date)] too early ($(date +%H:%M)), sleeping 10 min"
    sleep 600
    continue
  fi
  echo "[$(date +%H:%M:%S)] running monitor snapshot"
  python3 tools/monitor.py >> /tmp/monitor.log 2>&1
  echo "[$(date +%H:%M:%S)] adding changes and pushing"
  git add -A
  git commit -m "monitor $(TZ=Asia/Shanghai date +%H:%M) snapshot" --quiet 2>/dev/null || true
  $GH_CMD >> /tmp/monitor.log 2>&1 || true
  # sleep until next 15-min mark (~900s), but check the time at top of loop next iteration
  sleep "$LAST_SLEEP"
done
echo "[$(date)] FINAL snapshot"
python3 tools/monitor.py >> /tmp/monitor.log 2>&1
git add -A
git commit -m "final monitor snapshot ($(TZ=Asia/Shanghai date +%H:%M))" --quiet 2>/dev/null || true
$GH_CMD >> /tmp/monitor.log 2>&1 || true
echo "[$(date)] MONITOR LOOP COMPLETE"
