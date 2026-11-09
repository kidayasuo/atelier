import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import math, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt
from shapely import affinity as af

plt.rcParams["font.family"] = "Noto Sans CJK JP"

# ---------- geometry ----------
CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX)          # south frame angle (frame 19)
if TH_S < 0: TH_S += 2 * math.pi
def W(u, v):                     # u: m from south gable along the spine, v: m east of the spine
    th = TH_S - u / RW
    r = RW - v
    return (CX + r * math.cos(th), CY + r * math.sin(th))
def rect(u0, u1, v0, v1, n=8):
    return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]

SITE = [(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)]
SETB = [(-0.16, -1.41), (33.45, -43.67), (-14.28, -81.64), (-20.93, -73.27), (-24.79, -20.99)]
PARK = [(-14.44, -83.04), (-21.91, -73.65), (-12.52, -66.18), (-5.05, -75.57)]
WN = pickle.load(open(_os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb'))['WN']
WN = af.scale(WN, 0.001, 0.001, origin=(0, 0))
# cut the south-east corner of the west building -> the inlet ("入江") in front of the strait mouth
cut = SP([W(24.6, -0.5), W(20.3, -5.4), W(20.3, -0.5)])
WN2 = WN.difference(cut)

# ---------- page ----------
MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
xmin, xmax, ymin, ymax = -29.0, 10.0, -86.0, -33.0          # 1/200: 1 m = 5 mm
L, B = 25, 100
ax = fig.add_axes([L / 297, B / 420, (xmax - xmin) * 5 / 297, (ymax - ymin) * 5 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

def poly(pts, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1):
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
def line(pts, lw=0.5, c="black", ls="-", z=3):
    xs, ys = zip(*pts); ax.plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(x, y, s, size=6, c="#222222", ha="center", va="center", rot=0, z=9, **kw):
    ax.text(x, y, s, fontsize=size, color=c, ha=ha, va=va, rotation=rot, zorder=z, **kw)
def num(p, n):
    ax.add_patch(Circle(p, 0.75, fc="white", ec="black", lw=0.4, zorder=10))
    T(p[0], p[1], str(n), 5.6, z=11)
def tree(p, r=2.2, c="#5a7a3a"):
    ax.add_patch(Circle(p, r, fc="#DCE8C8", ec=c, lw=0.5, zorder=4, alpha=0.9))
    ax.add_patch(Circle(p, 0.18, fc=c, ec="none", zorder=5))

# ground
poly(SITE, fc="#FAFAF6", ec="black", lw=1.0, z=0)
poly(SETB, fc="none", ec="#999999", lw=0.3, ls=(0, (4, 3)), z=0.5)
# road (west) and river (south-east) labels
T(-27.6, -52, "西の道路", 7, rot=86)
T(8.0, -66.0, "高野川 →", 7, rot=38)

# park
poly(PARK, fc="#E3EDD3", ec="#5a7a3a", lw=0.7, z=1)
tree((-13.5, -74.8), 3.6)
T(-13.4, -79.6, "公園（12 × 12 m）\n待ち合わせの木", 6.5)

# ---------- main building (south half) ----------
COL = {"01": "#E6EFC2", "2": "#C5DE9A", "med": "#F7F3EA", "hall": "#E3C08D", "off": "#E9DCC4", "3": "#9FCB84",
       "void": "#F4EBDD", "eng": "#F4EBDD", "doma": "#E4E1DA", "strait": "#D9CBB4"}
poly(rect(0, 36, 0, 15), fc="#F6F2EA", ec="black", lw=0.8, z=2)
poly(rect(0, 12, 1.6, 12), fc=COL["01"], ec="none", z=2.1)
poly(rect(12, 18, 1.6, 12), fc=COL["2"], ec="none", z=2.1)
poly(rect(18, 21, 1.6, 12), fc=COL["med"], ec="none", z=2.1)
poly(rect(21, 30, 1.6, 12), fc=COL["hall"], ec="none", z=2.1)
poly(rect(30, 33, 1.6, 12), fc=COL["off"], ec="none", z=2.1)
poly(rect(33, 36, 1.6, 12), fc=COL["3"], ec="none", z=2.1)
poly(rect(0, 6, 0, 1.6), fc=COL["doma"], ec="none", z=2.2)        # receiving doma
poly(rect(21, 22.5, -0.05, 15), fc=COL["strait"], ec="none", z=2.3)  # strait (土足)
for u in [12, 18, 21, 30, 33]:
    line([W(u, 1.6), W(u, 12)], lw=0.5)
line([W(0, 1.6), W(36, 1.6)], lw=0.5)
line([W(0, 12), W(36, 12)], lw=0.4, c="#777777")
line([W(0, 15), W(36, 15)], lw=0.5)
line([W(0, 0), W(36, 0)], lw=1.2)
for (u, s) in [(6, "0・1歳"), (15, "2歳"), (19.5, "医務"), (26.5, "ホール"), (31.5, "事務"), (34.5, "3歳")]:
    p = W(u, 7); T(p[0], p[1], s, 6.5, rot=-3)
p = W(21.75, 7); T(p[0], p[1], "海 峡（土足）", 5.2, rot=-3)
p = W(3, 0.8); T(p[0], p[1], "受け取り\n土間", 4.6, rot=-3)
for u, v in [(21.75, 4.0), (21.75, 9.0)]:                           # stepping stones in the strait
    ax.add_patch(Circle(W(u, v), 0.5, fc="#BFAF95", ec="black", lw=0.3, zorder=3))
# south eave / porch / fence
poly([W(0, -1.0), W(0, 15), W(-1.8, 15), W(-4.2, -1.0)], fc="none", ec="#555555", lw=0.4, ls=(0, (5, 3)), z=3)
poly([W(0, -1.0), W(0, 1.6), W(-4.0, 1.6), W(-4.2, -1.0)], fc="#EFE8DA", ec="none", z=1.5)
line([W(0, 1.6), W(-9.5, 1.6)], lw=1.1, c="#6b5a3a")              # fence h1.2
p = W(-2.2, 0.3); T(p[0], p[1], "ポーチ\n藤棚", 5.2)
p = W(-4.5, 8); T(p[0], p[1], "乳児の庭", 6.5)

# ---------- west building ----------
x, y = WN2.exterior.xy
poly(list(zip(x, y)), fc="#F6E3A4", ec="black", lw=0.8, z=2)
# 1F zoning (south part): eating doma (south, glazed), kitchen, doma strip (east)
def wclip(pts):
    g = SP(pts).intersection(WN2)
    return [list(zip(*g.exterior.xy))] if g.geom_type == "Polygon" else [list(zip(*q.exterior.xy)) for q in g.geoms]
for pts in wclip(rect(20.0, 24.0, -3.4, -20)):
    poly(pts, fc="#F7D3B0", ec="none", z=2.1)
for pts in wclip(rect(24.0, 30.0, -3.4, -20)):
    poly(pts, fc="#F0B98A", ec="none", z=2.1)
for pts in wclip(rect(20.0, 33.0, -0.5, -3.4)):
    poly(pts, fc="#EFE6D2", ec="none", z=2.1)
x, y = WN2.exterior.xy
poly(list(zip(x, y)), fc="none", ec="black", lw=0.8, z=3)
line([W(24.0, -3.4), W(24.0, -15.5)], lw=0.5)
line([W(30.0, -3.4), W(30.0, -15.2)], lw=0.5)
line([W(23.2, -3.4), W(33.0, -3.4)], lw=0.4, c="#777777")
p = W(22.6, -9.5); T(p[0], p[1], "食べる土間", 6, rot=-3)
p = W(27.0, -9.5); T(p[0], p[1], "キッチン", 6.5, rot=-3)
p = W(27.0, -2.1); T(p[0], p[1], "土間", 5.2, rot=87)
p = W(34.0, -8.5); T(p[0], p[1], "遊戯室 →", 6.5, rot=-3)
# kitchen counter facing the eating doma, kitchen window to the road, delivery door
line([W(23.9, -4.0), W(23.9, -12.5)], lw=2.0, c="#8a5a2b", z=4)
def edge_pt(p0, p1, far=True):
    g = SL([p0, p1]).intersection(WN2.exterior)
    pts = [g] if g.geom_type == "Point" else list(getattr(g, "geoms", []))
    pts = sorted(pts, key=lambda q: q.distance(SPt(p0)))
    q = pts[-1] if far else pts[0]
    return (q.x, q.y)
kw = [edge_pt(W(u, -0.5), W(u, -30)) for u in (24.8, 29.2)]
line(kw, lw=2.0, c="#3d7fb0", z=5)
# glazing on the south face of the eating doma (toward the inlet)
gw = [edge_pt(W(26, v), W(15, v), far=False) for v in (-5.6, -10.6)]
line(gw, lw=2.0, c="#3d7fb0", z=5)
# display window ("today's lunch") in the diagonal wall
dp0, dp1 = W(23.0, -2.7), W(21.9, -3.9)
line([dp0, dp1], lw=3.2, c="#D85A30", z=5)

# ---------- inlet (forecourt), strait mouth, canopy ----------
inlet = SP([W(20.3, -0.6), W(24.6, -0.6), W(20.3, -5.4), W(20.3, -14.0), W(13.0, -14.0), W(13.0, -0.6)])
inlet = inlet.difference(WN2)
x, y = inlet.exterior.xy
poly(list(zip(x, y)), fc="#EDE4D3", ec="none", z=1.6)
# strait floor continues outside (土足, 洗い出し) as a widening band
poly([W(21.0, 0), W(22.5, 0), W(22.8, -2.6), W(19.5, -8.5), W(16.0, -8.5), W(20.3, -2.0)], fc=COL["strait"], ec="#8a7a60", lw=0.4, z=1.8)
for (u, v) in [(18.6, -9.6), (17.0, -10.8), (18.2, -12.2)]:
    ax.add_patch(Circle(W(u, v), 0.45, fc="#BFAF95", ec="black", lw=0.3, zorder=3))
# canopy over the mouth (monitor cap extended to the west building)
poly([W(20.0, 0.0), W(25.0, 0.0), W(25.0, -1.2), W(20.0, -4.6)], fc="none", ec="#555555", lw=0.5, ls=(0, (5, 3)), z=4)
tree(W(16.6, -5.2), 2.4)
line([W(15.3, -3.2), W(15.3, -6.8)], lw=2.4, c="#8a5a2b", z=5)    # bench under the tree
# coffee shelf at the strait entrance (inside)
line([W(22.6, 0.3), W(23.9, 0.3)], lw=2.0, c="#6b4b2a", z=5)

# ---------- path along the west wall ("見送りの小径") ----------
poly(rect(0.0, 13.0, -0.4, -2.4), fc="#E8DECB", ec="none", z=1.7)
line([W(0, -0.9), W(36, -0.9)], lw=0.4, c="#555555", ls=(0, (5, 3)))   # monitor cap overhang
for u in [6.6, 7.5, 8.4]:
    ax.add_patch(Circle(W(u, -0.05), 0.15, fc="#3d7fb0", ec="none", zorder=6))   # peek windows (kids' eye height)
for u in [2.2, 5.6, 9.0, 12.0]:
    ax.add_patch(Circle(W(u, -3.4), 0.55, fc="#E6EFD8", ec="#5a7a3a", lw=0.4, zorder=3))  # low planting (seasonal)
# ---------- parking (5, perpendicular to the road) and bikes ----------
roadA, roadB = np.array((-21.91, -73.65)), np.array((-25.83, -20.54))
t = (roadB - roadA) / np.linalg.norm(roadB - roadA); n = np.array([t[1], -t[0]])
if n[0] < 0: n = -n
def onroad(y):                          # point on the west boundary at given y
    s = (y - roadA[1]) / t[1]; return roadA + t * s
base = onroad(-66.6)
for k in range(6):
    a = base + t * 2.5 * k
    line([tuple(a), tuple(a + n * 5.5)], lw=0.4)
for k in range(5):
    a = base + t * (2.5 * k + 1.25) + n * 2.75
    T(a[0], a[1], "P", 6.5, c="#555555")
b0 = onroad(-54.0) + n * 0.3
for k in range(11):                      # bike racks
    a = b0 + n * (0.8 * k + 0.6)
    line([tuple(a), tuple(a + t * 1.8)], lw=0.6, c="#6b5a3a")
pb = b0 + n * 4.8 + t * 0.9
T(pb[0], pb[1], "駐輪", 5.5)
# gates
for g in [W(-4.4, -1.6), onroad(-50.0) + n * 0.4]:
    ax.add_patch(Circle(tuple(g), 0.35, fc="#6b5a3a", ec="none", zorder=6))

# ---------- numbers ----------
N = [((-13.4, -71.5), 1), (W(-3.0, -2.2), 2), (W(2.0, -4.6), 3), (W(7.0, -1.4), 4), (W(18.6, -6.5), 5), (W(21.75, -1.6), 6),
     (W(22.8, -4.6), 7), (W(21.0, -12.6), 8), (tuple(np.array(kw[0]) + np.array([-1.6, 0.6])), 9), (W(16.6, -5.2), 10), (W(23.2, 1.3), 11), (tuple(onroad(-60.0) + n * 7.2), 12), (tuple(onroad(-50.0) + n * 1.3), 13)]
for p, k in N:
    num(p, k)

# north arrow + scale
ax.annotate("", xy=(3.5, -38.5), xytext=(3.5, -41.5), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
T(3.5, -37.6, "N", 8)
sx, sy = -10.0, -84.6
for i in range(5):
    poly([(sx + 2 * i, sy), (sx + 2 * i + 2, sy), (sx + 2 * i + 2, sy + 0.35), (sx + 2 * i, sy + 0.35)], fc="black" if i % 2 == 0 else "white", lw=0.3, z=6)
for i, s in [(0, "0"), (5, "10 m")]:
    T(sx + 2 * i, sy - 0.8, s, 5)

fig.text(L / 297, 410 / 420, "育ち舎　アプローチ（南半分）たたき台", fontsize=12.5, weight="medium", va="top")
fig.text(L / 297, 402 / 420, "1/200（A3）　2026-10-20　公園 → ポーチ（0〜2歳）→ 見送りの小径 → 入江 → 海峡（3〜5歳）。破線は軒・キャップ・入江の屋根（頭上）。",
         fontsize=6.5, va="top", color="#444444")
legend = [
    "1　公園：待ち合わせの木。敷地への木戸",
    "2　ポーチと藤棚（0〜2歳の入口＝受け取り土間）",
    "3　見送りの小径 幅2.0（越屋根のキャップの下）",
    "4　0〜2歳の覗き窓（子どもの目の高さ）",
    "5　入江：海峡の床が外へひらく（洗い出し、飛び石）",
    "6　海峡の口（3〜5歳はここでバイバイ）",
    "7　「今日のごはん」の窓（斜めの壁、子どもの高さ）",
    "8　食べる土間の南のガラス越しにキッチンが見える",
    "9　キッチンの道路側の窓と搬入口",
    "10　入江の木とベンチ",
    "11　海峡の入口のコーヒーの棚（保護者）",
    "12　駐車 5台（道路から直角に）",
    "13　駐輪と道路側の木戸",
]
for i, s in enumerate(legend):
    c, r = (0, i) if i < 7 else (1, i - 7)
    fig.text((L + 125 * c) / 297, (52 - 4.6 * r) / 420, s, fontsize=6.3, va="top")
fig.savefig(_os.path.join(OUT, "sodachiya_approach.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_approach.png"), dpi=200)
