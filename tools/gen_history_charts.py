#!/usr/bin/env python3
"""Generate historical candlestick SVG charts from data/kline/history files."""
import os, sys, json
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(R, "data/kline/history")
CHARTS = os.path.join(R, "charts")

def parse(path):
    rows = []
    for l in open(path, encoding='utf-8'):
        if l.startswith('#') or '|' not in l: continue
        p = l.strip().split('|')
        if len(p) < 7: continue
        try: rows.append({'d': p[1], 'o': float(p[2]), 'c': float(p[3]), 'h': float(p[4]), 'l': float(p[5]), 'v': float(p[6])})
        except: pass
    return rows

def aggregate_yearly(rows):
    yrs = {}
    for r in rows:
        y = r['d'][:4]
        if y not in yrs: yrs[y] = []
        yrs[y].append(r)
    out = []
    for y in sorted(yrs):
        rs = yrs[y]
        out.append({'d': y, 'o': rs[0]['o'], 'c': rs[-1]['c'],
                    'h': max(r['h'] for r in rs), 'l': min(r['l'] for r in rs),
                    'v': sum(r['v'] for r in rs)})
    return out

def candle_svg(rows, title, out, W=1000, H=440):
    ML, MR, MT, MB = 60, 20, 44, 50
    pw, ph = W-ML-MR, H-MT-MB-50
    n = len(rows)
    if n < 2: return
    mn = min(r['l'] for r in rows); mx = max(r['h'] for r in rows)
    pad = (mx-mn)*0.08 or mx*0.01
    mn -= pad; mx += pad
    sc = ph/(mx-mn)
    vmax = max(r['v'] for r in rows) or 1
    step = max(1, n//8)
    out_s = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#fff"/>',
             f'<text x="{ML}" y="24" font-size="16" font-weight="bold">{title}  ({n} bars)</text>']
    for i in range(5):
        y = MT + ph*i/4; pv = mx-(mx-mn)*i/4
        out_s.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{W-MR}" y2="{y:.1f}" stroke="#eee"/>')
        out_s.append(f'<text x="{ML-6}" y="{y+4:.1f}" font-size="11" fill="#888" text-anchor="end">{pv:.2f}</text>')
    bw = pw/n*0.6
    for i, r in enumerate(rows):
        x = ML + (i+0.5)*pw/n
        yh = MT + (mx-r['h'])*sc; yl = MT + (mx-r['l'])*sc
        yo = MT + (mx-r['o'])*sc; yc = MT + (mx-r['c'])*sc
        up = r['c'] >= r['o']
        col = '#e63946' if up else '#2a9d8f'
        ty, th = (yo if yo<yc else yc), (abs(yc-yo) or 1)
        out_s.append(f'<line x1="{x:.1f}" y1="{yh:.1f}" x2="{x:.1f}" y2="{yl:.1f}" stroke="{col}"/>')
        out_s.append(f'<rect x="{x-bw/2:.1f}" y="{ty:.1f}" width="{bw:.1f}" height="{th:.1f}" fill="{col}"/>')
        vy = H-MB - (r['v']/vmax)*40
        out_s.append(f'<rect x="{x-bw/2:.1f}" y="{vy:.1f}" width="{bw:.1f}" height="{H-MB-vy:.1f}" fill="{col}" opacity="0.45"/>')
        if i % step == 0:
            out_s.append(f'<text x="{x:.1f}" y="{H-MB+30}" font-size="10" fill="#888" text-anchor="middle" transform="rotate(-45 {x:.1f} {H-MB+30})">{r["d"]}</text>')
    out_s.append('</svg>')
    with open(out, 'w') as f:
        f.write('\n'.join(out_s))
    print(f"chart: {out}")

# 1) sh000001 yearly 2000-2026
yrs = aggregate_yearly(parse(os.path.join(HIST, "sh000001.month.txt")))
candle_svg(yrs, "SSE Composite 历年年报（月线聚合 2000-2026）", os.path.join(CHARTS, "history-sh000001-yearly.svg"))

# 2) sh000001 2026 YTD daily
daily = parse(os.path.join(HIST, "sh000001.txt"))
d2026 = [r for r in daily if r['d'].startswith('2026')]
candle_svg(d2026, "SSE Composite 2026 YTD 日线（含成交量）", os.path.join(CHARTS, "history-sh000001-2026ytd.svg"))

# 3) sh000001 weekly last 250
weekly = parse(os.path.join(HIST, "sh000001.week.txt"))
candle_svg(weekly[-250:], "SSE Composite 周线（近5年）", os.path.join(CHARTS, "history-sh000001-weekly.svg"))

# 4) sz399006 yearly
cy = aggregate_yearly(parse(os.path.join(HIST, "sz399006.month.txt")))
candle_svg(cy, "ChiNext Index 历年年报（月线聚合 2010-2026）", os.path.join(CHARTS, "history-sz399006-yearly.svg"))

# 5) sz399001 yearly
sz = aggregate_yearly(parse(os.path.join(HIST, "sz399001.month.txt")))
candle_svg(sz, "SZ Component 历年年报（月线聚合 2000-2026）", os.path.join(CHARTS, "history-sz399001-yearly.svg"))

# 6) sh000300 yearly
hs = aggregate_yearly(parse(os.path.join(HIST, "sh000300.month.txt")))
candle_svg(hs, "CSI300 历年年报（月线聚合 2005-2026）", os.path.join(CHARTS, "history-sh000300-yearly.svg"))

# history.html index
files = sorted(f for f in os.listdir(CHARTS) if f.startswith('history-'))
html = ['<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>history charts</title>',
        '<style>body{font-family:sans-serif;margin:20px;background:#fafafa}a{display:inline-block;margin:4px 8px;padding:6px 10px;background:#fff;border:1px solid #ddd;border-radius:4px;text-decoration:none;color:#0366d6}</style></head><body>',
        f'<h1>历年 K 线图表（数据见 data/kline/history/，复盘见 docs/history.md）</h1>']
for f in files:
    html.append(f'<a href="{f}" target="_blank">{f.replace("history-","").replace(".svg","")}</a>')
html.append('<a href="../docs/history.md" target="_blank">docs/history.md（历年涨跌原因复盘）</a>')
html.append('</body></html>')
with open(os.path.join(CHARTS, "history.html"), 'w') as fh:
    fh.write('\n'.join(html))
print(f"index: {CHARTS}/history.html")
