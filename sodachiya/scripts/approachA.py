# 育ち舎 アプローチ A案 配置図 1/200（南半分、A3 縦）  2026-10-23
# base: approach.py（ページ・凡例の体裁）＋ parking.py の A（駐車南・ひろば北）
import math, pickle, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, Arc
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt
from shapely import affinity as af
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import infant200

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"

# ---------------------------------------------------------------- geometry
CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX)
if TH_S < 0: TH_S += 2 * math.pi
def W(u, v):                    # main-building frame: u m north of the south gable along the spine, v m east of the west face
    th = TH_S - u / RW; r = RW - v
    return (CX + r * math.cos(th), CY + r * math.sin(th))
def rect(u0, u1, v0, v1, n=8):
    return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
SITE = [(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)]
SETB = [(-0.16, -1.41), (33.45, -43.67), (-14.28, -81.64), (-20.93, -73.27), (-24.79, -20.99)]
PARK = [(-14.44, -83.04), (-21.91, -73.65), (-12.52, -66.18), (-5.05, -75.57)]
WN = pickle.load(open(os.path.join(ROOT, "data", "wnew.pkl"), "rb"))["WN"]
WN = af.scale(WN, 0.001, 0.001, origin=(0, 0))
WB = WN                                                                    # 10-21: no chamfer (south face = frame 12, u = 21)

# road frame: s m along the road from the park corner (north +), d m into the site (east +)
A0 = np.array((-21.91, -73.65)); B0 = np.array((-25.83, -20.54))
tt = (B0 - A0) / np.linalg.norm(B0 - A0); nn = np.array([tt[1], -tt[0]]); nn = nn if nn[0] > 0 else -nn
def P(s, d): p = A0 + tt * s + nn * d; return (float(p[0]), float(p[1]))
def Q(pts): return [P(*q) for q in pts]
def srect(s0, s1, d0, d1): return Q([(s0, d0), (s1, d0), (s1, d1), (s0, d1)])
def inv(p): v = np.array(p) - A0; return float(v @ tt), float(v @ nn)

# park tip and its north-east edge (the security line along the park)
TIP = np.array(inv(PARK[2])); PK3 = np.array(inv(PARK[3]))
EE = (PK3 - TIP) / np.linalg.norm(PK3 - TIP)          # along the park edge, toward SE
EN = np.array([-EE[1], EE[0]]);  EN = EN if EN[1] > 0 else -EN   # into the site
def E(a, b): q = TIP + EE * a + EN * b; return P(*q)   # a along the edge from the tip, b into the site
import minami_common as MN
FENCE_END = W(MN.GATE_POST_W[1], MN.GATE_POST_W[0])      # corner post of the west gate (infant fence + park lattice meet, data/minami.json)

# ---------------------------------------------------------------- key dimensions (m) -> data/approachA.json
import json
_D = json.load(open(os.path.join(ROOT, "data", "approachA.json"), encoding="utf-8"))
def _t(x): return tuple(_t(i) for i in x) if isinstance(x, list) and x and isinstance(x[0], list) else (tuple(x) if isinstance(x, list) else x)
for _k, _v in _D.items():
    if not _k.startswith("_"): globals()[_k] = _t(_v)
BEDS = [tuple(b) for b in BEDS]

C = dict(par="#FBE7CF", kid="#E2EDD0", red="#C8372D", path="#8a5a2b", blue="#3d7fb0", green="#5a7a3a",
         car="#ECECEC", plaza="#EEDFC6", kit="#F0B98A", eat="#F7D3B0", arai="#DCD3C3", hedge="#B7CF95",
         wood="#7a5a36", roof="#444444", gravel="#CFCAC0")
# ---------------------------------------------------------------- page
MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
xmin, xmax, ymin, ymax = -29.0, 12.0, -85.5, -33.0          # 1/200: 1 m = 5 mm
PL, PB = 14, 110
ax = fig.add_axes([PL / 297, PB / 420, (xmax - xmin) * 5 / 297, (ymax - ymin) * 5 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

def poly(pts, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1, a=None):
    a = a or ax
    if hasattr(pts, "geom_type"):
        if pts.is_empty: return
        gs = [pts] if pts.geom_type == "Polygon" else [g for g in getattr(pts, "geoms", []) if g.geom_type == "Polygon"]
        for g in gs: poly(list(zip(*g.exterior.xy)), fc, ec, lw, z, ls, hatch, alpha, a)
        return
    a.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
def line(pts, lw=0.5, c="black", ls="-", z=3, a=None):
    xs, ys = zip(*pts); (a or ax).plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(p, s, size=6, c="#222222", ha="center", va="center", rot=0, z=12, a=None, **kw):
    (a or ax).text(p[0], p[1], s, fontsize=size, color=c, ha=ha, va=va, rotation=rot, zorder=z, **kw)
def tree(p, r=1.8, z=6):
    ax.add_patch(Circle(p, r, fc="#DCE8C8", ec=C["green"], lw=0.5, zorder=z, alpha=0.85))
    ax.add_patch(Circle(p, 0.14, fc=C["green"], ec="none", zorder=z + 0.1))
def num(p, k):
    ax.add_patch(Circle(p, 0.72, fc="white", ec="black", lw=0.4, zorder=20)); T(p, str(k), 5.4, z=21)
def post(p, s=0.15):
    ax.add_patch(Rectangle((p[0] - s / 2, p[1] - s / 2), s, s, fc="black", ec="none", zorder=11))
def roof(pts, z=10):
    poly(pts, fc="none", ec=C["roof"], lw=0.6, ls=(0, (5, 2.5)), z=z)
def clipWB(g):
    return g.difference(WB).difference(SP(rect(-1, 40, 0, 40)))
ROT = math.degrees(math.atan2(tt[1], tt[0])) - 90      # text rotation following the road (≈ +4°)

# ---------------------------------------------------------------- ground, park, river, road
poly(SITE, fc="#FAFAF6", ec="black", lw=1.0, z=0)
poly(SETB, fc="none", ec="#999999", lw=0.3, ls=(0, (4, 3)), z=0.5)
T((-27.7, -55), "西の道路（歩道なし）", 6.5, rot=86)
T((6.8, -67.0), "高野川 →", 7, rot=38)
poly(PARK, fc="#E3EDD3", ec=C["green"], lw=0.7, z=1)
tree((-13.6, -75.2), 3.4)
T((-13.4, -80.2), "公園（12 × 12 m）\n待ち合わせの木", 6)
kid = SP(SITE).difference(SP(PARK)).intersection(SP(rect(-14, 40, 1.6, 40))).difference(SP(rect(0, 40, 0, 15)))
poly(kid, fc=C["kid"], ec="none", z=1)
line([W(0, 1.6), W(MN.D["FENCE_END_U"], 1.45), FENCE_END], lw=1.1, c="#6b5a3a", z=6)   # infant-garden fence h1.2
# みなみのさんかくの中身（data/minami.json、minami01.py のたたき台を 1/200 で）
def _mw(g): return SP([W(y, x) for x, y in g.exterior.coords])
for _n, _g in MN.loop_parts(): poly(_mw(_g), fc="#D8C3A0", ec="#9a8060", lw=0.2, z=2.2)
poly(_mw(MN.MOUND), fc="#C9DDA8", ec="#6a8a4a", lw=0.3, z=2.3)
poly(_mw(MN.SAND), fc="#EADBB0", ec="#8a7040", lw=0.4, z=2.3)
poly(_mw(MN.HERB), fc="#A9C98A", ec="none", z=2.3)
poly(_mw(MN.WATER), fc="#9CC9E6", ec="#3d7fb0", lw=0.4, z=2.3)
tree(W(*MN.D["TREE"]["c"]), MN.D["TREE"]["r"])
T(W(-8.3, 5.2), "みなみのさんかく", 6.0, c=C["green"], rot=-32)
for _n, _h, _e, _hh, _deg in MN.gates():                          # 木戸（東 h0.9）・非常用の門（西 h1.8）
    _o = MN.leaf_at(_h, _e, _deg)
    line([W(_h[1], _h[0]), W(_e[1], _e[0])], lw=1.4, c=C["wood"], z=7.6)
    line([W(_h[1], _h[0]), W(_o[1], _o[0])], lw=0.3, c=C["wood"], ls=(0, (2, 1.5)), z=7.6)

# ---------------------------------------------------------------- main building (south half)
COL = {"01": "#E6EFC2", "2": "#C5DE9A", "med": "#F7F3EA", "hall": "#E3C08D", "off": "#E9DCC4", "3": "#9FCB84"}
poly(rect(0, 36, -0.35, 15), fc="#F6F2EA", ec="none", z=4)
for (u0, u1, k) in [(18, 21, "med"), (21, 30, "hall"), (30, 33, "off"), (33, 36, "3")]:
    poly(rect(u0, u1, 1.6, 12), fc=COL[k], ec="none", z=4.1)
infant200.draw(ax, W, z0=4.15)                                     # 0・1歳・2歳の家具（plan01/02 から）
poly(rect(21, 22.5, -0.05, 15), fc="#D9CBB4", ec="none", z=4.3)      # strait
for u in [12, 18, 21, 30, 33]: line([W(u, 1.6), W(u, 12)], lw=0.45, z=4.5)
line([W(0, 1.6), W(36, 1.6)], lw=0.45, z=4.5)
line([W(0, 12), W(36, 12)], lw=0.35, c="#777777", z=4.5)
line([W(0, 15), W(36, 15)], lw=0.45, z=4.5)
poly(rect(0, 36, -0.35, 15), fc="none", ec="black", lw=0.9, z=4.6)
for (u, s) in [(19.5, "医務"), (26.5, "ホール"), (31.5, "事務"), (34.5, "3歳")]:
    T(W(u, 7), s, 6.3, rot=-3, clip_on=True)
T(W(21.75, 8.0), "海峡（土足）", 4.8, rot=-3)
T(W(3.0, 0.8), "受け取り\n土間", 4.4, rot=-3)
for u, v in [(21.75, 4.0), (21.75, 10.0)]:
    ax.add_patch(Circle(W(u, v), 0.45, fc="#BFAF95", ec="black", lw=0.3, zorder=4.7))
# doors: receiving doma (south gable), strait mouth
line([W(0, 0.15), W(0, 1.45)], lw=2.2, c="white", z=4.8); line([W(0, 0.15), W(0, 1.45)], lw=0.4, c="black", ls=(0, (1, 1)), z=4.9)
# peek windows of the 0・1 room (kids' eye height)
for u in [6.6, 7.5, 8.4]:
    ax.add_patch(Circle(W(u, -0.02), 0.17, fc=C["blue"], ec="none", zorder=7))
# overhead: south eave, monitor cap along the west face
roof([W(0, -1.0), W(0, 15), W(-1.8, 15), W(-4.2, -1.0)], z=9)
line([W(0, -0.35 - LID_OUT), W(21, -0.35 - LID_OUT)], lw=0.45, c=C["roof"], ls=(0, (5, 2.5)), z=9)     # floating lid edge (flush with the west wall in the current 3dm)

# ---------------------------------------------------------------- west building: kitchen (south corner) + eating doma
poly(WB, fc="#F6E3A4", ec="none", z=4)
for (u0, u1, fc, s) in [(21, 27.25, C["kit"], "キッチン"), (27.25, 30, C["eat"], "はれのま")]:
    g = SP(rect(u0, u1, -3.4, -22)).intersection(WB); poly(g, fc=fc, ec="none", z=4.2)
    T(W((u0 + u1) / 2, -9.5), s, 6.3, rot=-3)
poly(WB, fc="none", ec="black", lw=0.9, z=4.6)
for ln, kw in [(SL([W(27.25, -3.4), W(27.25, -30)]), dict(lw=0.45)), (SL([W(22.5, -3.4), W(36, -3.4)]), dict(lw=0.35, c="#777777")), (SL([W(30, -3.4), W(30, -30)]), dict(lw=0.45))]:
    g = ln.intersection(WB)
    for q in getattr(g, "geoms", [g]):
        if not q.is_empty: line(list(q.coords), z=4.5, **kw)
T(W(28.5, -2.0), "東の帯", 5, rot=87)
# the strait continues across the gap into the west building's doma (土足 −150); entrance on the west building's south face
poly(rect(21, 22.5, -3.4, -0.05), fc="#D9CBB4", ec="none", z=4.7)
line([W(22.5, -3.4), W(22.5, -0.9)], lw=0.5, c="#777777", ls=(0, (2, 1.5)), z=4.8)          # 框 to the barefoot doma
T(W(21.75, -2.0), "海峡", 4.2, rot=-3, z=12)
ent = [W(21, -0.1), W(21, -3.4)]
line(ent, lw=1.6, c="white", z=4.9)
line([W(21, -0.95), W(21, -2.75)], lw=0.9, c="#555555", ls=(0, (2, 1)), z=5)                # entrance: sliding doors 1.8
line([W(21, -0.15), W(21, -0.85)], lw=1.6, c=C["blue"], z=5)                                # glass across the gap
# kitchen south glass (straight part of the south face) and the 'today's lunch' window next to the entrance
line([W(21, -4.6), W(21, -9.6)], lw=2.2, c=C["blue"], z=6)
line([W(21, -3.5), W(21, -4.4)], lw=3.0, c="#D85A30", z=6)
# ---------------------------------------------------------------- parking (outside the line)
poly(srect(12.2, 17.7, 0.0, HEDGE_D - HW), fc="#F0F0EE", ec="none", z=2)            # aisle 5.5
def stall(s0, s1, d0, d1, lab="P"):
    poly(srect(s0, s1, d0, d1), fc=C["car"], ec="#666666", lw=0.4, z=3)
    T(P((s0 + s1) / 2, (d0 + d1) / 2), lab, 5.4 if lab == "P" else 4.6, c="#555555", rot=ROT)
for k in range(3): stall(7.2, 12.2, STALL_D0 + 2.5 * k, STALL_D0 + 2.5 * (k + 1))     # south 3
stall(17.7, 22.7, STALL_D0, STALL_D0 + 2.5, "搬入"); stall(17.7, 22.7, STALL_D0 + 2.5, STALL_D0 + 5.0)   # north 2
line(Q([(12.2, -0.05), (17.7, -0.05)]), lw=2.2, c="#888888", z=8)                       # one curb cut
# speed bump across the aisle (stalls open only beyond it)
poly(srect(12.3, 17.6, *BUMP), fc="#F2C94C", ec="#555555", lw=0.4, z=3.2)
for s in np.arange(12.6, 17.6, 0.6):
    poly(srect(s, s + 0.3, *BUMP), fc="#333333", ec="none", z=3.3)
T(P(14.95, 5.0), "車路 5.5", 5.2, c="#777777", rot=ROT)
# planting strip along the road in front of the stalls / delivery path
for (s0, s1) in [(7.2, 12.2), (17.7, 22.7), (22.7, 29.4)]:
    poly(srect(s0, s1, 0.15, STALL_D0 - 0.1), fc="#E3ECD6", ec="none", z=2)
# visitors' walk: aisle -> along the hedge (outside) -> park gate
poly(srect(*VWALK), fc=C["arai"], ec="none", z=2.2)
# bikes in the south triangle: row 1 straight off the road, row 2 off a short aisle; 0.7 pitch (child-seat bikes)
poly(SP(Q([(0.0, 0.15), (7.15, 0.15), (7.15, 20)])).intersection(SP([P(0, 0), P(*TIP), P(7.15, 20), P(7.15, 0)])).difference(SP(PARK)),
     fc="#ECE8E0", ec="none", z=2)
BIKES = []
for s0 in [1.55, 2.25, 2.95, 5.05, 5.75, 6.45]:                  # row 1 (gap 3.6–5.0 = aisle to row 2)
    BIKES.append(("d", s0, 0.3))
for d0 in [2.9, 3.6, 4.3, 5.0, 5.7, 6.4]:                        # row 2: along s, side by side in d
    BIKES.append(("s", 5.2, d0))
for kind, a, b in BIKES:
    if kind == "d":
        line(Q([(a + 0.35, b), (a + 0.35, b + 1.85)]), lw=1.0, c="#6b5a3a", z=3.6)
        line(Q([(a + 0.12, b + 0.9), (a + 0.58, b + 0.9)]), lw=0.4, c="#6b5a3a", z=3.6)
    else:
        line(Q([(a, b + 0.35), (a + 1.85, b + 0.35)]), lw=1.0, c="#6b5a3a", z=3.6)
        line(Q([(a + 0.95, b + 0.12), (a + 0.95, b + 0.58)]), lw=0.4, c="#6b5a3a", z=3.6)
N_BIKE = len(BIKES)

# ---------------------------------------------------------------- security line: hedges, fences, lattice, gate
def band(pts, w, fc, ec, z=7):
    g = SL(Q(pts)).buffer(w, cap_style=2, join_style=2)
    poly(g, fc=fc, ec=ec, lw=0.4, z=z)
HEDGE = [[(22.7, FENCE_D), (22.7, NHEDGE_D), (17.7, NHEDGE_D), (17.7, HEDGE_D), (S_PATH0, HEDGE_D)]]
for h in HEDGE:
    band(h, HW, C["hedge"], C["green"])
    line(Q(h), lw=0.35, c="#3f5a2a", ls=(0, (1.2, 1.2)), z=7.2)
    g = SL(Q(h))
    for t in np.arange(0.3, g.length, 0.7):
        q = g.interpolate(t); ax.add_patch(Circle((q.x, q.y), 0.22, fc="none", ec=C["green"], lw=0.3, zorder=7.1))
line([P(S_PATH0, HEDGE_D), P(*TIP)], lw=1.0, c=C["green"], z=7)
# board fence h1.8 on the road side of the plaza
fence = SL(Q([(22.7, FENCE_D), (32.0, FENCE_D)]))
fx = fence.intersection(WB.exterior)
fx = min(getattr(fx, "geoms", [fx]), key=lambda q: q.distance(SPt(P(22.7, FENCE_D))))
FENCE_S1 = inv((fx.x, fx.y))[0]
line([P(22.7, FENCE_D), (fx.x, fx.y)], lw=1.8, c=C["wood"], z=7.5)
# park gate (kido) 1.2 wide just SE of the park tip; lattice h1.8 from the gate to the infant fence
GA0, GA1 = 0.3, 1.5
line([E(0, 0), E(GA0, 0)], lw=1.6, c=C["wood"], z=7.5)
lat_end = np.array(inv(FENCE_END)); La = float((lat_end - TIP) @ EE)
line([E(GA1, 0), FENCE_END], lw=1.6, c=C["wood"], z=7.5)
for a in np.arange(GA1 + 0.15, La, 0.25):
    line([E(a, -0.12), E(a, 0.12)], lw=0.3, c=C["wood"], z=7.6)
ax.add_patch(Arc(E(GA0, 0), 2.4, 2.4, angle=math.degrees(math.atan2(*(np.array(E(1, 0)) - np.array(E(0, 0)))[::-1])),
                 theta1=0, theta2=90, lw=0.35, color="#555555", zorder=7.6))
LINE = Q([(FENCE_S1, FENCE_D), (22.7, FENCE_D), (22.7, NHEDGE_D), (17.7, NHEDGE_D), (17.7, HEDGE_D), (S_PATH0, HEDGE_D), tuple(TIP)]) + [FENCE_END]
line(LINE, lw=0.5, c=C["red"], ls=(0, (6, 2)), z=13)
ax.add_patch(Circle(E((GA0 + GA1) / 2, 0), 0.32, fc=C["red"], ec="white", lw=0.5, zorder=14))

# ---------------------------------------------------------------- kido roof + porch
KR = [E(-0.3, -0.7), E(2.6, -0.7), E(2.6, 2.9), E(-0.3, 2.9)]
poly(SP(KR).difference(SP(rect(-1, 40, -0.9, 40))), fc="#EFE8DA", ec="none", z=2.4)
roof(KR, z=10)
for p in [E(-0.05, -0.15), E(2.35, -0.15), E(-0.05, 2.6), E(2.35, 2.6)]: post(p)
poly([W(0, -1.0), W(0, 1.6), W(-4.0, 1.6), W(-4.2, -1.0)], fc="#EFE8DA", ec="none", z=2.4)
for k in range(5):
    u0 = -4.0 + 0.7 * k
    poly(rect(u0 + 0.06, u0 + 0.64, -0.85, 0.15, 2), fc="white", ec="#777777", lw=0.35, z=5)
    ax.add_patch(Circle(W(u0 + 0.35, -0.6), 0.08, fc="#777777", ec="none", zorder=5.1))
poly(rect(-3.6, -1.4, 1.05, 1.45, 2), fc=C["wood"], ec="none", z=5)

# ---------------------------------------------------------------- the path (見送りの小径) about 2.4 wide (hedge to the west wall at v -0.35)
def sband(s0, s1, d0, d1, fc, z=2.5, **kw):
    poly(clipWB(SP(srect(s0, s1, d0, d1))), fc=fc, ec="none", z=z, **kw)
sband(S_PATH0 - 0.4, 29.5, HEDGE_D + HW, WALL_D + 0.3, C["arai"])
sband(S_PATH0, S_PATH1, HEDGE_D + HW, HEDGE_D + HW + 0.3, "#C9DDB0", z=2.6)
for s in np.arange(S_PATH0 + 0.2, S_PATH1, 0.6):
    ax.add_patch(Circle(P(s, HEDGE_D + HW + 0.15), 0.1, fc=C["green"], ec="none", zorder=2.7, alpha=0.6))
sband(S_PATH0, 29.5, AMAOCHI[0], AMAOCHI[1], C["gravel"], z=2.6)                           # gravel strip along the wall (roof and lid drain east)
for s in np.arange(S_PATH0, 29.4, 0.35):
    for dd in (AMAOCHI[0] + 0.15, AMAOCHI[0] + 0.35):
        ax.add_patch(Circle(P(s, dd), 0.05, fc="#8f877a", ec="none", zorder=2.7))
T(P(12.8, 11.55), "見送りの小径", 6.2, c=C["path"], rot=ROT + 90, weight="bold")
for s in [9.0, 12.0, 15.0]:
    ax.add_patch(Circle(P(s, 10.95), 0.09, fc="#E8B33A", ec="#8a6a1a", lw=0.3, zorder=8))
# arched trellis over the path: posts on the hedge side at the main frames (3 m), arched beams every 1.5 m to the wall, ムベ
if PERGOLA:
    PG_D = HEDGE_D + HW + 0.15
    s_fr = [inv(W(u, 0))[0] for u in (0.75, 3, 6, 9)]          # frames u = 3, 6, 9 (+ start just north of the kido roof)
    s_a, s_b = s_fr[0], TEM[0]
    line([P(s_a, PG_D), P(s_b, PG_D)], lw=0.9, c=C["wood"], z=10.5)                     # 桁 on the posts
    for s in np.arange(s_a, s_b + 0.01, (s_b - s_a) / round((s_b - s_a) / 1.5)):
        line([P(s, PG_D), P(s, WALL_D)], lw=0.55, c=C["wood"], z=10.5)                 # arched beams (plan)
    for s in [s_a] + s_fr[1:] + [s_b]:
        post(P(s, PG_D), 0.14)
        ax.add_patch(Circle(P(s, PG_D - 0.05), 0.35, fc="#9DBE7A", ec="none", zorder=10.4, alpha=0.8))   # ムベ at the post foot
    for s in np.arange(s_a + 0.4, s_b, 0.8):                                            # foliage on top (light)
        ax.add_patch(Circle(P(s, (PG_D + WALL_D) / 2 + 0.3 * math.sin(s * 2.1)), 0.55, fc="#9DBE7A", ec="none", zorder=10.3, alpha=0.28))

# ---------------------------------------------------------------- plaza
plz = clipWB(SP(Q([(22.7, FENCE_D), (FENCE_S1 + 0.6, FENCE_D), (31.0, WALL_D + 0.3), (17.7, WALL_D + 0.3), (17.7, NHEDGE_D), (22.7, NHEDGE_D)])))
poly(plz, fc=C["plaza"], ec="none", z=2.2)
sband(17.7, 29.5, HEDGE_D + HW, WALL_D + 0.3, C["arai"], z=2.3)
T(P(24.7, 7.4), "ひろば", 8, c="#8a5a2b", rot=ROT, weight="bold")

# temizu (roofed 2.7 x 2.7): stone basin + bamboo spout, the walk passes under it
s0, s1, d0, d1 = TEM
roof(srect(s0, s1, d0, d1), z=11)
for p in [P(s0 + 0.3, d0 + 0.3), P(s1 - 0.3, d0 + 0.3), P(s0 + 0.3, d1 - 0.3), P(s1 - 0.3, d1 - 0.3)]: post(p)
poly(srect(18.9, 19.8, 10.7, 11.25), fc="#B9C2C8", ec="#555555", lw=0.5, z=11)
poly(srect(19.05, 19.65, 10.8, 11.15), fc="#9cc3e0", ec="none", z=11.1)
line(Q([(19.35, 10.45), (19.35, 10.85)]), lw=1.4, c="#8a9a5a", z=11.2)
poly([P(19.0, 11.5), P(19.7, 11.5), P(19.7, 11.95), P(19.0, 11.95)], fc="#D8D2C6", ec="#888888", lw=0.3, z=10.9)

# kitchen garden: three raised beds 0.9 x 3.1 in the sunny south part of the plaza, tap
for b in BEDS:
    poly(srect(*b), fc="#D9E6BF", ec=C["green"], lw=0.5, z=6)
    for d in np.arange(b[2] + 0.3, b[3], 0.5):
        ax.add_patch(Circle(P((b[0] + b[1]) / 2, d), 0.12, fc="#8DB36A", ec="none", zorder=6.1))
ax.add_patch(Circle(P(22.4, 6.9), 0.1, fc=C["blue"], ec="none", zorder=8))

# tea engawa under a lean-to off the kitchen south wall: 縁台 ×2, tea shelf with tap (kitchen plumbing nearby)
u0, u1, v0, v1 = LEAN_UV
poly(rect(u0, u1, v0, v1), fc="#E7D6BB", ec="none", z=2.4)
roof(rect(u0, u1, v0, v1))
LEAN_POSTS = [W(u0 + 0.25, v) for v in (-9.7, -6.4, -3.1, -0.3)]
for p in LEAN_POSTS: post(p)
for (va, vb) in [(-9.0, -7.2), (-6.6, -4.8)]:
    poly(rect(19.6, 20.5, va, vb, 2), fc="#B98E5E", ec=C["wood"], lw=0.4, z=9)             # 縁台 0.9 x 1.8
poly(rect(19.3, 20.8, -9.95, -9.5, 2), fc="#8a6a44", ec="none", z=9)                     # tea shelf
ax.add_patch(Circle(W(20.55, -9.72), 0.09, fc=C["blue"], ec="none", zorder=9.2))

# kamado (events): masonry 1.0 x 1.0, earth apron, wood rack on the board fence
s0, s1, d0, d1 = KAM
ax.add_patch(Circle(P((s0 + s1) / 2, (d0 + d1) / 2), 1.3, fc="#E3D3B8", ec="none", zorder=2.5))
poly(srect(s0, s1, d0, d1), fc="#C9A97A", ec="#6b4b2a", lw=0.6, z=8)
for dd in (3.85, 4.35):
    ax.add_patch(Circle(P(s1 - 0.3, dd), 0.15, fc="#4a3826", ec="none", zorder=8.1))
poly(srect(26.0, 27.6, FENCE_D + 0.1, FENCE_D + 0.55), fc="#a07a4c", ec=C["wood"], lw=0.3, z=8)   # 薪棚 on the board fence
for s in np.arange(26.15, 27.6, 0.3):
    ax.add_patch(Circle(P(s, FENCE_D + 0.33), 0.1, fc="none", ec="#5a3f22", lw=0.3, zorder=8.1))

# the tree at the inlet (deciduous)
tree(P(24.4, 9.6), 1.9)

# ---------------------------------------------------------------- delivery path (outside the line), kitchen back door + small roof
poly(srect(*DEL), fc="#E6E6E3", ec="none", z=2.3)
door = [P(30.4, 1.51), P(29.69, 2.18)]
line(door, lw=2.4, c="white", z=6); line(door, lw=0.9, c="#555555", z=6.1)
roof(srect(28.6, 31.2, 1.3, 3.0))
T(P(26.0, 2.1), "搬入路 1.6", 4.6, c="#555555", rot=ROT + 90)

# ---------------------------------------------------------------- walking lines (light)
def walk(pts, c=C["path"], lw=0.9):
    line(pts, lw=lw, c=c, ls=(0, (3, 2)), z=15)
walk([E(0.9, -1.6), E(0.9, 1.0), P(8.0, 11.6), P(17.0, 11.7), P(19.35, 12.3), P(25.0, 12.9), W(20.6, -1.85), W(21.3, -1.85)])
walk([E(0.9, 1.0), W(-0.6, -0.4), W(-0.6, 0.8), W(0.0, 0.8)], c="#b08a5b", lw=0.7)
walk([P(15.0, 3.0), P(12.6, 9.45), P(7.4, 9.45), E(0.9, -1.0)], c="#b08a5b", lw=0.7)          # visitors from the car
walk([P(4.3, 1.0), P(4.3, 6.0), E(1.4, -2.2), E(0.9, -1.6)], c="#b08a5b", lw=0.7)            # from the bikes

# ---------------------------------------------------------------- numbers
N = [(E(0.9, -2.6), 1), (W(-2.4, 0.4), 2), (E(5.2, -1.3), 3), (W(3.0, 3.0), 4), (P(9.6, 11.7), 5), (W(7.5, 1.0), 6),
     (P(21.6, 11.7), 7), (P(20.0, 5.6), 8), (W(20.1, -10.9), 9), (P(24.2, 6.0), 10), (P(24.4, 9.6), 11),
     (W(19.6, -2.0), 12), (W(19.4, -3.95), 13), (W(19.6, -7.0), 14), (P(31.2, 0.2), 15), (P(14.95, -1.4), 16),
     (P(10.0, 9.45), 17), (P(3.6, -1.2), 18), (P(23.6, 2.2), 19)]
for p, k in N: num(p, k)

# north arrow + scale (1/200)
ax.annotate("", xy=(4.0, -36.0), xytext=(4.0, -39.4), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
T((4.0, -35.1), "N", 8)
sx, sy = -6.0, -84.6
for i in range(5):
    poly([(sx + 2 * i, sy), (sx + 2 * i + 2, sy), (sx + 2 * i + 2, sy + 0.35), (sx + 2 * i, sy + 0.35)], fc="black" if i % 2 == 0 else "white", lw=0.3, z=6)
for i, s in [(0, "0"), (5, "10 m")]: T((sx + 2 * i, sy - 0.8), s, 5)
T((sx + 13.5, sy + 0.17), "1/200", 6)

# ---------------------------------------------------------------- titles + legend
fig.text(PL / 297, 410 / 420, "育ち舎　配置図（南半分）　アプローチ A 案", fontsize=13, weight="medium", va="top")
fig.text(PL / 297, 402 / 420, "1/200（A3）　2026-10-23　駐車は南、ひろばは北。公園 → 木戸 → ポーチ（0〜2歳）／見送りの小径 → 手水 → ひろば → 海峡の口（3〜5歳）。",
         fontsize=6.6, va="top", color="#444444")
fig.text(PL / 297, 396.5 / 420, "破線＝頭上の屋根・軒・キャップ　■＝柱　赤い破線＝セキュリティの線（内側は保護者の領域）　● 赤＝線の出入口（公園の木戸）　┅ 道すじ",
         fontsize=6.0, va="top", color="#666666")
legend = [
    ("1", "公園の木戸（屋根つき）。線の出入口はここだけ"),
    ("2", "ポーチ（軒の下）：ベビーカー5台・腰掛け"),
    ("3", "格子 h1.8（公園側の視線よけ）"),
    ("4", "受け取り土間（ベビーカーのまま入れる）"),
    ("5", "見送りの小径 2.4：アーチの棚（ムベ）"),
    ("6", "0・1歳の覗き窓（子どもの目の高さ）"),
    ("7", "手水（屋根 2.7×2.7、石の鉢と筧）"),
    ("8", "菜園（畝 0.9×3.1 ×3、南の日なた）"),
    ("9", "お茶の縁台（西館の南の下屋の下）"),
    ("10", "かまど（行事のとき）、薪棚は下屋の下"),
    ("11", "入江の木（落葉樹）"),
    ("12", "西館の南の入口→海峡（3〜5歳はここでバイバイ）"),
    ("13", "「今日のごはん」の窓（入口の脇）"),
    ("14", "キッチンの南のガラス"),
    ("15", "勝手口と庇、搬入路 1.6（線の外）"),
    ("16", "駐車5台・乗入れ1か所・スピードバンプ"),
    ("17", "来客の歩道 1.1（車から公園の木戸へ）"),
    ("18", "駐輪 %d台（子乗せ 0.7 ピッチ）" % N_BIKE),
    ("19", "板塀 h1.8（道路側、西日と視線よけ）"),
]
LX = 221
def leg_row(y, k, txt, r=1.6):
    fig.patches.append(Circle(((LX + 2) / 297, y - 0.0026), r / 297, transform=fig.transFigure, fc="white", ec="black", lw=0.4))
    fig.text((LX + 2) / 297, y - 0.0026, k, fontsize=4.9, ha="center", va="center")
    fig.text((LX + 5.0) / 297, y, txt, fontsize=5.5, va="top")
fig.text(LX / 297, 377 / 420, "アプローチ", fontsize=6.6, weight="bold", va="top")
for i, (k, t) in enumerate(legend):
    leg_row((371 - 5.5 * i) / 420, k, t)
Y2 = 371 - 5.5 * len(legend) - 6
fig.text(LX / 297, Y2 / 420, "0〜2歳（plan01・plan02 から）", fontsize=6.6, weight="bold", va="top")
for i, (k, u, v, t) in enumerate(infant200.ITEMS):
    leg_row((Y2 - 6 - 5.5 * i) / 420, str(k), t.replace("（", "\n（", 0))
for (k, u, v, t) in infant200.ITEMS:
    q = W(u, v); ax.add_patch(Circle(q, 0.55, fc="white", ec="black", lw=0.35, zorder=20)); T(q, str(k), 4.6, z=21)

notes = ("見送りの小径：生垣 h1.2（常緑、中にメッシュ柵 h1.2）／下草 0.3／洗い出し 1.9（平ら、ベビーカー可）／砂利 0.2（壁の足もとの跳ね返り止め。屋根と越屋根の蓋は東へ流れる）。\n"
         "アーチの棚：生垣の側に柱（本館の架構に合わせて 3 m ごと）、梁は 1.5 m ごとに本館の壁へ。木戸の屋根 → 棚 → 手水の屋根 → ひろば（ひらける）。\n"
         "車路：道路から 0.5 m にスピードバンプ（幅 0.5）、車室の口はそこから奥（道路から 1.3 m 以上）。来客の門はなし、来客も公園の木戸から。\n"
         "ひろば（線の内側、真砂土）約 %d m²。菜園は南の日なた、縁台は西館の南の下屋（入口の前まで一続き）の下。かまどは下屋から約 2 m、建物から 4 m 以上（行事のときだけ）。\n"
         "搬入は線の外：搬入の車室の後ろから搬入路（幅1.6、約7 m）を手押しで勝手口へ。")
plaza_area = plz.area
fig.text(PL / 297, 104 / 420, notes % round(plaza_area), fontsize=6.1, va="top", color="#333333", linespacing=1.65)

# ---------------------------------------------------------------- section A-A through the path (1/100, schematic)
# cut across the path at s ≈ 11 (looking north): car | hedge | path | wall | 0・1 room
sx0 = 14; sw = (16.3 - 6.0) * 10
axs = fig.add_axes([sx0 / 297, 14 / 420, sw / 297, 62 / 420])
axs.set_xlim(6.0, 16.3); axs.set_ylim(-0.4, 5.8); axs.set_aspect("equal"); axs.axis("off")
def sp(pts, **kw): poly(pts, a=axs, **kw)
def sl(pts, **kw): line(pts, a=axs, **kw)
def st(p, s, size=5.4, **kw): T(p, s, size, a=axs, **kw)
sl([(6.0, 0), (16.3, 0)], lw=0.9)
sp([(6.0, -0.4), (16.3, -0.4), (16.3, 0), (6.0, 0)], fc="#EEEAE2", ec="none", z=1)
# car (side view, schematic)
sp([(6.7, 0.15), (8.4, 0.15), (8.4, 1.0), (8.1, 1.5), (7.0, 1.5), (6.7, 1.0)], fc="#EDEDED", ec="#666666", lw=0.4)
st((7.55, 0.7), "駐車", 5)
sp([(8.9, -0.02), (10.0, -0.02), (10.0, 0.03), (8.9, 0.03)], fc=C["arai"], ec="#888888", lw=0.3)
st((9.45, 0.2), "来客の歩道", 3.9, c="#555555")
# arched trellis (beam springs from the post at 2.25, rises to ~2.5, lands on the wall)
xs = np.linspace(10.75, 13.0, 30); ys = 2.25 + 0.28 * np.sin(np.pi * (xs - 10.75) / 2.25) + 0.0 * xs
axs.plot(xs, ys, lw=1.0, color=C["wood"], zorder=6)
sp([(10.69, 0), (10.81, 0), (10.81, 2.3), (10.69, 2.3)], fc=C["wood"], ec="none", z=6)
for x0 in np.arange(10.9, 12.9, 0.35): axs.add_patch(Circle((x0, 2.55 + 0.12 * math.sin(x0 * 5) + 0.25 * math.sin(np.pi * (x0 - 10.75) / 2.25)), 0.22, fc="#9DBE7A", ec="none", alpha=0.7, zorder=5.5))
st((11.0, 3.15), "アーチの棚（ムベ）h2.3〜2.5", 4.4)
sl([(10.75, 0), (10.75, 2.25)], lw=0.0)
# hedge + mesh
axs.add_patch(matplotlib.patches.Ellipse((10.3, 0.62), 0.66, 1.24, fc=C["hedge"], ec=C["green"], lw=0.5, zorder=3))
sl([(10.3, 0), (10.3, 1.2)], lw=0.4, c="#3f5a2a", ls=(0, (1, 1)), z=4)
# path layers
sp([(10.6, 0), (10.9, 0), (10.9, 0.08), (10.6, 0.08)], fc="#C9DDB0", ec="none")
sp([(10.9, -0.03), (12.8, -0.03), (12.8, 0.03), (10.9, 0.03)], fc=C["arai"], ec="#888888", lw=0.3)
sp([(12.8, -0.08), (13.0, -0.08), (13.0, 0.0), (12.8, 0.0)], fc=C["gravel"], ec="#888888", lw=0.3)
# wall, peek window, floor (FL = GL+300), floating lid of the monitor (top FL+4.6 at the west edge, 350 out, 1/12)
sp([(13.0, 0), (13.15, 0), (13.15, 4.62), (13.0, 4.62)], fc="#cccccc", ec="black", lw=0.5)
sp([(12.98, 0.75), (13.17, 0.75), (13.17, 1.15), (12.98, 1.15)], fc="#9cc3e0", ec=C["blue"], lw=0.5, z=5)
sl([(13.15, 0.3), (16.3, 0.3)], lw=0.6)
sp([(13.35, 0.3), (15.0, 0.3), (15.0, 0.6), (13.35, 0.6)], fc="#E6EFC2", ec="#777777", lw=0.3)
st((14.3, 0.45), "小上がり", 4.2)
sl([(15.0, 4.3), (16.3, 4.19)], lw=0.6)
x0, x1 = 13.0 - LID_OUT, 13.35 + 1.6 + 0.35
sp([(x0, 4.9), (x1, 4.9 - (x1 - x0) / 12), (x1, 4.84 - (x1 - x0) / 12), (x0, 4.84)], fc="#cfe3ee", ec="black", lw=0.4)
for xl in np.arange(13.6, 15.0, 0.22):
    sl([(xl, 4.47), (xl + 0.12, 4.78)], lw=0.35, c=C["wood"])
st((14.3, 5.25), "越屋根の浮いた蓋（上端 FL+4.6）", 4.6)
sl([(x0, 4.84), (x0, 0.2)], lw=0.3, c="#9aa", ls=(0, (1, 2)))
st((x0 - 0.12, 3.6), "軒先の線", 4.2, rot=90, c="#778")
# figures: adult on the path, child inside at the window
def figure(x, h, c="#555555"):
    axs.add_patch(Circle((x, h - 0.12), 0.12, fc="none", ec=c, lw=0.5, zorder=6))
    sl([(x, h - 0.24), (x, h * 0.5)], lw=0.6, c=c, z=6); sl([(x - 0.15, 0), (x, h * 0.5), (x + 0.15, 0)], lw=0.6, c=c, z=6)
    sl([(x - 0.2, h * 0.68), (x + 0.2, h * 0.68)], lw=0.5, c=c, z=6)
figure(11.95, 1.6)
axs.add_patch(Circle((13.85, 1.05), 0.1, fc="none", ec="#555555", lw=0.5, zorder=6))
sl([(13.85, 0.95), (13.85, 0.7), (14.1, 0.6)], lw=0.6, c="#555555", z=6)
# dimensions
def dim(x0, x1, y, s):
    sl([(x0, y), (x1, y)], lw=0.35, c="#333333")
    for x in (x0, x1): sl([(x, y - 0.08), (x, y + 0.08)], lw=0.35, c="#333333")
    st(((x0 + x1) / 2, y + 0.17), s, 4.3)
for (x0, x1, s) in [(10.0, 10.6, "600"), (10.6, 10.9, "300"), (10.9, 12.8, "1900"), (12.8, 13.0, "200")]:
    sl([(x0, -0.3), (x1, -0.3)], lw=0.3, c="#333333")
    for x in (x0, x1): sl([(x, -0.36), (x, -0.24)], lw=0.3, c="#333333")
    st(((x0 + x1) / 2, -0.17 if s != "300" else -0.17), s, 3.9)
dim(10.6, 13.0, 1.95, "見送りの小径 2400")
sl([(9.85, 0), (9.85, 1.2)], lw=0.3, c="#333333"); st((9.7, 0.6), "1200", 3.9, rot=90)
st((10.3, 1.42), "生垣＋メッシュ柵", 4.4)
st((11.4, 0.18), "洗い出し", 4.0, c="#555555"); st((12.9, 0.18), "砂利", 3.6, c="#555555")
st((13.6, 1.35), "覗き窓", 4.4, c=C["blue"])
fig.text(sx0 / 297, 80 / 420, "A–A　見送りの小径の断面　1/100（高さは略図、北を見る）", fontsize=7, weight="medium", va="top")
# section mark on the plan
for d in (6.9, 15.8):
    pass
line([P(11.0, 6.9), P(11.0, 7.9)], lw=0.8, c="black", z=16); line([P(11.0, 15.3), P(11.0, 16.3)], lw=0.8, c="black", z=16)
T(P(11.0, 6.3), "A", 6.5, z=16, weight="bold"); T(P(11.0, 16.9), "A", 6.5, z=16, weight="bold")

os.makedirs(OUT, exist_ok=True)
fig.savefig(os.path.join(OUT, "sodachiya_site_A_1-200.pdf"))
fig.savefig(os.path.join(OUT, "sodachiya_site_A_1-200.png"), dpi=200)
print("plaza m2", round(plaza_area, 1), "fence s1", round(FENCE_S1, 2), "lattice len", round(La - GA1, 2))
