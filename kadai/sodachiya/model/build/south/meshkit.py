"""メッシュを作る小さな道具（add_play.py などで使う）。座標は mm、(u, v) は本館の座標 m（uv.py）"""
import math, numpy as np, rhino3dm as r
from shapely.geometry import Polygon
import mapbox_earcut as earcut
from uv import xy

def R(u0, u1, v0, v1, step=0.25):
    """(u, v) の長方形 → 世界座標の多角形（u の方向は弧に沿って細かく）"""
    us = np.linspace(u0, u1, max(2, int(abs(u1 - u0) / step) + 1))
    return Polygon([xy(u, v0) for u in us] + [xy(u, v1) for u in us[::-1]]).buffer(0)
def RW(u0, u1, w0, w1, step=0.25):
    """西館の「東から」w（v = −0.9 − w）で"""
    return R(u0, u1, -0.9 - w0, -0.9 - w1, step)

class Kit:
    def __init__(s, model): s.m = model
    def attr(s, li, col=None):
        a = r.ObjectAttributes(); a.LayerIndex = li
        if col is not None:
            a.ColorSource = r.ObjectColorSource.ColorFromObject; a.ObjectColor = (*col, 255)
        return a
    def add(s, mm, li, col=None):
        mm.Normals.ComputeNormals(); mm.Compact(); s.m.Objects.AddMesh(mm, s.attr(li, col))
    def prism(s, poly, z0, z1, li, col=None):
        """平面形（穴あり可）を z0〜z1 に。z1 は数か関数 f(x, y)"""
        if poly is None or poly.is_empty: return
        zf = z1 if callable(z1) else (lambda x, y: z1)
        for p in ([poly] if poly.geom_type == 'Polygon' else [g for g in getattr(poly, 'geoms', []) if g.geom_type == 'Polygon']):
            if p.area < 100: continue
            p = p.simplify(0.5)
            rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
            V2 = np.vstack(rings); n = len(V2)
            ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
            tri = earcut.triangulate_float64(V2, ends).reshape(-1, 3)
            zt = np.maximum(np.array([zf(x, y) for x, y in V2]), z0 + 5)
            mm = r.Mesh()
            for (x, y) in V2: mm.Vertices.Add(float(x), float(y), float(z0))
            for (x, y), z in zip(V2, zt): mm.Vertices.Add(float(x), float(y), float(z))
            for a, b, c in tri:
                mm.Faces.AddFace(int(a), int(c), int(b)); mm.Faces.AddFace(int(a + n), int(b + n), int(c + n))
            st = 0
            for e in ends:
                for i in range(st, e):
                    j = i + 1 if i + 1 < e else st
                    mm.Faces.AddFace(int(i), int(j), int(j + n), int(i + n))
                st = e
            s.add(mm, li, col)
    def flat(s, poly, z, li, col=None):
        for p in ([poly] if poly.geom_type == 'Polygon' else [g for g in getattr(poly, 'geoms', []) if g.geom_type == 'Polygon']):
            if p.area < 1e4: continue
            p = p.simplify(0.5)
            rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
            V2 = np.vstack(rings); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
            tri = earcut.triangulate_float64(V2, ends).reshape(-1, 3)
            mm = r.Mesh()
            for (x, y) in V2: mm.Vertices.Add(float(x), float(y), float(z))
            for a, b, c in tri: mm.Faces.AddFace(int(a), int(b), int(c))
            s.add(mm, li, col)
    def box8(s, P, li, col=None):
        """8 点の箱（下 4 点 → 上 4 点、同じ回り）"""
        mm = r.Mesh()
        for p in P: mm.Vertices.Add(*map(float, p))
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)): mm.Faces.AddFace(*f)
        s.add(mm, li, col)
    def tube(s, p0, p1, r0, r1, li, col=None, n=10, caps=True):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d); d /= L
        a = np.array([0, 0, 1.]) if abs(d[2]) < 0.9 else np.array([1., 0, 0])
        x = np.cross(d, a); x /= np.linalg.norm(x); y = np.cross(d, x)
        mm = r.Mesh()
        for c, rr in ((p0, r0), (p1, r1)):
            for k in range(n):
                t = 2 * math.pi * k / n; q = c + rr * (math.cos(t) * x + math.sin(t) * y); mm.Vertices.Add(*map(float, q))
        for k in range(n):
            j = (k + 1) % n; mm.Faces.AddFace(k, j, n + j, n + k)
        if caps:
            i0 = mm.Vertices.Add(*map(float, p0)); i1 = mm.Vertices.Add(*map(float, p1))
            for k in range(n):
                j = (k + 1) % n; mm.Faces.AddFace(k, i0, j); mm.Faces.AddFace(n + k, n + j, i1)
        s.add(mm, li, col)
    def surface(s, G, li, col=None):
        """格子状の点 G[i][j]（3D）→ 面"""
        G = np.asarray(G, float); ni, nj = G.shape[:2]; mm = r.Mesh()
        for i in range(ni):
            for j in range(nj): mm.Vertices.Add(*map(float, G[i, j]))
        for i in range(ni - 1):
            for j in range(nj - 1):
                a = i * nj + j; mm.Faces.AddFace(a, a + 1, a + nj + 1, a + nj)
        s.add(mm, li, col)
