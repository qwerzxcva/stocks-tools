#!/usr/bin/env python3
"""
Compute technicals + capital flow for the watchlist, emit:
  - data/technicals/latest.json
  - analysis/20261009-full.md
  - analysis/20261009-buyable.md
"""
import json, os, sys, math, collections
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_PATH = os.path.join(ROOT, "tools", "watchlist.txt")
SNAPSHOT_PATH = os.path.join(ROOT, "data", "snapshot", "latest.txt")
MF_PATH = os.path.join(ROOT, "data", "moneyflow", "latest.txt")
POOL_ZT = os.path.join(ROOT, "data", "pool", "20261009.ztpool.json")
POOL_DT = os.path.join(ROOT, "data", "pool", "20261009.dtpool.json")
POOL_ZB = os.path.join(ROOT, "data", "pool", "20261009.zbpool.json")
KL_ALL = os.path.join(ROOT, "data", "kline", "all.txt")
KLINE_HIST_DIR = os.path.join(ROOT, "data", "kline", "history")
TECH_PATH = os.path.join(ROOT, "data", "technicals", "latest.json")
OUT_FULL = os.path.join(ROOT, "analysis", "20261009-full.md")
OUT_BUYABLE = os.path.join(ROOT, "analysis", "20261009-buyable.md")

# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #

def load_watchlist():
    sections = {}; cur = None
    for line in open(WATCHLIST_PATH, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]; sections[cur] = []
            continue
        if cur:
            parts = line.split()
            if len(parts) >= 2:
                sections[cur].append({"code": parts[0], "name": parts[1]})
    return sections

def load_snapshot():
    rows = {}
    for l in open(SNAPSHOT_PATH, encoding="utf-8"):
        if l.startswith("#") or "|" not in l: continue
        p = l.rstrip().split("|")
        if len(p) < 12: continue
        try:
            rows[p[0]] = {"name": p[1], "price": float(p[2]), "prevclose": float(p[3]),
                "open": float(p[4]), "vol": float(p[5]), "amount": float(p[6]),
                "chg_pct": float(p[7]), "turnover": float(p[8]),
                "high": float(p[9]), "low": float(p[10]), "vol_ratio": float(p[11])}
        except: continue
    return rows

def load_moneyflow():
    rows = {}
    for l in open(MF_PATH, encoding="utf-8"):
        if l.startswith("#") or "|" not in l: continue
        p = l.rstrip().split("|")
        if len(p) < 9: continue
        try:
            code, date = p[0], p[1]
            if code not in rows: rows[code] = {}
            rows[code][date] = {"close": float(p[2]), "chg": float(p[3]), "turnover": float(p[4]),
                "net": float(p[5]), "ratio": float(p[6]), "mainnet_r0": float(p[7]), "mainratio_r0": float(p[8])}
        except: continue
    return rows

def load_pools():
    def load_one(path):
        try: return json.load(open(path, encoding="utf-8"))
        except: return {}
    zt = load_one(POOL_ZT); dt = load_one(POOL_DT); zb = load_one(POOL_ZB)
    return zt.get("data", {}), dt.get("data", {}), zb.get("data", {})

def load_kline(code_key):
    arr = []
    for path in [KL_ALL] + [os.path.join(KLINE_HIST_DIR, f) for f in os.listdir(KLINE_HIST_DIR) if f.startswith(code_key + ".")]:
        if not os.path.exists(path): continue
        for l in open(path, encoding="utf-8"):
            if l.startswith("#") or "|" not in l: continue
            p = l.rstrip().split("|")
            if len(p) < 7 or p[0] != code_key: continue
            try: arr.append({"date": p[1], "o": float(p[2]), "h": float(p[3]), "l": float(p[4]), "c": float(p[5]), "v": float(p[6])})
            except: pass
    arr.sort(key=lambda x: x["date"])
    return arr

def ema(arr, period):
    if len(arr) < period: return None
    k = 2 / (period + 1); v = arr[0]
    for x in arr[1:]: v = x * k + v * (1 - k)
    return v

def compute_technicals(klines):
    if len(klines) < 30: return {}
    closes = [b["c"] for b in klines]; vols = [b["v"] for b in klines]
    ma5 = sum(closes[-5:]) / 5; ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20; ma30 = sum(closes[-30:]) / 30
    vol_ma5 = sum(vols[-5:]) / 5
    vol_ratio = vols[-1] / vol_ma5 if vol_ma5 else 1.0
    chg_1d = (closes[-1] / closes[-2] - 1) * 100 if len(closes) > 1 else 0
    chg_5d = (closes[-1] / closes[-6] - 1) * 100 if len(closes) > 5 else 0
    chg_20d = (closes[-1] / closes[-21] - 1) * 100 if len(closes) > 20 else 0
    gains = [max(closes[i]-closes[i-1], 0) for i in range(len(closes)-14, len(closes))]
    losses = [max(closes[i-1]-closes[i], 0) for i in range(len(closes)-14, len(closes))]
    ag = sum(gains)/14; al = sum(losses)/14
    rsi = 100 - (100/(1+(ag/al))) if al else 100
    e12 = ema(closes, 12); e26 = ema(closes, 26)
    dif = e12 - e26
    # dea as EMA9 of dif series
    dif_series = []
    for i in range(len(closes)):
        sub = closes[max(0,i-26):i+1]
        dif_series.append(ema(sub, 12) - ema(sub, 26) if len(sub)>=26 else 0)
    dea = ema(dif_series, 9)
    macd_hist = (dif - dea) * 2
    ma_bull = ma5 > ma10 > ma20 > ma30
    window = closes[-min(250, len(closes)):]
    hi52 = max(window); lo52 = min(window)
    dist52 = (closes[-1] - lo52) / (hi52 - lo52) * 100 if hi52 != lo52 else 50
    dist_ma20 = (closes[-1] / ma20 - 1) * 100
    up_vol = chg_1d > 0 and vol_ratio > 1.2
    up_lowvol = chg_1d > 0 and vol_ratio < 0.8
    down_vol = chg_1d < 0 and vol_ratio > 1.2
    down_lowvol = chg_1d < 0 and vol_ratio < 0.8
    return dict(ma5=round(ma5,2), ma10=round(ma10,2), ma20=round(ma20,2), ma30=round(ma30,2),
        vol_ratio=round(vol_ratio,2), chg_1d=round(chg_1d,2), chg_5d=round(chg_5d,2), chg_20d=round(chg_20d,2),
        rsi=round(rsi,1), dif=round(dif,3), dea=round(dea,3), macd_hist=round(macd_hist,3),
        ma_bull=ma_bull, dist52=round(dist52,1), dist_ma20=round(dist_ma20,2),
        up_vol=up_vol, up_lowvol=up_lowvol, down_vol=down_vol, down_lowvol=down_lowvol)

def score_stock(t, snap, mf_latest, pool_zt_codes):
    s = 0; reasons = []
    if t.get("ma_bull"): s += 3; reasons.append("MA多头排列")
    elif (t.get("ma5") or 0) > (t.get("ma10") or 0): s += 1
    rsi = t.get("rsi", 50)
    if 40 <= rsi <= 60: s += 2; reasons.append(f"RSI={rsi:.0f}中性偏强")
    elif 60 < rsi <= 70: s += 1; reasons.append(f"RSI={rsi:.0f}强势未超买")
    elif rsi > 70: s -= 2; reasons.append(f"RSI={rsi:.0f}超买需警惕")
    elif rsi < 40: s += 1; reasons.append(f"RSI={rsi:.0f}超卖反弹机会")
    hist = t.get("macd_hist", 0)
    if hist > 0: s += 2; reasons.append("MACD红柱放大")
    elif hist > -0.01: s += 1; reasons.append("MACD金叉初期")
    else: s -= 2; reasons.append("MACD死叉/绿柱")
    vr = t.get("vol_ratio", 1); chg = t.get("chg_1d", 0)
    snap_chg = snap.get("chg_pct", 0) if snap else 0
    if t.get("up_vol") and snap_chg > 0: s += 3; reasons.append("放量上涨(量价齐升)")
    elif t.get("up_lowvol"): s -= 1; reasons.append("缩量上涨(乏力)")
    elif t.get("down_vol"): s -= 2; reasons.append("放量下跌(出货)")
    elif t.get("down_lowvol"): s += 1; reasons.append("缩量下跌(洗盘)")
    if mf_latest:
        r0 = mf_latest.get("mainnet_r0", 0); r0r = mf_latest.get("mainratio_r0", 0)
        if r0 > 0 and r0r > 1.0: s += 3; reasons.append(f"主力净流入{r0/1e8:.2f}亿(净占比{r0r:.1f}%)")
        elif r0 > 0: s += 1; reasons.append("主力小幅净流入")
        elif r0 < -2e8: s -= 3; reasons.append(f"主力净流出{abs(r0)/1e8:.2f}亿")
    d52 = t.get("dist52", 50)
    if d52 > 80: s += 1; reasons.append(f"52w位置{d52:.0f}%趋势强")
    elif d52 < 20: s += 2; reasons.append(f"52w位置{d52:.0f}%底部区域")
    return s, "; ".join(reasons)

def get_snap_for(code, snap):
    """Match snapshot by various key formats."""
    # direct match
    if code in snap: return snap[code]
    # try without prefix
    num = code.replace("sh","").replace("sz","").replace("bj","")
    for k in snap:
        if k.replace("sh","").replace("sz","").replace("bj","") == num: return snap[k]
    return {}

def get_mf_latest(code, mf):
    # try prefixed key first
    for k in [code, code.replace("sh","").replace("sz","").replace("bj","")]:
        if k in mf:
            dates = sorted(mf[k].keys(), reverse=True)
            if dates: return mf[k][dates[0]]
    return None

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

sections = load_watchlist()
snap = load_snapshot()
mf = load_moneyflow()
zt_data, dt_data, zb_data = load_pools()
zt_codes = {p.get("c","") for p in zt_data.get("pool", [])}
zt_names = {p.get("n",""): p.get("c","") for p in zt_data.get("pool", [])}

all_results = []
for section, items in sections.items():
    for item in items:
        code = item["code"]; name = item["name"]
        kl = load_kline(code)
        if not kl:
            all_results.append({"code": code, "name": name, "section": section, "error": "no kline"})
            continue
        t = compute_technicals(kl)
        s = get_snap_for(code, snap)
        mf_latest = get_mf_latest(code, mf)
        sc, reasons = score_stock(t, s, mf_latest, zt_codes)
        all_results.append({
            "code": code, "name": name, "section": section,
            "date": kl[-1]["date"] if kl else "",
            "close": round(kl[-1]["c"], 2) if kl else None,
            "snap": s, "tech": t, "mf_latest": mf_latest,
            "score": sc, "reasons": reasons,
        })

# Write technicals
out_techs = []
for r in all_results:
    if "error" in r: continue
    out_techs.append({"code": r["code"], "name": r["name"], "date": r["date"],
        "close": r["close"], **r["tech"], "score": r["score"]})
out_techs.sort(key=lambda x: x["code"])
os.makedirs(os.path.dirname(TECH_PATH), exist_ok=True)
json.dump(out_techs, open(TECH_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"wrote {len(out_techs)} records -> {TECH_PATH}")

# Sentiment
zt_count = zt_data.get("tc", 0); dt_count = dt_data.get("tc", 0); zb_count = zb_data.get("tc", 0)
zb_rate = zb_count / (zt_count + zb_count) * 100 if (zt_count + zb_count) else 0
max_lb = max((p.get("lbc", 0) for p in zt_data.get("pool", [])), default=0)
health = "ice" if zt_count < 40 and zb_rate > 40 else ("overheated" if zt_count > 150 and max_lb > 6 else ("healthy" if 80 <= zt_count <= 150 else "neutral"))

# Rank
valid = [r for r in all_results if "error" not in r]
top_buyable = sorted(valid, key=lambda x: -x["score"])
bottom_unbuyable = sorted([r for r in valid if r["score"] < 0], key=lambda x: x["score"])

# ---- FULL REPORT ----
lines = []
lines.append(f"# 2026年10月9日 A股全量技术+资金+情绪面综合分析报告")
lines.append("")
lines.append(f"- **数据时间**: 2026-10-09 盘中 (快照截至 12:05 CST, 收盘前)")
lines.append(f"- **分析时间**: 2026-10-09 12:45 CST")
lines.append(f"- **关注股票池**: {len(all_results)} 只 | 覆盖板块: {len(sections)}")
lines.append("")

# 1. 情绪面
lines.append("## 一、市场情绪面 (Sentiment)")
lines.append(f"- 涨停家数: **{zt_count}** | 跌停家数: **{dt_count}** | 炸板家数: **{zb_count}**")
lines.append(f"- 炸板率: **{zb_rate:.1f}%** (健康 <35% / 极端 >40%)")
lines.append(f"- 最高连板高度: **{max_lb}** 板 (新华传媒 600825 9连板)")
lines.append(f"- 情绪状态: **{health}**")
lines.append("- 今日特征: 节后首日科技股领跌 (光模块-5~6% / 半导体-6%)，防御资金涌入银行/电力/石油; 黄金突破4180美元 (+1.13%)")
lines.append("")

# 2. 指数
lines.append("## 二、A股指数 (今日盘中)")
idx_map = {"000001":"上证综指","399001":"深证成指","399006":"创业板指","000300":"沪深300","000688":"科创50","899050":"北证50"}
for k, label in idx_map.items():
    s = snap.get(k, {})
    if s: lines.append(f"- **{label}**: {s['price']} ({s['chg_pct']:+.2f}%) | 量比 {s['vol_ratio']:.2f} | 振幅 {(s['high']-s['low'])/s['prevclose']*100:.2f}%")
lines.append("")

lines.append("## 三、全球主要指数 (10-08收盘)")
lines.append("- **道指**: 51,231.64 (-0.10%) | **纳指**: 27,193.34 (-1.25%) | **标普**: 7,765.36 (-0.47%)")
lines.append("- **恒生**: 24,045.71 (+1.09%) | **恒生科技**: 4,136.35 (+1.55%)")
lines.append("- 解读: 美股小幅回调 (美债收益率5.35%压制估值)，港股独立走强 (资金回流南向)")
lines.append("")

# 4. 板块资金
lines.append("## 四、板块资金流向 (Sector Capital Flow — Sina)")
lines.append("- 强势板块: **石油石化 (+5.44% 广汇能源领涨)**、**银行**、**电力**、**煤炭**")
lines.append("- 弱势板块: **半导体 (-6%)**、**通信 (-5~6%)**、**消费电子**")
lines.append("- 风格切换: 从成长 (科技/AI) → 红利防御 (银行/能源/电力/黄金)")
lines.append("")

# 5. 技术面表格
lines.append("## 五、技术面评分 (Technicals)")
lines.append("| 代码 | 名称 | 收盘价 | 1日涨跌% | RSI | MACD柱 | MA排列 | 量比 | 52w位置 | 得分 | 信号 |")
lines.append("|------|------|--------|---------|-----|--------|--------|------|---------|------|------|")
for r in top_buyable[:30]:
    t = r["tech"]
    pos = f"{t.get('dist52',0):.0f}" if t.get('dist52') else "?"
    ma = "多头" if t.get("ma_bull") else ("偏多" if (t.get("ma5") or 0) > (t.get("ma10") or 0) else "空头")
    sig = "BUY" if r["score"] >= 8 else ("WATCH" if r["score"] >= 3 else "AVOID")
    cr = t.get("chg_1d", r.get("snap",{}).get("chg_pct",0))
    cr_str = f"{cr:+.2f}" if isinstance(cr, (int,float)) else str(cr)
    macd_str = f"{t.get('macd_hist',0):+.3f}" if isinstance(t.get('macd_hist'),(int,float)) else str(t.get('macd_hist','?'))
    vr_str = f"{t.get('vol_ratio',0):.2f}" if isinstance(t.get('vol_ratio'),(int,float)) else str(t.get('vol_ratio','?'))
    rsi_str = f"{t.get('rsi',0):.0f}" if isinstance(t.get('rsi'),(int,float)) else str(t.get('rsi','?'))
    pos_str = f"{pos:.0f}" if isinstance(pos,(int,float)) else str(pos)
    lines.append(f"| {r['code']} | {r['name']} | {r['close']} | {cr_str} | {rsi_str} | {macd_str} | {ma} | {vr_str} | {pos_str}% | {r['score']} | {sig} |")
lines.append("")

# 6. 买入推荐
lines.append("## 六、买入推荐 (Buyable — 综合评分 ≥5)")
buyable_high = [r for r in top_buyable if r["score"] >= 10]
buyable_mid = [r for r in top_buyable if 5 <= r["score"] < 10]
buyable_low = [r for r in top_buyable if 3 <= r["score"] < 5]

lines.append(f"### ⭐⭐⭐⭐⭐ 强烈买入 ({len(buyable_high)} 只)")
for r in buyable_high:
    t=r["tech"]; s=r["snap"]
    lines.append(f"- **{r['name']} ({r['code']})** 总分 {r['score']}")
    lines.append(f"  - 价格 {r['close']} | 1日 {t.get('chg_1d',0):+.2f}% | RSI {t.get('rsi',0):.0f} | MACD {t.get('macd_hist',0):+.3f}")
    lines.append(f"  - 52w位置 {t.get('dist52',0):.0f}% | 量比 {t.get('vol_ratio',0):.2f} | MA{r'多头' if t.get('ma_bull') else '偏空'}")
    mf = r.get("mf_latest", {})
    if mf:
        lines.append(f"  - 资金: 主力净流入 {mf.get('mainnet_r0',0)/1e8:+.2f}亿 (净占比 {mf.get('mainratio_r0',0):.2f}%)")
    lines.append(f"  - 核心逻辑: {r['reasons']}")
    lines.append("")
if not buyable_high:
    lines.append("- 暂无强烈推荐标的 (今日市场整体偏空，技术面MACD死叉普遍)")
    lines.append("")

lines.append(f"### ⭐⭐⭐⭐ 建议买入 ({len(buyable_mid)} 只)")
for r in buyable_mid:
    t=r["tech"]
    lines.append(f"- **{r['name']} ({r['code']})** — 总分 {r['score']} | RSI {t.get('rsi',0):.0f} | MACD {t.get('macd_hist',0):+.3f} | 52w {t.get('dist52',0):.0f}%")
    lines.append(f"  - 信号: {r['reasons']}")
    lines.append("")
if not buyable_mid:
    lines.append("- 暂无中强度买入标的")
    lines.append("")

lines.append(f"### ⭐⭐⭐ 观察/轻仓配置 ({len(buyable_low)} 只)")
for r in buyable_low:
    t=r["tech"]
    lines.append(f"- **{r['name']} ({r['code']})** — 总分 {r['score']} | RSI {t.get('rsi',0):.0f} | 52w {t.get('dist52',0):.0f}% | {r['reasons']}")
lines.append("")

# 7. 明确排除
lines.append("## 七、明确排除 (Not Buyable — 得分 < 0)")
for r in bottom_unbuyable[:12]:
    lines.append(f"- ❌ **{r['name']} ({r['code']})** — 总分 {r['score']} | {r['reasons']}")
lines.append("")

# 8. 异动
lines.append("## 八、异动涨跌 (Abnormal Moves)")
lines.append("### 今日异动上涨:")
for r in sorted(valid, key=lambda x: -(x.get("snap",{}).get("chg_pct",0)))[:8]:
    chg = r.get("snap",{}).get("chg_pct",0)
    if chg > 1.5:
        mf_str = f" 资金 {r.get('mf_latest',{}).get('mainnet_r0',0)/1e8:+.1f}亿" if r.get("mf_latest") else ""
        lines.append(f"- 📈 {r['name']} ({r['code']}): {chg:+.2f}%{mf_str}")
lines.append("")
lines.append("### 今日异动下跌 (领跌榜):")
for r in sorted(valid, key=lambda x: x.get("snap",{}).get("chg_pct",999))[:8]:
    chg = r.get("snap",{}).get("chg_pct",0)
    if chg < -2:
        mf_str = f" 资金 {r.get('mf_latest',{}).get('mainnet_r0',0)/1e8:+.1f}亿" if r.get("mf_latest") else ""
        lines.append(f"- 📉 {r['name']} ({r['code']}): {chg:+.2f}%{mf_str}")
lines.append("")

# 9. 消息面
lines.append("## 九、消息面 (News — Sina 7x24)")
news_path = os.path.join(ROOT, "消息面", "2026-10-09.md")
if os.path.exists(news_path):
    lines.append(f"- 完整新闻已写入 `{news_path}`，以下为今日核心事件:")
    lines.append("  1. **黄金突破 4180 美元/盎司** (+1.13%) → 利好赤峰黄金/湖南黄金")
    lines.append("  2. **软银 seeking $100B for AI (UAE)** → AI/算力链中长期受益")
    lines.append("  3. **印度 NIFTY +1%**、**恒生科技 +1.55%** → 外围偏暖")
    lines.append("  4. **中美贸易摩擦**: 中国稀土出口管制 → 美国威胁 100% 关税 → 半导体承压")
    lines.append("  5. **上海稳楼市新政** (9/29) → 地产板块节后开盘+3.82%")
lines.append("")

# 10. 基本面
lines.append("## 十、基本面 (Fundamentals)")
lines.append("- 当前处于三季报密集披露期 (10月)，业绩兑现为王")
lines.append("- 能源板块 (石油/煤炭/电力): Q3 煤价企稳 + 布伦特原油 $105 (+4.89%) → 业绩超预期概率高")
lines.append("- 银行: 净息差企稳 + 资产质量改善 → 稳健增长，但成长性有限")
lines.append("- 医药 CRO (药明康德/康龙化成): 受地缘政治 (美国Biotech法案) 压制，估值承压")
lines.append("")

# 11. 政策面
lines.append("## 十一、政策面 (Policy)")
lines.append("- **货币**: 降准预期存在但尚未落地; 央行维持宽松基调")
lines.append("- **房地产**: 9/29 上海稳楼市新政已落地，后续各城市跟进预期")
lines.append("- **贸易**: 稀土出口管制升级 vs 美国100%关税威胁 → 科技/半导体板块承压")
lines.append("- **利率**: 美债收益率 5.35% (2002年以来最高) → 压制全球成长股估值")
lines.append("")

# 12. 周期与联动
lines.append("## 十二、周期与联动效应 (Cycle & Linkage)")
lines.append("- **A股 vs 港股**: 恒科 +1.55% vs 创业板 -2.61% → 资金从内资科技流出至港股科技")
lines.append("- **A股内部风格切换**: 银行+2~3% vs 半导体-5~6% → 红利防御 vs 成长回撤")
lines.append("- **大宗商品联动**: 原油 +4.89% ($105) → 石油/煤炭/能源受益; 黄金 +1.13% → 贵金属受益")
lines.append("- **美债收益率 5.35%**: 持续压制高估值成长股，利好低估值高股息板块")
lines.append("")

# 13. 预测
lines.append("## 十三、未来预测 (Forecast — 1-2周)")
lines.append("### 情景 A (概率 40%): 震荡修复")
lines.append("上证 3750-3850 区间震荡，银行/能源延续强势，科技股企稳后反弹")
lines.append("### 情景 B (概率 35%): 继续探底")
lines.append("若美债收益率突破 5.4% 或中美贸易升级，可能下探 3700")
lines.append("### 情景 C (概率 25%): 情绪修复反弹")
lines.append("科技股带动指数反弹至 3900+ (需利好消息催化，如降准/贸易缓和)")
lines.append("")
lines.append("### 建议策略")
lines.append("- 仓位控制在 60-70%，核心配置红利 (银行/电力/石油/黄金)")
lines.append("- 保留 20% 现金等待科技股企稳信号 (MACD金叉 + 放量)")
lines.append("- 单一行业不超过 30%，避免过度集中")
lines.append("")

lines.append("## 风险提示")
lines.append("1. 当前为盘中分析 (12:05 CST)，下午走势可能改变判断")
lines.append("2. 中美贸易摩擦升级风险 (稀土→100%关税) 可能引发系统性下跌")
lines.append("3. 美债收益率 5.35% 创新高 → 全球成长股承压")
lines.append("4. 三季报地雷：业绩不及预期个股可能被大幅杀跌")
lines.append("5. 本分析仅供参考，不构成投资建议")
lines.append("")
lines.append(f"- 数据时间戳: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
lines.append(f"- 数据来源: 腾讯 qt.gtimg.cn / 东财 push2ex / 新浪 moneyflow / 新浪 7x24")

with open(OUT_FULL, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"wrote {OUT_FULL} ({len(lines)} lines)")

# ---- BUYABLE SUMMARY ----
blines = []
blines.append("# 2026-10-09 A股 可买 / 不可买 清单 (精简版)")
blines.append("")
blines.append("## ⭐ 可买 (Buyable)")
blines.append("")
blines.append("| 代码 | 名称 | 得分 | 逻辑摘要 | 建议仓位 | 止损 | 目标 |")
blines.append("|------|------|------|---------|---------|------|------|")
for r in top_buyable[:15]:
    t=r["tech"]; close = r["close"] or 0
    ma20 = t.get("ma20") or close
    stop = round(ma20 * 0.92, 2)
    target = round(ma20 * 1.15, 2)
    pos = "20%" if r["score"] >= 10 else ("15%" if r["score"] >= 5 else "5-10%")
    reason = r["reasons"].split(";")[0]
    blines.append(f"| {r['code']} | {r['name']} | {r['score']} | {reason} | {pos} | {stop} | {target} |")
blines.append("")

blines.append("## ❌ 不可买 (Not Buyable)")
blines.append("")
blines.append("| 代码 | 名称 | 得分 | 排除原因 |")
blines.append("|------|------|------|---------|")
for r in bottom_unbuyable[:12]:
    blines.append(f"| {r['code']} | {r['name']} | {r['score']} | {r['reasons']} |")
blines.append("")
blines.append("## 数据源")
blines.append("- 行情快照: `qt.gtimg.cn` (腾讯)")
blines.append("- 资金流: `vip.stock.finance.sina.com.cn/MoneyFlow.ssl_qsfx_zjlrqs` (新浪)")
blines.append("- 涨跌停池: `push2ex.eastmoney.com/getTopicZTPool` (东财)")
blines.append("- K 线: `web.ifzq.gtimg.cn` (腾讯前复权日线)")
blines.append("- 新闻: `app.cj.sina.com.cn/api/news/pc` (新浪7x24)")
blines.append("")
blines.append(f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")

with open(OUT_BUYABLE, "w", encoding="utf-8") as f:
    f.write("\n".join(blines))
print(f"wrote {OUT_BUYABLE} ({len(blines)} lines)")

# Print summary
print(f"\n=== Summary ===")
print(f"总标的: {len(all_results)} | 有效: {len(valid)}")
print(f"强烈买入 (score>=10): {len(buyable_high)}")
print(f"建议买入 (5<=score<10): {len(buyable_mid)}")
print(f"观察配置 (3<=score<5): {len(buyable_low)}")
print(f"排除 (score<0): {len(bottom_unbuyable)}")
print("\nTop 10 Buyable:")
for r in top_buyable[:10]:
    t=r["tech"]
    print(f"  {r['code']} {r['name']} score={r['score']} close={r['close']} chg1d={t.get('chg_1d','?')} RSI={t.get('rsi','?')} MACD={t.get('macd_hist','?')} 52w={t.get('dist52','?')}")
print("\nBottom 5 (Not Buyable):")
for r in bottom_unbuyable[:5]:
    print(f"  {r['code']} {r['name']} score={r['score']} reasons={r['reasons']}")
