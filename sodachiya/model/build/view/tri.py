import numpy as np, rhino3dm as r, math
import mapbox_earcut as earcut
from shapely.geometry import Polygon
def curve_pts(c, n=48):
    if isinstance(c, r.PolylineCurve): return [c.Point(i) for i in range(c.PointCount)]
    if isinstance(c, r.LineCurve): return [c.PointAtStart, c.PointAtEnd]
    d = c.Domain; return [c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]
A3 = lambda ps: np.array([[p.X, p.Y, p.Z] for p in ps], float)

def tri_mesh(g):
    V = A3([g.Vertices[i] for i in range(len(g.Vertices))]); T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; T.append((f[0], f[1], f[2]))
        if f[3] != f[2]: T.append((f[0], f[2], f[3]))
    return V[np.array(T)] if T else np.zeros((0, 3, 3))

def cap(rings):
    """平らな輪（外＋穴）→ 三角形"""
    P = np.vstack(rings); c = P.mean(0)
    n = np.zeros(3)
    for ring in rings[:1]:
        for i in range(len(ring)): n += np.cross(ring[i] - c, ring[(i + 1) % len(ring)] - c)
    if np.linalg.norm(n) < 1e-9: return []
    n /= np.linalg.norm(n); a = np.array([1., 0, 0]) if abs(n[0]) < .9 else np.array([0, 1., 0])
    x = np.cross(n, a); x /= np.linalg.norm(x); y = np.cross(n, x)
    Q = np.c_[(P - c) @ x, (P - c) @ y]
    ends = np.cumsum([len(rg) for rg in rings]).astype(np.uint32)
    idx = earcut.triangulate_float64(Q, ends)
    return [P[idx[i:i + 3]] for i in range(0, len(idx), 3)]

def tri_extrusion(g):
    T = []
    for k in range(g.ProfileCount):
        c0 = g.Profile3d(k, 0.0)
        if c0 is None: continue
        dvec = np.array([g.PathEnd.X - g.PathStart.X, g.PathEnd.Y - g.PathStart.Y, g.PathEnd.Z - g.PathStart.Z])
        p0 = A3(curve_pts(c0)); p1 = p0 + dvec           # まっすぐな押し出し：上の輪は下の輪を道の分だけ動かしたもの（始点のずれでねじれない）
        for i in range(len(p0) - 1):
            T += [np.array([p0[i], p0[i + 1], p1[i + 1]]), np.array([p0[i], p1[i + 1], p1[i]])]
    dvec = np.array([g.PathEnd.X - g.PathStart.X, g.PathEnd.Y - g.PathStart.Y, g.PathEnd.Z - g.PathStart.Z])
    for s in (0.0, 1.0):
        rings = []
        for k in range(g.ProfileCount):
            c = g.Profile3d(k, 0.0)
            if c is not None:
                q = A3(curve_pts(c)) + dvec * s; rings.append(q[:-1] if np.allclose(q[0], q[-1]) else q)
        if rings and g.IsClosed(0) if hasattr(g, 'IsClosed') else rings:
            try:
                # 輪の 0 番が外形、その中にある輪は穴。外にある輪（離れた別の形）は別に塞ぐ
                P_ = np.vstack(rings); mu_ = P_.mean(0); _, _, Vt_ = np.linalg.svd(P_ - mu_); B_ = Vt_[:2]
                pol = [Polygon((rg - mu_) @ B_.T).buffer(0) for rg in rings]
                inner = [rings[0]] + [rg for rg, pg in zip(rings[1:], pol[1:]) if pol[0].contains(pg.representative_point())]
                T += cap(inner)
                for rg, pg in zip(rings[1:], pol[1:]):
                    if not pol[0].contains(pg.representative_point()): T += cap([rg])
            except Exception: pass
    return np.array(T) if T else np.zeros((0, 3, 3))

def tri_brep(g, n=24):
    T = []
    for i in range(len(g.Surfaces)):
        s = g.Surfaces[i]; du, dv = s.Domain(0), s.Domain(1)
        G = [[s.PointAt(du.T0 + (du.T1 - du.T0) * a / n, dv.T0 + (dv.T1 - dv.T0) * b / n) for b in range(n + 1)] for a in range(n + 1)]
        G = np.array([[[p.X, p.Y, p.Z] for p in row] for row in G])
        for a in range(n):
            for b in range(n):
                T += [G[[a, a + 1, a + 1], [b, b, b + 1]], G[[a, a + 1, a], [b, b + 1, b + 1]]]
    return np.array(T) if T else np.zeros((0, 3, 3))

