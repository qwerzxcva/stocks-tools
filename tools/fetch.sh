#!/bin/bash
# fetch daily data: kline, snapshot, sector, pools, moneyflow
# usage: bash fetch.sh [YYYY-MM-DD]  (default: today CST)
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
DATA="$ROOT/data"
DATE="${1:-$(date -u -d '+8 hours' '+%Y-%m-%d')}"
D="${DATE//-/}"
mkdir -p "$DATA"/{kline,snapshot,sector,pool,moneyflow}
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

CODES=$(grep -v '^\s*\(#\|\[\|$\)' "$DIR/watchlist.txt" | awk '{print $1}')

echo "== fetch $DATE =="

# 1. kline (tencent, rolling 60d, dedup merge)
KL="$DATA/kline/all.txt"
: > /tmp/_kl_new.txt
for c in $CODES; do
  curl -s --max-time 20 "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=$c,day,,,60,qfq" \
    | grep -o '\["20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]"[^]]*\]' \
    | sed 's/[]["]//g' | awk -v c="$c" -F, '{print c"|"$1"|"$2"|"$3"|"$4"|"$5"|"$6}' >> /tmp/_kl_new.txt
done
cat /tmp/_kl_new.txt "$KL" 2>/dev/null | awk -F'|' '!seen[$1"|"$2]++' | sort -t'|' -k1,1 -k2,2 > /tmp/_kl_m.txt
mv /tmp/_kl_m.txt "$KL"

# 2. snapshot (latest only)
SNAPFILE="$DATA/snapshot/latest.txt"
{
echo "# snapshot $DATE  fields: code|name|price|prevclose|open|vol|amount|chg%|turnover%|high|low|volratio"
echo "$CODES" | tr '\n' ',' | sed 's/,$//' > /tmp/_codes.txt
curl -s --max-time 40 "https://qt.gtimg.cn/q=$(cat /tmp/_codes.txt)" | iconv -f gbk -t utf-8 2>/dev/null \
  | tr ';' '\n' | grep '^v_' | while IFS= read -r line; do
    b="${line#*=}"; b="${b#\"}"; b="${b%\"}"
    echo "$b" | awk -F'~' 'NF>40 {printf "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n", $3,$2,$4,$5,$6,$7,$38,$33,$39,$34,$35,$50}'
  done
} > "$SNAPFILE"

# 3. sector (sina)
curl -s --max-time 20 "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php" -H "Referer: https://finance.sina.com.cn" \
  | iconv -f gbk -t utf-8 2>/dev/null > "$DATA/sector/latest.txt"

# 4. pools (eastmoney)
for p in ztpool:getTopicZTPool dtpool:getTopicDTPool zbpool:getTopicZBPool; do
  name="${p%%:*}"; api="${p##*:}"
  curl -s --max-time 25 "https://push2ex.eastmoney.com/${api}?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date=$D" \
    -H "Referer: https://quote.eastmoney.com/" -H "User-Agent: $UA" > "$DATA/pool/$D.$name.json"
  sleep 1
done

# 5. moneyflow (sina)
MFFILE="$DATA/moneyflow/latest.txt"
{
echo "# moneyflow $DATE  fields: code|date|close|chg%|turnover%|netinflow|netrate%|mainnet(r0)|mainrate%"
for c in $CODES; do
  curl -s --max-time 15 "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_qsfx_zjlrqs?daima=$c" \
    -H "Referer: https://finance.sina.com.cn" 2>/dev/null \
    | grep -o '{"opendate"[^}]*}' | head -6 | while IFS= read -r rec; do
      echo "$rec" | awk -v c="$c" -F'","' '{
        d=$1; gsub(/"?.*:/,"",d); gsub(/"/,"",d)
        t=$2; gsub(/"?.*:/,"",t); gsub(/"/,"",t)
        cr=$3; gsub(/"?.*:/,"",cr); gsub(/"/,"",cr)
        to=$4; gsub(/"?.*:/,"",to); gsub(/"/,"",to)
        na=$5; gsub(/"?.*:/,"",na); gsub(/"/,"",na)
        ra=$6; gsub(/"?.*:/,"",ra); gsub(/"/,"",ra)
        r0=$7; gsub(/"?.*:/,"",r0); gsub(/"/,"",r0)
        r0r=$8; gsub(/"?.*:/,"",r0r); gsub(/"/,"",r0r)
        printf "%s|%s|%s|%s|%s|%s|%s|%s|%s\n", c,d,t,cr,to,na,ra,r0,r0r
      }'
    done
  sleep 0.3
done
} > "$MFFILE"

echo "== done =="
echo "kline: $(wc -l < "$KL") lines"
echo "snapshot: $(wc -l < "$SNAPFILE") lines"
echo "moneyflow: $(wc -l < "$MFFILE") lines"
