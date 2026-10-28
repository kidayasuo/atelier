# 南の入口まわり1/100（ラフ）：キッチン・はれのま（仮）・西館の土間・海峡の延長・入口・スパン7（窓口の帯・静養室・医務）
# スパン7の中身は3dm（add_hall.pyの「スパン7」の節、本館係10-23夜）に合わせる。
# 座標は本館の (u, v)。架構の番号は南から（架構kはu = 3(k−1)、スパンkは架構kとk+1のあいだ）。
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
         two="#C5DE9A", rest="#F3EEF5", roof="#F4EBDD", glass="#3d7fb0", wood="#8a5a2b", plaza="#EEDFC6", wet="#D5EBEE")

# ---------------------------------------------------------------- outside: plaza edge, lean-to, walk
poly(SP(rect(U0, 21, V0, 0, 8)).difference(WB).intersection(clip), C["plaza"], "none", 0, 0.5)
fill(U0, 21, -2.8, 0, "#DCD3C3", 0.6)                                      # walk (洗い出し)
box(19.0, 21.0, -10.0, 0.0, fc="none", ec="#555555", lw=0.6, z=8, ls=(0, (5, 2.5)))   # 下屋 (overhead)
for v in (-9.7, -6.4, -3.1, -0.3): box(19.18, 19.32, v - 0.07, v + 0.07, fc="black", ec="black", z=9)
for (va, vb) in [(-9.0, -7.2), (-6.6, -4.8)]: box(19.6, 20.5, va, vb, fc="#B98E5E", ec=C["wood"])
box(19.3, 20.8, -9.95, -9.5, fc="#8a6a44", ec="none"); circ(20.5, -9.72, 0.12, fc="#D85A30", lw=0.3)
T(18.4, -6.0, "ひろば", 8, c="#8a5a2b", weight="bold")

# ---------------------------------------------------------------- west building (south part)
poly(WB.intersection(clip), "#F6E3A4", "none", 0, 1)
KN = 27.25                                                                 # kitchen north wall (60 m² net)
kit = SP(rect(21, KN, -3.4, -20, 8)).intersection(WB); poly(kit, C["kit"], "none", 0, 1.2)
CB = -11.1                                                                 # cooks' block: from v −11.1 to the west face (west end ofはれのま)
cook = SP(rect(KN, 30, CB, -20, 6)).intersection(WB); poly(cook, "#EDEDED", "none", 0, 1.25)
store = SP(rect(KN, 30, CB + 0.6, CB, 4))                                     # はれのまの収納（西の端の壁、奥行き0.6）
hare = SP(rect(KN, 30, -3.4, -20, 8)).intersection(WB).difference(cook).difference(store)
poly(hare, C["hare"], "none", 0, 1.2)
band = SP(rect(22.5, 31.6, -0.2, -3.4, 8)).intersection(WB.union(SP(rect(22.5, 31.6, -0.2, -0.9))))
poly(SP(rect(22.5, 31.6, 0.0, -3.4, 8)), C["roof"], "none", 0, 1.2)       # east band + gap: barefoot ±0, one space with the hall
poly(SP(rect(21, 22.5, -0.2, -3.4, 4)), C["strait"], "none", 0, 1.3)
poly(WB.intersection(clip), "none", "black", 1.2, 6)
for ln in [[(KN, -3.4), (KN, -14)], [(30, -3.4), (30, -14)], [(21, -3.4), (31.6, -3.4)], [(KN, CB), (30, CB)]]:
    g = SP(rect(min(ln[0][0], ln[1][0]) - 0.06, max(ln[0][0], ln[1][0]) + 0.06, min(ln[0][1], ln[1][1]) - 0.06, max(ln[0][1], ln[1][1]) + 0.06, 6)).intersection(WB)
    poly(g, "#333333", "none", 0, 6)
# expansion joint between the two buildings (one interior space north of the strait)
line([(22.55, -0.9), (31.6, -0.9)], lw=5.0, c=C["roof"], z=6.4); line([(21.05, -0.9), (22.45, -0.9)], lw=5.0, c=C["strait"], z=6.4)          # the west building's east face is not a wall here
line([(22.5, -0.45), (31.6, -0.45)], lw=0.6, c="#777777", ls=(0, (6, 2, 1, 2)), z=6.5)
T(29.6, -0.45 + 0.0, "", 4)
# entrance (u = 21): sliding doors 1.8, glass across the gap, lunch window, kitchen glass
line([(21, -0.95), (21, -2.75)], lw=3.0, c="white", z=7)
line([(20.97, -0.95), (20.97, -1.9)], lw=0.8, c="#555555", z=7.1); line([(21.03, -1.8), (21.03, -2.75)], lw=0.8, c="#555555", z=7.1)
line([(21, -0.15), (21, -0.85)], lw=1.4, c=C["glass"], z=7)
line([(21, -3.5), (21, -4.4)], lw=2.6, c="#D85A30", z=7)
line([(21, -4.6), (21, -9.6)], lw=1.4, c=C["glass"], z=7)
# 框between the strait (土足 −150) and the barefoot band
line([(22.5, -3.4), (22.5, -0.2)], lw=1.2, c=C["wood"], z=7)

# kitchen (rough, 60 m² net): 検収 → 下処理 → 加熱 → 盛り付け → 配膳口 ／ 返却口 → 洗浄 → 保管
box(21.55, 22.45, -9.9, -10.8, fc="white"); T(22.0, -10.35, "検収", 4.6)
box(24.3, 26.5, -11.6, -12.95, fc="#E8DCC8", lw=0.6); T(25.4, -12.27, "食品庫", 5.2)
box(23.4, 24.2, -11.85, -12.7, fc="white"); T(23.8, -12.27, "冷蔵\n冷凍", 3.8)
box(21.15, 21.8, -6.6, -9.4, fc="#EAF4F6"); T(21.48, -8.0, "下処理\nシンク", 4.2)
box(22.1, 22.8, -6.9, -9.5, fc="white"); T(22.45, -8.2, "下処理台", 4.2)
box(23.4, 25.0, -6.8, -9.8, fc="white", lw=0.6); box(23.3, 25.1, -6.6, -10.0, fc="none", ec="#777777", ls=(0, (4, 2)), z=8)
circ(24.2, -7.6, 0.4, fc="#EEEEEE"); T(24.2, -7.6, "釜", 4.2)
box(23.6, 24.8, -8.4, -9.6, fc="#EEEEEE"); T(24.2, -9.0, "レンジ", 4.2)
box(25.3, 26.1, -10.2, -11.1, fc="#EEEEEE"); T(25.7, -10.65, "スチコン", 4.0)
box(22.6, 24.4, -4.0, -5.4, fc="white"); T(23.5, -4.7, "盛り付け", 4.6)
# キッチン・はれのまの東の面 v−3.4（3dm 737f681、10-28）：腰壁 h450 の上を 2 階の床の下 3170 までガラス（細い二本線）。
# 柱 u24・u27 の所とはれのまの壁の取り合いは壁、配膳口・返却口は h850〜1900 が開きその上はガラス、戸の上は欄間。
for (a0, a1) in [(21.2, 22.7), (24.1, 25.3), (26.1, 26.9), (27.3, 27.65), (28.65, 29.94)]:
    box(a0, a1, -3.46, -3.34, fc="white", ec="none", lw=0, z=7.0)
    for vg in (-3.43, -3.37): line([(a0, vg), (a1, vg)], lw=0.35, c=C["glass"], z=7.3)
for (a0, a1) in [(22.7, 23.85), (25.3, 26.1)]: box(a0, a1, -3.46, -3.34, fc="white", ec="none", lw=0, z=7.0)
line([(22.7, -3.4), (23.85, -3.4)], lw=3.0, c="#2E8B57", z=7.2)       # 配膳口（h850〜1900、上はガラス）
line([(25.3, -3.4), (26.1, -3.4)], lw=3.0, c="#9B59B6", z=7.2)        # 返却口（h850〜1900、上はガラス）
box(25.2, 26.4, -3.6, -5.4, fc="#EAF4F6"); T(25.8, -4.5, "下膳・\n洗浄", 4.4)
for _uc in (24.0, 27.0): box(_uc - 0.09, _uc + 0.09, -3.2, -3.6, fc="#333333", lw=0.3, z=8)   # 2 階の床梁を受ける骨格の柱 180×400（10-27）
box(26.5, 27.15, -5.6, -7.4, fc="white"); T(26.82, -6.5, "保管", 4.0, rotation=90)
box(21.15, 22.3, -3.5, -6.2, fc="#FFF4E8"); T(21.72, -5.2, "離乳食・\nアレルギー", 4.0)
box(21.15, 21.5, -3.5, -4.4, fc="#F6C9A8", lw=0.3)
box(22.6, 23.3, -10.6, -11.5, fc="white"); T(22.95, -11.05, "机", 4.2)
line([(KN, -7.8), (KN, -9.6)], lw=2.0, c="#F2D7B0", z=7)              # 見える台所（はれのまへの受け渡し）
bd = [W(21.06, -10.49), W(21.38, -11.41)]
ax.plot([bd[0][0], bd[1][0]], [bd[0][1], bd[1][1]], lw=3, color="white", zorder=7); ax.plot([bd[0][0], bd[1][0]], [bd[0][1], bd[1][1]], lw=0.9, color="#555555", zorder=7.1)
# cooks' block at the west end ofはれのま, with its own door to the outside (west face, road side, outside the line)
# outside → 更衣 → 前室（手洗い・長靴）→ kitchen (NW corner) ; 便所off更衣
line([(28.25, CB - 0.06), (28.25, -13.25)], lw=1.2, c="#333333", z=6.6)    # 前室・便所 | 更衣
line([(KN + 0.06, -12.2), (28.25, -12.2)], lw=1.2, c="#333333", z=6.6)    # 前室 | 便所
line([(KN, -11.25), (KN, -11.95)], lw=3.0, c="white", z=7)                # 前室 → kitchen
line([(28.25, -11.3), (28.25, -11.95)], lw=3.0, c="white", z=7)           # 更衣 → 前室
line([(28.25, -12.4), (28.25, -12.95)], lw=3.0, c="white", z=7)           # 更衣 → 便所
ed = [W(28.5, -13.33), W(29.3, -13.4)]                                     # outside door (west face)
ax.plot([ed[0][0], ed[1][0]], [ed[0][1], ed[1][1]], lw=3, color="white", zorder=7); ax.plot([ed[0][0], ed[1][0]], [ed[0][1], ed[1][1]], lw=0.9, color="#555555", zorder=7.1)
box(29.55, 29.94, -11.3, -13.0, fc="#E8DCC8", lw=0.3)                        # lockers
box(27.35, 28.1, -11.2, -11.6, fc=C["wet"], lw=0.3)                          # hand wash
ax.add_patch(Ellipse(W(27.75, -12.85), 0.38, 0.5, fc="white", ec="black", lw=0.35, zorder=5))
T(27.75, -11.85, "前室", 4.0); T(29.0, -12.0, "更衣", 4.6); T(27.75, -12.45, "便所", 3.8)
# はれのまの収納（西の端の壁）: 延長保育の道具・食育の道具・季節の棚（真ん中を飾り棚に）
poly(store, "#E8DCC8", "#777777", 0.4, 4)
box(28.3, 29.0, CB + 0.6, CB + 0.1, fc="#F6EFE0", lw=0.3); T(28.65, CB + 0.35, "季節の棚", 3.6)
T(27.75, CB + 0.3, "収納", 3.8); T(29.5, CB + 0.3, "延長の箱", 3.6)

# はれのま（仮）: counter along the kitchen wall (h600, kids' sink, pass window), table 0.8 wide, door from the band
box(KN + 0.02, KN + 0.42, -3.6, -10.4, fc="#F2E6D4", lw=0.5)
box(KN + 0.06, KN + 0.38, -9.2, -10.2, fc="#EAF4F6", lw=0.3); T(KN + 0.22, -9.7, "流し", 3.6, rotation=90)
box(28.15, 28.95, -5.0, -9.8, fc="white", lw=0.6)
for v in np.arange(-5.4, -9.8, -0.8):
    for u in (27.9, 29.2): box(u - 0.17, u + 0.17, v - 0.17, v + 0.17, lw=0.3)
box(27.65, 28.65, -3.46, -3.34, fc="white", ec="none", lw=0, z=7.0)        # はれのまの戸（h2100、上は欄間）
line([(27.68, -3.37), (28.2, -3.37)], lw=0.8, c="#555555", z=7.1); line([(28.13, -3.43), (28.62, -3.43)], lw=0.8, c="#555555", z=7.1)
ax.add_patch(Circle(W(28.6, -7.0), 0.45, fc="none", ec="#555555", lw=0.5, ls=(0, (3, 2)), zorder=9))   # 天井扇 φ0.9（8ed33f3）

# 生ごみの受け取り台（連携10-21夜5の3）：返却口の北隣、東の帯の側に低い台h500（奥行き0.4）。
# 3〜5歳のコンポスト当番がふた付きのバケツを受け取る（こどもはキッチンに入らない）。キッチンの側からは返却口・洗浄の側で渡す＝汚れ物の流れのまま。
box(26.2, 26.85, -3.38, -2.98, fc="#D8C9A8", lw=0.5); line([(26.25, -3.4), (26.8, -3.4)], lw=3.0, c="#7A8B3A", z=7.25)   # 台と受け渡しの小窓
circ(26.82, -3.18, 0.13, fc="#7A8B3A", lw=0.3)                                                                            # ふた付きのバケツ
# east band (barefoot): carts
for u in (23.3, 24.3): box(u, u + 0.8, -1.4, -2.6, fc="#DDDDDD", lw=0.4)

# ---------------------------------------------------------------- main building: spans 6–10
fill(U0, 18, 1.6, 12, C["two"]); fill(U0, 18, -0.2, 1.6, C["roof"])
fill(18, 21, -0.2, 1.6, C["off"]); fill(18, 21, 1.6, 4.5, C["rest"]); fill(18, 21, 4.5, 12, C["med"])
fill(21, 22.5, -0.2, 13.5, C["strait"], 1.4)
fill(22.5, U1, 1.6, 12, C["hall"]); fill(22.5, U1, -0.2, 1.6, C["roof"])
fill(U0, 21, 12, 15, C["roof"]); fill(22.5, U1, 12, 15, C["roof"]); fill(21, 22.5, 13.5, 15, C["strait"])
line([(U0, 13.5), (21, 13.5)], lw=1.2, c=C["glass"]); line([(22.5, 13.5), (U1, 13.5)], lw=1.2, c=C["glass"])
line([(U0, 15), (U1, 15)], lw=0.4, c="#777777", ls=(0, (6, 3)))
wall(U0, 21, -0.35, -0.20)                                                  # west outer wall（柱の外、v −0.35〜−0.20）: only south of the strait (north of it the hall opens to the west building)
for uf in range(18, 32, 3):
    for vc in (0, 12): box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, fc="black", ec="black", z=7)
wall(17.95, 18.07, 1.2, 12.0)                                              # 2-yr / span 7
wall(18.07, 21.0, 4.45, 4.57)                                              # 静養室 / 医務
line([(19.0, 4.51), (20.4, 4.51)], lw=2.6, c="white", z=7); line([(19.0, 4.6), (20.4, 4.6)], lw=0.5, ls=(0, (2, 1)), z=7.1)   # 医務との戸（引き分け戸）
line([(21, 4.45), (21, 12)], lw=1.6, c="#333333", z=6)                    # 医務｜海峡（閉じる）
wall(18.07, 18.6, 1.54, 1.66); wall(20.2, 21.0, 1.54, 1.66)                # 窓口の帯｜静養室
line([(18.6, 1.6), (20.2, 1.6)], lw=1.4, c=C["glass"], z=7)                # 室内窓（h0.9〜2.0、先生が見守る）
line([(21, 1.6), (21, 3.0)], lw=1.6, c="#333333", z=6); line([(21, 3.9), (21, 4.45)], lw=1.6, c="#333333", z=6)   # 静養室｜海峡
line([(21.06, 3.0), (21.06, 3.9)], lw=0.8, c="#555555", z=7.1)            # 戸（お迎えの保護者へ、片引き戸）
box(20.60, 20.95, 0.95, 1.55, fc="#E8DCC8", lw=0.5)                        # おはようの窓口: low counter, open to the strait
circ(20.25, 1.25, 0.2)                                                     # 先生の腰掛け
line([(22.5, 0.0), (22.5, 12)], lw=0.9, c=C["wood"], z=6)                 # 框: strait (−150) / hall (±0)
_t = np.linspace(0, 2 * math.pi, 40)
poly([W(21.75 + 0.2 * math.sin(a) * (1 - 0.15 * math.cos(a) ** 2), 0.8 + 0.5 * math.cos(a)) for a in _t], "#BFAF95", "#6b5a3a", 0.4, 6)   # 飛び石: lens 0.4 × 1.0 along the flow (top ±0, whaleback edges)
poly([W(21.75 + 0.12 * math.sin(a), 0.8 + 0.3 * math.cos(a)) for a in _t], "#CDBFA6", "none", 0, 6.1)
T(21.0 - 0.0, 3.4, "", 4)
# west window of the帯 (to the walk, 手水and entrance)
line([(18.6, -0.275), (20.8, -0.275)], lw=1.4, c=C["glass"], z=7)
# 静養室: こども用ベッド0.7×1.4 ×2（戸で閉じ、天井を張って換気は別、窓口の帯から室内窓）
for u0 in (18.10, 19.00):
    box(u0, u0 + 0.7, 1.75, 3.15, fc="white", lw=0.5); box(u0 + 0.08, u0 + 0.62, 2.75, 3.08, fc="#EEF3F6", lw=0.3)
# 静養室の換気扇（本館係 10-23夜16：天井（梁の下端）から真上へダクト、屋根の上の換気の頭へ。給気は戸の下のすき間から）
circ(19.5, 3.0, 0.22, fc="white", ec="#555555", lw=0.5)
for d_ in (-1, 1): line([(19.5 - 0.15, 3.0 - 0.15 * d_), (19.5 + 0.15, 3.0 + 0.15 * d_)], lw=0.5, c="#555555", z=6)
# 医務: 手当て・診察の台、手洗い、保健師の机、内縁側への戸
box(18.2, 18.95, 9.6, 11.5, fc="white", lw=0.5)
box(18.1, 18.6, 4.7, 5.5, fc=C["wet"]); T(18.35, 5.1, "手洗", 3.8)
box(20.3, 20.95, 5.0, 6.6, fc="white"); T(20.62, 5.8, "机", 4.0)
box(18.1, 18.45, 6.0, 8.2, fc="#E8DCC8"); T(18.27, 7.1, "薬", 3.8)
line([(19.6, 12), (20.5, 12)], lw=2.6, c="white", z=7)
T(19.2, 0.75, "窓口の帯", 5.6, weight="bold"); T(20.2, 3.6, "静養室", 6, weight="bold"); T(19.6, 7.6, "医務", 7, weight="bold")
T(17.2, 6.0, "2歳", 7, c="#3d5a1a"); T(26.0, 7.0, "ホール", 8); T(21.75, 10.0, "海峡", 5.6, rotation=90)
T(24.0, -8.2 + 0.0, "", 4)
T(25.2, -6.0 + 0, "", 4)
T(23.6, -11.3, "キッチン", 8, weight="bold"); T(28.6, -9.0 + 2.2, "", 4); T(28.55, -4.3, "はれのま（仮）", 6.4, weight="bold")
T(27.6, -2.15, "西館の東の帯（はだし ±0、ホールと一続き）", 4.8, rotation=90)
T(29.5, 13.0, "縁側", 5.4, c="#777777"); T(31.0, -8.0, "遊戯室 ↑", 6)

# the food route and the 2-yr route through事務 (curving, behind the desk)
route = [(23.5, -3.0), (23.5, -1.0), (23.0, 0.5), (22.2, 0.8), (21.75, 0.8), (21.2, 0.5), (20.2, 0.45), (18.6, 0.45), (18.0, 0.6), (U0 + 0.2, 0.6)]
pts = [W(u, v) for u, v in route]
ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=1.3, color="#2E8B57", ls=(0, (3, 2)), zorder=11)
ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, color="#2E8B57", lw=1.3, zorder=11))
kids = [(20.0, -1.6), (20.9, -1.85), (21.6, -1.6), (21.75, 0.5), (22.15, 2.6), (22.15, 4.2), (21.75, 5.5), (21.75, 13.0)]
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
NUMS = [(21.0, -1.85, 1), (22.0, -2.4, 2), (21.0, -3.95, 3), (21.0, -7.1, 4), (22.0, -10.35, 5), (23.5, -3.4, 6), (26.0, -3.0, 7),
        (KN, -8.7, 8), (28.55, -8.6, 9), (KN + 0.22, -6.0, 10), (24.0, -2.0, 11), (18.6, 1.15, 12), (20.78, 1.9, 13), (19.7, 4.5, 14),
        (19.55, 2.45, 15), (20.05, 12.0, 16), (19.9, -8.1, 17), (29.0, -12.6, 18), (22.35, 1.35, 19), (29.0, -10.3, 20), (25.0, -3.4, 21), (26.82, -2.75, 22), (21.3, 3.45, 23), (19.5, 3.55, 24)]
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
fig.text(PL / 420, 287 / 297, "育ち舎　南の入口まわり（キッチン・はれのま・窓口の帯・静養室・医務）　ラフ", fontsize=13, weight="medium", va="top")
a_kit, a_hare = kit.area, hare.area
a_off = SP(rect(18, 21, -0.2, 1.6)).area; a_rest = SP(rect(18, 21, 1.6, 4.5)).area; a_med = SP(rect(18, 21, 4.5, 12)).area
fig.text(PL / 420, 279.5 / 297, f"1/100（A3）　2026-10-29　架構の番号は南から（架構kは南の妻から3(k−1) m、スパンkは架構kとk+1のあいだ）。"
         f"面積（芯々、概算）：キッチン {a_kit:.0f} m²　はれのま {a_hare:.0f} m²　窓口の帯 {a_off:.1f} m²　静養室 {a_rest:.1f} m²　医務 {a_med:.0f} m²",
         fontsize=6.4, va="top", color="#444444")
leg = ["1　入口（西館の南の面、引き戸1.8）。すき間はガラス", "2　海峡の延長（土足 −150）。框から北は東の帯（はだし ±0）", "3　「今日のごはん」の窓（子どもの高さ、中は見本の棚）",
       "4　キッチンの南のガラス（下処理が見える）", "5　検収（勝手口のすぐ内側）", "6　配膳口（盛り付け → ワゴン）", "7　返却口（配膳口と分ける、一方通行）",
       "8　見える台所（はれのまへの受け渡しの窓）", "9　はれのまの机（幅0.8、12人）", "10　キッチン沿いのカウンターh600（子どもの流し・おやつの台・食育）",
       "11　配膳のワゴン置き場（東の帯）", "12　窓口の帯（受付・見守り、西の窓から小径の出口・手水・入口が見える。机仕事はスパン11の記録・連絡の机）", "13　おはようの窓口（低いカウンター、海峡に向く）。前に飛び石",
       "14　静養室と医務のあいだの戸（保健師が看る）", "15　静養室（こども用ベッド×2、戸で閉じ換気は別、窓口の帯から室内窓h0.9〜2.0）", "16　医務の戸（内縁側から、先生が子どもを連れてくる）", "17　下屋の下の縁台とお茶の棚（電気ポットはh1100の棚の上：給湯ロック・転倒湯もれ防止・蒸気レス・マグネットプラグ）",
       "18　調理の職員の更衣・便所・前室（外から直接：西の面の戸 → 更衣 → 前室 → キッチン）", "19　飛び石（窓口の帯の正面、流れに沿うレンズ形0.4×1.0、上面は床の高さ）", "20　はれのまの収納（西の端の壁、延長の箱・季節の棚）",
       "21　東の面：腰壁h450の上を2階の床の下までガラス（二本線、戸の上は欄間）。破線の円は天井扇φ0.9",
       "22　生ごみの受け取り台（返却口の隣、東の帯の側h500。3〜5歳のコンポスト当番がふた付きのバケツを受け取る）",
       "23　静養室の戸（海峡へ、お迎えの保護者が迎えに来る）", "24　静養室の換気扇（天井から真上へ、屋根の上の換気の頭。給気は戸の下から）"]
for i, s in enumerate(leg):
    c, r = divmod(i, 8)
    fig.text((PL + 132 * c) / 420, (74 - 4.3 * r) / 297, s, fontsize=5.8, va="top")
fig.text(PL / 420, 35 / 297, "┅ 緑：配膳の保育士と2歳の道（配膳口 → 東の帯 → ホールの西 → 飛び石で海峡を渡る → 窓口の帯を抜ける → 2歳の道）。┅ 茶：3〜5歳（入口 → 海峡 → 縁側、おはようの窓口の前を通る）。"
         "キッチンは 検収 → 下処理 → 加熱 → 盛り付け → 配膳口、返却口 → 洗浄 → 保管 の一方通行。\n"
         "西館の東の帯とすき間は、エキスパンションをはさんでホールと一続き（はだし ±0）。本館の西の壁はホールの範囲では開く。"
         "はれのまの日常：朝夕の延長保育（キッチンが近く、補食・おやつ）、5歳のお手伝い当番・おやつづくり、3〜5歳がクラスごとに順番に食べる日。ときどき：誕生会・行事食・保護者の試食会・離乳食の相談。", fontsize=6.2, va="top", color="#444444", linespacing=1.6)
fig.savefig(os.path.join(OUT, "sodachiya_05_south_entry.pdf"))
fig.savefig(os.path.join(OUT, "sodachiya_05_south_entry.png"), dpi=200)
print("areas", round(a_kit, 1), round(a_hare, 1), round(a_off, 1), round(a_med, 1))
