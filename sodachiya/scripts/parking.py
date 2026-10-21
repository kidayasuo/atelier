import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import math, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt
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
WB = WN.difference(SP([W(23.5, -0.5), W(20.3, -3.4), W(20.3, -0.5)]))      # small chamfer, inside the doma strip only

# road frame: s along the road from the park corner (north = +), d into the site (east = +)
A0 = np.array((-21.91, -73.65)); B0 = np.array((-25.83, -20.54))
tt = (B0 - A0) / np.linalg.norm(B0 - A0); nn = np.array([tt[1], -tt[0]]); nn = nn if nn[0] > 0 else -nn
def P(s, d): p = A0 + tt * s + nn * d; return (float(p[0]), float(p[1]))
def Q(pts): return [P(*q) for q in pts]
def srect(s0, s1, d0, d1): return Q([(s0, d0), (s1, d0), (s1, d1), (s0, d1)])

C = dict(par="#FBE7CF", kid="#E2EDD0", red="#C8372D", path="#8a5a2b", blue="#3d7fb0", green="#5a7a3a",
         car="#ECECEC", plaza="#EAD6B8", kit="#F0B98A", eat="#F7D3B0")

MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
XL, XR, YB, YT = -27.5, 1.5, -77.0, -37.0              # 29 x 40 m -> 1/200: 145 x 200 mm
axs = [fig.add_axes([(18 + k * 205) / 420, 62 / 297, 145 / 420, 200 / 297]) for k in range(2)]

def poly(ax, pts, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1):
    if hasattr(pts, "geom_type"):
        if pts.is_empty: return
        gs = [pts] if pts.geom_type == "Polygon" else [g for g in getattr(pts, "geoms", []) if g.geom_type == "Polygon"]
        for g in gs: poly(ax, list(zip(*g.exterior.xy)), fc, ec, lw, z, ls, hatch, alpha)
        return
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
def line(ax, pts, lw=0.5, c="black", ls="-", z=3):
    xs, ys = zip(*pts); ax.plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(ax, p, s, size=6, c="#222222", ha="center", va="center", rot=0, z=12, **kw):
    ax.text(p[0], p[1], s, fontsize=size, color=c, ha=ha, va=va, rotation=rot, zorder=z, clip_on=True, **kw)
def tree(ax, p, r=1.8):
    ax.add_patch(Circle(p, r, fc="#DCE8C8", ec=C["green"], lw=0.5, zorder=6, alpha=0.9))
    ax.add_patch(Circle(p, 0.14, fc=C["green"], ec="none", zorder=7))
def gate(ax, p, s=None, off=(0, 0), c=None):
    ax.add_patch(Circle(p, 0.45, fc=c or C["red"], ec="white", lw=0.6, zorder=11))
    if s: T(ax, (p[0] + off[0], p[1] + off[1]), s, 5.4, c=c or C["red"], weight="bold")
def num(ax, p, k):
    ax.add_patch(Circle(p, 0.7, fc="white", ec="black", lw=0.4, zorder=13)); T(ax, p, str(k), 5.6, z=14)
def walk(ax, pts, c=C["path"], lw=1.4):
    line(ax, pts, lw=lw, c=c, ls=(0, (3, 2)), z=9)
    a, b = np.array(pts[-2]), np.array(pts[-1])
    ax.add_patch(FancyArrowPatch(tuple(a + (b - a) * 0.5), tuple(b), arrowstyle="-|>", mutation_scale=9, color=c, lw=lw, zorder=9))
def cars(ax, s0, d0, n, along="d", depth=5.0, w=2.5, labels=None):
    """n stalls; along='d': stalls side by side along d, each s0..s0+depth (sign of depth = direction)."""
    for k in range(n):
        if along == "d": pts = srect(s0, s0 + depth, d0 + w * k, d0 + w * (k + 1))
        else:            pts = srect(s0 + w * k, s0 + w * (k + 1), d0, d0 + depth)
        poly(ax, pts, fc=C["car"], ec="#555555", lw=0.4, z=4)
        c = np.mean(pts, axis=0); T(ax, c, (labels[k] if labels else "P"), 5.6 if not labels else 4.8, c="#555555")
def hedge(ax, pts, lw=2.4, c=C["red"]):
    line(ax, Q(pts), lw=lw, c=c, z=8)

def base(ax):
    ax.set_xlim(XL, XR); ax.set_ylim(YB, YT); ax.set_aspect("equal"); ax.axis("off")
    poly(ax, SITE, fc="#FAFAF6", ec="black", lw=1.0, z=0)
    poly(ax, PARK, fc="#E3EDD3", ec=C["green"], lw=0.7, z=1)
    tree(ax, (-15.5, -74.0), 3.0); T(ax, (-17.5, -76.2), "公園", 7)
    T(ax, (-26.6, -56), "西の道路（歩道なし）", 6.5, rot=86)
    kid = SP(SITE).difference(SP(PARK)).intersection(SP(rect(-14, 40, 1.6, 40))).difference(SP(rect(0, 40, 0, 15)))
    poly(ax, kid, fc=C["kid"], ec="none", z=1)
    T(ax, W(-4.5, 6), "乳児の庭", 6.5, c=C["green"])
    poly(ax, rect(0, 36, 0, 15), fc="#F4F0E8", ec="black", lw=0.8, z=4)
    poly(ax, rect(21, 22.5, 0, 15), fc="#D9CBB4", ec="none", z=4.1)
    poly(ax, rect(0, 6, 0, 1.6), fc="#E4E1DA", ec="none", z=4.1)
    for u in [12, 18, 21, 30, 33]:
        line(ax, [W(u, 1.6), W(u, 12)], lw=0.4, z=4.2)
    line(ax, [W(0, 1.6), W(36, 1.6)], lw=0.4, z=4.2)
    for u, s in [(6, "0・1歳"), (15, "2歳"), (19.5, "医務"), (26.5, "ホール"), (31.5, "事務")]:
        T(ax, W(u, 7), s, 6, rot=-3)
    T(ax, W(21.75, 7.5), "海峡", 5, rot=-3)
    T(ax, W(3, 0.8), "受け取り\n土間", 4.4, rot=-3)
    for u in [6.6, 7.5, 8.4]:
        ax.add_patch(Circle(W(u, -0.05), 0.15, fc=C["blue"], ec="none", zorder=6))
    # porch + infant-garden fence
    poly(ax, [W(0, -1.0), W(0, 1.6), W(-4.0, 1.6), W(-4.2, -1.0)], fc="#EFE8DA", ec="#777777", lw=0.4, ls=(0, (4, 2)), z=3)
    T(ax, W(-2.1, 0.3), "ポーチ\n藤棚", 4.8)
    line(ax, [W(0, 1.6), W(-9.0, 1.6)], lw=1.2, c="#6b5a3a", z=4)
    # west building: kitchen moved to the south (same area), eating doma north of it
    poly(ax, WB, fc="#F6E3A4", ec="none", z=4)
    for (u0, u1, fc, s) in [(20, 26, C["kit"], "キッチン"), (26, 32, C["eat"], "食べる土間")]:
        g = SP(rect(u0, u1, -3.4, -22)).intersection(WB); poly(ax, g, fc=fc, ec="none", z=4.2)
        T(ax, W((u0 + u1) / 2, -9.5), s, 6, rot=-3)
    poly(ax, WB, fc="none", ec="black", lw=0.8, z=4.3)
    for ln, kw in [(SL([W(26, -3.4), W(26, -30)]), dict(lw=0.5)), (SL([W(20.6, -3.4), W(36, -3.4)]), dict(lw=0.4, c="#777777"))]:
        g = ln.intersection(WB)
        for q in getattr(g, "geoms", [g]):
            if not q.is_empty: line(ax, list(q.coords), z=4.4, **kw)
    T(ax, W(28.5, -2.0), "土間", 5, rot=87)
    # strait mouth canopy
    poly(ax, [W(20.0, 0.0), W(24.5, 0.0), W(24.5, -1.0), W(20.0, -3.6)], fc="none", ec="#555555", lw=0.5, ls=(0, (5, 3)), z=5)
    # north arrow + scale
    ax.annotate("", xy=(-1.0, -39.0), xytext=(-1.0, -42.0), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
    T(ax, (-1.0, -38.2), "N", 8)
    sx, sy = -12.0, -76.6
    for i in range(5):
        poly(ax, [(sx + 2 * i, sy), (sx + 2 * i + 2, sy), (sx + 2 * i + 2, sy + 0.3), (sx + 2 * i, sy + 0.3)], fc="black" if i % 2 == 0 else "white", lw=0.3, z=6)
    T(ax, (sx, sy - 0.6), "0", 5); T(ax, (sx + 10, sy - 0.6), "10 m", 5)

def kitchen_windows(ax):
    # south glass of the kitchen toward the plaza + 'today's lunch' window on the chamfer
    g = SL([W(19.5, -5.0), W(21.5, -5.0)]);
    pts = [W(20.3, -4.2), W(20.3, -10.0)]
    a = SL([W(26, -4.5), W(15, -4.5)]).intersection(WB.exterior); b = SL([W(26, -10.0), W(15, -10.0)]).intersection(WB.exterior)
    pa = min(getattr(a, "geoms", [a]), key=lambda q: q.distance(SPt(W(15, -4.5)))); pb = min(getattr(b, "geoms", [b]), key=lambda q: q.distance(SPt(W(15, -10))))
    line(ax, [(pa.x, pa.y), (pb.x, pb.y)], lw=2.2, c=C["blue"], z=6)
    line(ax, [W(23.2, -0.75), W(20.6, -3.1)], lw=3.0, c="#D85A30", z=6)

# ============================================================== A: parking south (by the park), plaza north (at the inlet)
ax = axs[0]; base(ax)
S_IN = 29.4                  # s of the west building's south face
# security line (inside = parents' realm)
inside = SP(Q([(S_IN, 1.3), (22.7, 1.3), (22.7, 5.3), (17.7, 5.3), (17.7, 10.3), (6.9, 10.3), (6.9, 16.0), (S_IN + 3, 16.0), (S_IN + 3, 1.3)]))
inside = inside.difference(SP(rect(0, 40, 0, 40))).difference(WB).intersection(SP(SITE))
poly(ax, inside, fc=C["par"], ec="none", z=1.5)
# parking: aisle perpendicular to the road, 3 stalls south + 2 north (one of them = delivery)
poly(ax, srect(12.2, 17.7, 0, 10.3), fc="#F2F2F2", ec="none", z=3)
cars(ax, 12.2, 0.1, 3, depth=-5.0)
cars(ax, 17.7, 0.1, 2, depth=5.0, labels=["搬入", "P"])
T(ax, P(14.95, 5.5), "車路 5.5", 5.2, c="#777777")
line(ax, Q([(12.2, -0.05), (17.7, -0.05)]), lw=2.0, c="#777777", z=8)
T(ax, P(14.95, -1.1), "乗入れ 1か所", 5, c="#555555", rot=86)
# delivery path to the kitchen (outside the line)
poly(ax, srect(22.7, S_IN, 0.1, 1.2), fc="#EEEEEE", ec="none", z=3)
T(ax, P(26.0, 0.65), "搬入路", 4.4, c="#555555", rot=86)
ax.add_patch(Circle(P(S_IN - 0.1, 0.7), 0.3, fc="#555555", zorder=8))
hedge(ax, [(S_IN, 1.3), (22.7, 1.3), (22.7, 5.3), (17.7, 5.3), (17.7, 10.3), (6.9, 10.3)])
line(ax, [P(6.9, 10.3), PARK[2], W(-9.0, 1.6)], lw=2.4, c=C["red"], z=8)
# remnant south of the parking: planting
poly(ax, SP(Q([(0, 0), (12.2, 0), (12.2, 10.3), (6.9, 10.3)])).difference(SP(PARK)), fc="#E9F0DF", ec="none", z=2)
for p in [P(4.0, 2.4), P(9.2, 9.2)]: tree(ax, p, 1.2)
# gates
gate(ax, P(7.4, 11.7), "公園の木戸", (-0.2, -1.4))
gate(ax, P(17.7, 7.8), "来客の門", (0.2, -1.4))
# path from the park along the main building (3 m), hedge on the parking side
poly(ax, srect(7.0, 26.0, 10.6, 13.3), fc="#E8DECB", ec="none", z=2)
T(ax, P(13.5, 11.9), "見送りの小径", 5.2, c=C["path"], rot=86)
# plaza (inlet)
plz = SP(Q([(22.8, 1.4), (S_IN + 0.5, 1.4), (S_IN + 2, 13.4), (17.8, 13.4), (17.8, 5.4), (22.8, 5.4)])).difference(WB).difference(SP(rect(0, 40, 0, 40)))
poly(ax, plz, fc=C["plaza"], ec="none", z=2.2)
T(ax, P(24.6, 2.5), "ひろば", 7.5, c="#8a5a2b")
# temizu (hand wash) at the arrival
poly(ax, srect(18.4, 20.2, 10.9, 12.9), fc="none", ec="#555555", lw=0.5, ls=(0, (4, 2)), z=7)
ax.add_patch(Circle(P(19.3, 11.9), 0.45, fc="#9cc3e0", ec=C["blue"], lw=0.5, zorder=8))
# tea pavilion / engawa-bench (roofed)
poly(ax, srect(24.0, 28.2, 4.2, 8.6), fc="none", ec="#555555", lw=0.6, ls=(0, (5, 3)), z=7)
line(ax, Q([(24.4, 4.6), (27.8, 4.6)]), lw=3.0, c="#8a5a2b", z=7)
line(ax, Q([(24.4, 8.2), (27.8, 8.2)]), lw=3.0, c="#8a5a2b", z=7)
line(ax, Q([(26.1, 5.6), (26.1, 7.2)]), lw=2.0, c="#6b4b2a", z=7)
# kitchen garden + kamado
for k in range(3):
    poly(ax, srect(23.4 + k * 1.5, 24.4 + k * 1.5, 9.0, 11.2), fc="#d9e6bf", ec=C["green"], lw=0.4, z=6)
ax.add_patch(Circle(P(19.0, 6.6), 0.75, fc="#C9A97A", ec="#6b4b2a", lw=0.6, zorder=8))
tree(ax, P(21.3, 7.6), 1.9)
kitchen_windows(ax)
walk(ax, [P(7.4, 11.7), P(12, 11.9), P(19.3, 11.9)])
walk(ax, [P(19.3, 11.9), P(26.5, 12.5), W(21.75, -0.3)])
walk(ax, [P(7.4, 11.7), W(-4.0, 0.0)], c="#b08a5b", lw=1.0)
walk(ax, [P(17.7, 7.8), P(19.0, 10.6)], c="#b08a5b", lw=1.0)
for p, k in [(P(7.4, 13.6), 1), (P(19.3, 14.2), 2), (P(22.9, 6.4), 3), (P(22.4, 10.0), 4), (P(19.0, 4.8), 5),
             (W(21.2, -6.6), 6), (W(23.9, -2.8), 7), (P(20.0, -1.1), 8), (P(16.2, 9.4), 9), (W(21.75, 1.8), 10)]:
    num(ax, p, k)

# ============================================================== B: parking north (by the kitchen), plaza south (by the park)
ax = axs[1]; base(ax)
inside = SP(Q([(0, 0.2), (15.2, 0.2), (15.2, 10.6), (S_IN + 3, 10.6), (S_IN + 3, 16), (0, 16)])).difference(SP(PARK))
inside = inside.difference(SP(rect(0, 40, 0, 40))).difference(WB).intersection(SP(SITE))
poly(ax, inside, fc=C["par"], ec="none", z=1.5)
# parking: aisle along the road, stalls perpendicular on the east side, entrance at the north end
poly(ax, srect(15.2, S_IN, 0, 5.5), fc="#F2F2F2", ec="none", z=3)
cars(ax, 16.6, 5.5, 5, along="s", depth=5.0, labels=["P", "P", "P", "P", "搬入"])
T(ax, P(20.0, 2.7), "車路 5.5", 5.2, c="#777777", rot=86)
line(ax, Q([(23.8, -0.05), (28.0, -0.05)]), lw=2.0, c="#777777", z=8)
T(ax, P(25.9, -1.1), "乗入れ 1か所", 5, c="#555555", rot=86)
ax.add_patch(Circle(P(S_IN - 0.1, 4.0), 0.3, fc="#555555", zorder=8))
T(ax, P(27.8, 3.2), "搬入口", 4.4, c="#555555")
hedge(ax, [(0.2, 0.2), (15.2, 0.2), (15.2, 10.6), (S_IN + 0.2, 10.6)])
line(ax, [P(0.2, 0.2), P(6.76, 9.91)], lw=0, c="none")
line(ax, [PARK[1], PARK[2], W(-9.0, 1.6)], lw=2.4, c=C["red"], z=8)
gate(ax, P(4.6, 6.8), "公園の木戸", (-1.6, 1.6))
gate(ax, P(15.2, 8.0), "来客の門", (2.4, 1.0))
# plaza (south, by the park and the porch)
plz = SP(Q([(1.0, 0.4), (15.0, 0.4), (15.0, 10.3), (10.0, 13.0), (7.2, 13.0)])).difference(SP(PARK)).difference(SP(rect(-6, 40, 0, 40)))
poly(ax, plz, fc=C["plaza"], ec="none", z=2.2)
T(ax, P(11.8, 5.0), "ひろば", 7.5, c="#8a5a2b")
# path north along the main building to the strait (2.8 m)
poly(ax, srect(13.0, S_IN + 1, 10.7, 13.3), fc="#E8DECB", ec="none", z=2)
T(ax, P(21.0, 12.0), "見送りの小径", 5.2, c=C["path"], rot=86)
# temizu at the park gate
poly(ax, srect(6.0, 8.0, 5.6, 7.6), fc="none", ec="#555555", lw=0.5, ls=(0, (4, 2)), z=7)
ax.add_patch(Circle(P(7.0, 6.6), 0.45, fc="#9cc3e0", ec=C["blue"], lw=0.5, zorder=8))
# tea pavilion
poly(ax, srect(8.8, 13.6, 0.9, 4.6), fc="none", ec="#555555", lw=0.6, ls=(0, (5, 3)), z=7)
line(ax, Q([(9.2, 1.3), (13.2, 1.3)]), lw=3.0, c="#8a5a2b", z=7)
line(ax, Q([(9.2, 4.2), (13.2, 4.2)]), lw=3.0, c="#8a5a2b", z=7)
line(ax, Q([(11.2, 2.2), (11.2, 3.4)]), lw=2.0, c="#6b4b2a", z=7)
# kitchen garden + kamado in the plaza, tree
for k in range(3):
    poly(ax, srect(1.8 + k * 1.4, 2.7 + k * 1.4, 1.0, 3.6), fc="#d9e6bf", ec=C["green"], lw=0.4, z=6)
ax.add_patch(Circle(P(13.4, 8.0), 0.75, fc="#C9A97A", ec="#6b4b2a", lw=0.6, zorder=8))
tree(ax, P(10.0, 8.4), 1.9)
line(ax, [W(23.2, -0.75), W(20.6, -3.1)], lw=3.0, c="#D85A30", z=6)
walk(ax, [P(4.6, 6.8), P(7.0, 6.6), P(11.0, 10.4), P(14.5, 12.0), P(26.5, 12.2), W(21.75, -0.3)])
walk(ax, [P(7.0, 6.6), W(-4.0, 0.0)], c="#b08a5b", lw=1.0)
walk(ax, [P(15.2, 8.0), P(13.0, 8.6)], c="#b08a5b", lw=1.0)
for p, k in [(P(3.0, 8.2), 1), (P(7.0, 8.6), 2), (P(11.2, 6.0), 3), (P(3.0, 4.8), 4), (P(13.4, 9.9), 5),
             (W(23.9, -2.8), 7), (P(25.9, -2.6), 8), (P(15.2, 11.6), 9), (W(21.75, 1.8), 10)]:
    num(ax, p, k)

# ============================================================== titles / legend
fig.text(18 / 420, 287 / 297, "育ち舎　アプローチ　駐車場（敷地内の車路）と保護者のひろば　A／B", fontsize=12.5, weight="medium", va="top")
fig.text(18 / 420, 279 / 297, "1/200（A3）　2026-10-21　5台（来客4＋搬入1）、道路からの乗入れは1か所。■ 線の内側（保護者の領域）　━ 赤＝セキュリティの線　● 赤＝線の出入口　┅ 登園の道すじ。"
         "キッチンは西館の南の角へ（食べる土間と入れ替え、面積は同じ）。西館の面取りは土間の部分だけ。",
         fontsize=6.5, va="top", color="#444444")
fig.text(18 / 420, 268 / 297, "A　駐車は南（公園寄り）、ひろばは北（入江、キッチンの前）", fontsize=10, weight="bold", va="top")
fig.text(223 / 420, 268 / 297, "B　駐車は北（キッチンの前、搬入が直結）、ひろばは南（公園とポーチの前）", fontsize=10, weight="bold", va="top")
leg = ["1　公園の木戸", "2　手水（屋根の下で手を洗う）", "3　お茶の縁台（屋根つき、保護者が一服）", "4　菜園", "5　かまど",
       "6　キッチンの南のガラス（ひろばから見える）", "7　「今日のごはん」の窓（面取りの壁）", "8　乗入れ 1か所（車路 5.5 m）", "9　来客の門（インターホン）", "10　海峡の口（先生が迎える）"]
for i, s in enumerate(leg):
    c, r = divmod(i, 5)
    fig.text((18 + 100 * c) / 420, (52 - 4.4 * r) / 297, s, fontsize=6.4, va="top")
notes = ("A：ひろばがキッチンと海峡の口の前にあり、食べ物・手水・一服・バイバイが一か所にまとまる。搬入は線の外の搬入路（約7 m）を手押しで。\n"
         "　 公園からの小径は駐車場の脇（生垣ごし）を通る。乳児の庭側の南端は植栽。\n"
         "B：搬入が車路の突き当たりでキッチンに直結。ひろばは公園とポーチの前で、0〜2歳の家族も同じひろばを使える。\n"
         "　 ただしキッチンの前は駐車場になり、ひろばからキッチンは見えない（食べ物は菜園・かまど・「今日のごはん」の窓で）。")
fig.text(223 / 420, 52 / 297, notes, fontsize=6.4, va="top", color="#333333", linespacing=1.6)
fig.savefig(_os.path.join(OUT, "sodachiya_parking_AB.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_parking_AB.png"), dpi=200)
