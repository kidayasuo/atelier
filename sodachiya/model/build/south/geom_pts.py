"""3dm のオブジェクトの点（形の確認・図化用）"""
import numpy as np, rhino3dm as r
def curve_pts(c, n=48):
    if isinstance(c, r.PolylineCurve): return [c.Point(i) for i in range(c.PointCount)]
    d = c.Domain; return [c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]
def pts(g):
    P = []
    if isinstance(g, r.Mesh):
        P = [g.Vertices[i] for i in range(len(g.Vertices))]
    elif isinstance(g, r.Extrusion):
        for k in range(g.ProfileCount):
            for s in (0.0, 1.0):
                c = g.Profile3d(k, s)
                if c: P += curve_pts(c)
    elif isinstance(g, r.Brep):
        for i in range(len(g.Edges)): P += curve_pts(g.Edges[i], 16)
    elif isinstance(g, r.Curve):
        P = curve_pts(g)
    return np.array([[p.X, p.Y, p.Z] for p in P]) if P else np.zeros((0, 3))
