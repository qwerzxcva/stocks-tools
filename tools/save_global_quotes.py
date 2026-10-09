#!/usr/bin/env python3
"""Save global index quotes (tencent qt) to data/global/quotes.txt"""
import re, os, sys
RAW = "/tmp/gq_raw.txt"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "global", "quotes.txt")
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
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("# global index quotes (tencent qt, 2026-10-09 midday CST)\n")
    f.write("# code|name|prevclose|close|chg|chg%\n")
    for r in rows:
        f.write("|".join(r) + "\n")
print(f"saved {len(rows)} quotes -> {OUT}")
