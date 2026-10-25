"""周辺の道路と建物（PLATEAU、data/context_plateau.json）を 3dm に
使い方: python3 add_context.py IN.3dm OUT.3dm data/context_plateau.json
- 03_周辺_道路（PLATEAU）：道路 LOD1 の面を一枚にまとめ、平らに（敷地の GL −300 の 20 下、10-25 ユーザー）。西の道・北の道の建物の側の縁は敷地の境にそろえる。
- 04_周辺_建物（PLATEAU LOD1）：建物の外形を下端から上端まで押し出した箱（LOD1 なので屋根の形は無い）。
- 敷地の中の今の住宅と、敷地の中を通る今の道は入れない（課題はそれを取り払った計画）。
- 出典：国土交通省 Project PLATEAU（京都市 2025 年度）。
"""
import sys, json, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/south')
from shapely.geometry import Polygon, LineString
from shapely import constrained_delaunay_triangles
from meshkit import Kit

IN, OUT, CJ = sys.argv[1:4]
J = json.load(open(CJ, encoding='utf-8'))
m = r.File3dm.Read(IN)
def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
L_RD = layer('03_周辺_道路（PLATEAU）', (175, 175, 170))
L_BL = layer('04_周辺_建物（PLATEAU LOD1）', (205, 200, 190))
K = Kit(m)

# 敷地（00 の大きい方、mm）
site = None
for o in m.Objects:
    if m.Layers[o.Attributes.LayerIndex].Name.startswith('00_') and isinstance(o.Geometry, r.PolylineCurve):
        g = o.Geometry; P = np.array([[g.Point(i).X, g.Point(i).Y] for i in range(g.PointCount)])
        if site is None or Polygon(P).area > Polygon(site).area: site = P
S = Polygon(site)

# 地盤の高さ：建物の下端（mm）を点として内挿
GP = np.array([[*Polygon(np.array(b['foot']) * 1000).centroid.coords[0], b['z0']] for b in J['bldg']])
def ground(x, y):
    d = np.hypot(GP[:, 0] - x, GP[:, 1] - y) + 1000.0
    w = 1.0 / d ** 2; i = np.argsort(d)[:8]
    return float((GP[i, 2] * w[i]).sum() / w[i].sum())

# 西の道の向かいの住宅3軒（北の三軒）を、塊の南の角を中心に回して、課題の敷地図の道の縁に沿わせる（ユーザー、10-26）。
# PLATEAU では道の縁に対して約12.6°開いていた。課題の敷地図（present/kadai_map.json の西の道の西の縁）の向きに合わせる
from shapely import affinity as _aff
ROT_BLOCK = {'ids': ('bldg_15ae39bf-872c-42a8-889f-3138a573794e', 'bldg_d62c7741-c440-4c87-ab0c-1fd708e067e3',
                     'bldg_cb1d1a2b-6ef5-4bb0-890a-fffa0ca64a4f'),
             'pivot': (-31148.0, -47801.0), 'deg': -12.65}
nb = nr = skip_b = skip_r = 0
for b in J['bldg']:
    F = Polygon(np.array(b['foot']) * 1000).buffer(0)
    if b.get('id') in ROT_BLOCK['ids']: F = _aff.rotate(F, ROT_BLOCK['deg'], origin=ROT_BLOCK['pivot'])
    if F.is_empty or F.area < 2e6: continue
    if F.intersection(S).area > 0.3 * F.area: skip_b += 1; continue
    if b['z1'] - b['z0'] < 500: continue
    K.prism(F, float(b['z0']), float(b['z1']), L_BL); nb += 1
# 道路（10-25、ユーザー）：平らな一枚に（道の少々の起伏は無視する。平面図に道路の片の継ぎ目や斜めの三角形の筋が入らないように）。
# 敷地に接する西の道・北の道は、建物の側の縁だけを敷地の境にそろえる（道が敷地にかかる所は削り、敷地とのすき間は道で埋める。
# 道の向こう側の縁は PLATEAU のまま）。元々道路と敷地が正確ではない（ユーザー）。
from shapely.geometry import LineString
from shapely.ops import unary_union
Z_RD = -320.0                       # 舗装の面：敷地の GL（−300）の 20 下
# 敷地の西の辺・北の辺（敷地の外形のうち、道に接する辺：00 の外形の頂点の並びから、道に 3 m 以内の辺）
ring = list(S.exterior.coords)
EDG = [LineString([ring[k], ring[k + 1]]) for k in range(len(ring) - 1)]
def _out(e):        # 辺の外向きの向き
    (x0, y0), (x1, y1) = e.coords; d = np.array([x1 - x0, y1 - y0]) / e.length; n = np.array([d[1], -d[0]])
    c = np.array(e.centroid.coords[0])
    return n if not S.contains(Polygon([c, c + n * 10 + d, c + n * 10 - d]).centroid) else -n
# 西の道（外向きが西）と北の道（外向きが北西＝川と直角）の辺だけ。川・公園・北東の隣家の辺は触らない
EDG = [e for e in EDG if e.length > 5000 and (_out(e) @ np.array([-1.0, 0.0]) > 0.9 or _out(e) @ np.array([-0.6225, 0.7826]) > 0.95)]
from shapely.ops import linemerge
ED = linemerge(unary_union(EDG))       # 一本の線に（角で帯が途切れて三角のすき間が残らないように）
RQ = []
for rd in J['road']:
    Q = Polygon(np.array(rd['xy']) * 1000).buffer(0)
    if Q.is_empty: continue
    QS = Q.intersection(S)
    # 敷地の中を通る今の道は入れない。ただし西の道・北の道の片が敷地にかかっているだけ（かかる所がおもに辺から 8 m 以内）なら入れる（かかる所は後で削る）
    if QS.area > 0.3 * Q.area and not QS.difference(ED.buffer(8000)).area < 0.25 * QS.area: skip_r += 1; continue
    RQ.append(Q)
RD = unary_union(RQ).buffer(50, join_style=2).buffer(-50, join_style=2)     # 片のあいだの細いすき間を閉じる
WB = 12000.0
band = S.buffer(WB, join_style=2).difference(S).intersection(ED.buffer(WB + 500, cap_style=2, join_style=2))
outer = S.buffer(WB, join_style=2).exterior
gaps = []
rest = band.difference(RD)
for g in getattr(rest, 'geoms', [rest]):
    if g.geom_type != 'Polygon' or g.area < 1e4: continue
    if g.distance(ED) < 50 and g.distance(outer) > 50:      # 敷地の辺と道のあいだに挟まれたすき間だけ（道の向こう側へ抜ける所は埋めない）
        gaps.append(g)
RD = unary_union([RD] + gaps).difference(S)
RD = RD.buffer(20, join_style=2).buffer(-20, join_style=2).difference(S)
print('road: edges', len(EDG), 'gaps', len(gaps), round(sum(g.area for g in gaps) / 1e6, 1), 'm2')
for g in getattr(RD, 'geoms', [RD]):
    if g.geom_type != 'Polygon' or g.area < 1e5: continue
    g = g.simplify(20)
    tris = constrained_delaunay_triangles(g)
    mm = r.Mesh(); idx = {}
    def vid(p):
        k = (round(p[0], 1), round(p[1], 1))
        if k not in idx: idx[k] = mm.Vertices.Add(p[0], p[1], Z_RD)
        return idx[k]
    for t in getattr(tris, 'geoms', [tris]):
        c = list(t.exterior.coords)[:3]
        mm.Faces.AddFace(vid(c[0]), vid(c[1]), vid(c[2]))
    if mm.Faces.Count:
        mm.Normals.ComputeNormals(); mm.Compact()
        a = r.ObjectAttributes(); a.LayerIndex = L_RD; a.Name = '道路（平ら）'
        m.Objects.AddMesh(mm, a); nr += 1
m.Write(OUT, 8)
print('context: bldg', nb, '(site', skip_b, 'removed)  road', nr, '(site', skip_r, 'removed) →', OUT, len(m.Objects))
