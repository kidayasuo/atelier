# -*- coding: utf-8 -*-
"""今のビューのまま、夜のレンダリングを1枚書き出す（プレゼンの準備、10-29）。昼は render_hiru.py

使い方（Rhino 8、Mac）：ビューの決め方は render_hiru.py の頭と同じ。昼を描いた後なら、名前付きビュー <名前> で同じ視点に戻せる。
  1. ツール→スクリプト→実行…（またはコマンド RunPythonScript）で、このファイルを選ぶ。
     ①名前（keikan／me／choukan／その他）と②大きさを聞かれる。昼と同じものを選ぶ。
  2. 書き出し：out/<名前>_yoru.png（mock.py は keikan_yoru.png を読む）と <名前>_view.json。
     夜：太陽を消し、スカイライトはごく弱く（SKYLIGHT_NIGHT）、弱い青白い月明かり（平行光、MOON_POWER）を1本、
     空は暗い群青の一色（NIGHT_SKY、不透明）。LED は 3dm の発光の材料で光る（線の光源は Mac の Cycles で落ちたので使わない）。
     周りの建物（04）は淡い暖かい灰で一時表示。終わったら全部戻す。1枚に約5〜15分。
     明るさの調整は render_common.py の頭の MOON_POWER・SKYLIGHT_NIGHT・NIGHT_SKY。
     Rhino が落ちるとき：コマンド行の最後の「段：…」が落ちた所。render_common.py の頭の切り替え
     USE_MOON・USE_SKYLIGHT_DIM・USE_SKY_BG を一つずつ False にして走らせ、どれが原因かを見る。
  3. できたら push：git add sodachiya/present/rhino/out && git commit -m "[プレゼン] レンダリング（夜）" && git push
中身は render_common.py。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import render_common
try:
    from importlib import reload as _reload
except ImportError:
    _reload = reload    # IronPython 2
render_common = _reload(render_common)     # 直したら読み直す（Rhino は前に読んだものを持ち続ける）
render_common.run("yoru")
