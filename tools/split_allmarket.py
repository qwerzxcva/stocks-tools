#!/usr/bin/env python3
"""Split allmarket bulk shards into per-code kline files (CSV).

Input:  ~/workspace/stocks/data/allmarket/{day_qfq,week,month}_NN.csv
Output: ~/workspace/stocks-data-kline/data/{day,week,month}/{code}.csv
"""
import glob, os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.environ.get("GITHUB_WORKSPACE", "")
# local layout: sibling ~/workspace/stocks-data-kline; Actions: GITHUB_WORKSPACE is the kline repo itself
KLINE_REPO = WS or os.path.join(ROOT, "..", "stocks-data-kline")
SRC = os.environ.get("STOCKS_KLINE_SRC") or os.path.join(ROOT, "data", "allmarket")
DST = os.environ.get("STOCKS_KLINE_DST") or os.path.join(KLINE_REPO, "data")
META = os.environ.get("STOCKS_KLINE_META") or os.path.join(KLINE_REPO, "meta")
MAP = {"day_qfq": ("day", "qfq daily, ~800 bars"), "week": ("week", "qfq weekly, ~320 bars"),
       "month": ("month", "qfq monthly, ~320 bars")}
CODE_RE = re.compile(r"^(sh|sz|bj)\d{6}$")

for shard_name, (freq, desc) in MAP.items():
    data = {}
    for fn in sorted(glob.glob(os.path.join(SRC, f"{shard_name}_*.csv"))):
        code = None
        for line in open(fn, encoding="utf-8"):
            if line.startswith("# "):
                parts = line[2:].split()
                code = parts[0] if len(parts) == 1 and CODE_RE.match(parts[0]) else None
                continue
            if code is None or "|" not in line:
                continue
            p = line.rstrip("\n").split("|")
            if len(p) != 7 or p[0] != code:
                continue
            data.setdefault(code, []).append(",".join(p[1:]))
    outdir = os.path.join(DST, freq)
    os.makedirs(outdir, exist_ok=True)
    rows = 0
    for code, lines in data.items():
        with open(os.path.join(outdir, f"{code}.csv"), "w", encoding="utf-8") as f:
            f.write(f"# {code} tencent {desc}\n")
            f.write("date,open,close,high,low,volume\n")
            f.write("\n".join(lines) + "\n")
            rows += len(lines)
    print(f"{shard_name} -> data/{freq}/: {len(data)} codes, {rows} rows")

os.makedirs(META, exist_ok=True)
for src in ("universe.csv", "_progress.json"):
    p = os.path.join(SRC, src)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(META, src))
        print(f"meta/{src} copied")
print("done")
