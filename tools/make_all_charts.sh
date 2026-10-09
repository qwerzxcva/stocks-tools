#!/bin/bash
# batch generate SVG charts
# usage: bash make_all_charts.sh [lastN] default 30
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
N="${1:-30}"
KL="$ROOT/data/kline/all.txt"
mkdir -p "$ROOT/charts"

grep -v '^\s*\(#\|\[\|$\)' "$DIR/watchlist.txt" | while read -r code name; do
  [ -z "$code" ] && continue
  awk -F'|' -v c="$code" '$1==c' "$KL" > /tmp/_one.txt
  [ -s /tmp/_one.txt ] || continue
  bash "$DIR/make_chart.sh" /tmp/_one.txt "$ROOT/charts/$code-$name.svg" "$name" "$N"
done
echo "charts: $ROOT/charts ($(ls "$ROOT/charts" | wc -l))"
