"""周辺の道路と建物（PLATEAU、data/context_plateau.json）を 3dm に
使い方: python3 add_context.py IN.3dm OUT.3dm data/context_plateau.json
- 03_周辺_道路（PLATEAU）：道路 LOD1 の面。高さは近くの建物の下端から内挿した地盤（敷地の GL を −300 として）。
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

nb = nr = skip_b = skip_r = 0
for b in J['bldg']:
    F = Polygon(np.array(b['foot']) * 1000).buffer(0)
    if F.is_empty or F.area < 2e6: continue
    if F.intersection(S).area > 0.3 * F.area: skip_b += 1; continue
    if b['z1'] - b['z0'] < 500: continue
    K.prism(F, float(b['z0']), float(b['z1']), L_BL); nb += 1
for rd in J['road']:
    Q = Polygon(np.array(rd['xy']) * 1000).buffer(0)
    if Q.is_empty: continue
    if Q.intersection(S).area > 0.3 * Q.area: skip_r += 1; continue      # 敷地の中を通る今の道
    Q = Q.difference(S.buffer(-50))
    for g in getattr(Q, 'geoms', [Q]):
        if g.geom_type != 'Polygon' or g.area < 1e5: continue
        tris = constrained_delaunay_triangles(g.simplify(20))
        mm = r.Mesh(); idx = {}
        def vid(p):
            k = (round(p[0], 1), round(p[1], 1))
            if k not in idx: idx[k] = mm.Vertices.Add(p[0], p[1], ground(*p) - 20.0)    # 舗装の面（地盤の 20 下、建物の足もととそろう程度）
            return idx[k]
        for t in getattr(tris, 'geoms', [tris]):
            c = list(t.exterior.coords)[:3]
            mm.Faces.AddFace(vid(c[0]), vid(c[1]), vid(c[2]))
        if mm.Faces.Count:
            mm.Normals.ComputeNormals(); mm.Compact()
            a = r.ObjectAttributes(); a.LayerIndex = L_RD; a.Name = rd['func'] or '道路'
            m.Objects.AddMesh(mm, a); nr += 1
m.Write(OUT, 8)
print('context: bldg', nb, '(site', skip_b, 'removed)  road', nr, '(site', skip_r, 'removed) →', OUT, len(m.Objects))
