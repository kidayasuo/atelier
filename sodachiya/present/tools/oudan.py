# -*- coding: utf-8 -*-
"""配置図 1/200 の横断歩道（ユーザー 11-02）：西の道を、橋の袂の三角形（道と公園のあいだ）の道の側の辺の中ほどから、
道に直角に向こう側の縁まで渡る。縞は日本の横断歩道の形（白い帯 幅0.45・すき間0.45、帯の長さ＝横断歩道の幅4.0、帯は道の向きに長い）。
配置図の素材（sozai/01a〜01d）と同じ紙の大きさ・同じ位置に描くので、.ai では配置図の素材と同じ所に重ねる。
道の縁は sozai/01b_配置図_1-200_色.pdf の道の面（灰 e2e2e0）から読む。"""
import os, sys, math
import numpy as np
import fitz
from shapely.geometry import Polygon, LineString, Point

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "sozai", "01b_配置図_1-200_色.pdf")
OUT = os.path.join(HERE, "sozai", "32_配置図_1-200_横断歩道.pdf")
M = 72 / 25.4 * 1000 / 200          # 1 m（実寸）＝ 紙の上の pt（1/200）
BAR, GAP, LEN = 0.45, 0.45, 4.0      # 帯の幅・すき間・帯の長さ（m）
EDGE = 0.3                           # 道の縁から帯までの最小（m）。帯は道の真ん中にそろえる

src = fitz.open(SRC)
pg = src[0]
road = None
_T = np.array([257.9, 1224.3])          # 三角形の道の側の辺の上の点（紙の pt）
def _d(dr):
    best = 1e9
    for it in dr["items"]:
        if it[0] in ("l", "c"):
            a, b = np.array(it[1]), np.array(it[-1])
            v = b - a
            tt = np.clip(np.dot(_T - a, v) / max(np.dot(v, v), 1e-9), 0, 1)
            best = min(best, np.linalg.norm(a + tt * v - _T))
    return best
_c = [dr for dr in pg.get_drawings() if dr.get("fill") and all(abs(x - y) < 0.01 for x, y in zip(dr["fill"], (0.886, 0.886, 0.878)))]
road = min(_c, key=_d) if _c else None
assert road, "道の面が見つからない"
print("道の面", [round(v) for v in road["rect"]], len(road["items"]))
# 道の縁の線分（曲線は端点で近似）
segs = []
for it in road["items"]:
    if it[0] == "l":
        segs.append((np.array(it[1]), np.array(it[2])))
    elif it[0] == "c":
        segs.append((np.array(it[1]), np.array(it[4])))
# 三角形の道の側の辺：公園の北西の角から川の側の縁まで（この2本）
e1 = (np.array([290.9, 1157.3]), np.array([224.9, 1291.3]))
e2 = (np.array([224.9, 1291.3]), np.array([210.9, 1325.8]))
def near(a, b):
    s = min(segs, key=lambda s: min(np.linalg.norm(s[0] - a) + np.linalg.norm(s[1] - b), np.linalg.norm(s[0] - b) + np.linalg.norm(s[1] - a)))
    return (s[0], s[1]) if np.linalg.norm(s[0] - a) < np.linalg.norm(s[0] - b) else (s[1], s[0])
e1, e2 = near(*e1), near(*e2)
L1, L2 = np.linalg.norm(e1[1] - e1[0]), np.linalg.norm(e2[1] - e2[0])
h = (L1 + L2) / 2
P0 = e1[0] + (e1[1] - e1[0]) * (h / L1) if h <= L1 else e2[0] + (e2[1] - e2[0]) * ((h - L1) / L2)
r = (e1[1] - e1[0]) / L1                 # 道の向き（縁に沿う）
n = np.array([r[1], -r[0]])              # 縁に直角、道の中へ（西北西）
if n[0] > 0:
    n = -n
# 向こう側の縁：P0 から n の向きで道の縁に当たる最初の点（自分の縁は除く）
ray = LineString([P0 + n * 0.5, P0 + n * 40 * M])
hits = []
for a, b in segs:
    x = ray.intersection(LineString([a, b]))
    if not x.is_empty and x.geom_type == "Point":
        hits.append(np.linalg.norm(np.array(x.coords[0]) - P0))
W = min(hits) / M if hits else 0.0                       # 渡る長さ（m）
print("渡る長さ %.2f m、向き（紙の上、右＝0°・上＝90°）%.1f°" % (W, math.degrees(math.atan2(-n[1], n[0]))))

out = fitz.open()
op = out.new_page(width=pg.rect.width, height=pg.rect.height)
N = int((W - 2 * EDGE + GAP) // (BAR + GAP))      # 入る本数、両端の余りを等しく（道の真ん中にそろえる）
t = (W - (N * (BAR + GAP) - GAP)) / 2
k = 0
while k < N:
    c0 = P0 + n * t * M
    c1 = P0 + n * (t + BAR) * M
    q = [c0 - r * LEN / 2 * M, c1 - r * LEN / 2 * M, c1 + r * LEN / 2 * M, c0 + r * LEN / 2 * M]
    op.draw_polyline([fitz.Point(*p) for p in q] + [fitz.Point(*q[0])], color=None, fill=(1, 1, 1), closePath=True)
    t += BAR + GAP
    k += 1
print("帯 %d 本（幅%.2f・すき間%.2f・長さ%.1f m）" % (k, BAR, GAP, LEN))
out.save(OUT)
print(OUT)
