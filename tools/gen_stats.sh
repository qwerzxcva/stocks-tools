#!/bin/bash
# generate daily sentiment metrics -> data/emotion.jsonl
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
POOL="$ROOT/data/pool"
OUT="$ROOT/data/emotion.jsonl"
mkdir -p "$ROOT/data"

: > "$OUT"
for f in "$POOL"/*.ztpool.json; do
  [ -e "$f" ] || continue
  D=$(basename "$f" | cut -d. -f1)
  perl -MJSON::PP -e '
    my ($zf,$dp,$bp,$dash)=@ARGV;
    my $z=JSON::PP->new->decode(getcontent($zf));
    my $dt=(-e $dp)?JSON::PP->new->decode(getcontent($dp))->{data}{tc}:0;
    my $zb=(-e $bp)?JSON::PP->new->decode(getcontent($bp))->{data}{tc}:0;
    my $zt=$z->{data}{tc};
    my $max=0; my %lb;
    for my $s (@{$z->{data}{pool}}) { $max=$s->{lbc} if $s->{lbc}>$max; $lb{$s->{lbc}}++ }
    my $zb_rate = ($zt+$zb)>0 ? sprintf("%.1f",$zb/($zt+$zb)*100) : "0";
    my @hi = map { "$_L:$lb{$_}" } sort { $b<=>$a } keys %lb;
    my %hy; for my $s (@{$z->{data}{pool}}) { $hy{$s->{hybk}}++ }
    my @hs = sort { $hy{$b}<=>$hy{$a} } keys %hy;
    my $last = $#hs>4 ? 4 : $#hs;
    my @top = map { "\"$_\":$hy{$_}" } @hs[0..$last];
    printf "{\"date\":\"%s\",\"zt\":%d,\"dt\":%d,\"zb\":%d,\"zb_rate\":%s,\"max_lb\":%d,\"ladder\":\"%s\",\"top_sectors\":{%s}}\n",
      $dash,$zt,$dt,$zb,$zb_rate,$max,join(",",@hi),join(",",@top);
    sub getcontent { my $f=shift; local $/; open my $h,"<",$f or return "{}"; <$h> }
  ' "$f" "$POOL/$D.dtpool.json" "$POOL/$D.zbpool.json" "${D:0:4}-${D:4:2}-${D:6:2}" >> "$OUT"
done
sort "$OUT" -o "$OUT" 2>/dev/null
echo "emotion: $OUT ($(wc -l < "$OUT"))"
