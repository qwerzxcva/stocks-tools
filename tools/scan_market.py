#!/usr/bin/env python3
# scan full A-share market from eastmoney, save to data/market/all_YYYY-MM-DD.txt
# fields: code|name|price|chg%|vol|amount|turnover%|PE|volratio|mktcap|floatcap|PB|main_net|main_ratio%|superlarge|super_ratio%|industry
import json,urllib.request,sys,os,time
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120","Referer":"https://data.eastmoney.com/"}
UT="b2884a393a59ad64002292a3e90d46a5"
FS=("m%3A0+t%3A6+f%3A!2%2Cm%3A0+t%3A13+f%3A!2%2Cm%3A0+t%3A80+f%3A!2%"
    "m%3A1+t%3A2+f%3A!2%2Cm%3A1+t%3A23+f%3A!2%2Cm%3A0+t%3A7+f%3A!2%2Cm%3A1+t%3A3+f%3A!2")
FIELDS="f12%2Cf14%2Cf2%2Cf3%2Cf5%2Cf6%2Cf8%2Cf9%2Cf10%2Cf20%2Cf21%2Cf23%2Cf62%2Cf184%2Cf66%2Cf69%2Cf100"
HOSTS=["push2delay.eastmoney.com","push2.eastmoney.com","1.push2.eastmoney.com"]

def fetch_page(host,pn,pz=100,fid="f3"):
    url=(f"https://{host}/api/qt/clist/get?pn={pn}&pz={pz}&po=0&np=1&fltt=2&invt=2&ut={UT}"
         f"&fid={fid}&fs={FS}&fields={FIELDS}")
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=25))
        except Exception:
            if attempt<2: time.sleep(1.5)
    return None

def get_page(pn,pz=100):
    for h in HOSTS:
        d=fetch_page(h,pn,pz)
        if d and d.get('data') and d['data'].get('diff'):
            return d
    return None

root=sys.argv[1] if len(sys.argv)>1 else "/root/stocks"
date=sys.argv[2] if len(sys.argv)>2 else time.strftime("%Y-%m-%d",time.localtime())
out=os.path.join(root,"data/market")
os.makedirs(out,exist_ok=True)
F=os.path.join(out,f"all_{date}.txt")

first=get_page(1)
if not first:
    print("FAILED: cannot fetch page1",file=sys.stderr); sys.exit(1)
total=first['data']['total']
pages=(total+99)//100
print(f"total={total} pages={pages}")
rows=[]
rows.extend(first['data']['diff'])
for pn in range(2,pages+1):
    d=get_page(pn)
    if d and d.get('data') and d['data'].get('diff'):
        rows.extend(d['data']['diff'])
    else:
        print(f"  page {pn} failed",file=sys.stderr)
    if pn%10==0: print(f"  ...{pn}/{pages}",flush=True)
    time.sleep(0.25)

def g(x,k,d=0):
    v=x.get(k,d)
    return v if v is not None else d
with open(F,'w',encoding='utf-8') as f:
    f.write(f"# full market {date} (eastmoney) total={len(rows)}\n")
    f.write("# code|name|price|chg%|amount|turnover%|PE|volratio|mktcap|floatcap|PB|main_net|main_ratio%|superlarge|super_ratio%|industry\n")
    for x in rows:
        f.write("|".join([
            str(g(x,'f12','')),str(g(x,'f14','')),str(g(x,'f2',0)),str(g(x,'f3',0)),
            str(g(x,'f6',0)),str(g(x,'f8',0)),str(g(x,'f9',0)),str(g(x,'f10',0)),
            str(g(x,'f20',0)),str(g(x,'f21',0)),str(g(x,'f23',0)),str(g(x,'f62',0)),
            str(g(x,'f184',0)),str(g(x,'f66',0)),str(g(x,'f69',0)),str(g(x,'f100',''))
        ])+"\n")
print(f"saved {len(rows)} -> {F}")
