# 育ち舎 引き継ぎ用一式（2026-10-18）
スクリプトは絶対パス /tmp/claude-0/t/... と /tmp/claude-0/mock2 を前提にしている。
復元：
  mkdir -p /tmp/claude-0 && cp -r tmp_claude-0_t /tmp/claude-0/t && cp -r mock2 /tmp/claude-0/mock2
  mkdir -p /home/claude/plans/rhino && cp outputs/sodachiya_frames_gh.py /home/claude/plans/rhino/
  pip install rhino3dm shapely scipy matplotlib --break-system-packages
主なスクリプト
  t/ideas/case3.py        西館（案3）・機械室（おむすびB）・部屋割りのモデル → sodachiya_west_case3.3dm
  t/exact/exact.py        GH の 2D 断面 → rhino3dm 押し出し・回転面（Tamedia 型の実形）。floor2_big（床梁の肉球）
  t/exact/exact_model.py  正確な架構モデル → sodachiya_exact.3dm（case3.py を読み込む）
  t/exact/sketch_pdf.py   配置スケッチ用 PDF（1/200、透明背景）
  t/exact/wnew.py         新しい西館の輪郭（東の角を直角、北端=架構2、南端=架構12）→ wnew.pkl
  t/exact/joint_detail3.py 取り合い詳細図（越屋根入り）→ joint_detail.pdf
  t/exact/swatch_pdf.py   部屋の色見本 PDF
  t/ideas/roof_geo.py     配置（conform.json の R205 案）と西館の 1 m シフト（WSHIFT）、PLACE_OVERRIDE フック
  t/ideas/roof_render.py  ku()（角度の折り返しを修正済み）
