"""西館の架構の柱（22a、名前なし）の輪郭を作り直す（11-04 設計監修、ユーザー 08:18：頭に対して穴が偏る・大きい、力学的に問題のある形）。
柱の足から、まっすぐな辺（足もとと 1.5 m の幅の線をそのまま上へ）＋ 穴（桁の通る穴）ごとに丸い膨らみ（穴の外接の楕円＋木の厚み 180、
Tamedia の頭・梁の丸い頭と同じ）を、なめらかな首（凸包）でつなぐ。頭は元の輪郭の凸包（＝梁の上端・屋根の下）を越えない。穴はそのまま。
使い方：python3 west_col_heads.py in.3dm out.3dm"""
import sys, math
import numpy as np
import rhino3dm as r
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
from shapely import affinity

M_WOOD = 180.0        # 穴のまわりの木の厚み（梁の丸い頭と同じ）
F2_BOT, F2_TOP = 3170.0, 3700.0   # 西館の2階の床の下面と、2階で首を広げない高さ
NECK = 250.0          # 膨らみの上下の、首のなめらかさ（凸包に入れる幅の帯）


def _v3(p): return np.array([p.X, p.Y, p.Z])


def _pts(c, n=500):
    d = c.Domain
    return np.array([_v3(c.PointAt(d.T0 + (d.T1 - d.T0) * i / n)) for i in range(n)])


def _span(poly, z0, z1):
    q = poly.intersection(box(-1e6, z0, 1e6, z1))
    if q.is_empty: return None
    b = q.bounds; return b[0], b[2]


def rebuild(g):
    A, B = _v3(g.PathStart), _v3(g.PathEnd)
    pd = B - A; pd[2] = 0; pd /= np.linalg.norm(pd)
    H = np.cross([0, 0, 1.0], pd); H /= np.linalg.norm(H)
    to2 = lambda P: np.c_[(P - A) @ H, P[:, 2]]
    outer = Polygon(to2(_pts(g.Profile3d(0, 0.0)))).buffer(0)
    holes = [Polygon(to2(_pts(g.Profile3d(k, 0.0)))).buffer(0) for k in range(1, g.ProfileCount)]
    if not holes: return None, None
    zmin = outer.bounds[1]
    f0 = _span(outer, zmin + 100, zmin + 400); f1 = _span(outer, 1400, 1600)
    if f0 is None or f1 is None: return None, None
    za, zb = zmin + 250, 1500.0
    kl = (f1[0] - f0[0]) / (zb - za); kr = (f1[1] - f0[1]) / (zb - za)
    sx = lambda z: (f0[0] + kl * (z - za), f0[1] + kr * (z - za))
    hh = max(holes, key=lambda h: h.centroid.y)
    ztop = hh.bounds[1]                                    # 軸は頭の穴の下まで
    l0, r0 = sx(zmin); l1, r1 = sx(ztop)
    shaft = Polygon([(l0, zmin), (r0, zmin), (r1, ztop), (l1, ztop)]).buffer(0)
    parts = [shaft]
    for h in holes:
        b = h.bounds; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        a_ = (b[2] - b[0]) / 2 + M_WOOD; b_ = (b[3] - b[1]) / 2 + M_WOOD
        ell = affinity.scale(Point(0, 0).buffer(1.0, 64), a_, b_, origin=(0, 0))
        ell = affinity.translate(ell, cx, cy)
        z0, z1 = cy - b_ - NECK, (cy + b_) if h is not hh else cy
        if h is hh and len(holes) > 1: z0 = max(z0, F2_TOP)     # 2階のある柱（架構8〜12）：2階の床の上では首を広げない
        sl = shaft.intersection(box(-1e6, z0, 1e6, z1))
        parts.append(unary_union([ell, sl]).convex_hull)
    new = unary_union(parts)
    # 上の限り＝元の輪郭の上端の線（屋根の面で切った線、凸包の上の辺を直線に）。横には限らない
    hv = np.array(outer.convex_hull.exterior.coords); hv = hv[hv[:, 1] > hh.bounds[3]]
    if len(hv) >= 2 and np.ptp(hv[:, 0]) > 50:
        a_t = np.polyfit(hv[:, 0], hv[:, 1], 1)[0]
    else:
        a_t = 0.0
    c_t = float(np.max(hv[:, 1] - a_t * hv[:, 0])) if len(hv) else outer.bounds[3]
    X0, X1 = outer.bounds[0] - 2000, outer.bounds[2] + 2000
    cap = Polygon([(X0, zmin - 1), (X1, zmin - 1), (X1, a_t * X1 + c_t), (X0, a_t * X0 + c_t)])
    new = new.intersection(cap)
    if len(holes) > 1:                                     # 2階の床の下面〜F2_TOP は元の輪郭より外へ出さない（床・間仕切りは元の柱で欠いてある、11-04 干渉 6）
        band = box(-1e6, F2_BOT, 1e6, F2_TOP)
        new = unary_union([new.difference(band), new.intersection(band).intersection(outer)])
    if new.geom_type != 'Polygon': new = max(new.geoms, key=lambda q: q.area)
    new = new.simplify(1.0)
    # 穴のまわりの木の最小の厚み（報告用）
    mins = [round(new.exterior.distance(h.exterior)) for h in holes]
    # 3D へ戻し、押し出しの面の座標に
    pl = g.GetProfilePlane(0.0); O, X, Y = _v3(pl.Origin), _v3(pl.XAxis), _v3(pl.YAxis)
    def loc(Q):
        P = A[None, :] + Q[:, :1] * H[None, :] + (Q[:, 1:2] - A[2]) * np.array([[0, 0, 1.0]])
        return np.c_[(P - O) @ X, (P - O) @ Y]
    Q = loc(np.array(new.exterior.coords))
    pc = r.Polyline(len(Q))
    for x, y in Q: pc.Add(float(x), float(y), 0.0)
    e = r.Extrusion()
    if not e.SetPathAndUp(g.PathStart, g.PathEnd, pl.YAxis): return None, None
    if not e.SetOuterProfile(pc.ToNurbsCurve(), True): return None, None
    for k in range(1, g.ProfileCount):
        nc = g.Profile3d(k, 0.0).ToNurbsCurve()
        for i in range(len(nc.Points)):
            p = nc.Points[i]; w = p.W if p.W else 1.0
            q = np.array([p.X / w, p.Y / w, p.Z / w]) - O
            nc.Points[i] = r.Point4d(float(q @ X) * w, float(q @ Y) * w, 0.0, w)
        if not e.AddInnerProfile(nc): return None, None
    return e, (outer, new, holes, mins)


def main(src, dst):
    m = r.File3dm.Read(src)
    L = [i for i, l in enumerate(m.Layers) if l.FullPath.split('::')[-1].startswith('22a_西館')]
    out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
    for l in m.Layers: out.Layers.Add(l)
    for mt in m.Materials: out.Materials.Add(mt)
    n = 0; rep = []
    for o in m.Objects:
        g = o.Geometry
        if o.Attributes.LayerIndex in L and not (o.Attributes.Name or '') and isinstance(g, r.Extrusion) and g.ProfileCount >= 2 \
                and g.GetBoundingBox().Max.Z < 6500:              # 西の低い柱だけ（東の高い柱はきれいな丸い頭）
            e, info = rebuild(g)
            if e is not None:
                g = e; n += 1; rep.append(info[3])
        out.Objects.Add(g, o.Attributes)
    out.Write(dst, 8)
    print(f'西館の架構の柱 {n} 本の輪郭を作り直した（まっすぐな辺＋穴ごとの丸い膨らみ、木の厚み{int(M_WOOD)}）。穴のまわりの木の最小 {min(min(x) for x in rep) if rep else "-"} mm')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
