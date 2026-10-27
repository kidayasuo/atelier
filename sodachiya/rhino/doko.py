# -*- coding: utf-8 -*-
"""育ち舎　どこ？：Rhino で点をクリックすると、その場所を決定事項の言い方で出す（設計監修、10-27）

使い方（Rhino 8、Mac）：
  1. sodachiya/sodachiya.3dm を開く（ほかの 3dm でも、育ち舎の座標（mm）なら同じ）。
  2. コマンド RunPythonScript で、このファイルを選ぶ。
  3. 場所をクリックする（物の端・面の上などにスナップしてよい）。何度でもクリックでき、Esc で終わる。
  4. コマンドの行に、例えば
       スパン14＋1.50（u 40.50）・v 3.20・z 1.20（FL から）　架構15から北へ1.50
     と出る。最後の一つはクリップボードにも入るので、チャットにそのまま貼れる。

言い方（決定事項の「配置」）：
  - 南北：スパン k（架構 k と k+1 のあいだ、架構 k は南の妻から 3(k−1) m）＋スパンの南端からの距離。
  - 東西：v＝本館の西の外壁の線（西の柱の列）から東へ m。西館では「東から w」（西館の東の線 v −0.9 から西へ m）も出す。
  - z は 3dm の高さ（FL ±0 からの m）。
  - 屋根の上 z 10 m の灰色の線は、架構の番号・(スパン)・v の目盛り（レイヤー「N 番号」）。
何も書き込まない（3dm は変わらない）。
"""
import math
import rhinoscriptsyntax as rs

# model/build/south/uv.py と同じ定数（本館の背骨 半径 205 m の弧）
CX, CY, RW = 194662.93237, -41348.26335, 205017.7
TH_S = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)


def uv(x, y):
    th = math.atan2(y - CY, x - CX) % (2 * math.pi)
    return (TH_S - th) * RW / 1000.0, (RW - math.hypot(x - CX, y - CY)) / 1000.0


def say(p):
    u, v = uv(p.X, p.Y)
    u, v = round(u, 3), round(v, 3)       # 架構のちょうど上が 2.99999 にならないように
    z = p.Z / 1000.0
    if u < 0:
        ns = u"南の妻より南へ %.2f（u %.2f）" % (-u, u)
    elif u > 57:
        ns = u"北の端（架構20）より北へ %.2f（u %.2f）" % (u - 57, u)
    else:
        k = min(int(u // 3) + 1, 19)
        ns = u"スパン%d＋%.2f（u %.2f）" % (k, u - 3 * (k - 1), u)
    s = ns + u"・v %.2f" % v
    if v < -0.9:
        s += u"（西館の東から w %.2f）" % (-v - 0.9)
    s += u"・z %.2f（FL から）" % z
    if 0 <= u <= 57:
        f = int(math.ceil(u / 3.0 - 0.5)) + 1     # 近いほうの架構（真ん中なら南の架構）
        d = u - 3 * (f - 1)
        if abs(d) < 0.005:
            s += u"　架構%dの上" % f
        else:
            s += u"　架構%dから%s%.2f" % (f, u"北へ" if d > 0 else u"南へ", abs(d))
    return s


last = None
while True:
    p = rs.GetPoint(u"どこ？ 場所をクリック（Esc で終わり）")
    if p is None:
        break
    last = say(p)
    print(last)
if last:
    try:
        rs.ClipboardText(last)
        print(u"（最後の一つをクリップボードに入れた）")
    except Exception:
        pass
