"""Rhino版に、場所を言うための番号を細い線で描く（設計監修、10-27。ユーザー：屋根に目立たない番号を）。

使い方: python3 marks.py sodachiya.3dm   （その場で書き換える。Rhino版だけ。図・面積表の読む exact_mesh には入れない）
- 架構の番号 1〜20（架構 k は南の妻から 3(k−1) m）と、スパンの番号 (1)〜(19)（架構 k と k+1 のあいだ）を、東の軒の外（v 15.8）と西館の西の外（v −16.3）に。
- v の目盛り（西の外壁の線 v=0 から東へ m）を、南（u −5.6）と北（u 59.0）に 1 m ごと、3 m ごとに数字。
- 高さは屋根より上の z 10 m に水平に置く（上から見ると屋根の上に並ぶ）。字は細い線なので、レンダリングには写らない。
- 位置の言い方は決定事項の「配置」（スパン番号＋スパンの南端からの距離、v）。クリックで同じ言い方を出すのは sodachiya/rhino/doko.py。
"""
import sys, os
import numpy as np
import rhino3dm as r
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uv import xy

Z = 10000.0
LAYER = 'N 番号（架構・スパン・v、屋根の上 z10 m）'
COLOR = (150, 150, 150, 255)

# 線の字（幅 0.6・高さ 1 の枠の中、字ごとに折れ線のリスト）
R = [(0, 0), (0.6, 0), (0.6, 1), (0, 1), (0, 0)]
FONT = {
    '0': [R, [(0, 0), (0.6, 1)]],
    '1': [[(0.3, 0), (0.3, 1), (0.12, 0.82)]],
    '2': [[(0, 1), (0.6, 1), (0.6, 0.5), (0, 0.5), (0, 0), (0.6, 0)]],
    '3': [[(0, 1), (0.6, 1), (0.6, 0), (0, 0)], [(0.1, 0.5), (0.6, 0.5)]],
    '4': [[(0, 1), (0, 0.5), (0.6, 0.5)], [(0.6, 1), (0.6, 0)]],
    '5': [[(0.6, 1), (0, 1), (0, 0.5), (0.6, 0.5), (0.6, 0), (0, 0)]],
    '6': [[(0.6, 1), (0, 1), (0, 0), (0.6, 0), (0.6, 0.5), (0, 0.5)]],
    '7': [[(0, 1), (0.6, 1), (0.6, 0)]],
    '8': [R, [(0, 0.5), (0.6, 0.5)]],
    '9': [[(0.6, 0.5), (0, 0.5), (0, 1), (0.6, 1), (0.6, 0), (0, 0)]],
    '(': [[(0.45, 1.05), (0.2, 0.75), (0.2, 0.25), (0.45, -0.05)]],
    ')': [[(0.15, 1.05), (0.4, 0.75), (0.4, 0.25), (0.15, -0.05)]],
    'v': [[(0, 0.6), (0.3, 0), (0.6, 0.6)]],
    '-': [[(0.1, 0.5), (0.5, 0.5)]],
}
ADV = 0.85


def text(s, u, v, h):
    """(u, v) を字の並びの中心に、東向き（+v）に読む字。上は北（+u）"""
    o = xy(u, v)
    ev = (xy(u, v + 1) - o)            # 1 m あたり（mm）
    eu = (xy(u + 1, v) - o)
    ev, eu = ev / np.linalg.norm(ev), eu / np.linalg.norm(eu)
    w = (len(s) * ADV - (ADV - 0.6)) * h
    start = o - ev * (w / 2) - eu * (h * 1000 / 2)
    lines = []
    for i, ch in enumerate(s):
        for stroke in FONT[ch]:
            pts = []
            for x, y in stroke:
                p = start + ev * ((i * ADV + x) * h * 1000) + eu * (y * h * 1000)
                pts.append(r.Point3d(float(p[0]), float(p[1]), Z))
            lines.append(pts)
    return lines


def seg(u0, v0, u1, v1):
    a, b = xy(u0, v0), xy(u1, v1)
    return [r.Point3d(float(a[0]), float(a[1]), Z), r.Point3d(float(b[0]), float(b[1]), Z)]


def main(path):
    m = r.File3dm.Read(path)
    L = r.Layer(); L.Name = LAYER; L.Color = COLOR
    L.Visible = False                            # 開いたときは消しておく（ユーザー 10-29：空中の目盛りは既定で消す。要るときにレイヤーを点ける）
    li = m.Layers.Add(L)
    strokes = []
    for k in range(1, 21):                       # 架構
        u = 3.0 * (k - 1)
        for v in (15.8, -16.3):
            strokes += text(str(k), u, v, 0.45)
        strokes.append(seg(u, 15.0, u, 15.45)); strokes.append(seg(u, -15.5, u, -15.95))
    for k in range(1, 20):                       # スパン
        u = 3.0 * (k - 1) + 1.5
        for v in (15.8, -16.3):
            strokes += text(f'({k})', u, v, 0.28)
    for uu, lab in ((-5.6, -6.2), (59.0, 59.6)):  # v の目盛り
        for v in range(-16, 17):
            strokes.append(seg(uu - 0.15, v, uu + 0.15, v) if v % 3 else seg(uu - 0.3, v, uu + 0.3, v))
            if v % 3 == 0:
                strokes += text(f'v{v}', lab, v, 0.25)
    n = 0
    for pts in strokes:
        if len(pts) < 2:
            continue
        a = r.ObjectAttributes(); a.LayerIndex = li
        m.Objects.Add(r.PolylineCurve(pts), a)
        n += 1
    m.Write(path, 8)
    print(f'marks: {os.path.basename(path)}：番号の線 {n}')


if __name__ == '__main__':
    main(sys.argv[1])
