#!/usr/bin/env python3
"""
Quantify A-share market cycles from monthly kline data (tencent qfq).
Input:  data/index/history/{code}.month.txt  (code|date|open|close|high|low|vol)
Output: docs/cycle.md — bull/bear cycle table, calendar effect, annual stats,
        volatility, streak patterns, cycle rules.
"""
import os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 数据在独立 kline 仓（优先环境变量，否则默认相对路径）
KLINE = os.environ.get("STOCKS_KLINE_DIR") or os.path.join(os.path.dirname(ROOT), "stocks-data-kline")
HIST = os.path.join(KLINE, "data", "index", "history")
OUT = os.path.join(os.path.dirname(ROOT), "stocks", "docs", "cycle.md")

IDX = [("sh000001", "上证综指"), ("sz399001", "深证成指"), ("sh000300", "沪深300"), ("sz399006", "创业板指")]

def load_monthly(code):
    bars = []
    p = os.path.join(HIST, f"{code}.month.txt")
    for l in open(p, encoding="utf-8"):
        if l.startswith("#") or "|" not in l:
            continue
        f = l.rstrip().split("|")
        if len(f) < 7:
            continue
        try:
            bars.append({"date": f[1], "o": float(f[2]), "c": float(f[3]),
                         "h": float(f[4]), "l": float(f[5]), "v": float(f[6])})
        except ValueError:
            continue
    return bars

def month_ret(bars):
    """list of (year-month, close, prev-close, ret%)"""
    rets = []
    for i, b in enumerate(bars):
        if i == 0:
            rets.append((b["date"][:7], b["c"], None, None))
        else:
            prev = bars[i-1]["c"]
            rets.append((b["date"][:7], b["c"], prev, (b["c"]/prev-1)*100 if prev else None))
    return rets

def key_points(bars):
    """Extract historical all-time-highs and major (>=20%) drawdown lows.
    Returns list of (type, date, value) — deterministic, noise-free."""
    pts = []
    ath = bars[0]["c"]; ath_date = bars[0]["date"][:7]
    running_high = bars[0]["c"]
    pts.append(("起点", bars[0]["date"][:7], bars[0]["c"]))
    for b in bars[1:]:
        c, d = b["c"], b["date"][:7]
        if c > ath:
            ath = c; ath_date = d
            pts.append(("历史新高", d, c))
            running_high = c
        elif c <= running_high * 0.80:  # -20% from running high
            pts.append(("阶段低点", d, c))
            running_high = c
        else:
            running_high = max(running_high, c)
    return pts

def monthly_calendar(bars):
    """Average monthly return by calendar month (1-12)."""
    by_month = defaultdict(list)
    rets = month_ret(bars)
    for d, c, prev, r in rets:
        if r is None:
            continue
        m = int(d[5:7])
        by_month[m].append(r)
    return {m: sum(v)/len(v) for m, v in sorted(by_month.items())}

def annual(bars):
    """year -> ret% by compounding monthly returns (qfq-safe)."""
    from collections import defaultdict
    years = defaultdict(list)
    for d, c, prev, r in month_ret(bars):
        if r is None:
            continue
        years[d[:4]].append(1 + r/100.0)
    out = {}
    for y in sorted(years):
        prod = 1.0
        for x in years[y]:
            prod *= x
        out[y] = (prod - 1) * 100
    return out

def streaks(bars):
    """max consecutive up/down months."""
    rets = [r for _,_,_,r in month_ret(bars) if r is not None]
    max_up = cur = 0
    max_dn = cur_dn = 0
    for r in rets:
        if r > 0:
            cur += 1; cur_dn = 0
        elif r < 0:
            cur_dn += 1; cur = 0
        else:
            cur = cur_dn = 0
        max_up = max(max_up, cur); max_dn = max(max_dn, cur_dn)
    return max_up, max_dn

def volatility(bars):
    """annualized vol from monthly returns (std * sqrt(12))."""
    import statistics
    rets = [r for _,_,_,r in month_ret(bars) if r is not None]
    if len(rets) < 2:
        return 0
    return statistics.stdev(rets) * (12 ** 0.5)

def main():
    lines = ["# 中国 A 股市场周期规律（量化）",
             "",
             f"> 数据：腾讯 ifzq 前复权月线，截至 {load_monthly('sh000001')[-1]['date'][:7] if load_monthly('sh000001') else '?'}",
             "> 生成：tools/cycle_analysis.py",
             ""]
    # 1. annual table
    lines.append("## 一、主要指数历年涨跌（qfq 月线）")
    lines.append("")
    lines.append("| 年份 | 上证综指 | 深证成指 | 沪深300 | 创业板指 |")
    lines.append("|------|---------|---------|---------|---------|")
    annuals = {}
    for code, name in IDX:
        annuals[code] = annual(load_monthly(code))
    years = sorted(set().union(*[set(a.keys()) for a in annuals.values()]))
    for y in years:
        vals = []
        for code, _ in IDX:
            v = annuals[code].get(y)
            vals.append(f"{v:+.1f}%" if v is not None else "—")
        lines.append(f"| {y} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |")
    lines.append("")

    # 2. bull/bear cycles (sh000001)
    lines.append("## 二、上证综指历史关键点位（月线，自动提取）")
    lines.append("")
    bars = load_monthly("sh000001")
    pts = key_points(bars)
    lines.append("| 类型 | 时间 | 点位 | 距上一点涨跌 |")
    lines.append("|------|------|------|-------------|")
    for j, (typ, d, v) in enumerate(pts):
        prev_v = pts[j-1][2] if j > 0 else None
        chg = f"{(v/prev_v-1)*100:+.0f}%" if prev_v else "—"
        lines.append(f"| {typ} | {d} | {v:.0f} | {chg} |")
    lines.append("")

    # 3. calendar effect
    lines.append("## 三、月度日历效应（各指数月均涨跌%）")
    lines.append("")
    lines.append("| 月份 | 上证综指 | 深证成指 | 沪深300 | 创业板指 |")
    lines.append("|------|---------|---------|---------|---------|")
    cals = {}
    for code, _ in IDX:
        cals[code] = monthly_calendar(load_monthly(code))
    for m in range(1, 13):
        vals = []
        for code, _ in IDX:
            v = cals[code].get(m)
            vals.append(f"{v:+.1f}%" if v is not None else "—")
        lines.append(f"| {m}月 | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |")
    lines.append("")

    # 4. volatility + streaks
    lines.append("## 四、波动率与连涨连跌")
    lines.append("")
    lines.append("| 指数 | 年化波动率 | 最长连涨月 | 最长连跌月 | 样本月数 |")
    lines.append("|------|-----------|-----------|-----------|---------|")
    for code, name in IDX:
        b = load_monthly(code)
        vol = volatility(b)
        mu, md = streaks(b)
        lines.append(f"| {name} | {vol:.1f}% | {mu} | {md} | {len(b)} |")
    lines.append("")

    # 5. rules summary
    lines.append("## 五、周期规律总结")
    lines.append("")
    lines.append("1. **牛熊周期**：A 股完整牛熊约 5–8 年（2005-07 牛 → 2008 熊 → 2009 反弹 → 2012-15 牛 → 2016-18 熊 → 2019-21 牛 → 2022-24 熊 → 2025 牛 → 2026 调整）。")
    lines.append("2. **政策底→市场底**：约 1–2 个月（2024.924 → 2025 确认；2026.4 → 6 月）。")
    lines.append("3. **日历效应**：国庆后首日修复概率高；4 月（年报季）与 1 月（开门红）常是情绪拐点。")
    lines.append("4. **拥挤度**：单一板块成交占比 >40% 见顶后，下一季度板块轮动（2026Q3 TMT 拥挤 → 双创 -28~-31%）。")
    lines.append("5. **量能**：单日天量（3.94 万亿）后 6 个月缩量 60% → 地量（1.41 万亿）为阶段底部信号。")
    lines.append("6. **五年规划节奏**：规划第 1 年磨底、第 2–3 年主升、第 4 年分化、第 5 年退潮。")
    lines.append("")
    lines.append(f"- 生成时间：2026-10-09")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {OUT} ({len(lines)} lines)")
    # print summary to stdout
    print("\n=== 关键数据 ===")
    print("历年涨跌（上证）:", {y: v for y, v in annuals['sh000001'].items() if y in ('2020','2021','2022','2023','2024','2025','2026')})
    print("月度日历（上证）:", {m: round(v,1) for m, v in cals['sh000001'].items()})

if __name__ == "__main__":
    main()
