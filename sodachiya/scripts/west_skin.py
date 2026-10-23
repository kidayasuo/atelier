"""西館の外皮の輪郭 WS を data/wnew.pkl に足す（西館係、10-23）。
- WN（今までの輪郭）は架構の輪郭のまま残す（柱・梁・桁は WN から作る。柱は動かさない）。
- WS は外壁と屋根の輪郭：北西の斜めの外壁（u 約42〜51）を、西の外壁と同じ壁面後退の線（敷地の境から1.0）まで出す。
  角の丸み（R3.1、今の輪郭と同じ）は作り直し、北の短い外壁（u51）と西の外壁はそのまま。
- 壁面後退の線は 3dm の 00_敷地 の 2 本の線のうち小さい方（敷地の境を 1.0 内側へ）。
使い方: python3 scripts/west_skin.py  （sodachiya/ の中で）
"""
import os, sys, pickle, numpy as np, rhino3dm as r
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
from shapely.geometry import Polygon
from meshkit import RW

P = os.path.join(ROOT, 'data', 'wnew.pkl')
D = pickle.load(open(P, 'rb')); WN = D['WN']
m = r.File3dm.Read(os.path.join(ROOT, 'model', 'sodachiya_exact_mesh.3dm'))
polys = []
for o in m.Objects:
    if m.Layers[o.Attributes.LayerIndex].Name.startswith('00') and isinstance(o.Geometry, r.PolylineCurve):
        g = o.Geometry; polys.append(Polygon([[g.Point(i).X, g.Point(i).Y] for i in range(g.PointCount)]))
site, SB = sorted(polys, key=lambda p: -p.area)
assert abs(site.buffer(-1000, join_style=2).area - SB.area) < 1e5, '00_敷地の小さい方が壁面後退の線でない'
Z = RW(41.0, 51.0, 2.0, 16.0)                 # 北西の斜めの面のあたり（北の短い外壁 u51 から外へは出さない）
R = 3100.0                                    # 角の丸み（今の輪郭と同じ）
U = WN.union(SB.intersection(Z))
O = U.buffer(-R, join_style=1).buffer(R, join_style=1)
WS = WN.union(O.intersection(Z)).buffer(1).buffer(-1)
assert WS.difference(SB).area < 1e4
D['WS'] = WS
D['_WS_note'] = '外皮（外壁・屋根）の輪郭。北西の斜めの外壁を壁面後退の線まで（10-23、西館係）。架構は WN'
pickle.dump(D, open(P, 'wb'))
print('WS added: +%.2f m2 (gross), inside setback' % ((WS.area - WN.area) / 1e6))
