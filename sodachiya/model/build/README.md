# sodachiya_exact.3dm の生成スクリプト（3dm 担当）
前提：archive/handoff_1018/t を /tmp/claude-0/t に展開し、この build/ の south/ shitsu/ ideas/roof_geo.py を上書きコピーする。
data/wnew.pkl を /tmp/claude-0/t/exact/wnew.pkl に置く。pip install rhino3dm shapely scipy matplotlib mapbox_earcut

手順（OUT は任意のフォルダ）
  python3 south/run_exact_new.py OUT/base_wnew.3dm        # 架構・西館（wnew 輪郭）
  python3 south/add_south.py OUT/base_wnew.3dm OUT/s1.3dm  # 南端・受け取り土間・本館の浮いた蓋・外部
  python3 south/add_monitor_west.py OUT/s1.3dm OUT/s2.3dm  # 西館の浮いた蓋・すき間の蓋・ファン
  python3 south/add_floor.py OUT/s2.3dm OUT/s3.3dm         # 床・縁側・海峡・東のガラス戸（鴨居 2270）
  python3 shitsu/add_shitsurae.py sodachiya/scripts OUT/s3.3dm OUT/s4.3dm   # plan01/02/04 のしつらえ
  python3 south/finish.py OUT/s4.3dm OUT/s5.3dm model/sodachiya_approachA_layers.3dm
  python3 south/add_west_south.py OUT/s5.3dm OUT/s6.3dm data/wnew.pkl                   # 西館の外壁と開口（南の入口・遊戯室の窓・大戸は data/play.json）、キッチン・更衣・はれのま・東の帯・スパン 7
  python3 south/add_play.py OUT/s6.3dm OUT/s7.3dm data/play.json data/wnew.pkl          # 遊戯室の遊具・しつらえ（レイヤー 80〜89、寸法は遊戯室のスレッドの data/play.json）
  python3 south/add_play_import.py OUT/s7.3dm OUT/s7p.3dm model/sodachiya_play_layers.3dm   # 80〜88 を遊戯室のチャットの取り込み用ファイル（scripts/play3d.py）で置き換える（89 の大戸・開口・床の穴は上のまま）
  python3 south/add_hall.py OUT/s7p.3dm OUT/s7b.3dm data/forest.json                     # ホールの北山杉の林（55、木ごとの h、頂部は半球）・スパン 11 の静養室／記録の机／園長室・2 階の更衣・ロッカー（43b）
  python3 south/fix_details.py OUT/s7b.3dm OUT/s7c.3dm data/wnew.pkl                     # 納まりの整理：本館の西の外壁 420（柱・桁を中に）、北の妻、西館の柱・梁・桁を壁の内側に、2 階の間仕切りを屋根まで、2 階の腰壁
  python3 south/add_site.py OUT/s7c.3dm OUT/s8.3dm model/sodachiya_garden_layers.3dm   # 護岸（02、公園の角で GL−5.0）＋園庭の取り込み（90〜98、98 は隠す）
  python3 south/add_context.py OUT/s8.3dm model/sodachiya_exact_mesh.3dm data/context_plateau.json          # 周辺の道路（03）と建物（04、LOD1）。敷地の中の今の家と道は入れない
  # data/context_plateau.json は context/plateau_fetch.py で PLATEAU（京都市 2025）から作る。位置合わせは data/georef.json
  python3 south/clean_wire.py model/sodachiya_exact_mesh.3dm model/sodachiya_exact.3dm   # Rhino 用（ワイヤフレームの筋なし）
  python3 south/draw100.py model/sodachiya_exact_mesh.3dm model/drawings                 # 1/100 平面・断面（モデルを直したら毎回）
finish.py：レイヤー統合・00〜69 に番号整理・ガラス材質（透明 0.8／すり 0.4）・外構を -300 で取り込み。
z=0 は本館 FL（GL = -300）。

2 つの 3dm
- `sodachiya_exact.3dm`：Rhino で開く版。レイヤーは親（A 屋根・越屋根／B 頭上／C 架構／D 壁・建具／E 床・部屋の色／F しつらえ／G 外（本体）／H 外構／I 敷地）の下にまとめてある。親を消すと子もまとめて消える。平らな面ごとにまとめ直し、立体は押し出し（穴つき）、その他はトリム平面（グループ）。アイソカーブ非表示。形のずれは 3 mm 以内。南の縁側（14）と弧に沿うルーバー（50c）はメッシュのまま。
- `sodachiya_exact_mesh.3dm`：スクリプトが読む版（すべて三角形のメッシュ、レイヤーは親なしの平らな一覧）。図やほかのスクリプトはこちらを読む。

1/100 の図（`model/drawings/`、3dm を更新するたびに作り直す。ファイル名は毎回同じ）
- `sodachiya_plan_1-100`：1 階平面（FL+1200 で切断）＋西館 2 階（2 階で切れる梁は破線）、A1 縦。
- `sodachiya_sections_1-100`：A1 横。断面 A＝縦断（保育室の中ほど r=197 m の弧で切って展開、西を見る）、
  B＝海峡（u 21.75、北を見る）、C＝4 歳・遊戯室（u 46.5、北を見る）。B・C は奥 3.2 m まで見えがかり。
- それぞれ PDF・PNG・DXF。DXF は 1/100 の図を 1:1 の mm で置いたもの（用紙 A1 × 100）。
  隠れ線は消してあり、切り口の線はつないである（塗りはハッチ）。手を入れるときに使う。
- DXF のレイヤー：01 切断（構造・壁）／02 切断（家具）／03 切断（ガラス）／04 切断（機械室などの塊）／
  10 見えがかり／11 見えがかり（家具）／12 見えがかり（ガラス）／20 上部（屋根の外形・梁、破線）／30 敷地・外構／
  40 通り芯／41 通り芯の符号／50 寸法／51 高さ／60 部屋名・面積／70 断面の位置／80 図名・縮尺・方位／90 図枠
- 通り芯：架構 1〜20（南から）と W（西の柱 r=205 m）・E（東の柱 r=193 m）。寸法：平面はスパン 3,000（背骨 r=205 m で）、
  断面 B・C は西館の幅・すき間 900・西吹き抜け 1,600・教室 10,400・内縁側 1,500・外縁側 1,500。
  高さ：GL・FL・2FL・本館の屋根の最高・越屋根の蓋・西館の最高（モデルの切断面から読む）。
- 図の右下に作った日時（と atelier の版）が入る。
