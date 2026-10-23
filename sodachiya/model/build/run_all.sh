#!/bin/bash
# 3dm・Rhino 版・1/100 の図（平面・断面・立面）・面積表を一度に作り直す（木造幼稚園建築設計）。
# 使い方（sodachiya/ の中で）: bash model/build/run_all.sh [OUT] [from]
#   OUT  途中のファイルの置き場（既定 /tmp/claude-0/out）
#   from base＝はじめから（既定。作業場を作り直した後はこれ）／s4＝しつらえの後から（OUT に s4.3dm があるとき、少し速い）
# 前提：setup.sh を一度走らせてある。
set -e
A=$(cd "$(dirname "$0")/../.." && pwd); M=$A/model; T=/tmp/claude-0/t
OUT=${1:-/tmp/claude-0/out}; FROM=${2:-base}
mkdir -p "$OUT"
# スクリプトはいつもリポジトリの版を使う（作業場の古い写しで作らない）
cp -r $A/model/build/south $A/model/build/shitsu $T/ ; cp $A/model/build/ideas/roof_geo.py $T/ideas/ ; cp $A/data/wnew.pkl $T/exact/wnew.pkl
log() { echo "== $*"; }
cd $T
if [ "$FROM" = base ] || [ ! -f "$OUT/s4.3dm" ]; then
  log 架構・西館;            python3 south/run_exact_new.py $OUT/base_wnew.3dm > $OUT/log_0.txt
  log 南端;                  python3 south/add_south.py $OUT/base_wnew.3dm $OUT/s1.3dm > $OUT/log_1.txt
  log 浮いた蓋;              python3 south/add_monitor_west.py $OUT/s1.3dm $OUT/s2.3dm > $OUT/log_2.txt
  log 床;                    python3 south/add_floor.py $OUT/s2.3dm $OUT/s3.3dm > $OUT/log_3.txt
  log しつらえ;              python3 shitsu/add_shitsurae.py $A/scripts $OUT/s3.3dm $OUT/s4.3dm > $OUT/log_4.txt
fi
cd $T/south
log 外構の取り込み;          python3 finish.py $OUT/s4.3dm $OUT/s5.3dm $M/sodachiya_approachA_layers.3dm > $OUT/log_5.txt
log 西館の外壁と開口;        python3 add_west_south.py $OUT/s5.3dm $OUT/s6.3dm $A/data/wnew.pkl > $OUT/log_6.txt
log 遊戯室;                  python3 add_play.py $OUT/s6.3dm $OUT/s7.3dm $A/data/play.json $A/data/wnew.pkl > $OUT/log_7.txt
log 遊戯室の取り込み;        python3 add_play_import.py $OUT/s7.3dm $OUT/s7p.3dm $M/sodachiya_play_layers.3dm > $OUT/log_7p.txt
log ホールの林;              python3 add_hall.py $OUT/s7p.3dm $OUT/s7b.3dm $A/data/forest.json > $OUT/log_7b.txt
log 納まり;                  python3 fix_details.py $OUT/s7b.3dm $OUT/s7c.3dm $A/data/wnew.pkl > $OUT/log_7c.txt
log 壁の端をそろえる;        python3 join_walls.py $OUT/s7c.3dm $OUT/s7d.3dm > $OUT/log_7d.txt
log 護岸と園庭の取り込み;    python3 add_site.py $OUT/s7d.3dm $OUT/s8.3dm $M/sodachiya_garden_layers.3dm > $OUT/log_8.txt
log 周辺;                    python3 add_context.py $OUT/s8.3dm $M/sodachiya_exact_mesh.3dm $A/data/context_plateau.json > $OUT/log_9.txt
log Rhino 版;                python3 clean_wire.py $M/sodachiya_exact_mesh.3dm $M/sodachiya_exact.3dm > $OUT/log_10.txt
log 面積表;                  python3 areas.py $M/sodachiya_exact_mesh.3dm $A/data $M/drawings | tee $OUT/log_12.txt | head -1
log 図（平面・断面・立面、部屋の面積は面積表から）;  python3 draw100.py $M/sodachiya_exact_mesh.3dm $M/drawings > $OUT/log_11.txt
grep -h "imported\|play:\|join_walls:\|context:\|written /" $OUT/log_5.txt $OUT/log_7p.txt $OUT/log_7d.txt $OUT/log_9.txt $OUT/log_10.txt 2>/dev/null | tail -5
echo "done: model/sodachiya_exact_mesh.3dm・sodachiya_exact.3dm・drawings/（平面・断面・立面 1・2・面積表）"
