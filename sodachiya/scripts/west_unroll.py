"""西館の外壁の展開立面（西館係、10-26）。外皮の外周 WS に沿って s（南東の角から時計回り…外周の向きのまま）と高さ z で、
外壁（21）・ガラスと建具（19・19b・27）・押縁（21b）を塗る。窓の割付を確かめるための図。
python3 scripts/west_unroll.py <3dm> <out.png>"""
import sys, os, pickle
import numpy as np, rhino3dm as r
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'model', 'build', 'south'))
from uv import uv, xy
from shapely.geometry import Point
D = pickle.load(open(os.path.join(HERE, '..', 'data', 'wnew.pkl'), 'rb'))
WS = D.get('WS', D['WN']); ring = WS.exterior
m = r.File3dm.Read(sys.argv[1]); lay = [l.Name for l in m.Layers]
COL = {'21_': '#c8a979', '21e': '#6b4a28', '19_': '#7fb3d5', '19b': '#8a6a45', '27_': '#7fb3d5', '19c': '#7fb3d5', '19d': '#7fb3d5'}
polys = {k: [] for k in COL}
def tris(g):
    if isinstance(g, r.Extrusion): g = g.GetMesh(r.MeshType.Any) or None
    if g is None or not isinstance(g, r.Mesh): return np.zeros((0, 3, 3))
    V = np.array([[v.X, v.Y, v.Z] for v in g.Vertices]); out = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; out.append(V[[f[0], f[1], f[2]]])
        if f[2] != f[3]: out.append(V[[f[0], f[2], f[3]]])
    return np.array(out)
L = ring.length
for o in m.Objects:
    n = lay[o.Attributes.LayerIndex]
    k = next((k for k in COL if n.startswith(k)), None)
    if k is None: continue
    T = tris(o.Geometry)
    if not len(T): continue
    c = T.mean(1)
    if (np.array([uv(x, y)[1] for x, y in c[:, :2]]) > -1.2).all(): continue      # 東の面（すき間の側）は除く
    for t in T:
        N = np.cross(t[1] - t[0], t[2] - t[0]); nn = np.linalg.norm(N)
        if nn < 1 or abs(N[2]) / nn > 0.3: continue                                   # 立った面だけ
        pc = Point(*t.mean(0)[:2])
        if ring.distance(pc) > 400: continue
        if WS.buffer(-5).contains(Point(*(t.mean(0)[:2] + N[:2] / nn * 30))): continue  # 外向きの面だけ
        s = [ring.project(Point(*p[:2])) for p in t]
        if max(s) - min(s) > L / 2: s = [x + L if x < L / 2 else x for x in s]
        sm = np.array(s) / 1000
        if not ((sm <= 20.2).all() or (sm >= 49.8).all()): continue           # 東の面（すき間の側）とのつなぎは描かない
        if (sm >= 49.8).all(): sm = sm - 49.8 + 21.0                          # 南の妻から西の面を、北の妻のあとに続けて並べる
        polys[k].append(np.c_[sm, t[:, 2] / 1000])
fig, ax = plt.subplots(figsize=(22, 4.2))
for k in COL:
    if polys[k]: ax.add_collection(PolyCollection(polys[k], facecolor=COL[k], edgecolor='none', lw=0, antialiased=False))
# 大和張りの見えの割り（約120）を細い縦線で：外壁の面（21）の形で切る。三角形の縁は描かない（前は網目の分け方の斜め線が見えていた）
from shapely.geometry import Polygon as _Pg, LineString as _Ls
from shapely.ops import unary_union as _uu
_wall = _uu([_Pg(p).buffer(0.002) for p in polys['21_'] if _Pg(p).is_valid and _Pg(p).area > 1e-6]).buffer(-0.002)
if not _wall.is_empty:
    x0_, y0_, x1_, y1_ = _wall.bounds
    for x in np.arange(x0_, x1_, 0.12):
        seg = _Ls([(x, y0_ - 1), (x, y1_ + 1)]).intersection(_wall)
        for g in getattr(seg, 'geoms', [seg]):
            if g.geom_type == 'LineString' and g.length > 0: ax.plot(*g.xy, color='#a88a5e', lw=0.25)
# 架構の線（u ごと）を外周に投影して印
for u in np.arange(21, 52, 3):
    for v in (-30,):
        pass
ax.autoscale(); ax.set_aspect('equal'); ax.grid(alpha=.3)
for s0, s1, t in ((0, 14, 'NW face (playroom, big door)'), (14, 20, 'north gable'), (21.2, 30.7, 'south gable'), (34, 53, 'west face: kitchen | staff | playroom')):
    ax.text((s0 + s1) / 2, 8.6, t, ha='center', fontsize=11)
ax.set_xticks(np.arange(0, 54, 2)); ax.axvline(20.6, color='k', lw=0.5, ls=':')
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=70)
print('ring length', round(L / 1000, 2))
