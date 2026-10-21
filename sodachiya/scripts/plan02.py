import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Ellipse, Arc

plt.rcParams["font.family"] = "Noto Sans CJK JP"

R = 205.0
phi0 = math.radians(186.67)
phi_mid = phi0 - 15.0 / R
rot = -(phi_mid - math.pi)
cr, sr = math.cos(rot), math.sin(rot)

def raw(u, v):
    p = phi0 - u / R
    r = R - v
    x, y = r * math.cos(p), r * math.sin(p)
    return x * cr - y * sr, x * sr + y * cr

X0, Y0 = raw(12, 0)
def P(u, v):
    x, y = raw(u, v)
    return x - X0, y - Y0

def rect_pts(u0, u1, v0, v1, n=6):
    pts = [P(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)]
    pts += [P(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
    return pts

def area(pts):
    s = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2

MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
xmin, xmax = -3.2, 21.0
ymin, ymax = -4.0, 10.6
left_mm, bottom_mm = 25, 240
ax = fig.add_axes([left_mm / 297, bottom_mm / 420, (xmax - xmin) * 10 / 297, (ymax - ymin) * 10 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

LW_F = 0.45
C_2, C_ROOF, C_WET, C_OTHER = "#C5DE9A", "#F4EBDD", "#D5EBEE", "#F2F2EF"

def fill(u0, u1, v0, v1, color, z=0):
    ax.add_patch(Polygon(rect_pts(u0, u1, v0, v1), closed=True, fc=color, ec="none", zorder=z))

def box(u0, u1, v0, v1, lw=LW_F, fc="white", ls="-", z=3, ec="black"):
    ax.add_patch(Polygon(rect_pts(u0, u1, v0, v1), closed=True, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))

def line(pts, lw=LW_F, ls="-", c="black", z=3):
    xs, ys = zip(*[P(u, v) for u, v in pts])
    ax.plot(xs, ys, lw=lw, ls=ls, color=c, zorder=z, solid_capstyle="butt")

def wall(u0, u1, v0, v1):
    box(u0, u1, v0, v1, lw=0.6, fc="#444444", z=5)

def txt(u, v, s, size=6.5, z=8, ha="center", va="center", **kw):
    x, y = P(u, v)
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, zorder=z, **kw)

def num(u, v, n):
    x, y = P(u, v)
    ax.add_patch(Circle((x, y), 0.28, fc="white", ec="black", lw=0.4, zorder=9))
    ax.text(x, y, str(n), fontsize=5.6, ha="center", va="center", zorder=10)

U0, U1 = 10.4, 19.6   # drawn range
# ---- fills
fill(U0, 12, 1.6, 12, C_OTHER)                 # 0-1 room (context)
fill(U0, 12, 1.6, 4.6, "#E6EEF0", z=1)
fill(18, U1, 1.6, 12, C_OTHER)                 # span 7 (医務)
fill(12, 18, 1.6, 12, C_2)                     # 2-yr room
fill(12, 14.7, 1.6, 4.6, C_WET, z=1)           # toilet
fill(U0, U1, 0, 1.6, C_ROOF)                   # west strip
fill(12, 18, 1.2, 1.6, "#D8E8B6", z=1)         # strip remnant joined to room
fill(U0, U1, 12, 15, C_ROOF)                   # engawa

# ---- walls & columns
wall(U0, U1, -0.075, 0.075)
for uf in [12, 15, 18]:
    for vc in [0, 12]:
        box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, lw=0.3, fc="black", z=6)
# 0-1 / 2 partition (u=12)
wall(11.94, 12.06, 1.6, 10.2); wall(11.94, 12.06, 11.4, 11.8)
line([(11.9, 10.1), (11.9, 11.2)], lw=0.5); line([(12.1, 10.4), (12.1, 11.5)], lw=0.5)
# 0-1 core west wall (context) and toilet walls
wall(U0, 14.7, 1.6, 1.72)
wall(14.63, 14.77, 1.6, 4.6)
wall(12.0, 13.4, 4.55, 4.67)                    # toilet east wall (entrance u13.4-14.63)
box(11.93, 12.07, 3.7, 4.5, lw=0.3, fc="white", z=6)    # 背伸びの戸
line([(12.14, 3.3), (12.14, 4.1)], lw=0.6, z=7)
# 2-yr / 医務 partition (u=18)
wall(17.95, 18.07, 1.6, 12.0)
# toilet entrance: low swing half-doors
line([(13.4, 4.61), (13.95, 5.0)], lw=0.35); line([(14.63, 4.61), (14.08, 5.0)], lw=0.35)

# ---- toilet interior
box(12.07, 12.9, 1.72, 2.6, lw=0.35, fc="#F2F7F8")      # shower pan
line([(12.07, 1.72), (12.9, 2.6)], lw=0.2); line([(12.07, 2.6), (12.9, 1.72)], lw=0.2)
for uc in [13.15, 13.85, 14.45]:
    box(uc - 0.12, uc + 0.12, 1.72, 1.9, lw=0.3)               # tank
    ax.add_patch(Ellipse(P(uc, 2.1), 0.34, 0.42, fc="white", ec="black", lw=0.35, zorder=4))
for up in [13.5, 14.15]:
    line([(up, 1.72), (up, 2.6)], lw=0.4)                       # low partitions h900
box(12.1, 12.55, 2.85, 3.55, lw=0.35, fc="white")               # changing stand

# ---- arrival / じぶんで
box(14.77, 15.12, 1.75, 4.55, fc="white")                       # lockers
for i in range(1, 10):
    line([(14.77, 1.75 + 0.28 * i), (15.12, 1.75 + 0.28 * i)], lw=0.2)
box(15.9, 16.3, 2.2, 4.0, fc="#F7F1E6")                          # slow bench
# teacher record counter
box(17.3, 17.95, 1.75, 3.0, fc="white")
# cool-down nook
box(16.9, 17.95, 3.3, 4.6, lw=0.8, fc="#E9DFC9", z=3)
box(16.98, 16.98 + 0.04, 3.6, 4.3, lw=0, fc="#E9DFC9", z=4)
line([(16.9, 3.62), (16.9, 4.28)], lw=1.2, c="#E9DFC9", z=5)    # opening (south)
box(17.05, 17.85, 3.45, 4.45, lw=0.3, ls=(0, (3, 2)), fc="none", z=4)   # low roof board (overhead)
# hand wash outside toilet
box(12.1, 13.3, 4.67, 5.2, fc="white")
for uc in [12.4, 13.0]:
    ax.add_patch(Ellipse(P(uc, 4.93), 0.34, 0.28, fc="#F2F7F8", ec="black", lw=0.3, zorder=4))
# books
box(12.07, 12.35, 6.0, 8.4, fc="white")
box(12.4, 13.3, 6.1, 8.3, lw=0.3, fc="#EFE6D2")                  # goza
# tables + chairs
for va in [5.9, 7.6]:
    box(13.6, 15.1, va, va + 0.6, fc="white")
    for uc in [13.8, 14.5]:
        box(uc, uc + 0.3, va - 0.4, va - 0.1, lw=0.3); box(uc, uc + 0.3, va + 0.7, va + 1.0, lw=0.3)
    box(15.2, 15.5, va + 0.15, va + 0.45, lw=0.3)
# nap futons / cots (dashed)
for vv in [(5.35, 6.4), (7.25, 8.3)]:
    for uc in [12.5, 13.18, 13.86, 14.54, 15.22]:
        box(uc, uc + 0.55, vv[0], vv[1], lw=0.3, ls=(0, (2, 1.5)), fc="none", ec="#4f6b2a", z=4)
# house (mamagoto)
box(16.2, 17.95, 5.0, 6.9, lw=0.3, ls=(0, (1, 1.2)), fc="#F6EFE0")
for pu, pv in [(16.25, 5.05), (16.25, 6.85), (17.9, 5.05), (17.9, 6.85)]:
    box(pu - 0.05, pu + 0.05, pv - 0.05, pv + 0.05, lw=0.3, fc="black", z=5)
box(16.4, 17.8, 5.2, 6.7, lw=0.3, ls=(0, (3, 2)), fc="none", z=4)   # low roof
box(17.4, 17.9, 5.3, 6.0, lw=0.3, fc="white", z=5)                  # tiny kitchen
# closet (cots / futon), high shelf
box(12.07, 12.7, 8.55, 10.05, lw=0.6, fc="#DDDDDD")
line([(12.07, 8.55), (12.7, 10.05)], lw=0.2); line([(12.07, 10.05), (12.7, 8.55)], lw=0.2)
# hill against north wall (contours), hideout inside, opening west
import math as _m
room_clip = Polygon(rect_pts(12, 17.95, 1.6, 12), closed=True, transform=ax.transData)
def hill(k, ru=1.9, re=2.2, rw=1.3, vc=9.6, n=40):
    pts = []
    for i in range(n + 1):
        t = _m.pi * i / n
        r = re if _m.cos(t) >= 0 else rw
        pts.append(P(17.95 - ru * k * _m.sin(t), vc + r * k * _m.cos(t)))
    return pts
for k, fc in [(1.0, "#E3EDC9"), (0.66, "#D3E3AE"), (0.33, "#C3D894")]:
    ax.add_patch(Polygon(hill(k), closed=True, fc=fc, ec="black", lw=0.4, zorder=3))
def on(k, t, ru=1.9, re=2.2, rw=1.3, vc=9.6):
    r = re if _m.cos(t) >= 0 else rw
    return (17.95 - ru * k * _m.sin(t), vc + r * k * _m.cos(t))
cl = [on(0.66, _m.pi * f) for f in [0.58, 0.63, 0.68, 0.73]]
line(cl, lw=2.0, c="#5b4a2e", z=6)                                   # small cliff h350
op = [on(1.0, _m.pi * f) for f in [0.84, 0.88, 0.92, 0.95]]
line(op, lw=2.4, c="#8a5a2b", z=6)                                   # hideout opening (west)
box(16.95, 17.9, 8.85, 10.3, lw=0.35, ls=(0, (1.5, 1.5)), fc="none", z=4)   # hideout below
pu, pv = on(1.0, _m.pi * 0.1)
ax.add_patch(Circle(P(pu, pv), 0.12, fc="white", ec="black", lw=0.4, zorder=6))   # peep hole east
# open floor marker
txt(13.9, 10.3, "ひらけた床", size=6, color="#4f6b2a")

# laundry nook (span 4, context) + drying poles + attic
box(10.4, 11.85, 0.95, 1.6, lw=0.5, fc="#EEF5F7", z=4)
box(10.4, 10.7, 1.0, 1.55, lw=0.35, fc="#F2F7F8", z=5)
box(10.85, 11.75, 1.0, 1.55, lw=0.3, fc="white", z=5)
for vp in [0.4, 1.0]:
    line([(10.4, vp), (17.8, vp)], lw=0.5, ls=(0, (5, 1.5, 1, 1.5)), c="#3d6f8a", z=7)
box(12.05, 14.65, 1.65, 4.55, lw=0.5, ls=(0, (6, 2, 1, 2)), fc="none", ec="#8a5a2b", z=7)
box(11.97, 12.03, 12.2, 13.0, lw=0.3, fc="#bbbbbb", z=5); box(11.97, 12.03, 13.9, 14.6, lw=0.3, fc="#bbbbbb", z=5)
line([(12.0, 13.0), (12.8, 13.0)], lw=0.4)

# ---- engawa
line([(U0, 14.7), (U1, 14.7)], lw=0.4); line([(U0, 14.76), (U1, 14.76)], lw=0.4)
for a, b in [(U0, 15.0), (16.0, 18.0)]:
    box(a, b, 14.9, 15.0, lw=0.3, fc="#bbbbbb", z=5)
line([(15.0, 14.95), (15.0, 15.95)], lw=0.4)
box(14.8, 16.2, 15.0, 15.3, lw=0.35); box(14.8, 16.2, 15.3, 15.6, lw=0.35)
line([(15.1, 15.08), (15.9, 15.08)], lw=1.6, c="#7b5ea7", z=6)
line([(U0, 15.0), (U1, 15.0)], lw=0.3, ls=(0, (6, 3)))
txt(18.8, 13.5, "縁側（開け放し）→", size=5.5, color="#666666")

# break lines
for ub in [U0, U1]:
    line([(ub, -0.3), (ub, 15.3)], lw=0.3, ls=(0, (8, 2, 1, 2)))

# ---- numbers
labels = [
    (16.0, 0.6, 1), (14.95, 3.15, 2), (16.1, 3.1, 3), (13.85, 2.1, 4), (12.33, 3.2, 5),
    (12.0, 3.0, 6), (12.7, 4.93, 7), (14.35, 6.2, 8), (12.85, 7.2, 9), (12.85, 10.3, 10),
    (16.9, 10.6, 11), (17.0, 6.0, 12), (17.45, 3.95, 13), (17.62, 2.4, 14), (15.0, 13.5, 15),
    (15.5, 15.95, 16), (12.0, 10.8, 17), (12.38, 9.3, 18), (12.45, 13.45, 19), (13.6, 0.7, 20), (13.8, 3.6, 21), (11.1, 1.27, 22),
]
for u, v, n in labels:
    num(u, v, n)
txt(15.0, 5.0, "2歳", size=10, color="#3d5a1a", weight="medium")
txt(11.2, 7.2, "0・1歳の部屋", size=6, color="#777777")
txt(18.8, 7.0, "医務（スパン7）", size=6, color="#777777")

# frames / dims
for uf, f in zip([12, 15, 18], [5, 6, 7]):
    x, y = P(uf, -1.15)
    ax.text(x, y, f"架構{f}", fontsize=5, ha="center", va="center")
    line([(uf, -0.35), (uf, -0.85)], lw=0.25)
for s, uc in zip([5, 6], [13.5, 16.5]):
    txt(uc, -1.15, f"スパン{s}", size=4.6, color="#666666")
line([(12, -1.9), (18, -1.9)], lw=0.3)
for uu in [12, 15, 18]:
    line([(uu, -1.75), (uu, -2.05)], lw=0.5)
for uu in [13.5, 16.5]:
    txt(uu, -2.3, "3,000", size=5)
ud = 19.9
line([(ud, 0), (ud, 15)], lw=0.3)
for vv in [0, 1.2, 1.6, 12, 15]:
    line([(ud - 0.15, vv), (ud + 0.15, vv)], lw=0.5)
for a, b, s in [(0, 1.2, "1,200"), (1.6, 12, "10,400"), (12, 15, "3,000")]:
    txt(ud + 0.35, (a + b) / 2, s, size=5)

# north arrow + scale
nx, ny = 19.0, 8.4
north = (-sr, cr)
ax.annotate("", xy=(nx + north[0] * 1.3, ny + north[1] * 1.3), xytext=(nx - north[0] * 0.6, ny - north[1] * 0.6),
            arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
ax.text(nx + north[0] * 1.8, ny + north[1] * 1.8, "N", fontsize=8, ha="center", va="center")
sx, sy = 14.5, -3.4
for i in range(5):
    ax.add_patch(Polygon([(sx + i, sy), (sx + i + 1, sy), (sx + i + 1, sy + 0.18), (sx + i, sy + 0.18)],
                         fc="black" if i % 2 == 0 else "white", ec="black", lw=0.3))
for i in [0, 1, 5]:
    ax.text(sx + i, sy - 0.3, f"{i}", fontsize=5, ha="center", va="top")
ax.text(sx + 5.4, sy + 0.09, "m", fontsize=5, va="center")

# ---- areas
a_room = area(rect_pts(12, 18, 1.6, 12))
a_wc = area(rect_pts(12, 14.7, 1.6, 4.6))
a_strip = area(rect_pts(12, 18, 1.2, 1.6))
a_path = area(rect_pts(12, 18, 0, 1.2))
a_eng = area(rect_pts(12, 18, 12, 15))
a01 = area(rect_pts(0, 12, 1.6, 12))
print(a_room, a_wc, a_room - a_wc, a_strip, a_path, a_eng)

fig.text(25 / 297, 410 / 420, "育ち舎　2歳の部屋　家具配置（たたき台）", fontsize=13, weight="medium", va="top")
fig.text(25 / 297, 402 / 420, "1/100（A3）　2026-10-19　架構5〜7（スパン5・6、南から）。破線は頭上（屋根板・軒・物干し・天袋）と午睡時のコット。",
         fontsize=6.5, va="top", color="#444444")
legend = [
    "1　2歳の道（先生と歩いて登園する。幅 1.2、壁なし）",
    "2　じぶんでの場所：個人棚・フック（10人分、h900）",
    "3　ゆっくりのベンチ h250（着替え・靴下。座の下は引き出し）",
    "4　トイレ：座る便器×3（低い仕切り h900）、シャワーパン",
    "5　立ったままパンツを替える台",
    "6　背伸びの戸（1歳が先生と来る）",
    "7　手洗い×2 h500・鏡（トイレを出てすぐ、食事の前）",
    "8　食卓 h400×2・椅子×10／午睡時はヒノキと帆布のコット×10（破線）",
    "9　絵本の面陳棚 h600・ござ",
    "10　ひらけた床（積み木・ブロック）",
    "11　山：頂上 h900、南 約1:2・東 約1:2.5 の斜面、肩に崖 h350、中はかくれ家（入口は西、東に覗き穴）",
    "12　ままごとの家（壁のない家：柱と低い屋根 h1400。先生の目が通る）",
    "13　落ち着くくぼみ（自分から入る狭い所。先生から見える）",
    "14　先生の記録台 h900（背は北の壁、部屋全体を見る）",
    "15　縁側（教室の一部）：引き込みのガラス戸＋格子の高欄 h900",
    "16　高欄の戸・二段の縁・「おひるね中」の暖簾",
    "17　1歳⇔2歳の引き戸（朝夕の合同保育）",
    "18　コットの収納（扉付き。上は先生の物の高い棚）",
    "19　縁側の低い柵の戸（0・1歳／2歳の縁側の境）",
    "20　物干し（昇降式の竹竿。西の吹き抜けの上、越屋根の下）",
    "21　天袋（トイレの上）",
    "22　洗濯（0・1歳の側、水まわりの配管壁沿い）",
]
col_x = [25 / 297, 160 / 297]
y0, dy, half = 225 / 420, 4.4 / 420, 11
for i, s in enumerate(legend):
    c, r = (0, i) if i < half else (1, i - half)
    fig.text(col_x[c], y0 - r * dy, s, fontsize=6.2, va="top")
fig.text(25 / 297, 170 / 420,
         f"面積（芯々、概算）　2歳の保育室 {a_room + a_eng:.1f} m²（縁側を含む）　室内 {a_room:.1f} m²（うちトイレ {a_wc:.1f}、トイレを除く {a_room - a_wc:.1f}）"
         f"　道の残り（室に含める帯）{a_strip:.1f}　2歳の道 {a_path:.1f}　縁側 {a_eng:.1f}",
         fontsize=6.2, va="top")
fig.text(25 / 297, 165 / 420,
         "危ないものと先生の物は扉の中か h1500 以上へ。それより低い所にあるものは全部さわってよい。",
         fontsize=6.2, va="top", color="#444444")

fig.savefig(_os.path.join(OUT, "sodachiya_02_furniture.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_02_furniture.png"), dpi=220)
