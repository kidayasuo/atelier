"""押し出し（rhino3dm.Extrusion）の輪郭を編集して押し出しのまま返す（西館係、10-25。ソリッド係の依頼：柱・梁・桁を網目にせず
押し出しのまま残す → Rhino 版で曲線・平らな面のまま出せる）。
edit(g, fn, path_fn=None)：
  fn(P, k) → P'：k 番目の輪郭（0＝外、1〜＝穴）の制御点（世界座標の (n,3) 配列、押し出しの始まりの面の上）を動かす。
  path_fn(a, b) → (a', b')：押し出しの道の両端（世界座標）を動かす（桁の上を屋根に合わせて傾けるなど）。
制御点を動かしても節（ノット）と次数はそのままなので、曲線は曲線のまま。"""
import numpy as np
import rhino3dm as r

def _pts(nc):
    """制御点（ユークリッド座標）。rhino3dm の Points は同次座標（x·w, y·w, z·w, w）"""
    P = []
    for i in range(len(nc.Points)):
        p = nc.Points[i]; w = p.W if p.W else 1.0
        P.append([p.X / w, p.Y / w, p.Z / w])
    return np.array(P)

def _set_pts(nc, P, W):
    for i, (x, y, z) in enumerate(P):
        nc.Points[i] = r.Point4d(x * W[i], y * W[i], z * W[i], W[i])

def _weights(nc):
    out = []
    for i in range(len(nc.Points)):
        p = nc.Points[i]
        w = getattr(p, 'W', 1.0)
        out.append(w if w else 1.0)
    return np.array(out, float)

def profiles3d(g):
    return [g.Profile3d(k, 0.0).ToNurbsCurve() for k in range(g.ProfileCount)]

def edit(g, fn=None, path_fn=None):
    """押し出し g の輪郭（と道）を動かした新しい押し出しを返す。うまくいかなければ None"""
    pl = g.GetProfilePlane(0.0)
    O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z])
    X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    a, b = g.PathStart, g.PathEnd
    A = np.array([a.X, a.Y, a.Z]); B = np.array([b.X, b.Y, b.Z])
    curves2d = []
    for k_, nc in enumerate(profiles3d(g)):
        W = _weights(nc); P = _pts(nc)
        if fn is not None: P = np.asarray(fn(P.copy(), k_), float)
        Q = np.c_[(P - O) @ X, (P - O) @ Y, np.zeros(len(P))]          # 輪郭の面の 2 次元へ
        _set_pts(nc, Q, W)
        curves2d.append(nc)
    if path_fn is not None:
        A2, B2 = path_fn(A.copy(), B.copy())
    else:
        A2, B2 = A, B
    e = r.Extrusion()
    up = pl.YAxis
    if not e.SetPathAndUp(r.Point3d(*map(float, A2)), r.Point3d(*map(float, B2)), up): return None
    if not e.SetOuterProfile(curves2d[0], True): return None
    for c2 in curves2d[1:]:
        if not e.AddInnerProfile(c2): return None
    return e

def samples(g, n=120, ends=(0.0, 1.0)):
    """押し出しの輪郭の上の点（両端の面、全部の輪郭）→ (m,3)"""
    out = []
    for s in ends:
        for k in range(g.ProfileCount):
            c = g.Profile3d(k, s)
            out += [[p.X, p.Y, p.Z] for p in (c.PointAt(t) for t in np.linspace(c.Domain.T0, c.Domain.T1, n))]
    return np.array(out)

def outer_samples(g, n=400):
    c = g.Profile3d(0, 0.0)
    return np.array([[p.X, p.Y, p.Z] for p in (c.PointAt(t) for t in np.linspace(c.Domain.T0, c.Domain.T1, n))])
