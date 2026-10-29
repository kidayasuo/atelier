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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import fonts42   # 文字は文字のまま（Type42）

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
# 公園の中身（ユーザー 10-29、data/approachA.jsonのPARK_PLAN）：局所座標(X, Y)＝原点PARK[0]、Xは川に沿ってPARK[3]へ、Yは南西の辺に沿ってPARK[1]へ
_PO = np.array(PARK[0]); _PX = np.array(PARK[3]) - _PO; _PX /= np.linalg.norm(_PX); _PY = np.array(PARK[1]) - _PO; _PY /= np.linalg.norm(_PY)
def PK(x, y): p = _PO + _PX * x + _PY * y; return (float(p[0]), float(p[1]))
def PKR(x0, x1, y0, y1): return [PK(x0, y0), PK(x1, y0), PK(x1, y1), PK(x0, y1)]
PP = PARK_PLAN
# 車の帯（ユーザー 10-29 9時）：道路側の辺の真ん中の開口から、同じ半径の弧2つのS字で川の端の非常用の門へ
_cb = PP["car_band"]; _dY = _cb["entry_y"] - _cb["exit_y"]; BAND_TH = 2 * math.atan(_dY / _cb["len"]); BAND_R = _cb["len"] / (2 * math.sin(BAND_TH))
_c1 = np.array([0.0, _cb["entry_y"] - BAND_R]); _c2 = np.array([_cb["len"], _cb["exit_y"] + BAND_R])
BAND_CL = [tuple(_c1 + BAND_R * np.array([math.sin(t), math.cos(t)])) for t in np.linspace(0, BAND_TH, 40)] + \
          [tuple(_c2 + BAND_R * np.array([-math.sin(t), -math.cos(t)])) for t in np.linspace(BAND_TH, 0, 40)[1:]]     # 中心の線（局所座標）
BAND_LOC = SL(BAND_CL).buffer(_cb["w"] / 2, cap_style=2, resolution=32).intersection(SP([(0, 0), (12, 0), (12, 12), (0, 12)]))                        # 帯（局所座標、両端は辺に直角）
BAND_R_IN = BAND_R - _cb["w"] / 2
PK_BAND = [PK(*q) for q in BAND_LOC.exterior.coords]
# 車の帯2.5は芝の下の保護材なので図には描かない（ユーザー 10-29：見せない）。形はBAND_LOC（3dmにも入れない）
_bcl = SL(BAND_CL)
PK_ROT = math.degrees(math.atan2(_PX[1], _PX[0]))                                             # 文字を川の向きに
poly(PKR(*PP["bike_overflow"]["x"], *PP["bike_overflow"]["y"]), fc="none", ec="#999999", lw=0.3, ls=(0, (1.5, 1.5)), z=1.3)
T(PK(2.0, 10.0), "行事の日の\n自転車のあふれ", 3.8, c="#777777")
_rl = PP["rail"]; _op = PP["opening"]
def rail_posts(y0, y1, pitch): n = max(1, round((y1 - y0) / pitch)); return list(np.linspace(y0, y1, n + 1))
for _ya, _yb in _rl["segments"]:
    line([PK(0, _ya), PK(0, _yb)], lw=1.0, c="#333333", z=7)                                  # 道路側の鉄柵h1.1（現況）
    for _y in rail_posts(_ya, _yb, _rl["post_pitch"]): post(PK(0, _y), 0.12)
for _y in _op["bollards_y"]: ax.add_patch(Circle(PK(0, _y), 0.12, fc="white", ec="#333333", lw=0.5, zorder=11))   # 上げ下げ式の車止め
_br = PP["bars"]; _bx = [_br["x0"] + _br["len"] * k for k in range(len(_br["h"]) + 1)]
BARS_CLR = SP(PKR(_bx[0], _bx[-1], max(0.0, _br["y"] - _br["clear"]), _br["y"] + _br["clear"]))
poly(BARS_CLR, fc="none", ec="#999999", lw=0.25, ls=(0, (1, 1.2)), z=1.4)                    # 前1.5（柵の側は柵まで）
line([PK(_bx[0], _br["y"]), PK(_bx[-1], _br["y"])], lw=0.9, c="#333333", z=7)
for _x in _bx: post(PK(_x, _br["y"]), 0.12)
T(PK((_bx[0] + _bx[-1]) / 2, _br["y"] + 0.6), "鉄棒h0.9・1.1・1.3", 3.8, c="#333333", rot=PK_ROT)
# すべり台：真南（3dm の −y）へ滑り降りる。SLD(a, s)＝p0 から真南へ a、東へ s（3dm の xy）
_sl = PP["slide"]; _p0 = np.array(PK(*_sl["p0"]))
def SLD(a, s): return (float(_p0[0] + s), float(_p0[1] - a))
def SLR(a0, a1, w): return [SLD(a0, -w / 2), SLD(a1, -w / 2), SLD(a1, w / 2), SLD(a0, w / 2)]
SLIDE_FOOT = SP(SLR(0, _sl["landing"][1], _sl["w_deck"])); SLIDE_CLR = SP(SLR(_sl["landing"][1], _sl["landing"][1] + _sl["clear"], _sl["w_deck"]))
poly(SLR(*_sl["chute"], _sl["w"]), fc="#E8EAEC", ec="#555555", lw=0.4, z=6)
poly(SLR(*_sl["landing"], _sl["w"]), fc="#F2F3F4", ec="#888888", lw=0.3, z=6)
poly(SLR(*_sl["deck"], _sl["w_deck"]), fc="#D0D3D6", ec="#555555", lw=0.4, z=6)
poly(SLR(*_sl["ladder"], _sl["w"]), fc="white", ec="#555555", lw=0.35, z=6)
for _a in np.arange(_sl["ladder"][0] + 0.12, _sl["ladder"][1], 0.12): line([SLD(_a, -_sl["w"] / 2), SLD(_a, _sl["w"] / 2)], lw=0.25, c="#555555", z=6.1)
poly(SLIDE_CLR, fc="none", ec="#999999", lw=0.25, ls=(0, (1, 1.2)), z=1.4)                   # 降り口の先1.5
T(SLD(2.5, 0.85), "すべり台（真南へ）", 3.8, c="#333333", rot=90)
for _b in PP["benches"]["list"]: poly(PKR(*_b["x"], *_b["y"]), fc=C["wood"], ec="none", z=6.8)   # 木のベンチ（キンモクセイの間、塀ぎわ）
_km = PP["kinmokusei"]
for _y in _km["y"]:
    ax.add_patch(Circle(PK(_km["x"], _y), _km["r"], fc="#E9D9A0", ec="#9a7a2a", lw=0.5, zorder=6.5, alpha=0.9))   # キンモクセイ（秋の橙の花）
    ax.add_patch(Circle(PK(_km["x"], _y), 0.08, fc="#6b5a3a", ec="none", zorder=6.6))
T(PK(8.0, 6.3), "公園（芝生、12×12 m）", 5.4, c=C["green"], rot=PK_ROT)        # 公園の真ん中の木は無い（ユーザー 10-24）
kid = SP(SITE).difference(SP(PARK)).intersection(SP(rect(-14, 40, 1.6, 40))).difference(SP(rect(0, 40, 0, 15)))
poly(kid, fc=C["kid"], ec="none", z=1)
line([W(0, 1.6), W(MN.D["FENCE_END_U"], 1.45), FENCE_END], lw=1.1, c="#6b5a3a", z=6)   # infant-garden fence h1.2
# みなみのさんかくの中身（data/minami.json、minami01.py のたたき台を 1/200 で）
def _mw(g): return SP([W(y, x) for x, y in g.exterior.coords])
for _n, _g in MN.loop_parts(): poly(_mw(_g), fc="#D8C3A0", ec="#9a8060", lw=0.2, z=2.2)
poly(_mw(MN.GRASS_RIVER), fc="#B4D38E", ec="none", z=2.15)               # 避難の帯の芝の川（刈り分け）
poly(_mw(MN.MOUND), fc="#C9DDA8", ec="#6a8a4a", lw=0.3, z=2.3)
poly(_mw(MN.SAND), fc="#EADBB0", ec="#8a7040", lw=0.4, z=2.3)
poly(_mw(MN.HERB), fc="#A9C98A", ec="none", z=2.3)
poly(_mw(MN.WATER), fc="#9CC9E6", ec="#3d7fb0", lw=0.4, z=2.3)
tree(W(*MN.D["TREE"]["c"]), MN.D["TREE"]["r"])
line([W(y, x) for x, y in MN.SCREEN.coords], lw=1.6, c="#5f8a4a", z=6.2)   # 川の柵の緑の目隠し h1.5（ムベ・アケビ）
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
poly(srect(12.3, 17.6, *BUMP), fc="#8E8E8A", ec="#555555", lw=0.4, z=3.2)          # 横断歩道の縞（ユーザー 10-29）：白い帯0.45・あき0.45、帯は車の向き
BUMP_STRIPES = [12.3 + (5.3 - 0.45 * 11) / 2 + 0.9 * k for k in range(6)]
for s in BUMP_STRIPES:
    poly(srect(s, s + 0.45, *BUMP), fc="#F4F4F2", ec="none", z=3.3)
T(P(14.95, 5.0), "車路 5.5", 5.2, c="#777777", rot=ROT)
# planting strip along the road in front of the stalls / delivery path
# 職員の駐輪の前（s22.7〜30.0）も歩道（ユーザー 10-29：ほかの歩道と同じ色で）。前の植栽帯はやめた
# 敷地の境から 1.0 を歩道として開放（公園の上の端〜食材納品場、ユーザー 10-25）
poly(srect(SIDEWALK["s"][0], SIDEWALK["s"][1], *SIDEWALK["d"]), fc=C["arai"], ec="#999999", lw=0.3, z=3.0)
line(Q([(SIDEWALK["s"][0], SIDEWALK["d"][1]), (SIDEWALK["s"][1], SIDEWALK["d"][1])]), lw=0.3, c="#999999", ls=(0, (2, 1.5)), z=3.05)
T(P(4.0, 0.5), "歩道（開放）1.0", 4.4, c="#555555", rot=ROT + 90)
# visitors' walk: aisle -> along the hedge (outside) -> park gate
poly(srect(*VWALK), fc=C["arai"], ec="none", z=2.2)
# bikes in the south triangle: row 1 straight off the road, row 2 off a short aisle; 0.7 pitch (child-seat bikes)
poly(SP(Q([(0.0, 0.15), (7.15, 0.15), (7.15, 20)])).intersection(SP([P(0, 0), P(*TIP), P(7.15, 20), P(7.15, 0)])).difference(SP(PARK)),
     fc="#ECE8E0", ec="none", z=2)
BIKES = []
for s0 in [x for grp in BIKE_ROW1["s"] for x in grp]:            # row 1 behind the sidewalk (gap = aisle to row 2)
    BIKES.append(("d", s0, BIKE_ROW1["d0"]))
for k in range(BIKE_ROW2["n"]):                                   # row 2: along s, side by side in d（0.65、前輪を互い違い）
    BIKES.append(("s", BIKE_ROW2["s0"], BIKE_ROW2["d0"] + BIKE_ROW2["pitch"] * k))
for kind, a, b in BIKES:
    if kind == "d":
        line(Q([(a + 0.35, b), (a + 0.35, b + 1.85)]), lw=1.0, c="#6b5a3a", z=3.6)
        line(Q([(a + 0.12, b + 0.9), (a + 0.58, b + 0.9)]), lw=0.4, c="#6b5a3a", z=3.6)
    else:
        line(Q([(a, b + 0.35), (a + 1.85, b + 0.35)]), lw=1.0, c="#6b5a3a", z=3.6)
        line(Q([(a + 0.95, b + 0.12), (a + 0.95, b + 0.58)]), lw=0.4, c="#6b5a3a", z=3.6)
N_BIKE = len(BIKES)
# staff bikes in the pocket off the delivery path (outside the line), staggered high/low racks at 0.5
_sb = STAFF_BIKE; _pk = _sb["pocket"]
POCKET = SP(srect(*_pk)).difference(WB)
_dl = SL(Q([(_pk[0], _pk[3]), (_pk[1], _pk[3])])).intersection(WB.exterior)
_dl = min(getattr(_dl, "geoms", [_dl]), key=lambda q: q.distance(SPt(P(_pk[0], _pk[3]))))
SX = inv((_dl.x, _dl.y))[0]                                        # the east fence of the pocket meets the west building here
_lean_s = inv(W(LEAN_UV[0] + 0.25, -9.7))[0]                     # west post of the lean-to stands in the pocket
STAFF_POS = [x for x in np.arange(_sb["bikes"][0], _sb["bikes"][1] + 0.01, _sb["pitch"]) if abs(x - _lean_s) > 0.28 and P(x, STAFF_BIKE["pocket"][2] + 1.0) and not WB.intersects(SL(Q([(x, STAFF_BIKE["pocket"][2]), (x, STAFF_BIKE["pocket"][2] + 1.95)])).buffer(0.23))]
poly(POCKET, fc="#ECE8E0", ec="none", z=2.35)
STAFF_N = 0
for _k, _s in enumerate(STAFF_POS):
    _d0 = _pk[2] + (0.05 if _k % 2 == 0 else 0.2)
    line(Q([(_s, _d0), (_s, _d0 + 1.75)]), lw=1.0, c="#6b5a3a", z=3.6)
    line(Q([(_s - 0.22, _d0 + 0.85), (_s + 0.22, _d0 + 0.85)]), lw=0.4, c="#6b5a3a", z=3.6)
    STAFF_N += 1
T(P(25.0, 2.1), "職員の自転車", 4.2, c="#555555", rot=ROT + 90)
T(P(23.3, 6.15), "通用口", 4.2, c="#555555", rot=ROT)

# ---------------------------------------------------------------- security line: hedges, fences, lattice, gate
def band(pts, w, fc, ec, z=7):
    g = SL(Q(pts)).buffer(w, cap_style=2, join_style=2)
    poly(g, fc=fc, ec=ec, lw=0.4, z=z)
SB = STAFF_BIKE; PS0, PS1, PD0, PD = SB["pocket"]; G0, G1 = SB["gate"]
HEDGE = [[(22.7, PD), (22.7, NHEDGE_D), (17.7, NHEDGE_D), (17.7, HEDGE_D), (S_PATH0, HEDGE_D)]]
for h in HEDGE:
    band(h, HW, C["hedge"], C["green"])
    line(Q(h), lw=0.35, c="#3f5a2a", ls=(0, (1.2, 1.2)), z=7.2)
    g = SL(Q(h))
    for t in np.arange(0.3, g.length, 0.7):
        q = g.interpolate(t); ax.add_patch(Circle((q.x, q.y), 0.22, fc="none", ec=C["green"], lw=0.3, zorder=7.1))
line([P(S_PATH0, HEDGE_D), P(*TIP)], lw=1.0, c=C["green"], z=7)
# board fence h1.8 on the road side of the plaza
fence = SL(Q([(25.0, FENCE_D), (32.0, FENCE_D)]))
fx = fence.intersection(WB.exterior)
fx = min(getattr(fx, "geoms", [fx]), key=lambda q: q.distance(SPt(P(25.0, FENCE_D))))
FENCE_S1 = inv((fx.x, fx.y))[0]
import yamato                                                          # 塀はすべてスギの大和張り（ユーザー 10-27）
yamato.plan(line, P(22.7, PD), P(G0, PD), C["wood"])                   # 職員の駐輪の東の塀（ひろばの道路側）、建物まで
yamato.plan(line, P(G1, PD), P(SX, PD), C["wood"])
line([P(G0, PD), P(G0, PD + (G1 - G0))], lw=0.4, c="#555555", z=7.6)    # staff gate leaf (opens into the plaza)
ax.add_patch(Circle(P((G0 + G1) / 2, PD), 0.16, fc="#555555", ec="white", lw=0.4, zorder=14))
# park gate (kido) 1.2 wide just SE of the park tip; lattice h1.8 from the gate to the infant fence
GA0, GA1 = 0.3, 1.5
yamato.plan(line, E(0, 0), E(GA0, 0), C["wood"])
lat_end = np.array(inv(FENCE_END)); La = float((lat_end - TIP) @ EE)
yamato.plan(line, E(GA1, 0), FENCE_END, C["wood"])                    # 公園側の塀＝スギの大和張り（外壁と同じ、ユーザー 10-27）
ax.add_patch(Arc(E(GA0, 0), 2.4, 2.4, angle=math.degrees(math.atan2(*(np.array(E(1, 0)) - np.array(E(0, 0)))[::-1])),
                 theta1=0, theta2=90, lw=0.35, color="#555555", zorder=7.6))
LINE = Q([(SX, PD), (22.7, PD), (22.7, NHEDGE_D), (17.7, NHEDGE_D), (17.7, HEDGE_D), (S_PATH0, HEDGE_D), tuple(TIP)]) + [FENCE_END]
line(LINE, lw=0.5, c=C["red"], ls=(0, (6, 2)), z=13)
ax.add_patch(Circle(E((GA0 + GA1) / 2, 0), 0.32, fc=C["red"], ec="white", lw=0.5, zorder=14))

# ---------------------------------------------------------------- kido roof + porch
# 木戸の屋根は無し（ユーザー 10-24）。木戸の内側の三角と南の軒の下の待ち受け（0〜2歳の受け取りの前）を、見送りの小径のムベの棚の続きで覆う
def _lat(s):                                                          # 公園との格子の線（E(a, 0)）の上で s の点
    a = (s - TIP[0]) / EE[0]; q = np.array(TIP) + EE * a; return float(q[0]), float(q[1])
_PGD = HEDGE_D + HW + 0.15; _sa = inv(W(0.75, 0))[0]
EAVE_S = SP([W(0, -1.0), W(0, 15), W(-1.8, 15), W(-4.2, -1.0)])        # 南の軒（ポーチ）
# 覆う範囲（ユーザー 10-24：待ち受けも含めてムベで。南側なので育つ、育たない所は上に屋根がある）＝木戸の内側の三角＋南の軒の下のポーチ
_sw = inv(W(-0.1, -0.35)); _eN = W(-0.1, 1.62); _gab = inv(_eN)          # 本館の南西の角、東の縁＝一本の線の柵（v1.6）の上（柵の柱が桁を受ける）
_fe = inv(FENCE_END)
TRI = SP(Q([tuple(TIP), (S_PATH0, HEDGE_D + HW), (_sa, _PGD), (_sa, WALL_D), _sw, _gab, (_fe[0], _fe[1])]))
TRI = TRI.difference(SP(rect(-0.1, 57.34, -0.35, 13.5, 48)))
TRI = max(getattr(TRI, "geoms", [TRI]), key=lambda q: q.area)
poly(TRI, fc="#EFE8DA", ec="none", z=2.4)
_e0 = W(-0.1, -1.05); _ec = W(-4.25, -1.05)                           # 軒の縁の桁（ポーチの西の縁、ベビーカーの外）
TRI_END = FENCE_END
# 軒の縁の桁の北の端は柱を立てず、本館の南西の角の柱に金物で留めた梁で受ける（ユーザー 10-27：小径の口の柱をやめる。小径の棚が梁を本館の壁へ留めるのと同じ構成）
_wb = SL([W(-0.1, -0.35), W(-0.1, -6.0)]).intersection(SL([P(_sa, _PGD), P(*TIP)]))
_wb = (_wb.x, _wb.y) if not _wb.is_empty else P(*TIP)
TRI_WALLBEAM = [W(-0.1, -0.35), _wb]                                   # 本館の角の柱 → 小径の続きの桁（その上を軒の縁の桁の北の端が受ける）
TRI_GIRDERS = [[P(_sa, _PGD), P(*TIP)], [P(*TIP), FENCE_END], [_e0, _ec], [_eN, FENCE_END], TRI_WALLBEAM]   # 桁：小径の続き・格子の線・軒の縁・東の縁（一本の線の柵の上、腰掛けを避けて柱）
TRI_BEAMS = []
for sb in (_sa - 1.5, _sa - 3.0, _sa - 4.5, _sa - 6.0, _sa - 7.5):     # 梁は 1.5 ごと（小径と同じ）、格子から東の縁まで
    seg = SL([P(*_lat(sb)), P(sb, 18.0)]).intersection(TRI.buffer(0.06))
    seg = max(getattr(seg, "geoms", [seg]), key=lambda q: q.length) if not seg.is_empty else seg
    if not seg.is_empty and seg.length > 0.6: TRI_BEAMS.append((seg.coords[0], seg.coords[-1]))
_east = SL([_eN, FENCE_END])
TRI_POSTS = [P(*TIP), _ec, SL([_e0, _ec]).interpolate(0.5, normalized=True).coords[0]] \
    + [_east.interpolate(_east.project(SPt(P(sx, 15.1)))).coords[0] for sx in (3.6, 1.2)] \
    + [b0 for b0, _ in TRI_BEAMS if SPt(b0).distance(SPt(P(*TIP))) > 0.5]          # 西の門の柱（FENCE_END）は門の柱が受ける
for g in TRI_GIRDERS: line(g, lw=0.6, c=C["wood"], ls=(0, (3, 1.5)), z=10.5)           # 頭上（h2.25）なので破線
for b0, b1 in TRI_BEAMS: line([b0, b1], lw=0.4, c=C["wood"], ls=(0, (2, 1.5)), z=10.5)
for p in TRI_POSTS:
    post(p, 0.14); ax.add_patch(Circle(p, 0.35, fc="#9DBE7A", ec="none", zorder=10.4, alpha=0.8))      # ムベを柱の足もとに
for q in [TRI.representative_point()] + [SPt(TRI.centroid.x + dx, TRI.centroid.y + dy) for dx, dy in ((1.2, -0.6), (-1.0, 0.8), (0.3, 1.4))]:
    if TRI.contains(q): ax.add_patch(Circle((q.x, q.y), 0.6, fc="#9DBE7A", ec="none", zorder=10.3, alpha=0.28))
poly([W(0, -1.0), W(0, 1.6), W(-4.0, 1.6), W(-4.2, -1.0)], fc="#EFE8DA", ec="none", z=2.4)
_st = PORCH["strollers"]; _bn = PORCH["bench"]                       # ベビーカーは柵ぎわの軒の下、腰掛けは公園側の塀ぎわ（10-27）
for k in range(_st["n"]):
    u1 = _st["u0"] - _st["pitch"] * k; u0 = u1 - _st["w"]
    poly(rect(u0, u1, _st["v"][0], _st["v"][1], 2), fc="white", ec="#777777", lw=0.35, z=5)
    ax.add_patch(Circle(W((u0 + u1) / 2, _st["v"][0] + 0.25), 0.08, fc="#777777", ec="none", zorder=5.1))
poly([E(_bn["a"][0], _bn["b"][0]), E(_bn["a"][1], _bn["b"][0]), E(_bn["a"][1], _bn["b"][1]), E(_bn["a"][0], _bn["b"][1])], fc=C["wood"], ec="none", z=5)

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
    line([P(s_a, PG_D), P(s_b, PG_D)], lw=0.6, c=C["wood"], ls=(0, (3, 1.5)), z=10.5)   # 桁 on the posts（頭上なので破線）
    for s in np.arange(s_a, s_b + 0.01, (s_b - s_a) / round((s_b - s_a) / 1.5)):
        line([P(s, PG_D), P(s, WALL_D)], lw=0.4, c=C["wood"], ls=(0, (2, 1.5)), z=10.5)   # arched beams (plan, overhead)
    for s in [s_a] + s_fr[1:] + [s_b]:
        post(P(s, PG_D), 0.14)
        ax.add_patch(Circle(P(s, PG_D - 0.05), 0.35, fc="#9DBE7A", ec="none", zorder=10.4, alpha=0.8))   # ムベ at the post foot
    for s in np.arange(s_a + 0.4, s_b, 0.8):                                            # foliage on top (light)
        ax.add_patch(Circle(P(s, (PG_D + WALL_D) / 2 + 0.3 * math.sin(s * 2.1)), 0.55, fc="#9DBE7A", ec="none", zorder=10.3, alpha=0.28))

# ---------------------------------------------------------------- plaza
plz = clipWB(SP(Q([(22.7, PD), (SX + 0.6, PD), (31.0, WALL_D + 0.3), (17.7, WALL_D + 0.3), (17.7, NHEDGE_D), (22.7, NHEDGE_D)])))
poly(plz, fc=C["plaza"], ec="none", z=2.2)
sband(17.7, 29.5, HEDGE_D + HW, WALL_D + 0.3, C["arai"], z=2.3)
T(P(23.2, 8.6), "ひろば", 8, c="#8a5a2b", rot=ROT, weight="bold")

# temizu (no roof, user 10-30): stone basin + bamboo spout, open to the sky after the trellis
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
for b, (crop, _) in zip(BEDS, _D["BED_CROPS"]["beds"]):   # 行事の作物（園庭の依頼 10-25）
    T(P((b[0] + b[1]) / 2, (b[2] + b[3]) / 2), crop, 4.2, c="#3f5a2a", rot=ROT, bbox=dict(fc="#EEF3E2", ec="none", pad=0.6, alpha=0.9))

# tea engawa under a lean-to off the kitchen south wall: 縁台 ×2, tea shelf with tap (kitchen plumbing nearby)
u0, u1, v0, v1 = LEAN_UV
poly(rect(u0, u1, v0, v1), fc="#E7D6BB", ec="none", z=2.4)
_HK = SP(rect(-0.1, 57.34, -0.35, 13.5, 96)).buffer(0.005)                              # 本館の外壁の外面（v −0.35）で止める
_LX = LEAN_EXT
_band = WB.buffer(_LX["depth"], resolution=32).difference(WB).intersection(SP(SITE).buffer(-_LX["margin"])).intersection(SP(srect(26.0, _LX["cut_s"], -1, 3.7)))
_band = max(getattr(_band, "geoms", [_band]), key=lambda q: q.area)
LEAN_ROOF = SP(rect(u0, u1, v0, v1)).difference(_HK).difference(WB).union(_band).buffer(0.01).buffer(-0.01)   # 下屋＋南西の丸みへの回り込み
roof(list(LEAN_ROOF.exterior.coords))
LEAN_GUTTER = LEAN_ROOF.exterior.difference(WB.buffer(0.05)).difference(_HK.buffer(0.05))
for _g in getattr(LEAN_GUTTER, "geoms", [LEAN_GUTTER]): line(list(_g.coords), lw=0.5, c="#3d7fb0", ls=(0, (1, 1)), z=10.5)
ax.add_patch(Circle(P(*_LX["rain_head"]), 0.1, fc="#3d7fb0", ec="none", zorder=10.6))
LEAN_POSTS = [W(u0 + 0.25, v) for v in (-9.7, -6.4, -3.1, -0.5)] + [P(*_LX["post"])]   # 東の柱は本館の外壁の外（前は v −0.3 で壁とガラスに入っていた）
for p in LEAN_POSTS: post(p)
# 西館の西の軒の雨（南の端）：樋 → 下屋の南の縁の鎖樋 → 石の受け桝 → ひろばの下の地中の雨水槽 → 菜園の脇の手押しポンプ（10-25）
_tk = RAIN["S_TANK"]; _in = RAIN["S_INLET"]; _pm = RAIN["S_PUMP"]
poly(srect(_tk["s"][0], _tk["s"][1], *_tk["d"]), fc="none", ec="#3d7fb0", lw=0.6, ls=(0, (2.5, 1.5)), z=8)      # 地中（破線）
ax.add_patch(Circle(P(_in[0], _in[1]), _in[2], fc="#BFD9EA", ec="#3d7fb0", lw=0.6, zorder=8.2))
ax.add_patch(Circle(P(*RAIN["S_CHAIN"]), 0.08, fc="#3d7fb0", ec="none", zorder=8.3))
line([P(_tk["s"][0], (_tk["d"][0] + _tk["d"][1]) / 2), P(_pm[0], _tk["d"][1] - 0.2), P(*_pm)], lw=0.5, c="#3d7fb0", ls=(0, (1, 1)), z=8)
ax.add_patch(Rectangle((P(*_pm)[0] - 0.14, P(*_pm)[1] - 0.14), 0.28, 0.28, fc="#3d7fb0", ec="none", zorder=8.4))
T(P(_tk["s"][0] - 0.35, (_tk["d"][0] + _tk["d"][1]) / 2 + 0.3), "地中の雨水槽 約%dm³" % round(_tk["vol_m3"]), 4.2, c="#2a5f8a", rot=ROT)
T(P(_pm[0], _pm[1] + 0.3), "手押しポンプ", 4.2, c="#2a5f8a", rot=ROT, ha="left")
for (va, vb) in TEA["benches_v"]:
    poly(rect(19.6, 20.5, va, vb, 2), fc="#B98E5E", ec=C["wood"], lw=0.4, z=9)             # 縁台 0.9 x 1.8
poly(rect(19.3, 20.8, *TEA["shelf_v"], 2), fc="#8a6a44", ec="none", z=9)                     # tea shelf
ax.add_patch(Circle(W(20.55, sum(TEA["shelf_v"]) / 2), 0.09, fc=C["blue"], ec="none", zorder=9.2))

# kamado (events): masonry 1.0 x 1.0, earth apron, wood rack on the board fence
s0, s1, d0, d1 = KAM
ax.add_patch(Circle(P((s0 + s1) / 2, (d0 + d1) / 2), 1.3, fc="#E3D3B8", ec="none", zorder=2.5))
poly(srect(s0, s1, d0, d1), fc="#C9A97A", ec="#6b4b2a", lw=0.6, z=8)
for dd in (d0 + 0.25, d0 + 0.75):
    ax.add_patch(Circle(P(s1 - 0.3, dd), 0.15, fc="#4a3826", ec="none", zorder=8.1))
poly(srect(*WOOD), fc="#a07a4c", ec=C["wood"], lw=0.3, z=8)   # 薪棚 on the plaza side of the pocket fence, next to the kamado
for s in np.arange(WOOD[0] + 0.15, WOOD[1], 0.3):
    ax.add_patch(Circle(P(s, (WOOD[2] + WOOD[3]) / 2), 0.1, fc="none", ec="#5a3f22", lw=0.3, zorder=8.1))

# the tree at the inlet (deciduous)
tree(P(24.4, 9.6), 1.9)

# ---------------------------------------------------------------- delivery path (outside the line), kitchen back door + small roof
poly(srect(*DEL), fc="#E6E6E3", ec="none", z=2.3)
door = [W(21.06, -10.49), W(21.38, -11.41)]                           # 勝手口（plan05・3dm、外開き）
line(door, lw=2.4, c="white", z=6); line(door, lw=0.9, c="#555555", z=6.1)
T(P(27.4, 2.1), "搬入路 1.6", 4.6, c="#555555", rot=ROT + 90)

# ---------------------------------------------------------------- walking lines (light)
WALKS = []
def walk(pts, c=C["path"], lw=0.9):
    line(pts, lw=lw, c=c, ls=(0, (3, 2)), z=15)
    WALKS.append([tuple(map(float, q)) for q in pts])
walk([E(0.9, -1.6), E(0.9, 1.0), P(8.0, 11.6), P(17.0, 11.7), P(19.35, 12.3), P(25.0, 12.9), W(20.6, -1.85), W(21.3, -1.85)])
walk([E(0.9, 1.0), W(-0.6, -0.4), W(-0.6, 0.8), W(0.0, 0.8)], c="#b08a5b", lw=0.7)
walk([P(15.0, 3.0), P(12.6, 9.45), P(7.4, 9.45), E(0.9, -1.0)], c="#b08a5b", lw=0.7)          # visitors from the car
walk([P(4.3, 1.0), P(4.3, 6.0), E(1.4, -2.2), E(0.9, -1.6)], c="#b08a5b", lw=0.7)            # from the bikes

# ---------------------------------------------------------------- numbers
N = [(E(0.9, -2.6), 1), (W(-2.2, -0.3), 2), (PK(10.6, 3.5), 3), (W(3.0, 3.0), 4), (P(9.6, 11.7), 5), (W(7.5, 1.0), 6),
     (P(21.6, 11.7), 7), (P(20.0, 5.6), 8), (W(20.1, -10.9), 9), (P(25.0, 8.1), 10), (P(24.4, 9.6), 11),
     (W(19.6, -2.0), 12), (W(19.4, -3.95), 13), (W(19.6, -7.0), 14), (P(31.2, 0.2), 15), (P(14.95, -1.4), 16),
     (P(10.0, 9.45), 17), (P(3.6, -1.2), 18), (P(26.2, 0.6), 19),
     (PK(9.0, 4.6), "P1"), (PK(-1.0, 6.0), "P3"), (PK(4.6, 1.2), "P4"), (PK(5.24, 10.55), "P5"), (PK(9.6, 8.6), "P6")]
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
fig.text(PL / 297, 410 / 420, "育ち舎　外構の図（南半分）　アプローチ A 案", fontsize=13, weight="medium", va="top")
fig.text(PL / 297, 402 / 420, "1/200（A3）　2026-10-23　駐車は南、ひろばは北。公園 → 木戸 → ポーチ（0〜2歳）／見送りの小径 → 手水 → ひろば → 海峡の口（3〜5歳）。",
         fontsize=6.6, va="top", color="#444444")
fig.text(PL / 297, 396.5 / 420, "破線＝頭上の屋根・軒・キャップ・ムベの棚の桁と梁　■＝柱　赤い破線＝セキュリティの線（内側は保護者の領域）　● 赤＝線の出入口（公園の木戸）　┅ 道すじ",
         fontsize=6.0, va="top", color="#666666")
legend = [
    ("1", "公園の木戸。線の出入口はここだけ。入るとムベの棚の下"),
    ("2", "待ち受け（軒の下）：ベビーカー5台は柵ぎわ、腰掛けは公園側の塀ぎわ、真ん中は空ける"),
    ("3", "公園側の塀 h1.8：スギの大和張り（外壁と同じ、視線よけ・風は抜ける）"),
    ("4", "受け取り土間（ベビーカーのまま入れる）"),
    ("5", "見送りの小径 2.4：アーチの棚（ムベ）。木戸の内側と待ち受けまで覆う"),
    ("6", "0・1歳の覗き窓（子どもの目の高さ）"),
    ("7", "手水（石の鉢と筧、屋根は無し）"),
    ("8", "菜園（畝×3）：大豆・カブとダイコン・サツマイモ"),
    ("9", "お茶の縁台（西館の南の下屋の下）"),
    ("10", "かまど（行事のとき）と薪棚"),
    ("11", "入江の木（落葉樹）"),
    ("12", "西館の南の入口→海峡（3〜5歳はここでバイバイ）"),
    ("13", "「今日のごはん」の窓（入口の脇）"),
    ("14", "キッチンの南のガラス"),
    ("15", "勝手口（回り込む下屋の下）、搬入路 1.6（線の外）"),
    ("16", "駐車5台・乗入れ1か所・スピードバンプ（歩道を続ける）"),
    ("17", "来客の歩道 1.1（車から公園の木戸へ）"),
    ("18", "駐輪 %d台（子乗せ 0.7・0.65 ピッチ）" % N_BIKE),
    ("19", "大和張りの塀 h1.8（道路側、西日と視線よけ、外壁と同じスギ）"),
    ("P1", "公園：全面を芝生（真ん中に木は置かない）"),
    ("P3", "道路側の鉄柵h1.1（現況）、辺の真ん中の開口3.0に上げ下げ式の車止め3本"),
    ("P4", "鉄棒h0.9・1.1・1.3（川の柵ぎわ、棒は川と平行、前1.5空ける）"),
    ("P5", "すべり台（現況を残す、真南へ滑り降りる）"),
    ("P6", "キンモクセイ3本、その間に木のベンチ2脚（塀ぎわ）"),
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

notes = ("職員の自転車：大和張りの塀をひろばの西で東へ2.0下げ、建物ぎわまでのポケットに%d台（搬入路から、北の端は下屋の下）。東の塀の南の端に職員の通用口0.9（ひろばへ開く）。縁台と棚は1.6東へ。\n" % STAFF_N + 
         "行事の日の自転車：車での来園は断り、駐車場を駐輪に（車室1つに約6〜8台）。あふれは公園の道路側の角に一時的に（市と相談、園庭への搬入の道と非常用の門の前は空ける）。\n"
         "西館の西の軒の雨：南の端は鎖樋から石の受け桝を通ってひろばの下の地中の雨水槽（約2m³）へ、菜園の脇の手押しポンプで汲んで子どもが水やり（あふれは浸透桝）、北の端は鎖樋で道路側の雨庭（浸透、約4.1×0.7）へ。\n"
         "見送りの小径：生垣 h1.2（常緑、中にメッシュ柵 h1.2）／下草 0.3／洗い出し 1.9（平ら、ベビーカー可）／砂利 0.2（壁の足もとの跳ね返り止め。屋根と越屋根の蓋は東へ流れる）。\n"
         "アーチの棚（ムベ）：生垣の側に柱（本館の架構に合わせて 3 m ごと）、梁は 1.5 m ごとに本館の壁へ。木戸の内側の三角と南の軒の下の待ち受け（0〜2歳の受け取りの前）も同じ棚で覆う（公園側の塀・軒の縁・東の柵の手前に桁、木戸の屋根は無し。軒の下で育たない所は屋根が覆う）。木戸 → 棚 → 手水（空の下）→ ひろば（ひらける）。\n"
         "歩道：西の道路沿いの敷地の境から 1.0 を、公園の上の端から食材納品場まで歩道として開放（洗い出し）。車路の前はスピードバンプ（長さ 1.0＝歩道の幅、台形 h約0.05）が歩道を続け、車室の口はその奥（道路から 1.3 m 以上）。駐輪は歩道にはみ出さない。来客の門はなし、来客も公園の木戸から。\n"
         "ひろば（線の内側、真砂土）約 %d m²。菜園は南の日なた（大豆・カブ・ダイコン・サツマイモ、冬は葉もの）、縁台は西館の南の下屋（入口の前まで一続き）の下。かまどは下屋から約 2 m、建物から 4 m 以上（行事のときだけ）。\n"
         "搬入は線の外：搬入の車室の後ろから搬入路（幅1.6、約7 m）を手押しで勝手口へ。西館の南の下屋を南西の丸みへ回り込ませ（外皮から2.0、敷地の境の0.1手前まで）、勝手口と搬入路の終わりを覆う。西館の南の鎖樋は下屋の上の集水で受け、下屋の軒樋で南の縁の鎖樋から地中の雨水槽へ。\n"
         "公園（全面を芝生）：園庭への搬入の車は道路側の辺の真ん中の開口（3.0、ふだんは上げ下げ式の車止め）から、芝の下の保護材（幅2.5、図には描かない）のS字（中心の半径約{BR}、内側約{BRI}）で非常用の門へ。鉄棒は川の柵ぎわ、北西の角は行事の日の自転車のあふれに空ける。砂場は撤去。")
notes = notes.replace("{BR}", "%.1f" % BAND_R).replace("{BRI}", "%.1f" % BAND_R_IN)
plaza_area = plz.area
fig.text(PL / 297, 108 / 420, notes % round(plaza_area), fontsize=6.1, va="top", color="#333333", linespacing=1.45)

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

# ---------------------------------------------------------------- 配置図 1/200（更新係が 3dm から描く）に描く中身（設計監修 10-25：中身はアプローチ係が決めて渡す）
# 座標は 3dm の xy（m、取り込み用ファイルと同じ）。書き出し：data/siteplan_approach.json
import siteplan_spec
siteplan_spec.write(globals())
