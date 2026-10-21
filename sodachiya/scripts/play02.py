# 遊戯室のひだ（西の壁のくぼみ）と北の窓辺の腰掛け 1/30：室内から見た立面・断面
# 寸法は data/play.json。担当：遊戯室のスレッド。
import os, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Ellipse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
D = json.load(open(os.path.join(ROOT, "data", "play.json"), encoding="utf-8"))
N, NW, CW = D["niche"], D["north_window"], D["catwalk"]

MM = 1 / 25.4; S = 1000 / 30 / 10          # 1/30 → 1 m = 33.3 mm ; axes units in m, figure in mm → factor
fig = plt.figure(figsize=(420 * MM, 297 * MM))
def axes(x0, y0, xr, zr):
    a = fig.add_axes([x0 / 420, y0 / 297, (xr[1] - xr[0]) * 33.33 / 420, (zr[1] - zr[0]) * 33.33 / 297])
    a.set_xlim(*xr); a.set_ylim(*zr); a.set_aspect("equal"); a.axis("off"); return a
def P(a, pts, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1):
    a.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
def R(a, x0, x1, z0, z1, **k): P(a, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], **k)
def L(a, pts, lw=0.5, c="black", ls="-", z=5): a.plot([p[0] for p in pts], [p[1] for p in pts], lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(a, x, y, s, size=6.5, c="#222222", ha="center", va="center", **kw): a.text(x, y, s, fontsize=size, color=c, ha=ha, va=va, zorder=12, **kw)
WOOD, WOOD2, GLASS, DARK = "#E3CDA6", "#5a4026", "#3d7fb0", "#333333"
def kid_sit(a, x, z0, facing=1, h=1.05):
    hd = h * 0.12; hip = (x, z0 + 0.06)
    a.add_patch(Circle((x + 0.03 * facing, z0 + 0.62), hd, fc="white", ec="#555555", lw=0.6, zorder=10))
    L(a, [(x, z0 + 0.5), hip], 0.8, "#555555", z=10)
    L(a, [hip, (x + 0.3 * facing, z0 + 0.06), (x + 0.32 * facing, z0 - 0.25)], 0.8, "#555555", z=10)
    L(a, [(x, z0 + 0.42), (x + 0.22 * facing, z0 + 0.3)], 0.8, "#555555", z=10)
def kid(a, x, z0, h=1.05, c="#555555"):
    hd = h * 0.13; a.add_patch(Circle((x, z0 + h - hd), hd, fc="white", ec=c, lw=0.6, zorder=10))
    L(a, [(x, z0 + h - 2 * hd), (x, z0 + h * 0.45)], 0.8, c, z=10)
    L(a, [(x - 0.12, z0), (x, z0 + h * 0.45), (x + 0.12, z0)], 0.8, c, z=10)
    L(a, [(x - 0.15, z0 + h * 0.62), (x, z0 + h * 0.72), (x + 0.15, z0 + h * 0.62)], 0.8, c, z=10)

# ---------------------------------------------------------------- A: elevation from the room (looking west), one bay
a = axes(10, 70, (32.75, 36.45), (-0.45, 4.9))
R(a, 32.75, 36.45, -0.3, -0.12, fc="#C8B48C", ec="none")
R(a, 32.75, 36.45, -0.45, -0.3, fc="#DDD6C8", ec="none", hatch="////")
R(a, 32.75, 36.45, 0, 4.65, fc="#F6EEDC", ec="none", z=0.5)                       # the wall seen from the room
L(a, [(32.75, 4.65), (36.45, 4.65)], 1.4, DARK)
for uc in (33.0, 36.0):                                                             # columns (180 face)
    R(a, uc - 0.09, uc + 0.09, 0, 4.65, fc="#B08A5A", ec=WOOD2, lw=0.5, z=3)
    T(a, uc, 4.78, "柱", 6)
u0, u1 = D["niches"][0]
b = N["board"]
R(a, u0, u1, 0, N["top_h"], fc="#3b3226", ec="none", z=2, alpha=0.18)              # inside of the niche (shade)
R(a, u0 - b, u0, 0, N["top_h"], fc=WOOD, ec=WOOD2, z=4)                              # side boards
R(a, u1, u1 + b, 0, N["top_h"], fc=WOOD, ec=WOOD2, z=4)
R(a, u0 - b, u1 + b, N["top_h"], N["top_h"] + b, fc=WOOD, ec=WOOD2, z=4)             # top board (shelf)
R(a, u0, u1, N["seat_h"] - b, N["seat_h"], fc=WOOD, ec=WOOD2, z=4)                   # seat
R(a, u0 + 0.05, u1 - 0.05, N["seat_h"], N["seat_h"] + 0.06, fc="#C9A0A0", ec="none", z=4.5)   # cushion
R(a, u0, u1, 0, N["seat_h"] - b, fc="#CDBB98", ec=WOOD2, z=3.5, hatch="////")        # drawer / storage under the seat
pk = N["peek"]; pc = (u0 + u1) / 2
R(a, pc - pk[2] / 2, pc + pk[2] / 2, pk[0], pk[1], fc="#CFE0EA", ec=GLASS, lw=0.8, z=3.8)
for x in np.arange(pc - pk[2] / 2 + 0.05, pc + pk[2] / 2, 0.05): L(a, [(x, pk[0]), (x, pk[1])], 0.6, WOOD2, z=3.9)
kid_sit(a, u0 + 0.6, N["seat_h"] + 0.06, 1); kid(a, 35.95 + 0.0, 0, 1.0)
# 地窓 (vent) between the niches, next to the column
R(a, 35.55, 35.85, 0.05, N["jimado_h"], fc="#CFE0EA", ec=GLASS, lw=0.8, z=3.8)
R(a, 36.15, 36.45, 0.05, N["jimado_h"], fc="#CFE0EA", ec=GLASS, lw=0.8, z=3.8)
# display on top (teachers) and dims
for x in (u0 + 0.3, u0 + 0.9, u1 - 0.35): R(a, x - 0.08, x + 0.08, N["top_h"] + b, N["top_h"] + b + 0.18, fc="#EFE2C8", ec=WOOD2, lw=0.4, z=4)
def dim(a, x, z0, z1, s, side=1):
    L(a, [(x, z0), (x, z1)], 0.4, "#666666"); L(a, [(x - 0.04, z0), (x + 0.04, z0)], 0.4, "#666666"); L(a, [(x - 0.04, z1), (x + 0.04, z1)], 0.4, "#666666")
    T(a, x + 0.08 * side, (z0 + z1) / 2, s, 5.6, ha="left" if side > 0 else "right")
dim(a, 32.85, 0, N["seat_h"], "300", 1); dim(a, 32.85, N["seat_h"], N["top_h"], "1100", 1)
T(a, pc, -0.05, "幅 %d（柱と柱のあいだ、架構の間の真ん中）" % round((u1 - u0) * 1000), 5.6, va="top")
T(a, pc, N["top_h"] + 0.45, "天板 h1400：先生の飾り棚（季節のもの・子どもの作品）", 5.8)
T(a, pc, (pk[0] + pk[1]) / 2 + 0.33, "奥に覗き窓（縦格子、座った目の高さ）", 5.6, c=GLASS)
T(a, 36.0, 0.65, "地窓\n（換気）", 5.4, c=GLASS)
T(a, pc, 0.15, "座の下は引き出し", 5.2, c="#5a4026")
T(a, 32.8, 4.95, "A　室内から見た西の壁（スパン 12、西を見る）", 8, ha="left", weight="bold")

# ---------------------------------------------------------------- B: section through the niche (looking north)
b_ = axes(140, 70, (-0.4, 2.1), (-0.45, 4.9))
X = lambda d: d                                                                       # distance from the inner face of the outer wall, + = into the room
R(b_, -0.4, 2.1, -0.3, -0.12, fc="#C8B48C", ec="none"); R(b_, -0.4, 2.1, -0.45, -0.3, fc="#DDD6C8", ec="none", hatch="////")
R(b_, -0.15, 0, 0, 4.65, fc=DARK, ec=DARK, z=3)                                       # outer wall
R(b_, -0.15, 0, pk[0], pk[1], fc="#CFE0EA", ec=GLASS, lw=0.8, z=3.5)
for z_ in np.arange(pk[0] + 0.04, pk[1], 0.08): L(b_, [(0.0, z_), (0.03, z_)], 0.4, WOOD2, z=4)
L(b_, [(-0.4, 4.6), (2.1, 4.65 + 2.1 * 0.26)], 1.6, DARK)                            # roof (rises to the east)
dep = N["depth"]
R(b_, 0, dep, N["top_h"], N["top_h"] + b, fc=WOOD, ec=WOOD2, z=4)                     # top board
R(b_, 0, N["seat_d"], N["seat_h"] - b, N["seat_h"], fc=WOOD, ec=WOOD2, z=4)           # seat
R(b_, 0.03, N["seat_d"] - 0.02, N["seat_h"], N["seat_h"] + 0.06, fc="#C9A0A0", ec="none", z=4.5)
R(b_, 0, N["seat_d"], 0, N["seat_h"] - b, fc="#CDBB98", ec=WOOD2, z=3.5, hatch="////")
P(b_, [(0, 0), (dep, 0), (dep, N["top_h"]), (0, N["top_h"])], fc="none", ec=WOOD2, lw=0.6, ls=(0, (3, 2)), z=3)   # side board beyond
L(b_, [(dep, N["top_h"] - 0.02), (dep, N["top_h"] + b)], 1.0, WOOD2, z=5)
kid_sit(b_, 0.18, N["seat_h"] + 0.06, 1)
kid(b_, 1.55, 0, 1.05)
T(b_, dep / 2, N["top_h"] + 0.22, "天板", 5.6); T(b_, 0.3, N["seat_h"] + 0.88, "", 5.6)
T(b_, dep + 0.05, (N["seat_h"] + N["top_h"]) / 2, "内のり h%d\n（座って頭の上 約 0.2）" % round((N["top_h"] - N["seat_h"]) * 1000), 5.6, ha="left")
T(b_, -0.2, (pk[0] + pk[1]) / 2, "覗き窓", 5.6, c=GLASS, ha="right")
T(b_, dep / 2, -0.05, "奥行き %d" % round(dep * 1000), 5.6, va="top")
T(b_, -0.35, 4.95, "B　くぼみの断面（北を見る）", 8, ha="left", weight="bold")
T(b_, -0.35, 4.75, "左＝外（西の道路、細い道と住宅）", 5.6, ha="left", c="#666666")

# ---------------------------------------------------------------- C: north window seat (looking west), the maple outside
c = axes(228, 70, (-0.3, 5.3), (-0.45, 4.9))
X2 = lambda du: 51.0 - du                                                            # x = distance north of the north wall's inner face … flip so north is on the right
def x_(u): return u - 51.0 + 1.6
R(c, -0.3, 5.3, -0.3, -0.12, fc="#C8B48C", ec="none"); R(c, -0.3, 5.3, -0.45, -0.3, fc="#DDD6C8", ec="none", hatch="////")
R(c, -0.3, 1.6, -0.12, 0.0, fc="#C8B48C", ec="none")
wall0 = 1.6
R(c, wall0, wall0 + 0.15, 0, 4.6, fc=DARK, ec=DARK, z=3)
R(c, wall0, wall0 + 0.15, NW["h0"], NW["h1"], fc="#CFE0EA", ec=GLASS, lw=0.8, z=3.5)
R(c, wall0 - NW["seat_d"], wall0, NW["seat_h"] - b, NW["seat_h"], fc=WOOD, ec=WOOD2, z=4)
R(c, wall0 - NW["seat_d"] + 0.02, wall0 - 0.02, NW["seat_h"], NW["seat_h"] + 0.06, fc="#C9A0A0", ec="none", z=4.5)
R(c, wall0 - NW["seat_d"], wall0, 0, NW["seat_h"] - b, fc="#CDBB98", ec=WOOD2, z=3.5, hatch="////")
# catwalk overhead along the north wall
R(c, wall0 - 0.25 - CW["width"], wall0 - 0.25, CW["h"] - 0.15, CW["h"], fc="#B08A5A", ec=WOOD2, z=4)
L(c, [(wall0 - 0.25 - CW["width"], CW["h"]), (wall0 - 0.25 - CW["width"], CW["h"] + CW["rail"])], 0.6, WOOD2)
T(c, wall0 - 0.7, CW["h"] + 1.3, "キャットウォーク\nh3.0（頭上）", 5.6)
kid_sit(c, wall0 - 0.33, NW["seat_h"] + 0.06, 1)
L(c, [(wall0 - 0.3, NW["seat_h"] + 0.7), (4.3, 1.6)], 0.4, "#B4553A", ls=(0, (2, 2)), z=6)
# outside: moss and the maple (about 3 m north)
R(c, wall0 + 0.15, 5.3, -0.3, -0.26, fc="#9BAA7A", ec="none", z=2)
mx = wall0 + 0.15 + 3.0
L(c, [(mx, -0.3), (mx, 2.0)], 2.6, "#6a3a2a", z=4)
for (dx, dz, w) in [(-0.7, 2.6, 1.3), (0.3, 2.9, 1.2), (0.0, 3.4, 1.5), (-0.3, 2.1, 1.1)]:
    c.add_patch(Ellipse((mx + dx, dz), w, w * 0.6, fc="#E7B9A4", ec="#B4553A", lw=0.4, alpha=0.8, zorder=3))
T(c, mx - 0.4, 4.25, "読書の庭のモミジ\n（苔の上、窓から約 3 m）", 6, c="#8a3a2a")
T(c, wall0 - NW["seat_d"] / 2, -0.05, "腰掛け 奥行き %d、+%d" % (round(NW["seat_d"] * 1000), round(NW["seat_h"] * 1000)), 5.6, va="top")
T(c, wall0 + 0.25, (NW["h0"] + NW["h1"]) / 2, "窓\nh%d〜%d" % (round(NW["h0"] * 1000), round(NW["h1"] * 1000)), 5.6, c=GLASS, ha="left")
T(c, -0.25, 4.95, "C　北の窓辺の腰掛け（遊戯室の北の壁、西を見る）", 8, ha="left", weight="bold")
T(c, -0.25, 4.75, "左＝遊戯室、右＝読書の庭（北）", 5.6, ha="left", c="#666666")

# ---------------------------------------------------------------- titles and notes
fig.text(14 / 420, 280 / 297, "育ち舎　遊戯室のひだ（西の壁のくぼみ）と北の窓辺の腰掛け　たたき台", fontsize=13, weight="bold")
fig.text(14 / 420, 272 / 297, "1/30（A3）　2026-10-21　寸法は data/play.json。図の場所は play01（遊戯室の平面）の 11・14。", fontsize=7, color="#444444")
notes = [
    "くぼみのつくり：西の壁の柱と柱のあいだ（架構の間 約 3.2 m）の真ん中に、スギの板の箱（袖板 2 枚・天板・座）を壁に付けて置く。構造とは関係しない家具（造作）。",
    "子どもは靴を脱いだまま座に上がり、天板の下にもぐる。内のり 1.1 m は座ると頭の上に 20 cm ほど残る高さ（3〜5 歳の座高 約 0.6 m）。",
    "奥の覗き窓は座った目の高さ。外は細い道と住宅なので、縦格子で外から中が見えにくく、中から外の気配がわかる程度にする（本館の覗き窓と同じ語彙）。",
    "くぼみとくぼみのあいだ（柱の両脇）に地窓：換気の窓（通風の「見る窓と換気の窓を交互に」）。天板の上は先生の飾り棚。座の下は引き出し（遊戯室の小物）。",
    "北の窓辺：遊戯室の北の壁（スパン 17 の北の端）に腰掛け +300 と窓 h350〜1200。座ると読書の庭のモミジが正面に見える。本の奥（本館）からも同じ木が見える。",
]
for i, t in enumerate(notes):
    fig.text(14 / 420, (52 - i * 8) / 297, "・" + t, fontsize=6.6, color="#333333")

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, "sodachiya_play_02_hida." + ext), dpi=200 if ext == "png" else None)
print("ok")
