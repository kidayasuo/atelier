import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import math, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt, box
from shapely import affinity as af

plt.rcParams["font.family"] = "Noto Sans CJK JP"

CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX)
if TH_S < 0: TH_S += 2 * math.pi
def W(u, v):
    th = TH_S - u / RW; r = RW - v
    return (CX + r * math.cos(th), CY + r * math.sin(th))
def rect(u0, u1, v0, v1, n=8):
    return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]

SITE = [(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)]
PARK = [(-14.44, -83.04), (-21.91, -73.65), (-12.52, -66.18), (-5.05, -75.57)]
WN = pickle.load(open(_os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb'))['WN']
WN = af.scale(WN, 0.001, 0.001, origin=(0, 0))
CUT = WN.difference(SP([W(24.6, -0.5), W(20.3, -5.4), W(20.3, -0.5)]))

roadA, roadB = np.array((-21.91, -73.65)), np.array((-25.83, -20.54))
tt = (roadB - roadA) / np.linalg.norm(roadB - roadA)
nn = np.array([tt[1], -tt[0]]);  nn = nn if nn[0] > 0 else -nn
def R(y, d=0.0):                       # point on the road boundary at y, d m inside the site
    s = (y - roadA[1]) / tt[1]; p = roadA + tt * s + nn * d; return (p[0], p[1])
def PK(f):                             # point on the park's NW edge, f=0 road corner .. 1 NE corner
    a, b = np.array(PARK[1]), np.array(PARK[2]); p = a + (b - a) * f; return (p[0], p[1])

C = dict(pub="#FFFFFF", par="#FBE7CF", kid="#E2EDD0", bld="#F4F0E8", wb="#F6E3A4", kit="#F0B98A", eat="#F7D3B0",
         red="#C8372D", path="#8a5a2b", blue="#3d7fb0", green="#5a7a3a")

def poly(ax, pts, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1):
    if hasattr(pts, "geom_type"):
        if pts.is_empty: return
        if pts.geom_type == "GeometryCollection":
            for g in pts.geoms:
                if g.geom_type in ("Polygon", "MultiPolygon"): poly(ax, g, fc, ec, lw, z, ls, hatch, alpha)
            return
        gs = [pts] if pts.geom_type == "Polygon" else list(pts.geoms)
        for g in gs: poly(ax, list(zip(*g.exterior.xy)), fc, ec, lw, z, ls, hatch, alpha)
        return
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
def line(ax, pts, lw=0.5, c="black", ls="-", z=3):
    xs, ys = zip(*pts); ax.plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="round")
def T(ax, p, s, size=6, c="#222222", ha="center", va="center", rot=0, z=12, **kw):
    ax.text(p[0], p[1], s, fontsize=size, color=c, ha=ha, va=va, rotation=rot, zorder=z, clip_on=True, **kw)
def tree(ax, p, r=2.0):
    ax.add_patch(Circle(p, r, fc="#DCE8C8", ec=C["green"], lw=0.5, zorder=5, alpha=0.9))
    ax.add_patch(Circle(p, 0.15, fc=C["green"], ec="none", zorder=6))
def gate(ax, p, s=None, off=(0, 0)):
    ax.add_patch(Circle(p, 0.55, fc=C["red"], ec="white", lw=0.6, zorder=11))
    if s: T(ax, (p[0] + off[0], p[1] + off[1]), s, 5.6, c=C["red"], weight="bold")
def walk(ax, pts, c=C["path"], lw=1.6):
    line(ax, pts, lw=lw, c=c, ls=(0, (3, 2)), z=8)
    a, b = np.array(pts[-2]), np.array(pts[-1])
    ax.add_patch(FancyArrowPatch(tuple(a + (b - a) * 0.6), tuple(b), arrowstyle="-|>", mutation_scale=9, color=c, lw=lw, zorder=8))
def stones(ax, pts, r=0.35):
    for p in pts: ax.add_patch(Circle(p, r, fc="#BFAF95", ec="#555555", lw=0.3, zorder=7))
def lerp(pts, k):
    out = []
    for (a, b) in zip(pts[:-1], pts[1:]):
        for i in range(k): out.append((a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k))
    return out
def cars(ax, y0, n, d0=0.3, depth=5.0):
    for k in range(n + 1):
        a = np.array(R(y0 + 2.5 * k * tt[1] / abs(tt[1]), d0))
    base = np.array(R(y0, d0))
    for k in range(n + 1):
        a = base + tt * 2.5 * k; line(ax, [tuple(a), tuple(a + nn * depth)], lw=0.4)
    for k in range(n):
        a = base + tt * (2.5 * k + 1.25) + nn * depth / 2; T(ax, a, "P", 6, c="#555555")
def delivery(ax, y0=-48.6):
    a = np.array(R(y0, 0.3)); b = a + tt * 3.2
    poly(ax, [tuple(a), tuple(b), tuple(b + nn * 6.0), tuple(a + nn * 6.0)], fc="#EEEEEE", ec="#555555", lw=0.4, z=3)
    c = a + tt * 1.6 + nn * 3.0; T(ax, c, "搬入\nP", 5.2, c="#555555")

STRIP = SP(SITE).difference(SP(PARK)).difference(SP(rect(-12, 60, 0, 40))).intersection(box(-40, -90, 40, -44.32)).difference(WN)

def base(ax, title, sub, west=CUT):
    ax.set_xlim(-29, 8); ax.set_ylim(-85, -35); ax.set_aspect("equal"); ax.axis("off")
    poly(ax, SITE, fc="#FAFAF6", ec="black", lw=0.9, z=0)
    poly(ax, PARK, fc="#E3EDD3", ec=C["green"], lw=0.6, z=1)
    tree(ax, (-13.5, -75.5), 3.2); T(ax, (-13.4, -80.3), "公園", 6.5)
    T(ax, (-27.6, -55), "西の道路", 6.5, rot=86)
    # children's realm east of the fence (infant garden + garden)
    kid = SP(SITE).difference(SP(PARK)).intersection(SP(rect(-14, 40, 1.6, 40))).difference(SP(rect(0, 40, 0, 15)))
    poly(ax, kid, fc=C["kid"], ec="none", z=1)
    T(ax, W(-5, 9), "乳児の庭", 5.8, c=C["green"]); T(ax, W(27, 16.2), "園庭", 6.5, c=C["green"])
    poly(ax, rect(0, 40, 0, 15), fc=C["bld"], ec="black", lw=0.7, z=4)
    poly(ax, rect(21, 22.5, 0, 15), fc="#D9CBB4", ec="none", z=4.1)
    poly(ax, rect(0, 6, 0, 1.6), fc="#E4E1DA", ec="none", z=4.1)
    for u, s in [(6, "0・1歳"), (15, "2歳"), (26.5, "ホール"), (31.5, "事務"), (36.5, "3歳")]:
        T(ax, W(u, 7), s, 5.6, rot=-3)
    T(ax, W(21.75, 7.5), "海峡", 4.6, rot=-3)
    line(ax, [W(0, 1.6), W(-9.0, 1.6)], lw=1.0, c="#6b5a3a", z=4)       # infant garden fence
    poly(ax, west, fc=C["wb"], ec="black", lw=0.7, z=4)
    bb = ax.get_position()
    fig.text(bb.x0 + 0.01, bb.y1 + 0.036, title, fontsize=10, weight="bold", va="top")
    fig.text(bb.x0 + 0.01, bb.y1 + 0.019, sub, fontsize=6.4, va="top", color="#444444", linespacing=1.45)

def kitchen_std(ax, west=CUT):
    for (u0, u1, fc, s) in [(20, 24, C["eat"], "食べる土間"), (24, 30, C["kit"], "キッチン")]:
        g = SP(rect(u0, u1, -3.4, -20)).intersection(west); poly(ax, g, fc=fc, ec="none", z=4.2)
        T(ax, W((u0 + u1) / 2, -10), s, 5.2, rot=-3)
    poly(ax, west, fc="none", ec="black", lw=0.7, z=4.3)

def kitchen_sw(ax, west=CUT, passage=False):
    rows = [(20, 24, C["kit"], "キッチン"), (25.8 if passage else 24, 30, C["eat"], "食べる土間")]
    for (u0, u1, fc, s) in rows:
        g = SP(rect(u0, u1, -3.4, -20)).intersection(west); poly(ax, g, fc=fc, ec="none", z=4.2)
        T(ax, W((u0 + u1) / 2 + 0.4, -9), s, 5.2, rot=-3)
    poly(ax, west, fc="none", ec="black", lw=0.7, z=4.3)
def delivery_sw(ax):          # delivery pocket at the SW corner, outside the fence, door into the kitchen
    a = np.array(R(-44.6, 0.3)); b = a - tt * 3.2
    poly(ax, [tuple(a), tuple(b), tuple(b + nn * 6.0), tuple(a + nn * 6.0)], fc="#EEEEEE", ec="#555555", lw=0.4, z=3)
    c = a - tt * 1.6 + nn * 3.0; T(ax, c, "搬入\nP", 5.2, c="#555555")
    line(ax, [tuple(b), tuple(b + nn * 6.3), tuple(a + nn * 6.3)], lw=1.4, c=C["red"], z=6)
    ax.add_patch(Circle(tuple(a + nn * 4.5), 0.3, fc="#555555", zorder=7))


def perimeter(ax, park_gate=None, c=C["red"], lw=2.2):
    """road fence with a guest-parking pocket (4 cars) outside it, park-edge fence; delivery pocket at the SW corner."""
    pts = [R(-47.8, 0.2), R(-55.8, 0.2), R(-55.8, 5.6), R(-66.4, 5.6), PK(0.62), PARK[2]]
    line(ax, pts, lw=lw, c=c, z=6)
    cars(ax, -66.2, 4, d0=0.3, depth=5.0)
    T(ax, R(-61.0, 6.6), "来客P 4台（線の外）", 4.6, c="#555555", rot=86)
    delivery_sw(ax)
    poly(ax, SP([PK(0.0), R(-66.4, 0.2), R(-66.4, 5.6), PK(0.62)]), fc="#E9F0DF", ec="none", z=1.6)
    return pts
def passage_block(ax):
    kitchen_sw(ax, W2, passage=True)
    poly(ax, hashiri, fc="#E8DECB", ec="none", z=4.4)
    for u in (24.0, 25.8):
        line(ax, [W(u, -3.4), W(u, -12.8)], lw=0.5, z=4.5)
    line(ax, [W(24.0, -4.5), W(24.0, -11.5)], lw=2.2, c=C["blue"], z=5)
    poly(ax, rect(24.2, 25.6, -5.5, -11), fc="none", ec="#777777", lw=0.5, ls=(0, (4, 2)), z=5)
hashiri = SP(rect(24.0, 25.8, -0.5, -30)).intersection(WN)
W2 = WN.difference(hashiri)
gx = SL([W(24.9, -5), W(24.9, -40)]).intersection(WN.exterior)
gp = (gx.x, gx.y) if gx.geom_type == "Point" else (list(gx.geoms)[-1].x, list(gx.geoms)[-1].y)
DOOR = ((R(-66.4, 5.6)[0] + PK(0.62)[0]) / 2, (R(-66.4, 5.6)[1] + PK(0.62)[1]) / 2)

def edge_pt(p0, p1, far=True, geom=None):
    g = SL([p0, p1]).intersection((geom or CUT).exterior)
    pts = [g] if g.geom_type == "Point" else list(getattr(g, "geoms", []))
    pts = sorted(pts, key=lambda q: q.distance(SPt(p0)))
    q = pts[-1] if far else pts[0]
    return (q.x, q.y)

fig = plt.figure(figsize=(400 / 25.4, 440 / 25.4))
fig.text(0.03, 0.985, "育ち舎　アプローチの5案と組み合わせ（ダイアグラム）", fontsize=14, weight="medium", va="top")
fig.text(0.03, 0.968, "2026-10-21　南半分、縮尺はおよそ 1/350。　■ 保護者の領域（セキュリティの線の内側、子どもは通るだけ）　■ 子どもの庭　"
         "● 赤＝セキュリティの線の出入口　━ 赤＝線（塀・柵・生垣）　┅ 茶＝登園の道すじ",
         fontsize=7, va="top", color="#444444")
# legend swatches
axs = []
W_, H_ = 0.315, 0.405
for i in range(6):
    c, r = i % 3, i // 3
    axs.append(fig.add_axes([0.02 + c * 0.325, 0.51 - r * 0.475, W_, H_]))

def zone(ax, g):
    poly(ax, g.intersection(SP(SITE)), fc=C["par"], ec="none", z=1.5)
def wall(ax, pts, lw=2.2, c=C["red"]):
    line(ax, pts, lw=lw, c=c, z=6)

# ---------------------------------------------------------------- 1 露地
ax = axs[0]
base(ax, "1　露地の門（茶庭）", "外露地で待ち、中門をくぐり、蹲踞で手を洗う。\n線は中門。外露地は来客と、開門前の保護者の場所。")
kitchen_sw(ax)
nakamon = [R(-60.0, 0.3), (-15.8, -60.6), PK(0.62)]
inner = STRIP.difference(SP([R(-90), R(-60.0, 0.3), (-15.8, -60.6), PK(0.62), (-12, -90)]))
zone(ax, inner)
outer = STRIP.difference(inner)
poly(ax, outer, fc="#F3F1EA", ec="none", z=1.5)
wall(ax, [R(-47.8, 0.2), R(-60.0, 0.3)]); wall(ax, nakamon, c="#6b8a3a", lw=2.6)   # hedge/sode-gaki
wall(ax, [PK(0.62), PARK[2]])
line(ax, [R(-60, 0.3), R(-73.0, 0.3)], lw=1.4, c="#999999", z=6)
gate(ax, (-15.8, -60.6), "中門", (2.2, -0.3))
ax.add_patch(Circle((-14.6, -59.3), 0.55, fc="#9cc3e0", ec=C["blue"], lw=0.5, zorder=9))
T(ax, (-12.0, -58.6), "蹲踞", 5.4, c=C["blue"])
line(ax, [(-19.6, -66.8), (-17.3, -63.6)], lw=2.4, c="#8a5a2b", z=7); T(ax, (-20.4, -63.6), "腰掛\n待合", 5.2)
T(ax, (-18.3, -69.8), "外露地", 6.2, c="#666666")
ax.add_patch(Circle(PK(0.35), 0.5, fc="#999999", ec="white", lw=0.6, zorder=11)); T(ax, (PK(0.35)[0] - 2.4, PK(0.35)[1] - 0.6), "木戸", 5.2, c="#666666")
cars(ax, -72.6, 4, depth=5.0)
st = lerp([PK(0.35), (-16.6, -62.8), (-15.8, -60.6), (-13.5, -57.0), W(4, -2.0), W(14, -2.6), W(20.5, -2.8), W(21.75, -0.4)], 3)
stones(ax, st[::1])
line(ax, [(-13.5, -57.0), W(-4.0, -0.4)], lw=1.4, c=C["path"], ls=(0, (3, 2)), z=8)
T(ax, W(-2.5, -3.6), "ポーチ\n(0〜2)", 5.0)
T(ax, W(9, -4.3), "内露地", 6.2, c="#8a5a2b")
delivery_sw(ax)
T(ax, R(-70.5, 6.8), "来客P 4台", 4.6, c="#555555", rot=86)


# ---------------------------------------------------------------- 2 走り庭
ax = axs[1]
base(ax, "2　走り庭（京町家）", "西館の南を土間の通り庭が東西に貫く。片側はキッチン（ガラス）、反対側は食べる土間、上は火袋。\n線は道路側の京格子（中から見え、外から見えにくい）。キッチンは南の角へ。", west=W2)
passage_block(ax)
T(ax, W(24.9, -8.2), "火袋", 4.6, rot=-3, c="#555555")
zone(ax, STRIP); zone(ax, SP(rect(20.0, 26, -0.0, -3.4)).difference(W2))
perimeter(ax)
gate(ax, gp, "京格子", (0.6, 1.5))
gate(ax, PK(0.8), "木戸", (1.4, -1.4))
walk(ax, [(gp[0] - 2.2, gp[1] + 0.3), gp, W(24.9, -1.5), W(23.0, -1.5), W(22.0, 0.6)])
walk(ax, [PK(0.8), W(-4.5, -2.0), W(4, -2.0), W(18, -2.0), W(21.0, -0.2)], c="#b08a5b", lw=1.1)
T(ax, W(16.5, -9.0), "毎朝、出汁の湯気の\n中を通って登園", 5.4, c=C["path"])
ax.set_xlim(-31, 6)

# ---------------------------------------------------------------- 3 walled garden
ax = axs[2]
base(ax, "3　壁の中の扉（walled garden）", "公園と道路の角に、塀の扉が一枚（大人用＋子ども用）。中はキッチンに面した菜園。\nキッチンは南の角へ。園庭と公園の境はハハー（沈めた柵）。")
kitchen_sw(ax)
zone(ax, STRIP)
perimeter(ax, c="#9a5b3a", lw=3.0)
gate(ax, DOOR, "扉（大＋小）", (-0.5, -1.6))
for k in range(4):
    u0 = 12.5 + k * 1.6
    poly(ax, rect(u0, u0 + 1.0, -2.8, -7.8, 2), fc="#d9e6bf", ec=C["green"], lw=0.4, z=5)
for k in range(3):
    u0 = 7.0 + k * 1.6
    poly(ax, rect(u0, u0 + 1.0, -2.8, -6.0, 2), fc="#d9e6bf", ec=C["green"], lw=0.4, z=5)
T(ax, W(10.0, -8.6), "菜園", 6.2, c=C["green"])
ax.add_patch(FancyArrowPatch(W(18.0, -6.0), W(21.0, -8.0), arrowstyle="-|>", mutation_scale=9, color=C["green"], lw=1.0, zorder=9))
T(ax, W(16.0, -10.6), "とれた野菜→キッチン", 4.8, c=C["green"])
walk(ax, [DOOR, (-15.0, -62.0), W(1, -4.0), W(-3.0, -0.5)], c="#b08a5b", lw=1.1)
walk(ax, [DOOR, (-15.0, -62.0), W(4, -1.8), W(12, -1.6), W(20.5, -1.8), W(21.75, -0.2)])
hh = [PARK[2], PARK[3]]
p0, p1 = np.array(PARK[2]), np.array(PARK[3]); dn = np.array([-(p1 - p0)[1], (p1 - p0)[0]]); dn = dn / np.linalg.norm(dn)
line(ax, [tuple(p0 + dn * 0.8), tuple(p1 + dn * 0.8)], lw=0.6, c="#555555", ls=(0, (2, 1.5)), z=6)
T(ax, tuple((p0 + p1) / 2 + dn * 3.0), "ハハー", 5.0, c="#555555", rot=-51)

# ---------------------------------------------------------------- 4 piazza
ax = axs[3]
base(ax, "4　ピアッツァ（レッジョ・エミリア）", "入江を保護者の広場に。外に見せるのは子どもではなく子どもの仕事（ドキュメンテーションの壁）。\nキッチンを南の角へ移し、広場からガラス越しに見せる。")
kitchen_sw(ax)
zone(ax, STRIP)
pz = SP([W(20.3, -0.3), W(24.6, -0.3), W(20.3, -5.4), W(20.3, -16), W(11.0, -16), W(11.0, -0.3)]).difference(CUT).intersection(STRIP.union(SP(rect(20, 25, 0, -3))).difference(CUT))
poly(ax, pz, fc="#EAD6B8", ec="none", z=1.7)
T(ax, W(15.0, -7.0), "広場", 7.5, c="#8a5a2b")
line(ax, [W(23.0, -2.7), W(20.5, -5.4)], lw=3.4, c="#D85A30", z=6)
T(ax, W(26.0, -4.0), "ドキュメン\nテーション\nの壁", 4.6, c="#D85A30")
gw = [edge_pt(W(26, v), W(15, v)) for v in (-5.6, -8.6)]
line(ax, gw, lw=2.4, c=C["blue"], z=6)
T(ax, W(18.6, -6.0), "キッチンのガラス", 4.8, c=C["blue"])
perimeter(ax)
gate(ax, PK(0.8), "木戸", (1.4, -1.4)); gate(ax, R(-51.8, 0.2), "道路の門", (3.2, -1.2))
walk(ax, [PK(0.8), W(-4.5, -2.0), W(4, -2.0), W(13, -2.6), W(18, -2.8), W(21.75, -0.2)])
walk(ax, [R(-51.8, 0.2), W(13.5, -5.0), W(18.5, -3.5)], c="#b08a5b", lw=1.1)
line(ax, [W(22.6, 0.3), W(23.9, 0.3)], lw=2.0, c="#6b4b2a", z=6)
T(ax, W(23.4, 2.2), "コーヒー", 4.6)
for u, v in [(13.0, -9.5), (15.6, -9.5)]:
    line(ax, [W(u, v), W(u + 1.4, v)], lw=2.2, c="#8a5a2b", z=6)
# ---------------------------------------------------------------- 5 waldorf
ax = axs[4]
base(ax, "5　迎えの場所とかまど（シュタイナー）", "ゆるく曲がる小径。木戸に季節のテーブル。\n海峡の口で先生が一人ずつ握手で迎える。入江にかまど。")
kitchen_sw(ax)
zone(ax, STRIP)
perimeter(ax)
gate(ax, PK(0.55), "木戸", (-0.2, -1.6))
poly(ax, [(-15.6, -67.0), (-14.0, -65.7), (-13.6, -66.2), (-15.2, -67.5)], fc="#E9C46A", ec="#8a5a2b", lw=0.5, z=9)
T(ax, (-10.8, -65.2), "季節の\nテーブル", 5.0, c="#8a5a2b")
ts = np.linspace(0, 1, 60)
ctrl = [PK(0.55), (-13.0, -62.0), (-17.0, -57.0), (-12.5, -51.5), (-15.0, -47.5), W(21.4, -1.5)]
from scipy.interpolate import CubicSpline
cx = CubicSpline(np.linspace(0, 1, len(ctrl)), [p[0] for p in ctrl]); cy = CubicSpline(np.linspace(0, 1, len(ctrl)), [p[1] for p in ctrl])
cur = [(float(cx(s)), float(cy(s))) for s in ts]
line(ax, cur, lw=7.0, c="#E8DECB", z=3)
walk(ax, cur[::3] + [W(21.75, -0.2)])
for p in [(-16.2, -55.5), (-12.8, -59.5), (-15.8, -49.5)]:
    tree(ax, p, 1.4)
ax.add_patch(Circle(W(21.75, -1.0), 1.1, fc="none", ec=C["red"], lw=0.9, ls=(0, (2, 1.5)), zorder=9))
T(ax, W(24.8, 2.6), "握手の場所", 5.0, c=C["red"])
ax.add_patch(Circle(W(16.0, -9.0), 0.9, fc="#C9A97A", ec="#6b4b2a", lw=0.6, zorder=8))
T(ax, W(16.0, -11.4), "かまど", 5.4, c="#6b4b2a")
T(ax, W(5.5, -6.5), "小径", 5.6, c="#8a5a2b")

# ---------------------------------------------------------------- 6 combination
ax = axs[5]
base(ax, "6　組み合わせ（2を骨格に、1・3を足す）", "公園からは塀の扉（大＋小）→ 菜園 → 蹲踞で手を洗う → 海峡。道路からは京格子 → 走り庭 → 海峡。\n線の出入口は2か所、どちらもインターホンで事務につながる。", west=W2)
passage_block(ax)
T(ax, W(24.9, -8.2), "火袋", 4.6, rot=-3, c="#555555")
zone(ax, STRIP); zone(ax, SP(rect(20.0, 26, -0.0, -3.4)).difference(W2))
perimeter(ax, c="#9a5b3a", lw=3.0)
gate(ax, DOOR, "扉（大＋小）", (-0.5, -1.6))
gate(ax, gp, "京格子", (0.6, 1.5))
for k in range(4):
    u0 = 11.0 + k * 1.6
    poly(ax, rect(u0, u0 + 1.0, -3.0, -8.0, 2), fc="#d9e6bf", ec=C["green"], lw=0.4, z=5)
T(ax, W(13.5, -9.6), "菜園", 5.8, c=C["green"])
ax.add_patch(Circle(W(19.6, -1.6), 0.55, fc="#9cc3e0", ec=C["blue"], lw=0.5, zorder=9))
T(ax, W(18.4, -3.6), "蹲踞", 5.0, c=C["blue"])
walk(ax, [DOOR, (-15.0, -62.0), W(4, -1.6), W(12, -1.6), W(19.0, -1.6), W(21.75, -0.2)])
walk(ax, [DOOR, (-15.0, -62.0), W(1, -4.0), W(-3.0, -0.5)], c="#b08a5b", lw=1.1)
walk(ax, [(gp[0] - 2.2, gp[1] + 0.3), gp, W(24.9, -1.5), W(23.0, -1.5), W(22.0, 0.6)], c="#b08a5b", lw=1.1)
ax.set_xlim(-31, 6)

fig.savefig(_os.path.join(OUT, "sodachiya_approach_ideas.png"), dpi=170)
fig.savefig(_os.path.join(OUT, "sodachiya_approach_ideas.pdf"))
