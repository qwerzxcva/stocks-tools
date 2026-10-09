#!/usr/bin/env python3
"""Aggregate global index klines (daily -> weekly/monthly/quarterly/yearly) from data/global/*.json"""
import json, os, glob
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "global")
os.makedirs(OUT, exist_ok=True)

def bars_of(fn):
    try:
        d = json.load(open(fn, encoding="utf-8"))
    except Exception:
        return os.path.basename(fn).replace(".json", ""), []
    code = os.path.basename(fn).replace(".json", "")
    inner = d.get("data", {}).get(code, {})
    arr = inner.get("qfqday") or inner.get("day") or []
    out = []
    for r in arr:
        out.append({"date": r[0], "o": float(r[1]), "c": float(r[2]), "h": float(r[3]), "l": float(r[4]), "v": float(r[5])})
    return code, out

def resample(bars, keyfn):
    groups = defaultdict(list)
    for b in bars:
        groups[keyfn(b["date"])].append(b)
    rows = []
    for k in sorted(groups):
        g = sorted(groups[k], key=lambda x: x["date"])
        rows.append({"key": k, "date": g[0]["date"], "o": g[0]["o"], "c": g[-1]["c"],
                     "h": max(x["h"] for x in g), "l": min(x["l"] for x in g), "v": sum(x["v"] for x in g)})
    return rows

def write(path, header, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for r in rows:
            f.write(f"{r['key']}|{r['date']}|{r['o']:.2f}|{r['c']:.2f}|{r['h']:.2f}|{r['l']:.2f}|{int(r['v'])}\n")
    print(f"  {os.path.basename(path)}: {len(rows)} rows")

for fn in sorted(glob.glob(os.path.join(OUT, "*.json"))):
    code, bars = bars_of(fn)
    if not bars:
        print(f"{code}: empty, skip"); continue
    print(f"{code}: {len(bars)} daily bars ({bars[0]['date']}..{bars[-1]['date']})")
    write(os.path.join(OUT, f"{code}.day.txt"), f"# {code} daily", bars)
    write(os.path.join(OUT, f"{code}.week.txt"), f"# {code} weekly",
          resample(bars, lambda d: d[:4] + "-W" + str(int(d[5:7]) // 7 + 1)))
    write(os.path.join(OUT, f"{code}.month.txt"), f"# {code} monthly",
          resample(bars, lambda d: d[:7]))
    write(os.path.join(OUT, f"{code}.quarter.txt"), f"# {code} quarterly",
          resample(bars, lambda d: d[:4] + "-Q" + str((int(d[4:6]) - 1) // 3 + 1)))
    write(os.path.join(OUT, f"{code}.year.txt"), f"# {code} yearly",
          resample(bars, lambda d: d[:4]))
print("done")
