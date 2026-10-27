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
         92: ("92_園庭_水（小川・雨の川・床の噴水・乳児の床の噴水・雨庭・護岸の溝）", (76, 141, 184)), 93: ("93_園庭_小屋（便所・倉庫・コンポストの間）", (155, 118, 83)),
         94: ("94_園庭_木の幹（名前＝種類）", (111, 100, 80)), "94c": ("94c_園庭_樹冠（葉、名前＝種類）", (111, 143, 87)), 95: ("95_園庭_遊び場（砂場・粒・すりばち・柳の家）", (168, 142, 88)),
         "95w": ("95w_園庭_鉄棒の柱（栗の丸太）", (140, 110, 80)), "95m": ("95m_園庭_鉄棒の棒（ステンレス）", (150, 155, 162)),
         96: ("96_園庭_石（橋・飛び石・バルブます）", (110, 104, 92)), 97: ("97_園庭_車の道・木戸", (183, 169, 140)), "97h": ("97h_園庭_生垣（葉、のぞきの低い生垣 h0.6）", (120, 150, 90)),
         98: ("98_園庭_等高線の板（閉じた形：+は高さ L 以上、−は L 以下のくぼみ）", (200, 120, 60)),
         99: ("99_園庭_雨の川（玉石の溝、本館の雨落ち）", (140, 134, 119))}
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
levels = [round(v, 1) for v in np.arange(-0.4, float(HH.max()) + 0.01, 0.2) if abs(v) > 1e-6]
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
def trough(cl, half, k, name, water=None, top=None):
    """中心線 cl=[(a, d, 底のz)] に沿う U 字の溝（岸は地面、底は z）。water があれば底+water に水面の帯"""
    mesh = r.Mesh(); wm = r.Mesh() if water else None
    for i, (a, d, zb) in enumerate(cl):
        j = min(i + 1, len(cl) - 1); h = max(i - 1, 0)
        ta, td = cl[j][0] - cl[h][0], cl[j][1] - cl[h][1]; ln = math.hypot(ta, td) or 1
        na, nd = -td / ln, ta / ln
        for (sa, zz) in ((-half - 0.05, None), (-half, zb), (half, zb), (half + 0.05, None)):
            q = P3(a + na * sa, d + nd * sa, zz if zz is not None else (top if top is not None else None))
            mesh.Vertices.Add(q.X, q.Y, q.Z)
        if wm:
            for sa in (-half, half):
                q = P3(a + na * sa, d + nd * sa, zb + water); wm.Vertices.Add(q.X, q.Y, q.Z)
    for i in range(len(cl) - 1):
        for c in range(3):
            mesh.Faces.AddFace(4 * i + c, 4 * i + c + 1, 4 * (i + 1) + c + 1, 4 * (i + 1) + c)
        if wm:
            wm.Faces.AddFace(2 * i, 2 * i + 1, 2 * (i + 1) + 1, 2 * (i + 1))
    mesh.Normals.ComputeNormals(); m.Objects.AddMesh(mesh, at(k, name))
    if wm:
        wm.Normals.ComputeNormals(); m.Objects.AddMesh(wm, at(92, name + "の水面"))


s = G["STREAM"]
bed = gc.stream_bed(240)
trough(bed, 0.25, 92, "小川（幅 0.5、底は平ら、岸は急）", water=0.04)
m.Objects.AddPolyline(r.Polyline([P3(a, d, z) for a, d, z in bed]), at(92, "小川の川床（中心線）"))
FL = s.get("fall")
if FL:
    (la, ld, lz) = FL["lip"]; pc = FL["pool"]
    pa, pd = pc["c"]
    for k_, (fa, fd, fz) in enumerate([(la, ld, lz), (la + (pa - la) * 0.45, ld + (pd - ld) * 0.45, lz - 0.25)]):
        box(fa - 0.35, fa + 0.35, fd - 0.2, fd + 0.2, fz - 0.15, fz, 92, f"滝の落ち口の平たい石 {k_ + 1}（落差 約 0.45）")
    disk = r.Mesh(); cpt = P3(pa, pd, pc["bed"] + 0.12); disk.Vertices.Add(cpt.X, cpt.Y, cpt.Z)
    for q in np.linspace(0, 2 * math.pi, 33):
        v = P3(pa + pc["r"] * math.cos(q), pd + pc["r"] * math.sin(q), pc["bed"] + 0.12); disk.Vertices.Add(v.X, v.Y, v.Z)
    for i in range(1, 33):
        disk.Faces.AddFace(0, i, i + 1)
    disk.Normals.ComputeNormals(); m.Objects.AddMesh(disk, at(92, "滝壺の水面（φ1.0、深さ 0.15）"))
    curve_ad(ell((pa, pd), (pc["r"], pc["r"])), 92, "滝壺", close=True)
curve_ad(s["culvert"], 92, "暗渠（用水路 → みなもと）", z=-0.6, drape=False)
am = G["AMAOCHI"]
cl = []
for u in np.linspace(am["u"][1], am["u"][0], 140):        # 北の端から南へ（流れの向き）。南の端の落とし口へつなぐ（前は北の端から落とし口へ54 mの帯が渡っていた、10-27）
    a, d = gc.AD(*gc.UV(u, G["EDGE_V"])); cl.append((a, d, H(a, d) - am["depth"]))
for (a0_, d0_), (a1_, d1_) in zip(am["outlet"][:-1], am["outlet"][1:]):
    for t in np.linspace(0, 1, 8)[1:]:
        a, d = a0_ + (a1_ - a0_) * t, d0_ + (d1_ - d0_) * t; cl.append((a, d, H(a, d) - am["depth"]))
trough(cl, am["w"] / 2, 99, "雨の川（雨落ちの溝、玉石、幅 0.5・深さ 0.2）")
# 玉石の面（溝の底から 0.12 上まで玉石を敷く）
pebble = r.Mesh()
for i, (a, d, zb) in enumerate(cl):
    j = min(i + 1, len(cl) - 1); h = max(i - 1, 0)
    ta, td = cl[j][0] - cl[h][0], cl[j][1] - cl[h][1]; ln = math.hypot(ta, td) or 1
    na, nd = -td / ln, ta / ln
    for sa in (-am["w"] / 2, am["w"] / 2):
        q = P3(a + na * sa, d + nd * sa, zb + 0.12); pebble.Vertices.Add(q.X, q.Y, q.Z)
for i in range(len(cl) - 1):
    pebble.Faces.AddFace(2 * i, 2 * i + 1, 2 * (i + 1) + 1, 2 * (i + 1))
pebble.Normals.ComputeNormals(); m.Objects.AddMesh(pebble, at(99, "雨の川の玉石（φ50〜100）"))
F = G["FOUNTAIN"]; curve_ad(ell(F["c"], F["r"], F["rot"]), 92, "床の噴水（石張り、噴き口 0.8 m ごと）", close=True)
SP = G["SPLASH"]; curve_ad(ell(SP["c"], SP["r"], 0), 92, "乳児の床の噴水（φ4.0、石張り、低い泡の噴き口）", close=True)
if SP.get("mist"):
    _ms = SP["mist"]; zm = H(*SP["c"]) + _ms["h"]
    curve_ad(ell(SP["c"], (_ms["r"], _ms["r"]), n=48), 92, "霧のわ（φ1.8、h2.0）", close=True, z=zm, drape=False)
    for q in _ms["posts"]:
        g_ = H(*q); box(q[0] - 0.05, q[0] + 0.05, q[1] - 0.05, q[1] + 0.05, g_, zm + 0.1, 92, "霧のわの柱 100 角")
for dd, nm in ((15.3, "護岸の溝（小川、幅 0.3）"), (35.0, "護岸の溝（雨の川、幅 0.3）")):
    pa, pb = P3(56.0, dd - 0.15, 0.0), P3(56.0, dd + 0.15, 0.0)
    for zz in (0.0, -4.0):
        m.Objects.AddLine(r.Point3d(pa.X, pa.Y, zz * 1000 + GL), r.Point3d(pb.X, pb.Y, zz * 1000 + GL), at(92, nm))

# ---- 93 小屋 ----
Hh = G["HUT"]; a0, a1 = Hh["a"]; d0, d1 = Hh["d"]; ac = Hh["closed_a"]; sa_ = Hh["split_a"]
g0 = max(H(a, d) for a in (a0, a1) for d in (d0, d1))
# 10-25（ユーザー）：屋根は本館と同じ東下がりの片流れ、勾配 1/10。枠の d− が北東（東寄り）なので、
# 北東の軒（隣家側、d0−0.3）が低く 2.4、南西の深い軒の先（d1＋1.5）が高い。雨は北東へ落ちて雨水タンクへ。
R_LO, R_PITCH, R_T = 2.4, 0.1, 0.15
rd0, rd1 = d0 - 0.3, d1 + Hh["eave"]
def zr(d):                                             # 屋根の下面の高さ（GL からの m）
    return g0 + R_LO + (d - rd0) * R_PITCH
def prism(a0_, a1_, d0_, d1_, zb, zt0, zt1, k, name, t=None):
    """(a, d) の長方形の箱。上面は d0_ で zt0、d1_ で zt1 の斜め（t を与えると厚さ t の斜めの板）"""
    ms = r.Mesh()
    bot = (lambda dd, zt: zt - t) if t else (lambda dd, zt: zb)
    corners = ((a0_, d0_, zt0), (a1_, d0_, zt0), (a1_, d1_, zt1), (a0_, d1_, zt1))
    for a_, d_, zt in corners:
        q = P3(a_, d_, bot(d_, zt)); ms.Vertices.Add(q.X, q.Y, q.Z)
    for a_, d_, zt in corners:
        q = P3(a_, d_, zt); ms.Vertices.Add(q.X, q.Y, q.Z)
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        ms.Faces.AddFace(*f)
    ms.Normals.ComputeNormals(); m.Objects.AddMesh(ms, at(k, name))
prism(a0, sa_, d0, d1, g0, zr(d0), zr(d1), 93, "便所（座る便器×2・手洗い）")
prism(sa_, ac, d0, d1, g0, zr(d0), zr(d1), 93, "倉庫")
prism(a0 - 0.3, a1 + 0.3, rd0, rd1, 0, zr(rd0) + R_T, zr(rd1) + R_T, 93,
      "小屋の屋根（ひとつの屋根、東下がりの片流れ 1/10、本館と同じ、南西に軒 1.5）", t=R_T)
for q in ((a1 - 0.1, d0), (a1 - 0.1, d1 - 0.1), (a1 - 0.1, rd1 - 0.15), (ac, rd1 - 0.15), (a0, rd1 - 0.15)):
    box(q[0], q[0] + 0.12, q[1], q[1] + 0.12, g0, zr(q[1] + 0.12), 93, "柱 120 角")
CP = G["COMPOST"]
for i in range(CP["n"]):
    q0 = CP["a0"] + i * CP["w"]
    box(q0 + 0.05, q0 + CP["w"] - 0.05, CP["d0"], CP["d0"] + CP["depth"], g0, g0 + 0.7, 93, "コンポストの枠：" + CP["labels"][i])

# ---- 雨庭（洲浜）（92・96） ----
AW = G.get("AMANIWA")
if AW:
    curve_ad(AW["poly"], 92, "雨庭（洲浜、玉石の浜の浅いくぼみ −0.25、溢れたら護岸の溝へ）", close=True)
    for sa_, sd_, sr_ in AW["stones"]:
        c0 = P3(sa_, sd_); sph = r.Sphere(r.Point3d(c0.X, c0.Y, c0.Z + sr_ * 300), sr_ * 1000)
        m.Objects.AddBrep(sph.ToBrep(), at(96, "雨庭の景石"))

# ---- シャワーの柱と輪のシャワー「あめのわ」（95） ----
SH = G["SHOWER"]; _rg = SH.get("ring")
if _rg:
    g_ = H(*SH["c"])
    for q in _rg.get("posts", [SH["c"]]):
        gq = H(*q); box(q[0] - 0.06, q[0] + 0.06, q[1] - 0.06, q[1] + 0.06, gq, gq + _rg["h"] + 0.15, 95, "あめのわの柱 120 角")
    gr_ = H(*_rg["c"]) + _rg["h"]
    curve_ad(ell(_rg["c"], (_rg["r"], _rg["r"]), n=64), 95, "あめのわ（輪のシャワー φ2.4、噴き口48）", close=True, z=gr_, drape=False)
    vx, vy = _rg["c"][0] - SH["c"][0], _rg["c"][1] - SH["c"][1]; L_ = math.hypot(vx, vy)
    pe = (_rg["c"][0] - vx / L_ * _rg["r"], _rg["c"][1] - vy / L_ * _rg["r"])
    m.Objects.AddLine(P3(SH["c"][0], SH["c"][1], gr_), P3(pe[0], pe[1], gr_), at(95, "あめのわの腕"))

# ---- 年中行事の草（95） ----
for a_, d_, r_, nm_, n_ in G.get("GYOJI", {}).get("items", []):
    curve_ad(ell((a_, d_), (r_, r_)), 95, f"{nm_}（{n_}）", close=True)

# ---- 94 木 ----
TH = {"big": (7.5, 3.0), "climb": (7.0, 3.2), "mid": (5.0, 2.1), "fruit": (4.0, 2.3), "ever": (4.5, 1.9)}
for a, d, kind, _, note in G["TREES"]:
    sp = note.split("（")[0]; ht, rc = TH[kind]
    base = P3(a, d); top = r.Point3d(base.X, base.Y, base.Z + (ht - rc) * 1000)
    m.Objects.AddLine(base, top, at(94, sp + "（幹）"))
    sph = r.Sphere(r.Point3d(base.X, base.Y, base.Z + (ht - rc * 0.9) * 1000), rc * 0.9 * 1000)
    m.Objects.AddBrep(sph.ToBrep(), at("94c", note))

# ---- 95 遊び場 ----
curve_ad(G["SAND"]["poly"], 95, "砂場", close=True)
GR = G["GRAIN"]; ca, sa = math.cos(math.radians(GR["rot"])), math.sin(math.radians(GR["rot"]))
gr = lambda u, v: (GR["c"][0] + u * ca - v * sa, GR["c"][1] + u * sa + v * ca)
hl, hw = GR["l"] / 2, GR["w"] / 2
curve_ad([gr(-hl, -hw), gr(hl, -hw), gr(hl, hw), gr(-hl, hw)], 95, "粒の遊び場 2.4×3.0（木の縁、帆布の巻き取り）", close=True)
curve_ad([gr(-hl, hw + 0.35), gr(hl, hw + 0.35)], 95, "帆布を巻いた棒")
B = G["BOWL"]; curve_ad(ell(B["c"], (B["r"], B["r"])), 95, "すりばち（お話の輪、大雨の日は雨の池）", close=True)
W = G["WILLOW"]; curve_ad(ell(W["c"], (W["r"], W["r"])), 95, "柳の家（生きたヤナギのドーム φ3）", close=True)

# ---- 95w・95m 鉄棒ひと組（10-27 ユーザー）：柱＝栗の丸太（閉じた円柱）、棒＝ステンレス φ25（閉じた円柱） ----
BR = G.get("BAR")
if BR:
    cb, sb = math.cos(math.radians(BR["rot"])), math.sin(math.radians(BR["rot"]))
    br = lambda u, v: (BR["c"][0] + u * cb - v * sb, BR["c"][1] + u * sb + v * cb)
    z0 = H(*BR["c"])                                   # その場で平らにならす
    n_ = len(BR["bars"]); u0 = -BR["span"] * n_ / 2
    def circ(p, n, rad):
        c = r.Circle(p, rad); c.Plane = r.Plane(p, n); return c
    def post(u, h):
        p = P3(*br(u, 0), z=z0)
        cyl = r.Cylinder(circ(p, r.Vector3d(0, 0, 1), BR["post_d"] / 2 * 1000), h * 1000)
        m.Objects.AddBrep(cyl.ToBrep(True, True), at("95w", f"鉄棒の柱（栗の丸太 φ{BR['post_d'] * 1000:.0f}、h{h:.2f}）"))
    for i in range(n_ + 1):
        hs = [BR["bars"][j] for j in (i - 1, i) if 0 <= j < n_]
        post(u0 + i * BR["span"], max(hs) + BR["post_over"])
    for j, hb in enumerate(BR["bars"]):
        p0 = P3(*br(u0 + j * BR["span"], 0), z=z0 + hb); p1 = P3(*br(u0 + (j + 1) * BR["span"], 0), z=z0 + hb)
        ax_ = r.Vector3d(p1.X - p0.X, p1.Y - p0.Y, p1.Z - p0.Z)
        cyl = r.Cylinder(circ(p0, ax_, BR["bar_d"] / 2 * 1000), ax_.Length())
        m.Objects.AddBrep(cyl.ToBrep(True, True), at("95m", f"鉄棒の棒（ステンレス φ{BR['bar_d'] * 1000:.0f}、h{hb:.2f}）"))

# ---- 96 石 ----
for q in G["SEKIMORI"].get("steps", []):
    curve_ad(ell(q, (0.26, 0.26)), 96, "飛び石（縁側の前の道）", close=True)
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
GN = G.get("GATE_N")
if GN:
    (ga0, gd0), (ga1, gd1) = GN["p0"], GN["p1"]
    gz = H(ga0, (gd0 + gd1) / 2)
    box(ga0 - 0.02, ga0 + 0.02, min(gd0, gd1), max(gd0, gd1), gz, gz + GN["h"], 97, "北の口の木戸 h1.2（庭の側へ開く、掛け金は外側の高い所）")

curve_ad(G["VEHICLE"]["line"], 97, "剪定・搬入の車の道（芝の保護材 幅 2.5）")
lk = G["LOOKOUT"]; (h0a, h0d), (h1a, h1d) = lk["hedge"]
curve_ad([(56.0 - 0.15 - lk["hedge_w"], h0d), (56.0 - 0.15 - lk["hedge_w"], h1d)], "97h", "のぞきの低い生垣 h0.6（口 3 か所）")

out = os.path.join(gc.ROOT, "model", "sodachiya_garden_layers.3dm")
m.Write(out, 7)
print("wrote", out, "contours", nc, "plates", npl, "trees", len(G["TREES"]))
