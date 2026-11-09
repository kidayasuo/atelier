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
         "90g": ("90g_園庭_ひみつのたにの底（砂利）", (158, 148, 128)), "90l": ("90l_園庭_線（中心線・輪郭・道すじ。開いたときは消す）", (120, 120, 120)),
         92: ("92_園庭_水（小川の水・滝壺の水）", (76, 141, 184)), "92s": ("92s_園庭_雨庭の玉石（洲浜、白）", (222, 218, 206)),
         "92b": ("92b_園庭_小川の川床（溝の底と岸・滝壺の器、玉石）", (140, 136, 126)), 93: ("93_園庭_小屋（便所・倉庫・コンポストの間）", (155, 118, 83)),
         94: ("94_園庭_木の幹（円柱、名前＝種類）", (111, 100, 80)), "94c": ("94c_園庭_樹冠（葉、名前＝種類、柳の家）", (111, 143, 87)), "94g": ("94g_園庭_草（年中行事の草・てんぐのたにのシャガ、h0.3の塊、葉）", (150, 175, 100)),
         "94b": ("94b_園庭_低木（葉、ヤマブキの株、扁平な半球）", (170, 160, 80)),
         95: ("95_園庭_遊び場（砂場の砂・粒の遊び場の粒）", (168, 142, 88)),
         "95w": ("95w_園庭_雲梯の柱と桁（栗の丸太・角材）", (140, 110, 80)), "95m": ("95m_園庭_雲梯の握り棒と段（ステンレス）", (150, 155, 162)),
         "95n": ("95n_園庭_ネットのハンモック（麻のロープ）", (196, 170, 120)),
         "95r": ("95r_園庭_木の縁と丸太（砂場・粒の遊び場の縁、帆布を巻いた棒、丸太の橋）", (150, 115, 80)),
         "95k": ("95k_園庭_切り株と丸太の木口と芯（明るい木）", (214, 182, 132)),
         "95h": ("95h_園庭_切り株と丸太の樹皮（幹の外周・裾・根張り・年輪の輪）", (104, 88, 70)),
         "95s": ("95s_園庭_輪のシャワー（あめのわ・霧のわの輪と腕、ステンレス）", (160, 165, 172)),
         "95p": ("95p_園庭_シャワーの柱（あめのわ・霧のわ、木 120角・100角）", (165, 130, 90)),
         96: ("96_園庭_石（床の噴水の御影石・橋・飛び石・滝の石・景石・バルブます）", (110, 104, 92)), "96g": ("96g_園庭_ゴム舗装（乳児の床の噴水の床、EPDMのゴムチップ）", (208, 210, 206)), "96w": ("96w_園庭_石積み（境の土留め、空石積み）", (110, 104, 92)), 97: ("97_園庭_木戸", (183, 169, 140)),
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


def kirikabu(m_, c, z_g, d, h, li_kiguchi, li_kawa, tilt=0.0, tilt_dir=0.0, roots=4, embed=80.0, seed=0, name="切り株"):
    """木の切り株（11-01 ユーザー：「木の切り株だ」と分かる造形）。園庭と、本館の教室の切り株（本館係）が使う。
    使い方（座標は mm、3dm の世界の座標）：
        import katachi  # model/build/south を sys.path に（garden_common が入れる）
        n = kirikabu(m, (x, y), z_g, d, h, li_kiguchi, li_kawa, tilt=8, tilt_dir=30, roots=4, embed=80, seed=3, name="切り株")
      c＝根もとの中心 (x, y)、z_g＝地面（床）の高さ、d＝幹の径、h＝木口の中心の地面からの高さ（どれも mm）。
      li_kiguchi＝木口と芯のレイヤー（明るい木）、li_kawa＝樹皮・裾・根・年輪の輪のレイヤー（樹皮）。
      tilt＝幹の傾き（度、0〜12くらい。木口が斜めに切れて見える）、tilt_dir＝傾く向き（xy の度）。
      roots＝根張りの本数（3〜5。床の上に置く教室の切り株は 0）、embed＝地面に埋める深さ（床の上なら 0）。
      seed で根の向きと長さが変わる。返り値は作った物の数。
    形（katachi の押し出し・回転体だけ、メッシュは使わない）：
      芯（円柱、木口の色）／樹皮（外周の厚さ約15の管）／裾（根もとで径×1.15に広がる円錐台、回転体）／
      根張り（根もとから斜め下へ地面に潜る短い円柱）／年輪（木口の上に厚さ3・幅4の薄い輪を2〜3本、樹皮の色）"""
    import katachi as K
    rnd = np.random.default_rng(seed)
    R = d / 2.0; t = min(15.0, 0.08 * R)
    tl = math.radians(tilt); td = math.radians(tilt_dir)
    u = np.array([math.sin(tl) * math.cos(td), math.sin(tl) * math.sin(td), math.cos(tl)])
    base = np.array([c[0], c[1], z_g - embed])
    L = (h + embed) / max(math.cos(tl), 0.5)
    top = base + u * L
    n = 0
    K.add(m_, K.enchu(base, top, R - t), li_kiguchi, name=name + "（芯・木口）"); n += 1
    K.add(m_, K.enchu(base, top, R, R - t), li_kawa, name=name + "（樹皮）"); n += 1
    hs = min(0.35 * h, 120.0)                                           # 裾：根もとで少し広がる
    K.add(m_, K.kaiten([(0, z_g - embed), (R * 1.15, z_g - embed), (R * 1.15, z_g), (R * 1.0, z_g + hs), (0, z_g + hs)], (c[0], c[1]), 0, 360),
          li_kawa, name=name + "（裾）"); n += 1
    for k in range(roots):                                              # 根張り：幹の中から斜め下へ地面に潜る
        a = 2 * math.pi * (k + rnd.uniform(-0.15, 0.15)) / roots
        rr = R * rnd.uniform(0.2, 0.28); lr = R + rnd.uniform(90.0, 170.0)
        p0 = (c[0] + 0.5 * R * math.cos(a), c[1] + 0.5 * R * math.sin(a), z_g + min(0.3 * h, 70.0))
        p1 = (c[0] + lr * math.cos(a), c[1] + lr * math.sin(a), z_g - 1.5 * rr)
        K.add(m_, K.enchu(p0, p1, rr), li_kawa, name=name + "（根張り）"); n += 1
    for f in ((0.32, 0.58, 0.8) if R > 200 else (0.4, 0.75)):           # 年輪：木口の上の薄い輪
        K.add(m_, K.enchu(top, top + u * 3.0, f * (R - t), f * (R - t) - 4.0), li_kawa, name=name + "（年輪）"); n += 1
    return n


def maruta(m_, p0, p1, d, li_kiguchi, li_kawa, sink=None, seed=0, name="丸太"):
    """横たわる丸太（11-03 ユーザー：切り株と丸太をたくさん散らす）。切り株（kirikabu）と同じ素材の決まり。
    使い方（座標は mm、3dm の世界の座標）：
        n = maruta(m, (x0, y0, z0), (x1, y1, z1), d, li_kiguchi, li_kawa, sink=70, seed=3, name="丸太")
      p0・p1＝両端の木口の下の地面の点（x, y, 地面の高さ）。軸は両端の地面＋半径−sink を結ぶ（地面の傾きに沿って寝る）。
      d＝径、sink＝地面に沈める深さ（既定は径の1/4）。li_kiguchi＝芯と両端の木口（明るい木）、li_kawa＝樹皮と木口の年輪の輪。
      seed で年輪の輪の大きさが少し変わる。返り値は作った物の数。
    形（katachi の円柱・管だけ、メッシュは使わない）：
      芯（円柱、両端の面が木口）／樹皮（外周の厚さ約15の管、木口より 5 mm 引っ込める）／
      年輪（両端の木口の外に厚さ3・幅4の薄い輪を2〜3本、樹皮の色）"""
    import katachi as K
    rnd = np.random.default_rng(seed)
    R = d / 2.0; t = min(15.0, 0.08 * R)
    s = 0.25 * d if sink is None else sink
    a = np.array([p0[0], p0[1], p0[2] + R - s]); b = np.array([p1[0], p1[1], p1[2] + R - s])
    u = (b - a) / np.linalg.norm(b - a)
    n = 0
    K.add(m_, K.enchu(a, b, R - t), li_kiguchi, name=name + "（芯・木口）"); n += 1
    K.add(m_, K.enchu(a + u * 5.0, b - u * 5.0, R, R - t), li_kawa, name=name + "（樹皮）"); n += 1
    fs = (0.3, 0.55, 0.8) if R > 120 else (0.4, 0.75)
    for e, w in ((a, -u), (b, u)):                                      # 年輪：両端の木口の外の薄い輪
        for f in fs:
            f = f * rnd.uniform(0.92, 1.08)
            K.add(m_, K.enchu(e, e + w * 3.0, f * (R - t), f * (R - t) - 4.0), li_kawa, name=name + "（年輪）"); n += 1
    return n


def tube_ad(q0, q1, z, rad, k, name):
    """(a, d) の 2 点を z（GL からの m）の高さで結ぶ管（rad は m）"""
    p0 = P3(*q0, z=z); p1 = P3(*q1, z=z)
    _cyl(p0, r.Vector3d(p1.X - p0.X, p1.Y - p0.Y, p1.Z - p0.Z), rad * 1000, k, name)


def rect(c, l, w, rot):
    """中心 c、rot の向きに長さ l・直角に幅 w の長方形（(a, d) の 4 点）"""
    ca_, sa_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [(c[0] + u * ca_ - v * sa_, c[1] + u * sa_ + v * ca_) for u, v in ((-l / 2, -w / 2), (l / 2, -w / 2), (l / 2, w / 2), (-l / 2, w / 2))]


# ---- 90 地形（0.5 m の格子、園庭の中だけ） ----
# 10-31（ユーザー：雨落ちがモデルにない）：溝・池・洲浜の上を地形が覆っていた。小川と雨の川の溝（岸の縁まで）・滝壺・雨庭（洲浜）の形で
# 地形を切り欠く。切り欠きにかかる格子の目は、残りを三角形で埋める（縁の点は溝の岸・洲浜の縁と同じ点、高さは地面）
from shapely import constrained_delaunay_triangles as _cdt0
from shapely.ops import unary_union as _uu0
from shapely.geometry import box as _box0


def _lip_strip(cl, half):
    """trough と同じ岸の縁（中心線から ±half）の点で、溝を囲む多角形"""
    L_, R_ = [], []
    for i, (a, d, _z) in enumerate(cl):
        j = min(i + 1, len(cl) - 1); h = max(i - 1, 0)
        ta, td = cl[j][0] - cl[h][0], cl[j][1] - cl[h][1]; ln = math.hypot(ta, td) or 1
        na, nd = -td / ln, ta / ln
        L_.append((a - na * half, d - nd * half)); R_.append((a + na * half, d + nd * half))
    return Polygon(L_ + R_[::-1]).buffer(0)


def _rain_cl():
    am_ = G["AMAOCHI"]; out = []
    for u in np.linspace(am_["u"][1], am_["u"][0], 140):
        a, d = gc.AD(*gc.UV(u, G["EDGE_V"])); out.append((a, d, H(a, d) - am_["depth"]))
    for (a0_, d0_), (a1_, d1_) in zip(am_["outlet"][:-1], am_["outlet"][1:]):
        for t in np.linspace(0, 1, 8)[1:]:
            a, d = a0_ + (a1_ - a0_) * t, d0_ + (d1_ - d0_) * t; out.append((a, d, H(a, d) - am_["depth"]))
    return out


def _aw_ring():
    _pg = Polygon(G["AMANIWA"]["poly"]).buffer(0); _bd = list(_pg.exterior.coords)[:-1]; out = []
    for (a0_, d0_), (a1_, d1_) in zip(_bd, _bd[1:] + _bd[:1]):
        n_ = max(1, int(math.ceil(math.hypot(a1_ - a0_, d1_ - d0_) / 0.3)))
        out += [(a0_ + (a1_ - a0_) * t / n_, d0_ + (d1_ - d0_) * t / n_) for t in range(n_)]
    return out


_holes = [_lip_strip(gc.stream_bed(240), 0.25 + 0.05), _lip_strip(_rain_cl(), G["AMAOCHI"]["w"] / 2 + 0.05)]
_fl = G["STREAM"].get("fall")
if _fl:
    _pc = _fl["pool"]
    _holes.append(Polygon([(_pc["c"][0] + _pc["r"] * math.cos(q), _pc["c"][1] + _pc["r"] * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 33)[:-1]]))
# 11-02（ユーザー）：雨庭は見える面がGL±0、地形に穴をあけず 92s の薄い板をのせる
_holes.append(Polygon(G["SAND"]["poly"]).buffer(0.15, join_style=1))      # 10-31：掘り込んだ砂場（砂・縁・土留めの外まで）
HOLES = _uu0(_holes)
gpoly = Polygon([gc.AD(*p) for p in gc.garden_poly().exterior.coords])
S = 0.5
A = np.arange(12.0, 56.01, S); D = np.arange(0.0, 36.01, S)
mesh = r.Mesh(); idx = {}; _vk = {}


def _tv(a, d):
    k_ = (round(a, 5), round(d, 5))
    if k_ not in _vk:
        p = P3(a, d); _vk[k_] = mesh.Vertices.Add(p.X, p.Y, p.Z)
    return _vk[k_]


for i, a in enumerate(A):
    for j, d in enumerate(D):
        if gpoly.buffer(0.6).contains(Point(a, d)):
            idx[(i, j)] = _tv(a, d)
_cut = []
for (i, j), v in idx.items():
    q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
    if all(k in idx for k in q):
        cell = _box0(A[i], D[j], A[i] + S, D[j] + S)
        if cell.intersects(HOLES):
            _cut.append(cell)
        else:
            mesh.Faces.AddFace(*[idx[k] for k in q])
_rest = _uu0(_cut).difference(HOLES)
for _pp in getattr(_rest, "geoms", [_rest]):
    if _pp.geom_type != "Polygon" or _pp.area < 1e-6:
        continue
    for t_ in _cdt0(_pp).geoms:
        c3 = list(t_.exterior.coords)[:3]
        mesh.Faces.AddFace(*[_tv(*c_) for c_ in c3])
mesh.Normals.ComputeNormals(); mesh.Compact()
m.Objects.AddMesh(mesh, at(90, "園庭の地形（GL からの起伏、溝・滝壺・洲浜は切り欠く）"))

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


def water_body(cl, half, top, bot, name):
    """小川の水（10-31 ユーザー：レイトレースで水に見えるように）：溝に沿う閉じた薄い立体（メッシュ）。
    上面は川床+top、下面は川床+bot、幅は溝の岸から 3 mm 内（岸・川床の面と重ねない）。法線は外向き"""
    V = []
    for i, (a, d, zb) in enumerate(cl):
        j = min(i + 1, len(cl) - 1); h = max(i - 1, 0)
        ta, td = cl[j][0] - cl[h][0], cl[j][1] - cl[h][1]; ln = math.hypot(ta, td) or 1
        na, nd = -td / ln, ta / ln
        for sa, zz in ((-half, top), (half, top), (half, bot), (-half, bot)):
            q = P3(a + na * sa, d + nd * sa, zb + zz); V.append((q.X, q.Y, q.Z))
    F = []
    for i in range(len(cl) - 1):
        for c in range(4):
            c1 = (c + 1) % 4; F.append((4 * i + c, 4 * i + c1, 4 * (i + 1) + c1, 4 * (i + 1) + c))
    n = len(cl) - 1
    F.append((3, 2, 1, 0)); F.append((4 * n, 4 * n + 1, 4 * n + 2, 4 * n + 3))
    P_ = np.array(V); vol = 0.0
    for f in F:
        for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])):
            vol += np.dot(P_[t[0]], np.cross(P_[t[1]], P_[t[2]])) / 6
    if vol < 0:
        F = [f[::-1] for f in F]
    wm = r.Mesh()
    for v in V:
        wm.Vertices.Add(*v)
    for f in F:
        wm.Faces.AddFace(*f)
    wm.Normals.ComputeNormals(); wm.Compact(); m.Objects.AddMesh(wm, at(92, name))


s = G["STREAM"]
bed = gc.stream_bed(240)
# 10-31（ユーザー：小川が茶色い）：溝（川床と岸）は 92b（玉石）、水は 92 に溝の幅いっぱいの閉じた薄い立体（水深 0.04）
trough(bed, 0.25, "92b", "小川の溝（幅 0.5、底は平ら、岸は急。川床と岸）")
water_body(bed, 0.25 - 0.003, 0.04, 0.003, "小川の水（幅 0.5、水深 0.04、閉じた薄い立体）")
m.Objects.AddPolyline(r.Polyline([P3(a, d, z) for a, d, z in bed]), at("90l", "小川の川床（中心線）"))
FL = s.get("fall")
if FL:
    (la, ld, lz) = FL["lip"]; pc = FL["pool"]
    pa, pd = pc["c"]
    for k_, (fa, fd, fz) in enumerate([(la, ld, lz), (la + (pa - la) * 0.45, ld + (pd - ld) * 0.45, lz - 0.25)]):
        box(fa - 0.35, fa + 0.35, fd - 0.2, fd + 0.2, fz - 0.15, fz, 96, f"滝の落ち口の平たい石 {k_ + 1}（落差約0.45）")
    # 10-31：滝壺の水は閉じた円柱（底から 3 mm 上〜底+0.12、器の壁から 3 mm 内）
    import sys as _sys0
    _sys0.path.insert(0, os.path.join(gc.ROOT, "model", "build", "south"))
    import katachi as _KT0
    _x, _y = gc.X(pa, pd)
    _KT0.add(m, _KT0.enchu((_x * 1000, _y * 1000, (pc["bed"] + 0.003) * 1000 + GL), (_x * 1000, _y * 1000, (pc["bed"] + 0.12) * 1000 + GL),
                           (pc["r"] - 0.003) * 1000), LAY[92], name="滝壺の水面（φ1.0、深さ 0.15、水は閉じた円柱）")
    # 10-31：地形を切り欠いたので、滝壺の器（地面の縁から底まで の壁と、底）を足す
    bas = r.Mesh(); _n = 32
    for q in np.linspace(0, 2 * math.pi, _n + 1)[:-1]:
        ea, ed = pa + pc["r"] * math.cos(q), pd + pc["r"] * math.sin(q)
        v1 = P3(ea, ed); v2 = P3(ea, ed, pc["bed"]); bas.Vertices.Add(v1.X, v1.Y, v1.Z); bas.Vertices.Add(v2.X, v2.Y, v2.Z)
    cb = P3(pa, pd, pc["bed"]); ic = bas.Vertices.Add(cb.X, cb.Y, cb.Z)
    for k_ in range(_n):
        k1 = (k_ + 1) % _n
        bas.Faces.AddFace(2 * k_, 2 * k1, 2 * k1 + 1, 2 * k_ + 1); bas.Faces.AddFace(2 * k_ + 1, 2 * k1 + 1, ic)
    bas.Normals.ComputeNormals(); m.Objects.AddMesh(bas, at("92b", "滝壺（φ1.0、石組みの器）"))
    curve_ad(ell((pa, pd), (pc["r"], pc["r"])), "90l", "滝壺（輪郭）", close=True)
curve_ad(s["culvert"], "90l", "暗渠（用水路→みなもと、道すじ）", z=-0.6, drape=False)
am = G["AMAOCHI"]
cl = []
for u in np.linspace(am["u"][1], am["u"][0], 140):        # 北の端から南へ（流れの向き）。南の端の落とし口へつなぐ（前は北の端から落とし口へ54 mの帯が渡っていた、10-27）
    a, d = gc.AD(*gc.UV(u, G["EDGE_V"])); cl.append((a, d, H(a, d) - am["depth"]))
for (a0_, d0_), (a1_, d1_) in zip(am["outlet"][:-1], am["outlet"][1:]):
    for t in np.linspace(0, 1, 8)[1:]:
        a, d = a0_ + (a1_ - a0_) * t, d0_ + (d1_ - d0_) * t; cl.append((a, d, H(a, d) - am["depth"]))
trough(cl, am["w"] / 2, 99, "雨の川（雨落ちの溝、玉石の絵、幅 0.5・深さ 0.2）")
# 11-02（ユーザー）：中の玉石の粒の面はやめ、溝の面に玉石の絵（素材「玉石（雨落ちの溝）」、texture tamaishi_g、materials.py が本当の寸法で貼る）
# 床の噴水の石張り（10-30：閉じた板、上面は中心の地面 +0.01、厚さ 0.1。3〜5歳はφ4.6の円＝乳児と同じまん丸）
F = G["FOUNTAIN"]; _fz = H(*F["c"]) + 0.01
vcyl(F["c"], F["r"][0], _fz - 0.1, _fz, 96, f"床の噴水の石張り（御影石のバーナー仕上げ、φ{2 * F['r'][0]:.1f}、噴き口 0.8 m ごと）")
SP = G["SPLASH"]; _sz = H(*SP["c"]) + 0.01
vcyl(SP["c"], SP["r"][0], _sz - 0.1, _sz, "96g", "乳児の床の噴水のゴム舗装（EPDMのゴムチップ、φ4.0、低い泡の噴き口）")   # 11-01 ユーザー：乳児はゴム舗装
# 砂だめ（泥だめます、11-01 ユーザー：床の噴水は事実上の足洗い、砂対策は万全に）：排水口の内側に、上に掃除できる鋳鉄の蓋（床から +5 mm）
for _Q, _qz, _nm in ((F, _fz, "床の噴水"), (SP, _sz, "乳児の床の噴水")):
    _st_ = _Q.get("sand_trap"); _dr = _Q.get("drain")
    if _st_ and _dr:
        _v = np.array(_dr) - np.array(_Q["c"]); _v = _v / (np.linalg.norm(_v) or 1)
        _tc = np.array(_Q["c"]) + _v * (_Q["r"][0] - 0.05 - _st_["w"] / 2); _h = _st_["w"] / 2
        box(_tc[0] - _h, _tc[0] + _h, _tc[1] - _h, _tc[1] + _h, _qz - _st_["depth"], _qz + 0.005, 96,
            f"{_nm}の砂だめ（泥だめます {_st_['w']:.1f}×{_st_['w']:.1f}・深さ{_st_['depth']:.2f}、掃除できる鋳鉄の蓋）")
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
    curve_ad(AW["poly"], "90l", "雨庭（洲浜、見える面はGL±0の白い玉石の浜、下に砕石の貯留層、溢れたら護岸の溝へ）", close=True)
    for sa_, sd_, sr_ in AW["stones"]:
        c0 = P3(sa_, sd_); sph = r.Sphere(r.Point3d(c0.X, c0.Y, c0.Z + sr_ * 300), sr_ * 1000)
        m.Objects.AddBrep(sph.ToBrep(), at(96, "雨庭の景石"))
    # 11-02（ユーザー）：洲浜の白い玉石の層は、雨庭の輪郭の平らな薄い板（GL±0の上t0.02、katachi の押し出し）。玉石は絵（素材「白い玉石（洲浜）」の texture tamaishi）。
    # 下の砕石の貯留層（約4〜5 m³）はモデル化しない
    import sys as _sys
    _sys.path.insert(0, os.path.join(gc.ROOT, "model", "build", "south"))
    import katachi as KT
    _pg = Polygon(AW["poly"]).buffer(0); _z0 = max(H(a_, d_) for a_, d_ in _pg.exterior.coords)
    _pw = Polygon([(q_.X, q_.Y) for q_ in (P3(a_, d_, 0.0) for a_, d_ in _pg.exterior.coords)])
    KT.add(m, KT.ita(_pw, _z0 * 1000 + GL, (_z0 + 0.02) * 1000 + GL, simplify=0), LAY["92s"], name="雨庭の白い玉石の層（洲浜、GL±0の上t0.02の平らな板、玉石は絵）")

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
# 10-30：粒は薄い板（上面は範囲のいちばん高い地面 +0.02、厚さ 0.1）、縁は幅 0.15 の輪（95r、木、10-31 から h0.10）
def _ring_out(pts_ad, w):
    pg = Polygon(pts_ad).buffer(w, join_style=1)
    return list(pg.exterior.coords)[:-1]
# 10-31（ユーザー、項 20261031-2054-kanshu）：掘り込んだ砂場。砂の面は水平で、縁のいちばん低い所の地面と同じ高さ。
# 縁の上端も水平で砂の面+0.15（腰掛け）。外の地面が縁の上端より高い所（坂の上）は、丸太φ0.15を横に積んだ土留め（上端を地面にそろえる）。
# 地形（90）は砂場と縁の外の線まで切り欠く（上の _holes）
import sys as _sys1
_sys1.path.insert(0, os.path.join(gc.ROOT, "model", "build", "south"))
import katachi as _K1
from shapely.geometry import MultiPolygon as _MP1
_sd = G["SAND"]["poly"]; _SPG = Polygon(_sd).buffer(0)
_ob = list(_SPG.exterior.coords)[:-1]; _ol = []
for (a0_, d0_), (a1_, d1_) in zip(_ob, _ob[1:] + _ob[:1]):
    n_ = max(1, int(math.ceil(math.hypot(a1_ - a0_, d1_ - d0_) / 0.1)))
    _ol += [(a0_ + (a1_ - a0_) * t / n_, d0_ + (d1_ - d0_) * t / n_) for t in range(n_)]
_RW = 0.15                                              # 縁・丸太の幅（φ0.15）
_sz = min(H(*q) for q in _ol)                           # 砂の面＝縁のいちばん低い所の地面
_st = _sz + 0.15                                        # 縁の上端（腰掛け）
_segs = []                                              # (始め, 終わり, 外向きの法線, 段の数)
for i_, q0 in enumerate(_ol):
    q1 = _ol[(i_ + 1) % len(_ol)]; ta, td = q1[0] - q0[0], q1[1] - q0[1]; ln = math.hypot(ta, td) or 1
    na, nd = -td / ln, ta / ln
    mid = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
    if _SPG.contains(Point(mid[0] + na * 0.05, mid[1] + nd * 0.05)):
        na, nd = -na, -nd
    ho = H(mid[0] + na * _RW, mid[1] + nd * _RW)        # 縁の外の地面
    _segs.append((q0, q1, (na, nd), 1 if ho <= _st else max(1, int(round((ho - _sz) / _RW)))))
slab(_sd, _sz - 0.3, _sz, 95, f"砂場の砂（約12 m²、砂の面は水平 GL{_sz:+.2f}、掘り込み）")
_RING = _SPG.buffer(_RW, join_style=1).difference(_SPG)
def _wedge(q0, q1, nv, ext=0.02):
    ta, td = q1[0] - q0[0], q1[1] - q0[1]; ln = math.hypot(ta, td) or 1; ea, ed = ta / ln * ext, td / ln * ext
    a0, a1 = (q0[0] - ea, q0[1] - ed), (q1[0] + ea, q1[1] + ed)
    return Polygon([(a0[0] - nv[0] * 0.05, a0[1] - nv[1] * 0.05), (a1[0] - nv[0] * 0.05, a1[1] - nv[1] * 0.05),
                    (a1[0] + nv[0] * 0.3, a1[1] + nv[1] * 0.3), (a0[0] + nv[0] * 0.3, a0[1] + nv[1] * 0.3)])
from shapely.ops import unary_union as _uu1
_seat = _uu1([_wedge(q0, q1, nv) for q0, q1, nv, k_ in _segs if k_ == 1]).intersection(_RING)
def _w_mm(pg):
    def _r(cs): return [tuple(v * 1000 for v in gc.X(a, d)) for a, d in cs]
    out = [Polygon(_r(g.exterior.coords), [_r(h.coords) for h in g.interiors]) for g in getattr(pg, "geoms", [pg]) if g.geom_type == "Polygon"]
    return _MP1(out) if len(out) > 1 else out[0]
def _w3s(a, d, z):
    q = P3(a, d, z); return (q.X, q.Y, q.Z)
_K1.add(m, _K1.ita(_w_mm(_seat), (_sz - 0.15) * 1000 + GL, _st * 1000 + GL, simplify=2), LAY["95r"],
        name=f"砂場の縁（丸太の腰掛け、幅 0.15、上端は水平 GL{_st:+.2f}＝砂の面+0.15）")
# 坂の上の土留め：同じ段の数の続きごとに、0.6 m ほどの弦に分けて丸太（円柱φ0.15）を横に積む（いちばん下の一本は砂の下に埋める）
_runs = []
for q0, q1, nv, k_ in _segs:
    if k_ >= 2 and _runs and _runs[-1][0] == k_ and _runs[-1][1][-1] == q0:
        _runs[-1][1].append(q1); _runs[-1][2].append(nv)
    elif k_ >= 2:
        _runs.append([k_, [q0, q1], [nv]])
if len(_runs) > 1 and _runs[0][1][0] == _runs[-1][1][-1] and _runs[0][0] == _runs[-1][0]:
    _runs[0] = [_runs[0][0], _runs[-1][1] + _runs[0][1][1:], _runs[-1][2] + _runs[0][2]]; _runs.pop()
_nlog = 0
for k_, qs, nvs in _runs:
    step = max(1, int(round(0.6 / 0.1)))
    for i0 in range(0, len(qs) - 1, step):
        i1 = min(i0 + step, len(qs) - 1)
        nv = np.mean(nvs[i0:i1], axis=0); nv = nv / (np.linalg.norm(nv) or 1)
        q0, q1 = np.array(qs[i0]), np.array(qs[i1]); tv = (q1 - q0) / (np.linalg.norm(q1 - q0) or 1)
        e0 = q0 + nv * _RW / 2 - tv * 0.04; e1 = q1 + nv * _RW / 2 + tv * 0.04
        for c_ in range(k_ + 1):
            zc = _sz - _RW / 2 + c_ * _RW
            _K1.add(m, _K1.enchu(_w3s(*e0, zc), _w3s(*e1, zc), _RW / 2 * 1000), LAY["95r"],
                    name=f"砂場の土留め（丸太φ0.15を横に{k_}段、上端は地面にそろえる GL{_sz + k_ * _RW:+.2f}）"); _nlog += 1
print(f"砂場：砂の面 GL{_sz:+.3f}、縁の上端 GL{_st:+.3f}、縁の外の地面 {min(H(q0[0] + nv[0] * _RW, q0[1] + nv[1] * _RW) for q0, q1, nv, k_ in _segs):+.3f}〜"
      f"{max(H(q0[0] + nv[0] * _RW, q0[1] + nv[1] * _RW) for q0, q1, nv, k_ in _segs):+.3f}、土留めの丸太 {_nlog} 本（段の数 {sorted(set(k_ for k_, _, _ in _runs))}）")
_GG = gc.grain_geom()                         # 11-01：乳児の床の噴水の隣の砂浜ビーチ（噴水の円に沿う三日月）。粒の面は水平
_gp = _GG["sand"]; _go = _GG["frame"]; _gz = gmax(_gp) + 0.02
_ga = Polygon(_gp).area
slab(_gp, _gz - 0.1, _gz, 95, f"粒の遊び場の粒（1〜2 mm、砂浜、噴水に沿う三日月約{_ga:.1f} m²）")
slab(_go, gmin(_go) - 0.1, gmax(_gp) + 0.10, "95r", "粒の遊び場の木の縁（幅 0.15・h0.10、2歳がまたいで入れる）", hole_ad=_gp)   # 10-31 ユーザー：h0.25→0.10
_r0, _r1 = _GG["roller"]; _rz = max(H(*_r0), H(*_r1)) + 0.1
tube_ad(_r0, _r1, _rz, 0.1, "95r", f"帆布を巻いた棒（φ0.2、長さ {math.dist(_r0, _r1):.1f}、芝の帯の側）")
_bz = H(*G["BOWL"]["c"])                     # ひみつのたにの底（11-01：直径2 mの平ら、砂利。地形は芝なので素材を分ける）
vcyl(G["BOWL"]["c"], G["BOWL"].get("flat_r", 1.0), _bz - 0.03, _bz + 0.01, "90g", f"ひみつのたにの底（砂利、お話の輪、直径{2 * G['BOWL'].get('flat_r', 1.0):.1f}）")
B = G["BOWL"]; curve_ad(ell(B["c"], (B["r"], B["r"])), "90l", "ひみつのたに（輪郭、お話の輪、縁取りで水を入れない）", close=True)   # くぼみは地形（90）
W = G["WILLOW"]; _wp = ring_pts(W["c"], W["r"], 24)
dome(W["c"], W["r"], 2.0, gmin(_wp) - 0.05, "94c", "柳の家（生きたヤナギのドームφ3・h2.0）")   # 生きた木なので樹冠のレイヤー（10-28）

# ---- 95w・95m雲梯（11-01ユーザー：鉄棒をやめて雲梯に）。katachiの円柱（柱・握り棒・段）と角材（桁） ----
# 握り棒の高さは両端の地面を結んだ線 + grip_h（斜面でも地面からそろう、桁はまっすぐ）
import katachi as _KU
BR = G.get("BAR")
if BR:
    cb, sb = math.cos(math.radians(BR["rot"])), math.sin(math.radians(BR["rot"]))
    br = lambda u, v: (BR["c"][0] + u * cb - v * sb, BR["c"][1] + u * sb + v * cb)
    hL, hW = BR["L"] / 2, BR["W"] / 2
    bb, bh = BR["beam"]; pr = BR["post_d"] / 2
    vb = hW + bb / 2                                   # 桁の芯（握り棒は桁の内側に渡す）
    vp = vb + bb / 2 + pr                              # 柱の芯（桁の外に添える）
    g0, g1 = H(*br(-hL, 0)), H(*br(hL, 0))
    zg = lambda u: g0 + (g1 - g0) * (u + hL) / (2 * hL) + BR["grip_h"]     # 握り棒の芯の高さ（GLからのm）
    def w3(u, v, z):
        q = P3(*br(u, v), z=z); return (q.X, q.Y, q.Z)
    for su in (-1, 1):
        for sv in (-1, 1):
            u_, v_ = su * hL, sv * vp; gp = H(*br(u_, v_))
            zt = zg(u_) + bh / 2 + BR["post_over"]
            _KU.add(m, _KU.enchu(w3(u_, v_, gp - 0.05), w3(u_, v_, zt), pr * 1000), LAY["95w"],
                    name=f"雲梯の柱（栗の丸太φ{BR['post_d'] * 1000:.0f}、無塗装、根もとは鋼の脚、h{zt - gp:.2f}）")
        for k_, hs in enumerate(BR["steps"]):           # 両端のはしご：端の2本の柱のあいだに段
            gs = (H(*br(su * hL, -vp)) + H(*br(su * hL, vp))) / 2
            _KU.add(m, _KU.enchu(w3(su * hL, -vp + pr, gs + hs), w3(su * hL, vp - pr, gs + hs), BR["grip_d"] / 2 * 1000), LAY["95m"],
                    name=f"雲梯の登る段（ステンレスφ{BR['grip_d'] * 1000:.0f}、地面から{hs:.2f}）")
    for sv in (-1, 1):                                 # 上の桁（長手の2本の梁、栗の角材）
        u0_, u1_ = -hL - pr, hL + pr
        _KU.add(m, _KU.bou(w3(u0_, sv * vb, zg(u0_)), w3(u1_, sv * vb, zg(u1_)), bb * 1000, bh * 1000), LAY["95w"],
                name=f"雲梯の桁（栗の角材{bb * 1000:.0f}×{bh * 1000:.0f}）")
    n_g = int(round(2 * (hL - 0.15) / BR["grip_pitch"])) + 1
    for i in range(n_g):
        u_ = -(n_g - 1) * BR["grip_pitch"] / 2 + i * BR["grip_pitch"]
        _KU.add(m, _KU.enchu(w3(u_, -vb + bb / 2, zg(u_)), w3(u_, vb - bb / 2, zg(u_)), BR["grip_d"] / 2 * 1000), LAY["95m"],
                name=f"雲梯の握り棒（ステンレスφ{BR['grip_d'] * 1000:.0f}、地面から{zg(u_) - H(*br(u_, 0)):.2f}）")
    print(f"雲梯：握り棒{n_g}本、地面から両端{zg(-(n_g - 1) * BR['grip_pitch'] / 2) - H(*br(-(n_g - 1) * BR['grip_pitch'] / 2, 0)):.2f}・"
          f"{zg((n_g - 1) * BR['grip_pitch'] / 2) - H(*br((n_g - 1) * BR['grip_pitch'] / 2, 0)):.2f}、真ん中{zg(0) - H(*br(0, 0)):.2f}")

# ---- 95nネットのハンモック（11-01ユーザー）：エノキとホオノキの幹に吊る（育った後の形）。ネット＝薄い円柱、縁の輪＝管（円柱の輪）、吊りロープ＝円柱（katachi） ----
HM = G.get("HAMMOCK")
if HM:
    zn = H(*HM["c"]) + HM["h"]                         # ネットの上面（水平）
    xc, yc = gc.X(*HM["c"]); xc, yc = xc * 1000, yc * 1000
    _KU.add(m, _KU.enchu((xc, yc, (zn - HM["t"]) * 1000 + GL), (xc, yc, zn * 1000 + GL), HM["r"] * 1000), LAY["95n"],
            name=f"ネットのハンモック（麻のロープの網φ{HM['r'] * 2:.1f}、地面から約{HM['h']:.1f}）")
    _KU.add(m, _KU.enchu((xc, yc, (zn - HM["rim_d"]) * 1000 + GL), (xc, yc, zn * 1000 + GL), (HM["r"] + HM["rim_d"]) * 1000, rin=HM["r"] * 1000), LAY["95n"],
            name=f"ネットの縁の輪（太いロープφ{HM['rim_d'] * 1000:.0f}）")
    for tr in HM["trees"]:
        dx, dy = tr[0] - HM["c"][0], tr[1] - HM["c"][1]; th = math.atan2(dy, dx); dist = math.hypot(dx, dy)
        for k_, sg in enumerate((-1, 1)):
            q = th + sg * math.radians(HM["rope_spread"])
            p0 = (HM["c"][0] + (HM["r"] + HM["rim_d"] / 2) * math.cos(q), HM["c"][1] + (HM["r"] + HM["rim_d"] / 2) * math.sin(q))
            p1 = (HM["c"][0] + (dist - TRUNK_R["big"]) * math.cos(th), HM["c"][1] + (dist - TRUNK_R["big"]) * math.sin(th))
            z1 = H(*tr[:2]) + HM["rope_h"][k_]
            q0 = P3(*p0, z=zn - HM["rim_d"] / 2); q1 = P3(*p1, z=z1)
            _KU.add(m, _KU.enchu((q0.X, q0.Y, q0.Z), (q1.X, q1.Y, q1.Z), HM["rope_d"] / 2 * 1000), LAY["95n"],
                    name=f"ハンモックの吊りロープ（φ{HM['rope_d'] * 1000:.0f}、幹の地上{HM['rope_h'][k_]:.1f}へ）")
    print(f"ハンモック：ネットの上面GL{zn:+.2f}、中心の地面から{HM['h']:.2f}")

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

# ---- 95k・95h 木の切り株（11-01 ユーザー：園庭の平らな所に、しずかのもりに5・だいさんかくに10）。kirikabu（上の関数）
_ns = 0
for _s in G.get("STUMPS", {}).get("items", []):
    _x, _y = gc.X(_s[0], _s[1])
    _td = math.degrees(math.atan2(*(np.array(gc.X(_s[0] + math.cos(math.radians(_s[5])), _s[1] + math.sin(math.radians(_s[5])))) - np.array([_x, _y]))[::-1])) if _s[4] else 0.0
    _ns += kirikabu(m, (_x * 1000, _y * 1000), H(_s[0], _s[1]) * 1000 + GL, _s[2] * 1000, _s[3] * 1000, LAY["95k"], LAY["95h"],
                    tilt=_s[4], tilt_dir=_td, roots=_s[6], seed=int(_s[0] * 10 + _s[1]), name=f"切り株（{_s[7]}、径{_s[2]:.2f}・h{_s[3]:.2f}）")
print(f"切り株：{len(G.get('STUMPS', {}).get('items', []))} 個、物 {_ns}")
# ---- 95k・95h 横たわる丸太（11-03 ユーザー：切り株と同じ考えで約12、長さ1.2〜3.0・径0.2〜0.4、少し沈める）。maruta（kirikabu の下の関数）
_nl = 0
for _k, _l in enumerate(G.get("LOGS", {}).get("items", [])):
    _ca, _sa = math.cos(math.radians(_l[4])), math.sin(math.radians(_l[4]))
    _e = [(_l[0] + _sg * _l[2] / 2 * _ca, _l[1] + _sg * _l[2] / 2 * _sa) for _sg in (-1, 1)]
    _p = [(*[v * 1000 for v in gc.X(*q)], H(*q) * 1000 + GL) for q in _e]
    _nl += maruta(m, _p[0], _p[1], _l[3] * 1000, LAY["95k"], LAY["95h"], sink=_l[5] * 1000, seed=_k + 7,
                  name=f"丸太（{_l[6]}、長さ{_l[2]:.1f}・径{_l[3]:.2f}）")
print(f"丸太：{len(G.get('LOGS', {}).get('items', []))} 本、物 {_nl}")

# ---- 96w 境の石積み（11-01 ユーザー）：てんぐのたにの南東の口から川沿いの柵の際まで、大地を上げた区間の境の内側に。
# 境に沿う立面の輪郭（下は根入れ、上端は境の地面に沿う折れ線）を厚さ t だけ内へ押し出した一つの押し出し（katachi）
_WL = G.get("DAICHI", {}).get("WALL")
if _WL:
    import katachi as _KW
    _wa = np.arange(G["DAICHI"]["valley"]["a_end"][0] - 0.5, 56.0, 0.25)
    _wh = np.array([H(a_, 0.0) for a_ in _wa]); _on = np.nonzero(_wh > _WL["h_min"])[0]
    _wa, _wh = _wa[_on[0]:_on[-1] + 1], _wh[_on[0]:_on[-1] + 1]
    _a0 = float(_wa[0]); _ue = np.array([*G["UE"], 0.0]); _nb = np.array([*G["NB"], 0.0])
    _prof = [(0.0, -_WL["embed"] * 1000)] + [((a_ - _a0) * 1000, z_ * 1000) for a_, z_ in zip(_wa, _wh)] + [((_wa[-1] - _a0) * 1000, -_WL["embed"] * 1000)]
    _x0, _y0 = gc.X(_a0, 0.0)
    _sg = 1.0 if np.dot(np.cross(_ue, [0, 0, 1]), -_nb) > 0 else -1.0     # 押し出す向き＝園庭の内（d+）
    _KW.add(m, _KW.oshidashi(_prof, O=(_x0 * 1000, _y0 * 1000, GL), X=_ue, Y=(0, 0, 1), h=_sg * _WL["t"] * 1000), LAY["96w"],
            name=f"境の石積み（空石積みの土留め、a{_a0:.1f}〜{_wa[-1]:.1f}、上端は境の地面 最大 +{_wh.max():.2f}、厚さ {_WL['t']}・根入れ {_WL['embed']}）")
    print(f"境の石積み：a{_a0:.2f}〜{_wa[-1]:.2f}（{_wa[-1] - _a0:.1f} m）、高さ 最大 {_wh.max():.2f}")

# ---- 97 車の道 ----
GN = G.get("GATE_N")
if GN:
    (ga0, gd0), (ga1, gd1) = GN["p0"], GN["p1"]
    gz = H(ga0, (gd0 + gd1) / 2)
    box(ga0 - 0.02, ga0 + 0.02, min(gd0, gd1), max(gd0, gd1), gz, gz + GN["h"], 97, "北の口の木戸 h1.2（庭の側へ開く、掛け金は外側の高い所）")

curve_ad(G["VEHICLE"]["line"], "90l", "剪定・搬入の車の道（道すじ、芝の保護材、幅2.5）")
# 10-31：のぞきの生垣はやめた（柵ぎわ約1 mには踏み台になる物を置かない）

# ---- 92f 床の噴水の水（10-31、プレゼンの準備の項 20261031-1541-present：水遊び場の絵で噴き上がる水を見せる） ----
# ふだんは非表示（コットと同じ：レイヤーを Visible=False で作る。図・配置図・模型は非表示のレイヤーを読まない）。
# 名前に「噴水の水」（プレゼンの render_common.py がこの語で昼の絵だけ点ける）。形は katachi の円柱（押し出し）
import sys as _sys
_sys.path.insert(0, os.path.join(gc.ROOT, "model", "build", "south"))
import katachi as KT
_lw = r.Layer(); _lw.Name = "92f_園庭_床の噴水の水（噴き上がる水・雨のカーテン・泡。ふだん非表示、絵のときだけ）"
_lw.Color = (150, 200, 230, 255); _lw.Visible = False; LAY["92f"] = m.Layers.Add(_lw)


def _w3(a, d, z):
    q = P3(a, d, z); return (q.X, q.Y, q.Z)


_rng = np.random.default_rng(31)
# 11-01（ユーザー、項 20261101-1939-present：モノクロの絵でも噴水と分かるリアルさ）：水は決めてある自由な形（閉じたメッシュ、地形・雨の川と同じ扱い）。
# 水の柱は根もとが細く上で太る円錐台、頂で開いて落ちる小さな水の粒の冠。座標は世界（mm）。
_p = (1 + 5 ** 0.5) / 2   # 正二十面体（水の粒、頂点12）
_ICO_V = np.array([(-1, _p, 0), (1, _p, 0), (-1, -_p, 0), (1, -_p, 0), (0, -1, _p), (0, 1, _p), (0, -1, -_p), (0, 1, -_p),
                   (_p, 0, -1), (_p, 0, 1), (-_p, 0, -1), (-_p, 0, 1)], float)
_ICO_V /= np.linalg.norm(_ICO_V[0])
_ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
          (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]


class _Wm:
    """閉じたメッシュを貯める（粒・円錐台・短い線分を一つの物に）"""
    def __init__(self): self.m = r.Mesh(); self.n = 0
    def _v(self, P):
        for x, y, z in P: self.m.Vertices.Add(float(x), float(y), float(z))
        k = self.n; self.n += len(P); return k
    def drop(self, c, rad, sz=1.0):
        k = self._v(np.asarray(c) + _ICO_V * [rad, rad, rad * sz])
        for f in _ICO_F: self.m.Faces.AddFace(k + f[0], k + f[1], k + f[2])
    def frustum(self, p0, p1, r0, r1, seg=8):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; d = d / np.linalg.norm(d)
        X = np.cross([0, 1., 0] if abs(d[0]) > 0.9 else [1., 0, 0], d); X /= np.linalg.norm(X); Y = np.cross(d, X)
        t = np.linspace(0, 2 * math.pi, seg, endpoint=False); ring = np.outer(np.cos(t), X) + np.outer(np.sin(t), Y)
        k = self._v(np.vstack([p0 + ring * r0, p1 + ring * r1, [p0, p1]])); c0, c1 = k + 2 * seg, k + 2 * seg + 1
        for i in range(seg):
            j = (i + 1) % seg
            self.m.Faces.AddFace(k + i, k + j, k + seg + j, k + seg + i)
            self.m.Faces.AddFace(c0, k + j, k + i); self.m.Faces.AddFace(c1, k + seg + i, k + seg + j)


def _jet(W, base, h, r0, r1, tilt, n_cr, rc):
    """一本の噴き上がる水：base（mm）から高さ h（mm）、傾き tilt（度）。頂に n_cr 個の粒の冠（外へ開いて下がる）、rc は粒の半径の目安"""
    az = _rng.uniform(0, 2 * math.pi); tl = math.radians(tilt)
    d = np.array([math.sin(tl) * math.cos(az), math.sin(tl) * math.sin(az), math.cos(tl)])
    top = np.asarray(base, float) + d * h
    W.frustum(base, top, r0, r1)
    W.drop(top + d * r1 * 0.6, r1 * 1.15, 1.3)                 # 頂のふくらみ
    a0 = _rng.uniform(0, 2 * math.pi)
    for i in range(n_cr):
        q = a0 + 2 * math.pi * i / n_cr + _rng.uniform(-0.3, 0.3)
        sp = _rng.uniform(1.6, 3.2) * r1 + h * _rng.uniform(0.02, 0.05)   # 外へ開く
        dz = _rng.uniform(0.2, 0.9) * sp                                   # 少し下がる
        W.drop(top + [sp * math.cos(q), sp * math.sin(q), -dz], rc * _rng.uniform(0.6, 1.0), 1.25)


def _scatter(c, R, n, dmin, ok):
    """円（中心 c、半径 R、m）の中に、たがいに dmin 以上離れたばらつく点を n 個まで（ダーツ投げ）"""
    pts = []
    for _ in range(40000):
        if len(pts) >= n: break
        rr, q = R * math.sqrt(_rng.uniform()), _rng.uniform(0, 2 * math.pi)
        p = (c[0] + rr * math.cos(q), c[1] + rr * math.sin(q))
        if ok(p) and all(math.hypot(p[0] - s[0], p[1] - s[1]) >= dmin for s in pts): pts.append(p)
    return pts


# 3〜5歳の床の噴水：高さ約0.10 m（0.07〜0.13、11-03 ユーザー：前は0.3〜0.6）、約150本、円の全面にばらつかせる（縁から0.15内）。根もと半径2.5〜3.5 mm→上5〜7 mm、頂の小さな粒の冠
_rg = G["SHOWER"]["ring"]; _zr = H(*_rg["c"]) + _rg["h"]
_rpost = _rg.get("posts", [G["SHOWER"]["c"]]) + [G["SHOWER"]["c"]]
_ftrap = None
if F.get("sand_trap") and F.get("drain"):
    _v = np.array(F["drain"]) - np.array(F["c"]); _v = _v / (np.linalg.norm(_v) or 1)
    _ftrap = np.array(F["c"]) + _v * (F["r"][0] - 0.05 - F["sand_trap"]["w"] / 2)


def _f_ok(p):
    if min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in _rpost) < 0.2: return False      # あめのわの柱・シャワーの柱（120角）
    if math.hypot(p[0] - F["drain"][0], p[1] - F["drain"][1]) < 0.25: return False         # 排水口
    if _ftrap is not None and max(abs(p[0] - _ftrap[0]), abs(p[1] - _ftrap[1])) < F["sand_trap"]["w"] / 2 + 0.08: return False   # 砂だめの蓋
    if abs(math.hypot(p[0] - _rg["c"][0], p[1] - _rg["c"][1]) - _rg["r"]) < 0.05: return False   # 雨のカーテンの真下
    return True


_fj = _scatter(F["c"], F["r"][0] - 0.15, 150, 0.21, _f_ok)
_nf = 0; _hs = []
for k_ in range(0, len(_fj), 10):                                          # 10本ずつ一つの物に
    W = _Wm()
    for q in _fj[k_:k_ + 10]:
        hj = float(_rng.uniform(0.07, 0.13)); _hs.append(hj)
        _jet(W, _w3(*q, _fz), hj * 1000, _rng.uniform(2.5, 3.5), _rng.uniform(5.0, 7.0), _rng.uniform(0, 6),
             int(_rng.integers(5, 8)), 3.0); _nf += 1
    KT.add(m, W.m, LAY["92f"], name=f"床の噴水の水の柱（{len(_fj[k_:k_ + 10])}本、h0.07〜0.13、根もとr2.5〜3.5・上r5〜7 mm、頂の小さな粒の冠）")
# 雨のカーテン：輪の噴き口から床まで、途中で切れた細い粒の列（半径 1〜1.5 mm の短い線分を縦に、11-03 ユーザー：前は2〜3 mm）
def _curtain(c_ad, R, n, z_floor, z_ring, name, avoid=()):
    nc = 0
    for k_ in range(n):
        q_ = 2 * math.pi * k_ / n
        a_, d_ = c_ad[0] + R * math.cos(q_), c_ad[1] + R * math.sin(q_)
        if any(math.hypot(a_ - pp[0], d_ - pp[1]) < 0.08 for pp in avoid): continue
        p0 = np.array(_w3(a_, d_, z_floor)); z1 = _w3(a_, d_, z_ring - 0.03)[2]; W = _Wm(); z = z1
        rw = _rng.uniform(1.0, 1.5)
        while z - p0[2] > 20:
            L = min(_rng.uniform(30, 90) * (0.5 + (z - p0[2]) / (z1 - p0[2])), z - p0[2])   # 上ほど長い筋、下ほど短い粒
            W.frustum(p0 + [0, 0, z - L - p0[2]], p0 + [0, 0, z - p0[2]], rw, rw, 6); nc += 1
            z -= L + _rng.uniform(15, 45)
        KT.add(m, W.m, LAY["92f"], name=name)
    return nc


_ncur = _curtain(_rg["c"], _rg["r"], _rg["n"], _fz, _zr, "あめのわの雨のカーテン（途中で切れた細い粒の列、r1〜1.5 mm）")
# 0〜2歳の床の噴水：噴き口ごとに低い泡（高さ約0.05＝0.03〜0.07、11-03 ユーザー：前は0.10〜0.20。低い円錐台＋頂の小さな粒）
_ns = 0; _hb = []
if _js := SP.get("jets", 0):
    W = _Wm(); _strap = None
    if SP.get("sand_trap") and SP.get("drain"):
        _v = np.array(SP["drain"]) - np.array(SP["c"]); _v = _v / (np.linalg.norm(_v) or 1)
        _strap = np.array(SP["c"]) + _v * (SP["r"][0] - 0.05 - SP["sand_trap"]["w"] / 2)
    for ja in np.arange(-SP["r"][0], SP["r"][0] + 0.01, _js):
        for jd in np.arange(-SP["r"][0], SP["r"][0] + 0.01, _js):
            if math.hypot(ja, jd) < SP["r"][0] - 0.3:
                hb = float(_rng.uniform(0.03, 0.07)); a_, d_ = SP["c"][0] + ja, SP["c"][1] + jd
                if _strap is not None and max(abs(a_ - _strap[0]), abs(d_ - _strap[1])) < SP["sand_trap"]["w"] / 2 + 0.08: continue   # 砂だめの蓋の上は外す
                _jet(W, _w3(a_, d_, _sz), hb * 1000, _rng.uniform(8, 11), _rng.uniform(14, 19), _rng.uniform(0, 4),
                     int(_rng.integers(6, 9)), 5.0); _ns += 1; _hb.append(hb)
    KT.add(m, W.m, LAY["92f"], name="乳児の床の噴水の泡（低い円錐台h0.03〜0.07＋頂の粒）")
# 霧のわ（11-03 ユーザー：霧が筒に見える）：霧をやめ、あめのわと同じ細い雨のカーテン。噴き口の数はあめのわの割合（輪の長さあたり）で
_nmist = 0; _nmn = 0
if SP.get("mist"):
    _ms = SP["mist"]; _nmn = int(round(_rg["n"] * _ms["r"] / _rg["r"]))
    _nmist = _curtain(SP["c"], _ms["r"], _nmn, _sz, H(*SP["c"]) + _ms["h"],
                      "霧のわの雨のカーテン（霧の代わりに細い雨、途切れた粒の列、r1〜1.5 mm）")
print(f"噴水の水{_nf}本（h{min(_hs):.3f}〜{max(_hs):.3f}）・雨のカーテン{_rg['n']}本（線分{_ncur}）・泡{_ns}（h{min(_hb or [0]):.3f}〜{max(_hb or [0]):.3f}）・霧のわの雨{_nmn}本（線分{_nmist}）")

out = os.path.join(gc.ROOT, "model", "sodachiya_garden_layers.3dm")
m.Write(out, 7)
print("wrote", out, "contours", nc, "plates", npl, "trees", len(G["TREES"]))
