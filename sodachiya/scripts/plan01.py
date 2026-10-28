import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["pdf.fonttype"] = 42   # 文字は文字のまま（Type42、Illustrator で書体を置き換える）
from matplotlib.patches import Polygon, Circle, Ellipse, Arc
from matplotlib import font_manager as fm

plt.rcParams["font.family"] = "Noto Sans CJK JP"

# ---- geometry: u = arc length along west spine (m, from south gable, north +), v = depth eastward from spine
R = 205.0
phi0 = math.radians(186.67)          # radial (outward/west) direction at south gable
phi_mid = phi0 - 6.0 / R
rot = -(phi_mid - math.pi)            # make frame at u=6 horizontal
cr, sr = math.cos(rot), math.sin(rot)
ox, oy = None, None

def raw(u, v):
    p = phi0 - u / R
    r = R - v
    x, y = r * math.cos(p), r * math.sin(p)
    return x * cr - y * sr, x * sr + y * cr

X0, Y0 = raw(0, 0)
def P(u, v):
    x, y = raw(u, v)
    return x - X0, y - Y0

def rect_pts(u0, u1, v0, v1, n=6):
    pts = []
    for i in range(n + 1):
        pts.append(P(u0 + (u1 - u0) * i / n, v0))
    for i in range(n + 1):
        pts.append(P(u1 - (u1 - u0) * i / n, v1))
    return pts

def area(pts):
    s = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2

# ---- page: A3 portrait, 1/100 (1 m = 10 mm)
MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
xmin, xmax = -3.2, 23.2
ymin, ymax = -7.0, 15.6
left_mm, bottom_mm = 20, 165
ax = fig.add_axes([left_mm / 297, bottom_mm / 420, (xmax - xmin) * 10 / 297, (ymax - ymin) * 10 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

LW_WALL, LW_F, LW_T = 1.4, 0.45, 0.3
C_01, C_ROOF, C_WET, C_DOMA, C_OUT = "#E6EFC2", "#F4EBDD", "#D5EBEE", "#E4E1DA", "#EEF3E6"

def fill(u0, u1, v0, v1, color, z=0, ec="none", lw=0, ls="-"):
    ax.add_patch(Polygon(rect_pts(u0, u1, v0, v1), closed=True, fc=color, ec=ec, lw=lw, ls=ls, zorder=z))

def box(u0, u1, v0, v1, lw=LW_F, fc="white", ls="-", z=3, ec="black"):
    ax.add_patch(Polygon(rect_pts(u0, u1, v0, v1), closed=True, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))

def line(pts, lw=LW_F, ls="-", c="black", z=3):
    xs, ys = zip(*[P(u, v) for u, v in pts])
    ax.plot(xs, ys, lw=lw, ls=ls, color=c, zorder=z, solid_capstyle="butt")

_WALLS = []
def wall(u0, u1, v0, v1):
    _WALLS.append((u0, v0, u1, v1)); box(u0, u1, v0, v1, lw=0, fc="#444444", ec="#444444", z=5)

def txt(u, v, s, size=6.5, z=8, ha="center", va="center", **kw):
    x, y = P(u, v)
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, zorder=z, **kw)

def num(u, v, n):
    x, y = P(u, v)
    ax.add_patch(Circle((x, y), 0.28, fc="white", ec="black", lw=0.4, zorder=9))
    ax.text(x, y, str(n), fontsize=5.6, ha="center", va="center", zorder=10)

# ---- floor fills
fill(0, 12, 1.6, 12, C_01)                     # 0-1 room
fill(9, 12, 1.6, 4.6, C_WET, z=1)              # water core
fill(12, 13.6, 1.6, 4.6, C_WET, z=1)           # 2-yr toilet (partial)
fill(0, 6, 0, 1.6, C_DOMA)                     # receiving doma
fill(6, 13.6, 0, 1.0, C_ROOF)                  # 2-yr path
fill(9, 13.6, 1.0, 1.6, C_ROOF)
fill(6, 9, 1.0, 1.6, "#DCE7B0", z=1)           # window seat
fill(0, 12, 12, 15, C_ROOF)                    # engawa
# south engawa wedge
south_w = [P(0, 1.6), P(-2.4, 1.6)] + [P(-2.4 * (11.5 - v) / 9.9, v) for v in [3, 5, 7, 9, 11.5]] + [P(0, 11.5)]
ax.add_patch(Polygon(south_w, closed=True, fc=C_ROOF, ec="black", lw=LW_F, zorder=1))

# ---- walls & columns
wall(-0.0, 13.6, -0.075, 0.075)                # west outer wall (spine)
for uf in [0, 3, 6, 9, 12]:
    for vc in [0, 12]:
        box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, lw=0.3, fc="black", z=6)
# south gable: doma door opening, glazing for room
wall(-0.075, 0.075, -0.075, 0.2)
wall(-0.075, 0.075, 1.4, 1.75)
# 乳児室の南の妻（10-26夜、ユーザー：B2＋格子。3dm は south/fix_details.py の「乳児室の南の妻」）：
# ガラスの引き戸 6 枚（2 本のレール、引き違い 3 組、v1.75〜11.45）、東の端は 0.35 の袖壁、外に杉の縦格子（30×45、120おき）を固定
wall(-0.075, 0.075, 11.45, 11.8)                                  # 南の妻の東の袖壁
_gw = (11.45 - 1.75) / 6
for _i in range(6):
    _a = 1.75 + _i * _gw - (0.02 if _i % 2 else 0); _b = 1.75 + (_i + 1) * _gw + (0 if _i % 2 else 0.02)
    _uu = (0.06, 0.09) if _i % 2 else (0.02, 0.05)
    box(_uu[0], _uu[1], max(_a, 1.75), min(_b, 11.45), lw=0.3, fc="#DCEBF3", z=6)   # ガラスの引き戸（外・内のレール）
def _lattice_s(v0, v1):                                               # 杉の縦格子（見付30・見込45、120おき、ガラスの外に固定）
    for _v in [v0 + 0.045 + 0.12 * k for k in range(int((v1 - v0 - 0.075) / 0.12) + 1)]:
        box(-0.23, -0.185, _v, _v + 0.03, lw=0, fc="#8a6a45", z=6)
_lattice_s(1.75, 11.45)
box(0.02, 0.05, 12.2, 13.5, lw=0.3, fc="#DCEBF3", z=6)                # 内縁側の端のガラス
_lattice_s(12.2, 13.5)                                                # 内縁側の端の格子
# 受け取り土間の格子の引き分け戸（v0.2〜1.4、10-27：開き戸の振れがベビーカー置き場に当たるので）：2 枚とも南の妻の外側を引く。
# 西の 1 枚（0.55）は外壁の角まで、東の 1 枚（0.65）は袖壁と格子の前へ。閉めた位置を描き、引く先は破線
box(-0.12, -0.035, 0.2, 0.75, lw=0.3, fc="#8a6a45", z=6); box(-0.12, -0.035, 0.75, 1.4, lw=0.3, fc="#8a6a45", z=6)
line([(-0.08, -0.35), (-0.08, 0.2)], lw=0.3, ls=(0, (2, 1.5)), c="#8a6a45"); line([(-0.08, 1.4), (-0.08, 2.05)], lw=0.3, ls=(0, (2, 1.5)), c="#8a6a45")
# low wall h600 between doma and room
box(0, 5.4, 1.6, 1.72, lw=0.4, fc="#999999", z=5)
line([(0, 1.45), (5.4, 1.45)], lw=0.3)           # kamachi edge
# shikidai + gate
box(5.4, 6.0, 0.1, 1.0, lw=LW_F, fc="#F7F1E6")
line([(6.0, 0.08), (6.0, 1.0)], lw=0.8)          # wooden gate
box(6.0, 9.0, 0.98, 1.06, lw=0.3, fc="white", z=5)   # lattice rail h600
box(5.95, 6.05, 1.0, 1.6, lw=0.4, fc="#999999", z=5)  # seat end wall
# peek windows in west wall
for uw, ww in [(3 * k - 1.5, 0.60) for k in range(1, 5)]:   # 西の窓（同じ大きさ 0.6×0.9、北へ高く、10-26夜）
    box(uw - ww / 2, uw + ww / 2, -0.075, 0.075, lw=0.3, fc="white", z=6)
# core walls
wall(9.0, 13.6, 1.6, 1.72)
wall(11.93, 12.07, 1.6, 4.6)
wall(12.0, 13.6, 4.55, 4.67)
# north partition to 2-yr room (with sliding door)
wall(11.94, 12.06, 4.6, 10.2)
wall(11.94, 12.06, 11.4, 11.8)
line([(11.9, 10.1), (11.9, 11.2)], lw=0.5); line([(12.1, 10.4), (12.1, 11.5)], lw=0.5)

# ---- water core furniture
box(9.0, 9.7, 1.72, 3.2, fc="white")                         # diaper counter
box(9.15, 9.6, 1.85, 3.05, lw=0.3, fc="#F2F7F8")              # diaper mats
box(9.0, 9.7, 3.2, 3.9, lw=0.3, ls=(0, (2, 1.5)), fc="none")  # child gate
box(9.0, 11.1, 3.9, 4.6, fc="white")                           # handwash + diaper shelf h850
box(9.9, 10.6, 4.0, 4.5, lw=0.3, fc="#F2F7F8")                 # handwash sink
box(11.25, 11.93, 1.72, 2.7, fc="white")                       # bath tub counter
ax.add_patch(Ellipse(P(11.6, 2.2), 0.45, 0.75, fc="#F2F7F8", ec="black", lw=0.3, zorder=4))
box(11.72, 11.93, 2.95, 3.35, lw=0.3, fc="white")              # small toilet (1-yr)
ax.add_patch(Ellipse(P(11.5, 3.15), 0.42, 0.32, fc="#F2F7F8", ec="black", lw=0.3, zorder=4))
box(11.93, 12.07, 3.7, 4.5, lw=0.3, fc="white", z=6)           # door to 2-yr toilet
line([(11.86, 3.3), (11.86, 4.1)], lw=0.6, z=7)
box(12.07, 13.6, 1.72, 2.5, lw=0.3, fc="none", ls=":")        # 2-yr toilet stalls hint

# ---- teacher's bench desk (back to diaper counter)
box(8.6, 9.0, 1.75, 3.15, fc="#F7F1E6")
box(7.85, 8.45, 1.85, 3.05, fc="white")

# ---- 0-yr side
box(3.6, 4.4, 1.95, 2.45, fc="white")                         # check table
box(0.6, 4.1, 3.0, 3.4, fc="white")                           # 0-yr lockers
for i in range(1, 10):
    line([(0.6 + 0.35 * i, 3.0), (0.6 + 0.35 * i, 3.4)], lw=0.2)
# nest
box(2.2, 5.6, 4.0, 7.6, lw=0.7, fc="none", z=4)
fill(2.2, 5.6, 4.0, 7.6, "#F3F5E4", z=2)
for vv in [(4.25, 5.45), (6.15, 7.35)]:
    for uu in [(2.45, 3.15), (3.55, 4.25), (4.65, 5.35)]:
        box(uu[0], uu[1], vv[0], vv[1], lw=0.35, fc="white")
box(5.56, 5.64, 5.2, 6.2, lw=0, fc=C_01, z=5)                  # opening
box(2.35, 5.45, 4.12, 7.48, lw=0.35, ls=(0, (4, 2)), fc="none", z=4)   # canopy (overhead)
# hanging cradles from beam at frame u=3
for vc in [8.5, 9.7]:
    ax.add_patch(Ellipse(P(3.0, vc), 0.5, 0.85, fc="white", ec="black", lw=0.4, zorder=4))
    ax.add_patch(Circle(P(3.0, vc), 0.62, fc="none", ec="black", lw=0.25, ls=(0, (2, 2)), zorder=4))
line([(3.0, 7.9), (3.0, 10.5)], lw=0.25, ls=(0, (6, 2, 1, 2)))
# crawling mound
ax.add_patch(Ellipse(P(1.25, 9.6), 1.8, 2.4, fc="#DCE7B0", ec="black", lw=0.4, zorder=3))
ax.add_patch(Ellipse(P(1.25, 9.6), 0.9, 1.2, fc="none", ec="black", lw=0.25, zorder=3))
# movable low shelves on boundary
for v0, v1 in [(3.5, 5.0), (6.4, 8.2), (9.0, 10.8)]:
    box(5.8, 6.2, v0, v1, fc="white")
    line([(5.8, v0 + 0.2), (6.2, v0 + 0.2)], lw=0.2)

# ---- 1-yr side
for u0 in [6.9, 9.5]:
    box(u0, u0 + 1.5, 5.5, 6.1, fc="white")
    for uc in [u0 + 0.25, u0 + 0.95]:
        box(uc, uc + 0.3, 5.1, 5.4, lw=0.3); box(uc, uc + 0.3, 6.2, 6.5, lw=0.3)
    box(u0 + 1.6, u0 + 1.9, 5.65, 5.95, lw=0.3)
# nap cots (dashed)
for vv in [(4.85, 5.9), (6.75, 7.8)]:
    for uc in [6.7, 7.65, 8.6, 9.55, 10.5]:
        box(uc, uc + 0.55, vv[0], vv[1], lw=0.3, ls=(0, (2, 1.5)), fc="none", ec="#6b7f3a", z=4)
# 1-yr lockers on north partition
box(11.55, 11.94, 5.0, 7.0, fc="white")                         # two-tier lockers
for i in range(1, 5):
    line([(11.55, 5.0 + 0.4 * i), (11.94, 5.0 + 0.4 * i)], lw=0.2)
box(11.3, 11.94, 7.1, 8.35, lw=0.6, fc="#DDDDDD")                # cot cabinet
line([(11.3, 7.1), (11.94, 8.35)], lw=0.2); line([(11.3, 8.35), (11.94, 7.1)], lw=0.2)
# laundry nook on the path (span 4, against plumbing wall)
box(9.15, 11.85, 0.95, 1.6, lw=0.5, fc="#EEF5F7", z=4)
box(9.3, 9.95, 0.97, 1.58, lw=0.35, fc="white", z=5)
ax.add_patch(Circle(P(9.62, 1.27), 0.22, fc="none", ec="black", lw=0.3, zorder=6))
box(10.1, 10.7, 1.0, 1.55, lw=0.35, fc="#F2F7F8", z=5)
box(10.85, 11.75, 1.0, 1.55, lw=0.3, fc="white", z=5)
# drying poles (overhead, in the west void under the roof monitor)
for vp in [0.4, 1.2]:
    line([(6.2, vp), (12.0, vp)], lw=0.5, ls=(0, (5, 1.5, 1, 1.5)), c="#3d6f8a", z=7)
# attic storage above water core (overhead)
box(9.05, 11.95, 1.65, 4.55, lw=0.5, ls=(0, (6, 2, 1, 2)), fc="none", ec="#8a5a2b", z=7)
# engawa low gate at the 0-1 / 2 boundary
box(11.97, 12.03, 12.2, 13.0, lw=0.3, fc="#bbbbbb", z=5); box(11.97, 12.03, 13.9, 14.6, lw=0.3, fc="#bbbbbb", z=5)
line([(12.0, 13.0), (12.8, 13.0)], lw=0.4)
# steps + slide
box(7.4, 9.9, 9.2, 10.8, fc="white")
for uu in [7.9, 8.4, 8.9]:
    line([(uu, 9.2), (uu, 10.8)], lw=0.25)
box(6.8, 7.4, 9.7, 10.3, lw=0.3, fc="white")
# milk nook (separate from diapers)
fill(10.3, 11.94, 8.5, 10.0, "#EAF4F6", z=1)
box(11.3, 11.94, 8.55, 9.95, fc="white")                      # counter h850
box(11.4, 11.85, 8.7, 9.2, lw=0.3, fc="#F2F7F8")              # milk sink
box(11.4, 11.85, 9.35, 9.85, lw=0.3, ls=(0, (2, 1.5)), fc="none")  # fridge under
line([(10.3, 8.5), (10.3, 9.0)], lw=0.9, c="#777777"); line([(10.3, 9.6), (10.3, 10.0)], lw=0.9, c="#777777")
line([(10.3, 9.0), (10.85, 9.0)], lw=0.4, ls=(0, (2, 1.5)))   # gate leaf
line([(10.3, 8.5), (11.3, 8.5)], lw=0.9, c="#777777")
line([(10.3, 10.0), (11.3, 10.0)], lw=0.9, c="#777777")

# ---- 縁側（10-26夜、3dm は south/add_floor.py）：中ほど v13.5 に、スパンごとに北の半分は杉の壁（外の大和張り＋断熱＋内の杉板、
# v13.465〜13.6）、南の半分はガラスの片引き戸（壁の室内側 v13.42〜13.46 を走り、開けると壁の前に重なる）。外縁側 v13.5〜15 は土足 −150
fill(0, 12, 13.6, 15, "#EAE0CF", z=0.5)                              # 外縁側（土足 −150）
for _k in range(4):
    _n, _s = 3 * _k + 3, 3 * _k
    wall(_n - 1.5, _n, 13.465, 13.6)                                  # 縁側の杉の壁（北の半分）
    box(_s, _n - 1.45, 13.42, 13.46, lw=0.3, fc="#DCEBF3", z=6)       # ガラスの片引き戸（閉、南の半分）
    line([(_n - 1.45, 13.44), (_n - 0.05, 13.44)], lw=0.25, ls=(0, (2, 1.5)))   # 開けたときの戸の位置（壁の前）
# ---- engawa edge: lattice railing + gates
for g0, g1 in [(2.2, 3.2), (8.4, 9.4)]:
    pass
railing = [(0, 2.2), (3.2, 8.4), (9.4, 12)]
for a, b in railing:
    box(a, b, 14.9, 15.0, lw=0.3, fc="#bbbbbb", z=5)
for g0, g1 in [(2.2, 3.2), (8.4, 9.4)]:
    line([(g0, 14.95), (g0, 15.95)], lw=0.4)   # gate leaf open
    box(g0 - 0.2, g1 + 0.2, 15.0, 15.3, lw=0.35, fc="white")   # step 1
    box(g0 - 0.2, g1 + 0.2, 15.3, 15.6, lw=0.35, fc="white")   # step 2
# eave line (overhead)
line([(0, 15.0), (12, 15.0)], lw=0.3, ls=(0, (6, 3)))
line([(-1.8, 15.0), (-4.2, 0.0)], lw=0.3, ls=(0, (6, 3)))
line([(-1.8, 15.0), (0, 15.0)], lw=0.3, ls=(0, (6, 3)))

# ---- south outside
line([(0, 1.6), (-5.8, 1.6)], lw=0.9)                   # fence h1.2 (line extension)
for uu in [-1, -2, -3, -4, -5]:
    box(uu - 0.05, uu + 0.05, 1.55, 1.65, lw=0.2, fc="black")
# crawl-out point (mound meeting engawa)
ax.add_patch(Ellipse(P(-2.4, 7.2), 2.4, 2.0, fc="#DCE7B0", ec="black", lw=0.4, zorder=0.5))
# two-step edge
box(-2.1, -1.65, 4.6, 5.6, lw=0.35, fc="white", z=2); box(-2.55, -2.1, 4.6, 5.6, lw=0.35, fc="white", z=2)
# outdoor-air bassinets
for vc in [2.4, 3.4]:
    ax.add_patch(Ellipse(P(-1.0, vc), 0.5, 0.8, fc="white", ec="black", lw=0.3, zorder=3))
# outdoor shed (walk carts, sand tools) on garden side of fence
box(-4.3, -2.6, 1.7, 2.75, lw=0.6, fc="#EDE6D6", z=3)
line([(-4.3, 1.7), (-2.6, 2.75)], lw=0.2); line([(-4.3, 2.75), (-2.6, 1.7)], lw=0.2)

# ---- morning garden (east, schematic)
fill(0, 12, 15.6, 22.0, C_OUT, z=-1)
for a, b in [(-0.5, 2.6), (4.2, 8.0), (9.8, 13.0)]:
    line([(a, 21.2), (b, 21.2)], lw=0.5, ls=(0, (1, 1.5)))
    line([(a, 21.7), (b, 21.7)], lw=0.5, ls=(0, (1, 1.5)))
ax.add_patch(Ellipse(P(5.5, 18.3), 3.2, 2.2, fc="#F4EFE2", ec="black", lw=0.35, ls=(0, (2, 1.5)), zorder=1))
for (uu, vv) in [(1.5, 17.6), (10.3, 18.6)]:
    ax.add_patch(Circle(P(uu, vv), 1.6, fc="none", ec="#5a7a3a", lw=0.4, zorder=1))
    ax.add_patch(Circle(P(uu, vv), 0.12, fc="#5a7a3a", ec="none", zorder=1))
# bench outside railing for big kids
box(4.0, 6.5, 15.15, 15.5, lw=0.35, fc="white")

# ---- break line to the north
line([(13.6, -0.3), (13.6, 15.2)], lw=0.3, ls=(0, (8, 2, 1, 2)))

# ---- labels (numbers)
labels = [
    (3.0, 0.8, 1), (2.6, 1.66, 2), (5.7, 0.55, 3), (8.4, 0.5, 4), (7.5, 1.3, 5),
    (4.0, 2.2, 6), (2.3, 3.2, 7), (3.85, 5.8, 8), (3.0, 11.0, 9), (1.25, 9.6, 10),
    (6.0, 8.6, 11), (8.15, 2.45, 12), (9.35, 2.45, 13), (11.0, 2.2, 14), (10.95, 4.25, 30),
    (8.0, 7.2, 16), (11.75, 6.7, 17), (8.65, 10.0, 18), (6.0, 12.75, 19), (2.7, 15.45, 20),
    (8.9, 15.8, 21), (-1.0, 4.3, 22), (-2.4, 7.2, 23), (-4.0, 1.25, 24), (12.8, 3.1, 25),
    (12.4, 10.8, 26), (5.5, 18.3, 27), (5.25, 15.8, 28), (9.0, 20.9, 29), (10.8, 9.25, 15), (10.4, 0.5, 31), (6.9, 0.45, 32), (-3.45, 2.75, 33), (11.62, 7.72, 34), (10.3, 3.25, 35), (12.45, 13.45, 36), (-0.65, 9.6, 37),
]
for u, v, n in labels:
    num(u, v, n)

# zone captions
txt(4.6, 10.9, "0歳", size=10, color="#4d6b1f", weight="medium")
txt(9.0, 8.5, "1歳", size=10, color="#4d6b1f", weight="medium")
txt(-3.3, 0.6, "ポーチ", size=6)
txt(-4.6, 8.5, "乳児の庭（みなみの三角）↓", size=6)
txt(3.6, 20.4, "朝の庭（年齢ミックス・昼から静か）", size=6)
txt(13.9, 7.0, "2歳の部屋 →", size=6, ha="left")

# frame labels + span labels
for uf, f in zip([0, 3, 6, 9, 12], [1, 2, 3, 4, 5]):
    x, y = P(uf, -1.15)
    ax.text(x, y, f"架構{f}", fontsize=5, ha="center", va="center")
    line([(uf, -0.35), (uf, -0.85)], lw=0.25)
for s, uc in zip([1, 2, 3, 4], [1.5, 4.5, 7.5, 10.5]):
    txt(uc, -1.15, f"スパン{s}", size=4.6, color="#666666")
# dimensions along top (u = 14.6)
ud = 14.7
pts = [0, 1.6, 12, 13.5, 15]
line([(ud, 0), (ud, 15)], lw=0.3)
for vv in pts:
    line([(ud - 0.15, vv), (ud + 0.15, vv)], lw=0.5)
for a, b, s in [(0, 1.6, "1,600"), (1.6, 12, "10,400"), (12, 13.5, "1,500"), (13.5, 15, "1,500")]:
    txt(ud + 0.35, (a + b) / 2, s, size=5)
# dims along west (v = -1.9): spans 3,000
line([(0, -1.9), (12, -1.9)], lw=0.3)
for uu in [0, 3, 6, 9, 12]:
    line([(uu, -1.75), (uu, -2.05)], lw=0.5)
for uu in [1.5, 4.5, 7.5, 10.5]:
    txt(uu, -2.3, "3,000", size=5)

# north arrow (true north)
nx, ny = 20.5, 13.0
north = (-sr, cr)  # rotate (0,1)
ax.annotate("", xy=(nx + north[0] * 1.3, ny + north[1] * 1.3), xytext=(nx - north[0] * 0.6, ny - north[1] * 0.6),
            arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
ax.text(nx + north[0] * 1.8, ny + north[1] * 1.8, "N", fontsize=8, ha="center", va="center")
# scale bar
sx, sy = 16.0, -6.6
for i in range(5):
    ax.add_patch(Polygon([(sx + i, sy), (sx + i + 1, sy), (sx + i + 1, sy + 0.18), (sx + i, sy + 0.18)],
                         fc="black" if i % 2 == 0 else "white", ec="black", lw=0.3))
for i in [0, 1, 5]:
    ax.text(sx + i, sy - 0.35, f"{i}", fontsize=5, ha="center", va="top")
ax.text(sx + 5.4, sy + 0.09, "m", fontsize=5, va="center")

# ---- areas
a_room = area(rect_pts(0, 12, 1.6, 12))
a0 = area(rect_pts(0, 6, 1.6, 12))
a1 = area(rect_pts(6, 12, 1.6, 12)) - area(rect_pts(9, 12, 1.6, 4.6)) - area(rect_pts(10.3, 12, 8.5, 10.0))
a_core = area(rect_pts(9, 12, 1.6, 4.6))
a_seat = area(rect_pts(6, 9, 1.0, 1.6))
a_eng = area(rect_pts(0, 12, 12, 15))
a_doma = area(rect_pts(0, 6, 0, 1.6))
print(a_room, a0, a1, a_core, a_seat, a_eng, a_doma)

# ---- title & legend
fig.text(20 / 297, 410 / 420, "育ち舎　0・1歳の部屋　家具配置（たたき台）", fontsize=13, weight="medium", va="top")
fig.text(20 / 297, 402 / 420, "1/100（A3）　2026-10-27　西の背骨（r=205）を上下に、北を上寄りに描く。破線は頭上（軒・天蓋・物干し・天袋）と午睡時のコット。",
         fontsize=6.5, va="top", color="#444444")

legend = [
    "1　受け取り土間（GL＝FL−300）。南の妻の格子の引き分け戸（外を引く、両方開けて 1.2）・背くらべの柱",
    "2　框＋腰壁 h600（受け渡しのカウンター）",
    "3　式台 150＋木戸（2歳はここで靴を脱ぐ。木戸は先生が開ける）",
    "4　2歳の道（幅 1.0、西の外壁沿い）",
    "5　窓辺の小上がり h300＋格子の手すり h600。覗き窓は西の外壁。中は引き出し",
    "6　受け入れ（検温・連絡帳の小机）",
    "7　0歳の個人棚 h700（10人分）",
    "8　ねどこ：ベビーベッド×6（ほかは床に布団）、囲い h900、布の天蓋",
    "9　吊りかご×2（寝かしつけ用。架構2 の梁から4点吊り、破線は振れの範囲）",
    "10　ほふくの丘（h200 のゆるい起伏）",
    "11　動かせる低い棚 h600（0歳／1歳の境。寄せれば閉じる）",
    "12　先生の腰掛ける机（座 h300・天板 h500、背はおむつ台の腰壁、座の下は収納）",
    "13　おむつ替え台 h850（先生は北に立ち、部屋を向く）",
    "14　沐浴槽・1歳の小さな便器・2歳トイレへの戸（背伸びの戸）",
    "15　調乳コーナー（おむつと完全に分ける。シンク・冷蔵庫、柵 h900＋戸）",
    "16　1歳の食卓 h350×2・椅子×10／午睡時はヒノキと帆布のコット×10（破線）",
    "17　1歳の個人棚（二段、北の間仕切り沿い）",
    "18　上り下りの段々（150×3）と短いすべり台",
    "19　縁側：内縁側 1.5（はだし）＋外縁側 1.5（土足 −150）。中ほどにスパンごとに杉の壁＋ガラスの片引き戸、外の端に格子の高欄 h900",
    "20　高欄の戸（先生が開ける）と二段の縁（150×2）",
    "22　南の縁側：外気浴（深い軒の下）",
    "23　這い出せる一点（築山が縁側の高さまで上がる）と二段の縁",
    "24　柵 h1.2（一本の線の延長）→ 非常用の門。西はポーチ",
    "25　2歳のトイレ（参考、入口は東向き）",
    "26　1歳⇔2歳の引き戸（朝夕の合同保育）",
    "27　1–2 mm の粒の遊び場（夕方は「おやすみの布」）",
    "28　大きい子の縁台 h300（高欄越しに目が合う）",
    "29　土手＋生垣（切れ目から入る。奥行きは配置図で決める）",
    "30　手洗い・おむつの棚 h850（水まわりの東の縁、腰壁を兼ねる）",
    "31　洗濯：洗濯乾燥機・予洗いのシンク・たたむ棚（水まわりの配管壁に沿う）",
    "32　物干し（昇降式の竹竿。西の吹き抜けの上、越屋根の下で乾かす）",
    "33　外の物置（散歩車・砂場の道具。柵と一体、南の軒の下）",
    "34　1歳のコットの収納（重ねて 10台）",
    "35　天袋（水まわりの上。季節のもの・おむつの在庫・予備の寝具）",
    "36　縁側の低い柵の戸（0・1歳／2歳の縁側の境）",
    "37　南の妻：ガラスの引き戸（引き違い）の外に杉の縦格子 30×45@120。戸を開けても柵（上端は縁側の鴨居と一本）",
]
col_x = [20 / 297, 158 / 297]
y0 = 150 / 420
dy = 4.3 / 420
half = 18
for i, s in enumerate(legend):
    c = 0 if i < half else 1
    r = i if i < half else i - half
    fig.text(col_x[c], y0 - r * dy, s, fontsize=6.2, va="top")

summary = (f"面積（芯々、概算）　0・1歳の保育室 {a_room + a_eng:.1f} m²（縁側 {a_eng:.1f} を含む）　室内 {a_room:.1f} m²（うち 0歳側 {a0:.1f}、1歳側 {a1:.1f}、水まわり {a_core:.1f}、調乳 {area(rect_pts(10.3, 12, 8.5, 10.0)):.1f}）"
           f"　窓辺 {a_seat:.1f}　土間 {a_doma:.1f}")
fig.text(20 / 297, 68 / 420, summary, fontsize=6.2, va="top")
fig.text(20 / 297, 63 / 420,
         "基準の目安：ほふく室 3.3 m²/人 × 20人 = 66 m²。"
         "柱 400×180（黒）。室と縁側のあいだ（架構の東の柱の列）は開け放し。縁側の中ほどの杉の壁とガラスの片引き戸が外壁。",
         fontsize=6.2, va="top", color="#444444")

# 換気扇（10-24、ユーザー：建物の中で臭いが出るのはおむつ替え・沐浴）：天井の換気扇 → ダクトで西へ → 越屋根の東の口（逆流止め）
uu, vv = 10.5, 2.0
box(uu - 0.15, uu + 0.15, vv - 0.15, vv + 0.15, lw=0.35, fc="white", z=9)
line([(uu - 0.15, vv - 0.15), (uu + 0.15, vv + 0.15)], lw=0.3, z=9); line([(uu - 0.15, vv + 0.15), (uu + 0.15, vv - 0.15)], lw=0.3, z=9)
txt(uu + 0.32, vv + 0.75, "換気扇→越屋根", size=3.4, color="#3d7fb0", z=9)
# ---- 壁の輪郭を一本に（10-24、draw100.py の joined() と同じ考え：同じ種類の壁をまとめ、角の欠けとすき間 120 未満を閉じて輪郭を描く）----
from shapely.geometry import box as _sbox
from shapely.ops import unary_union as _uu
def _wall_outline():
    g = _uu([_sbox(*w) for w in _WALLS]).buffer(0.06, join_style=2).buffer(-0.06, join_style=2)
    for p in getattr(g, "geoms", [g]):
        if p.is_empty: continue
        for ring in [p.exterior] + list(p.interiors):
            ax.add_patch(Polygon([P(u, v) for u, v in ring.coords], closed=True, fc="none", ec="black", lw=0.5, zorder=5.5))
_wall_outline()
fig.savefig(_os.path.join(OUT, "sodachiya_01_furniture.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_01_furniture.png"), dpi=220)
