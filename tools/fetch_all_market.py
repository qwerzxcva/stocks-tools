#!/usr/bin/env python3
"""
Bulk collector: full A-share + index/ETF klines (tencent) -> data/allmarket/
- day qfq/raw (800 bars ~3y), week (320), month (320 ~10y), m60 (320 bars)
- rate-limited, resumable, WAF-aware (pauses & retries)
- output: sharded CSVs (<90MB each) + universe.csv + _stats.json

usage: python3 tools/fetch_all_market.py [workers]
"""
import csv, json, os, sys, threading, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("STOCKS_KLINE_OUT") or os.path.join(ROOT, "data", "allmarket")
UNIVERSE = os.path.join(OUT, "universe.csv")
PROGRESS = os.path.join(OUT, "_progress.json")
STATS = os.path.join(OUT, "_stats.json")
FALLBACK_UNIVERSE = os.environ.get("STOCKS_UNIVERSE_FALLBACK") or os.path.join(ROOT, "data", "market", "all_2026-09-18.txt")
WATCHLIST = os.environ.get("STOCKS_WATCHLIST") or os.path.join(ROOT, "tools", "watchlist.txt")
if not os.path.exists(WATCHLIST):
    # Actions env: watchlist is in config/watchlist.txt instead of tools/watchlist.txt
    _alt = os.path.join(ROOT, "config", "watchlist.txt")
    WATCHLIST = _alt if os.path.exists(_alt) else WATCHLIST
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
FREQS = [("day_qfq", "day", 800, "qfq"), ("day_raw", "day", 800, ""), ("week", "week", 320, "qfq"),
         ("month", "month", 320, "qfq"), ("m60", "m60", 320, "")]
SHARDS = 10
WAF_WAIT = [30, 90, 240, 600, 1800]

lock = threading.Lock()
progress = {"done": {}, "failed": [], "waf_blocks": 0, "last_waf": 0}
if os.path.exists(PROGRESS):
    try:
        progress = json.load(open(PROGRESS, encoding="utf-8"))
    except Exception:
        pass

def save_progress():
    with lock:
        json.dump(progress, open(PROGRESS, "w", encoding="utf-8"))

def is_waf(body):
    return b"501page" in body[:400] or b"waf.tencent.com" in body[:400] or not body.startswith(b"{")

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://gu.qq.com/"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def fetch_kline(code, freq, cnt, fq):
    """Return list of 'date|open|close|high|low|vol' rows, or None on failure."""
    param = f"{code},{freq},,,{cnt}" + ("," + fq if fq else "")
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={param}"
    if freq == "m60":
        url = f"https://web.ifzq.gtimg.cn/appstock/app/kline/mkline/get?param={code},m60,,{cnt}"
    last_err = ""
    for waf_i in range(len(WAF_WAIT) + 1):
        for attempt in range(2):
            try:
                body = http_get(url)
                if is_waf(body):
                    raise ValueError("waf")
                d = json.loads(body.decode("utf-8", "replace"))
                inner = (d.get("data") or {}).get(code) or {}
                if fq:
                    arr = inner.get(f"qfq{freq}") or inner.get(freq) or []
                else:
                    arr = inner.get(freq) or []
                if freq == "m60":
                    arr = (inner.get("m60") or [])[0] if inner.get("m60") else []
                rows = []
                for r in arr:
                    if isinstance(r, list) and len(r) >= 6:
                        rows.append(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}")
                if rows:
                    return rows
                return None
            except ValueError:
                with lock:
                    progress["waf_blocks"] += 1
                    progress["last_waf"] = time.time()
                wait = WAF_WAIT[min(waf_i, len(WAF_WAIT) - 1)]
                if waf_i == len(WAF_WAIT):
                    return None
                print(f"  WAF blocked, waiting {wait}s ...", flush=True)
                time.sleep(wait)
                break
            except Exception as e:
                last_err = str(e)[:80]
                time.sleep(2)
    return None

def load_universe():
    """code|name|industry,sh|... ; try eastmoney clist, fallback to last snapshot file."""
    rows = []
    try:
        fs = ("m%3A0%2Bt%3A6%2Cm%3A0%2Bt%3A13%2Cm%3A0%2Bt%3A80%2Cm%3A1%2Bt%3A2%2C"
              "m%3A1%2Bt%3A23%2Cm%3A0%2Bt%3A7%2Cm%3A1%2Bt%3A3%2Cm%3A0%2Bt%3A81")
        url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=6000&po=0&np=1&fltt=2&invt=2"
               f"&ut=b2884a393a59ad64002292a3e90d46a5&fid=f12&fs={fs}&fields=f12,f14,f13")
        body = http_get(url, 25)
        if not is_waf(body):
            d = json.loads(body.decode())
            diff = (d.get("data") or {}).get("diff") or []
            for x in diff:
                c = str(x.get("f12", ""))
                if c and str(x.get("f3", "")).replace(".", "") != "-":
                    mkt = "sh" if c[0] == "6" else ("bj" if c.startswith(("8", "4", "9")) else "sz")
                    rows.append(f"{mkt}{c}|{x.get('f14','')}|{mkt}")
            if rows:
                print(f"universe from eastmoney clist: {len(rows)}", flush=True)
    except Exception as e:
        print(f"clist failed ({e}), using fallback", flush=True)
    if not rows and os.path.exists(FALLBACK_UNIVERSE):
        for l in open(FALLBACK_UNIVERSE, encoding="utf-8"):
            if l.startswith("#") or "|" not in l:
                continue
            p = l.rstrip().split("|")
            if len(p) < 2:
                continue
            c, name = p[0], p[1]
            if not c or c.startswith("-"):
                continue
            mkt = "sh" if c[0] == "6" else ("bj" if c.startswith(("8", "4", "9")) else "sz")
            rows.append(f"{mkt}{c}|{name}|{mkt}")
        print(f"universe from fallback file: {len(rows)}", flush=True)
    # Support STOCKS_UNIVERSE_FILE for Actions env (e.g., meta/universe.csv with format: code|name|market)
    uf = os.environ.get("STOCKS_UNIVERSE_FILE")
    if uf and os.path.exists(uf):
        extras = []
        for l in open(uf, encoding="utf-8"):
            if l.startswith("#") or "|" not in l: continue
            p = l.rstrip().split("|")
            if len(p) < 3: continue
            c,name,mkt = p[0].strip(), p[1].strip(), p[2].strip()
            if c: extras.append(f"{c}|{name}|{mkt}")
        seen = {r.split("|")[0] for r in rows}
        rows += [e for e in extras if e.split("|")[0] not in seen]
        print(f"universe from STOCKS_UNIVERSE_FILE: +{len(extras)} codes (total {len(rows)})", flush=True)
    # add watchlist indices & ETFs
    seen = {r.split("|")[0] for r in rows}
    for l in open(WATCHLIST, encoding="utf-8"):
        l = l.strip()
        if not l or l.startswith("#") or l.startswith("["):
            continue
        c = l.split()[0]
        if c not in seen:
            rows.append(f"{c}|{c}|{c[:2]}")
    os.makedirs(OUT, exist_ok=True)
    with open(UNIVERSE, "w", encoding="utf-8") as f:
        f.write("# code|name|market\n")
        for r in rows:
            f.write(r + "\n")
    return [r.split("|")[0] for r in rows]

def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    os.makedirs(OUT, exist_ok=True)
    universe = load_universe()
    print(f"total codes: {len(universe)}", flush=True)
    # shard openers: code -> shard index
    shard_map = {c: i for i, c in enumerate(universe)}
    freq_files = {}
    for fq, *_ in FREQS:
        freq_files[fq] = {}
        for i in range(SHARDS):
            p = os.path.join(OUT, f"{fq}_{i:02d}.csv")
            freq_files[fq][i] = open(p, "a", encoding="utf-8")
            freq_files[fq][i].write(f"# allmarket {fq} shard {i} (code|date|open|close|high|low|vol)\n")

    # resume: skip codes already fully done (all FREQS fetched)
    done_set = {c for c, n in progress.get("done", {}).items() if n == len(FREQS)}
    todo = [c for c in universe if c not in done_set]

    q = list(universe)
    idx = 0
    stop = threading.Event()

    def worker():
        nonlocal idx
        while not stop.is_set():
            with lock:
                if idx >= len(q):
                    break
                c = q[idx]
                idx += 1
            if c in done_set:
                continue
            got = 0
            for fq, freq, cnt, qfq in FREQS:
                rows = fetch_kline(c, freq, cnt, qfq)
                if rows:
                    sh = shard_map.get(c, 0) % SHARDS
                    with lock:
                        f = freq_files[fq][sh]
                        f.write(f"# {c}\n")
                        for row in rows:
                            f.write(f"{c}|{row}\n")
                        f.flush()
                    got += 1
                time.sleep(0.25)
            if got == len(FREQS):
                with lock:
                    progress["done"][c] = got
                done_set.add(c)
            else:
                with lock:
                    progress["failed"].append({"code": c, "got": got, "need": len(FREQS)})
                    progress["done"][c] = got
            save_progress()
            if len(done_set) % 200 == 0:
                print(f"progress {len(done_set)}/{len(universe)} failed={len(progress['failed'])}", flush=True)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for i in range(SHARDS):
        for fq in freq_files:
            freq_files[fq][i].close()
    total_bytes = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".csv"))
    stats = {"codes": len(universe), "complete": len([c for c in universe if c in progress.get("done", {}) and progress["done"][c] == len(FREQS)]),
             "failed": len(progress.get("failed", [])), "csv_bytes": total_bytes, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(stats, open(STATS, "w", encoding="utf-8"), indent=1)
    print(f"DONE {stats}", flush=True)

if __name__ == "__main__":
    main()
