#!/bin/bash
# fetch one kline (eastmoney) -> /tmp/kl/<code>.json  raw response saved
c="$1"
# secid: 1=沪(sh), 0=深(sz/bj)
case "$c" in
  6*) m="1" ;;
  *)  m="0" ;;
esac
u="https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=$m.$c&klt=101&fqt=1&lmt=60&end=20500101&fields1=f1,f2,f3&fields2=f51,f53"
curl -s --max-time 12 "$u" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120" -H "Referer: https://quote.eastmoney.com/" -o "/tmp/kl/$c.json"
