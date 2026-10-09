#!/usr/bin/env python3
"""
Intraday monitor (every ~15 min during A-share afternoon session).
Outputs per cycle:
  - data/mon/YYYYMMDD_HHMM.json       (raw snapshot + scored results)
  - analysis/monitor_YYYYMMDD_HHMM.md (buyable / watch / avoid + forecasts)
Usage: python3 tools/monitor.py [YYYYMMDD]
"""
import json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(ROOT, "tools", "watchlist.txt")
SNAPSHOT_PATH = os.path.join(ROOT, "data", "snapshot", "latest.txt")
MF_PATH = os.path.join(ROOT, "data", "moneyflow", "latest.txt")
POOL_DIR = os.path.join(ROOT, "data", "pool")
TECH_PATH = os.path.join(ROOT, "data", "technicals", "latest.json")
OUT_MON = os.path.join(ROOT, "data", "mon")
OUT_ANA = os.path.join(ROOT, "analysis")
os.makedirs(OUT_MON, exist_ok=True)
os.makedirs(OUT_ANA, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
      "Referer": "https://gu.qq.com/"}

def dt_now():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8)))

def load_watchlist():
    rows = []; cur = None
    for l in open(WATCHLIST, encoding="utf-8"):
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        if l.startswith("[") and l.endswith("]"):
            cur = l[1:-1]; continue
        if cur:
            p = l.split()
            if len(p) >= 2:
                rows.append({"code": p[0], "name": p[1], "section": cur})
    return rows

def load_snapshot():
    rows = {}
    for l in open(SNAPSHOT_PATH, encoding="utf-8"):
        if l.startswith("#") or "|" not in l:
            continue
        p = l.rstrip().split("|")
        if len(p) < 12:
            continue
        try:
            rows[p[0]] = {"name": p[1], "price": float(p[2]), "prevclose": float(p[3]),
                          "chg_pct": float(p[7]), "vol_ratio": float(p[11])}
        except Exception:
            continue
    return rows

def load_mf():
    rows = {}
    for l in open(MF_PATH, encoding="utf-8"):
        if l.startswith("#") or "|" not in l:
            continue
        p = l.rstrip().split("|")
        if len(p) < 9:
            continue
        try:
            code, date = p[0], p[1]
            if code not in rows:
                rows[code] = {}
            rows[code][date] = {"mainnet_r0": float(p[7])}
        except Exception:
            continue
    return rows

def load_pools(date_str):
    def load_one(fn):
        p = os.path.join(POOL_DIR, f"{fn}.json")
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return load_one(f"{date_str}.ztpool"), load_one(f"{date_str}.dtpool"), load_one(f"{date_str}.zbpool")

def load_technicals():
    try:
        d = json.load(open(TECH_PATH, encoding="utf-8"))
        return {x["code"]: x for x in d}
    except Exception:
        return {}

def get_snap(codes):
    url = f"https://qt.gtimg.cn/q={','.join(codes)}"
    try:
        body = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15).read()
    except Exception as e:
        print(f"snapshot err: {e}", file=sys.stderr)
        return {}
    result = {}
    for line in body.decode("gbk", "replace").split(";"):
        m = re.match(r'v_(\w+)="(.*)"', line.strip())
        if not m:
            continue
        p = m.group(2).split("~")
        if len(p) < 35:
            continue
        try:
            price, prev = float(p[3]), float(p[4])
            result[m.group(1)] = {
                "name": p[1], "price": price, "prevclose": prev, "open": float(p[5]),
                "high": float(p[33]) if p[33] else 0, "low": float(p[34]) if p[34] else 0,
                "chg_pct_auto": round((price - prev) / prev * 100, 2) if prev else 0}
        except Exception:
            continue
    return result

def score(snap, tech, mf):
    s = 0; reasons = []
    chg = snap.get("chg_pct_auto", snap.get("chg_pct", 0))
    rsi = tech.get("rsi", 50)
    hist = tech.get("macd_hist", 0)
    ma_bull = tech.get("ma_bull", False)
    d52 = tech.get("dist52", 50)
    vr = snap.get("vol_ratio", 1)
    if chg > 2:
        s += 2; reasons.append(f"今日{chg:+.1f}%强势")
    elif chg > 0:
        s += 1; reasons.append(f"今日{chg:+.1f}%")
    elif chg < -3:
        s -= 3; reasons.append(f"今日大跌{chg:.1f}%")
    elif chg < -1:
        s -= 1; reasons.append(f"今日{chg:.1f}%")
    if 40 <= rsi <= 65:
        s += 2; reasons.append(f"RSI={rsi:.0f}健康")
    elif rsi > 75:
        s -= 2; reasons.append(f"RSI={rsi:.0f}超买")
    elif rsi < 25:
        s += 1; reasons.append(f"RSI={rsi:.0f}超卖")
    if hist > 0:
        s += 2; reasons.append("MACD红柱")
    elif hist < -0.1:
        s -= 2; reasons.append("MACD绿柱")
    if ma_bull:
        s += 2; reasons.append("MA多头")
    if d52 < 15:
        s += 1; reasons.append(f"52w底部{d52:.0f}%")
    if vr > 1.2 and chg > 0:
        s += 2; reasons.append("放量上涨")
    elif vr > 1.2 and chg < 0:
        s -= 1; reasons.append("放量下跌")
    if mf:
        r0 = mf.get("mainnet_r0", 0)
        if r0 > 0:
            s += 2; reasons.append(f"主力净流入{r0/1e8:.1f}亿")
        elif r0 < -1e8:
            s -= 2; reasons.append(f"主力净流出{abs(r0)/1e8:.1f}亿")
    return s, "; ".join(reasons) if reasons else "neutral"

def classify(score_val):
    if score_val >= 8:
        return "BUY"
    if score_val >= 3:
        return "WATCH"
    if score_val <= -1:
        return "SELL"
    return "HOLD"

NONTRADABLE = {"sh000001", "sz399001", "sz399006", "sh000300", "sh000688", "bj899050",
               "sh000928", "sh000929", "sh000930", "sh000931", "sh000932", "sh000933",
               "sh000934", "sh000935", "sh000936", "sh000937"}

def afternoon_forecast(all_snap):
    lines = ["## 下午走势预测 (基于当前动能)"]
    for k, label in [("sh000001", "上证"), ("sz399001", "深证"), ("sz399006", "创业板"),
                     ("sh000300", "沪深300"), ("sh000688", "科创50")]:
        s = all_snap.get(k, {})
        if not s:
            continue
        chg = s.get("chg_pct_auto", s.get("chg_pct", 0))
        vr = s.get("vol_ratio", 1)
        if chg < -1.5 and vr > 1.2:
            pred = f"继续走弱，预计收盘 {chg-0.3:.2f}% ~ {chg:.2f}%"
        elif chg < -0.5 and vr < 1.0:
            pred = f"缩量阴跌，预计收盘 {chg-0.1:.2f}% ~ {chg+0.2:.2f}%"
        elif chg > -0.5:
            pred = f"震荡企稳，预计收盘 {max(chg-0.2, 0):.2f}% ~ {chg+0.3:.2f}%"
        else:
            pred = f"跟随大盘，收盘在 {chg:.2f}% 附近"
        lines.append(f"- **{label}**: 现价 {chg:+.2f}% → {pred}")
    lines.append("")
    return "\n".join(lines)

def tomorrow_forecast(all_snap):
    sh = all_snap.get("sh000001", {}).get("chg_pct_auto", 0)
    lines = ["## 明日 (10-10) 情景预测",
             f"- 依据: 今日上证 {sh:+.2f}% 收盘状态",
             "- **情景A (40%) 震荡修复**: 美债回落+港股续强, 上证 3780-3850, 科技止跌",
             "- **情景B (35%) 继续探底**: 美债破5.40%或贸易升级, 上证 3700-3780",
             "- **情景C (25%) V型反转**: 降准落地/贸易缓和, 上证 3900+",
             "",
             "### 明日关键催化",
             "- 今晚美股收盘 (纳指若跌>1% → 明日科技低开)",
             "- 美债10Y 收益率 (5.40% 是系统性风险线)",
             "- 周末政策: 稀土/关税/央行OMO",
             "- 三季报: 明日继续披露, 业绩地雷杀跌",
             ""]
    return "\n".join(lines)

def main(date_str=None):
    date_str = date_str or dt_now().strftime("%Y%m%d")
    ts = dt_now().strftime("%H%M")
    codes = [it["code"] for it in load_watchlist()]
    snap = load_snapshot()
    mf = load_mf()
    tech = load_technicals()
    zt_data, dt_data, zb_data = load_pools(date_str)
    zt_codes = {p.get("c", "") for p in zt_data.get("pool", [])}
    all_snap = get_snap(codes)
    all_snap.update({k.replace("sh", "").replace("sz", "").replace("bj", ""): v
                     for k, v in all_snap.items() if k not in snap})
    all_snap.update(snap)

    results = []
    for it in load_watchlist():
        c = it["code"]; name = it["name"]
        s = all_snap.get(c, {})
        t = tech.get(c, {})
        m = None
        for k in [c, c.replace("sh", "").replace("sz", "").replace("bj", "")]:
            if k in mf:
                dates = sorted(mf[k].keys(), reverse=True)
                if dates:
                    m = mf[k][dates[0]]
                    break
        sc, rs = score(s, t, m)
        cat = "INDEX" if c in NONTRADABLE else classify(sc)
        results.append({"code": c, "name": name, "section": it["section"], "score": sc,
                        "category": cat, "reasons": rs,
                        "price": s.get("price", 0),
                        "chg_pct": s.get("chg_pct_auto", s.get("chg_pct", 0)),
                        "rsi": t.get("rsi"), "macd_hist": t.get("macd_hist"),
                        "dist52": t.get("dist52"),
                        "mainnet_r0": m.get("mainnet_r0", 0) if m else 0,
                        "in_zt": c in zt_codes,
                        "in_dt": c in {p.get("c", "") for p in dt_data.get("pool", [])}})
    results.sort(key=lambda x: ({"BUY": 0, "WATCH": 1, "HOLD": 2, "INDEX": 3, "SELL": 4}.get(x["category"], 9), -x["score"]))
    buyable = [r for r in results if r["category"] == "BUY"]
    watch = [r for r in results if r["category"] == "WATCH"]
    sell = [r for r in results if r["category"] == "SELL"]
    indices = [r for r in results if r["category"] == "INDEX"]
    if not buyable and watch:
        buyable = watch[:3]

    zt_c = zt_data.get("tc", 0); dt_c = dt_data.get("tc", 0); zb_c = zb_data.get("tc", 0)
    zb_rate = zb_c / (zt_c + zb_c) * 100 if (zt_c + zb_c) else 0

    snap_obj = {"ts": f"{date_str}_{ts}", "date": date_str,
                "meta": {"zt": zt_c, "dt": dt_c, "zb": zb_c, "zb_rate": round(zb_rate, 1)},
                "indices": indices, "buyable": buyable, "watch": watch, "sell": sell, "all": results}
    with open(os.path.join(OUT_MON, f"{date_str}_{ts}.json"), "w", encoding="utf-8") as f:
        json.dump(snap_obj, f, ensure_ascii=False, indent=2)

    md = [f"# 监控快照 {date_str} {ts} (A股)",
          "",
          f"- 涨停: {zt_c} | 跌停: {dt_c} | 炸板: {zb_c} | 炸板率: {zb_rate:.1f}%"]
    for r in indices:
        md.append(f"- {r['name']}: {r['price']} ({r['chg_pct']:+.2f}%)")
    md.append("")
    md.append("## ⭐ 建议买入 (BUY / 或轻仓候选)")
    md.append("| 代码 | 名称 | 得分 | 今日涨跌% | RSI | MACD | 52w位置% | 主力净流入亿 | 信号 |")
    md.append("|------|------|------|---------|-----|------|---------|------------|------|")
    for r in buyable:
        md.append(f"| {r['code']} | {r['name']} | {r['score']} | {r['chg_pct']:+.2f} | {r.get('rsi','?')} | {r.get('macd_hist','?')} | {r.get('dist52','?')} | {r.get('mainnet_r0',0)/1e8:+.2f} | {r['reasons'][:60]} |")
    md.append("")
    md.append("## ⚠️ 建议观望 (WATCH)")
    md.append("| 代码 | 名称 | 得分 | 今日涨跌% | 信号 |")
    md.append("|------|------|------|---------|------|")
    for r in watch[3:]:
        md.append(f"| {r['code']} | {r['name']} | {r['score']} | {r['chg_pct']:+.2f} | {r['reasons'][:50]} |")
    md.append("")
    md.append("## ❌ 建议回避 (SELL)")
    md.append("| 代码 | 名称 | 得分 | 今日涨跌% | 信号 |")
    md.append("|------|------|------|---------|------|")
    for r in sell:
        md.append(f"| {r['code']} | {r['name']} | {r['score']} | {r['chg_pct']:+.2f} | {r['reasons'][:50]} |")
    md.append("")
    md.append(afternoon_forecast(all_snap))
    md.append(tomorrow_forecast(all_snap))
    md.append("")
    md.append("## 风险提示")
    md.append("1. 本监控每15分钟运行一次，数据来自实时行情快照 (腾讯 qt.gtimg.cn)")
    md.append("2. 技术面评分基于 RSI/MACD/量价/资金流 综合计算，不保证预测准确")
    md.append("3. 本信号不构成投资建议；股市有风险，本金可能亏损")
    md.append(f"- 快照生成时间: {date_str} {ts} CST")
    with open(os.path.join(OUT_ANA, f"monitor_{date_str}_{ts}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"snapshot {date_str} {ts}: BUY={len(buyable)} WATCH={len(watch)} SELL={len(sell)}")
    print(f"-> data/mon/{date_str}_{ts}.json + analysis/monitor_{date_str}_{ts}.md", flush=True)
    return snap_obj

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else dt_now().strftime("%Y%m%d"))
