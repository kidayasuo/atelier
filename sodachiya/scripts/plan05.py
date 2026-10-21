# 南の入口まわり 1/100（ラフ）：キッチン・はれのま（仮）・西館の土間・海峡の延長・入口・スパン7（医務・事務）
# 座標は本館の (u, v)。架構の番号は南から（架構 k は u = 3(k−1)、スパン k は架構 k と k+1 のあいだ）。
import math, os, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Ellipse, Arc, FancyArrowPatch
from shapely.geometry import Polygon as SP, box as sbox
from shapely import affinity as af

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"

CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
def Wraw(u, v):
    th = TH_S - u / RW; r = RW - v
    return (CX + r * math.cos(th), CY + r * math.sin(th))
O = np.array(Wraw(24, 0)); dvec = np.array(Wraw(24.5, 0)) - np.array(Wraw(23.5, 0))
ANG = math.atan2(dvec[1], dvec[0]) - math.pi / 2          # rotate so that +u points up
ca, sa = math.cos(-ANG), math.sin(-ANG)
def rot(p):
    x, y = p[0] - O[0], p[1] - O[1]
    return (x * ca - y * sa, x * sa + y * ca)
def W(u, v): return rot(Wraw(u, v))
def rect(u0, u1, v0, v1, n=4):
    return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
WN = pickle.load(open(os.path.join(ROOT, "data", "wnew.pkl"), "rb"))["WN"]
WN = af.scale(WN, 0.001, 0.001, origin=(0, 0))
WB = SP([rot(p) for p in WN.exterior.coords])

MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
U0, U1, V0, V1 = 16.4, 31.6, -14.6, 15.6
xs = [W(u, v)[0] for u in (U0, U1) for v in (V0, V1)]; ys = [W(u, v)[1] for u in (U0, U1) for v in (V0, V1)]
xmin, xmax, ymin, ymax = min(xs) - 0.3, max(xs) + 0.3, min(ys) - 0.3, max(ys) + 0.3
PL, PB = 18, 82
ax = fig.add_axes([PL / 420, PB / 297, (xmax - xmin) * 10 / 420, (ymax - ymin) * 10 / 297])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

def poly(pts, fc="none", ec="black", lw=0.45, z=2, ls="-", alpha=1):
    if hasattr(pts, "geom_type"):
        gs = [pts] if pts.geom_type == "Polygon" else [g for g in getattr(pts, "geoms", []) if g.geom_type == "Polygon"]
        for g in gs: poly(list(g.exterior.coords), fc, ec, lw, z, ls, alpha)
        return
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, alpha=alpha))
def box(u0, u1, v0, v1, fc="white", ec="black", lw=0.45, z=4, ls="-"):
    poly(rect(u0, u1, v0, v1), fc, ec, lw, z, ls)
def fill(u0, u1, v0, v1, c, z=1):
    poly(rect(u0, u1, v0, v1), c, "none", 0, z)
def line(uv, lw=0.45, c="black", ls="-", z=5):
    p = [W(u, v) for u, v in uv]; ax.plot([q[0] for q in p], [q[1] for q in p], lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def wall(u0, u1, v0, v1): box(u0, u1, v0, v1, fc="#333333", ec="#333333", lw=0.3, z=6)
def T(u, v, s, size=6, c="#222222", z=10, **kw):
    x, y = W(u, v); ax.text(x, y, s, fontsize=size, color=c, ha="center", va="center", zorder=z, **kw)
def num(u, v, k):
    x, y = W(u, v); ax.add_patch(Circle((x, y), 0.3, fc="white", ec="black", lw=0.4, zorder=12)); ax.text(x, y, str(k), fontsize=5.4, ha="center", va="center", zorder=13)
def circ(u, v, r, fc="white", ec="black", lw=0.4, z=5):
    ax.add_patch(Circle(W(u, v), r, fc=fc, ec=ec, lw=lw, zorder=z))
clip = SP(rect(U0, U1, V0, V1, 12))

C = dict(kit="#F0B98A", hare="#F7D3B0", doma="#EFE6D2", strait="#D9CBB4", med="#F7F3EA", off="#E9DCC4", hall="#E3C08D",
         two="#C5DE9A", roof="#F4EBDD", glass="#3d7fb0", wood="#8a5a2b", plaza="#EEDFC6", wet="#D5EBEE")

# ---------------------------------------------------------------- outside: plaza edge, lean-to, walk
poly(SP(rect(U0, 21, V0, 0, 8)).difference(WB).intersection(clip), C["plaza"], "none", 0, 0.5)
fill(U0, 21, -2.8, 0, "#DCD3C3", 0.6)                                      # walk (洗い出し)
box(19.0, 21.0, -10.0, 0.0, fc="none", ec="#555555", lw=0.6, z=8, ls=(0, (5, 2.5)))   # 下屋 (overhead)
for v in (-9.7, -6.4, -3.1, -0.3): box(19.18, 19.32, v - 0.07, v + 0.07, fc="black", ec="black", z=9)
for (va, vb) in [(-9.0, -7.2), (-6.6, -4.8)]: box(19.6, 20.5, va, vb, fc="#B98E5E", ec=C["wood"])
box(19.3, 20.8, -9.95, -9.5, fc="#8a6a44", ec="none")
T(18.4, -6.0, "ひろば", 8, c="#8a5a2b", weight="bold")

# ---------------------------------------------------------------- west building (south part)
poly(WB.intersection(clip), "#F6E3A4", "none", 0, 1)
kit = SP(rect(21, 27, -3.4, -20, 8)).intersection(WB); poly(kit, C["kit"], "none", 0, 1.2)
hare = SP(rect(27, 30, -3.4, -20, 8)).intersection(WB); poly(hare, C["hare"], "none", 0, 1.2)
poly(SP(rect(22.5, 31.6, -0.9, -3.4, 8)).intersection(WB), C["doma"], "none", 0, 1.2)
poly(SP(rect(21, 22.5, -0.9, -3.4, 4)).intersection(WB), C["strait"], "none", 0, 1.3)
poly(WB.intersection(clip), "none", "black", 1.2, 6)
for ln in [[(27, -3.4), (27, -14)], [(30, -3.4), (30, -14)], [(21, -3.4), (31.6, -3.4)]]:
    g = SP(rect(min(ln[0][0], ln[1][0]) - 0.06, max(ln[0][0], ln[1][0]) + 0.06, min(ln[0][1], ln[1][1]) - 0.06, max(ln[0][1], ln[1][1]) + 0.06, 6)).intersection(WB)
    poly(g, "#333333", "none", 0, 6)
# entrance (u = 21): sliding doors 1.8, glass across the gap, lunch window, kitchen glass
line([(21, -0.95), (21, -2.75)], lw=3.0, c="white", z=7)
line([(20.97, -0.95), (20.97, -1.9)], lw=0.8, c="#555555", z=7.1); line([(21.03, -1.8), (21.03, -2.75)], lw=0.8, c="#555555", z=7.1)
line([(21, -0.15), (21, -0.85)], lw=1.4, c=C["glass"], z=7)
line([(21, -3.5), (21, -4.4)], lw=2.6, c="#D85A30", z=7)
line([(21, -4.6), (21, -9.6)], lw=1.4, c=C["glass"], z=7)
# 框 between the strait (土足) and the barefoot doma; gap glazing at u 22.5 (north side of the link)
line([(22.5, -3.4), (22.5, -0.9)], lw=1.2, c=C["wood"], z=7)
line([(22.5, -0.15), (22.5, -0.85)], lw=1.2, c=C["glass"], z=7)
fill(21, 22.5, -0.9, -0.2, C["strait"], 1.4)

# kitchen (rough): 検収 → 下処理 → 加熱 → 盛り付け → 配膳口 ／ 返却口 → 洗浄 → 保管
box(21.55, 22.45, -9.9, -10.8, fc="white"); T(22.0, -10.35, "検収", 4.6)
box(24.6, 26.9, -11.6, -12.95, fc="#E8DCC8", lw=0.6); T(25.75, -12.27, "食品庫", 5.2)
box(23.6, 24.45, -11.85, -12.7, fc="white"); T(24.02, -12.27, "冷蔵\n冷凍", 3.8)
box(21.15, 21.8, -6.6, -9.4, fc="#EAF4F6"); T(21.48, -8.2, "下処理\nシンク", 4.2)
box(22.1, 22.8, -6.9, -9.5, fc="white"); T(22.45, -8.2, "下処理台", 4.2)
box(23.4, 25.0, -6.8, -9.8, fc="white", lw=0.6); box(23.3, 25.1, -6.6, -10.0, fc="none", ec="#777777", ls=(0, (4, 2)), z=8)
circ(24.2, -7.6, 0.4, fc="#EEEEEE"); T(24.2, -7.6, "釜", 4.2)
box(23.6, 24.8, -8.4, -9.6, fc="#EEEEEE"); T(24.2, -9.0, "レンジ", 4.2)
box(25.3, 26.1, -10.2, -11.1, fc="#EEEEEE"); T(25.7, -10.65, "スチコン", 4.0)
box(22.6, 24.4, -4.0, -5.4, fc="white"); T(23.5, -4.7, "盛り付け", 4.6)
line([(22.7, -3.4), (24.3, -3.4)], lw=3.0, c="#2E8B57", z=7.2)        # 配膳口
line([(24.6, -3.4), (25.4, -3.4)], lw=3.0, c="#9B59B6", z=7.2)        # 返却口
box(24.6, 26.6, -4.9, -6.3, fc="#EAF4F6"); T(25.6, -5.6, "下膳・洗浄", 4.6)
box(26.3, 26.94, -6.6, -9.6, fc="white"); T(26.62, -8.1, "保管庫", 4.0, rotation=90)
box(25.6, 26.94, -3.5, -4.8, fc="#F2F2F2", lw=0.6); T(26.27, -4.15, "前室", 4.4)
line([(26.94, -3.4), (26.94, -3.4)], lw=0)
box(21.15, 22.3, -3.5, -6.2, fc="#FFF4E8"); T(21.72, -5.2, "離乳食・\nアレルギー", 4.0)
box(21.15, 21.5, -3.5, -4.4, fc="#F6C9A8", lw=0.3);
box(22.7, 23.4, -10.6, -11.5, fc="white"); T(23.05, -11.05, "机", 4.2)
line([(27, -7.0), (27, -9.0)], lw=2.0, c="#F2D7B0", z=7)               # 見える台所（はれのまへの受け渡し）
# back door (SW corner, 勝手口)
bd = [W(21.06, -10.49), W(21.38, -11.41)]
ax.plot([bd[0][0], bd[1][0]], [bd[0][1], bd[1][1]], lw=3, color="white", zorder=7); ax.plot([bd[0][0], bd[1][0]], [bd[0][1], bd[1][1]], lw=0.9, color="#555555", zorder=7.1)

# はれのま（仮）: big table, kids' cooking counter + low sink, seasonal shelf, door from the doma
box(28.0, 29.0, -6.0, -10.6, fc="white", lw=0.6)
for v in np.arange(-6.3, -10.6, -0.7):
    for u in (27.6, 29.4): box(u - 0.17, u + 0.17, v - 0.17, v + 0.17, lw=0.3)
box(27.1, 27.6, -10.9, -12.8, fc="#EAF4F6"); T(27.35, -11.85, "子どもの\n流し", 3.8)
box(29.45, 29.94, -11.0, -12.8, fc="#E8DCC8"); T(29.7, -11.9, "季節の棚", 3.8, rotation=90)
line([(30, -6.2), (30, -9.8)], lw=0, c="none")
line([(28.0, -3.4), (29.3, -3.4)], lw=3.0, c="white", z=7); line([(28.0, -3.42), (29.3, -3.42)], lw=0.6, c="#555555", ls=(0, (2, 1)), z=7.1)

# doma (barefoot) north of the 框: carts parking
for u in (23.3, 24.3): box(u, u + 0.8, -1.4, -2.6, fc="#DDDDDD", lw=0.4)
T(23.9, -2.0, "", 4)

# ---------------------------------------------------------------- main building: spans 6–10
fill(U0, 18, 1.6, 12, C["two"]); fill(U0, 18, 0, 1.6, C["roof"])
fill(18, 21, 0, 4.5, C["off"]); fill(18, 21, 4.5, 12, C["med"])
fill(21, 22.5, -0.2, 13.5, C["strait"], 1.4)
fill(22.5, U1, 1.6, 12, C["hall"]); fill(22.5, U1, 0, 1.6, C["roof"])
fill(U0, 21, 12, 15, C["roof"]); fill(22.5, U1, 12, 15, C["roof"]); fill(21, 22.5, 13.5, 15, C["strait"])
line([(U0, 13.5), (21, 13.5)], lw=1.2, c=C["glass"]); line([(22.5, 13.5), (U1, 13.5)], lw=1.2, c=C["glass"])
line([(U0, 15), (U1, 15)], lw=0.4, c="#777777", ls=(0, (6, 3)))
wall(U0, U1, -0.08, 0.08)                                                  # west outer wall (spine)
for uf in range(18, 32, 3):
    for vc in (0, 12): box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, fc="black", ec="black", z=7)
wall(17.95, 18.07, 1.2, 12.0)                                              # 2-yr / span 7
wall(18.07, 21.0, 4.45, 4.57)                                              # 事務 / 医務
line([(19.0, 4.51), (19.9, 4.51)], lw=2.6, c="white", z=7); line([(19.0, 4.6), (19.9, 4.6)], lw=0.5, z=7.1)
line([(21, 0.08), (21, 0.6)], lw=1.6, c="#333333", z=6); line([(21, 2.6), (21, 2.85)], lw=1.6, c="#333333", z=6)
line([(21, 4.15), (21, 12)], lw=1.6, c="#333333", z=6)                    # north wall of span 7 (to the strait)
line([(21, 0.6), (21, 2.6)], lw=1.4, c=C["glass"], z=6)                    # reception window to the strait
line([(22.5, 1.6), (22.5, 12)], lw=0.6, c="#777777", ls=(0, (2, 1.5)), z=6)  # strait / hall (飛び石の床の切り替え)
circ(21.75, 6.5, 0.45, fc="#BFAF95", lw=0.3)                               # stepping stone
# west windows of 事務 (to the walk, 手水 and entrance)
line([(18.6, 0), (20.8, 0)], lw=1.4, c=C["glass"], z=7)
# 事務: desk at the west window, chairs, shelf, phone/monitor
box(18.7, 20.8, 0.12, 0.8, fc="white"); circ(19.3, 1.15, 0.22); circ(20.2, 1.15, 0.22)
box(18.1, 18.5, 1.9, 4.4, fc="#E8DCC8"); T(18.3, 3.15, "棚", 4.2)
box(20.3, 20.95, 0.6, 2.6, fc="none", ec="#555555", lw=0.3, ls=(0, (2, 1)))
# 医務: 2 beds (one behind a curtain), hand wash, nurse desk, door to the inner engawa
for u0 in (18.2, 19.75):
    box(u0, u0 + 0.75, 9.6, 11.5, fc="white", lw=0.5); box(u0 + 0.1, u0 + 0.65, 11.0, 11.4, fc="#EEF3F6", lw=0.3)
line([(19.45, 8.8), (19.45, 11.9)], lw=0.6, c="#A06AB4", ls=(0, (3, 1.5)), z=7)  # curtain
box(18.1, 18.6, 4.7, 5.5, fc=C["wet"]); T(18.35, 5.1, "手洗", 3.8)
box(20.3, 20.95, 5.0, 6.6, fc="white"); T(20.62, 5.8, "机", 4.0)
box(18.1, 18.45, 6.0, 8.2, fc="#E8DCC8"); T(18.27, 7.1, "薬", 3.8)
line([(19.6, 12), (20.5, 12)], lw=2.6, c="white", z=7)
T(19.5, 2.9, "事務", 7, weight="bold"); T(19.6, 7.6, "医務", 7, weight="bold")
T(17.2, 6.0, "2歳", 7, c="#3d5a1a"); T(26.0, 7.0, "ホール", 8); T(21.75, 10.0, "海峡", 5.6, rotation=90)
T(24.0, -8.2 + 0.0, "", 4)
T(25.2, -6.0 + 0, "", 4)
T(23.6, -11.3, "キッチン", 8, weight="bold"); T(28.5, -5.0, "はれのま（仮）", 7, weight="bold")
T(27.0, -2.1, "西館の土間（はだし）", 5.4)
T(29.5, 13.0, "縁側", 5.4, c="#777777"); T(31.0, -8.0, "遊戯室 ↑", 6)

# the food route and the 2-yr route through 事務 (curving, behind the desk)
route = [(22.0, -2.0), (21.75, -1.0), (21.75, 3.5), (20.6, 3.5), (19.4, 2.4), (18.6, 1.6), (18.0, 0.6), (U0 + 0.2, 0.6)]
pts = [W(u, v) for u, v in route]
ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=1.3, color="#2E8B57", ls=(0, (3, 2)), zorder=11)
ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, color="#2E8B57", lw=1.3, zorder=11))
kids = [(20.0, -1.6), (20.9, -1.85), (21.6, -1.6), (21.75, 0.5), (21.75, 13.0)]
pts = [W(u, v) for u, v in kids]
ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=1.3, color="#8a5a2b", ls=(0, (3, 2)), zorder=11)
ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, color="#8a5a2b", lw=1.3, zorder=11))

# frames (south-based) and spans
for k in range(7, 12):
    u = 3 * (k - 1)
    x, y = W(u, -15.0); ax.text(x, y, f"架構{k}", fontsize=5.2, ha="center", va="center", rotation=0)
for k in range(6, 11):
    T(3 * (k - 1) + 1.5, 15.35, f"スパン{k}", 4.8, c="#666666")

# numbers
NUMS = [(21.0, -1.85, 1), (22.0, -2.4, 2), (21.0, -3.95, 3), (21.0, -7.1, 4), (22.0, -10.35, 5), (23.5, -3.4, 6), (25.0, -3.4, 7),
        (27.0, -8.0, 8), (28.5, -8.3, 9), (27.35, -10.4, 10), (24.0, -2.0, 11), (19.6, 0.5, 12), (21.0, 1.6, 13), (19.9, 3.9, 14),
        (19.3, 10.3, 15), (20.05, 12.0, 16), (19.9, -8.1, 17)]
for u, v, k in NUMS: num(u, v, k)

# north arrow, scale
nx, ny = W(30.2, 14.4)
nv = np.array(rot((0, 1))) - np.array(rot((0, 0)))
ax.annotate("", xy=(nx + nv[0] * 1.2, ny + nv[1] * 1.2), xytext=(nx, ny), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
ax.text(nx + nv[0] * 1.6, ny + nv[1] * 1.6, "N", fontsize=8, ha="center", va="center")
sx, sy = xmin + 0.6, ymin + 0.4
for i in range(5):
    ax.add_patch(Polygon([(sx + i, sy), (sx + i + 1, sy), (sx + i + 1, sy + 0.15), (sx + i, sy + 0.15)], fc="black" if i % 2 == 0 else "white", ec="black", lw=0.3, zorder=12))
ax.text(sx, sy - 0.35, "0", fontsize=5, ha="center"); ax.text(sx + 5, sy - 0.35, "5 m", fontsize=5, ha="center")

# ---------------------------------------------------------------- text
fig.text(PL / 420, 287 / 297, "育ち舎　南の入口まわり（キッチン・はれのま・事務・医務）　ラフ", fontsize=13, weight="medium", va="top")
a_kit, a_hare = kit.area, hare.area
a_off = SP(rect(18, 21, 0, 4.5)).area; a_med = SP(rect(18, 21, 4.5, 12)).area
fig.text(PL / 420, 279.5 / 297, f"1/100（A3）　2026-10-21　架構の番号は南から（架構 k は南の妻から 3(k−1) m、スパン k は架構 k と k+1 のあいだ）。"
         f"面積（芯々、概算）：キッチン {a_kit:.0f} m²　はれのま {a_hare:.0f} m²　事務（スパン7 の西）{a_off:.0f} m²　医務 {a_med:.0f} m²＋内縁側",
         fontsize=6.4, va="top", color="#444444")
leg = ["1　入口（西館の南の面、引き戸 1.8）。すき間はガラス", "2　海峡の延長（土足 −150）。框から北ははだしの土間", "3　「今日のごはん」の窓（子どもの高さ、中は見本の棚）",
       "4　キッチンの南のガラス（下処理が見える）", "5　検収（勝手口のすぐ内側）", "6　配膳口（盛り付け → ワゴン）", "7　返却口（配膳口と分ける、一方通行）",
       "8　見える台所（はれのまへの受け渡しの窓）", "9　はれのまの大きな机（10〜12 人）", "10　子どもの流しと調理台（食育）",
       "11　配膳のワゴン置き場（土間）", "12　事務の机（西の窓：小径の出口・手水・ひろば・入口が見える）", "13　受付の窓（海峡に向く）",
       "14　医務への戸（事務から）", "15　ベッド×2（カーテンで分ける、静養・隔離）", "16　医務の戸（内縁側から、先生が子どもを連れてくる）", "17　下屋の下の縁台"]
for i, s in enumerate(leg):
    c, r = divmod(i, 6)
    fig.text((PL + 132 * c) / 420, (70 - 4.6 * r) / 297, s, fontsize=6.2, va="top")
fig.text(PL / 420, 38 / 297, "┅ 緑：配膳の保育士と 2 歳の道（海峡 → 事務を曲がりながら抜ける → 2 歳の道）。┅ 茶：3〜5 歳（入口 → 海峡 → 縁側）。"
         "キッチンは 検収 → 下処理 → 加熱 → 盛り付け → 配膳口、返却口 → 洗浄 → 保管 の一方通行。破線の箱はフード・下屋（頭上）。", fontsize=6.2, va="top", color="#444444")
fig.savefig(os.path.join(OUT, "sodachiya_05_south_entry.pdf"))
fig.savefig(os.path.join(OUT, "sodachiya_05_south_entry.png"), dpi=200)
print("areas", round(a_kit, 1), round(a_hare, 1), round(a_off, 1), round(a_med, 1))
