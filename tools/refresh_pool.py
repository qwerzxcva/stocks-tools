#!/usr/bin/env python3
"""Refresh limit-up/down/broken-seal pools + index snapshot for the current date.
Writes to $STOCKS_LIVE/pool/{date}.{zt,dt,zb}pool.json and $STOCKS_LIVE/snapshot/latest.txt
"""
import json, os, re, sys, urllib.request, time

LIVE = os.environ.get("STOCKS_LIVE") or os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "..", "stocks-data-live", "data"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120", "Referer": "https://quote.eastmoney.com/"}
POOLDIR = os.path.join(LIVE, "pool")
os.makedirs(POOLDIR, exist_ok=True)

def now_date():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")

def fetch_pool(name, fn):
    url = (f"https://push2ex.eastmoney.com/getTopic{name}Pool"
           f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date={now_date()}")
    try:
        body = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
        d = json.loads(body.decode("utf-8"))
        out = os.path.join(POOLDIR, f"{now_date()}.{fn}")
        json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        tc = d.get("data", {}).get("tc")
        print(f"{name}: tc={tc}")
    except Exception as e:
        print(f"{name}: ERR {e}", file=sys.stderr)

for name, fn in [("ZT", "ztpool"), ("DT", "dtpool"), ("ZB", "zbpool")]:
    fetch_pool(name, fn)
    time.sleep(0.5)

# index snapshot via qt
import urllib.parse
idx = "sh000001,sz399001,sz399006,sh000300,sh000688,bj899050"
try:
    body = urllib.request.urlopen(urllib.request.Request(
        f"https://qt.gtimg.cn/q={idx}", headers={"User-Agent": UA["User-Agent"], "Referer": "https://gu.qq.com/"}), timeout=15).read()
    lines = body.decode("gbk", "replace").split(";")
    with open(os.path.join(LIVE, "snapshot", "latest.txt"), "w", encoding="utf-8") as f:
        f.write(f"# snapshot {now_date()}  fields: code|name|price|prevclose|open|vol|amount|chg%|turnover%|high|low|volratio\n")
        for l in lines:
            m = re.match(r'\s*v_(\w+)="(.*)"', l)
            if not m:
                continue
            p = m.group(2).split("~")
            if len(p) < 40:
                continue
            try:
                f.write(f"{p[2]}|{p[1]}|{p[3]}|{p[4]}|{p[5]}|{p[6]}|{p[35]}|{p[31]}|{p[38]}|{p[33]}|{p[34]}|{p[49]}\n")
            except Exception:
                continue
    print("index snapshot written")
except Exception as e:
    print(f"snapshot ERR {e}", file=sys.stderr)
