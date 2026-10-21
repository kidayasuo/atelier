"""園庭（だいさんかく・しずかのもり）のたたき台  配置 1/200＋断面 1/100（A2 縦）
読むもの：data/garden.json（園庭の寸法）、model/sodachiya_exact_mesh.3dm（敷地・建物）
出すもの：out/sodachiya_garden_01.pdf / .png（出力先は環境変数 OUT で変えられる）
"""
import math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle, Ellipse, Rectangle, FancyArrowPatch
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
import garden_common as gc
from garden_common import G, X, XS, AD, UV, d_edge

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["hatch.linewidth"] = 0.4
OUT = os.environ.get("OUT", os.path.join(gc.ROOT, "out"))
MM = 1 / 25.4
PW, PH = 420, 594                                     # A2 縦
fig = plt.figure(figsize=(PW * MM, PH * MM))

C = dict(grass="#F1F3E6", shizu="#DCE7D0", field="#F4F1E0", water="#7FB7D9", waterL="#CFE6F3", sand="#EADCB5",
         bld="#E9E6E0", bldE="#8A847A", engawa="#F4EBDD", tree="#9DBB82", treeE="#6F8F57", ever="#6E9466",
         fruit="#D9A35B", hut="#D8C3A0", red="#C8463D", path="#C9B89A", ink="#222222", gray="#777777",
         hidden="#C8463D", cont="#8A7A5C", wood="#9B7653")

# ---------------- 3dm から ----------------
LAY = gc.read_mesh_layers(["10_本館_屋根", "20_西館_屋根", "14_本館_外縁側（土足 −150）", "13_本館_内縁側（はだし ±0）",
                           "35_機械室（本館の北）", "62_外構_みなみのさんかく（乳児の園庭）", "63_外構_避難の帯",
                           "60_外構_柵（一本の線の延長）", "64_外構_ポーチ", "02_敷地_高野川の護岸（現況、寸法は仮）"])
GARDEN = gc.garden_poly()

# ---------------- 地形の格子（a, d） ----------------
STEP = 0.25
GA = np.arange(10.0, 57.01, STEP); GD = np.arange(-1.0, 37.01, STEP)
AA, DD = np.meshgrid(GA, GD)
HH = gc.height(AA, DD)
# 小川の川床とたまりは別に描く（地形は GL のまま）


def h_at(a, d):
    from scipy.ndimage import map_coordinates
    a = np.atleast_1d(np.asarray(a, float)); d = np.atleast_1d(np.asarray(d, float))
    r = map_coordinates(HH, [(d - GD[0]) / STEP, (a - GA[0]) / STEP], order=1, mode="nearest")
    return r if r.size > 1 else r[0]


# ---------------- 死角（先生の目から子どもの頭が見えない所） ----------------
H = G["HUT"]
HUT_AD = Polygon([(H["a"][0], H["d"][0]), (H["a"][1], H["d"][0]), (H["a"][1], H["d"][1]), (H["a"][0], H["d"][1])])
teachers = []
for a, d, lab in G["TEACHERS"]["pts"]:
    if d is None:
        d = d_edge(a) - 0.7; z = 0.15                  # 外縁側（土足 −150 ＝ GL+150）
    else:
        z = float(h_at(np.array(a), np.array(d)))
    teachers.append((a, d, z + G["TEACHERS"]["eye"], lab))
CH = G["TEACHERS"]["child"]
VA = np.arange(12.0, 56.0, 0.5); VD = np.arange(1.0, 36.0, 0.5)
hidden = []
gpoly_ad = Polygon([AD(*p) for p in GARDEN.exterior.coords])
hut_line = HUT_AD.buffer(0.01)
for a in VA:
    for d in VD:
        if not gpoly_ad.contains(Point(a, d)) or d > d_edge(a) - 0.3:
            continue
        zt = float(h_at(np.array(a), np.array(d))) + CH
        seen = False
        for ta, td, tz, _ in teachers:
            L = math.hypot(a - ta, d - td)
            n = max(2, int(L / 0.25))
            s = np.linspace(0.04, 0.96, n)
            pa = ta + (a - ta) * s; pd = td + (d - td) * s
            zr = tz + (zt - tz) * s
            ground = h_at(pa, pd)
            if np.any(ground > zr):
                continue
            if LineString([(ta, td), (a, d)]).intersects(HUT_AD):
                continue
            seen = True; break
        if not seen:
            hidden.append(Polygon([(a - .25, d - .25), (a + .25, d - .25), (a + .25, d + .25), (a - .25, d + .25)]))
HIDDEN = unary_union(hidden).buffer(0.05).buffer(-0.05) if hidden else Polygon()


# ---------------- 描くための道具 ----------------
def poly(ax, g, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1.0):
    if g is None or g.is_empty:
        return
    gs = [g] if g.geom_type == "Polygon" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]
    for q in gs:
        ax.add_patch(MPoly(np.array(q.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
        for r in q.interiors:
            ax.add_patch(MPoly(np.array(r.coords), closed=True, fc="white" if fc != "none" else "none", ec=ec, lw=lw * 0.6, zorder=z + 0.01))


def P(pts):
    return Polygon(XS(pts))


def line(ax, pts, lw=0.5, c="black", ls="-", z=3, **kw):
    pts = np.array(pts); ax.plot(pts[:, 0], pts[:, 1], lw=lw, c=c, ls=ls, zorder=z, solid_capstyle="round", **kw)


def T(ax, p, s, size=6, c=C["ink"], ha="center", va="center", rot=0, z=20, **kw):
    kw.setdefault("clip_on", True)
    ax.text(p[0], p[1], s, fontsize=size, color=c, ha=ha, va=va, rotation=rot, zorder=z, **kw)


def ell_ad(c, r, rot=0, n=48):
    t = np.linspace(0, 2 * np.pi, n)
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [(c[0] + r[0] * math.cos(q) * ca - r[1] * math.sin(q) * sa, c[1] + r[0] * math.cos(q) * sa + r[1] * math.sin(q) * ca) for q in t]


# 紙の上の mm で軸を置く
def axes_mm(x, y, w, h):
    return fig.add_axes([x / PW, 1 - (y + h) / PH, w / PW, h / PH])


# ================= 配置 1/200 =================
X0, X1, Y0, Y1 = 1.0, 38.0, -69.0, -6.0               # m（3dm の xy）
SC = 1000 / 200                                       # 1 m = 5 mm
ax = axes_mm(14, 40, (X1 - X0) * SC, (Y1 - Y0) * SC)
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.axis("off")
clip = Rectangle((X0, Y0), X1 - X0, Y1 - Y0, transform=ax.transData)

# 敷地・川
poly(ax, gc.SITE, fc="white", ec=C["ink"], lw=0.9, z=0.5)
for k in ("02_敷地_高野川の護岸（現況、寸法は仮）",):
    if k in LAY:
        poly(ax, LAY[k], fc="#F0F3F5", ec="#9AA7B0", lw=0.3, z=0.4)
# 園庭の地
poly(ax, GARDEN, fc=C["grass"], ec="none", z=1)
bank_line = LineString(G["BANK"]["line"])
shizu_ad = Polygon([tuple(p) for p in G["BANK"]["line"]] + [(56.0, 18.2), (56.0, 37.0), (d_a := 53.6, 36.0)] + [(a, d_edge(a)) for a in np.linspace(53.4, 40.6, 20)])
SHIZU = P(list(shizu_ad.exterior.coords)).intersection(GARDEN)
poly(ax, SHIZU, fc=C["shizu"], ec="none", z=1.1)

# 建物
for k, fc in (("20_西館_屋根", C["bld"]), ("10_本館_屋根", C["bld"]), ("35_機械室（本館の北）", C["bld"])):
    if k in LAY:
        poly(ax, LAY[k], fc=fc, ec=C["bldE"], lw=0.6, z=5)
for k in ("14_本館_外縁側（土足 −150）", "13_本館_内縁側（はだし ±0）"):
    if k in LAY:
        poly(ax, LAY[k], fc=C["engawa"], ec=C["bldE"], lw=0.3, z=5.2)
for k in ("62_外構_みなみのさんかく（乳児の園庭）", "63_外構_避難の帯", "64_外構_ポーチ"):
    if k in LAY:
        poly(ax, LAY[k], fc="#F3F1EA", ec="#B9B2A3", lw=0.3, z=1.2)
if "60_外構_柵（一本の線の延長）" in LAY:
    poly(ax, LAY["60_外構_柵（一本の線の延長）"], fc=C["wood"], ec="none", z=5)
for (u0, u1, s) in [(0, 12, "0・1歳"), (12, 18, "2歳"), (18, 21, "医務・事務"), (21, 30, "ホール"), (30, 33, "事務"), (33, 39, "3歳"),
                    (39, 42, "便・倉庫"), (42, 48, "4歳"), (48, 51, "便・倉庫"), (51, 57, "5歳")]:
    p = UV((u0 + u1) / 2, 7.0); T(ax, p, s, 6.0 if "便" not in s else 4.8, c="#6B655B", rot=-86)
T(ax, UV(28, -11.5), "西館", 7, c="#6B655B")
T(ax, (-0.6, -4.8), "おむすび", 5, c="#6B655B")

# 車の道（芝の保護材）
veh = LineString(G["VEHICLE"]["line"]).buffer(G["VEHICLE"]["w"] / 2, cap_style=2, join_style=1)
poly(ax, P(list(veh.exterior.coords)).intersection(GARDEN), fc="none", ec="#9C8A66", lw=0.6, z=2.2, ls=(0, (4, 2)))

# 地形：等高線 0.2 m ごと（1.0 m を太く）
XX = UE0 = None
XYX = AA * G["UE"][0] - DD * G["NB"][0]; XYY = AA * G["UE"][1] - DD * G["NB"][1]
HHc = np.where(HH > 0.001, HH, np.where(HH < -0.001, HH, 0))
levels = [-0.4, -0.2] + [round(0.2 * k, 1) for k in range(1, 12)]
cs = ax.contour(XYX, XYY, HHc, levels=levels, colors=C["cont"], linewidths=[0.5 if abs(l - round(l)) < 1e-6 and l != 0 else 0.25 for l in levels], zorder=3)
gclip = MPoly(np.array(GARDEN.exterior.coords), closed=True, transform=ax.transData)
for coll in ([cs] if hasattr(cs, "set_clip_path") else cs.collections):
    coll.set_clip_path(gclip)
# 斜面の向き（転がる斜面）
m = G["MOUND"]; a0, d0 = m["top"]
ax.add_patch(Circle(X(a0, d0), 0.22, fc=C["cont"], ec="none", zorder=4))
T(ax, X(a0 + 1.6, d0 - 0.4), "+2.2", 6.5, c=C["cont"], z=21, fontweight="bold")
for dd, txt in ((3.2, "1:3"), ):
    pass
T(ax, X(a0 + 0.6, d0 + 4.4), "転がる斜面\n1:3〜1:4（芝）", 5.2, c=C["cont"], rot=-38)
T(ax, X(a0 - 0.6, d0 - 2.3), "裏の斜面 1:1.5\n（植え込み、入らない）", 4.4, c=C["cont"], rot=-38)
T(ax, X(17.4, 3.2), "+0.6", 5, c=C["cont"])
T(ax, X(50.6, 4.2), "+0.7", 5, c=C["cont"])
T(ax, X(47.0, 21.9), "土手 +0.7", 5, c=C["cont"], rot=-38)
T(ax, X(G["BOWL"]["c"][0], G["BOWL"]["c"][1] + 0.1), "−0.4", 4.6, c=C["cont"])

# 死角
poly(ax, P(list(HIDDEN.exterior.coords)) if HIDDEN.geom_type == "Polygon" else MultiPolygon([P(list(q.exterior.coords)) for q in HIDDEN.geoms]),
     fc="none", ec=C["hidden"], lw=0.3, z=3.5, hatch="////", alpha=0.75)

# 小川
s = G["STREAM"]
line(ax, XS(s["culvert"]), lw=0.8, c=C["water"], ls=(0, (3, 2)), z=6)
for ln in (s["line"], s["line2"]):
    g = LineString(XS(ln)).buffer(s["w"] / 2, cap_style=1, join_style=1)
    poly(ax, g, fc=C["water"], ec="#4C8DB8", lw=0.3, z=6)
poly(ax, P(ell_ad(G["POOL"]["c"], G["POOL"]["r"], G["POOL"]["rot"])), fc=C["waterL"], ec="#4C8DB8", lw=0.5, z=6)
poly(ax, P(ell_ad(G["POOL"]["c"], [G["POOL"]["r"][0] + 0.35, G["POOL"]["r"][1] + 0.35], G["POOL"]["rot"])), fc="none", ec="#A7A08E", lw=1.6, z=5.9, alpha=0.6)
bc = s["beach"]; poly(ax, Point(*X(bc[0], bc[1])).buffer(bc[2]), fc="#E6E1D4", ec="#A7A08E", lw=0.3, z=5.8, hatch="....")
poly(ax, P(ell_ad(G["TANK"]["c"], G["TANK"]["r"], -30)), fc="none", ec="#4C8DB8", lw=0.35, ls=(0, (2, 1.5)), z=5.7)
ax.add_patch(Circle(X(*G["PUMP"]), 0.28, fc="#4C8DB8", ec="white", lw=0.4, zorder=7))
for b in G["BRIDGES"]:
    c = b["c"]
    if b["w"] > 0:
        # 小川の向きに直交する板
        ln = LineString(s["line"] + s["line2"]); t0 = ln.project(Point(*c)); p0 = ln.interpolate(t0 - 0.4); p1 = ln.interpolate(t0 + 0.4)
        ta = np.array([p1.x - p0.x, p1.y - p0.y]); ta /= np.linalg.norm(ta)
        hw = 0.45 if b["w"] < 2 else 0.75
        q = [np.array(c) + ta * i * hw + np.array([-ta[1], ta[0]]) * j * b["w"] / 2 for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        poly(ax, P([tuple(v) for v in q]), fc="#D8D2C2" if b["w"] > 2 else C["wood"], ec="#6B655B", lw=0.4, z=6.5)
    else:
        for k in (-0.35, 0.35):
            ax.add_patch(Circle(X(c[0] + k * 0.5, c[1] + k), 0.22, fc="#D8D2C2", ec="#6B655B", lw=0.3, zorder=6.5))

# 砂場・水浴び場・粒・柳
poly(ax, P(G["SAND"]["poly"]), fc=C["sand"], ec="#A88E58", lw=0.4, z=5.5, hatch="....")
poly(ax, P(ell_ad(G["SPLASH"]["c"], G["SPLASH"]["r"], G["SPLASH"]["rot"])), fc=C["waterL"], ec="#4C8DB8", lw=0.4, z=5.5)
poly(ax, P(ell_ad(G["GRAIN"]["c"], G["GRAIN"]["r"], G["GRAIN"]["rot"])), fc="#EFE6CF", ec="#A88E58", lw=0.3, z=5.5, hatch="...")
wl = G["WILLOW"]; ax.add_patch(Circle(X(*wl["c"]), wl["r"], fc="none", ec=C["treeE"], lw=0.9, ls=(0, (1, 1)), zorder=8))

# 小屋
a_0, a_1 = H["a"]; d_0, d_1 = H["d"]
poly(ax, P([(a_0, d_0), (a_1, d_0), (a_1, d_1), (a_0, d_1)]), fc=C["hut"], ec=C["ink"], lw=0.8, z=9)
line(ax, XS([(H["split_a"], d_0), (H["split_a"], d_1)]), lw=0.5, z=9.1)
poly(ax, P([(a_0 - 0.3, d_1), (a_1 + 0.3, d_1), (a_1 + 0.3, d_1 + H["eave"]), (a_0 - 0.3, d_1 + H["eave"])]), fc="none", ec=C["ink"], lw=0.4, ls=(0, (3, 2)), z=9)
T(ax, X((a_0 + H["split_a"]) / 2, (d_0 + d_1) / 2), "便所", 5, rot=-38)
T(ax, X((H["split_a"] + a_1) / 2, (d_0 + d_1) / 2), "倉庫", 5.5, rot=-38)

# のぞき
lk = G["LOOKOUT"]; c = lk["c"]
poly(ax, P([(c[0] - lk["deck_d"], c[1] - lk["w"] / 2), (56.0, c[1] - lk["w"] / 2), (56.0, c[1] + lk["w"] / 2), (c[0] - lk["deck_d"], c[1] + lk["w"] / 2)]),
     fc="#E3D3B5", ec=C["wood"], lw=0.5, z=8)
line(ax, XS([(56.0, c[1] - lk["w"] / 2 - 0.2), (56.0, c[1] + lk["w"] / 2 + 0.2)]), lw=2.0, c=C["wood"], z=8.5)

# 木
TT = G["TREE_TYPES"]
for a, d, kind, _, note in G["TREES"]:
    r = TT[kind]["r"]; p = X(a, d)
    fc = {"ever": C["ever"], "fruit": C["fruit"]}.get(kind, C["tree"])
    ax.add_patch(Circle(p, r, fc=fc, ec=C["treeE"], lw=0.35, alpha=0.38 if kind != "ever" else 0.5, zorder=10))
    ax.add_patch(Circle(p, 0.12, fc="#5D4A36", ec="none", zorder=10.5))
    if kind == "climb":
        ax.add_patch(Circle(p, r, fc="none", ec=C["ink"], lw=0.6, ls=(0, (2, 1)), zorder=10.6))

# 先生の目
for ta, td, tz, lab in teachers:
    p = X(ta, td)
    ax.add_patch(Circle(p, 0.42, fc="white", ec=C["red"], lw=0.8, zorder=22))
    ax.add_patch(Circle(p, 0.15, fc=C["red"], ec="none", zorder=22.5))

# ニッチの番号
for k, (a, d, txt) in enumerate(G["NICHES"], 1):
    p = X(a, d)
    ax.add_patch(Circle(p, 0.75, fc="white", ec=C["ink"], lw=0.5, zorder=24))
    T(ax, p, str(k), 5.6, z=25)

# 場所の名前
T(ax, X(39.4, 13.6), "原っぱ", 7.5, c="#6B5E3A", z=21)
T(ax, X(48.6, 26.3), "しずかのもり", 9, c="#56704A", z=21, fontweight="bold")
T(ax, X(30.0, 15.4), "みずべ", 7, c="#4C7A99", z=21)
T(ax, X(16.0, 7.2), "北のもり", 6.5, c="#56704A", z=21, rot=-38)
T(ax, X(51.8, 8.6), "おくのもり", 6.5, c="#56704A", z=21, rot=-38)
T(ax, X(45.2, 15.6), "だいさんかく", 10, c="#6B5E3A", z=21, fontweight="bold", alpha=0.85, rot=-38)
T(ax, X(55.4, 7.0), "← 高野川（崖 4〜5 m）", 5.2, c="#5E7A8C", rot=-38 + 90, z=21)
T(ax, X(28.0, -1.4), "北東の隣家（境から 1 m）", 5.2, c=C["gray"], rot=-38)
T(ax, X(4.0, 1.3), "用水路から暗渠", 4.6, c="#4C8DB8", rot=-38)

# 比叡山の向き（ホールから築山の頂へ）
HIEI = 63.5   # 敷地（35.047N, 135.786E）から大比叡（35.0667N, 135.8344E）への方位
tp = X(a0, d0); v = np.array([math.sin(math.radians(HIEI)), math.cos(math.radians(HIEI))])
hp = np.array(tp) - v * 18.5
far = np.array(tp) + v * 9
ax.add_patch(FancyArrowPatch(hp, far, arrowstyle="-|>", mutation_scale=7, lw=0.6, color="#8B6BB0", ls=(0, (5, 2)), zorder=19))
brg = math.degrees(math.atan2(v[0], v[1])) % 360
T(ax, far + np.array([0.3, 0.9]), f"比叡山（真北から約 {brg:.0f}°）", 5.4, c="#8B6BB0", ha="left")

# 断面の線
SEC = {}
dirv = np.array([math.sin(math.radians(HIEI)), math.cos(math.radians(HIEI))])
top_xy = np.array(X(a0, d0))
SEC["A"] = (top_xy - dirv * 27.0, top_xy + dirv * 12.0)
p0 = np.array(X(a0 - 1.5, d0 - 0.6)); p1 = np.array(X(*lk["c"]))
dv = (p1 - p0) / np.linalg.norm(p1 - p0)
SEC["B"] = (p0 - dv * 4.0, p1 + dv * 15.0)
for k, (q0, q1) in SEC.items():
    seg = LineString([tuple(q0), tuple(q1)]).intersection(Rectangle((0, 0), 1, 1) and Polygon([(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]))
    cc = np.array(seg.coords)
    line(ax, cc, lw=0.5, c="#555555", ls=(0, (8, 2, 1, 2)), z=18)
    for e in (cc[0], cc[-1]):
        ax.add_patch(Circle(e, 0.9, fc="#555555", ec="none", zorder=23)); T(ax, e, k, 6.5, c="white", z=24, fontweight="bold")

# 方位・縮尺
nx, ny = X1 - 3.0, Y1 - 4.5
ax.add_patch(FancyArrowPatch((nx, ny - 2.2), (nx, ny + 1.6), arrowstyle="-|>", mutation_scale=10, lw=0.8, color=C["ink"], zorder=30))
T(ax, (nx, ny + 2.6), "N", 8, z=30)
sx, sy = X0 + 1.0, Y0 + 1.5
for i in range(5):
    ax.add_patch(Rectangle((sx + i * 2, sy), 2, 0.5, fc="black" if i % 2 == 0 else "white", ec="black", lw=0.4, zorder=30))
T(ax, (sx, sy - 1.0), "0", 5, z=30); T(ax, (sx + 10, sy - 1.0), "10 m", 5, z=30)
T(ax, (sx + 13.5, sy + 0.25), "1/200", 6, ha="left", z=30)

# ================= 見出しと凡例 =================
fx = fig.text
fx(14 / PW, 1 - 16 / PH, "育ち舎　園庭（だいさんかく・しずかのもり）　たたき台", fontsize=15, ha="left", va="baseline")
fx(14 / PW, 1 - 24 / PH, "配置 1/200　断面 1/100（A2）　2026-10-21　遊具を置かず、木と地形で遊ぶ庭。山・川・原っぱ・森、そのあいだにたくさんのニッチ。",
   fontsize=7.2, ha="left", color="#444444")
fx(14 / PW, 1 - 30 / PH, "地形は GL（＝FL−300）からの高さ。等高線 0.2 m ごと（1 m を太く）。築山の位置と形はこの図で決め直した（Keynote の位置は前提にしていない）。",
   fontsize=6.0, ha="left", color="#666666")

LX = 210; LY = 42
def L(y, s, size=6.4, c=C["ink"], w="normal", x=LX):
    fx(x / PW, 1 - y / PH, s, fontsize=size, color=c, ha="left", va="top", fontweight=w)

# 凡例の小さな見本
lax = axes_mm(LX, LY, 196, 300); lax.set_xlim(0, 196); lax.set_ylim(300, 0); lax.axis("off")
def sw(y, kind, txt):
    if kind == "tree":
        lax.add_patch(Circle((5, y), 3.0, fc=C["tree"], ec=C["treeE"], lw=0.4, alpha=0.4))
    elif kind == "ever":
        lax.add_patch(Circle((5, y), 2.2, fc=C["ever"], ec=C["treeE"], lw=0.4, alpha=0.5))
    elif kind == "fruit":
        lax.add_patch(Circle((5, y), 2.4, fc=C["fruit"], ec=C["treeE"], lw=0.4, alpha=0.38))
    elif kind == "climb":
        lax.add_patch(Circle((5, y), 3.0, fc=C["tree"], ec=C["ink"], lw=0.6, ls=(0, (2, 1)), alpha=0.6))
    elif kind == "water":
        lax.add_patch(Rectangle((1, y - 1), 8, 2, fc=C["water"], ec="#4C8DB8", lw=0.3))
    elif kind == "culvert":
        lax.plot([1, 9], [y, y], c=C["water"], lw=0.9, ls=(0, (3, 2)))
    elif kind == "sand":
        lax.add_patch(Rectangle((1, y - 2), 8, 4, fc=C["sand"], ec="#A88E58", lw=0.4, hatch="...."))
    elif kind == "hidden":
        lax.add_patch(Rectangle((1, y - 2), 8, 4, fc="none", ec=C["hidden"], lw=0.4, hatch="////"))
    elif kind == "eye":
        lax.add_patch(Circle((5, y), 1.6, fc="white", ec=C["red"], lw=0.8)); lax.add_patch(Circle((5, y), 0.6, fc=C["red"], ec="none"))
    elif kind == "veh":
        lax.add_patch(Rectangle((1, y - 2), 8, 4, fc="none", ec="#B7A98C", lw=0.5, ls=(0, (4, 2))))
    elif kind == "cont":
        lax.plot([1, 9], [y - 1, y - 1], c=C["cont"], lw=0.3); lax.plot([1, 9], [y + 1, y + 1], c=C["cont"], lw=0.6)
    lax.text(13, y, txt, fontsize=6.2, va="center", ha="left")

y = 4
lax.text(0, y, "凡例", fontsize=8, fontweight="bold", va="center"); y += 8
rows = [("tree", TT["big"]["名"] + "／" + TT["mid"]["名"]), ("fruit", TT["fruit"]["名"]), ("ever", TT["ever"]["名"]),
        ("climb", TT["climb"]["名"]), ("water", "小川（幅 0.5、岸は急、底は平らで浅い）・たまり・水浴び場"), ("culvert", "暗渠（用水路から北の角を通って、みなもとまで）"),
        ("sand", "砂場・粒の遊び場（1〜2 mm）"), ("cont", "等高線 0.2 m（太線 1.0 m）"), ("veh", "剪定・搬入の車の道（芝の保護材 幅 2.5、ふだんは庭）"),
        ("eye", "先生のいる所（縁側の外の縁・小屋の軒、目の高さ GL+1.35）"), ("hidden", f"死角：どの先生からも子どもの頭（地面+{CH}）が見えない所")]
for k, t in rows:
    sw(y, k, t); y += 7.2
y += 3
lax.text(0, y, "ニッチ（静かに遊べる・ひとりになれる所）", fontsize=8, fontweight="bold", va="center"); y += 7
for k, (a, d, txt) in enumerate(G["NICHES"], 1):
    lax.add_patch(Circle((5, y), 2.4, fc="white", ec=C["ink"], lw=0.5)); lax.text(5, y, str(k), fontsize=5.6, ha="center", va="center")
    lax.text(13, y, txt, fontsize=6.2, va="center"); y += 6.2
y += 4

# 数字
ga = GARDEN.area; sa = SHIZU.area
mfoot = float((gc.mound_h(AA, DD) > 0.02).sum() * STEP * STEP)
mvol = float(gc.mound_h(AA, DD).sum() * STEP * STEP)
bvol = 0.0
for b in G["BUMPS"]:
    bvol += float(gc.bump_h(AA, DD, b).sum() * STEP * STEP)
bankv = float((gc.bank_h(AA, DD)).sum() * STEP * STEP)
bowlv = float(-gc.bowl_h(AA, DD).sum() * STEP * STEP)
s_len = sum(LineString(XS(ln)).length for ln in (s["line"], s["line2"]))
hid_a = HIDDEN.area
NUM = dict(garden=ga, shizu=sa, mfoot=mfoot, mvol=mvol, fill=mvol + bvol + bankv, cut=bowlv, stream=s_len, trees=len(G["TREES"]), hidden=hid_a,
           hut=(a_1 - a_0) * (d_1 - d_0), wc=(H["split_a"] - a_0) * (d_1 - d_0), store=(a_1 - H["split_a"]) * (d_1 - d_0))
lax.text(0, y, "数字（この図から）", fontsize=8, fontweight="bold", va="center"); y += 7
for t in [f"だいさんかく（しずかのもりを含む）約 {ga:.0f} m²　うち しずかのもり 約 {sa:.0f} m²（3〜5 歳 70 人で 1 人 {(ga - sa) / 70:.1f} m²、基準は 3.3）",
          f"築山：頂 +{G['MOUND']['h']} m、裾の広さ 約 {mfoot:.0f} m²、土 約 {mvol:.0f} m³。起伏・土手を足すと盛る土は 約 {NUM['fill']:.0f} m³",
          "　→ 基礎・小川・すりばち・遊戯室の穴の底を掘った土で足りる量（外から運び込まない、外へ出さない）",
          f"小川：地上の長さ 約 {s_len:.0f} m、川床 GL−0.15 → −0.40（勾配 約 1/200）。木 {len(G['TREES'])} 本（下書き、種類はこれから）",
          f"小屋：{NUM['hut']:.1f} m²（便所 {NUM['wc']:.1f}＋倉庫 {NUM['store']:.1f}）。倉庫は教材庫×2（13.0）＋遊戯室の道具入れ（5.7）に足して 30 m² を超える",
          f"死角：約 {hid_a:.0f} m²。築山の裏（隣家側）の植え込みと、北のもりの奥。植え込みは入らない所にする"]:
    lax.text(0, y, t, fontsize=6.0, va="center"); y += 6.0
y += 4
lax.text(0, y, "保母さんが困らないように（木と地形の約束）", fontsize=8, fontweight="bold", va="center"); y += 7
for t in ["・高木は枝下 2 m 以上に仕立て、目の高さを見通す。低木は 60 cm 以下（大人は上から見える、子どもは隠れられる）。",
          "・縁側の外の縁と小屋の軒から全体が見える。見えない所（赤の斜線）は植え込みで入らない所にする。",
          "・毒・とげ・かぶれの木は使わない（キョウチクトウ・イチイ・アセビ・ピラカンサ・ハゼ など）。",
          "・ツバキ・サザンカは植えない（チャドクガ）。落葉樹が中心、落ち葉は遊びに使い、掃くのは小径と縁側の前だけ。",
          "・木登りの木は決めておく（2 本まで）。下は剪定の枝でつくった木のチップ（剪定 → チップ → 根もと、を園の中で回す）。",
          "・水は浅く（小川 5〜10 cm、たまり 15 cm）、縁は平らな石。水のある所はどこも先生から見える。",
          "・縁側の前 1.5 m は木を植えない（出入りと見通し）。車の道の筋（幅 2.5）は木と起伏を置かない。"]:
    lax.text(0, y, t, fontsize=6.0, va="center"); y += 6.0

# ================= 断面 1/100 =================
SCS = 1000 / 100                                      # 1 m = 10 mm


def section(key, y_mm, title, beyond=None, zmin=-5.6, zmax=6.0):
    q0, q1 = SEC[key]
    L = float(np.linalg.norm(q1 - q0)); dv = (q1 - q0) / L
    t = np.arange(0, L, 0.05)
    pts = q0[None, :] + t[:, None] * dv[None, :]
    adv = np.array([AD(*p) for p in pts])
    ground = h_at(adv[:, 0], adv[:, 1]).astype(float)
    w = (t[-1] - t[0]) * SCS
    sax = axes_mm(14, y_mm, min(w, 392), (zmax - zmin) * SCS)
    sax.set_xlim(0, min(w, 392) / SCS); sax.set_ylim(zmin, zmax); sax.set_aspect("equal"); sax.axis("off")
    inside = np.array([gc.SITE.contains(Point(*p)) for p in pts])
    bld = np.array([adv[i, 1] > d_edge(adv[i, 0]) and inside[i] and adv[i, 0] < 56 for i in range(len(t))])
    river = adv[:, 0] > 56.0
    nb = adv[:, 1] < 0
    z = np.where(inside & ~bld, ground, 0.0)
    # 崖（現況、寸法は仮）：川沿いの辺からの距離 e
    e = adv[:, 0] - 56.0
    cliff = np.select([e < 0.25, e < 1.0, e < 2.3, e < 11.0], [0.3, -0.3, -0.3 - (e - 1.0) / 1.3 * 3.9, -4.2], -4.6)
    z = np.where(river, cliff, z)
    tt = t
    sax.fill_between(tt, zmin, z, where=~bld | True, color="#EDE7DA", lw=0, zorder=1)
    sax.plot(tt, z, c=C["ink"], lw=0.9, zorder=3)
    # 建物（ホール・縁側）：v で
    if bld.any():
        idx = np.where(bld)[0]
        vv = np.array([gc.uv_of(*pts[i])[1] for i in idx])
        fl = np.where(vv > 12.0, 0.15, 0.3)
        sax.fill_between(tt[idx], -0.3, fl, color="#D9D2C3", lw=0, zorder=2)
        sax.plot(tt[idx], fl, c=C["ink"], lw=0.8, zorder=3)
        roof = 0.3 + 3.0 + (12.0 - vv) / 12.0
        roof = np.where(vv > 15.0, np.nan, roof)
        sax.fill_between(tt[idx], roof, roof + 0.3, color="#BDB3A0", lw=0, zorder=3)
        sax.plot(tt[idx], roof, c=C["ink"], lw=0.5, zorder=3)
        # 東の柱の列（v=12）とガラス戸（v=13.5）
        for vk, lab in ((12.0, "柱"), (13.5, "ガラス戸")):
            k = np.argmin(abs(vv - vk))
            if abs(vv[k] - vk) < 0.2:
                x = tt[idx][k]
                sax.plot([x, x], [fl[k], roof[k] if vk == 12 else 0.3 + 2.27], c="#6B655B", lw=1.2 if vk == 12 else 0.6, zorder=4)
        x = tt[idx][0] if vv[0] < vv[-1] else tt[idx][-1]
        sax.text(np.nanmean(tt[idx]), 2.0, "ホール", fontsize=7, ha="center", color="#6B655B")
        k = np.argmin(abs(vv - 15.0)); sax.text(tt[idx][k], 3.9, "縁側", fontsize=5.5, ha="center", color="#6B655B")
    # 隣家
    if nb.any():
        i0 = np.where(nb)[0][0]; x = tt[i0]
        sax.add_patch(Rectangle((x, 0), 0.12, 1.2, fc="#B9B2A3", ec="none", zorder=4))
        sax.add_patch(MPoly([(x + 1.0, 0), (x + 9, 0), (x + 9, 5.6), (x + 5, 7.0), (x + 1.0, 5.6)], closed=True, fc="none", ec="#AAAAAA", lw=0.5, ls=(0, (3, 2)), zorder=2, clip_on=True))
        sax.text(x + 5, 2.5, "隣家", fontsize=6, color="#999999", ha="center")
        sax.text(x - 0.2, 1.4, "境", fontsize=5, ha="right", color=C["gray"])
    # 川・崖
    if river.any():
        i0 = np.where(river)[0][0]; x0 = tt[i0]
        sax.plot([x0 + 0.12, x0 + 0.12], [0.3, 1.5], c="#777777", lw=0.8, zorder=5)
        sax.text(x0 + 0.35, 1.6, "柵 h1.2（のぞきの所は格子）", fontsize=5, color=C["gray"])
        iw = np.where(e > 11.0)[0]
        if len(iw):
            sax.fill_between(tt[iw], zmin, -4.6, color=C["water"], alpha=0.7, lw=0, zorder=2)
            sax.text(tt[iw].mean(), -4.95, "高野川", fontsize=6.5, ha="center", color="white", zorder=6)
        sax.text(x0 + 4.5, -3.8, "河川敷（草）", fontsize=5.5, color=C["gray"])
        sax.text(x0 + 1.7, -1.9, "谷積みの石積み", fontsize=5, color=C["gray"], rotation=-72)
    # 小川・たまり
    for ln in (s["line"], s["line2"]):
        sl = LineString(ln)
        for i in range(0, len(tt), 2):
            pass
    sl = LineString(s["line"] + s["line2"])
    near = np.array([sl.distance(Point(*p)) for p in adv])
    for i in np.where(near < 0.06)[0][::6]:
        sax.add_patch(Rectangle((tt[i] - 0.25, -0.12), 0.5, 0.12, fc=C["water"], ec="#4C8DB8", lw=0.3, zorder=5))
        sax.text(tt[i], -0.55, "小川", fontsize=5.2, ha="center", color="#4C8DB8")
    # 木（断面の線から 2 m 以内）
    line_sh = LineString([tuple(q0), tuple(q1)])
    for a, d, kind, _, note in G["TREES"]:
        p = Point(*X(a, d)); dist = line_sh.distance(p)
        if dist < 2.2:
            x = line_sh.project(p)
            if not (0 <= x <= sax.get_xlim()[1]):
                continue
            g0 = float(h_at(np.array(a), np.array(d)))
            r = TT[kind]["r"]; ht = {"big": 7.5, "climb": 7, "mid": 5, "fruit": 4.0, "ever": 4.5}[kind]
            sax.plot([x, x], [g0, g0 + ht * 0.45], c="#5D4A36", lw=1.0, zorder=6)
            sax.add_patch(Ellipse((x, g0 + ht * 0.68), r * 2, ht * 0.62, fc=C["ever"] if kind == "ever" else C["tree"], ec=C["treeE"], lw=0.4, alpha=0.35, zorder=6, clip_on=True))
    # 人
    def person(x, z0, hgt, c="#555555"):
        sax.add_patch(Circle((x, z0 + hgt - hgt * 0.09), hgt * 0.09, fc=c, ec="none", zorder=9))
        sax.plot([x, x], [z0, z0 + hgt * 0.82], c=c, lw=1.1, zorder=9)
    if beyond:
        beyond(sax, tt, z, adv, person, bld)
    sax.plot([0, sax.get_xlim()[1]], [0, 0], c="#999999", lw=0.3, ls=(0, (6, 3)), zorder=0.5)
    sax.text(0.1, 0.12, "GL±0（FL−300）", fontsize=5, color=C["gray"])
    fx(14 / PW, 1 - (y_mm - 2) / PH, title, fontsize=8.5, ha="left", fontweight="bold")
    for k in range(int(zmin), int(zmax) + 1):
        if k % 1 == 0 and -5 <= k <= 5:
            sax.plot([-0.0, 0.25], [k, k], c=C["gray"], lw=0.4)
    return sax, tt, z, adv


def deco_A(sax, tt, z, adv, person, bld):
    # 先生（縁側）、転がる子、比叡山へ
    idx = np.where(bld)[0]
    if len(idx):
        xe = tt[idx].min() if adv[idx[0], 1] > adv[idx[-1], 1] else tt[idx].max()
    k = np.argmax(z); xs = tt[k]
    sax.text(xs, z[k] + 0.35, f"築山の頂 +{G['MOUND']['h']}", fontsize=6, ha="center", color=C["cont"])
    person(xs + 0.5, z[k], 1.05)
    for f in (0.35, 0.6):
        i = int(k + (len(tt) * 0 + (np.where(bld)[0].max() - k if len(idx) and np.where(bld)[0].max() < k else -k * 0) * 0))
    # 転がる斜面の子
    j = k - int(3.5 / 0.05)
    if 0 <= j < len(tt):
        sax.add_patch(Ellipse((tt[j], z[j] + 0.25), 0.9, 0.38, angle=math.degrees(math.atan2(z[k] - z[j], tt[k] - tt[j])), fc="#555555", ec="none", zorder=9))
        sax.text(tt[j], z[j] + 0.75, "ころがる", fontsize=5.5, ha="center", color="#555555")
    xr = sax.get_xlim()[1]
    sax.annotate("", xy=(xr - 0.2, 3.6), xytext=(xr - 5.2, 3.6), arrowprops=dict(arrowstyle="-|>", color="#8B6BB0", lw=0.7))
    sax.text(xr - 5.2, 4.0, "比叡山（約 4.9 km 先）", fontsize=6, color="#8B6BB0")
    # 目線：ホールの縁側から頂の木へ
    sax.text(1.0, 4.9, "ホール → 縁側 → 小川 → 原っぱ → 築山 → 境の木 → 隣家", fontsize=6.2, color="#444444")


def deco_B(sax, tt, z, adv, person, bld):
    e = adv[:, 0] - 56.0
    i0 = np.where(e > 0)[0]
    if not len(i0):
        return
    x0 = tt[i0[0]]
    # のぞきの段と子ども
    sax.add_patch(Rectangle((x0 - G["LOOKOUT"]["deck_d"], 0), G["LOOKOUT"]["deck_d"], G["LOOKOUT"]["h"], fc="#E3D3B5", ec=C["wood"], lw=0.5, zorder=5))
    person(x0 - 0.5, G["LOOKOUT"]["h"], 1.05)
    eye = (x0 - 0.5, G["LOOKOUT"]["h"] + 0.95)
    wx = tt[np.where(e > 11.0)[0][0]] + 1.5 if (e > 11.0).any() else x0 + 12
    sax.plot([eye[0], wx], [eye[1], -4.6], c="#4C8DB8", lw=0.6, ls=(0, (3, 2)), zorder=7)
    sax.text(x0 + 3.0, -1.0, "のぞきに来ると\n水面が見える", fontsize=5.6, color="#4C8DB8")
    # 原っぱからの目線：崖の縁にさえぎられる
    k = i0[0] - int(9.0 / 0.05)
    if k > 0:
        e2 = (tt[k], z[k] + 0.95); person(tt[k], z[k], 1.05)
        slope = (0.3 - e2[1]) / (x0 + 0.1 - e2[0])
        xe = x0 + 12
        sax.plot([e2[0], xe], [e2[1], e2[1] + slope * (xe - e2[0])], c="#999999", lw=0.5, ls=(0, (2, 2)), zorder=7)
        sax.text(e2[0] + 1.0, e2[1] + 0.55, "原っぱからは崖の縁で水面は見えない", fontsize=5.6, color="#777777")
    kk = np.argmax(z[: i0[0]]); sax.text(tt[kk], z[kk] + 0.3, "築山（尾）", fontsize=5.6, ha="center", color=C["cont"])
    sax.text(x0 + 0.3, -0.25, "小段", fontsize=4.6, color=C["gray"])


sa_y = 40 + (Y1 - Y0) * SC + 22
section("A", sa_y, "断面 A–A　ホールから築山の頂を通って比叡山の向きへ　1/100", deco_A, zmin=-1.0, zmax=6.6)
section("B", sa_y + 92, "断面 B–B　築山から小川・のぞきを通って高野川へ　1/100（崖・河川敷の寸法は仮）", deco_B, zmin=-5.2, zmax=4.6)

fx(406 / PW, 6 / PH, "こどもたちの育ち舎　garden01.py（data/garden.json・sodachiya_exact_mesh.3dm から）", fontsize=5.2, ha="right", color="#888888")
os.makedirs(OUT, exist_ok=True)
fig.savefig(os.path.join(OUT, "sodachiya_garden_01.pdf"))
fig.savefig(os.path.join(OUT, "sodachiya_garden_01.png"), dpi=110)
import json as _j
print(_j.dumps({k: round(v, 1) if isinstance(v, float) else v for k, v in NUM.items()}, ensure_ascii=False))
