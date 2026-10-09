#!/usr/bin/env python3
# batch-fetch kline closes for candidate codes (parallel via xargs curl) -> cache json
# usage: klcache.py <codes_file> <out_json>
import sys,os,json,subprocess,tempfile
codes=[l.strip() for l in open(sys.argv[1]) if l.strip()]
out=sys.argv[2]
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"

def pre(code):
    if code.startswith('6'): return 'sh'+code
    if code.startswith(('0','3')): return 'sz'+code
    return 'bj'+code

# build a bash script that curls all in parallel
fd,script=tempfile.mkstemp(suffix='.sh')
with os.fdopen(fd,'w') as f:
    f.write("#!/bin/bash\n")
    for c in codes:
        full=pre(c)
        u=f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={full},day,,,60,qfq"
        f.write(f'echo "====={c}"; curl -s --max-time 12 "{u}" -H "User-Agent: {UA}"; echo\n')
os.chmod(script,0o755)
r=subprocess.run(["bash",script],capture_output=True,text=True,timeout=len(codes)*3+120)
os.unlink(script)

res={}
cur=None
for line in r.stdout.split('\n'):
    if line.startswith('====='):
        cur=line[5:].strip()
    elif cur and line.strip().startswith('{'):
        try:
            d=json.loads(line)
            arr=d['data'][pre(cur)].get('qfqday') or d['data'][pre(cur)].get('day')
            if arr:
                res[cur]=[float(x[2]) for x in arr]
        except Exception:
            pass
        cur=None
json.dump(res,open(out,'w'))
print(f"cached {len(res)}/{len(codes)} -> {out}")
