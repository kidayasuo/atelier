#!/bin/bash
# 3dm・Rhino 版・1/100 の図（平面・断面・立面）・面積表を一度に作り直す（木造幼稚園建築設計、設計監修）。
# 使い方（sodachiya/ の中で）: bash model/build/run_all.sh [OUT] [from] [--publish]
#   OUT        途中のファイルの置き場（既定 /tmp/claude-0/out）
#   from       base＝はじめから（既定）／s4＝しつらえの後から（OUT に s4.3dm があるとき、少し速い）。
#              s4 でも、前半（しつらえまで）の読むものが写しを作った後に1つでも変わっていれば、自動ではじめから流す（10-24）。
#   --publish  できたもの（sodachiya.3dm・drawings/・model/sodachiya_exact_mesh.3dm・model/drawings/）をリポジトリに書く。
#              **更新係だけが使う**（ユーザー、10-24）。付けなければ OUT/preview/ に同じ並びで書く（確かめるだけ、リポジトリは変わらない）。
# 最後に面積表と干渉の一覧をリポジトリの前の版と比べる（check_build.py）。--publish で「止める」が出たら終わりの値 1（push しない）。
# 各段が読んだファイルは OUT/reads_<段>.txt、段の表は model/build/stages.md（--publish のとき）。
# 前提：setup.sh を一度走らせてある。
set -eE
PUBLISH=0; ARGS=()
for a in "$@"; do if [ "$a" = --publish ]; then PUBLISH=1; else ARGS+=("$a"); fi; done
A=$(cd "$(dirname "$0")/../.." && pwd); M=$A/model; T=/tmp/claude-0/t; B=$A/model/build
OUT=${ARGS[0]:-/tmp/claude-0/out}; FROM=${ARGS[1]:-base}
mkdir -p "$OUT"
if [ $PUBLISH = 1 ]; then DM=$M; DA=$A; else DM=$OUT/preview/model; DA=$OUT/preview; fi
mkdir -p $DM/drawings $DA/drawings
# スクリプトはいつもリポジトリの版を使う（作業場の古い写しで作らない）。凍結した土台・外の部品も毎回写す（10-24）
cp -r $A/archive/handoff_1018/t/. $T/
mkdir -p /home/claude/plans/rhino /tmp/claude-0/mock2
cp $B/vendor/plans_rhino/* /home/claude/plans/rhino/ ; cp -r $B/vendor/mock2/. /tmp/claude-0/mock2/
cp -r $B/south $B/shitsu $T/ ; cp $B/ideas/roof_geo.py $T/ideas/ ; cp $A/data/wnew.pkl $T/exact/wnew.pkl
exec 3>&1
log() { echo "== $*" >&3; }
if command -v strace >/dev/null; then TRACE=1; else TRACE=0; echo "strace が無い：読むものの記録と前半の指紋は作らない（s4 は使えない）" >&3; fi
# 段：stage 記号 名前 コマンド…（読んだファイルを strace で記録する）
# 段のエラー出力は OUT/err_<段>.txt へ（画面には段の名前と最後の要約だけ）。止まったら、その段のログとエラーの最後の20行だけを出す（監修、10-24、連携10-24昼8の5）
CUR=""
trap 'if [ -n "$CUR" ]; then echo "!! 止まった：$CUR（ログ $OUT/log_$CUR.txt・$OUT/err_$CUR.txt の最後の20行）" >&3; tail -n 20 $OUT/log_$CUR.txt >&3 2>/dev/null; tail -n 20 $OUT/err_$CUR.txt >&3 2>/dev/null; fi' ERR
stage() { local k=$1 n=$2; shift 2; log "$n"; CUR=$k
  if [ $TRACE = 1 ]; then strace -f -qq -e trace=openat -e status=successful -o $OUT/reads_$k.raw "$@" 2>$OUT/err_$k.txt; else "$@" 2>$OUT/err_$k.txt; fi; CUR=""; }
if [ "$FROM" = s4 ] && [ -f "$OUT/s4.3dm" ]; then
  if [ $TRACE = 0 ] || ! python3 $B/reads.py verify $OUT >&3; then log "前半の写しが古いので、はじめから"; FROM=base; fi
fi
cd $T
if [ "$FROM" = base ] || [ ! -f "$OUT/s4.3dm" ]; then
  stage 0 架構・西館            python3 south/run_exact_new.py $OUT/base_wnew.3dm > $OUT/log_0.txt
  stage 1 南端                  python3 south/add_south.py $OUT/base_wnew.3dm $OUT/s1.3dm > $OUT/log_1.txt
  stage 2 浮いた蓋              python3 south/add_monitor_west.py $OUT/s1.3dm $OUT/s2.3dm > $OUT/log_2.txt
  stage 3 床                    python3 south/add_floor.py $OUT/s2.3dm $OUT/s3.3dm > $OUT/log_3.txt
  stage 4 しつらえ              python3 shitsu/add_shitsurae.py $A/scripts $OUT/s3.3dm $OUT/s4.3dm > $OUT/log_4.txt
  if [ $TRACE = 1 ]; then python3 $B/reads.py collect $OUT $A && python3 $B/reads.py fingerprint $OUT 0 1 2 3 4 >&3; fi
fi
cd $T/south
stage 5 外構の取り込み          python3 finish.py $OUT/s4.3dm $OUT/s5.3dm $M/sodachiya_approachA_layers.3dm > $OUT/log_5.txt
stage 6 西館の外壁と開口        python3 add_west_south.py $OUT/s5.3dm $OUT/s6.3dm $A/data/wnew.pkl > $OUT/log_6.txt
stage 7 遊戯室                  python3 add_play.py $OUT/s6.3dm $OUT/s7.3dm $A/data/play.json $A/data/wnew.pkl > $OUT/log_7.txt
stage 7p 遊戯室の取り込み       python3 add_play_import.py $OUT/s7.3dm $OUT/s7p.3dm $M/sodachiya_play_layers.3dm > $OUT/log_7p.txt
stage 7b ホールの林             python3 add_hall.py $OUT/s7p.3dm $OUT/s7b.3dm $A/data/forest.json > $OUT/log_7b.txt
stage 7c 納まり                 python3 fix_details.py $OUT/s7b.3dm $OUT/s7c.3dm $A/data/wnew.pkl > $OUT/log_7c.txt
stage 7c2 2階の間仕切り         python3 add_inner.py walls $OUT/s7c.3dm $OUT/s7c2.3dm > $OUT/log_7c2.txt
stage 7c3 間仕切りの構法        python3 walls_spec.py $OUT/s7c2.3dm $OUT/s7c3.3dm > $OUT/log_7c3.txt
stage 7d 壁の端をそろえる       python3 join_walls.py $OUT/s7c3.3dm $OUT/s7d.3dm > $OUT/log_7d.txt
stage 7e 室内の戸               python3 add_inner.py doors $OUT/s7d.3dm $OUT/s7e.3dm > $OUT/log_7e.txt
stage 7f 優先順位で削る         python3 clip_parts.py $OUT/s7e.3dm $OUT/s7f.3dm $A/data/wnew.pkl $OUT/clip.json > $OUT/log_7f.txt 2>&1
stage 8 護岸と園庭の取り込み    python3 add_site.py $OUT/s7f.3dm $OUT/s8.3dm $M/sodachiya_garden_layers.3dm > $OUT/log_8.txt
stage 9 周辺                    python3 add_context.py $OUT/s8.3dm $DM/sodachiya_exact_mesh.3dm $A/data/context_plateau.json > $OUT/log_9.txt
stage 10 Rhino版               python3 clean_wire.py $DM/sodachiya_exact_mesh.3dm $DA/sodachiya.3dm > $OUT/log_10.txt
stage 12 面積表                 python3 areas.py $DM/sodachiya_exact_mesh.3dm $A/data $DM/drawings $DA/drawings | tee $OUT/log_12.txt | head -1
stage 11 図（平面・断面・立面、部屋の面積は面積表から）  python3 draw100.py $DM/sodachiya_exact_mesh.3dm $DM/drawings $DA/drawings > $OUT/log_11.txt
stage 13 干渉の一覧             python3 clash.py $DM/sodachiya_exact_mesh.3dm $DM/drawings/sodachiya_clash.json $DM/drawings/sodachiya_clash.txt 2>/dev/null | head -1
grep -h "imported\|play:\|join_walls:\|walls_spec: {\|add_inner\|clip_parts:\|context:\|written /" $OUT/log_5.txt $OUT/log_7p.txt $OUT/log_7c2.txt $OUT/log_7c3.txt $OUT/log_7d.txt $OUT/log_7e.txt $OUT/log_7f.txt $OUT/log_9.txt $OUT/log_10.txt 2>/dev/null | tail -7
if [ $TRACE = 1 ]; then python3 $B/reads.py collect $OUT $A
  if [ $PUBLISH = 1 ]; then python3 $B/reads.py table $OUT $A $B/stages.md >&3; else python3 $B/reads.py table $OUT $A $OUT/stages.md >&3; fi; fi
set +e
python3 $B/check_build.py $A $DM/drawings $DM/drawings/sodachiya_check.txt; CK=$?
if [ $PUBLISH = 1 ]; then
  echo "done（--publish）: sodachiya.3dm・drawings/・model/sodachiya_exact_mesh.3dm・model/drawings/"
  if [ $CK != 0 ]; then echo "check で止まった：push しないで、上の ✗ を直してから作り直す"; exit 1; fi
else
  echo "done（確かめるだけ）: $DA/ に作った（リポジトリは変わっていない。3dm・図・面積表は push しない、更新係が作り直す）"
fi
