"""園庭を 3dm に書き出す（取り込み用、レイヤー90〜99）。座標は sodachiya_exact.3dm と同じ mm、z=0 が FL±0（GL は −300）。
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
# 10-30（ユーザー）：線として意味のある線（中心線・輪郭・道すじ・腕の線）は 90l に集める（開いたときは消す）。
# ほかの物はみな閉じた立体（91 等高線・98 等高線の板は線のまま、90 地形・92 水・99 雨の川はメッシュのまま）
NAMES = {90: ("90_園庭_地形（GL からの起伏、メッシュ）", (196, 186, 150)), 91: ("91_園庭_等高線（0.2 m、名前に高さ）", (138, 122, 92)),
         "90l": ("90l_園庭_線（中心線・輪郭・道すじ。開いたときは消す）", (120, 120, 120)),
         92: ("92_園庭_水（小川の溝と水面・滝壺の水面）", (76, 141, 184)), "92s": ("92s_園庭_雨庭の玉石（洲浜、白）", (222, 218, 206)), 93: ("93_園庭_小屋（便所・倉庫・コンポストの間）", (155, 118, 83)),
         94: ("94_園庭_木の幹（円柱、名前＝種類）", (111, 100, 80)), "94c": ("94c_園庭_樹冠（葉、名前＝種類、柳の家）", (111, 143, 87)), "94g": ("94g_園庭_草（年中行事の草・てんぐのたにのシャガ・川沿いの柵ぎわの草、h0.3の塊、葉）", (150, 175, 100)),
         "94b": ("94b_園庭_低木（葉、ヤマブキの株、扁平な半球）", (170, 160, 80)),
         95: ("95_園庭_遊び場（砂場の砂・粒の遊び場の粒）", (168, 142, 88)),
         "95w": ("95w_園庭_鉄棒の柱（栗の丸太）", (140, 110, 80)), "95m": ("95m_園庭_鉄棒の棒（ステンレス）", (150, 155, 162)),
         "95r": ("95r_園庭_木の縁と丸太（砂場・粒の遊び場の縁、帆布を巻いた棒、丸太の橋）", (150, 115, 80)),
         "95s": ("95s_園庭_輪のシャワー（あめのわ・霧のわの輪と腕、ステンレス）", (160, 165, 172)),
         "95p": ("95p_園庭_シャワーの柱（あめのわ・霧のわ、木 120角・100角）", (165, 130, 90)),
         96: ("96_園庭_石（床の噴水・乳児の床の噴水の石張り・橋・飛び石・滝の石・景石・バルブます）", (110, 104, 92)), 97: ("97_園庭_木戸", (183, 169, 140)),
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


# ---- 閉じた立体の道具（10-30） ----
def _crv_xy(pts_ad, z):
    """(a, d) の閉じた多角形 → z（m）の高さの、xy で左回りの閉じた曲線"""
    pg = Polygon([gc.X(a, d) for a, d in pts_ad]).buffer(0)
    from shapely.geometry.polygon import orient
    pg = orient(pg, 1.0)
    return r.Polyline([r.Point3d(x * 1000, y * 1000, z * 1000 + GL) for x, y in pg.exterior.coords]).ToNurbsCurve()


def slab(pts_ad, z0, z1, k, name, hole_ad=None):
    """(a, d) の閉じた形を z0〜z1（GL からの m）の押し出しに。hole_ad で穴（縁の輪）"""
    ex = r.Extrusion.Create(_crv_xy(pts_ad, z0), (z1 - z0) * 1000, True)
    if hole_ad is not None:
        ex.AddInnerProfile(_crv_xy(hole_ad, z0))
    m.Objects.AddExtrusion(ex, at(k, name))


def gmin(pts_ad):
    return min(H(a, d) for a, d in pts_ad)


def gmax(pts_ad):
    return max(H(a, d) for a, d in pts_ad)


def ring_pts(c, rad, n=48):
    return [(c[0] + rad * math.cos(q), c[1] + rad * math.sin(q)) for q in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def _cyl(p0, axis, rad, k, name):
    """p0（Point3d）から axis（Vector3d、長さ＝高さ）の向きの閉じた円柱、rad は mm"""
    c = r.Circle(p0, rad); c.Plane = r.Plane(p0, axis)
    m.Objects.AddBrep(r.Cylinder(c, axis.Length()).ToBrep(True, True), at(k, name))


def vcyl(c_ad, rad, z0, z1, k, name):
    """(a, d) を中心に、z0〜z1（GL からの m）の縦の円柱（rad は m）"""
    x, y = gc.X(*c_ad)
    _cyl(r.Point3d(x * 1000, y * 1000, z0 * 1000 + GL), r.Vector3d(0, 0, (z1 - z0) * 1000), rad * 1000, k, name)


def torus(c_ad, z, R, rr, k, name):
    """水平の輪（管）。z は GL からの m、R・rr は m"""
    x, y = gc.X(*c_ad); cp = r.Point3d(x * 1000, y * 1000, z * 1000 + GL)
    sc = r.Point3d(cp.X + R * 1000, cp.Y, cp.Z)
    c = r.Circle(sc, rr * 1000); c.Plane = r.Plane(sc, r.Vector3d(0, 1, 0))
    rv = r.RevSurface.Create(c.ToNurbsCurve(), r.Line(cp, r.Point3d(cp.X, cp.Y, cp.Z + 1000)), 0, 2 * math.pi)
    m.Objects.AddBrep(r.Brep.CreateFromRevSurface(rv, False, False), at(k, name))


def dome(c_ad, R, h, z0, k, name):
    """縦の軸のまわりの半楕円体のドーム（底は平ら、閉じた一つの面）"""
    x, y = gc.X(*c_ad); cp = r.Point3d(x * 1000, y * 1000, z0 * 1000 + GL)
    pts = [r.Point3d(cp.X + R * 1000 * math.sin(t), cp.Y, cp.Z + h * 1000 * math.cos(t)) for t in np.linspace(0, math.pi / 2, 33)]
    pts.append(r.Point3d(cp.X, cp.Y, cp.Z))
    rv = r.RevSurface.Create(r.Polyline(pts).ToNurbsCurve(), r.Line(cp, r.Point3d(cp.X, cp.Y, cp.Z + 1000)), 0, 2 * math.pi)
    m.Objects.AddBrep(r.Brep.CreateFromRevSurface(rv, False, False), at(k, name))


def tube_ad(q0, q1, z, rad, k, name):
    """(a, d) の 2 点を z（GL からの m）の高さで結ぶ管（rad は m）"""
    p0 = P3(*q0, z=z); p1 = P3(*q1, z=z)
    _cyl(p0, r.Vector3d(p1.X - p0.X, p1.Y - p0.Y, p1.Z - p0.Z), rad * 1000, k, name)


def rect(c, l, w, rot):
    """中心 c、rot の向きに長さ l・直角に幅 w の長方形（(a, d) の 4 点）"""
    ca_, sa_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [(c[0] + u * ca_ - v * sa_, c[1] + u * sa_ + v * ca_) for u, v in ((-l / 2, -w / 2), (l / 2, -w / 2), (l / 2, w / 2), (-l / 2, w / 2))]


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
m.Objects.AddPolyline(r.Polyline([P3(a, d, z) for a, d, z in bed]), at("90l", "小川の川床（中心線）"))
FL = s.get("fall")
if FL:
    (la, ld, lz) = FL["lip"]; pc = FL["pool"]
    pa, pd = pc["c"]
    for k_, (fa, fd, fz) in enumerate([(la, ld, lz), (la + (pa - la) * 0.45, ld + (pd - ld) * 0.45, lz - 0.25)]):
        box(fa - 0.35, fa + 0.35, fd - 0.2, fd + 0.2, fz - 0.15, fz, 96, f"滝の落ち口の平たい石 {k_ + 1}（落差約0.45）")
    disk = r.Mesh(); cpt = P3(pa, pd, pc["bed"] + 0.12); disk.Vertices.Add(cpt.X, cpt.Y, cpt.Z)
    for q in np.linspace(0, 2 * math.pi, 33):
        v = P3(pa + pc["r"] * math.cos(q), pd + pc["r"] * math.sin(q), pc["bed"] + 0.12); disk.Vertices.Add(v.X, v.Y, v.Z)
    for i in range(1, 33):
        disk.Faces.AddFace(0, i, i + 1)
    disk.Normals.ComputeNormals(); m.Objects.AddMesh(disk, at(92, "滝壺の水面（φ1.0、深さ 0.15）"))
    curve_ad(ell((pa, pd), (pc["r"], pc["r"])), "90l", "滝壺（輪郭）", close=True)
curve_ad(s["culvert"], "90l", "暗渠（用水路→みなもと、道すじ）", z=-0.6, drape=False)
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
# 床の噴水の石張り（10-30：閉じた板、上面は中心の地面 +0.01、厚さ 0.1。3〜5歳はφ4.6の円＝乳児と同じまん丸）
F = G["FOUNTAIN"]; _fz = H(*F["c"]) + 0.01
vcyl(F["c"], F["r"][0], _fz - 0.1, _fz, 96, f"床の噴水の石張り（φ{2 * F['r'][0]:.1f}、噴き口 0.8 m ごと）")
SP = G["SPLASH"]; _sz = H(*SP["c"]) + 0.01
vcyl(SP["c"], SP["r"][0], _sz - 0.1, _sz, 96, "乳児の床の噴水の石張り（φ4.0、低い泡の噴き口）")
if SP.get("mist"):
    _ms = SP["mist"]; zm = H(*SP["c"]) + _ms["h"]
    torus(SP["c"], zm, _ms["r"], 0.02, "95s", "霧のわ（φ1.8、h2.0、ステンレスの管φ40）")
    for q in _ms["posts"]:
        g_ = H(*q); box(q[0] - 0.05, q[0] + 0.05, q[1] - 0.05, q[1] + 0.05, g_ - 0.05, zm + 0.1, "95p", "霧のわの柱 100 角")
        vx_, vy_ = q[0] - SP["c"][0], q[1] - SP["c"][1]; L0 = math.hypot(vx_, vy_)
        pe_ = (SP["c"][0] + vx_ / L0 * _ms["r"], SP["c"][1] + vy_ / L0 * _ms["r"])
        tube_ad(q, pe_, zm, 0.015, "95s", "霧のわの腕（ステンレスφ30）")
        curve_ad([q, pe_], "90l", "霧のわの腕（線）", z=zm, drape=False)
for dd, nm in ((15.3, "護岸の溝（小川、幅 0.3）"), (35.0, "護岸の溝（雨の川、幅 0.3）")):
    pa, pb = P3(56.0, dd - 0.15, 0.0), P3(56.0, dd + 0.15, 0.0)
    for zz in (0.0, -4.0):
        m.Objects.AddLine(r.Point3d(pa.X, pa.Y, zz * 1000 + GL), r.Point3d(pb.X, pb.Y, zz * 1000 + GL), at("90l", nm))

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
    curve_ad(AW["poly"], "90l", "雨庭（洲浜、玉石の浜の浅いくぼみ−0.25、溢れたら護岸の溝へ）", close=True)
    for sa_, sd_, sr_ in AW["stones"]:
        c0 = P3(sa_, sd_); sph = r.Sphere(r.Point3d(c0.X, c0.Y, c0.Z + sr_ * 300), sr_ * 1000)
        m.Objects.AddBrep(sph.ToBrep(), at(96, "雨庭の景石"))
    # 10-30（ユーザー）：洲浜の白い玉石の層。地形（くぼみを含む H）に沿って厚さ 0.05 の閉じた立体（メッシュ）
    from shapely import constrained_delaunay_triangles as _cdt
    _pg = Polygon(AW["poly"]).buffer(0)
    _bd = list(_pg.exterior.coords)[:-1]; _dn = []
    for (a0_, d0_), (a1_, d1_) in zip(_bd, _bd[1:] + _bd[:1]):
        n_ = max(1, int(math.ceil(math.hypot(a1_ - a0_, d1_ - d0_) / 0.3)))
        _dn += [(a0_ + (a1_ - a0_) * t / n_, d0_ + (d1_ - d0_) * t / n_) for t in range(n_)]
    _tris = [list(t.exterior.coords)[:3] for t in _cdt(Polygon(_dn)).geoms]

    def _split(t, lv):                                  # 中点で4つに（隣どうし同じ点で割れるので継ぎ目なし）
        if lv == 0:
            return [t]
        p, q, s = t; mid = lambda u, v: ((u[0] + v[0]) / 2, (u[1] + v[1]) / 2)
        pq, qs, sp = mid(p, q), mid(q, s), mid(s, p)
        return sum((_split(x, lv - 1) for x in ((p, pq, sp), (pq, q, qs), (sp, qs, s), (pq, qs, sp))), [])
    _tris = sum((_split(t, 3) for t in _tris), [])
    WM = r.Mesh(); _vi = {}; TH = 0.05

    def _v(p, top):
        k_ = (round(p[0], 6), round(p[1], 6), top)
        if k_ not in _vi:
            q_ = P3(p[0], p[1], H(*p) + (TH if top else 0.0)); _vi[k_] = WM.Vertices.Add(q_.X, q_.Y, q_.Z)
        return _vi[k_]
    _edges = {}
    for t in _tris:
        xy = [gc.X(*p) for p in t]
        if (xy[1][0] - xy[0][0]) * (xy[2][1] - xy[0][1]) - (xy[1][1] - xy[0][1]) * (xy[2][0] - xy[0][0]) < 0:
            t = (t[0], t[2], t[1])                       # xy で左回りに（上面が上向き）
        WM.Faces.AddFace(_v(t[0], 1), _v(t[1], 1), _v(t[2], 1))
        WM.Faces.AddFace(_v(t[0], 0), _v(t[2], 0), _v(t[1], 0))
        for u_, w_ in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            ku, kw = (round(u_[0], 6), round(u_[1], 6)), (round(w_[0], 6), round(w_[1], 6))
            _edges[(ku, kw)] = (u_, w_)
    for (ku, kw), (u_, w_) in _edges.items():         # 外周（逆向きの辺が無い辺）に側面
        if (kw, ku) not in _edges:
            WM.Faces.AddFace(_v(u_, 0), _v(w_, 0), _v(w_, 1), _v(u_, 1))
    WM.Normals.ComputeNormals(); WM.Compact()
    m.Objects.AddMesh(WM, at("92s", f"雨庭の白い玉石の層（洲浜、t{TH:.2f}、地形のくぼみに沿う）"))

# ---- シャワーの柱と輪のシャワー「あめのわ」（95） ----
SH = G["SHOWER"]; _rg = SH.get("ring")
if _rg:
    g_ = H(*SH["c"])
    for q in _rg.get("posts", [SH["c"]]):
        gq = H(*q); box(q[0] - 0.06, q[0] + 0.06, q[1] - 0.06, q[1] + 0.06, gq - 0.05, gq + _rg["h"] + 0.15, "95p", "あめのわの柱 120 角")
    gr_ = H(*_rg["c"]) + _rg["h"]
    torus(_rg["c"], gr_, _rg["r"], 0.025, "95s", "あめのわ（輪のシャワーφ2.4、ステンレスの管φ50、噴き口48）")
    for q in _rg.get("posts", [SH["c"]]):              # 腕：柱から輪へ（両側から支える）
        vx, vy = q[0] - _rg["c"][0], q[1] - _rg["c"][1]; L_ = math.hypot(vx, vy)
        pe = (_rg["c"][0] + vx / L_ * _rg["r"], _rg["c"][1] + vy / L_ * _rg["r"])
        tube_ad(q, pe, gr_, 0.02, "95s", "あめのわの腕（ステンレスφ40）")
        curve_ad([q, pe], "90l", "あめのわの腕（線）", z=gr_, drape=False)

# ---- 年中行事の草（94g） ----
for a_, d_, r_, nm_, n_ in G.get("GYOJI", {}).get("items", []):
    _rp = ring_pts((a_, d_), r_, 24)                  # 10-30：草は h0.3 の塊（閉じた円柱、上面は範囲のいちばん高い地面 +0.3）
    vcyl((a_, d_), r_, gmin(_rp) - 0.05, gmax(_rp) + 0.3, "94g", f"{nm_}（{n_}）")

# ---- てんぐのたに（10-31）：シャガ（94g、h0.3の塊）・ヤマブキ（94b、低木の株）。口のヒイラギは TREES ----
TG = G.get("TENGU", {})
for a_, d_, r_ in TG.get("shaga", []):
    _rp = ring_pts((a_, d_), r_, 24)
    vcyl((a_, d_), r_, gmin(_rp) - 0.05, gmax(_rp) + 0.3, "94g", "シャガ（てんぐのたにの下草）")
for a_, d_, r_ in TG.get("yamabuki", []):
    _rp = ring_pts((a_, d_), r_, 24)        # 10-31 7:45：低木は地面から盛り上がる扁平な半球（94b）、木の形にしない
    dome((a_, d_), r_, gmax(_rp) - gmin(_rp) + 1.2, gmin(_rp) - 0.05, "94b", "ヤマブキ（てんぐのたに、低木の株 h1.2）")
for a_, d_, r_ in G.get("KATA", {}).get("yamabuki", []):     # 築山の北東の肩のヤマブキの茂み（10-31）
    _rp = ring_pts((a_, d_), r_, 24)
    dome((a_, d_), r_, gmax(_rp) - gmin(_rp) + G["KATA"].get("h", 1.0), gmin(_rp) - 0.05, "94b", "ヤマブキ（築山の北東の肩の茂み、転がり落ちない帯 h1.0）")

# ---- 94 木 ----
TRUNK_R = {"small": 0.05, "big": 0.15, "climb": 0.15, "mid": 0.09, "fruit": 0.09, "ever": 0.075}   # 幹の半径（m）
TH = {"small": (1.8, 0.7), "big": (7.5, 3.0), "climb": (7.0, 3.2), "mid": (5.0, 2.1), "fruit": (4.0, 2.3), "ever": (4.5, 1.9)}
for a, d, kind, _, note in G["TREES"]:
    sp = note.split("（")[0]; ht, rc = TH[kind]
    base = P3(a, d)
    zc = ht - rc * 0.9                                   # 樹冠の中心の高さ（地面から）
    for tu in G.get("TREE_UNDER", {}).get("trees", []):  # 枝下を上げる木（下枝を払う、10-29）
        if abs(tu["at"][0] - a) < 0.01 and abs(tu["at"][1] - d) < 0.01: zc = max(zc, tu["under"] + rc * 0.9)
    g0_ = H(a, d)                                        # 10-30：幹は閉じた円柱、地面の少し下から樹冠の球の中ほどまで
    vcyl((a, d), TRUNK_R[kind], g0_ - 0.1, g0_ + zc, 94, f"{sp}（幹φ{TRUNK_R[kind] * 2000:.0f}）")
    sph = r.Sphere(r.Point3d(base.X, base.Y, base.Z + zc * 1000), rc * 0.9 * 1000)
    m.Objects.AddBrep(sph.ToBrep(), at("94c", note))

# ---- 95 遊び場 ----
# 10-30：砂・粒は薄い板（上面は範囲のいちばん高い地面 +0.02、厚さ 0.1）、縁は幅 0.15・h0.25 の輪（95r、木）
def _ring_out(pts_ad, w):
    pg = Polygon(pts_ad).buffer(w, join_style=1)
    return list(pg.exterior.coords)[:-1]
_sd = G["SAND"]["poly"]; _sz = gmax(_sd) + 0.02
slab(_sd, _sz - 0.1, _sz, 95, "砂場の砂（約12 m²）")
slab(_ring_out(_sd, 0.15), gmin(_sd) - 0.1, _sz + 0.23, "95r", "砂場の縁（丸太の腰掛け、幅 0.15・h0.25）", hole_ad=_sd)
GR = G["GRAIN"]; ca, sa = math.cos(math.radians(GR["rot"])), math.sin(math.radians(GR["rot"]))
gr = lambda u, v: (GR["c"][0] + u * ca - v * sa, GR["c"][1] + u * sa + v * ca)
hl, hw = GR["l"] / 2, GR["w"] / 2
_gp = [gr(-hl, -hw), gr(hl, -hw), gr(hl, hw), gr(-hl, hw)]; _gz = gmax(_gp) + 0.02
slab(_gp, _gz - 0.1, _gz, 95, "粒の遊び場の粒（1〜2 mm、2.4×3.0）")
_go = [gr(-hl - 0.15, -hw - 0.15), gr(hl + 0.15, -hw - 0.15), gr(hl + 0.15, hw + 0.15), gr(-hl - 0.15, hw + 0.15)]
slab(_go, gmin(_gp) - 0.1, _gz + 0.23, "95r", "粒の遊び場の木の縁（幅 0.15・h0.25）", hole_ad=_gp)
_r0, _r1 = gr(-hl, hw + 0.35), gr(hl, hw + 0.35); _rz = max(H(*_r0), H(*_r1)) + 0.1
tube_ad(_r0, _r1, _rz, 0.1, "95r", "帆布を巻いた棒（φ0.2、長さ 3.0）")
B = G["BOWL"]; curve_ad(ell(B["c"], (B["r"], B["r"])), "90l", "すりばち（輪郭、お話の輪、大雨の日は雨の池）", close=True)   # くぼみは地形（90）
W = G["WILLOW"]; _wp = ring_pts(W["c"], W["r"], 24)
dome(W["c"], W["r"], 2.0, gmin(_wp) - 0.05, "94c", "柳の家（生きたヤナギのドームφ3・h2.0）")   # 生きた木なので樹冠のレイヤー（10-28）

# ---- 95w・95m 鉄棒ひと組（10-27 ユーザー）：柱＝栗の丸太（閉じた円柱）、棒＝ステンレスφ25（閉じた円柱） ----
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
        m.Objects.AddBrep(cyl.ToBrep(True, True), at("95m", f"鉄棒の棒（ステンレスφ{BR['bar_d'] * 1000:.0f}、h{hb:.2f}）"))

# ---- 96 石 ----
for q in G["SEKIMORI"].get("steps", []):             # 10-30：飛び石は閉じた円柱（φ0.52、上面は地面 +0.04、厚さ 0.12）
    g_ = H(*q); vcyl(q, 0.26, g_ - 0.08, g_ + 0.04, 96, "飛び石（縁側の前の道）")
for q in G["SEKIMORI"]["pts"]:
    p = P3(*q); sph = r.Sphere(r.Point3d(p.X, p.Y, p.Z + 120), 150)
    m.Objects.AddBrep(sph.ToBrep(), at(96, "関守石（しずかのもりの境）"))
_SL = LineString(G["STREAM"]["line"])
for b in G["BRIDGES"]:                                  # 10-30：橋・小川の飛び石は閉じた立体
    c = b["c"]; nm = b["_"]
    t_ = _SL.project(Point(*c)); q0_, q1_ = _SL.interpolate(max(t_ - 0.5, 0)), _SL.interpolate(t_ + 0.5)
    rs = math.degrees(math.atan2(q1_.y - q0_.y, q1_.x - q0_.x))       # 小川の向き
    if b["w"] > 2:                                      # 平らな石の橋：小川に沿って幅 w、渡る向きに 1.2、厚さ 0.2
        _bp = rect(c, b["w"], 1.2, rs); _bz = gmax(_bp) + 0.05
        slab(_bp, _bz - 0.2, _bz, 96, nm)
    elif b["w"] > 0:                                    # 丸太の橋：φ0.3 の丸太 3 本、渡る向きに長さ 1.4
        n_l = 3; dl = b["w"] / n_l
        for i in range(n_l):
            o_ = -b["w"] / 2 + dl * (i + 0.5)
            cc = (c[0] + o_ * math.cos(math.radians(rs)), c[1] + o_ * math.sin(math.radians(rs)))
            e0, e1 = rect(cc, 0.0, 1.4, rs)[0], rect(cc, 0.0, 1.4, rs)[3]
            tube_ad(e0, e1, max(H(*e0), H(*e1)) + 0.1, 0.15, "95r", nm + "（丸太φ0.3）")
    else:                                               # 小川の飛び石：川床から地面 +0.03 まで
        g_ = H(*c); vcyl(c, 0.3, g_ - 0.35, g_ + 0.03, 96, nm + "（小川の中）")
vb = F["valve"]["c"]; box(vb[0] - 0.45, vb[0] + 0.45, vb[1] - 0.3, vb[1] + 0.3, H(*vb) - 0.6, H(*vb), 96, "バルブます（電磁弁 4 系統・逆流防止・子メーター）")

# ---- 97 車の道・柵ぎわの草 ----
GN = G.get("GATE_N")
if GN:
    (ga0, gd0), (ga1, gd1) = GN["p0"], GN["p1"]
    gz = H(ga0, (gd0 + gd1) / 2)
    box(ga0 - 0.02, ga0 + 0.02, min(gd0, gd1), max(gd0, gd1), gz, gz + GN["h"], 97, "北の口の木戸 h1.2（庭の側へ開く、掛け金は外側の高い所）")

curve_ad(G["VEHICLE"]["line"], "90l", "剪定・搬入の車の道（道すじ、芝の保護材、幅2.5）")
# 10-31：のぞきの生垣はやめた。柵ぎわ1 mの低い草の帯（94g、h0.3 の閉じた箱、約 1 m ごとに地面に沿わせる）
RP = G.get("RIVER_PLANTING", {})
for d0_, d1_ in RP.get("segs", []):
    nseg = max(1, int(round((d1_ - d0_) / 1.0)))
    for i in range(nseg):
        e0, e1 = d0_ + (d1_ - d0_) * i / nseg, d0_ + (d1_ - d0_) * (i + 1) / nseg
        _c4 = [(RP["a"][0], e0), (RP["a"][1], e0), (RP["a"][1], e1), (RP["a"][0], e1)]
        box(RP["a"][0], RP["a"][1], e0, e1, gmin(_c4) - 0.05, gmax(_c4) + RP.get("h", 0.3), "94g", "川沿いの柵ぎわの低い草（カンスゲ・ヤブラン・野芝、h0.3）")

out = os.path.join(gc.ROOT, "model", "sodachiya_garden_layers.3dm")
m.Write(out, 7)
print("wrote", out, "contours", nc, "plates", npl, "trees", len(G["TREES"]))
