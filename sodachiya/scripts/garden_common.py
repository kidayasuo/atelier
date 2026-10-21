"""園庭（だいさんかく・しずかのもり）の共通：枠 (a, d) と xy の変換、地形の高さ、3dm から読む敷地と建物。
garden01.py（図）と、木の配置の下書き garden_trees.py が使う。寸法は data/garden.json。"""
import json, math, os, sys
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
G = json.load(open(os.path.join(ROOT, "data", "garden.json"), encoding="utf-8"))
UE = np.array(G["UE"]); NB = np.array(G["NB"])

sys.path.insert(0, os.path.join(ROOT, "model", "build", "south"))
from uv import xy as _uvxy, uv as _xyuv   # 本館の (u, v) ⇄ 3dm の mm

SITE = Polygon([(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)])
PARK = Polygon([(-14.44, -83.04), (-21.91, -73.65), (-12.52, -66.18), (-5.05, -75.57)])


def X(a, d):
    """園庭の枠 (a, d) → 3dm の xy（m）"""
    p = a * UE - d * NB
    return (float(p[0]), float(p[1]))


def AD(x, y):
    p = np.array([x, y])
    return (float(p @ UE), float(-(p @ NB)))


def UV(u, v):
    """本館の (u, v) → xy（m）"""
    p = _uvxy(u, v) / 1000.0
    return (float(p[0]), float(p[1]))


def uv_of(x, y):
    return _xyuv(x * 1000.0, y * 1000.0)


def XS(pts):
    return [X(a, d) for a, d in pts]


# 本館の東の線（庇の先・外縁側の外、v = EDGE_V）を (a, d) で
_EDGE = [AD(*UV(u, G["EDGE_V"])) for u in np.linspace(-0.5, 57.5, 117)]
_EA = np.array([p[0] for p in _EDGE]); _ED = np.array([p[1] for p in _EDGE])


def d_edge(a):
    """枠の a での本館の東の線の d"""
    return float(np.interp(a, _EA[::-1], _ED[::-1]))


def garden_poly():
    """だいさんかく（しずかのもりを含む）の範囲：北東の辺・川沿いの辺・本館の東の線で囲む"""
    north = (float(_EA[-1]), 0.0)                       # 本館の北の端の東を北東の辺へ
    poly = [north, (56.0, 0.0), (56.0, float(_ED[0]))] + [(float(a), float(d)) for a, d in zip(_EA, _ED)][::1]
    # _EA は u の増加で a が減る：南（a 大）から北へ
    g = Polygon(XS(poly)).buffer(0)
    return g.intersection(SITE)


def stream_lines():
    s = G["STREAM"]
    return [s["line"]]


# ---------------- 地形 ----------------
def _cone(q):
    q = np.asarray(q, float)
    out = np.where(q < 0.25, 1 - (q ** 2 / 0.5 + 0.125), 1 - q)
    return np.clip(out, 0, None)


def mound_h(A, D):
    m = G["MOUND"]
    a0, d0 = m["top"]
    ra = np.where(A < a0, m["r_nw"], m["r_se"])
    rd = np.where(D < d0, m["r_ne"], m["r_sw"])
    q = np.hypot((A - a0) / ra, (D - d0) / rd)
    return m["h"] / 0.875 * _cone(q)


def bump_h(A, D, b):
    a0, d0 = b["c"]; rnw, rse, rne, rsw = b["r"]
    ra = np.where(A < a0, rnw, rse); rd = np.where(D < d0, rne, rsw)
    q = np.hypot((A - a0) / ra, (D - d0) / rd)
    return b["h"] * (0.5 + 0.5 * np.cos(np.pi * np.clip(q, 0, 1)))


def bank_h(A, D):
    bk = G["BANK"]; line = LineString(bk["line"])
    flat = np.zeros_like(A, dtype=float)
    it = np.nditer([A, D, flat], op_flags=[["readonly"], ["readonly"], ["writeonly"]])
    L = line.length
    gaps = bk["gaps"]
    for a, d, o in it:
        p = Point(float(a), float(d)); dist = line.distance(p)
        if dist >= bk["half_w"]:
            o[...] = 0; continue
        s = line.project(p)
        hh = bk["h"] * (0.5 + 0.5 * math.cos(math.pi * dist / bk["half_w"]))
        # 端はなだらかに
        e = min(s, L - s); hh *= min(1.0, e / 1.2)
        for (g_a, g_w) in gaps:
            sg = line.project(Point(g_a, float(np.interp(g_a, [q[0] for q in bk["line"]], [q[1] for q in bk["line"]]))))
            k = abs(s - sg) - g_w / 2
            if k < 1.0:
                hh *= max(0.0, k) / 1.0
        o[...] = hh
    return flat


def bowl_h(A, D):
    b = G["BOWL"]; q = np.hypot(A - b["c"][0], D - b["c"][1]) / b["r"]
    return b["h"] * (0.5 + 0.5 * np.cos(np.pi * np.clip(q, 0, 1)))


def height(A, D):
    A = np.asarray(A, float); D = np.asarray(D, float)
    h = mound_h(A, D)
    for b in G["BUMPS"]:
        h = np.maximum(h, bump_h(A, D, b))
    h = np.maximum(h, bank_h(A, D))
    return h + bowl_h(A, D)


# ---------------- 3dm から ----------------
def read_mesh_layers(names):
    import rhino3dm as r
    m = r.File3dm.Read(os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm"))
    out = {}
    for o in m.Objects:
        L = m.Layers[o.Attributes.LayerIndex].Name
        if L not in names:
            continue
        g = o.Geometry
        if not isinstance(g, r.Mesh):
            continue
        V = np.array([[g.Vertices[i].X, g.Vertices[i].Y] for i in range(len(g.Vertices))]) / 1000
        ps = []
        for i in range(len(g.Faces)):
            idx = list(dict.fromkeys(g.Faces[i]))
            if len(idx) < 3:
                continue
            p = Polygon(V[idx])
            if p.area > 1e-6:
                ps.append(p.buffer(1e-4))
        if ps:
            out.setdefault(L, []).append(unary_union(ps).buffer(-1e-4))
    return {k: unary_union(v) for k, v in out.items()}
