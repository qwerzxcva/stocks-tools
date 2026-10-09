#!/bin/bash
# poll sina financial news every 10 min, append to 消息面/, push to github when new
ROOT=/root/stocks
cd "$ROOT" || exit 1
LOG="$ROOT/消息面/.cron.log"
while true; do
  TS=$(date -u -d '+8 hours' '+%Y-%m-%d %H:%M:%S')
  n=$(python3 tools/news_collect.py "$ROOT" 2>>"$LOG")
  if [ "$n" != "0" ] && [ -n "$n" ]; then
    git add 消息面/
    git -c user.email=bot@local -c user.name=newsbot commit -q -m "news: +$n @ $TS" >>"$LOG" 2>&1
    git push origin main >>"$LOG" 2>&1
    echo "$TS +$n pushed" >>"$LOG"
  else
    echo "$TS none" >>"$LOG"
  fi
  sleep 60
done
