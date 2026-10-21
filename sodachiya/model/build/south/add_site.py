"""敷地の現況：高野川の護岸（崖）を敷地の南東の辺に沿って
使い方: python3 add_site.py IN.3dm OUT.3dm
決定事項「敷地の現況」（10-21 ユーザーの実測と写真）：高さ 5 m（土が積もって 4 m の所が多い）。
上から 柵（金網）の土台のコンクリートの立ち上がり → 小段（コンクリートの天端）→ 谷積みの石積み（垂直に近い）→ 草の河川敷 → 川。
寸法は写真からの見立て（仮）：立ち上がり 幅 0.2・GL+0.3、小段 幅 0.6・GL−0.3、石積み 勾配 1:0.3 で GL−4.0 まで、
河川敷 幅 8 m（川へ 0.3 下がる）、川の水面 GL−4.5。z=0 は FL（GL = −300）。
"""
import sys, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/south')
from uv import uv
from meshkit import Kit
from shapely.geometry import Polygon

IN, OUT = sys.argv[1:3]
m = r.File3dm.Read(IN)
def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
L_RV = layer('02_敷地_高野川の護岸（現況、寸法は仮）', (140, 150, 140))
K = Kit(m)

# 敷地の外形（00 の大きい方）から南東の辺（u が小さく v が大きい 2 点：東の角 → 南の角）
site = None
for o in m.Objects:
    if m.Layers[o.Attributes.LayerIndex].Name.startswith('00_') and isinstance(o.Geometry, r.PolylineCurve):
        g = o.Geometry; P = np.array([[g.Point(i).X, g.Point(i).Y] for i in range(g.PointCount)])
        if site is None or Polygon(P).area > Polygon(site).area: site = P
UV = [uv(*p) for p in site]
iE = max(range(len(UV) - 1), key=lambda i: UV[i][1])               # 東の角（v がいちばん大きい）
iS = min(range(len(UV) - 1), key=lambda i: UV[i][0])               # 南の角（u がいちばん小さい）
a, b = site[iE], site[iS]
d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])
cen = site[:-1].mean(0)
if np.dot(n, cen - (a + b) / 2) > 0: n = -n                        # 敷地の外（川の側）へ
ext = 3000                                                         # 辺の両端を少し延ばす
a2, b2 = a - d * ext, b + d * ext
GL = -300.0
def band(o0, o1):
    return Polygon([a2 + n * o0, b2 + n * o0, b2 + n * o1, a2 + n * o1])
K.prism(band(0, 200), GL - 300, GL + 300, L_RV, (190, 190, 185))                 # 柵の土台の立ち上がり
K.prism(band(200, 800), GL - 400, GL, L_RV, (190, 190, 185))                     # 小段（コンクリートの天端）
# 谷積みの石積み（勾配 1:0.3、小段の下 GL−0.4 → GL−4.0）：外の面は小段の縁 800 から下で 800+1080 へ、裏は 500 で垂直
top, bot = GL - 400, GL - 4000
W0, W1 = 800, 800 + 0.3 * (top - bot)
V = lambda p, off, z: [*(p + n * off), z]
K.box8([V(a2, 500, bot), V(b2, 500, bot), V(b2, W1, bot), V(a2, W1, bot),
        V(a2, 500, top), V(b2, 500, top), V(b2, W0, top), V(a2, W0, top)], L_RV, (150, 140, 120))
K.prism(band(W1, W1 + 8000), bot - 300, bot, L_RV, (150, 175, 120))                     # 草の河川敷（上面 GL−4.0）
K.prism(band(W1 + 8000, W1 + 14000), bot - 800, bot - 500, L_RV, (120, 160, 200))                # 川（水面 GL−4.5）
m.Write(OUT, 8); print('written', OUT, 'river edge from', np.round(uv(*a), 1), 'to', np.round(uv(*b), 1))
