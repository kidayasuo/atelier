# sodachiya_exact.3dm の生成スクリプト（3dm 担当）
前提：archive/handoff_1018/t を /tmp/claude-0/t に展開し、この build/ の south/ shitsu/ ideas/roof_geo.py を上書きコピーする。
data/wnew.pkl を /tmp/claude-0/t/exact/wnew.pkl に置く。pip install rhino3dm shapely scipy matplotlib mapbox_earcut

手順（OUT は任意のフォルダ）
  python3 south/run_exact_new.py OUT/base_wnew.3dm        # 架構・西館（wnew 輪郭）
  python3 south/add_south.py OUT/base_wnew.3dm OUT/s1.3dm  # 南端・受け取り土間・本館の浮いた蓋・外部
  python3 south/add_monitor_west.py OUT/s1.3dm OUT/s2.3dm  # 西館の浮いた蓋・すき間の蓋・ファン
  python3 south/add_floor.py OUT/s2.3dm OUT/s3.3dm         # 床・縁側・海峡・東のガラス戸（鴨居 2270）
  python3 shitsu/add_shitsurae.py sodachiya/scripts OUT/s3.3dm OUT/s4.3dm   # plan01/02/04 のしつらえ
  python3 south/finish.py OUT/s4.3dm model/sodachiya_exact.3dm model/sodachiya_approachA_layers.3dm
finish.py：レイヤー統合・00〜69 に番号整理・ガラス材質（透明 0.8／すり 0.4）・外構を -300 で取り込み。
z=0 は本館 FL（GL = -300）。
