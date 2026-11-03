# 南の入口まわり1/100（ラフ）：キッチン・遊戯室の入り口（スパン10、10-29 夜まではれのま）・西館の土間・あまのがわの延長・入口・スパン7（窓口の帯・静養室・医務）
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
import json
from scipy.interpolate import PchipInterpolator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import fonts42   # 文字は文字のまま（Type42）、図はPDFだけ

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
# あまのがわの北の縁（本館係の data/amanogawa.json、案4：(v, 幅) を PCHIP で結ぶ。南の縁は u21 でまっすぐ）
_AM = json.load(open(os.path.join(ROOT, "data", "amanogawa.json")))
_amf = PchipInterpolator([p[0] for p in _AM["CONTROL"]], [p[1] for p in _AM["CONTROL"]])
AM_V = np.linspace(_AM["V_RANGE"][0], _AM["V_RANGE"][1], 120)
AM_EDGE = [(_AM["U_SOUTH"] + float(_amf(v)), float(v)) for v in AM_V]

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
# 10-29 夜（ユーザー）：はれのまは無くし、スパン10 は遊戯室の「もう一つの入り口」（洞・遊戯室と一続きの床、中身はこれから）。家具・収納は外した
hare = SP(rect(KN, 30, -3.4, -20, 8)).intersection(WB).difference(cook)
poly(hare, "#F6E3A4", "none", 0, 1.2)
band = SP(rect(22.5, 31.6, -0.2, -3.4, 8)).intersection(WB.union(SP(rect(22.5, 31.6, -0.2, -0.9))))
poly(SP(rect(22.5, 31.6, 0.0, -3.4, 8)), C["roof"], "none", 0, 1.2)       # east band + gap: barefoot ±0, one space with the hall
poly(SP(rect(21, 22.5, -0.2, -3.4, 4)), C["strait"], "none", 0, 1.3)
poly(WB.intersection(clip), "none", "black", 1.2, 6)
for ln in [[(KN, -3.4), (KN, -14)], [(21, -3.4), (KN + 0.06, -3.4)], [(30, -3.4), (31.6, -3.4)], [(KN, CB), (30, CB)]]:   # 10-29：スパン10 と東の帯・遊戯室（u30）のあいだの仕切りは無し
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

# kitchen（60 m²、11-01 ユーザー）：大量調理施設衛生管理マニュアルの考え方（約115食で対象外だが乳幼児・離乳食・アレルギー食があるので従う）。
# 部屋で分けず、床の色（淡い塗り分け）と腰の高さの仕切り（細い線）で汚染作業区域と非汚染作業区域を分ける。流れは逆戻りさせない：
# 検収→下処理→加熱→盛り付け→配膳口／返却口→下膳台→シンク→食器洗浄機→消毒保管庫（パススルー）→盛り付け・保管
# 11-03（ユーザー：口はひとつ、北の面の西の端＝昔のはれのまのいちばん奥にガラスの引き戸）：西＝汚染（南西＝検収・下処理、北西＝洗浄）、
# 東＝非汚染（加熱・盛り付け・配膳車）。戸は二つの区域の継ぎ目にあり、戸の前（灰）は配膳と下膳を時間で分けて使う。
# 盛り付け→配膳車→戸は北のガラスに沿う非汚染の通り（幅1.3）で、下処理の区域を横切らない。下膳は戸から西へ、洗浄の通り（汚染）を通る。
KD = -9.4                                                                  # 汚染（南西：検収・下処理）｜非汚染（加熱）の仕切り
KDU, KDW = 24.1, -11.0                                                     # 洗浄（北西）の区域：u24.1〜27.25・v−11.0より西
KDR0, KDR1 = -9.95, -11.04                                                 # 引き戸の開口（v）
ZD, ZC, HW = "#F6DDC8", "#E2EFD9", "#CDE8F2"                               # 汚染作業区域・非汚染作業区域・手洗い
ZT = "#E4E0D8"                                                             # 戸の前（時間で分ける）
z_dirty = kit.intersection(SP(rect(21, KDU, KD, -20, 8)).union(SP(rect(KDU, KN, KDW, -20, 6))))
z_door = SP(rect(25.9, KN, KDR0, KDW, 4))
poly(z_dirty, ZD, "none", 0, 1.22); poly(kit.difference(z_dirty).difference(z_door), ZC, "none", 0, 1.21); poly(z_door, ZT, "none", 0, 1.23)
KP = "#4a4a4a"                                                             # 腰の高さの仕切り
line([(21.03, KD), (KDU, KD), (KDU, -10.1)], lw=0.8, c=KP, z=6.2)          # 開き v−10.1〜−11.0・u24.1〜24.7（下処理・洗浄から手洗いを通って非汚染へ）
line([(24.7, KDW), (25.9, KDW)], lw=0.8, c=KP, z=6.2)                      # 消毒保管庫の所（両側から出し入れ）
def obox(p0, p1, d, fc="white", lw=0.45, z=4):                             # 曲がった壁に背をつける箱（p0→p1 が背、d は奥行き）
    a, b = np.array(p0), np.array(p1); t = (b - a) / np.linalg.norm(b - a); n = np.array([-t[1], t[0]])
    if n[0] + n[1] < 0: n = -n
    poly([W(*q) for q in (a, b, b + d * n, a + d * n)], fc, "black", lw, z)
    return a + (t * np.linalg.norm(b - a) + d * n) / 2
def hw(u0, u1, v0, v1): box(u0, u1, v0, v1, fc=HW, lw=0.35); circ((u0 + u1) / 2, (v0 + v1) / 2, 0.09, fc="white", lw=0.3)
# 汚染作業区域（南西）：検収・冷凍冷蔵庫・下処理（シンクは魚肉用と野菜用を分ける）。仕切りに沿う台で下処理を済ませた物を仕切り越しに加熱へ
hw(21.1, 21.5, KD - 0.05, -9.85)                                           # 検収・下処理の手洗い（勝手口のすぐ内側）
box(21.55, 22.35, KD - 0.05, -10.1); T(21.95, -9.77, "検収台\n（下は食品庫）", 2.8)
box(22.35, 23.35, KD - 0.05, -10.1, fc="#EAF4F6"); T(22.85, -9.77, "シンク2槽\n野菜用", 3.2)
box(23.35, 24.05, KD - 0.05, -10.1); T(23.7, -9.77, "下処理台\n（下は冷蔵）", 2.8)
_c = obox((21.85, -12.0), (22.75, -12.62), 0.75, fc="#EEF3F6"); T(*_c, "冷凍冷蔵庫", 3.4, rotation=-55)
box(23.25, 23.9, -11.95, -12.6, fc="#EAF4F6"); T(23.57, -12.27, "シンク\n魚肉用", 3.0)
# 汚染作業区域（北西）：下膳・洗浄（西の窓の前は低い物だけ：食洗機は下に入る型）。消毒保管庫は区域の境で両側から出し入れ
box(26.1, 26.9, -12.2, -12.95); T(26.5, -12.55, "下膳台", 3.4)
box(25.3, 26.1, -12.2, -12.95, fc="#EAF4F6"); T(25.7, -12.55, "シンク", 3.4)
box(24.7, 25.3, -12.2, -12.95, fc="#EEEEEE"); T(25.0, -12.55, "食洗機\n（下に入る型）", 2.8)
box(24.1, 24.7, -12.2, -12.95); T(24.4, -12.55, "洗浄後", 3.2)
box(24.7, 25.9, -10.7, -11.3, fc="#EEF3F6", lw=0.6); T(25.3, -11.0, "消毒保管庫", 3.4)
hw(24.2, 24.6, -9.5, -9.9)                                                 # 下処理・洗浄・前室から非汚染へ入る所の手洗い
# 非汚染作業区域：加熱の島（フードの範囲を点線）
box(22.65, 23.45, -5.5, -6.4, fc="#EEEEEE"); circ(23.05, -5.95, 0.32, fc="white"); T(23.05, -5.95, "回転釜", 3.2)
box(22.65, 23.45, -6.4, -7.6, fc="#EEEEEE"); T(23.05, -7.0, "ガスレンジ", 3.4, rotation=90)
box(22.65, 23.45, -7.6, -8.2)
box(23.45, 24.25, -5.5, -6.4, fc="#EEEEEE"); T(23.85, -5.95, "スチコン", 3.4)
box(23.45, 24.25, -6.4, -8.2); T(23.85, -7.3, "作業台（下は冷蔵）", 3.4, rotation=90)
box(22.55, 24.35, -5.4, -8.3, fc="none", ec="#777777", ls=(0, (4, 2)), z=8)
# 盛り付け・配膳車（北のガラスに沿う通り、幅1.3）、アレルギー食（南東の角）・離乳食
box(25.15, 25.85, -5.5, -8.2); T(25.5, -6.85, "盛り付け台", 3.8, rotation=90)
for _v0, _v1 in ((-8.5, -9.1), (-9.2, -9.8)): box(26.0, 27.0, _v0, _v1, fc="#DDDDDD", lw=0.4)      # 配膳車（保温・保冷）
box(22.7, 23.85, -3.45, -4.1); T(23.27, -3.78, "アレルギー食の\n盛り付け", 3.0)
box(21.55, 22.65, -3.45, -4.1, fc="#FFF4E8"); T(22.1, -3.78, "アレルギー台", 3.4, rotation=90)
box(21.1, 21.55, -4.5, -5.4, fc="#FFF4E8"); T(21.33, -4.95, "専用器具の棚", 3.0)
box(21.1, 21.75, -5.5, -6.8, fc="#FFF4E8"); T(21.43, -6.15, "離乳食・\n調乳", 3.4)
box(21.1, 21.75, -6.9, -7.55, fc="#EEF3F6"); T(21.43, -7.22, "保存食\n−20℃", 3.0)
hw(21.1, 21.5, -8.3, -8.7)                                                 # 加熱・盛り付けの職員の手洗い
T(26.55, -10.5, "戸の前\n（配膳と下膳は時間で分ける）", 2.8, c="#555555")
# 流れ（細い矢印）：食材は橙、下膳は紫
def flow(path, c):
    p = [W(u, v) for u, v in path]
    ax.plot([q[0] for q in p[:-1]], [q[1] for q in p[:-1]], lw=0.7, color=c, zorder=11, solid_capstyle="round")
    ax.add_patch(FancyArrowPatch(p[-2], p[-1], arrowstyle="-|>", mutation_scale=5, color=c, lw=0.7, zorder=11))
FOOD, DISH = "#D2691E", "#8E44AD"
flow([(21.3, -11.0), (22.0, -10.7), (23.7, -10.7), (23.7, -10.25)], FOOD)       # 勝手口→検収→下処理
flow([(23.85, -9.25), (23.85, -8.35)], FOOD)                               # 下処理台越しに→加熱
flow([(24.3, -6.9), (25.1, -6.9)], FOOD)                                   # 加熱→盛り付け台
flow([(25.95, -6.2), (26.5, -6.2), (26.5, -8.4)], FOOD)                     # 盛り付け台→配膳車
flow([(26.7, -9.9), (26.95, -10.25), (27.75, -10.25)], FOOD)               # 配膳車→戸→遊戯室の入り口・東の帯へ
flow([(27.75, -10.7), (26.75, -10.7), (26.5, -11.5), (26.5, -12.1)], DISH)  # 戸→下膳台
flow([(26.1, -11.95), (24.4, -11.95), (24.4, -11.5), (24.75, -11.4)], DISH) # シンク→食洗機→洗浄後→消毒保管庫
flow([(25.3, -10.6), (25.5, -9.4), (25.5, -8.3)], DISH)                    # 消毒保管庫の非汚染の側から→盛り付け
# キッチンの区域と流れの凡例・注（紙の左上、図の上の空き）
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
def _fx(mm_): return mm_ / 420
def _fy(mm_): return mm_ / 297
fig.text(_fx(18), _fy(268.5), "キッチン", fontsize=6.2, weight="bold", va="center")
for i, (fc_, s_) in enumerate([(ZD, "汚染作業区域（検収・下処理・洗浄）"), (ZC, "非汚染作業区域（加熱・盛り付け・配膳車）"), (HW, "手洗い（足踏みかセンサーの水栓）")]):
    y_ = 264.5 - 4.0 * i
    fig.add_artist(Rectangle((_fx(18), _fy(y_ - 1.2)), _fx(6), _fy(2.4), fc=fc_, ec="black", lw=0.35, transform=fig.transFigure))
    fig.text(_fx(26), _fy(y_), s_, fontsize=5.6, va="center")
for i, (c_, s_) in enumerate([(FOOD, "食材の流れ（検収→下処理→加熱→盛り付け→配膳車→戸）"), (DISH, "下膳の流れ（戸→下膳台→シンク→食洗機→消毒保管庫→盛り付け）"), (KP, "腰の高さの仕切り（区域の境）。点線はフードの範囲")]):
    y_ = 264.5 - 4.0 * i
    if i < 2:
        fig.add_artist(FancyArrowPatch((_fx(100), _fy(y_)), (_fx(107), _fy(y_)), arrowstyle="-|>", mutation_scale=5, color=c_, lw=0.7, transform=fig.transFigure))
    else:
        fig.add_artist(Line2D([_fx(100), _fx(107)], [_fy(y_), _fy(y_)], lw=0.8, color=c_, transform=fig.transFigure))
    fig.text(_fx(109), _fy(y_), s_, fontsize=5.6, va="center")
fig.text(_fx(196), _fy(268.5), "キッチンの作り（11-03）：大量調理施設衛生管理マニュアル（厚労省、1回300食以上が対象）の考え方に沿う。約115食で対象外だが、\n"
         "乳幼児・離乳食・アレルギー食があるので従う。部屋で分けず、床の色と腰の高さの仕切りで区域を分け、流れを逆戻りさせない。床はドライの床。\n"
         "背の高い物（冷凍冷蔵庫・消毒保管庫・スチコン）は西の窓・東と北のガラスの前に置かない（食洗機は下に入る型）。保存食は−20℃で2週間。\n"
         "口は北の面の西の端の引き戸ひとつ：西は汚染、東は非汚染。配膳と下膳は時間で分け、戸の前（灰）で交わらない。配膳車は北のガラスに沿って戸へ。",
         fontsize=5.4, va="top", linespacing=1.55, color="#333333")
# キッチンの東の面 v−3.4・北の面 u27.25（11-03、ユーザー：遊戯室の入り口の側と同じ作りで統一）：腰壁 h450 の上を 2 階の床の下 3170 まで
# 一続きのガラス（細い二本線）、柱 u24・u27 はそのまま（ガラスは柱の面に突き当てる）、角は鋼の方立て□50×50。配膳口・返却口・生ごみの台は無し。
box(21.2, 27.225, -3.46, -3.34, fc="white", ec="none", lw=0, z=7.0)
for vg in (-3.43, -3.37): line([(21.2, vg), (27.225, vg)], lw=0.35, c=C["glass"], z=7.3)
for _uc in (24.0, 27.0): box(_uc - 0.09, _uc + 0.09, -3.2, -3.6, fc="#333333", lw=0.3, z=8)   # 2 階の床梁を受ける骨格の柱 180×400（10-27）
box(KN - 0.06, KN + 0.06, -3.46, KDR1, fc="white", ec="none", lw=0, z=7.0)
for ug in (KN - 0.03, KN + 0.03): line([(ug, -3.425), (ug, KDR0)], lw=0.35, c=C["glass"], z=7.3)
box(KN - 0.025, KN + 0.025, -3.375, -3.425, fc="#333333", lw=0.2, z=7.4)          # 角の方立て □50×50
# 引き戸（ガラス戸、下450は腰壁と同じ杉の板、上吊り）：開口 v−9.95〜−11.04（有効約1.0）、キッチンの側で東へ引く（引き込みは点線）
line([(KN - 0.085, -9.90), (KN - 0.085, -11.09)], lw=1.0, c="#555555", z=7.5)
line([(KN - 0.085, -8.71), (KN - 0.085, -9.90)], lw=0.6, c="#555555", ls=(0, (2, 1.5)), z=7.5)
box(26.5, 27.15, -4.25, -5.45, fc="white"); box(24.15, 26.85, -3.6, -4.25, fc="white")   # 保管（低い棚 h450・2段）：北東の角、ガラスの見通しを保つ
T(25.5, -3.93, "保管（低い棚h450・2段）", 3.6, rotation=90)
for (a0, a1, b0, b1) in [(KN + 0.06, KN + 0.41, -3.5, -9.7), (22.6, 23.85, -3.34, -2.99), (24.15, 26.85, -3.34, -2.99)]:
    box(a0, a1, b0, b1, fc="#D8C9A8", lw=0.4, z=6.8)                              # 踏み台 h300（東の帯の通路は約2.1 m 残る）
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
T(28.6, -5.2, "遊戯室の入り口", 5.6, weight="bold")                     # 10-29 夜：はれのまは無くした（机・椅子・カウンター・収納も外す）
ax.add_patch(Circle(W(28.6, -7.0), 0.45, fc="none", ec="#555555", lw=0.5, ls=(0, (3, 2)), zorder=9))   # 天井扇 φ0.9（8ed33f3）


# ---------------------------------------------------------------- main building: spans 6–10
fill(U0, 18, 1.6, 12, C["two"]); fill(U0, 18, -0.2, 1.6, C["roof"])
fill(18, 21, -0.2, 1.6, C["off"]); fill(18, 21, 1.6, 4.5, C["rest"]); fill(18, 21, 4.5, 12, C["med"])
poly([W(21, AM_V[0])] + [W(u, v) for u, v in AM_EDGE] + [W(21, AM_V[-1])], C["strait"], "none", 0, 1.4)   # あまのがわ（土足 −150）
fill(21, U1, 1.6, 12, C["hall"]); fill(21, U1, -0.2, 1.6, C["roof"])
fill(U0, 21, 12, 15, C["roof"]); fill(22.5, U1, 12, 15, C["roof"]); fill(21, 22.5, 13.5, 15, C["strait"])
line([(U0, 13.5), (21, 13.5)], lw=1.2, c=C["glass"]); line([(22.5, 13.5), (U1, 13.5)], lw=1.2, c=C["glass"])
line([(U0, 15), (U1, 15)], lw=0.4, c="#777777", ls=(0, (6, 3)))
wall(U0, 21, -0.35, -0.20)                                                  # west outer wall（柱の外、v −0.35〜−0.20）: only south of the strait (north of it the hall opens to the west building)
for uf in range(18, 32, 3):
    for vc in (0, 12): box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, fc="black", ec="black", z=7)
wall(17.95, 18.07, 1.2, 12.0)                                              # 2-yr / span 7
wall(18.07, 21.0, 4.45, 4.57)                                              # 静養室 / 医務
line([(19.0, 4.51), (20.4, 4.51)], lw=2.6, c="white", z=7); line([(19.0, 4.6), (20.4, 4.6)], lw=0.5, ls=(0, (2, 1)), z=7.1)   # 医務との戸（引き分け戸）
line([(21, 4.45), (21, 12)], lw=1.6, c="#333333", z=6)                    # 医務｜あまのがわ（閉じる）
wall(18.07, 18.6, 1.54, 1.66); wall(20.2, 21.0, 1.54, 1.66)                # 窓口の帯｜静養室
line([(18.6, 1.6), (20.2, 1.6)], lw=1.4, c=C["glass"], z=7)                # 室内窓（h0.9〜2.0、先生が見守る）
line([(21, 1.6), (21, 3.0)], lw=1.6, c="#333333", z=6); line([(21, 3.9), (21, 4.45)], lw=1.6, c="#333333", z=6)   # 静養室｜あまのがわ
line([(21.06, 3.0), (21.06, 3.9)], lw=0.8, c="#555555", z=7.1)            # 戸（お迎えの保護者へ、片引き戸）
box(20.60, 20.95, 0.95, 1.55, fc="#E8DCC8", lw=0.5)                        # おはようの窓口: low counter, open to the strait
circ(20.25, 1.25, 0.2)                                                     # 先生の腰掛け
line([(u, v) for u, v in AM_EDGE if 0.0 <= v <= 12.0], lw=0.9, c=C["wood"], z=6)   # 框（曲線の杉）: あまのがわ (−150) / hall (±0)
_t = np.linspace(0, 2 * math.pi, 40)
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
T(17.2, 6.0, "2歳", 7, c="#3d5a1a"); T(26.0, 7.0, "ホール", 8); T(21.7, 9.6, "あまのがわ", 5.6, rotation=90)
T(24.0, -8.2 + 0.0, "", 4)
T(25.2, -6.0 + 0, "", 4)
T(24.7, -4.9, "キッチン", 8, weight="bold"); 
T(27.6, -2.15, "西館の東の帯（はだし ±0、ホールと一続き）", 4.8, rotation=90)
T(29.5, 13.0, "縁側", 5.4, c="#777777"); T(31.0, -8.0, "遊戯室 ↑", 6)

# the food route and the 2-yr route through事務 (curving, behind the desk)
route = [(27.75, -10.25), (28.3, -9.6), (28.3, -2.8), (26.6, -1.7), (24.3, -0.9), (23.6, 1.5), (23.8, 6.0), (23.6, 12.75), (22.5, 12.85), (20.5, 12.85), (18.0, 12.85), (U0 + 0.2, 12.85)]   # 給食は内縁側で渡る（本館係の案4）
pts = [W(u, v) for u, v in route]
ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=1.3, color="#2E8B57", ls=(0, (3, 2)), zorder=11)
ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, color="#2E8B57", lw=1.3, zorder=11))
kids = [(20.0, -1.6), (20.9, -1.85), (21.6, -1.6), (21.75, 0.5), (21.95, 2.6), (21.65, 4.2), (21.6, 5.5), (21.6, 13.0)]
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
NUMS = [(21.0, -1.85, 1), (22.0, -2.4, 2), (21.0, -3.95, 3), (21.0, -7.1, 4), (20.95, -11.65, 5), (KN + 0.75, -10.5, 6),
        (KN + 0.75, -7.2, 8), (26.5, -9.15, 11), (18.6, 1.15, 12), (20.78, 1.9, 13), (19.7, 4.5, 14),
        (19.55, 2.45, 15), (20.05, 12.0, 16), (19.9, -8.1, 17), (29.0, -12.6, 18), (22.75, 7.4, 19), (25.5, -2.6, 21), (21.3, 3.45, 23), (19.5, 3.55, 24)]
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
fig.text(PL / 420, 287 / 297, "育ち舎　南の入口まわり（キッチン・遊戯室の入り口・窓口の帯・静養室・医務）　ラフ", fontsize=13, weight="medium", va="top")
a_kit, a_hare = kit.area, hare.area
a_off = SP(rect(18, 21, -0.2, 1.6)).area; a_rest = SP(rect(18, 21, 1.6, 4.5)).area; a_med = SP(rect(18, 21, 4.5, 12)).area
fig.text(PL / 420, 279.5 / 297, f"1/100（A3）　2026-10-29　架構の番号は南から（架構kは南の妻から3(k−1) m、スパンkは架構kとk+1のあいだ）。"
         f"面積（芯々、概算）：キッチン {a_kit:.0f} m²　遊戯室の入り口（遊戯室に含める） {a_hare:.0f} m²　窓口の帯 {a_off:.1f} m²　静養室 {a_rest:.1f} m²　医務 {a_med:.0f} m²",
         fontsize=6.4, va="top", color="#444444")
leg = ["1　入口（西館の南の面、引き戸1.8）。すき間はガラス", "2　あまのがわの延長（土足 −150、幅1.5）。框から北は東の帯（はだし ±0）", "3　「今日のごはん」の窓（子どもの高さ、中は見本の棚）",
       "4　キッチンの南のガラス（離乳食・調乳の台と加熱が見える）", "5　検収（勝手口のすぐ内側）", "6　キッチンの口：北の面の西の端のガラスの引き戸（有効約1.0、上吊り、キッチンの側で東へ引く）",
       "8　キッチンの北のガラス（腰壁h450の上、角は方立て□50×50）と踏み台h300（3〜5歳が作業台越しに見る）",
       "11　配膳車（保温・保冷）の置き場（キッチンの中、戸の脇）", "12　窓口の帯（受付・見守り、西の窓から小径の出口・手水・入口が見える。机仕事はスパン11の記録・連絡の机）", "13　おはようの窓口（低いカウンター、あまのがわの広い淵に向く）",
       "14　静養室と医務のあいだの戸（保健師が看る）", "15　静養室（こども用ベッド×2、戸で閉じ換気は別、窓口の帯から室内窓h0.9〜2.0）", "16　医務の戸（内縁側から、先生が子どもを連れてくる）", "17　下屋の下の縁台とお茶の棚（電気ポットはh1100の棚の上：給湯ロック・転倒湯もれ防止・蒸気レス・マグネットプラグ）",
       "18　調理の職員の更衣・便所・前室（外から直接：西の面の戸 → 更衣 → 前室 → キッチン）", "19　あまのがわの北の縁（ホールとの段150、框は曲線の杉。本館係の案4、飛び石は無し）",
       "21　キッチンの東の面：北の面と同じ、腰壁h450の上を2階の床の下まで一続きのガラス（二本線、柱u24・u27は残る）。ホールの側に踏み台h300。破線の円は天井扇φ0.9",
       "23　静養室の戸（あまのがわへ、お迎えの保護者が迎えに来る）", "24　静養室の換気扇（天井から真上へ、屋根の上の換気の頭。給気は戸の下から）"]
for i, s in enumerate(leg):
    c, r = divmod(i, 8)
    fig.text((PL + 132 * c) / 420, (74 - 4.3 * r) / 297, s, fontsize=5.8, va="top")
fig.text(PL / 420, 35 / 297, "┅ 緑：配膳の保育士（キッチンの北の引き戸 → 遊戯室の入り口 → 東の帯 → ホール → 内縁側で先生があまのがわを渡る（段150、両側に手すり）→ 南の保育室）。┅ 茶：3〜5歳（入口 → あまのがわ → 縁側、おはようの窓口の前を通る）。"
         "キッチンは検収→下処理→加熱→盛り付け→配膳車→戸、戸→下膳台→洗浄→消毒保管庫→盛り付けの一方通行（配膳と下膳は時間で分ける）（区域と流れは左上）。\n"
         "西館の東の帯とすき間は、エキスパンションをはさんでホールと一続き（はだし ±0）。本館の西の壁はホールの範囲では開く。"
         "スパン10 は遊戯室のもう一つの入り口（10-29 夜、ユーザー：はれのまは無くす。中身はこれから）。記念日のお祝いはホール、延長保育は玄関に近い保育室（案）。", fontsize=6.2, va="top", color="#444444", linespacing=1.6)
fig.savefig(os.path.join(OUT, "sodachiya_05_south_entry.pdf"))
print("areas", round(a_kit, 1), round(a_hare, 1), round(a_off, 1), round(a_med, 1))
