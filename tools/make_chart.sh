#!/bin/bash
# SVG candlestick chart from kline data (awk only)
# usage: bash make_chart.sh <kline.txt> <out.svg> <title> [lastN]
set -u
IN="$1"; OUT="$2"; TITLE="${3:-chart}"; N="${4:-30}"

awk -F'|' -v out="$OUT" -v title="$TITLE" -v n="$N" '
BEGIN {
  W=1000; H=420; ML=60; MR=20; MT=40; MB=50;
  pw=W-ML-MR; ph=H-MT-MB;
}
{
  # group by code
  if ($1 != last) { if (cnt>0) flush(); last=$1; cnt=0 }
  cnt++; d[cnt]=$2; o[cnt]=$3+0; c[cnt]=$4+0; h[cnt]=$5+0; l[cnt]=$6+0; v[cnt]=$7+0
}
function flush(  i,s,e,mn,mx,step,bw,x,y,pv,sc,i2,start,cum,volmax,vy) {
  if (cnt<2) return
  s = (cnt>n)? cnt-n+1 : 1; e = cnt
  mn=1e18; mx=-1e18
  for (i=s;i<=e;i++) { if (l[i]<mn) mn=l[i]; if (h[i]>mx) mx=h[i] }
  pad=(mx-mn)*0.08; if (pad==0) pad=mx*0.01
  mn-=pad; mx+=pad
  sc=ph/(mx-mn)
  bw=pw/(e-s+1)*0.6
  volmax=0; for (i=s;i<=e;i++) if (v[i]>volmax) volmax=v[i]
  print "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" > out
  print "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\""W"\" height=\""H"\" font-family=\"sans-serif\">" > out
  print "<rect width=\""W"\" height=\""H"\" fill=\"#fff\"/>" > out
  printf "<text x=\"%d\" y=\"24\" font-size=\"16\" font-weight=\"bold\">%s  (last %d bars)</text>\n", ML, title, e-s+1 > out
  # grid + y-axis
  for (i2=0;i2<=4;i2++) {
    y=MT+ph*i2/4; pv=mx-(mx-mn)*i2/4
    printf "<line x1=\"%d\" y1=\"%.1f\" x2=\"%d\" y2=\"%.1f\" stroke=\"#eee\"/>\n", ML, y, W-MR, y > out
    printf "<text x=\"%d\" y=\"%.1f\" font-size=\"11\" fill=\"#888\" text-anchor=\"end\">%.2f</text>\n", ML-6, y+4, pv > out
  }
  for (i=s;i<=e;i++) {
    x=ML+(i-s+0.5)*pw/(e-s+1)
    yh=MT+(mx-h[i])*sc; yl=MT+(mx-l[i])*sc
    yo=MT+(mx-o[i])*sc; yc=MT+(mx-c[i])*sc
    up=(c[i]>=o[i])
    col=up?"#e63946":"#2a9d8f"
    printf "<line x1=\"%.1f\" y1=\"%.1f\" x2=\"%.1f\" y2=\"%.1f\" stroke=\"%s\"/>\n", x, yh, x, yl, col > out
    ty=(yo<yc)?yo:yc; th=(yo<yc)?(yc-yo):(yo-yc); if (th<1) th=1
    printf "<rect x=\"%.1f\" y=\"%.1f\" width=\"%.1f\" height=\"%.1f\" fill=\"%s\"/>\n", x-bw/2, ty, bw, th, col > out
    # volume
    vy=H-MB - (v[i]/volmax)*40
    printf "<rect x=\"%.1f\" y=\"%.1f\" width=\"%.1f\" height=\"%.1f\" fill=\"%s\" opacity=\"0.5\"/>\n", x-bw/2, vy, bw, (H-MB)-vy, col > out
  }
  # x-axis dates
  step=int((e-s+1)/6); if (step<1) step=1
  for (i=s;i<=e;i+=step) {
    x=ML+(i-s+0.5)*pw/(e-s+1)
    printf "<text x=\"%.1f\" y=\"%d\" font-size=\"10\" fill=\"#888\" text-anchor=\"middle\" transform=\"rotate(-45 %.1f %d)\">%s</text>\n", x, H-MB+30, x, H-MB+30, substr(d[i],6) > out
  }
  print "</svg>" > out
  printf "chart: %s (%d bars)\n", out, e-s+1
}
END { flush() }
' "$IN"
