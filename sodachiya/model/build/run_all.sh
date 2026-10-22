#!/bin/bash
# 3dm と 1/100 の図を一度に作り直す（木造幼稚園建築設計）。前提は README の「前提」。
# 使い方: bash model/build/run_all.sh OUT [from]   from = base（はじめから）| s4（既定、s4.3dm があればしつらえの後から）
set -e
OUT=${1:?OUT}; FROM=${2:-s4}
A=$(cd "$(dirname "$0")/../.." && pwd); M=$A/model; T=/tmp/claude-0/t
mkdir -p "$OUT"; cd $T
if [ "$FROM" = base ] || [ ! -f "$OUT/s4.3dm" ]; then
  python3 south/run_exact_new.py $OUT/base_wnew.3dm
  python3 south/add_south.py $OUT/base_wnew.3dm $OUT/s1.3dm
  python3 south/add_monitor_west.py $OUT/s1.3dm $OUT/s2.3dm
  python3 south/add_floor.py $OUT/s2.3dm $OUT/s3.3dm
  python3 shitsu/add_shitsurae.py $A/scripts $OUT/s3.3dm $OUT/s4.3dm
fi
cd $T/south
python3 finish.py $OUT/s4.3dm $OUT/s5.3dm $M/sodachiya_approachA_layers.3dm
python3 add_west_south.py $OUT/s5.3dm $OUT/s6.3dm $A/data/wnew.pkl
python3 add_play.py $OUT/s6.3dm $OUT/s7.3dm $A/data/play.json $A/data/wnew.pkl
python3 add_play_import.py $OUT/s7.3dm $OUT/s7p.3dm $M/sodachiya_play_layers.3dm
python3 add_hall.py $OUT/s7p.3dm $OUT/s7b.3dm $A/data/forest.json > $OUT/hall.log
python3 fix_details.py $OUT/s7b.3dm $OUT/s7c.3dm $A/data/wnew.pkl
python3 add_site.py $OUT/s7c.3dm $OUT/s8.3dm $M/sodachiya_garden_layers.3dm
python3 add_context.py $OUT/s8.3dm $M/sodachiya_exact_mesh.3dm $A/data/context_plateau.json
python3 clean_wire.py $M/sodachiya_exact_mesh.3dm $M/sodachiya_exact.3dm
python3 draw100.py $M/sodachiya_exact_mesh.3dm $M/drawings
echo "done: $M/sodachiya_exact_mesh.3dm / sodachiya_exact.3dm / drawings"
