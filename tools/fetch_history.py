#!/usr/bin/env python3
"""
Fetch historical monthly weekly and daily klines for major indices.
Run: python3 tools/fetch_history.py [output_dir]
Saves to: output_dir/*.txt, *.month.txt, *.week.txt, *.yearly.csv
"""
import json, os, sys, subprocess, time
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data", "kline", "history")
os.makedirs(OUT, exist_ok=True)

indices = [
    ("sh000001", "上证综指", 800),   # daily 2024+
    ("sh000300", "沪深300", 800),
    ("sz399001", "深证成指", 800),
    ("sz399006", "创业板指", 800),
    ("sh000688", "科创50", 500),
]

for code, name, cnt in indices:
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{cnt},qfq"
    r = subprocess.run(["curl","-s","--max-time","40",url,"-H",f"User-Agent: {UA}","-H","Referer: https://gu.qq.com/",
                        "-o", f"/tmp/fetch_{code}.json"], capture_output=True, text=True)
    try:
        with open(f"/tmp/fetch_{code}.json", encoding='utf-8', errors='replace') as f:
            raw = f.read().replace('\x00','')
        d = json.loads(raw, strict=False)
        k = d['data'][code]
        arr = k.get('qfqday') or k.get('day') if isinstance(k, dict) else None
        if arr and len(arr) > 100:
            with open(os.path.join(OUT, f"{code}.txt"), 'w') as f:
                f.write(f"# {code} {name} qfq daily kline, {len(arr)} bars\n")
                for row in arr:
                    f.write(f"{code}|{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}\n")
            print(f"✓ {code} daily: {len(arr)} bars {arr[0][0]}..{arr[-1][0]}")
    except Exception as e:
        print(f"✗ {code} daily: {e}")

# monthly
for code, name, _ in [("sh000001","上证综指",None),("sz399001","深证成指",None),("sz399006","创业板指",None),("sh000300","沪深300",None)]:
    cnt = 320 if code != "sz399006" else 220
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},month,,,{cnt},qfq"
    r = subprocess.run(["curl","-s","--max-time","40",url,"-H",f"User-Agent: {UA}","-H","Referer: https://gu.qq.com/",
                        "-o", f"/tmp/fetch_{code}.json"], capture_output=True, text=True)
    try:
        with open(f"/tmp/fetch_{code}.json", encoding='utf-8', errors='replace') as f:
            raw = f.read().replace('\x00','')
        d = json.loads(raw, strict=False)
        k = d['data'][code]
        arr = k.get('qfqmonth') or k.get('month') if isinstance(k, dict) else None
        if arr and len(arr) > 50:
            with open(os.path.join(OUT, f"{code}.month.txt"), 'w') as f:
                f.write(f"# {code} {name} qfq monthly kline, {len(arr)} bars\n")
                for row in arr:
                    f.write(f"{code}|{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}\n")
            print(f"✓ {code} monthly: {len(arr)} bars {arr[0][0]}..{arr[-1][0]}")
    except Exception as e:
        print(f"✗ {code} monthly: {e}")

# weekly
code = "sh000001"
url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},week,,,800,qfq"
r = subprocess.run(["curl","-s","--max-time","40",url,"-H",f"User-Agent: {UA}","-H","Referer: https://gu.qq.com/",
                    "-o", f"/tmp/fetch_{code}.json"], capture_output=True, text=True)
try:
    with open(f"/tmp/fetch_{code}.json", encoding='utf-8', errors='replace') as f:
        raw = f.read().replace('\x00','')
    d = json.loads(raw, strict=False)
    k = d['data'][code]
    arr = k.get('qfqweek') or k.get('week') if isinstance(k, dict) else None
    if arr and len(arr) > 100:
        with open(os.path.join(OUT, f"{code}.week.txt"), 'w') as f:
            f.write(f"# {code} qfq weekly kline, {len(arr)} bars\n")
            for row in arr:
                f.write(f"{code}|{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}\n")
        print(f"✓ {code} weekly: {len(arr)} bars {arr[0][0]}..{arr[-1][0]}")
except Exception as e:
    print(f"✗ {code} weekly: {e}")

# generate yearly CSV for each daily file
from collections import defaultdict
for code, name, _ in [("sh000001","上证综指"),("sh000300","沪深300"),("sz399001","深证成指"),("sz399006","创业板指")]:
    months = []
    for l in open(os.path.join(OUT, f"{code}.month.txt"), encoding='utf-8'):
        if l.startswith('#') or '|' not in l: continue
        p = l.strip().split('|')
        if len(p) < 7: continue
        try: months.append({'y': p[0][:4], 'o': float(p[2]), 'c': float(p[3]), 'h': float(p[4]), 'l': float(p[5]), 'v': float(p[6])})
        except: pass
    yrs = defaultdict(list)
    for m in months: yrs[m['y']].append(m)
    prev = None
    rows = []
    for y in sorted(yrs):
        rs = sorted(yrs[y], key=lambda x:x['y'])
        hi = max(x['h'] for x in rs); lo = min(x['l'] for x in rs)
        ret = (rs[-1]['c']/prev-1)*100 if prev else None
        v = sum(x['v'] for x in rs)
        rows.append([y, rs[0]['o'], rs[-1]['c'], hi, lo, ret, v, len(rs)])
        prev = rs[-1]['c']
    path = os.path.join(OUT, f"{code}.yearly.csv")
    with open(path, 'w') as f:
        f.write("year,open,close,high,low,ret_pct,total_vol,bars\n")
        for r in rows:
            ret_str = f"{r[5]:.2f}" if r[5] is not None else ""
            f.write(f"{r[0]},{r[1]:.2f},{r[2]:.2f},{r[3]:.2f},{r[4]:.2f},{ret_str},{int(r[6])},{r[7]}\n")
    print(f"✓ {code}.yearly.csv ({len(rows)} years)")

# append updated daily_index rows for 9/22-9/30
target_dates = ["2026-09-22","2026-09-23","2026-09-24","2026-09-28","2026-09-29","2026-09-30"]
idx_codes = ["sh000001","sh000300","sh000688","sz399001","sz399006"]
di_path = os.path.join(os.path.dirname(__file__), "..", "data", "daily_index.txt")
if not os.path.exists(di_path):
    # actions / fresh-checkout mode: file missing -> create empty and skip append
    with open(di_path, "w", encoding="utf-8") as _f:
        _f.write("# date|code|name|open|close|high|low|vol|chg|amp\n")
# load existing data for prev closes
existing = {}
for l in open(di_path, encoding='utf-8'):
    if l.startswith('#') or '|' not in l: continue
    p = l.strip().split('|')
    if len(p) >= 6: existing[(p[0],p[1])] = float(p[5])
data = {}
for code in idx_codes:
    bars = []
    for l in open(os.path.join(OUT, f"{code}.txt")):
        if l.startswith('#') or '|' not in l: continue
        p = l.strip().split('|')
        if len(p) >= 7:
            bars.append({'date':p[1],'o':float(p[2]),'c':float(p[3]),'h':float(p[4]),'l':float(p[5]),'v':float(p[6])})
    data[code] = bars
new_rows = []
for code in idx_codes:
    bars = data[code]
    closes = {b['date']: b['c'] for b in bars}
    prev_c = {b['date']: bars[i-1]['c'] for i,b in enumerate(bars) if i>0}
    for d in target_dates:
        if d not in closes: continue
        b = next(x for x in bars if x['date']==d)
        chg = (b['c']/prev_c[d]-1)*100 if d in prev_c else 0.0
        amp = (b['h']-b['l'])/prev_c[d]*100 if d in prev_c else 0.0
        new_rows.append(f"{d}|{code}|{code}|{b['o']:.3f}|{b['c']:.3f}|{b['h']:.3f}|{b['l']:.3f}|{b['v']:.3f}|{chg:.2f}|{amp:.2f}")
with open(di_path, 'a', encoding='utf-8') as f:
    for r in sorted(set(new_rows)):
        key = r.split('|')[0]+'|'+r.split('|')[1]
        if key not in existing:
            f.write(r+"\n")
            existing[key] = 1
print(f"\nappended {len(new_rows)} rows to {di_path}")

print("\nDone.")
