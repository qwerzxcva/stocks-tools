#!/usr/bin/env python3
"""Local 24/7 daemon (5-min granularity). Calls cron_entrypoint.sh tasks.
Runs continuously while device is on; crashes → will restart next time.
Usage: python3 local_daemon.py [--once]
  --once : run all applicable tasks for now and exit (useful for testing)
"""
import os, subprocess, sys, time, re
from datetime import datetime, timezone, timedelta

WS = os.environ.get("WORKSPACE", "/root/workspace")
HUB = os.path.join(WS, "stocks")
CRON = os.path.join(HUB, "cron_entrypoint.sh")
LOG = os.path.join(HUB, "logs", "daemon.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_task(task):
    try:
        r = subprocess.run(["bash", CRON, "run", task], capture_output=True, text=True, timeout=1200)
        log(f"task {task}: rc={r.returncode} out={r.stdout[-200:]!r} err={r.stderr[-200:]!r}")
    except Exception as e:
        log(f"task {task} ERROR: {e}")

def main():
    if "--once" in sys.argv:
        # Test mode: run applicable tasks for current time
        now = datetime.now(timezone(timedelta(hours=8)))
        h, m = now.hour, now.minute
        is_weekend = now.weekday() >= 5
        log(f"once mode: {now} weekend={is_weekend}")
        if h == 3:
            run_task("nightly")
        if 9 <= h < 16 and not is_weekend:
            run_task("intra")
        if h == 15 and 25 <= m <= 35:
            run_task("close")
        run_task("news")
        return
    log("daemon started")
    last = {"intra": 0, "close": None, "nightly": 0, "news": 0}
    while True:
        now = datetime.now(timezone(timedelta(hours=8)))
        h, m, d = now.hour, now.minute, now.weekday()
        is_trading = (9 <= h < 16) and (d < 5)
        tag = f"{h:02d}:{m:02d}"
        try:
            # Intraday: every 15 min during trading (13:xx already handled by monitor_loop)
            if is_trading and m % 15 == 0 and (time.time() - last["intra"]) > 800:
                last["intra"] = time.time()
                run_task("intra")
            # Close: once around 15:30
            if h == 15 and 28 <= m <= 33 and last["close"] != tag:
                last["close"] = tag
                run_task("close")
            # Nightly: once around 03:00
            if h == 3 and m < 2 and (time.time() - last["nightly"]) > 3600:
                last["nightly"] = time.time()
                run_task("nightly")
            # News: every 30 min always
            if (time.time() - last["news"]) > 1700:
                last["news"] = time.time()
                run_task("news")
        except Exception as e:
            log(f"loop error: {e}")
        # Check out-of-market sleeps to save battery/CPU
        sleep = 300 if is_trading else 900
        time.sleep(sleep)

if __name__ == "__main__":
    main()
