# -*- coding: utf-8 -*-
"""今のビューのまま、昼のレンダリングを1枚書き出す（プレゼンの準備、10-29）。夜は render_yoru.py

使い方（Rhino 8、Mac）：
  1. atelier を pull して、sodachiya/sodachiya.3dm を開く。
  2. ビューを決める（スクリプトはビューを動かさない。見えている通りに描く）：
     ・SetCameraTarget（カメラとターゲット）で立つ所と見る点を置く。歩くなら Walkabout、目の高さは
       カメラの z を GL＋1.5 m（1500）に。
     ・レンズ：プロパティ（ビューを選んだ状態）の「レンズの長さ」（35 mm 換算。24〜28 が広め、35〜50 が自然）。
     ・縦の線を縦にするなら、ビューの名前のメニュー→「2点透視」（Rhino 8）。
     ・レイトレースの表示で光と影を確かめる。写したくない物は Hide しておく（スクリプトは隠さない）。
     ・レンダリングの絵と画面の縦横比が違うと写る範囲が少し変わる。気になれば下の②で「今のビューの縦横比」を選ぶ。
  3. ツール→スクリプト→実行…（またはコマンド RunPythonScript）で、このファイルを選ぶ。二つ聞かれる：
     ①名前：keikan＝沿川の景観／me＝透視図（公園の角）／choukan＝鳥瞰／room_…＝教室・居場所（room_view.py で準備）／その他（文字で、例 naibu_4sai）
     ②大きさ：A4横 3508×2480／1600×1200（room_ の既定）／横長 2.5:1 4252×1701／今のビューの縦横比で長辺4252
     1枚に約5〜15分（レンダリングの設定の最大回数しだい）。
  4. 書き出し：out/ に、昼の絵と、カメラを書いた <名前>_view.json。名前付きビュー <名前> も残る（同じ視点で昼夜をそろえられる）。
     昼の絵の名前は mock.py が読む名前に合わせる：keikan→keikan_hiru.png（背景は透明、空は mock.py）、
     me→me.png、choukan→choukan.png、その他→<名前>_hiru.png（me・choukan・その他は淡い空で不透明）。
     11/5 10:00 の太陽、周りの建物（04）を淡い暖かい灰で一時表示。room_ は太陽を使わず、③部屋の光（散乱光／窓の光）を聞く。終わったら全部戻す（3dm は保存しなくてよい）。
  5. 続けて夜：同じビューのまま（名前付きビューで戻してもよい）render_yoru.py を走らせる。
  6. できたら push：git add sodachiya/present/rhino/out && git commit -m "[プレゼン] レンダリング" && git push
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
render_common.run("hiru")
