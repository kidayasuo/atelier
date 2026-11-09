#!/bin/bash
# 3dm の作業場を用意する（新しいセッション、または作業場が片付けられた後に一度だけ）。
# 使い方: bash model/build/setup.sh        （sodachiya/ の中で）
# - /tmp/claude-0/t に、凍結した土台（archive/handoff_1018/t）を広げ、model/build/ のスクリプトで上書きする。
# - Python と node の道具を入れる。日本語の字（Noto Sans CJK）が無ければ入れる。
set -e
A=$(cd "$(dirname "$0")/../.." && pwd); B=$A/model/build; T=/tmp/claude-0/t
mkdir -p $T
cp -r $A/archive/handoff_1018/t/. $T/
cp -r $B/south $B/shitsu $T/
mkdir -p $T/ideas $T/exact $T/view
cp $B/ideas/roof_geo.py $T/ideas/
cp $A/data/wnew.pkl $T/exact/wnew.pkl
cp $B/view/* $T/view/
# 作業場の外にあった部品（架構の元のスクリプトと、Rhino の代わりの部品）。run_exact_new.py がこの場所を読む
mkdir -p /home/claude/plans/rhino /tmp/claude-0/mock2
cp $B/vendor/plans_rhino/* /home/claude/plans/rhino/
cp -r $B/vendor/mock2/. /tmp/claude-0/mock2/
pip install --break-system-packages -q rhino3dm shapely scipy matplotlib mapbox_earcut ezdxf trimesh rtree manifold3d remotezip networkx lxml pyproj scikit-image 2>&1 | tail -1 || true
if ! fc-list | grep -q "Noto Sans CJK"; then
  (apt-get install -y -q fonts-noto-cjk >/dev/null 2>&1 || pip install --break-system-packages -q fonts-noto-cjk) || echo "日本語の字が入らなかった（図の字が化ける）"
fi
(cd $T/view && npm install --silent >/dev/null 2>&1) || echo "node の道具（絵の確認用）が入らなかった。3dm と図は作れる"
echo "ready: $T"
