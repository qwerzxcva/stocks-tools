#!/bin/bash
# Generate charts/index.html
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
OUT="$ROOT/charts/index.html"

{
echo '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
echo '<meta name="viewport" content="width=device-width,initial-scale=1">'
echo '<title>charts</title>'
echo '<style>body{font-family:sans-serif;margin:20px;background:#fafafa}'
echo 'h1{font-size:18px}h2{font-size:14px;margin-top:24px;color:#333;border-bottom:1px solid #ddd;padding-bottom:4px}'
echo 'a{display:inline-block;margin:4px 8px 4px 0;padding:6px 10px;background:#fff;border:1px solid #ddd;border-radius:4px;text-decoration:none;color:#0366d6;font-size:13px}'
echo 'a:hover{background:#0366d6;color:#fff}</style></head><body>'
echo "<p style=\"color:#999;font-size:12px\">$(date -u -d '+8 hours' '+%Y-%m-%d %H:%M') CST | $(ls "$ROOT/charts"/*.svg 2>/dev/null | wc -l) charts</p>"

while IFS= read -r line; do
  case "$line" in
    \[*\]*) echo "<h2>$(echo "$line" | tr -d '[]')</h2>" ;;
    ""|\#*) ;;
    *)
      code=$(echo "$line" | awk '{print $1}')
      name=$(echo "$line" | awk '{print $2}')
      f="$code-$name.svg"
      [ -f "$ROOT/charts/$f" ] && echo "<a href=\"$f\" target=\"_blank\">$name</a>"
      ;;
  esac
done < "$DIR/watchlist.txt"

echo '</body></html>'
} > "$OUT"
echo "index: $OUT"
