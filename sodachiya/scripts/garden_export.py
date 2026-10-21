"""園庭を 3dm に書き出す（取り込み用、レイヤー 90〜97）。座標は sodachiya_exact.3dm と同じ mm、z=0 が FL±0（GL は −300）。
木造のチャットが本体に Import する。模型のチャットは等高線（91）と水（92）からレーザーのデータを作れる。

  python3 sodachiya/scripts/garden_export.py   → model/sodachiya_garden_layers.3dm
"""
import math, os
import numpy as np
import rhino3dm as r
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, LineString
import garden_common as gc

G = gc.G
GL = -300.0
m = r.File3dm()
m.Settings.ModelUnitSystem = r.UnitSystem.Millimeters
LAY = {}
NAMES = {90: ("90_園庭_地形（GL からの起伏、メッシュ）", (196, 186, 150)), 91: ("91_園庭_等高線（0.2 m、名前に高さ）", (138, 122, 92)),
         92: ("92_園庭_水（小川・雨の川・床の噴水・水浴び場・護岸の溝）", (76, 141, 184)), 93: ("93_園庭_小屋（便所・倉庫・コンポストの間）", (155, 118, 83)),
         94: ("94_園庭_木（幹・樹冠、名前＝種類）", (111, 143, 87)), 95: ("95_園庭_遊び場（砂場・粒・すりばち・柳の家）", (168, 142, 88)),
         96: ("96_園庭_石（関守石・橋・飛び石・バルブます）", (110, 104, 92)), 97: ("97_園庭_車の道・生垣", (183, 169, 140)),
         98: ("98_園庭_等高線の板（閉じた形：+は高さ L 以上、−は L 以下のくぼみ）", (200, 120, 60))}
for k, (n, c) in NAMES.items():
    l = r.Layer(); l.Name = n; l.Color = (*c, 255); LAY[k] = m.Layers.Add(l)


def at(k, name=None):
    a = r.ObjectAttributes(); a.LayerIndex = LAY[k]
    if name: a.Name = name
    return a


def H(a, d):
    return float(gc.height(np.array([a]), np.array([d]))[0])


def P3(a, d, z=None):
    x, y = gc.X(a, d)
    return r.Point3d(x * 1000, y * 1000, (H(a, d) if z is None else z) * 1000 + GL)


def curve_ad(pts, k, name=None, close=False, z=None, drape=True):
    pts = list(pts)
    if close:
        pts = pts + [pts[0]]
    if drape and z is None:
        dense = []
        for (a0, d0), (a1, d1) in zip(pts[:-1], pts[1:]):
            n = max(1, int(math.hypot(a1 - a0, d1 - d0) / 0.5))
            dense += [(a0 + (a1 - a0) * t / n, d0 + (d1 - d0) * t / n) for t in range(n)]
        dense.append(pts[-1]); pts = dense
    pl = r.Polyline([P3(a, d, z) for a, d in pts])
    m.Objects.AddPolyline(pl, at(k, name))


def ell(c, rr, rot=0, n=48):
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [(c[0] + rr[0] * math.cos(q) * ca - rr[1] * math.sin(q) * sa, c[1] + rr[0] * math.cos(q) * sa + rr[1] * math.sin(q) * ca)
            for q in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def box(a0, a1, d0, d1, z0, z1, k, name):
    """(a, d) の長方形を z0〜z1 の箱に（m）"""
    crv = r.Polyline([r.Point3d(*(np.array(gc.X(a, d)) * 1000), z0 * 1000 + GL) for a, d in ((a0, d0), (a1, d0), (a1, d1), (a0, d1), (a0, d0))]).ToNurbsCurve()
    ex = r.Extrusion.Create(crv, (z1 - z0) * 1000, True)
    if ex is not None:
        bb = ex.GetBoundingBox()
        if bb.Min.Z < z0 * 1000 + GL - 1:                 # 曲線の向きで下へ伸びたら上下を直す
            ex = r.Extrusion.Create(crv, -(z1 - z0) * 1000, True)
        m.Objects.AddExtrusion(ex, at(k, name))


# ---- 90 地形（0.5 m の格子、園庭の中だけ） ----
gpoly = Polygon([gc.AD(*p) for p in gc.garden_poly().exterior.coords])
S = 0.5
A = np.arange(12.0, 56.01, S); D = np.arange(0.0, 36.01, S)
mesh = r.Mesh(); idx = {}
for i, a in enumerate(A):
    for j, d in enumerate(D):
        if gpoly.buffer(0.6).contains(Point(a, d)):
            p = P3(a, d); idx[(i, j)] = mesh.Vertices.Add(p.X, p.Y, p.Z)
for (i, j), v in idx.items():
    q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
    if all(k in idx for k in q):
        mesh.Faces.AddFace(*[idx[k] for k in q])
mesh.Normals.ComputeNormals(); mesh.Compact()
m.Objects.AddMesh(mesh, at(90, "園庭の地形（GL からの起伏）"))

# ---- 91 等高線 ----
STEP = 0.1
GA = np.arange(10.0, 57.01, STEP); GD = np.arange(-1.0, 37.01, STEP)
AA, DD = np.meshgrid(GA, GD); HH = gc.height(AA, DD)
levels = [round(v, 1) for v in np.arange(-0.4, 2.21, 0.2) if abs(v) > 1e-6]
cs = plt.contour(AA, DD, HH, levels=levels)
nc = 0
for lev, segs in zip(cs.levels, cs.allsegs):
    for seg in segs:
        if len(seg) < 4:
            continue
        ln = LineString(seg).intersection(gpoly)
        parts = [ln] if ln.geom_type == "LineString" else list(getattr(ln, "geoms", []))
        for pp in parts:
            if pp.length < 0.8:
                continue
            curve_ad(list(pp.coords), 91, f"{lev:+.1f} m", z=float(lev), drape=False); nc += 1

# ---- 98 等高線の板（閉じた形） ----
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
from shapely import affinity as _aff


def _polys(cs):
    """contourf の 1 段ぶんを shapely に（穴は偶奇で）"""
    out = []
    for segs in cs.allsegs:
        ring = Polygon()
        for seg in segs:
            if len(seg) < 4:
                continue
            pg = Polygon(seg).buffer(0)
            ring = ring.symmetric_difference(pg)
        out.append(ring)
    return out


PLATES = []
for lev in [l for l in levels if l > 0]:
    cf = plt.contourf(AA, DD, HH, levels=[lev, 99.0]); plt.close("all")
    g = unary_union(_polys(cf)).buffer(0.05).buffer(-0.05).intersection(gpoly).simplify(0.03)
    PLATES.append((lev, g))
for lev in [l for l in levels if l < 0]:
    cf = plt.contourf(AA, DD, HH, levels=[-99.0, lev]); plt.close("all")
    g = unary_union(_polys(cf)).intersection(gpoly).simplify(0.03)
    PLATES.append((lev, g))
npl = 0
for lev, g in PLATES:
    for pg in (g.geoms if hasattr(g, "geoms") else [g]):
        if pg.is_empty or pg.area < 0.05:
            continue
        curve_ad(list(pg.exterior.coords)[:-1], 98, f"{lev:+.1f} m の板（外形）", close=True, z=float(lev), drape=False); npl += 1
        for hole in pg.interiors:
            curve_ad(list(hole.coords)[:-1], 98, f"{lev:+.1f} m の板（穴）", close=True, z=float(lev), drape=False)
curve_ad(list(gpoly.exterior.coords)[:-1], 98, "園庭の外形（GL ±0 の板）", close=True, z=0.0, drape=False)
import json as _js
_js.dump({f"{lev:+.1f}": round(g.area, 1) for lev, g in PLATES}, open(os.path.join(gc.ROOT, "out", "garden_plates.json"), "w"), ensure_ascii=False)

# ---- 92 水 ----
s = G["STREAM"]; L = LineString(s["line"])
z0, z1 = s["bed"] if "bed" in s else (0.2, -0.4)
pts = [(L.interpolate(t, normalized=True).x, L.interpolate(t, normalized=True).y) for t in np.linspace(0, 1, 120)]
pl = r.Polyline([P3(a, d, z0 + (z1 - z0) * k / 119) for k, (a, d) in enumerate(pts)])
m.Objects.AddPolyline(pl, at(92, "小川の川床（中心線、幅 0.5）"))
for side in (-0.25, 0.25):
    off = L.parallel_offset(abs(side), "left" if side < 0 else "right")
    curve_ad(list(off.coords), 92, "小川の岸")
curve_ad(s["culvert"], 92, "暗渠（用水路 → みなもと）", z=-0.6, drape=False)
am = G["AMAOCHI"]
edge = [(gc.AD(*gc.UV(u, G["EDGE_V"]))) for u in np.linspace(am["u"][0], am["u"][1], 60)]
curve_ad(edge, 92, "雨の川（雨落ちの溝の中心、幅 0.5・深さ 0.2）")
curve_ad(am["outlet"], 92, "雨の川 → 護岸の溝")
F = G["FOUNTAIN"]; curve_ad(ell(F["c"], F["r"], F["rot"]), 92, "床の噴水（石張り、噴き口 0.8 m ごと）", close=True)
SP = G["SPLASH"]; curve_ad(ell(SP["c"], SP["r"], 0), 92, "水浴び場（円形 φ4.0、段なしの浅い皿）", close=True)
for dd, nm in ((15.3, "護岸の溝（小川、幅 0.3）"), (35.0, "護岸の溝（雨の川、幅 0.3）")):
    pa, pb = P3(56.0, dd - 0.15, 0.0), P3(56.0, dd + 0.15, 0.0)
    for zz in (0.0, -4.0):
        m.Objects.AddLine(r.Point3d(pa.X, pa.Y, zz * 1000 + GL), r.Point3d(pb.X, pb.Y, zz * 1000 + GL), at(92, nm))

# ---- 93 小屋 ----
Hh = G["HUT"]; a0, a1 = Hh["a"]; d0, d1 = Hh["d"]; ac = Hh["closed_a"]; sa_ = Hh["split_a"]
g0 = max(H(a, d) for a in (a0, a1) for d in (d0, d1))
box(a0, sa_, d0, d1, g0, g0 + 2.4, 93, "便所（座る便器×2・手洗い）")
box(sa_, ac, d0, d1, g0, g0 + 2.4, 93, "倉庫")
box(a0 - 0.3, a1 + 0.3, d0 - 0.3, d1 + Hh["eave"], g0 + 2.4, g0 + 2.55, 93, "小屋の屋根（ひとつの屋根、南西に軒 1.5）")
for q in ((a1 - 0.1, d0), (a1 - 0.1, d1 - 0.1), (a1 - 0.1, d1 + Hh["eave"] - 0.15), (ac, d1 + Hh["eave"] - 0.15), (a0, d1 + Hh["eave"] - 0.15)):
    box(q[0], q[0] + 0.12, q[1], q[1] + 0.12, g0, g0 + 2.4, 93, "柱 120 角")
CP = G["COMPOST"]
for i in range(CP["n"]):
    q0 = CP["a0"] + i * CP["w"]
    box(q0 + 0.05, q0 + CP["w"] - 0.05, CP["d0"], CP["d0"] + CP["depth"], g0, g0 + 0.7, 93, "コンポストの枠：" + CP["labels"][i])

# ---- 94 木 ----
TH = {"big": (7.5, 3.0), "climb": (7.0, 3.2), "mid": (5.0, 2.1), "fruit": (4.0, 2.3), "ever": (4.5, 1.9)}
for a, d, kind, _, note in G["TREES"]:
    sp = note.split("（")[0]; ht, rc = TH[kind]
    base = P3(a, d); top = r.Point3d(base.X, base.Y, base.Z + (ht - rc) * 1000)
    m.Objects.AddLine(base, top, at(94, sp + "（幹）"))
    sph = r.Sphere(r.Point3d(base.X, base.Y, base.Z + (ht - rc * 0.9) * 1000), rc * 0.9 * 1000)
    m.Objects.AddBrep(sph.ToBrep(), at(94, note))

# ---- 95 遊び場 ----
curve_ad(G["SAND"]["poly"], 95, "砂場", close=True)
GR = G["GRAIN"]; ca, sa = math.cos(math.radians(GR["rot"])), math.sin(math.radians(GR["rot"]))
gr = lambda u, v: (GR["c"][0] + u * ca - v * sa, GR["c"][1] + u * sa + v * ca)
hl, hw = GR["l"] / 2, GR["w"] / 2
curve_ad([gr(-hl, -hw), gr(hl, -hw), gr(hl, hw), gr(-hl, hw)], 95, "粒の遊び場 2.7×3.6（木の縁、帆布の巻き取り）", close=True)
curve_ad([gr(-hl, hw + 0.35), gr(hl, hw + 0.35)], 95, "帆布を巻いた棒")
B = G["BOWL"]; curve_ad(ell(B["c"], (B["r"], B["r"])), 95, "すりばち（お話の輪、大雨の日は雨の池）", close=True)
W = G["WILLOW"]; curve_ad(ell(W["c"], (W["r"], W["r"])), 95, "柳の家（生きたヤナギのドーム φ3）", close=True)

# ---- 96 石 ----
for q in G["SEKIMORI"]["pts"]:
    p = P3(*q); sph = r.Sphere(r.Point3d(p.X, p.Y, p.Z + 120), 150)
    m.Objects.AddBrep(sph.ToBrep(), at(96, "関守石（しずかのもりの境）"))
for b in G["BRIDGES"]:
    c = b["c"]; nm = b["_"]
    if b["w"] > 0:
        w2 = b["w"] / 2
        curve_ad(ell(c, (w2, 0.6 if b["w"] > 2 else 0.25), 0, 4), 96, nm, close=True)
    else:
        curve_ad(ell(c, (0.3, 0.3)), 96, nm, close=True)
vb = F["valve"]["c"]; box(vb[0] - 0.45, vb[0] + 0.45, vb[1] - 0.3, vb[1] + 0.3, H(*vb) - 0.6, H(*vb), 96, "バルブます（電磁弁 4 系統・逆流防止・子メーター）")

# ---- 97 車の道・生垣 ----
curve_ad(G["VEHICLE"]["line"], 97, "剪定・搬入の車の道（芝の保護材 幅 2.5）")
lk = G["LOOKOUT"]; (h0a, h0d), (h1a, h1d) = lk["hedge"]
curve_ad([(56.0 - 0.15 - lk["hedge_w"], h0d), (56.0 - 0.15 - lk["hedge_w"], h1d)], 97, "のぞきの低い生垣 h0.6（口 3 か所）")

out = os.path.join(gc.ROOT, "model", "sodachiya_garden_layers.3dm")
m.Write(out, 7)
print("wrote", out, "contours", nc, "plates", npl, "trees", len(G["TREES"]))
