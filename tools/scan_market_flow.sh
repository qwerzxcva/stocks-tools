#!/bin/bash
# scan full market WITH multi-day capital flow (5d/10d main net) -> data/market/flow_YYYY-MM-DD.txt
# fields: f164=5日主力净额  f174=10日主力净额  f62=当日主力  f109/f160=多日涨跌/占比
# usage: bash scan_market_flow.sh [YYYY-MM-DD]
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
DATE="${1:-$(TZ=Asia/Shanghai date '+%Y-%m-%d')}"
OUT="$ROOT/data/market"
mkdir -p "$OUT"
TMP="/tmp/scanflow_$$"
mkdir -p "$TMP"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
UT="b2884a393a59ad64002292a3e90d46a5"
FS="m%3A0+t%3A6+f%3A!2%2Cm%3A0+t%3A13+f%3A!2%2Cm%3A0+t%3A80+f%3A!2%2Cm%3A1+t%3A2+f%3A!2%2Cm%3A1+t%3A23+f%3A!2%2Cm%3A0+t%3A7+f%3A!2%2Cm%3A1+t%3A3+f%3A!2"
FIELDS="f12%2Cf14%2Cf2%2Cf3%2Cf6%2Cf8%2Cf9%2Cf10%2Cf20%2Cf21%2Cf23%2Cf62%2Cf164%2Cf174%2Cf109%2Cf160%2Cf100"

fetch() {
  curl -s --max-time 25 \
    "https://$1/api/qt/clist/get?pn=$2&pz=100&po=0&np=1&fltt=2&invt=2&ut=$UT&fid=f3&fs=$FS&fields=$FIELDS" \
    -H "User-Agent: $UA" -H "Referer: https://data.eastmoney.com/"
}

for H in push2delay.eastmoney.com push2.eastmoney.com; do
  P1=$(fetch "$H" 1)
  echo "$P1" | grep -q '"total"' && break
  P1=""
done
[ -z "$P1" ] && { echo "FAILED page1"; exit 1; }
TOTAL=$(echo "$P1" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['total'])")
PAGES=$(( (TOTAL + 99) / 100 ))
echo "total=$TOTAL pages=$PAGES host=$H"
echo "$P1" > "$TMP/p1.json"
PN=2
while [ $PN -le $PAGES ]; do
  R=$(fetch "$H" $PN)
  echo "$R" | grep -q '"diff"' && echo "$R" > "$TMP/p$PN.json"
  PN=$((PN+1))
  sleep 0.2
done

python3 - "$TMP" "$OUT/flow_$DATE.txt" "$DATE" << 'PY'
import sys,json,os,glob
tmp,outf,date=sys.argv[1:4]
rows=[]
for f in sorted(glob.glob(os.path.join(tmp,"p*.json")),key=lambda x:int(os.path.basename(x)[1:-5])):
    try:
        rows.extend(json.load(open(f,encoding='utf-8'))['data']['diff'])
    except Exception: pass
seen={}; uniq=[]
for x in rows:
    c=x.get('f12')
    if c and c not in seen: seen[c]=1; uniq.append(x)
def g(x,k,d=0):
    v=x.get(k,d); return v if v is not None else d
with open(outf,'w',encoding='utf-8') as f:
    f.write(f"# full market + multiday flow {date} total={len(uniq)}\n")
    f.write("# code|name|price|chg%|amount|turnover%|PE|volratio|mktcap|floatcap|PB|main_today|main_5d|main_10d|chg_5d%|ratio_5d%|industry\n")
    for x in uniq:
        f.write("|".join([str(g(x,'f12','')),str(g(x,'f14','')),str(g(x,'f2',0)),str(g(x,'f3',0)),
            str(g(x,'f6',0)),str(g(x,'f8',0)),str(g(x,'f9',0)),str(g(x,'f10',0)),
            str(g(x,'f20',0)),str(g(x,'f21',0)),str(g(x,'f23',0)),str(g(x,'f62',0)),
            str(g(x,'f164',0)),str(g(x,'f174',0)),str(g(x,'f109',0)),str(g(x,'f160',0)),
            str(g(x,'f100',''))])+"\n")
print(f"saved {len(uniq)} -> {outf}")
PY
rm -rf "$TMP"
