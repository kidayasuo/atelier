"""西館の外皮の輪郭 WS を data/wnew.pkl に足す（西館係、10-23）。
- WN（今までの輪郭）は架構の輪郭のまま残す（柱・梁・桁は WN から作る。柱は動かさない）。
- WS は外壁と屋根の輪郭：北西の斜めの外壁（u 約42〜51）を、西の外壁と同じ壁面後退の線（敷地の境から1.0）まで出す。
  角の丸み（R3.1、今の輪郭と同じ）は作り直し、北の短い外壁（u51）と西の外壁はそのまま。
- 壁面後退の線は 3dm の 00_敷地 の 2 本の線のうち小さい方（敷地の境を 1.0 内側へ）。
- 小さな段の掃除（11-02、西館係）：WN（u41 まで）と丸め直した角（u41 から）の継ぎ目に、約4 mm の段（と、buffer で丸まった
  細かい点の列）が残っていた。外壁の内面（150 内側）ではこれが細かい弧の片になり、Rhino版で曲面（円環）に当てはめられて、
  遊戯室スパン14の西の外壁にレンズ形の面が飛び出した（ユーザー 11-02）。短い辺（20 mm 未満）が続く広がり 5 mm 未満の点の列を、
  いちばん外の1点にまとめる（WS と WN の両方。東の面の柱の欠き込み 7〜21 mm は残る）。
使い方: python3 scripts/west_skin.py  （sodachiya/ の中で）
        python3 scripts/west_skin.py --jog   今の WS・WN の段の掃除だけ（輪郭は作り直さない）
"""
import os, sys, pickle, numpy as np, rhino3dm as r
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
from shapely.geometry import Polygon, Point
from meshkit import RW

P = os.path.join(ROOT, 'data', 'wnew.pkl')
D = pickle.load(open(P, 'rb')); WN = D['WN']

def no_jog(poly, seg=20.0, ext=5.0):
    """外の輪の、短い辺（seg 未満）が続く広がり ext 未満の点の列を、いちばん外（内へ 50 の輪郭から遠い）の1点にまとめる"""
    c = np.asarray(poly.exterior.coords)[:-1]; n = len(c)
    d = np.linalg.norm(np.roll(c, -1, 0) - c, axis=1)
    k0 = int(np.argmax(d))                       # 長い辺の終わりから回す（列が輪の継ぎ目にまたがらない）
    c = np.roll(c, -(k0 + 1), 0); d = np.roll(d, -(k0 + 1))
    core = poly.buffer(-50.0)
    out, i = [], 0
    while i < n:
        j = i
        while j < n - 1 and d[j] < seg: j += 1
        run = c[i:j + 1]
        if len(run) > 1 and np.ptp(run, 0).max() < ext:
            out.append(max(run, key=lambda q: core.exterior.distance(Point(q))))
        else:
            out.extend(run)
        i = j + 1
    q = Polygon(out, [h.coords for h in poly.interiors])
    assert q.is_valid and abs(q.area - poly.area) < 5e4, '段の掃除で形が変わりすぎた'
    return q

if '--jog' in sys.argv:
    for k in ('WS', 'WN'):
        a = len(D[k].exterior.coords); D[k] = no_jog(D[k]); print(k, a, '->', len(D[k].exterior.coords), '点')
    pickle.dump(D, open(P, 'wb')); sys.exit()
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
WS = no_jog(WN.union(O.intersection(Z)).buffer(1).buffer(-1))
assert WS.difference(SB).area < 1e4
D['WS'] = WS
D['_WS_note'] = '外皮（外壁・屋根）の輪郭。北西の斜めの外壁を壁面後退の線まで（10-23、西館係）。架構は WN'
pickle.dump(D, open(P, 'wb'))
print('WS added: +%.2f m2 (gross), inside setback' % ((WS.area - WN.area) / 1e6))
