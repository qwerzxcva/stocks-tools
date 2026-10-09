#!/bin/bash
# fetch eastmoney capital flow (fills the gap left by quantplay.cn paywall)
#   - sector flow  (BKxxxx)   -> data/capflow/sector.txt
#   - stock flow   (top net inflow) -> data/capflow/stock.txt
# usage: bash fetch_capflow.sh [YYYY-MM-DD]
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
DATE="${1:-$(TZ=Asia/Shanghai date '+%Y-%m-%d')}"
OUT="$ROOT/data/capflow"
mkdir -p "$OUT"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
REF="https://data.eastmoney.com/"
UT="b2884a393a59ad64002292a3e90d46a5"

SEC="https://push2.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=40&pn=1&np=1&fltt=2&invt=2&ut=${UT}&fs=m%3A90+t%3A2&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184"
STK="https://push2.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=40&pn=1&np=1&fltt=2&invt=2&ut=${UT}&fs=m%3A0+t%3A6+f%3A!2%2Cm%3A0+t%3A13+f%3A!2%2Cm%3A0+t%3A80+f%3A!2%2Cm%3A1+t%3A2+f%3A!2%2Cm%3A1+t%3A23+f%3A!2%2Cm%3A0+t%3A7+f%3A!2%2Cm%3A1+t%3A3+f%3A!2&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69"

# push2.eastmoney.com often drops/blocks; push2delay works (delayed data, fine for review).
# several hosts tried in order; each retried 3x.
HOSTS_CSV="push2delay.eastmoney.com,push2.eastmoney.com,1.push2.eastmoney.com"

python3 - "$DATE" "$OUT" "$UA" "$REF" "$UT" "$HOSTS_CSV" << 'PY'
import sys,json,urllib.request,time
date,out,ua,ref,ut,hosts_csv=sys.argv[1:7]
HOSTS=[h for h in hosts_csv.split(',') if h]
def build(host,fs,fields,pz=40):
    return (f"https://{host}/api/qt/clist/get?fid=f62&po=1&pz={pz}&pn=1&np=1&fltt=2&invt=2&ut={ut}"
            f"&fs={fs}&fields={fields}")
def get(url):
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url,headers={"User-Agent":ua,"Referer":ref}),timeout=25))
        except Exception:
            if attempt<2: time.sleep(2)
    return None
def try_hosts(fs,fields,pz=40):
    for h in HOSTS:
        d=get(build(h,fs,fields,pz))
        if d and d.get('data'): return d
    return None

SEC_FS="m%3A90+t%3A2"
SEC_FIELDS="f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184"
STK_FS="m%3A0+t%3A6+f%3A!2%2Cm%3A0+t%3A13+f%3A!2%2Cm%3A0+t%3A80+f%3A!2%2Cm%3A1+t%3A2+f%3A!2%2Cm%3A1+t%3A23+f%3A!2%2Cm%3A0+t%3A7+f%3A!2%2Cm%3A1+t%3A3+f%3A!2"
STK_FIELDS="f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69"

d=try_hosts(SEC_FS,SEC_FIELDS)
sfile=f"{out}/sector_{date}.txt"
if d and d.get('data'):
    rows=[(x.get('f12',''),x.get('f14',''),x.get('f3',0),x.get('f62',0),x.get('f184',0)) for x in d['data']['diff']]
    with open(sfile,'w',encoding='utf-8') as f:
        f.write(f"# sector capital flow {date} (eastmoney)\n")
        f.write("# code|name|chg%|main_net_inflow(yuan)|net_ratio%\n")
        for r in rows:
            f.write(f"{r[0]}|{r[1]}|{r[2]}|{r[3]:.0f}|{r[4]}\n")
    print(f"sector: {len(rows)} -> {sfile}")
    print("TOP12 板块主力净流入:")
    for r in rows[:12]:
        print(f"  {r[1]:<22s} {r[2]:+6.2f}%  {r[3]/1e8:+7.2f}亿  净占比{r[4]}%")
else:
    print("sector: FAILED (all hosts)",file=sys.stderr)

d=try_hosts(STK_FS,STK_FIELDS)
kfile=f"{out}/stock_{date}.txt"
if d and d.get('data'):
    rows=[(x.get('f12',''),x.get('f14',''),x.get('f2',0),x.get('f3',0),x.get('f62',0),x.get('f184',0),x.get('f66',0),x.get('f69',0)) for x in d['data']['diff']]
    with open(kfile,'w',encoding='utf-8') as f:
        f.write(f"# stock capital flow {date} (eastmoney, top main net inflow)\n")
        f.write("# code|name|price|chg%|main_net_inflow|net_ratio%|superlarge_net|superlarge_ratio%\n")
        for r in rows:
            f.write(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]:.0f}|{r[5]}|{r[6]:.0f}|{r[7]}\n")
    print(f"stock: {len(rows)} -> {kfile}")
    print("TOP15 个股主力净流入:")
    for r in rows[:15]:
        print(f"  {r[1]:<10s} {r[0]} {r[3]:+6.2f}%  {r[4]/1e8:+6.2f}亿  超大单占比{r[7]}%")
else:
    print("stock: FAILED (all hosts)",file=sys.stderr)
PY
