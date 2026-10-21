# 遊戯室（スパン 11–17）のたたき台 1/100：平面と東西の断面（摺鉢ネットの中心で切る）
# 座標は本館の (u, v)。西館の東西は「東から」w（v = −0.9 − w）。寸法は data/play.json。
# 架構の番号は南から（架構 k は u = 3(k−1)、スパン k は架構 k と k+1 のあいだ）。担当：遊戯室のスレッド。
import math, os, json, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt
from shapely.ops import unary_union
from shapely import affinity as af
import rhino3dm as r3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
D = json.load(open(os.path.join(ROOT, "data", "play.json"), encoding="utf-8"))

# ---------------------------------------------------------------- frame
CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
def Wraw(u, v):
    th = TH_S - u / RW; r = RW - v
    return (CX + r * math.cos(th), CY + r * math.sin(th))
def UVraw(x, y):
    th = math.atan2(y - CY, x - CX) % (2 * math.pi)
    return ((TH_S - th) * RW, RW - math.hypot(x - CX, y - CY))
UC = 41.0
O = np.array(Wraw(UC, 0)); dvec = np.array(Wraw(UC + 0.5, 0)) - np.array(Wraw(UC - 0.5, 0))
ANG = math.atan2(dvec[1], dvec[0]) - math.pi / 2
ca, sa = math.cos(-ANG), math.sin(-ANG)
def rot(p):
    x, y = p[0] - O[0], p[1] - O[1]
    return (x * ca - y * sa, x * sa + y * ca)
def W(u, v): return rot(Wraw(u, v))
def Ww(u, w): return W(u, -0.9 - w)                       # west building: w m west of the east line
def rect(u0, u1, v0, v1, n=6):
    return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
def rectw(u0, u1, w0, w1, n=6): return rect(u0, u1, -0.9 - w0, -0.9 - w1, n)
WN = af.scale(pickle.load(open(os.path.join(ROOT, "data", "wnew.pkl"), "rb"))["WN"], 0.001, 0.001, origin=(0, 0))
WB = SP([rot(p) for p in WN.exterior.coords])

# 3dm (mesh version): stair, 2nd floor, west-building columns, maple
M = r3.File3dm.Read(os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm"))
LN = {i: l.FullPath for i, l in enumerate(M.Layers)}
def layer(prefix):
    ps = []
    for o in M.Objects:
        if not LN[o.Attributes.LayerIndex].startswith(prefix) or type(o.Geometry).__name__ != "Mesh": continue
        g = o.Geometry; V = [rot((g.Vertices[i].X / 1000, g.Vertices[i].Y / 1000)) for i in range(len(g.Vertices))]
        for i in range(len(g.Faces)):
            idx = list(dict.fromkeys(g.Faces[i]))
            if len(idx) >= 3:
                p = SP([V[j] for j in idx])
                if p.area > 1e-6: ps.append(p.buffer(0.002))
    return unary_union(ps) if ps else SP()
STAIR = layer("36_"); F2 = layer("23_")
COLS = []
for o in M.Objects:
    if LN[o.Attributes.LayerIndex] == "22a_西館_柱":
        bb = o.Geometry.GetBoundingBox()
        COLS.append(UVraw((bb.Min.X + bb.Max.X) / 2000, (bb.Min.Y + bb.Max.Y) / 2000))
MAPLE = None
for o in M.Objects:
    if LN[o.Attributes.LayerIndex].startswith("67_"):
        bb = o.Geometry.GetBoundingBox()
        if bb.Min.Z < 0: MAPLE = UVraw((bb.Min.X + bb.Max.X) / 2000, (bb.Min.Y + bb.Max.Y) / 2000)

# ---------------------------------------------------------------- page (A3 portrait)
MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
U0, U1, V0, V1 = 29.0, 52.6, -15.4, 5.2
pts = [W(u, v) for u in np.linspace(U0, U1, 8) for v in (V0, V1)]
xmin, xmax = min(p[0] for p in pts) - 0.2, max(p[0] for p in pts) + 0.2
ymin, ymax = min(p[1] for p in pts) - 0.2, max(p[1] for p in pts) + 0.2
PL, PB = 12, 160
ax = fig.add_axes([PL / 297, PB / 420, (xmax - xmin) * 10 / 297, (ymax - ymin) * 10 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

def poly(pts, fc="none", ec="black", lw=0.45, z=2, ls="-", alpha=1, a=None, hatch=None):
    a = a or ax
    if hasattr(pts, "geom_type"):
        if pts.is_empty: return
        gs = [pts] if pts.geom_type == "Polygon" else [g for g in getattr(pts, "geoms", []) if g.geom_type == "Polygon"]
        for g in gs: poly(list(g.exterior.coords), fc, ec, lw, z, ls, alpha, a, hatch)
        return
    a.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, alpha=alpha, hatch=hatch))
def line(pts, lw=0.45, c="black", ls="-", z=5, a=None):
    (a or ax).plot([p[0] for p in pts], [p[1] for p in pts], lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(p, s, size=6, c="#222222", z=12, rot_=0, **kw):
    ax.text(p[0], p[1], s, fontsize=size, color=c, ha="center", va="center", zorder=z, rotation=rot_, **kw)
def num(p, k):
    ax.add_patch(Circle(p, 0.3, fc="white", ec="black", lw=0.4, zorder=14)); ax.text(p[0], p[1], str(k), fontsize=5.4, ha="center", va="center", zorder=15)
def circ(p, r, fc="white", ec="black", lw=0.4, z=5, ls="-", alpha=1):
    ax.add_patch(Circle(p, r, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, alpha=alpha))

C = dict(play="#F6E3A4", cave="#EADBB2", deck="#D8B98A", cat="#B08A5A", net="#7a5a36", pit="#E9C9A6", soft="#EFE2C8",
         stump="#8a6a44", wood="#8a5a2b", glass="#3d7fb0", red="#C8372D", gray="#777777", corr="#F4EBDD",
         three="#9FCB84", four="#86BC78", five="#6FA96E", wet="#D5EBEE", off="#E9DCC4", hall="#E3C08D", fan="#5a7a9a")

clip = SP(rect(U0, U1, V0, V1, 16))
PLAY = WB.intersection(SP(rect(30.0, 60, -0.9, -30, 16)))           # west building north of frame 11 (u 30)

# ---------------------------------------------------------------- main building (context)
for (u0, u1, c, s) in [(29.0, 30.0, C["hall"], ""), (30, 33, C["off"], "事務"), (33, 39, C["three"], "3 歳"), (39, 42, C["wet"], "便・倉庫"),
                       (42, 48, C["four"], "4 歳"), (48, 51, C["wet"], "便・倉庫"), (51, 52.6, C["five"], "5 歳")]:
    poly(SP(rect(u0, u1, 1.6, 5.2)), c, "none", 0, 1)
    if s: T(W((u0 + u1) / 2, 3.6), s, 7, c="#3a3a3a")
poly(SP(rect(29.0, 52.6, 0.0, 1.6, 12)), C["corr"], "none", 0, 1)
T(W(36.0, 0.8), "西吹き抜け（絵本の通り）", 5.2, rot_=90 + math.degrees(0))
line([W(29.0, 1.6), W(52.6, 1.6)], 1.0, "#333333", z=6)              # classroom west wall (h2.4 + lattice)
for uu in (33, 39, 42, 48, 51): line([W(uu, 1.6), W(uu, 5.2)], 0.6, "#555555", z=6)
# main building west wall: open at the north mouth (u 44.1–46.1), closed elsewhere north of the hall
def mwall(u0, u1): poly(SP(rect(u0, u1, -0.12, 0.0)), "#333333", "#333333", 0.3, 6)
mwall(30.0, D["north_mouth"]["u0"]); mwall(D["north_mouth"]["u1"], 52.6)
poly(SP(rect(29.0, 52.6, -0.9, -0.12, 12)), "#ECE6DA", "none", 0, 0.8)       # the gap (expansion), under the gap lid
T(W(50.0, -0.5), "すき間", 4.6, c="#777777", rot_=90)

# ---------------------------------------------------------------- west building
poly(WB.intersection(clip), "#F3EBD6", "none", 0, 0.5)
poly(PLAY, C["play"], "none", 0, 1)
poly(WB.intersection(SP(rect(29.0, 30.0, -0.9, -30))), "#F7D3B0", "none", 0, 1)     # はれのま (south of u 30)
T(Ww(29.5, 6.5), "はれのま（仮）", 6, c="#8a5a2b")
# 2nd floor above (dashed) and the low cave
CV = D["cave"]
poly(SP(rectw(CV["u0"], CV["u1"], CV["w0"], 13.5)).intersection(PLAY), C["cave"], "none", 0, 1.5)
poly(F2.intersection(SP(rect(29.6, 33.2, -0.9, -30))), "none", "#7a4fa0", 0.8, 9, ls=(0, (4, 2)))
pf = CV["platform"]
poly(SP(rectw(CV["u0"] + 0.1, CV["u1"] - 0.1, pf[0], pf[1])).intersection(PLAY), "#D9C49A", "#8a6a44", 0.45, 4)
T(Ww(31.5, (pf[0] + pf[1]) / 2), "+%d" % int(pf[2] * 1000), 4.6, c="#5a4a30")
poly(SP(rectw(CV["u0"], CV["u1"], CV["store"][0], CV["store"][1])).intersection(PLAY), "#CDBB98", "#555555", 0.45, 4, hatch="////")
# stair
poly(STAIR, "#888888", "#333333", 0.5, 6); T(Ww(31.5, 2.7), "階段\n（2 階へ）", 5, c="white")
line([Ww(33.0, 1.3), Ww(33.0, 4.1)], 0.9, "#333333", z=7)                       # rail between stair top and the room
# west building outline, columns
poly(WB.intersection(clip), "none", "black", 1.3, 7)
for (u, v) in COLS:
    if u > 29.5:
        p = W(u, v); ax.add_patch(Polygon([(p[0] - 0.13, p[1] - 0.13), (p[0] + 0.13, p[1] - 0.13), (p[0] + 0.13, p[1] + 0.13), (p[0] - 0.13, p[1] + 0.13)], fc="black", ec="black", zorder=9))
# east wall of the west building with the north mouth
EW = 0.15
def ewall(u0, u1): poly(SP(rect(u0, u1, -0.9, -0.9 - EW)), "#333333", "#333333", 0.3, 8)
ewall(33.0, D["north_mouth"]["u0"]); ewall(D["north_mouth"]["u1"], 51.0)
nm = D["north_mouth"]; poly(SP(rect(nm["u0"], nm["u1"], 0.05, -1.05)), C["corr"], "none", 0, 8.5)   # the bridge across the gap
# big door on the north-west face (span 16, between the west columns of u 45 and u 48)
wc = sorted([c for c in COLS if c[0] > 44 and -c[1] - 0.9 > 5], key=lambda c: c[0])
pa, pb = np.array(W(*wc[0])), np.array(W(*wc[1]))
mid = (pa + pb) / 2; dv = (pb - pa) / np.linalg.norm(pb - pa); half = D["big_door"]["width"] / 2
da, db = mid - dv * half, mid + dv * half
nrm = np.array([-dv[1], dv[0]]); nrm = nrm if np.dot(nrm, np.array(Ww(46.5, 6.0)) - mid) > 0 else -nrm
line([tuple(da), tuple(db)], 3.2, "white", z=8.2)
line([tuple(da), tuple(db)], 0.6, C["red"], z=8.4)
for s in (da, db): line([tuple(s), tuple(s + nrm * 0.25)], 0.6, C["red"], z=8.4)
# ---------------------------------------------------------------- play elements
# soft ring and stump
st = D["stump"]
poly(SPt(Ww(st["u"], st["w"])).buffer(st["soft_r"], 64).intersection(PLAY), C["soft"], "#B79B6B", 0.4, 2, ls=(0, (3, 2)))
poly(SPt(Ww(st["u"], st["w"])).buffer(st["crown_r"], 64).intersection(PLAY), "none", C["stump"], 0.5, 6, ls=(0, (1, 1.2)))
cpt = np.array(Ww(st["u"], st["w"]))
up = np.array(Ww(st["u"] + 1, st["w"])) - cpt; up = up / np.linalg.norm(up); rt = np.array([up[1], -up[0]])
for (ang, L) in st["branches"]:
    a = math.radians(ang); d = up * math.cos(a) + rt * math.sin(a)
    p0 = cpt + d * st["trunk_r"] * 0.8; p1 = cpt + d * L; pm = cpt + d * (L * 0.55) + np.array([-d[1], d[0]]) * 0.15
    ax.plot([p0[0], pm[0], p1[0]], [p0[1], pm[1], p1[1]], lw=2.4, color=C["stump"], zorder=7, solid_capstyle="round")
circ(tuple(cpt), st["trunk_r"], fc="#A88456", ec="#5a4026", lw=0.7, z=8)
for rr in (0.15, 0.3, 0.42): circ(tuple(cpt), rr, fc="none", ec="#6a5030", lw=0.25, z=8.5)
# lower deck (storage under) and climbing wall
dk = D["deck"]
poly(SP(rectw(dk["u0"], dk["u1"], dk["w0"], dk["w1"])), C["deck"], "#5a4026", 0.6, 5)
T(Ww((dk["u0"] + dk["u1"]) / 2, 1.95), "デッキ +1200\n下は道具入れ", 4.8, c="#3a2a1a")
ds = D["deck_steps"]; n_ = len(ds["hs"])
for k, h in enumerate(ds["hs"]):
    ua = ds["u0"] + (ds["u1"] - ds["u0"]) * k / n_; ub = ds["u0"] + (ds["u1"] - ds["u0"]) * (k + 1) / n_
    poly(SP(rectw(ua, ub, ds["w0"], ds["w1"])), "#E3CDA6", "#5a4026", 0.45, 5)
    T(Ww((ua + ub) / 2, (ds["w0"] + ds["w1"]) / 2), "+%d" % int(h * 1000), 4.2, c="#3a2a1a")
cl = D["climb"]
for k in range(6):
    uu = cl["u0"] + (cl["u1"] - cl["u0"]) * k / 5
    line([Ww(uu, dk["w0"]), Ww(uu, dk["w0"] + 0.18)], 0.9, "#3a2a1a", z=10)
# catwalk (follows the outline 0.25 inside, width 0.9, east wall + north side)
cw = D["catwalk"]
band = WB.buffer(-cw["inset"], join_style=1).difference(WB.buffer(-(cw["inset"] + cw["width"]), join_style=1))
zone = SP(rectw(cw["u_start"], 60, -0.5, 1.6)).union(SP(rectw(cw["north_u"], 60, -0.5, cw["west_w"])))
CAT = band.intersection(zone)
poly(CAT, "#E6D3B3", C["cat"], 0.6, 10, alpha=0.85)
poly(CAT, "none", C["cat"], 0.0, 10, hatch="....")
# ring walkway around the net (same height as the catwalk) and a bridge to the north side
RG = D["ring"]; npt0 = Ww(D["net"]["u"], D["net"]["w"])
RING = SPt(npt0).buffer(RG["outer_r"], 96).difference(SPt(npt0).buffer(RG["inner_r"], 96))
bf, bt = D["bridge"]["from"], D["bridge"]["to"]
BRIDGE = SP(rectw(bf[0], bt[0], bf[1] - D["bridge"]["width"] / 2, bf[1] + D["bridge"]["width"] / 2)).difference(SPt(npt0).buffer(RG["inner_r"], 96))
for g in (RING, BRIDGE):
    poly(g, "#E6D3B3", C["cat"], 0.6, 10.2, alpha=0.85); poly(g, "none", C["cat"], 0.0, 10.2, hatch="....")
for k in range(RG["rods"]):
    a = 2 * math.pi * (k + 0.5) / RG["rods"]; rr_ = (RG["inner_r"] + RG["outer_r"]) / 2
    circ((npt0[0] + rr_ * math.cos(a), npt0[1] + rr_ * math.sin(a)), 0.07, fc="#333333", ec="none", z=12)
# slide from the catwalk's west end
sl = D["slide"]; s0, s1 = np.array(Ww(*sl["from"])), np.array(Ww(*sl["to"]))
sd = (s1 - s0) / np.linalg.norm(s1 - s0); sn = np.array([-sd[1], sd[0]]) * sl["width"] / 2
poly([tuple(s0 + sn), tuple(s1 + sn), tuple(s1 - sn), tuple(s0 - sn)], "#CFE0EA", "#3d7fb0", 0.6, 9)
ax.add_patch(FancyArrowPatch(tuple(s0 + sd * 0.4), tuple(s1 - sd * 0.2), arrowstyle="-|>", mutation_scale=7, color="#3d7fb0", lw=0.6, zorder=9.5))
# net and pit
nt, pt = D["net"], D["pit"]; npt = Ww(nt["u"], nt["w"])
circ(npt, pt["r"], fc=C["pit"], ec="#8a6a44", lw=0.6, z=3)
circ(npt, pt["r"] - 0.12, fc="#F2DEC4", ec="none", z=3.1)
for k in range(24):
    a = 2 * math.pi * k / 24
    line([(npt[0] + nt["bottom_r"] * math.cos(a), npt[1] + nt["bottom_r"] * math.sin(a)), (npt[0] + nt["ring_r"] * math.cos(a), npt[1] + nt["ring_r"] * math.sin(a))], 0.3, C["net"], z=11)
for rr in np.linspace(nt["bottom_r"], nt["ring_r"], 7):
    circ(npt, rr, fc="none", ec=C["net"], lw=0.3, z=11)
circ(npt, nt["ring_r"], fc="none", ec=C["net"], lw=1.2, z=11.5)
# niches along the west wall and the round bench at the NW corner
def west_w(u):   # w of the west face at u (straight part)
    ln = SL([Ww(u, 0), Ww(u, 20)]); x = ln.intersection(WB.exterior)
    pts_ = [x] if x.geom_type == "Point" else list(getattr(x, "geoms", []))
    best = max(pts_, key=lambda p: SPt(Ww(u, 0)).distance(p))
    return SPt(Ww(u, 0)).distance(best)
for (ua, ub) in D["niches"]:
    wa = min(west_w(ua), west_w(ub))
    poly(SP(rectw(ua, ub, wa - D["niche_depth"], wa + 0.2)).intersection(WB), "#D9C49A", "#5a4026", 0.5, 6)
    line([Ww(ua, wa - D["niche_depth"]), Ww(ub, wa - D["niche_depth"])], 0.8, "#5a4026", z=7)
for (ua, ub) in [(D["niches"][0][1], D["niches"][1][0]), (D["niches"][1][1], D["niches"][2][0])]:
    wa = min(west_w(ua), west_w(ub))
    line([Ww(ua + 0.15, wa + 0.05), Ww(ub - 0.15, wa + 0.05)], 1.6, C["glass"], z=9)   # 地窓 between the niches
rb = D["round_bench"]
rbz = WB.difference(WB.buffer(-rb["depth"], join_style=1)).intersection(SP(rectw(rb["u0"], rb["u1"], 6.5, 20)))
poly(rbz, "#D9C49A", "#5a4026", 0.5, 6)
# north window seat facing the reading garden's maple
nw = D["north_window"]
north_edge = WB.exterior.intersection(SP(rectw(50.6, 51.6, nw["w0"], nw["w1"])))
if not north_edge.is_empty:
    gs = [north_edge] if north_edge.geom_type == "LineString" else list(getattr(north_edge, "geoms", []))
    for g in gs:
        if g.geom_type == "LineString": line(list(g.coords), 1.6, C["glass"], z=9)
poly(SP(rectw(51.0 - 0.15 - nw["seat_d"], 51.0 - 0.15, nw["w0"], nw["w1"])), "#D9C49A", "#5a4026", 0.5, 6.5)
if MAPLE:   # the maple stands about 3 m north of the north window (outside this sheet): point to it
    a0 = Ww(50.9, 1.6); a1 = Ww(51.6, 1.6)
    ax.add_patch(FancyArrowPatch(a0, a1, arrowstyle="-|>", mutation_scale=8, color="#B4553A", lw=0.8, zorder=9))
    T(Ww(49.6, 3.2), "→ 読書の庭のモミジ\n（北へ約 %.0f m）" % (MAPLE[0] - 51.0), 5.2, c="#8a3a2a")
# east wall: peeking windows along the catwalk (dashed, overhead)
for (ua, ub) in [(36.4, 39.0), (39.6, 41.8), (47.0, 49.6)]:
    line([W(ua, -0.97), W(ub, -0.97)], 1.3, C["glass"], z=8.6, ls=(0, (2, 1)))
# fans: phi 1.1 under the ridge lid (the void w 0–1.0), one per span, like the main building
FN = D["fans"]
for u in FN["u"]:
    p = Ww(u, FN["w"]); circ(p, FN["d"] / 2, fc="none", ec=C["fan"], lw=0.5, z=12, ls=(0, (3, 2)))
    for a in (0, 120, 240):
        aa = math.radians(a + 20); line([p, (p[0] + 0.5 * math.cos(aa), p[1] + 0.5 * math.sin(aa))], 0.8, C["fan"], z=12)
    circ(p, 0.08, fc=C["fan"], ec="none", z=12.5)
# the ridge lid (overhead): the void under it
lw_ = D["lid"]
line([Ww(30.0, lw_["w1"]), Ww(51.0, lw_["w1"])], 0.5, "#3d7fb0", ls=(0, (6, 3)), z=8.8)
# circulation arrows
def arrow(a, b, c=C["red"], lw=1.1, z=13):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, color=c, lw=lw, zorder=z))
arrow(Ww(30.4, 0.65), Ww(33.6, 0.65))
arrow(W(45.1, 1.0), Ww(45.1, 2.2))
T(Ww(29.55, 0.65), "ホール・東の帯から", 4.8, c=C["red"])
T(W(45.1, 2.3), "西吹き抜けから", 4.8, c=C["red"])
# open floor (area)
fixed = unary_union([SP(rectw(30.0, 33.0, 0, 30)),                      # cave + stair + passage zone
                     SP(rectw(dk["u0"], dk["u1"], dk["w0"], dk["w1"])),
                     SPt(Ww(st["u"], st["w"])).buffer(st["soft_r"]),
                     SP(rectw(ds["u0"], ds["u1"], ds["w0"], ds["w1"])),
                     SPt(npt).buffer(pt["r"] + 0.3),
                     rbz] + [SP(rectw(ua, ub, west_w(ua) - D["niche_depth"], 30)) for ua, ub in D["niches"]])
OPEN = PLAY.difference(fixed)
A_play, A_open, A_cave = PLAY.area, OPEN.area, SP(rectw(30, 33, 4.1, 30)).intersection(PLAY).area
T(Ww(46.0, 6.6), "あけておく床\n約 %d m²" % round(A_open), 7.5, c="#8a6a2a", weight="bold")
T(Ww(38.5, 9.0), "遊戯室", 13, c="#7a5a1a", weight="bold")
# span labels
for k in range(11, 19):
    u0 = 3 * (k - 1)
    if u0 >= U0: line([W(u0, -15.2), W(u0, -14.5)], 0.4, "#999999", z=3)
    uc = u0 + 1.5
    if U0 < uc < U1 - 0.5: T(W(uc, -15.0), str(k), 6.5, c="#666666")
T(W(52.2, -15.0), "スパン", 5.2, c="#666666")
# numbers
NUMS = [
    (Ww(33.25, 0.65), "南の口（ホール・東の帯から、階段の東を抜ける）。口①はここにまとめた"),
    (W(46.5, 0.8), "北の口（口②、西吹き抜けから、すき間を渡る）"),
    (Ww(30.6, 5.0), "洞（2 階の下、梁の下 h2.23・床の裏 h3.17）。木のてっぺんが 2 階の床に届く。西に腰掛けの台 +300"),
    (Ww(31.5, 12.0), "道具入れ 約 %.1f m²（西の低い隅、発表会の椅子など。倉庫 30 m² の一つに数える）" % SP(rectw(CV["u0"], CV["u1"], CV["store"][0], CV["store"][1])).intersection(PLAY).area),
    (Ww(st["u"] + 1.9, st["w"] + 1.6), "枝付きの切り株（幹 φ1.0、枝の広がり φ4.0）。頭は 2 階の床の下、北の枝は天井の高い側へ出る。行事の日は木の前が舞台"),
    (Ww(dk["u0"] + 0.4, 2.3), "デッキ h1.2（下はマット・ボールの道具入れ）。南に家具階段 +300／600／900、東の壁に登り壁 → キャットウォーク"),
    (Ww(44.0, 0.7), "キャットウォーク h3.0、幅 0.9（東の壁と北の角に沿う、手すり h1.1）。ネットの輪から北の側へ橋（幅 0.9）を渡し、空中の輪にする"),
    (Ww(nt["u"] - 2.4, nt["w"] + 0.8), "摺鉢ネット（上の縁 φ4.2、下の口 φ0.6 が h0.5）。まわりに輪の通路 h3.0（幅 0.8、外 φ5.8）、ネットの縁は通路の内側の鋼の輪に一周留める。輪は梁から 6 本の吊り材"),
    (Ww(nt["u"] + 1.2, nt["w"] - 0.2), "穴の底（φ3.2、−450、マット 100）"),
    (Ww(47.9, 8.9), "すべり台（キャットウォークの西の端 → 床）"),
    (Ww(35.0, west_w(35.0) - 1.1), "ひだ：柱と柱のあいだのくぼみ（造作の箱、奥行き 0.7、座 +300、天板 h1.4、奥に格子の覗き窓）。あいだの壁に地窓。詳しくは play02"),
    (Ww(43.3, 11.0), "北西の丸い角の丸いベンチ"),
    (Ww(47.0, 11.0), "搬入の大戸（幅 3.6×h3.0、ふだんは閉じる、避難口）"),
    (Ww(50.0, 1.6), "北の窓辺の腰掛け +300（窓 h350〜1200、座って読書の庭のモミジを見る）"),
    (W(40.7, -1.35), "東の壁の覗き窓（キャットウォークの高さ、すき間越しに本館）"),
    (Ww(FN["u"][1], 1.5), "天井扇 φ1.1 ×6（本館と同じ、越屋根の吹き抜け w 0–1.0 の真下、h6.0）"),
]
for i, (p, s) in enumerate(NUMS, 1): num(p, i)

# ---------------------------------------------------------------- section (E–W through the net, looking north)
su = D["section_u"]
SX0, SX1, SZ0, SZ1 = -15.6, 5.2, -0.9, 9.3
SB = 30
ax2 = fig.add_axes([PL / 297, SB / 420, (SX1 - SX0) * 10 / 297, (SZ1 - SZ0) * 10 / 420])
ax2.set_xlim(SX0, SX1); ax2.set_ylim(SZ0, SZ1); ax2.set_aspect("equal"); ax2.axis("off")
def P2(pts, fc="none", ec="black", lw=0.45, z=2, ls="-", hatch=None): poly(pts, fc, ec, lw, z, ls, 1, ax2, hatch)
def L2(pts, lw=0.45, c="black", ls="-", z=5): line(pts, lw, c, ls, z, ax2)
def T2(x, y, s, size=5.6, c="#222222", ha="center", **kw): ax2.text(x, y, s, fontsize=size, color=c, ha=ha, va="center", zorder=12, **kw)
def X(w): return -0.9 - w                                            # section x = v
west_face = west_w(su)
GL = -0.3
P2([(SX0, GL), (SX1, GL), (SX1, GL - 0.5), (SX0, GL - 0.5)], "#DDD6C8", "none", 0, 1, hatch="////")
# main building (v 0 … 5.2): floor, west wall, classroom wall with lattice, roof 1/12, lid over the west void
P2([(0, 0), (SX1, 0), (SX1, -0.12), (0, -0.12)], "#C8B48C", "none")
P2([(-0.12, GL), (0, GL), (0, 4.0), (-0.12, 4.0)], "#333333", "#333333", 0.3, 6)
P2([(1.55, 0), (1.67, 0), (1.67, 2.4), (1.55, 2.4)], "#333333", "#333333", 0.3, 6)
for zz in np.arange(2.5, 3.9, 0.12): pass
for xx in np.arange(1.56, 1.67, 0.05): pass
L2([(1.61, 2.4), (1.61, 3.87)], 1.6, "#8a5a2b", z=6)
T2(1.95, 3.1, "縦格子", 4.6, c="#8a5a2b", ha="left")
roofz = lambda v: 4.0 - (v - 1.6) / 12 if v > 1.6 else 4.0
L2([(1.6, 4.0), (SX1, roofz(SX1))], 1.2, "#333333", z=6)
P2([(-0.12, 4.0), (1.6, 4.0), (1.6, 4.15), (-0.12, 4.15)], "#555555", "none", z=6)
# the main building's floating lid continues west over the gap to the west building's wall ("すき間の蓋", 3dm 50a: z 4.30 at v 1.95 → 4.60 at v −0.9)
lidz = lambda v: 4.30 + (1.95 - v) / 2.85 * 0.30
P2([(1.95, lidz(1.95) - 0.06), (-0.9, lidz(-0.9) - 0.06), (-0.9, lidz(-0.9)), (1.95, lidz(1.95))], "#E8EEF2", "#3d7fb0", 0.4, 7)
T2(1.0, 4.95, "浮いた蓋（本館）→ すき間の蓋（西館の壁まで）", 4.4, c="#3d7fb0")

T2(0.8, 1.2, "西吹き\n抜け", 4.6, c="#666666")
T2(3.6, 1.6, "便・倉庫（スパン 14）", 4.8, c="#666666")
# gap
P2([(-0.9, 0), (0, 0), (0, -0.12), (-0.9, -0.12)], "#ECE6DA", "none")
T2(-0.45, 0.35, "すき間", 4.2, c="#777777")
# west building
WT = 0.15
z_roof = lambda w: 8.0 - (8.0 - 4.65) * w / west_face     # east 8.0 → west face about 4.65 (3dm)
P2([(X(0), GL), (X(0) - WT, GL), (X(0) - WT, 8.0), (X(0), 8.0)], "#333333", "#333333", 0.3, 6)                     # east wall
P2([(X(west_face), GL), (X(west_face) + WT, GL), (X(west_face) + WT, z_roof(west_face)), (X(west_face), z_roof(west_face))], "#333333", "#333333", 0.3, 6)
ws = np.linspace(0, west_face, 30)
L2([(X(w), z_roof(w) + 0.05) for w in ws], 2.0, "#333333", z=6)
P2([(X(-0.2), 8.0 + 0.02), (X(1.2), z_roof(1.2) + 0.02), (X(1.2), 8.55), (X(-0.2), 8.62)], "#E8EEF2", "#3d7fb0", 0.5, 7)   # ridge lid
T2(X(0.5), 9.0, "浮いた蓋（西館）", 4.6, c="#3d7fb0")
# east wall openings: peeking window at catwalk height, high window above the main roof
for (h0, h1, s) in [(D["east_peek"]["h0"], D["east_peek"]["h1"], "覗き窓"), (D["east_high"]["h0"], D["east_high"]["h1"], "東の高窓（朝の光）")]:
    P2([(X(0) - WT, h0), (X(0), h0), (X(0), h1), (X(0) - WT, h1)], "#CFE0EA", C["glass"], 0.6, 7)
    T2(X(0) + 0.25, (h0 + h1) / 2, s, 4.6, c=C["glass"], ha="left")
# floor with the pit
pr = D["pit"]["r"]; px0, px1 = X(nt["w"] - pr), X(nt["w"] + pr)
P2([(X(0), 0), (px0, 0), (px0, -D["pit"]["depth"]), (px1, -D["pit"]["depth"]), (px1, 0), (X(west_face), 0), (X(west_face), -0.12), (X(0), -0.12)], "#C8B48C", "none", z=2)
P2([(px0, -D["pit"]["depth"]), (px1, -D["pit"]["depth"]), (px1, -D["pit"]["depth"] + D["pit"]["mat"]), (px0, -D["pit"]["depth"] + D["pit"]["mat"])], "#E9A97A", "#8a5a2b", 0.4, 3)
# catwalk + rail
cwx0, cwx1 = X(cw["inset"]), X(cw["inset"] + cw["width"])
P2([(cwx0, cw["h"]), (cwx1, cw["h"]), (cwx1, cw["h"] - 0.15), (cwx0, cw["h"] - 0.15)], "#B08A5A", "#5a4026", 0.5, 8)
L2([(cwx1, cw["h"]), (cwx1, cw["h"] + cw["rail"])], 0.6, "#5a4026", z=8)
L2([(cwx1 - 0.05, cw["h"] + cw["rail"]), (cwx0 + 0.02, cw["h"] + cw["rail"])], 0.6, "#5a4026", z=8)
# net (ring at catwalk height, sagging to the bottom opening)
rr, br = nt["ring_r"], nt["bottom_r"]; cx = X(nt["w"])
for side in (-1, 1):
    xs_ = np.linspace(rr, br, 20); zz = nt["bottom_h"] + (cw["h"] - nt["bottom_h"]) * ((xs_ - br) / (rr - br)) ** 1.6
    L2([(cx + side * x_, z_) for x_, z_ in zip(xs_, zz)], 1.0, C["net"], z=9)
L2([(cx - rr, cw["h"]), (cx + rr, cw["h"])], 0.4, C["net"], ls=(0, (1, 1)), z=9)
for sgn in (-1, 1):
    xa, xb = cx + sgn * RG["inner_r"], cx + sgn * RG["outer_r"]
    P2([(xa, cw["h"]), (xb, cw["h"]), (xb, cw["h"] - 0.15), (xa, cw["h"] - 0.15)], "#B08A5A", "#5a4026", 0.5, 8)
    L2([(xb, cw["h"]), (xb, cw["h"] + cw["rail"])], 0.6, "#5a4026", z=8)
    L2([(xa, cw["h"]), (xa, cw["h"] + 0.15)], 0.8, "#5a4026", z=8)                     # kick board at the net edge
    L2([((xa + xb) / 2, cw["h"]), ((xa + xb) / 2, z_roof(abs(xa - X(0))) - 0.1)], 0.4, "#333333", ls=(0, (3, 2)), z=7)   # hanger rod
T2(cx - RG["outer_r"] - 0.15, cw["h"] + 0.5, "輪の通路 h3.0", 4.6, ha="right")
# fan under the lid (seen beyond, u 43.5)
L2([(X(FN["w"]) - FN["d"] / 2, FN["h"]), (X(FN["w"]) + FN["d"] / 2, FN["h"])], 1.6, C["fan"], z=9)
L2([(X(FN["w"]), FN["h"]), (X(FN["w"]), 8.3)], 0.5, C["fan"], z=9)
T2(X(FN["w"]) - 0.7, FN["h"], "天井扇 φ1.1", 4.6, c=C["fan"], ha="right")
# west wall: low window
P2([(X(west_face), 0.0), (X(west_face) + WT, 0.0), (X(west_face) + WT, 0.6), (X(west_face), 0.6)], "#CFE0EA", C["glass"], 0.6, 7)
T2(X(west_face) + 0.3, 0.9, "地窓", 4.6, c=C["glass"])
# people (3–5 years, h 1.0–1.1; adult 1.6)
def kid(x, z0, h=1.05, c="#555555"):
    hd = h * 0.13; ax2.add_patch(Circle((x, z0 + h - hd), hd, fc="white", ec=c, lw=0.5, zorder=10))
    L2([(x, z0 + h - 2 * hd), (x, z0 + h * 0.45)], 0.6, c, z=10)
    L2([(x - 0.12, z0), (x, z0 + h * 0.45), (x + 0.12, z0)], 0.6, c, z=10)
    L2([(x - 0.15, z0 + h * 0.62), (x, z0 + h * 0.72), (x + 0.15, z0 + h * 0.62)], 0.6, c, z=10)
kid(X(0.7), cw["h"]); kid(cx + 0.9, 1.1, 1.0); kid(cx, -D["pit"]["depth"] + D["pit"]["mat"], 1.0); kid(X(7.0), 0); kid(X(10.5), 0, 1.6, "#777777")
# levels
for z_, s in [(0, "FL ±0"), (GL, "GL −300"), (cw["h"], "h3.0"), (8.0, "8.0"), (z_roof(west_face), "%.1f" % z_roof(west_face))]:
    pass
T2(X(west_face) - 0.2, z_roof(west_face) + 0.25, "%.1f" % z_roof(west_face), 4.6, ha="right")
T2(X(0) + 0.15, 8.2, "8.0", 4.6, ha="left")
T2(cwx1 - 0.15, cw["h"] - 0.35, "キャットウォーク h3.0", 4.6, ha="right")
T2(cx + 2.0, -0.18, "穴の底 −450", 4.6, ha="left")
T2(X(west_face) + 0.25, -0.12, "FL ±0", 4.2, ha="left")
T2(SX0 + 0.1, 9.05, "東西の断面（摺鉢ネットの中心 u %.1f で切る、北を見る）　左＝西（道路）、右＝東（本館）" % su, 7, ha="left", weight="bold")
for xx, s in [(X(0), "西館の東の線"), (0, "本館の西の外壁")]:
    L2([(xx, -0.75), (xx, -0.55)], 0.4, "#999999")
T2(X(west_face / 2), 0.35, "遊戯室（西館）", 6, c="#7a5a1a")
T2(2.6, 0.35, "本館", 5.2, c="#555555")

# ---------------------------------------------------------------- section 2 (N–S through the tree, looking west)
s2w = D["section2_w"]
QU0, QU1, QZ0, QZ1 = 29.5, 36.3, -0.7, 6.6
ax3 = fig.add_axes([226 / 297, 34 / 420, (QU1 - QU0) * 10 / 297, (QZ1 - QZ0) * 10 / 420])
ax3.set_xlim(QU0, QU1); ax3.set_ylim(QZ0, QZ1); ax3.set_aspect("equal"); ax3.axis("off")
def P3(pts, fc="none", ec="black", lw=0.45, z=2, ls="-", hatch=None): poly(pts, fc, ec, lw, z, ls, 1, ax3, hatch)
def L3(pts, lw=0.45, c="black", ls="-", z=5): line(pts, lw, c, ls, z, ax3)
def T3(x, y, s_, size=4.8, c="#222222", ha="center", **kw): ax3.text(x, y, s_, fontsize=size, color=c, ha=ha, va="center", zorder=12, **kw)
P3([(QU0, -0.3), (QU1, -0.3), (QU1, -0.65), (QU0, -0.65)], "#DDD6C8", "none", 0, 1, hatch="////")
P3([(QU0, 0), (QU1, 0), (QU1, -0.12), (QU0, -0.12)], "#C8B48C", "none")
P3([(29.88, 0), (30.0, 0), (30.0, CV["slab"]), (29.88, CV["slab"])], "#333333", "#333333", 0.3, 6)       # wall to はれのま
T3(29.7, 1.2, "はれのま", 4.4, c="#777777", rotation=90)
P3([(QU0, CV["slab"]), (33.0, CV["slab"]), (33.0, CV["slab_top"] + 0.05), (QU0, CV["slab_top"] + 0.05)], "#555555", "none", z=6)  # 2F floor
for ub in CV["beams_u"]:
    P3([(ub - 0.09, CV["beam_bottom"]), (ub + 0.09, CV["beam_bottom"]), (ub + 0.09, CV["slab"]), (ub - 0.09, CV["slab"])], "#8a6a44", "#5a4026", 0.4, 6)
T3(31.5, 3.55, "2 階（会議室・ホール）", 4.6, c="#7a4fa0")
zr = 8.0 - (8.0 - 4.65) * s2w / west_face
L3([(33.0, zr), (QU1, zr)], 1.6, "#333333", z=6)
T3(34.6, zr + 0.25, "屋根 h%.1f（東から %.1f の高さ）" % (zr, s2w), 4.4)
# tree: trunk, branches reaching the slab between the beams, the north ones out into the tall side
tu = st["u"]; th_ = st["height"]
P3([(tu - 0.5, 0), (tu + 0.5, 0), (tu + 0.42, 1.1), (tu - 0.42, 1.1)], "#A88456", "#5a4026", 0.6, 7)
BR = [(-1.6, 2.15), (-1.0, 2.9), (-0.3, 3.1), (0.5, 3.1), (1.0, 2.2), (1.6, 3.4), (2.1, 3.0)]
for (dx, z_) in BR:
    xm = tu + dx * 0.45; zm = 1.1 + (z_ - 1.1) * 0.55
    ax3.plot([tu + dx * 0.1, xm, tu + dx], [1.05, zm, z_], lw=2.6 if abs(dx) < 1.2 else 2.0, color=C["stump"], zorder=7, solid_capstyle="round")
P3([(tu - st["soft_r"], 0.0), (tu + st["soft_r"], 0.0), (tu + st["soft_r"], 0.04), (tu - st["soft_r"], 0.04)], "#E9A97A", "none", z=3)
# platform (beyond, west) and kids
P3([(30.1, 0), (32.9, 0), (32.9, CV["platform"][2]), (30.1, CV["platform"][2])], "none", "#8a6a44", 0.4, 3, ls=(0, (2, 1.5)))
def kid3(x, z0, h=1.05, c="#555555"):
    hd = h * 0.13; ax3.add_patch(Circle((x, z0 + h - hd), hd, fc="white", ec=c, lw=0.5, zorder=10))
    L3([(x, z0 + h - 2 * hd), (x, z0 + h * 0.45)], 0.6, c, z=10); L3([(x - 0.12, z0), (x, z0 + h * 0.45), (x + 0.12, z0)], 0.6, c, z=10)
    L3([(x - 0.15, z0 + h * 0.62), (x, z0 + h * 0.72), (x + 0.15, z0 + h * 0.62)], 0.6, c, z=10)
kid3(tu - 0.9, 1.25, 1.0); kid3(tu + 1.3, 1.45, 1.0); kid3(34.6, 0); kid3(35.4, 0, 1.6, "#777777")
T3(33.0, -0.5, "2 階の床の縁", 4.2, c="#7a4fa0")
L3([(33.0, -0.35), (33.0, -0.2)], 0.4, "#7a4fa0")
for z_, s_ in [(CV["beam_bottom"], "梁の下 2.23"), (CV["slab"], "床の裏 3.17")]:
    T3(QU0 + 0.05, z_ - 0.18, s_, 4.2, ha="left", c="#555555")
fig.text(226 / 297, 112 / 420, "南北の断面（木の中心、東から %.1f で切る、西を見る）\n左＝南（はれのま）、右＝北" % s2w, fontsize=5.6, weight="bold")

# ---------------------------------------------------------------- titles, legend
fig.text(12 / 297, 408 / 420, "育ち舎　遊戯室（スパン 11–17）　たたき台", fontsize=13, weight="bold")
fig.text(12 / 297, 400 / 420, "1/100（A3）　2026-10-21　上が北（本館の背骨に沿って回した）。西館の東西は「東から」（v = −0.9 の線から西へ）。寸法は data/play.json。"
         "破線の紫＝2 階の床（上）、青の破線＝越屋根の吹き抜け（上）、破線の円＝枝の広がり・扇、点の帯＝キャットウォーク（頭上 h3.0）。",
         fontsize=6.2, color="#444444")
fig.text(12 / 297, 395 / 420, "面積（概算）：遊戯室 %.0f m²（うち洞・階段・南の口のスパン 11 は %.0f m²）　あけておく床 約 %.0f m²" % (A_play, SP(rectw(30, 33, 0, 30)).intersection(PLAY).area, A_open),
         fontsize=6.2, color="#444444")
lx, ly = 222, 392
fig.text(lx / 297, ly / 420, "番号", fontsize=7, weight="bold")
for i, (_, s) in enumerate(NUMS, 1):
    fig.text(lx / 297, (ly - 5 - (i - 1) * 9.2) / 420, f"{i}", fontsize=6, weight="bold")
    import textwrap
    fig.text((lx + 5) / 297, (ly - 5 - (i - 1) * 9.2) / 420, "\n".join(textwrap.wrap(s, 21)), fontsize=5.6, va="top")
fig.text(lx / 297, 168 / 420, "遊び方の輪：南の口 → 家具階段 → デッキ → 登り壁 →\nキャットウォーク ⇄ ネットの輪 ⇄ 橋 → ネットで降りる（穴の底）\n／すべり台 → 北の口から西吹き抜けへ。木は低い洞に：てっぺんが\n2 階の床に届き、枝の先が高い側へ出る。",
         fontsize=5.6, color="#7a4a1a", va="top")

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, "sodachiya_play_01." + ext), dpi=200 if ext == "png" else None)
print("play %.1f  open %.1f  cave %.1f" % (A_play, A_open, A_cave))
