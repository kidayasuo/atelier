#!/bin/bash
# 作り直しを確かめる（--publish なし）。長い出力は会話に入れず、ファイルに置いて要る行だけ出す（効率化委員会、10-28）。
# 使い方（sodachiya/ の中で）: bash tools/tsukuru.sh [OUT] [from]   引数は run_all.sh と同じ（--publish は付けない）
# Bash の run_in_background で走らせ、終わりの知らせを待つ（途中で何度も覗かない）。
cd "$(dirname "$0")/.."
mkdir -p /tmp/claude-0/out
L=/tmp/claude-0/out/tsukuru_$(date +%m%d-%H%M%S).log
for a in "$@"; do [ "$a" = --publish ] && { echo "--publish は付けない（作り直しは push で自動）"; exit 2; }; done
bash model/build/run_all.sh "$@" >"$L" 2>&1; rc=$?
echo "ログ：$L（丸ごと読まない。要る所は grep -n で）"
grep -E '^check:|✗|^!! |^done' "$L" | tail -n 12
if [ $rc != 0 ]; then echo "--- 止まった所（最後の10行）"; tail -n 10 "$L"; fi
exit $rc
