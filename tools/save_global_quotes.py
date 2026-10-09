#!/usr/bin/env python3
"""Fetch global index quotes (tencent qt) and save to <kline repo>/data/global/quotes.txt.
Env: STOCKS_KLINE_GLOBAL_DIR (output dir, default: <repo>/data/global)
"""
import os, re, urllib.request

RAW = os.environ.get("GQ_RAW_PATH", "/tmp/gq_raw.txt")
OUT_DIR = os.environ.get("STOCKS_KLINE_GLOBAL_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "global")

if not os.path.exists(RAW):
    url = "https://qt.gtimg.cn/q=usDJI,usIXIC,usINX,hkHSI,hkHSTECH"
    try:
        body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read()
        os.makedirs(os.path.dirname(RAW), exist_ok=True)
        with open(RAW, "wb") as f:
            f.write(body)
        print(f"fetched global quotes ({len(body)} bytes)", flush=True)
    except Exception as e:
        print(f"fetch failed: {e}", flush=True)
        raise SystemExit(1)

rows = []
for l in open(RAW, encoding="latin-1"):
    m = re.match(r'v_(\w+)="(.*)"', l.strip())
    if not m:
        continue
    p = m.group(2).split("~")
    if len(p) < 35:
        continue
    rows.append((m.group(1), p[2], p[3] if len(p) > 3 else "", p[4] if len(p) > 4 else "",
                 p[32] if len(p) > 32 else "", p[33] if len(p) > 33 else ""))
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "quotes.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("# global index quotes (tencent qt)\n")
    f.write("# code|name|prevclose|close|chg|chg%\n")
    for r in rows:
        f.write("|".join(r) + "\n")
print(f"saved {len(rows)} quotes -> {out}")
