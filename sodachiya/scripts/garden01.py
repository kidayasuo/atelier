"""園庭（だいさんかく・しずかのもり）のたたき台  配置 1/200＋断面 1/100（A2 縦）
読むもの：data/garden.json（園庭の寸法）、model/sodachiya_exact_mesh.3dm（敷地・建物）
出すもの：out/sodachiya_garden_01.pdf / .png（出力先は環境変数 OUT で変えられる）
"""
import math, os, json
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
# 文字をIllustratorで文字として直せるように（ヒラギノへ置き換える、プレゼンの準備 10-24）、TrueTypeのNotoをType42で埋め込む（room3_50 と同じ）
import sys as _sys, subprocess as _sp, matplotlib.font_manager as _fm
_TTF = os.path.expanduser("~/.cache/sodachiya_fonts")
if not os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")):
    _sp.run([_sys.executable, os.path.join(gc.ROOT, "present", "tools", "make_ttf.py"), _TTF], check=False)
if os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")):
    # 同じ名前の OTF（.ttc）が先に選ばれる（Type 0C になる）ので、Noto CJK の .ttc を候補から外す
    _fm.fontManager.ttflist = [f for f in _fm.fontManager.ttflist if not ("NotoSansCJK" in f.fname and f.fname.endswith((".ttc", ".otf")))]
    for _f in ("Regular", "Bold"):
        _fm.fontManager.addfont(os.path.join(_TTF, f"NotoSansCJKjp-{_f}.ttf"))
    plt.rcParams["font.family"] = _fm.FontProperties(fname=os.path.join(_TTF, "NotoSansCJKjp-Regular.ttf")).get_name()
    plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["hatch.linewidth"] = 0.4
OUT = os.environ.get("OUT", os.path.join(gc.ROOT, "out"))
MM = 1 / 25.4
PW, PH = 420, 594                                     # A2 縦
fig = plt.figure(figsize=(PW * MM, PH * MM))

C = dict(grass="#F1F3E6", shizu="#DCE7D0", field="#F4F1E0", water="#7FB7D9", waterL="#CFE6F3", sand="#EADCB5",
         bld="#E9E6E0", bldE="#8A847A", engawa="#F4EBDD", tree="#9DBB82", treeE="#6F8F57", ever="#6E9466",
         fruit="#D9A35B", hut="#D8C3A0", red="#C8463D", path="#C9B89A", ink="#222222", gray="#777777",
         hidden="#C8463D", cont="#8A7A5C", wood="#9B7653")
GC = {"香り": "#B98BC9", "花": "#E79AB0", "紅葉": "#D9774A", "実": "#D9A35B", "常緑": "#6E9466", "木陰": "#9DBB82"}   # 木の色分け

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
HUT_AD = Polygon([(H["a"][0], H["d"][0]), (H["closed_a"], H["d"][0]), (H["closed_a"], H["d"][1]), (H["a"][0], H["d"][1])])   # 視線をさえぎるのは閉じた部屋だけ
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
# 図の向き：高野川（川沿いの辺）を下に（ユーザー）。3dm の xy を ROT 度回して描く（北は右上）
from shapely import affinity
from matplotlib.transforms import Affine2D
import matplotlib.text as mtext
ROT = G["VIEW_ROT"]["deg"]
_gr = affinity.rotate(GARDEN, ROT, origin=(0, 0)).bounds
VX0, VY0, VX1, VY1 = _gr[0] - 6.0, _gr[1] - 6.0, _gr[2] + 3.0, _gr[3] + 3.0     # 回した後の見える範囲（m）
SC = 1000 / 200                                       # 1 m = 5 mm
PLAN_W, PLAN_H = (VX1 - VX0) * SC, (VY1 - VY0) * SC
ax = axes_mm(14, 40, PLAN_W, PLAN_H)
ax.set_aspect("equal"); ax.axis("off")
VIEW = affinity.rotate(Polygon([(VX0, VY0), (VX1, VY0), (VX1, VY1), (VX0, VY1)]), -ROT, origin=(0, 0))   # 元の xy での見える範囲
X0, Y0, X1, Y1 = VIEW.bounds

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
T(ax, X(a0 + 1.6, d0 - 0.4), f"+{G['MOUND']['h']}", 6.5, c=C["cont"], z=21, fontweight="bold")
for dd, txt in ((3.2, "1:3"), ):
    pass
T(ax, X(a0 + 0.6, d0 + 4.4), "転がる斜面\n1:3〜1:4（芝）", 5.2, c=C["cont"], rot=-38)
T(ax, X(a0 - 0.6, d0 - 2.3), "裏の斜面 1:1.5\n（植え込み、入らない）", 4.4, c=C["cont"], rot=-38)
T(ax, X(17.4, 3.2), "+0.6", 5, c=C["cont"])
T(ax, X(50.6, 4.2), "+1.0", 5, c=C["cont"])
T(ax, X(47.0, 21.9), f"土手 +{G['BANK']['h']}", 5, c=C["cont"], rot=-38)
T(ax, X(G["BOWL"]["c"][0], G["BOWL"]["c"][1] + 0.1), "−0.4", 4.6, c=C["cont"])

# 死角
poly(ax, P(list(HIDDEN.exterior.coords)) if HIDDEN.geom_type == "Polygon" else MultiPolygon([P(list(q.exterior.coords)) for q in HIDDEN.geoms]),
     fc="none", ec=C["hidden"], lw=0.3, z=3.5, hatch="////", alpha=0.75)

# 小川
s = G["STREAM"]
line(ax, XS(s["culvert"]), lw=0.8, c=C["water"], ls=(0, (3, 2)), z=6)
for ln in (s["line"],):
    g = LineString(XS(ln)).buffer(s["w"] / 2, cap_style=1, join_style=1)
    poly(ax, g, fc=C["water"], ec="#4C8DB8", lw=0.3, z=6)
# 床の噴水（上水、ためない）
F = G["FOUNTAIN"]
fpoly = P(ell_ad(F["c"], F["r"], F["rot"]))
poly(ax, fpoly, fc="#E6E3DA", ec="#8C8677", lw=0.6, z=6)
ca, sa_ = math.cos(math.radians(F["rot"])), math.sin(math.radians(F["rot"]))
nj = 0
_rp = G["SHOWER"].get("ring", {}).get("posts", [G["SHOWER"]["c"]])   # あめのわの柱と重なる噴き口は外す
for i in np.arange(-F["r"][0], F["r"][0] + 0.01, F["jets"][0]):
    for j in np.arange(-F["r"][1], F["r"][1] + 0.01, F["jets"][1]):
        if (i / (F["r"][0] - 0.4)) ** 2 + (j / (F["r"][1] - 0.4)) ** 2 <= 1:
            q = (F["c"][0] + i * ca - j * sa_, F["c"][1] + i * sa_ + j * ca)
            if min(math.hypot(q[0] - p_[0], q[1] - p_[1]) for p_ in _rp) < 0.3: continue
            ax.add_patch(Circle(X(*q), 0.11, fc="#4C8DB8", ec="none", zorder=6.3)); nj += 1
dr = F["drain"]; line(ax, XS([F["c"], dr]), lw=0.5, c="#4C8DB8", ls=(0, (1.5, 1.5)), z=6.2)
ax.add_patch(Rectangle(np.array(X(*dr)) - 0.25, 0.5, 0.5, fc="#8C8677", ec="none", zorder=6.4))
# 護岸の溝（小川はここを滑り落ちて高野川へ）
gv = s["groove"]; ga_ = np.array(X(*gv["at"]))
line(ax, [X(54.2, 15.4), tuple(ga_)], lw=2.4, c=C["water"], z=6.5)
ax.add_patch(Rectangle(ga_ - 0.25, 0.5, 0.5, fc=C["water"], ec="#2F6E95", lw=0.5, zorder=8.6))
T(ax, X(53.4, 13.4), "護岸の溝を滑り落ちて高野川へ", 4.4, c="#3E6E8E", rot=-38)
# 雨の川（雨落ちの溝、本館の東の軒の真下、樋なし）→ 南東の角から護岸の溝へ。溢れたらすりばち（雨の池）へ
AM = G["AMAOCHI"]
uu = np.linspace(AM["u"][0], AM["u"][1], 80)
trench = Polygon([UV(u, G["EDGE_V"]) for u in uu] + [UV(u, G["EDGE_V"] + AM["w"]) for u in uu[::-1]])
poly(ax, trench, fc="#D9D4C6", ec="#8C8677", lw=0.3, z=5.6, hatch="oo")
og = LineString(XS(AM["outlet"])).buffer(AM["w"] / 2, cap_style=2)
poly(ax, og, fc="#D9D4C6", ec="#8C8677", lw=0.3, z=5.6, hatch="oo")
ga2 = np.array(X(*AM["outlet"][-1]))
ax.add_patch(Rectangle(ga2 - 0.25, 0.5, 0.5, fc=C["water"], ec="#2F6E95", lw=0.5, zorder=8.6))
# 雨庭（洲浜）：雨の川の行き着く所、しずかのもりの高野川べり（ユーザー）
AW = G.get("AMANIWA")
if AW:
    poly(ax, Polygon(XS(AW["poly"])), fc="#F2EFE6", ec="#8C8677", lw=0.4, z=5.7, hatch="o.")
    for sa_, sd_, sr_ in AW["stones"]:
        ax.add_patch(Circle(X(sa_, sd_), sr_, fc="#8C8677", ec="#4A4438", lw=0.4, zorder=8.8))
    T(ax, X(54.7, 28.2), "雨庭（洲浜）", 4.6, c="#4A4438", rot=52, z=21, fontweight="bold")
    T(ax, X(55.9, 33.0), "溢れたら護岸の溝へ", 3.6, c="#3E6E8E", rot=52, z=21)
T(ax, UV(30.5, 16.6), "雨の川（晴れの日は枯れ流れ）", 4.4, c="#6B655B", rot=-86)
sp = AM["spill"]
ax.add_patch(FancyArrowPatch(X(*sp[0]), X(*sp[1]), arrowstyle="-|>", mutation_scale=6, lw=0.6, color="#2F6E95", ls=(0, (2, 1.5)), zorder=8.7))
T(ax, X(G["BOWL"]["c"][0] - 0.2, G["BOWL"]["c"][1] - 1.2), "雨の池（大雨のとき）", 4.2, c="#2F6E95", rot=-38)
# シャワーの柱とあめのわ（床の噴水の真ん中、10-30）
sh = G["SHOWER"]; shp = np.array(X(*sh["c"]))
ax.add_patch(Rectangle(shp - 0.09, 0.18, 0.18, fc=C["wood"], ec="none", zorder=6.9))          # 柱 1 本
_rg = sh.get("ring")
if _rg:
    rcp = np.array(X(*_rg["c"]))
    for q in _rg.get("posts", [sh["c"]]):
        ax.add_patch(Rectangle(np.array(X(*q)) - 0.09, 0.18, 0.18, fc=C["wood"], ec="none", zorder=6.9))   # 柱（両側から支える）
    line(ax, [X(*q) for q in _rg.get("posts", [sh["c"]])], lw=0.8, c=C["wood"], z=6.85)   # 梁
    ax.add_patch(Circle(rcp, _rg["r"], fc="#CFE6F3", ec="#2F6E95", lw=0.6, alpha=0.55, zorder=6.8))
    for k in range(_rg["n"]):
        q = 2 * math.pi * k / _rg["n"]
        ax.add_patch(Circle(rcp + _rg["r"] * np.array([math.cos(q), math.sin(q)]), 0.035, fc="#2F6E95", ec="none", zorder=6.82))
    T(ax, rcp + np.array([0.3, 1.95]), "あめのわ（輪のシャワー φ2.4）", 4.2, c="#2F6E95", z=21, fontweight="bold")
else:
    line(ax, [tuple(shp), tuple(shp + np.array([0.45, -0.35]))], lw=0.8, c=C["wood"], z=6.85)        # 腕
    ax.add_patch(Circle(shp + np.array([0.45, -0.35]), 0.3, fc="#CFE6F3", ec="#2F6E95", lw=0.5, zorder=6.8))
    T(ax, shp + np.array([1.0, 0.9]), "シャワーの柱（あめのシャワー＋ハンド、温水）", 4.4, c="#3E6E8E", ha="left")
poly(ax, P(ell_ad(G["TANK"]["c"], G["TANK"]["r"], -30)), fc="none", ec="#4C8DB8", lw=0.35, ls=(0, (2, 1.5)), z=5.7)
for b in G["BRIDGES"]:
    c = b["c"]
    if b["w"] > 0:
        # 小川の向きに直交する板
        ln = LineString(s["line"]); t0 = ln.project(Point(*c)); p0 = ln.interpolate(t0 - 0.4); p1 = ln.interpolate(t0 + 0.4)
        ta = np.array([p1.x - p0.x, p1.y - p0.y]); ta /= np.linalg.norm(ta)
        hw = 0.45 if b["w"] < 2 else 0.75
        q = [np.array(c) + ta * i * hw + np.array([-ta[1], ta[0]]) * j * b["w"] / 2 for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        poly(ax, P([tuple(v) for v in q]), fc="#D8D2C2" if b["w"] > 2 else C["wood"], ec="#6B655B", lw=0.4, z=6.5)
    else:
        for k in (-0.35, 0.35):
            ax.add_patch(Circle(X(c[0] + k * 0.5, c[1] + k), 0.22, fc="#D8D2C2", ec="#6B655B", lw=0.3, zorder=6.5))

# 砂場・水浴び場・粒・柳
poly(ax, P(G["SAND"]["poly"]), fc=C["sand"], ec="#A88E58", lw=0.4, z=5.5, hatch="....")
_SP = G["SPLASH"]
poly(ax, P(ell_ad(_SP["c"], _SP["r"], _SP["rot"])), fc="#E6E2D8", ec="#4C8DB8", lw=0.4, z=5.5)   # 乳児の床の噴水（石張り）
_js = _SP.get("jets", 0)
if _js:
    for ja in np.arange(-_SP["r"][0], _SP["r"][0] + 0.01, _js):
        for jd in np.arange(-_SP["r"][0], _SP["r"][0] + 0.01, _js):
            if math.hypot(ja, jd) < _SP["r"][0] - 0.3:
                ax.add_patch(Circle(X(_SP["c"][0] + ja, _SP["c"][1] + jd), 0.06, fc="#4C8DB8", ec="none", zorder=5.6))
_ms = _SP.get("mist")
if _ms:
    ax.add_patch(Circle(X(*_SP["c"]), _ms["r"], fc="#CFE6F3", ec="#2F6E95", lw=0.5, ls=(0, (1, 1)), alpha=0.6, zorder=6.8))
    for q in _ms["posts"]:
        ax.add_patch(Rectangle(np.array(X(*q)) - 0.07, 0.14, 0.14, fc=C["wood"], ec="none", zorder=6.9))
    T(ax, X(_SP["c"][0] + 0.2, _SP["c"][1] + 2.6), "乳児の床の噴水・霧のわ", 4.0, c="#2F6E95", rot=-38, z=21, fontweight="bold")
GR = G["GRAIN"]; _ca, _sa = math.cos(math.radians(GR["rot"])), math.sin(math.radians(GR["rot"]))
def _gr(u, v):
    return (GR["c"][0] + u * _ca - v * _sa, GR["c"][1] + u * _sa + v * _ca)
_hl, _hw = GR["l"] / 2, GR["w"] / 2
poly(ax, P([_gr(-_hl - .15, -_hw - .15), _gr(_hl + .15, -_hw - .15), _gr(_hl + .15, _hw + .15), _gr(-_hl - .15, _hw + .15)]), fc=C["wood"], ec=C["wood"], lw=0.3, z=5.4)
poly(ax, P([_gr(-_hl, -_hw), _gr(_hl, -_hw), _gr(_hl, _hw), _gr(-_hl, _hw)]), fc="#EFE6CF", ec="#A88E58", lw=0.3, z=5.5, hatch="...")
line(ax, XS([_gr(-_hl, _hw + .35), _gr(_hl, _hw + .35)]), lw=2.2, c="#C9B48E", z=5.6)   # 帆布を巻いた棒
T(ax, X(*_gr(0, _hw + 0.9)), "帆布の巻き取り", 3.4, c="#6B5A3A", rot=-38, z=9.3)
# 鉄棒ひと組（10-27 ユーザー）：3段の低い鉄棒、点線は安全の範囲
BR = G.get("BAR")
if BR:
    _cb, _sb = math.cos(math.radians(BR["rot"])), math.sin(math.radians(BR["rot"]))
    def _br(u, v):
        return (BR["c"][0] + u * _cb - v * _sb, BR["c"][1] + u * _sb + v * _cb)
    _zl, _zw = BR["zone"][0] / 2, BR["zone"][1] / 2
    poly(ax, P([_br(-_zl, -_zw), _br(_zl, -_zw), _br(_zl, _zw), _br(-_zl, _zw)]), fc="none", ec="#5A4630", lw=0.5, z=20, ls=(0, (2, 1.5)))
    _n = len(BR["bars"]); _u0 = -BR["span"] * _n / 2
    line(ax, XS([_br(_u0, 0), _br(-_u0, 0)]), lw=1.0, c="#3F444A", z=20.1)
    for i in range(_n + 1):
        ax.add_patch(Circle(X(*_br(_u0 + i * BR["span"], 0)), BR["post_d"] / 2 + 0.05, fc=C["wood"], ec="#5A4630", lw=0.4, zorder=20.2))
    _hs = "・".join(f"{h:.2f}" for h in BR["bars"])
    T(ax, X(*_br(0, -_zw - 0.9)), f"鉄棒（3段 h{_hs}）", 4.0, c="#5A4630", rot=-38, z=21, fontweight="bold")
# 小さな滝と滝壺（みなもと）
_FL = G["STREAM"].get("fall")
if _FL:
    _pc = _FL["pool"]
    ax.add_patch(Circle(X(*_pc["c"]), _pc["r"], fc=C["water"], ec="#4C8DB8", lw=0.4, zorder=7.1))
    for _k in (0.0, 0.45):
        _q = (_FL["lip"][0] + (_pc["c"][0] - _FL["lip"][0]) * _k, _FL["lip"][1] + (_pc["c"][1] - _FL["lip"][1]) * _k)
        ax.add_patch(Rectangle(np.array(X(*_q)) - 0.3, 0.6, 0.6, angle=0, fc="#B9B2A3", ec="#6B655B", lw=0.4, zorder=7.2))
    T(ax, X(_pc["c"][0] + 1.4, _pc["c"][1] + 0.4), "小さな滝（落差 約0.45）", 3.8, c="#2F6E9A", rot=-38, z=9.3)
# 北の口の木戸
_GN = G.get("GATE_N")
if _GN:
    line(ax, XS([_GN["p0"], _GN["p1"]]), lw=2.0, c=C["wood"], z=9.5)
    T(ax, X(_GN["p0"][0] + 0.9, _GN["p0"][1] * 0.5), "北の口の木戸", 3.8, c="#6B5A3A", rot=-38, z=9.6)
# 縁側の前の飛び石（しずかのもりへの道）。関守石は置かない（10-25 ユーザー：入ってだめなわけではない）
for q in G["SEKIMORI"].get("steps", []):
    ax.add_patch(Circle(X(*q), 0.26, fc="#D8D2C2", ec="#6B655B", lw=0.3, zorder=6.6))
for q in G["SEKIMORI"]["pts"]:
    ax.add_patch(Circle(X(*q), 0.32, fc="#8C8677", ec=C["ink"], lw=0.4, zorder=8.6))
    line(ax, [np.array(X(*q)) + v for v in (np.array([-0.32, 0]), np.array([0.32, 0]))], lw=0.6, c="#3A2E22", z=8.7)
    line(ax, [np.array(X(*q)) + v for v in (np.array([0, -0.32]), np.array([0, 0.32]))], lw=0.6, c="#3A2E22", z=8.7)
# 噴水のバルブます
_vb = G["FOUNTAIN"]["valve"]["c"]
poly(ax, P([(_vb[0] - .45, _vb[1] - .3), (_vb[0] + .45, _vb[1] - .3), (_vb[0] + .45, _vb[1] + .3), (_vb[0] - .45, _vb[1] + .3)]), fc="#D8D2C2", ec=C["ink"], lw=0.4, z=7.2)
T(ax, X(_vb[0] + 0.1, _vb[1] - 1.0), "バルブます", 3.4, rot=-38, z=9.3)
wl = G["WILLOW"]; ax.add_patch(Circle(X(*wl["c"]), wl["r"], fc="none", ec=C["treeE"], lw=0.9, ls=(0, (1, 1)), zorder=8))

# 小屋（ひとつの屋根：便所｜倉庫｜コンポスト）
a_0, a_1 = H["a"]; d_0, d_1 = H["d"]; a_c = H["closed_a"]
poly(ax, P([(a_0, d_0), (a_c, d_0), (a_c, d_1), (a_0, d_1)]), fc=C["hut"], ec=C["ink"], lw=0.8, z=9)
line(ax, XS([(H["split_a"], d_0), (H["split_a"], d_1)]), lw=0.5, z=9.1)
poly(ax, P([(a_c, d_0), (a_1, d_0), (a_1, d_1), (a_c, d_1)]), fc="#EFE6D2", ec=C["ink"], lw=0.4, ls=(0, (3, 2)), z=8.9)   # 壁のない間（屋根だけ）
for q in ((a_c, d_0), (a_1 - 0.1, d_0), (a_1 - 0.1, d_1 - 0.1)):
    ax.add_patch(Rectangle(np.array(X(*q)) - 0.06, 0.12, 0.12, fc=C["ink"], ec="none", zorder=9.1))
poly(ax, P([(a_0 - 0.3, d_1), (a_1 + 0.3, d_1), (a_1 + 0.3, d_1 + H["eave"]), (a_0 - 0.3, d_1 + H["eave"])]), fc="none", ec=C["ink"], lw=0.4, ls=(0, (3, 2)), z=9)
T(ax, X((a_0 + H["split_a"]) / 2, (d_0 + d_1) / 2), "便所", 5, rot=-38)
T(ax, X((H["split_a"] + a_c) / 2, (d_0 + d_1) / 2), "倉庫", 5.5, rot=-38)
CP = G["COMPOST"]
for i in range(CP["n"]):
    q0 = CP["a0"] + i * CP["w"]
    poly(ax, P([(q0 + 0.05, CP["d0"]), (q0 + CP["w"] - 0.05, CP["d0"]), (q0 + CP["w"] - 0.05, CP["d0"] + CP["depth"]), (q0 + 0.05, CP["d0"] + CP["depth"])]),
         fc="#C9B48E", ec=C["wood"], lw=0.5, z=9.2)
    T(ax, X(q0 + CP["w"] / 2, CP["d0"] + CP["depth"] / 2), CP["labels"][i], 3.2, rot=-38, z=9.3)
T(ax, X(CP["a0"] + CP["n"] * CP["w"] / 2, CP["d0"] + CP["depth"] + 1.0), "コンポスト（屋根の下）", 4.4, c="#6B5A3A", rot=-38)
T(ax, X((a_0 + a_c) / 2, d_1 + 0.75), "足洗い・ベンチ（軒の下）", 3.8, c="#6B5A3A", rot=-38)

# のぞき
lk = G["LOOKOUT"]; c = lk["c"]
(h0a, h0d), (h1a, h1d) = lk["hedge"]
cuts = sorted(lk["gaps"])
segs = []; d_ = h0d
for gd, gw in cuts:
    segs.append((d_, gd - gw / 2)); d_ = gd + gw / 2
segs.append((d_, h1d))
for q0, q1 in segs:
    poly(ax, P([(56.0 - 0.15 - lk["hedge_w"], q0), (56.0 - 0.15, q0), (56.0 - 0.15, q1), (56.0 - 0.15 - lk["hedge_w"], q1)]), fc=C["ever"], ec=C["treeE"], lw=0.3, z=8, alpha=0.7)
for gd, gw in cuts:
    line(ax, XS([(56.0, gd - gw / 2), (56.0, gd + gw / 2)]), lw=1.6, c=C["wood"], z=8.5)

# 木
TT = G["TREE_TYPES"]
SP = G["SPECIES"]
def sp_of(note):
    return note.split("（")[0]
for a, d, kind, _, note in G["TREES"]:
    r = TT[kind]["r"]; p = X(a, d)
    fc = GC[SP[sp_of(note)]["g"]]
    ax.add_patch(Circle(p, r, fc=fc, ec=C["treeE"], lw=0.35, alpha=0.42 if kind != "ever" else 0.55, zorder=10))
    T(ax, (p[0], p[1] - 0.55), sp_of(note), 3.0, c="#3A3A3A", rot=-38, z=10.8)
    ax.add_patch(Circle(p, 0.12, fc="#5D4A36", ec="none", zorder=10.5))
    if kind == "climb":
        ax.add_patch(Circle(p, r, fc="none", ec=C["ink"], lw=0.6, ls=(0, (2, 1)), zorder=10.6))

# 年中行事の草（セリ・ショウブ・摘み草・ススキ）
for a_, d_, r_, nm_, _n in G.get("GYOJI", {}).get("items", []):
    ax.add_patch(Circle(X(a_, d_), r_, fc="#C9D99A", ec="#6F8F57", lw=0.4, ls=(0, (1.2, 0.8)), alpha=0.85, zorder=10.9))
    T(ax, X(a_, d_), nm_, 3.4, c="#3F5A2E", rot=-38, z=11.0)

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
T(ax, X(50.6, 23.4), "しずかのもり", 9, c="#56704A", z=21, fontweight="bold")
T(ax, X(*G["FOUNTAIN"]["c"]), "床の噴水", 5.6, c="#3E6E8E", z=21, rot=-38)
T(ax, X(23.6, 11.6), "みずべ", 7, c="#4C7A99", z=21)
T(ax, X(16.0, 7.2), "おくのもり", 6.5, c="#56704A", z=21, rot=-38)
T(ax, X(51.8, 8.6), "かぜのもり", 6.5, c="#56704A", z=21, rot=-38)
T(ax, X(40.6, 1.7), "てんぐのたに", 6.5, c="#56704A", z=21, rot=-38)
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
SEC["B"] = (p0 + dv * 1.0, p1 + dv * 20.0)
for k, (q0, q1) in SEC.items():
    seg = LineString([tuple(q0), tuple(q1)]).intersection(VIEW)
    cc = np.array(seg.coords)
    line(ax, cc, lw=0.5, c="#555555", ls=(0, (8, 2, 1, 2)), z=18)
    for e in (cc[0], cc[-1]):
        ax.add_patch(Circle(e, 0.9, fc="#555555", ec="none", zorder=23)); T(ax, e, k, 6.5, c="white", z=24, fontweight="bold")

# 回す（描いたものを全部 ROT 度回す。文字は向きも足す）
TR = Affine2D().rotate_deg(ROT) + ax.transData
for art in list(ax.patches) + list(ax.lines) + list(ax.collections) + list(ax.texts):
    art.set_transform(TR)
    if isinstance(art, mtext.Text):
        r0 = art.get_rotation() % 360
        if any(abs(r0 - q) < 1.0 or abs(r0 - q - 360) < 1.0 for q in (0.0, 322.0, 52.0)):     # 園庭の文字は回した図で水平に（建物の文字だけ建物に沿わせる）
            art.set_rotation(0)
        else:
            art.set_rotation((r0 + ROT) % 360)
gclip2 = MPoly(np.array(GARDEN.exterior.coords), closed=True, transform=TR)
cs.set_clip_path(gclip2)
ax.set_xlim(VX0, VX1); ax.set_ylim(VY0, VY1)

# 方位・縮尺（回した後の図に）
nv = np.array([-math.sin(math.radians(ROT)), math.cos(math.radians(ROT))])
nc = np.array([VX1 - 4.0, VY0 + 3.2])
ax.add_patch(FancyArrowPatch(tuple(nc - nv * 2.0), tuple(nc + nv * 2.0), arrowstyle="-|>", mutation_scale=10, lw=0.8, color=C["ink"], zorder=30))
ax.text(*(nc + nv * 3.0), "N", fontsize=8, ha="center", va="center", zorder=30)
sx, sy = VX0 + 1.0, VY0 + 1.2
for i in range(5):
    ax.add_patch(Rectangle((sx + i * 2, sy), 2, 0.5, fc="black" if i % 2 == 0 else "white", ec="black", lw=0.4, zorder=30))
ax.text(sx, sy - 1.0, "0", fontsize=5, ha="center", va="center"); ax.text(sx + 10, sy - 1.0, "10 m", fontsize=5, ha="center", va="center")
ax.text(sx + 13.5, sy + 0.25, "1/200　高野川を下に（北は右上）", fontsize=6, ha="left", va="center")

# ================= 見出しと凡例 =================
fx = fig.text
fx(14 / PW, 1 - 16 / PH, "育ち舎　園庭（だいさんかく・しずかのもり）　たたき台 8", fontsize=15, ha="left", va="baseline")
fx(14 / PW, 1 - 24 / PH, "配置 1/200　断面 1/100（A2）　2026-10-27　遊具は鉄棒ひと組だけ、木と地形で遊ぶ庭。山・川・原っぱ・森、そのあいだにたくさんのニッチ。",
   fontsize=7.2, ha="left", color="#444444")
fx(14 / PW, 1 - 30 / PH, "地形は GL（＝FL−300）からの高さ。等高線 0.2 m ごと（1 m を太く）。築山の位置と形はこの図で決め直した（Keynote の位置は前提にしていない）。",
   fontsize=6.0, ha="left", color="#666666")

LX = 14 + PLAN_W + 8; LY = 42; LW = 406 - LX
import textwrap
WRAP = int((LW - 14) / 2.2)
def L(y, s, size=6.4, c=C["ink"], w="normal", x=LX):
    fx(x / PW, 1 - y / PH, s, fontsize=size, color=c, ha="left", va="top", fontweight=w)

# 凡例の小さな見本
lax = axes_mm(LX, LY, LW, 300); lax.set_xlim(0, LW); lax.set_ylim(300, 0); lax.axis("off")
def sw(y, kind, txt):
    if kind == "tree":
        lax.add_patch(Circle((5, y), 3.0, fc=C["tree"], ec=C["treeE"], lw=0.4, alpha=0.4))
    elif kind == "ever":
        lax.add_patch(Circle((5, y), 2.2, fc=C["ever"], ec=C["treeE"], lw=0.4, alpha=0.5))
    elif kind == "fruit":
        lax.add_patch(Circle((5, y), 2.4, fc=C["fruit"], ec=C["treeE"], lw=0.4, alpha=0.38))
    elif kind == "climb":
        lax.add_patch(Circle((5, y), 3.0, fc=C["tree"], ec=C["ink"], lw=0.6, ls=(0, (2, 1)), alpha=0.6))
    elif kind.startswith("g:"):
        lax.add_patch(Circle((5, y), 1.7, fc=GC[kind[2:]], ec=C["treeE"], lw=0.4, alpha=0.6))
    elif kind == "amaniwa":
        lax.add_patch(Rectangle((1, y - 1.4), 8, 2.8, fc="#F2EFE6", ec="#8C8677", lw=0.3, hatch="o."))
        lax.add_patch(Circle((6.5, y), 0.8, fc="#8C8677", ec="#4A4438", lw=0.3))
    elif kind == "gyoji":
        lax.add_patch(Circle((5, y), 2.0, fc="#C9D99A", ec="#6F8F57", lw=0.4, ls=(0, (1.2, 0.8))))
    elif kind == "seki":
        for _dx in (3.2, 6.8):
            lax.add_patch(Circle((_dx, y), 1.1, fc="#D8D2C2", ec="#6B655B", lw=0.3))
    elif kind == "water":
        lax.add_patch(Rectangle((1, y - 1), 8, 2, fc=C["water"], ec="#4C8DB8", lw=0.3))
    elif kind == "trench":
        lax.add_patch(Rectangle((1, y - 1.2), 8, 2.4, fc="#D9D4C6", ec="#8C8677", lw=0.3, hatch="oo"))
    elif kind == "jets":
        lax.add_patch(Rectangle((1, y - 2), 8, 4, fc="#E6E3DA", ec="#8C8677", lw=0.4))
        for xx in (2.6, 5, 7.4):
            lax.add_patch(Circle((xx, y), 0.45, fc="#4C8DB8", ec="none"))
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
    lines = textwrap.wrap(txt, WRAP)
    lax.text(13, y - (len(lines) - 1) * 1.3, "\n".join(lines), fontsize=6.2, va="center", ha="left", linespacing=1.15)
    return len(lines)

def para(y, t, size=6.0, indent=0):
    lines = textwrap.wrap(t, WRAP + 6, subsequent_indent="　" if t.startswith("・") else "")
    lax.text(indent, y, "\n".join(lines), fontsize=size, va="top", ha="left", linespacing=1.25)
    return y + len(lines) * 2.65 + 1.2

y = 4
lax.text(0, y, "凡例", fontsize=8, fontweight="bold", va="center"); y += 8
from collections import Counter as _Ct
_cnt = _Ct(sp_of(t[4]) for t in G["TREES"])
rows = [("g:" + g, g + "：" + "・".join(f"{k} {_cnt[k]}" for k in SP if k != "_" and SP[k]["g"] == g and _cnt[k])) for g in GC] + [
        ("climb", "木登りの木（エノキ、下は木のチップ）"), ("gyoji", "行事の草：セリ・ショウブ・摘み草・ススキ・キク"),  ("seki", "飛び石：ホールの前から縁側沿いにしずかのもりへ。境は石や柵で示さず、「ここからは しずかに」と伝えるだけ（ユーザー：入ってだめなわけではない）。招かれた入口は柳の家をくぐる道"), ("water", "小川（幅 0.5、岸は急、底は平らで浅い。終わりは護岸の溝を滑り落ちる、破線は暗渠）"), ("jets", "床の噴水（水遊び場、上水をためずに一度だけ使う、排水は雨の川へ。ポンプなし、弁はシャワーの柱の隣のバルブます）。上に輪のシャワー「あめのわ」。0〜2歳の前にも小さな床の噴水（φ4.0、低い泡と霧のわ、南のカツラの木陰）"), ("trench", "雨の川（雨落ちの溝、玉石。本館の雨は樋なしで落ち、南へ流れて雨庭へ。大雨で溢れたらすりばちが雨の池）"), ("amaniwa", "雨庭（洲浜）：玉石の浜の浅いくぼみ −0.25、下に砕石。初めの約5 mmの雨を溜めてしみ込ませ、溢れた分だけ護岸の溝から高野川へ。景石3、ミソハギ（盆花）・ギボウシ・カンスゲ・ハンゲショウ"),
        ("sand", "砂場・粒の遊び場（1〜2 mm、2.4×3.0 の木の縁、帆布を巻いた棒を転がして「おやすみね」とカバー）"), ("cont", "等高線 0.2 m（太線 1.0 m）"), ("veh", "剪定・搬入の車の道（芝の保護材 幅 2.5、ふだんは庭）"),
        ("eye", "先生のいる所（縁側の外の縁・小屋の軒、目の高さ GL+1.35）"), ("hidden", f"死角：どの先生からも子どもの頭（地面+{CH}）が見えない所")]
for k, t in rows:
    n = sw(y, k, t); y += (3.4 if k.startswith("g:") else 4.0) + 2.6 * n
y += 3
lax.text(0, y, "ニッチ（静かに遊べる・ひとりになれる所）", fontsize=8, fontweight="bold", va="center"); y += 7
for k, (a, d, txt) in enumerate(G["NICHES"], 1):
    lax.add_patch(Circle((5, y), 2.4, fc="white", ec=C["ink"], lw=0.5)); lax.text(5, y, str(k), fontsize=5.6, ha="center", va="center")
    lines = textwrap.wrap(txt, WRAP)
    lax.text(13, y - 1.2, "\n".join(lines), fontsize=6.2, va="top", linespacing=1.2); y += 3.6 + 2.6 * len(lines)
y += 4

# 数字
ga = GARDEN.area; sa = SHIZU.area
mfoot = float((gc.mound_h(AA, DD) > 0.02).sum() * STEP * STEP)
mvol = float(gc.mound_h(AA, DD).sum() * STEP * STEP)
bvol = 0.0
for b in G["BUMPS"]:
    bvol += float(gc.bump_h(AA, DD, b).sum() * STEP * STEP)
bankv = float((gc.bank_h(AA, DD)).sum() * STEP * STEP) + float(gc.tilt_h(AA, DD).sum() * STEP * STEP)
bowlv = float(-gc.bowl_h(AA, DD).sum() * STEP * STEP)
s_len = LineString(XS(s["line"])).length
hid_a = HIDDEN.area
NUM = dict(garden=ga, shizu=sa, mfoot=mfoot, mvol=mvol, fill=mvol + bvol + bankv, cut=bowlv, stream=s_len, trees=len(G["TREES"]), hidden=hid_a,
           hut=(a_c - a_0) * (d_1 - d_0), wc=(H["split_a"] - a_0) * (d_1 - d_0), store=(a_c - H["split_a"]) * (d_1 - d_0), cbay=(a_1 - a_c) * (d_1 - d_0))
CALC = json.load(open(os.path.join(gc.ROOT, "out", "garden_calc.json"), encoding="utf-8"))
lax.text(0, y, "数字（この図から）", fontsize=8, fontweight="bold", va="center"); y += 7
_hut_all = NUM["hut"] + NUM["cbay"]
for t in [f"だいさんかく（しずかのもりを含む）約 {ga:.0f} m²。屋外遊戯場として数えるのは小屋（便所・倉庫・コンポストの間 約 {_hut_all:.0f} m²）を除いた 約 {ga - _hut_all:.0f} m²（2 歳以上 70 人で 1 人 約 {(ga - _hut_all) / 70:.1f} m²、基準は 3.3）。うち しずかのもり 約 {sa:.0f} m²",
          f"築山：頂 +{G['MOUND']['h']} m、裾の広さ 約 {mfoot:.0f} m²、土 約 {mvol:.0f} m³。起伏・土手を足すと盛る土は 約 {NUM['fill']:.0f} m³",
          f"　→ おくのもりへの上り（最大 +0.7）・かぜのもりの林床・土手 +1.0 も含めて締め固め 約 {CALC['soil']['fill_m3']} m³。運び込まない。本館の床は床下空間（根切り GL−0.6、ユーザー）で、掘る土は 約 {CALC['soil']['total_cut_m3']} m³（本館 約 {CALC['soil']['honkan_cut_m3']}、西館ほか 約 {CALC['soil']['west_cut_m3']}、園庭 約 {CALC['soil']['garden_cut_m3']}）",
          f"小川：地上の長さ 約 {s_len:.0f} m、みなもとの小さな滝（落差 約0.45）から、川床は滝壺 +0.05 → −0.40（地面から0.15以上下げる）。水深 3〜5 cm で 約 {CALC['stream']['rows'][0]['Q_Ls']:.0f}〜{CALC['stream']['rows'][1]['Q_Ls']:.0f} L/s（流れ 0.3〜0.4 m/s）。用水路の口の堰板で加減、大雨は水門を閉じる",
          f"木 {len(G['TREES'])} 本（{len(_cnt)} 種）。噴水の夏の日陰（7 月下旬）：9 時 {CALC['fountain_shade_jul'][0]['shaded']:.0%}、10〜13 時 約 {sum(r['shaded'] for r in CALC['fountain_shade_jul'][1:5]) / 4:.0%}（南東のケヤキ）、15 時 {CALC['fountain_shade_jul'][6]['shaded']:.0%}、16 時 {CALC['fountain_shade_jul'][7]['shaded']:.0%}（本館の影）。休むのは縁側の庇の下",
          f"床の噴水：約 {fpoly.area:.0f} m²、噴き口 {nj} 個（0.8 m ごと）＋輪のシャワー「あめのわ」。上水、排水は雨の川へ。雨の川：屋根 約 880 m²、100 mm/h で南の端 約 24 L/s、溝 0.5×0.2・1/200 で 約 50 L/s（目安）",
          f"小屋：便所 {NUM['wc']:.1f}＋倉庫 {NUM['store']:.1f}＋コンポストの間 {NUM['cbay']:.1f} m²（一つの屋根）。倉庫は教材庫×2（13.0）＋遊戯室の道具入れ（5.7）に足して 30 m² を超える",
          "コンポスト：小屋の倉庫の南東、屋根の下の壁のない間に木枠 4 つ（落ち葉・入れる・寝かせる・できた、全体 約 4.6×1.2）。4・5 歳の当番がキッチンから野菜くずをもらい、落ち葉と重ね、できた土を入口の前の菜園へ運ぶ（ユーザー）",
          f"土の使い道（ユーザー：無理なく使える分だけ）：表土 約 {CALC['soil']['topsoil_m3']} m³ は全部敷地に残す（築山の表面 0.2・木の下の林床 0.2 約 {CALC['soil']['woods_m2']} m²・菜園）。下の土は築山の芯・土手・林床の盛り・西館の床の下へ。外へ出すのは下の土 約 {CALC['soil']['out_subsoil_m3']} m³（近くの工事へ）",
          f"死角：約 {hid_a:.0f} m²。築山の裏（隣家側）の植え込み（てんぐのたに）と、おくのもりの奥。植え込みは入らない所にする"]:
    y = para(y, t)
y += 4
_KEEP = ["・高木は枝下 2 m 以上に仕立て、目の高さを見通す。低木は 60 cm 以下（大人は上から見える、子どもは隠れられる）。",
          "・縁側の外の縁と小屋の軒から全体が見える。見えない所（赤の斜線）は植え込みで入らない所にする。",
          "・毒・とげ・かぶれの木は使わない（キョウチクトウ・イチイ・アセビ・ピラカンサ・ハゼ・エゴノキ・ジンチョウゲ・ツツジ類 など）。ロウバイ（種に毒）は園庭に置かない（本館の読書の庭へ）。",
          "・ツバキ・サザンカは植えない（チャドクガ）。落葉樹が中心、落ち葉は遊びに使い、掃くのは小径と縁側の前だけ。",
          "・木登りの木は決めておく（2 本まで）。下は剪定の枝でつくった木のチップ（剪定 → チップ → 根もと、を園の中で回す）。",
          "・水は浅く（小川 3〜5 cm）、床の噴水は水がたまらず外縁側のすぐ前（濡れたまま縁側へ、シャワーの柱）。子どもが手や口にふれる水は上水だけ（小川の水は飲まない、遊んだら足洗い場で洗う）。",
          "・縁側の前 1.5 m は木を植えない（出入りと見通し）。車の道は要素の間を縫う目安（車のために木や遊び場をずらさない）。"]
print("legend_end_mm", round(LY + y), "section_top_mm", 40 + PLAN_H + 22)

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
    sl = LineString(s["line"])
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
    # 小川が護岸の溝を滑り落ちて、河川敷の細い溝で高野川へ
    iw = np.where((e > -0.6) & (e < 12.0))[0]
    zw = np.where(e[iw] < 1.0, np.minimum(z[iw], -0.12), z[iw]) + 0.06   # 立ち上がりは溝で切る
    sax.plot(tt[iw], zw, c="#2F6E95", lw=1.6, zorder=8, solid_capstyle="round")
    sax.text(x0 + 2.6, -2.9, "護岸の溝を\n滑り落ちる", fontsize=5.6, color="#2F6E95")
    # のぞきの段と子ども
    person(x0 - 0.3, 0.0, 1.05)
    eye = (x0 - 0.3, 0.95)
    wx = tt[np.where(e > 11.0)[0][0]] + 1.5 if (e > 11.0).any() else x0 + 12
    sax.plot([eye[0], wx], [eye[1], -4.6], c="#4C8DB8", lw=0.6, ls=(0, (3, 2)), zorder=7)
    sax.text(x0 + 3.0, -1.0, "柵の際（生垣の口）まで来ると\n水面が見える", fontsize=5.6, color="#4C8DB8")
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


sa_y = 40 + PLAN_H + 22
section("A", sa_y, "断面 A–A　ホールから築山の頂を通って比叡山の向きへ　1/100", deco_A, zmin=-1.0, zmax=6.6)
section("B", sa_y + 92, "断面 B–B　築山から原っぱ・のぞき（生垣の口）を通って高野川へ　1/100（崖・河川敷の寸法は仮）", deco_B, zmin=-5.2, zmax=4.6)

fx(406 / PW, 6 / PH, "こどもたちの育ち舎　garden01.py（data/garden.json・sodachiya_exact_mesh.3dm から）", fontsize=5.2, ha="right", color="#888888")
os.makedirs(OUT, exist_ok=True)
# 保母さんが困らないように（ページの下、全幅）
_yb = sa_y + 92 + (4.6 + 5.2) * SCS + 14
fx(14 / PW, 1 - _yb / PH, "保母さんが困らないように（木と地形の約束）", fontsize=8, fontweight="bold", ha="left", va="top")
_yb += 6
for t in _KEEP:
    for ln_ in textwrap.wrap(t, 175, subsequent_indent="　"):
        fx(14 / PW, 1 - _yb / PH, ln_, fontsize=6.0, ha="left", va="top"); _yb += 2.75
    _yb += 0.6
print("bottom_end_mm", round(_yb))
fig.savefig(os.path.join(OUT, "sodachiya_garden_01.pdf"))
fig.savefig(os.path.join(OUT, "sodachiya_garden_01.png"), dpi=110)
import json as _j
print(_j.dumps({k: round(v, 1) if isinstance(v, float) else v for k, v in NUM.items()}, ensure_ascii=False))
