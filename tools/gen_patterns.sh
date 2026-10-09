#!/bin/bash
# mine patterns: sentiment -> next-day index move; capital flow -> next-day stock move
# usage: bash gen_patterns.sh   (appends to data/research/patterns.md)
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
OUT="$ROOT/data/research/patterns.md"
mkdir -p "$ROOT/data/research"

python3 - "$ROOT" > "$OUT" << 'PY'
import json,sys,os
root=sys.argv[1]

# load emotion
emo=[]
p=os.path.join(root,'data/emotion.jsonl')
if os.path.exists(p):
    emo=[json.loads(l) for l in open(p) if l.strip()]
    emo.sort(key=lambda x:x['date'])

# load index closes
idx={}
for l in open(os.path.join(root,'data/kline/all.txt')):
    f=l.strip().split('|')
    if len(f)==7 and f[0]=='sh000001': idx[f[1]]=float(f[3])
dts=sorted(idx)

print("# patterns (auto-generated, do not edit)")
print()
print("## sentiment -> next-day SHComp")
print("| date | zt | dt | zb_rate% | max_lb | next_day_SHComp% |")
print("|---|---|---|---|---|---|")
for e in emo:
    d=e['date']; nxt=None
    if d in dts:
        j=dts.index(d)
        if j+1<len(dts): nxt=(idx[dts[j+1]]/idx[d]-1)*100
    print(f"| {d} | {e['zt']} | {e['dt']} | {e['zb_rate']} | {e['max_lb']} | {f'{nxt:+.2f}' if nxt is not None else '—'} |")

n=len([e for e in emo if e['date'] in dts])
print()
print(f"sample size: {n} days — too small for statistical significance; accumulate daily.")
print()
print("## hypothesis to test (need >=30 samples)")
print("1. zb_rate >35% (chasing-high loses money) -> next day index weak / zt count down")
print("2. zb_rate <15% + dt <10 -> healthy, trend likely continues")
print("3. max_lb >=6 (sentiment ceiling) -> next day fade risk high")
print()
print("## notes")
print("- this file regenerates on each run; keep raw data (emotion.jsonl, kline) as source of truth")
PY

echo "patterns: $OUT"
