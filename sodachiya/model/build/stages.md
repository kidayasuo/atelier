# 作り直しの段と、それぞれが読むもの（自動、`run_all.sh` が作り直しのたびに書く）

データ・スクリプト・取り込み用ファイルを変えたら、それを読む**いちばん上の段から下**が作り直しになる。
前半（0〜4、しつらえまで）は写し`s4.3dm`を使い回せるが、`run_all.sh … s4`は前半の読むものが1つでも変わっていれば自動ではじめから流す。

| 段 | 名前 | 読むもの（リポジトリの場所、`sodachiya/`から） |
|---|---|---|
| 0 | 架構・西館 | `data/wnew.pkl`・`model/build/ideas/roof_geo.py`・`model/build/south/run_exact_new.py`・`model/build/vendor/plans_rhino/sodachiya_frames_gh.py`・`archive/handoff_1018/t/`の10ファイル・`model/build/vendor/mock2/`の2ファイル |
| 1 | 南端 | `model/build/south/add_south.py` |
| 2 | 浮いた蓋 | `model/build/south/add_monitor_west.py`・`model/build/south/add_south.py` |
| 3 | 床 | `logo/sodachiya_logo.svg`・`model/build/south/add_floor.py`・`model/build/south/add_south.py` |
| 4 | しつらえ | `model/build/shitsu/add_shitsurae.py`・`model/build/shitsu/capture.py`・`model/build/shitsu/ref/plan01.py`・`model/build/shitsu/ref/plan02.py`・`model/build/shitsu/ref/plan04.py`・`scripts/plan01.py`・`scripts/plan02.py`・`scripts/plan04.py` |
| 5 | 外構の取り込み | `model/build/south/finish.py`・`model/sodachiya_approachA_layers.3dm` |
| 6 | 西館の外壁と開口 | `data/play.json`・`data/wnew.pkl`・`model/build/south/add_west_south.py`・`model/build/south/meshkit.py`・`model/build/south/roofw.py`・`model/build/south/uv.py` |
| 7 | 遊戯室 | `data/play.json`・`data/wnew.pkl`・`model/build/south/add_play.py` |
| 7p | 遊戯室の取り込み | `model/build/south/add_play_import.py`・`model/sodachiya_play_layers.3dm` |
| 7b | ホールの林 | `data/forest.json`・`model/build/south/add_hall.py` |
| 7c | 納まり | `data/approachA.json`・`data/wnew.pkl`・`model/build/south/extedit.py`・`model/build/south/fix_details.py`・`model/build/south/solids.py`・`archive/handoff_1018/t/`の1ファイル |
| 7c2 | 2階の間仕切り | `model/build/south/add_inner.py`・`model/build/south/draw100.py` |
| 7c3 | 間仕切りの構法 | `model/build/south/draw100.py`・`model/build/south/walls_spec.py` |
| 7d | 壁の端をそろえる | `model/build/south/join_walls.py` |
| 7e | 室内の戸 | `model/build/south/add_inner.py` |
| 7f | 優先順位で削る | `data/wnew.pkl`・`model/build/south/clip_parts.py` |
| 8 | 護岸と園庭の取り込み | `model/build/south/add_site.py`・`model/sodachiya_garden_layers.3dm` |
| 9 | 周辺 | `data/context_plateau.json`・`model/build/south/add_context.py` |
| 10 | Rhino版 | `data/wnew.pkl`・`model/build/south/clean_wire.py`・`model/build/south/onbrep.py`・`model/build/south/ruled_roof.py`・`model/build/south/solidify.py`・`model/sodachiya_exact_mesh.3dm` |
| 12 | 面積表 | `data/garden.json`・`data/minami.json`・`model/build/south/areas.py`・`model/sodachiya_exact_mesh.3dm` |
| 11 | 図（平面・断面・立面、部屋の面積は面積表から） | `data/garden.json`・`data/siteplan_approach.json`・`model/build/south/draw100.py`・`model/build/south/uv.py`・`model/drawings/sodachiya_areas.json`・`model/sodachiya_exact_mesh.3dm`・`scripts/garden_common.py` |
| 13 | 干渉の一覧 | `model/build/south/clash.py`・`model/sodachiya_exact_mesh.3dm` |
