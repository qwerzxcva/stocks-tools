#!/bin/bash
# fetch macro: US indices, commodities, asia
# usage: bash fetch_macro.sh [YYYY-MM-DD]
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
DATE="${1:-$(date -u -d '+8 hours' '+%Y-%m-%d')}"
OUT="$ROOT/data/macro/latest.txt"
mkdir -p "$ROOT/data/macro"

{
echo "# macro $DATE CST"
echo "# type|name|last|chg|chg%|time"
for p in "usDJI:Dow" "usIXIC:Nasdaq" "usINX:SP500" "usNDX:Nasdaq100"; do
  c="${p%%:*}"; nm="${p##*:}"
  curl -s --max-time 15 "https://qt.gtimg.cn/q=$c" | iconv -f gbk -t utf-8 2>/dev/null \
    | awk -F'~' -v nm="$nm" 'NF>40{printf "US|%s|%s|%s|%s|%s\n", nm, $4, $32, $33, $31}'
done
for pair in "hf_CL:WTI" "hf_OIL:Brent" "hf_XAU:Gold" "hf_XAG:Silver"; do
  c="${pair%%:*}"; nm="${pair##*:}"
  curl -s --max-time 15 "https://qt.gtimg.cn/q=$c" | iconv -f gbk -t utf-8 2>/dev/null \
    | sed 's/^[^"]*"//; s/".*//' \
    | awk -F',' -v nm="$nm" 'NF>6{printf "CMD|%s|%s|%s|%s|%s\n", nm, $1, $2, $3, $7}'
done
for c in hkHSI hkHSCEI; do
  curl -s --max-time 12 "https://qt.gtimg.cn/q=$c" | iconv -f gbk -t utf-8 2>/dev/null \
    | awk -F'~' 'NF>10{printf "HK|%s|%s|%s|%s|%s\n", $2, $4, $5, $6, $31}'
done
} > "$OUT"

curl -s --max-time 15 "https://hq.sinajs.cn/list=hf_CHA50CFD" -H "Referer: https://finance.sina.com.cn" 2>/dev/null \
  | iconv -f gbk -t utf-8 | sed 's/var hq_str_hf_CHA50CFD=//' \
  | awk -F'[",]' '{if(NF>3)printf "FUT|A50|%s|%s|%s|%s\n", $1, $3, $4, $12}' >> "$OUT"

cat "$OUT"
