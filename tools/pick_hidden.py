#!/usr/bin/env python3
# find "hidden" / low-profile candidates: not on hot radars, but quietly turning up
#
# what "hidden" means here (all must hold):
#   A. not crowded  : NOT in top-150 by turnover amount, NOT in top-30 by main net inflow
#   B. low position : price below MA30 by >8% (oversold / not yet repaired)
#   C. just turned  : close > MA5 AND MA5 >= previous-day MA5 (short-term turning up)
#   D. capital in   : main_net > 0, main_ratio >= 1.0% (real money, not retail)
#   E. waking up    : vol_ratio 1.1-3.0 (volume picking up, not exploded)
#   F. started small: today 0.5%-6% gain (moved, but NOT limit-up -> still off radars)
#   G. sanity       : PE 0-80, mktcap >= 30亿, turnover 0.8-15%, no ST/退
import sys,os,json,subprocess,time
root=sys.argv[1] if len(sys.argv)>1 else "/root/stocks"
date=sys.argv[2] if len(sys.argv)>2 else "2026-09-18"
mf=os.path.join(root,"data/market",f"all_{date}.txt")
if not os.path.exists(mf):
    print("missing",mf,file=sys.stderr); sys.exit(1)

rows=[]
for l in open(mf,encoding='utf-8'):
    if l.startswith('#'): continue
    p=l.rstrip('\n').split('|')
    if len(p)<16: continue
    try:
        rows.append({"code":p[0],"name":p[1],"price":float(p[2]),"chg":float(p[3]),
            "amount":float(p[4]),"turnover":float(p[5]),"pe":float(p[6]),
            "volratio":float(p[7]),"mktcap":float(p[8]),"floatcap":float(p[9]),
            "pb":float(p[10]),"main":float(p[11]),"main_ratio":float(p[12]),
            "sup":float(p[13]),"sup_ratio":float(p[14]),"ind":p[15]})
    except Exception: continue

def bad(r):
    n=r['name']
    if 'ST' in n or '退' in n or 'N' == n[:1]: return True
    if r['price']<=0 or r['amount']<=0: return True
    if r['pe']<=0 or r['pe']>80: return True
    if r['mktcap']<3e9: return True
    if r['turnover']<0.8 or r['turnover']>15: return True
    if r['volratio']<1.1 or r['volratio']>3.0: return True
    if r['chg']<0.5 or r['chg']>6.0: return True
    if r['main']<=0: return True
    if r['main_ratio']<1.0: return True
    return False

cand=[r for r in rows if not bad(r)]
print(f"全市场 {len(rows)} → 基础过滤后 {len(cand)}")

hot={r['code'] for r in sorted(rows,key=lambda x:-x['amount'])[:150]}
hot|={r['code'] for r in sorted(rows,key=lambda x:-x['main'])[:30]}
cand=[r for r in cand if r['code'] not in hot]
print(f"剔除热门(成交额前150 / 主力净流入前30) → {len(cand)}")

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
def kline(code):
    pre='sh' if code[0]=='6' else ('sz' if code[0] in ('0','3') else 'bj')
    full=pre+code
    u=f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={full},day,,,60,qfq"
    try:
        r=subprocess.run(["curl","-s","--max-time","15",u,"-H",f"User-Agent: {UA}"],
                         capture_output=True,text=True,timeout=20)
        d=json.loads(r.stdout)
        arr=d['data'][full].get('qfqday') or d['data'][full].get('day')
        if not arr: return None
        return [float(x[2]) for x in arr]   # close
    except Exception:
        return None

print(f"逐只校验均线位置与超跌幅度 ({len(cand)} 只)...")
res=[]
for i,r in enumerate(cand):
    cl=kline(r['code'])
    if not cl or len(cl)<31: continue
    ma5=sum(cl[-5:])/5; ma10=sum(cl[-10:])/10; ma20=sum(cl[-20:])/20; ma30=sum(cl[-30:])/30
    last=cl[-1]
    prev_ma5=sum(cl[-6:-1])/5
    below30=(last/ma30-1)*100
    turn_up = last>ma5 and ma5>=prev_ma5
    if not (below30 < -8.0 and turn_up): continue
    r.update({"ma5":round(ma5,2),"ma10":round(ma10,2),"ma20":round(ma20,2),"ma30":round(ma30,2),
              "below_ma30_pct":round(below30,2),"dist_ma20_pct":round((last/ma20-1)*100,2),
              "chg20":round((last/cl[-21]-1)*100,2),"chg60":round((last/cl[-61]-1)*100,2) if len(cl)>61 else 0})
    res.append(r)
    if (i+1)%30==0: print(f"  ...{i+1}/{len(cand)} 命中{len(res)}",flush=True)
    time.sleep(0.1)

# score: deeper oversold + stronger capital + just-turned + not yet run
for r in res:
    r['score'] = round(
        (-r['below_ma30_pct'])*1.0 + min(r['main_ratio'],8)*1.5 + min(r['volratio'],3)*2
        + (2 if r['sup_ratio']>2 else 0) - (3 if r['chg']>5 else 0), 2)
res.sort(key=lambda r:-r['score'])

print(f"\n=== 低调票候选 {len(res)} 只 ===")
print(f"{'代码':<7s}{'名称':<9s}{'行业':<10s}{'现价':>7s}{'涨%':>6s}{'距MA30%':>8s}{'20日%':>7s}{'主力亿':>7s}{'净占%':>6s}{'超大单%':>7s}{'量比':>5s}{'换手%':>6s}{'市值亿':>7s}{'PE':>6s}{'分':>6s}")
for r in res[:35]:
    print(f"{r['code']:<7s}{r['name'][:8]:<9s}{r['ind'][:8]:<10s}{r['price']:>7.2f}{r['chg']:>6.2f}{r['below_ma30_pct']:>8.2f}{r['chg20']:>7.2f}{r['main']/1e8:>7.2f}{r['main_ratio']:>6.2f}{r['sup_ratio']:>7.2f}{r['volratio']:>5.2f}{r['turnover']:>6.2f}{r['mktcap']/1e8:>7.0f}{r['pe']:>6.1f}{r['score']:>6.1f}")

out=os.path.join(root,"data/research"); os.makedirs(out,exist_ok=True)
json.dump(res,open(os.path.join(out,f"hidden_{date}.json"),'w'),ensure_ascii=False,indent=1)
print(f"\nsaved -> data/research/hidden_{date}.json  ({len(res)})")
