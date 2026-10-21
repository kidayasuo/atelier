# ホールの北山杉の林 1/100：平面＋断面（北を見る）＋模型のピアノ線の表（A3 横）
# 配列は data/forest.json（scripts/forest_gen.py が作る）。座標は本館の (u, v)。
import json, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
F = json.load(open(os.path.join(ROOT, "data", "forest.json")))
P, TR, TOPC, MOD = F["PARAMS"], F["TREES"], F["TOP"], F["MODEL"]

CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
def Wraw(u, v):
    th = TH_S - u / RW; r = RW - v
    return (CX + r * math.cos(th), CY + r * math.sin(th))
O = np.array(Wraw(26, 6)); dvec = np.array(Wraw(26.5, 6)) - np.array(Wraw(25.5, 6))
ANG = math.atan2(dvec[1], dvec[0]) - math.pi / 2                     # +u up (as plan05)
ca, sa = math.cos(-ANG), math.sin(-ANG)
def W(u, v):
    x, y = Wraw(u, v); x, y = x - O[0], y - O[1]
    return (x * ca - y * sa, x * sa + y * ca)
def rect(u0, u1, v0, v1, n=4):
    return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]

def top(v):
    return TOPC["WEST_VOID_TOP"] if v < TOPC["WEST_VOID_V"] else 4.0 - v / 12.0

C = dict(hall="#E3C08D", roof="#F4EBDD", strait="#D9CBB4", kit="#F0B98A", hare="#F7D3B0", off="#E9DCC4", med="#F7F3EA",
         glass="#3d7fb0", wood="#8a5a2b", food="#2E8B57", view="#8B6BB0", t50="#C9A27A", t70="#9C6B3F", t100="#6B4423", nushi="#3E2512")
DCOL = {0.05: C["t50"], 0.07: C["t70"], 0.1: C["t100"], 0.2: C["nushi"]}

MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
U0, U1, V0, V1 = 20.3, 31.0, -4.2, 15.6
xs = [W(u, v)[0] for u in (U0, U1) for v in (V0, V1)]; ys = [W(u, v)[1] for u in (U0, U1) for v in (V0, V1)]
xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
PL, PB = 14, 118
ax = fig.add_axes([PL / 420, PB / 297, (xmax - xmin) * 10 / 420, (ymax - ymin) * 10 / 297])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

def poly(pts, fc="none", ec="black", lw=0.45, z=2, ls="-"):
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls))
def fill(u0, u1, v0, v1, c, z=1): poly(rect(u0, u1, v0, v1), c, "none", 0, z)
def box(u0, u1, v0, v1, fc="white", ec="black", lw=0.45, z=4, ls="-"): poly(rect(u0, u1, v0, v1), fc, ec, lw, z, ls)
def line(uv, lw=0.45, c="black", ls="-", z=5):
    p = [W(u, v) for u, v in uv]; ax.plot([q[0] for q in p], [q[1] for q in p], lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(u, v, s, size=6, c="#222222", z=10, **kw):
    x, y = W(u, v); ax.text(x, y, s, fontsize=size, color=c, ha=kw.pop("ha", "center"), va=kw.pop("va", "center"), zorder=z, **kw)
def num(u, v, k, c="black"):
    x, y = W(u, v); ax.add_patch(Circle((x, y), 0.28, fc="white", ec=c, lw=0.5, zorder=14))
    ax.text(x, y, str(k), fontsize=5.4, ha="center", va="center", zorder=15, color=c)

# ---------------------------------------------------------------- floors
fill(21, 30, 1.6, 12, C["hall"]); fill(21, U1, 0, 1.6, C["roof"]); fill(22.5, U1, -3.4, 0, C["roof"])
fill(U0, U1, 12, 15, C["roof"]); fill(21, 22.5, -3.4, 13.5, C["strait"], 1.2); fill(21, 22.5, 13.5, 15, C["strait"], 1.2)
fill(U0, 21, 0, 4.45, C["off"]); fill(U0, 21, 4.45, 12, C["med"])
fill(30, U1, 1.6, 12, C["off"])
fill(U0, 21, -3.4, -0.2, "#EEDFC6"); fill(22.5, 27.25, -4.2, -3.4, C["kit"]); fill(27.25, U1, -4.2, -3.4, C["hare"])
# walls, glass, columns, 框
line([(22.5, -3.4), (U1, -3.4)], lw=1.4, c="#333333", z=6)
for a0, a1 in [(21.0, 22.6), (24.4, 25.5), (26.5, 27.15)]: line([(a0, -3.4), (a1, -3.4)], lw=1.4, c=C["glass"], z=6.5)
line([(22.7, -3.4), (24.3, -3.4)], lw=2.6, c=C["food"], z=7); T(23.5, -3.9, "配膳口", 4.6, c=C["food"])
line([(22.5, -0.45), (U1, -0.45)], lw=0.5, c="#777777", ls=(0, (6, 2, 1, 2)), z=6); T(30.6, -0.2, "エキスパンション", 3.8, c="#777777", rotation=90)
line([(21, 0), (21, 2.3)], lw=0.5, c=C["wood"], ls=(0, (2, 1.5)), z=6); box(20.6, 21.0, 0.2, 2.3, fc="#E8DCC8", lw=0.4)
line([(21, 2.4), (21, 4.4)], lw=0.5, c=C["wood"], ls=(0, (2, 1.5)), z=6)
line([(21, 4.45), (21, 12)], lw=1.4, c="#333333", z=6)
line([(30, 1.6), (30, 12)], lw=1.4, c="#333333", z=6)
line([(22.5, 0), (22.5, 12)], lw=0.9, c=C["wood"], z=6); line([(22.5, -3.4), (22.5, -0.2)], lw=0.9, c=C["wood"], z=6)
line([(U0, 13.5), (21, 13.5)], lw=1.2, c=C["glass"]); line([(22.5, 13.5), (U1, 13.5)], lw=1.2, c=C["glass"])
line([(U0, 15), (U1, 15)], lw=0.4, c="#777777", ls=(0, (6, 3)))
for uf in (21, 24, 27, 30):
    for vc in (0, 12): box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, fc="black", ec="black", z=7)
    if uf in (24, 27):                                             # beams overhead (2 leaves)
        line([(uf - 0.14, 0), (uf - 0.14, 12)], lw=0.35, c="#555555", ls=(0, (5, 3)), z=5)
        line([(uf + 0.14, 0), (uf + 0.14, 12)], lw=0.35, c="#555555", ls=(0, (5, 3)), z=5)
for v in (0, 1.6): line([(U0, v), (U1, v)], lw=0.35, c="#999999", ls=(0, (2, 2)), z=5)
_t = np.linspace(0, 2 * math.pi, 40)
poly([W(21.75 + 0.2 * math.sin(a), 3.4 + 0.5 * math.cos(a)) for a in _t], "#BFAF95", "#6b5a3a", 0.4, 6)

# ---------------------------------------------------------------- design devices
cl = P["CLEARING"]; cu, cv = cl["c"]
poly([W(cu + cl["r"] * math.cos(a), cv + cl["r"] * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 80)], "#EED7AE", "#B08D57", 0.5, 2, ls=(0, (4, 2)))
for k in range(20):                                                  # 20 children sitting in a ring
    a = 2 * math.pi * (k + 0.5) / 21
    x, y = W(cu + 1.7 * math.cos(a), cv + 1.7 * math.sin(a)); ax.add_patch(Circle((x, y), 0.15, fc="#FFFFFF", ec="#B08D57", lw=0.3, zorder=3))
x, y = W(cu + 1.7 * math.cos(-0.15), cv + 1.7 * math.sin(-0.15)); ax.add_patch(Circle((x, y), 0.2, fc="#B08D57", ec="none", zorder=3))
duv = np.array(F["RESULT"]["view_dir_uv"]); t = (P["VIEW"]["v_end"] - cv) / duv[1]
a = W(cu + duv[0] * 0.5, cv + duv[1] * 0.5); b = W(cu + duv[0] * (t + 3.6), cv + duv[1] * (t + 3.6))
ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=7, lw=0.7, color=C["view"], ls=(0, (5, 2)), zorder=8))
T(cu + duv[0] * (t + 3.0) - 0.6, cv + duv[1] * (t + 3.0) + 0.1, "築山の頂へ\n（比叡山の向き）", 4.8, c=C["view"])
rm = P["ROOM"]; poly([W(rm["c"][0] + 0.85 * math.cos(a), rm["c"][1] + 0.85 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 60)], "#F3E2C0", "none", 0, 2)
fu, fv = P["FOOD"]
poly(rect(22.5, fu, 0.0, fv), "none", C["food"], 0.4, 3, ls=(0, (1, 1.5)))
# food route (green)
pr = [W(23.5, -3.4), W(23.6, -1.8), W(23.75, 0.6), W(23.3, 2.6), W(22.4, 3.3), W(21.75, 3.4), W(21.0, 3.4)]
ax.plot([p[0] for p in pr], [p[1] for p in pr], lw=1.0, color=C["food"], zorder=8, alpha=0.8)
ax.add_patch(FancyArrowPatch(pr[-2], (pr[-1][0] - 0.0, pr[-1][1]), arrowstyle="-|>", mutation_scale=6, lw=1.0, color=C["food"], zorder=8))

# ---------------------------------------------------------------- trees
for i, t_ in enumerate(TR, 1):
    u, v, d = t_["u"], t_["v"], t_["d"]
    x, y = W(u, v)
    ax.add_patch(Circle((x, y), d / 2 + P["GAP"] / 2, fc="none", ec="#B9A27E", lw=0.25, ls=(0, (1, 1.5)), zorder=8))
    if t_.get("shape") == "taiko":                                   # 太鼓落とし：平らな面を列の向きに（少し大きめに描く）
        a = math.radians(t_["ang"]); ea = np.array([math.cos(a), math.sin(a)]); eb = np.array([-ea[1], ea[0]])
        hw, ht = max(d / 2, 0.07), max(t_["t"] / 2, 0.04)
        poly([W(*(np.array([u, v]) + ea * sx * hw + eb * sy * ht)) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]], DCOL[d], "black", 0.25, 9)
    else:
        ax.add_patch(Circle((x, y), max(d / 2, 0.05), fc=DCOL[d], ec="black", lw=0.25, zorder=9))
    if abs(u - round(u)) < 1e-6 and int(round(u)) in P["FRAMES"]:
        ax.add_patch(Circle((x, y), max(d / 2, 0.06) + 0.07, fc="none", ec="#333333", lw=0.5, zorder=9))
    ax.text(x + 0.16, y + 0.16, str(i), fontsize=3.6, color="#555555", zorder=10)

# group labels and row direction
for g in P["GROUPS"]:
    a = math.radians(g["ang"]); ea = np.array([math.cos(a), math.sin(a)]); c0 = np.array(g["c"])
    p1, p2 = c0 - ea * 0.9, c0 + ea * 0.9
    ax.add_patch(FancyArrowPatch(W(*p1), W(*p2), arrowstyle="<->", mutation_scale=5, lw=0.5, color="#8a5a2b", zorder=11, alpha=0.8))
    T(c0[0] - 0.35, c0[1] + 0.0, g["name"], 4.8, c="#8a5a2b", z=12)
# labels and numbered devices
T(26.4, -1.9, "西館の東の帯（はだし ±0）→ 遊戯室", 4.6, c="#666666", rotation=90)
T(21.75, 9.0, "海峡（土足 −150）", 5.0, c="#6b5a3a", rotation=90)
T(20.0, 2.0, "事務", 6, weight="bold"); T(20.0, 8.0, "医務", 6, weight="bold"); T(30.6, 7.0, "事務・静養室", 5.2, rotation=90)
T(29.6, 13.0, "内縁側", 4.8, c="#777777"); T(29.6, 14.3, "外縁側", 4.8, c="#777777")
T(30.6, 0.8, "絵本の通りへ ↑", 4.4, c="#777777", rotation=90)
T(23.6, 7.6, "ホール", 8, c="#6B4F2A", weight="bold")
num(cu - 0.15, cv + 0.75, 1); num(cu + duv[0] * 3.6 + 0.5, cv + duv[1] * 3.6, 2); num(rm["c"][0], rm["c"][1], 3)
num(25.35 + 0.55, 0.55, 4); num(27.0 - 0.0, 3.0 + 0.0, 5); num(23.6, 2.0, 6); num(23.3, 11.2, 7)

# scale bar + north
sx, sy = W(20.6, -4.0)
ax.plot([sx, sx + 5], [sy - 0.6, sy - 0.6], lw=1.2, color="black", zorder=20)
for k in range(6): ax.plot([sx + k, sx + k], [sy - 0.75, sy - 0.45], lw=0.5, color="black", zorder=20)
ax.text(sx + 2.5, sy - 1.1, "0　　　　5 m　　1/100", fontsize=5, ha="center", va="top")
nx, ny = W(30.2, 14.6); nd = np.array(W(30.2, 14.6)); nd2 = np.array(Wraw(30.2, 14.6))
northv = np.array([0, 1.0]); northv = np.array([northv[0] * ca - northv[1] * sa, northv[0] * sa + northv[1] * ca])
ax.add_patch(FancyArrowPatch((nx, ny), (nx + northv[0] * 1.2, ny + northv[1] * 1.2), arrowstyle="-|>", mutation_scale=8, lw=0.8, color="black", zorder=20))
ax.text(nx + northv[0] * 1.55, ny + northv[1] * 1.55, "N", fontsize=6, ha="center", va="center")

fig.text(PL / 420, 290 / 297, "ホールの北山杉の林　平面 1/100（たたき台・2 版：向きをもつ群）", fontsize=11, weight="bold", va="top")
n = len(TR); nd = {dd: sum(1 for t_ in TR if t_["d"] == dd) for dd in DCOL}
fig.text(PL / 420, 282 / 297, f"スパン 8–10　間伐材 {n} 本（φ50 ×{nd[0.05]}・φ70 ×{nd[0.07]}・φ100 ×{nd[0.1]}・ぬしの木 φ200 ×{nd[0.2]}）。幹と幹のあき 900 以上（点線の輪＝あきの半分）。"
         "海峡・西吹き抜けの道・東の帯・内縁側には生やさない", fontsize=6.4, va="top")

# ---------------------------------------------------------------- section (looking north): projected trunks
SB, SH = 22, 74
SV0, SV1 = -4.2, 15.6
sax = fig.add_axes([PL / 420, SB / 297, (SV1 - SV0) * 10 / 420, 5.6 * 10 / 297 * 1.0])
sax.set_xlim(SV0, SV1); sax.set_ylim(-0.4, 5.2); sax.set_aspect("equal"); sax.axis("off")
sax.fill_between([SV0, 22.5 - 22.5 + 15.6], -0.4, -0.3, color="#BBBBBB", lw=0)
sax.plot([-3.4, 15.0], [0, 0], lw=1.0, color="black")
# main roof (beam top 4.0 → 3.0) and eave; west void lantern
sax.plot([1.6, 12], [4.0 - 1.6 / 12, 3.0], lw=1.2, color="#333333"); sax.plot([12, 15], [3.0, 2.75], lw=1.2, color="#333333")
sax.plot([0, 0, 1.6, 1.6], [4.0, 4.6, 4.55, 4.0 - 1.6 / 12], lw=0.8, color="#333333")
sax.fill([0, 1.6, 1.6, 0], [4.45, 4.45, 4.6, 4.6], color="#E8E8F0", lw=0)
for (a0, a1) in [(0, 0.18)]: pass
# beam beyond (frame 10, u 27): underside 0.6 below the top
vv = np.array([0, 12]); sax.fill(np.r_[vv, vv[::-1]], np.r_[4.0 - vv / 12, (4.0 - vv[::-1] / 12) - 0.6], color="#D9C7A8", lw=0, zorder=1)
sax.text(6, 3.1, "架構 10 の梁（2 枚組、奥）", fontsize=4.6, color="#7a6a50", ha="center")
for vc in (0, 12): sax.add_patch(Polygon([(vc - 0.2, 0), (vc + 0.2, 0), (vc + 0.2, 4.0 - vc / 12 - 0.05), (vc - 0.2, 4.0 - vc / 12 - 0.05)], fc="#CBB89A", ec="none", zorder=1))
# west building east band roof (gap lid) and 2nd floor
sax.plot([-3.4, 0], [3.25, 3.25], lw=0.9, color="#777777"); sax.text(-1.7, 3.4, "西館 2 階の床", fontsize=4.4, ha="center", color="#777777")
sax.plot([13.5, 13.5], [0, 2.27], lw=1.0, color=C["glass"])
order = sorted(TR, key=lambda t_: -t_["u"])
for t_ in order:
    u, v, d = t_["u"], t_["v"], t_["d"]
    k = (u - 23.0) / 6.6
    col = DCOL[d]
    sax.add_patch(Polygon([(v - d / 2, 0), (v + d / 2, 0), (v + d / 2, top(v)), (v - d / 2, top(v))], fc=col, ec="none", alpha=0.35 + 0.65 * (1 - k), zorder=3 + (1 - k)))
# people
def person(v, h, c="#555555"):
    sax.add_patch(Circle((v, h - 0.11), 0.11, fc=c, ec="none", zorder=6))
    sax.add_patch(Polygon([(v - 0.13, 0), (v + 0.13, 0), (v + 0.11, h - 0.24), (v - 0.11, h - 0.24)], fc=c, ec="none", zorder=6))
person(cv - 1.6, 0.7, "#B08D57"); person(cv + 1.6, 0.7, "#B08D57"); person(9.8, 1.6); person(4.9, 1.05)
sax.text(cv, 0.95, "ひらけ（座って輪に）", fontsize=4.6, ha="center", color="#8a6a3a")
for z in (0, 1, 2, 3, 4): sax.text(SV0 + 0.2, z, f"{z:.0f}", fontsize=4.2, va="center", color="#888888")
sax.text(0.8, 4.75, "越屋根", fontsize=4.4, ha="center", color="#555555")
sax.text(SV0, 5.15, "断面（北を見る、林を投影、手前ほど濃い）1/100　幹の上端は屋根の下（垂木の下端）、西吹き抜けでは越屋根の中 h4.4", fontsize=6, va="top", weight="bold")
for vv_, s in [(-1.7, "東の帯"), (0.8, "西吹き抜け"), (7.0, "ホール"), (12.75, "内縁側"), (14.25, "外縁側")]:
    sax.text(vv_, -0.28, s, fontsize=4.4, ha="center", va="top", color="#555555")

# ---------------------------------------------------------------- right column: notes and model table
RX = 232
items = [
    ("1", "ひらけとぬしの木", f"クラス 20 人と先生がぬしの木（φ200、ひとつだけ太い）を囲んで輪に座れる半径 {P['CLEARING']['r']} の空き地。朝の会・お話・雨の日の集まり。こどもの腕で抱きつける太さ。"),
    ("2", "築山の頂への見通し", "ひらけから縁側へ、幅 1.0 だけ幹を立てない筋。ホールから比叡山の方向（真北から 63.5°）に置いた築山の頂が見える。両脇の比叡の群の列がこの向きにそろう。"),
    ("3", "林の小部屋", "西の群（いちばん密な茂み）の列の目を一つ抜いた穴（半径 0.8）。まわりの株立ちが壁になる。布と洗濯ばさみ・ひもで、こどもが自分で家にする。"),
    ("4", "光の木", "西の柱の列の上、柱と柱のあいだに 1 本ずつ。越屋根の中まで伸び、上からの光を浴びる。西の群の列の筋の突き当たりに見える。"),
    ("5", "梁を抜ける木", "架構の線の上では、幹は梁の 2 枚のあいだ（180）を抜けて屋根まで立ち、梁で上が留まる（太い輪）。西の群は列が梁と同じ東西なので、一列がまるごと梁を抜ける。"),
    ("6", "林のへりの広場", "配膳の道（配膳口 → 東の帯 → ホールの西 → 飛び石）と海峡の口には生やさない。"),
    ("7", "縁側のへり", "縁側の前は疎ら。朝の東の光が幹の影を床に長く落とし、昼に向かって影が回って短くなる（林が日時計になる）。"),
]
yy = 286
fig.text(RX / 420, yy / 297, "林のしかけ", fontsize=8.5, weight="bold", va="top"); yy -= 6
for k, h, s in items:
    fig.text(RX / 420, yy / 297, f"{k}　{h}", fontsize=6.4, weight="bold", va="top"); yy -= 3.8
    import textwrap
    for ln in textwrap.wrap(s, 46):
        fig.text((RX + 4) / 420, yy / 297, ln, fontsize=5.6, va="top", color="#333333"); yy -= 3.0
    yy -= 1.2
yy -= 1
fig.text(RX / 420, yy / 297, "配列の決め方", fontsize=8.5, weight="bold", va="top"); yy -= 5.5
rules = [
    "KAIT 工房（石上純也）に学ぶ：柱の向きで見え方が変わる。丸い幹では向きが出ないので、「並びの向き」で出す。木を 3 つの群に分け、群の中は列に並べる。列に沿って見ると筋が透け、横切ると幹が重なる（ばらは 2 枚目）。",
    "群ごとに列の向きを変える：西の群＝東西（梁と同じ）、海峡の群＝南北、比叡の群＝比叡山の向き。だから立つ所と見る向きで景色が変わる（2 枚目の A〜D）。",
    "疎密：西の群は茂み（株の間 1.1、株立ちが多い）、海峡の群は中くらい（1.3）、比叡の群は疎ら（若い木）。群と群のあいだは空き地（ひらけ・へりの広場・縁側の前）。",
    "株立ち：群の木の多くは細い 2〜3 本が触れあって立つ（台杉に倣う、株の中はあき 0）。列の向きに並べるので、扁平な柱のように向きで薄くも厚くも見える。あき 900 は株の外形で測る。",
    f"まっすぐ走れる線（幅 0.6）：林の中で最長 {F['RESULT']['longest_run']:.1f} m（列に沿う筋。群が小さいので筋は短い）。",
    "幹：北山杉の間伐材（磨き丸太、群の単木の φ70・100 は太鼓落とし）、塗らない。足もとは床の穴に沓、上は垂木に金物で留める。",
]
for s in rules:
    for i, ln in enumerate(textwrap.wrap(s, 48)):
        fig.text((RX + (0 if i == 0 else 2.5)) / 420, yy / 297, ("・" if i == 0 else "") + ln, fontsize=5.4, va="top", color="#333333"); yy -= 2.8
    yy -= 0.6

# model table
yy -= 1.5
fig.text(RX / 420, yy / 297, "模型 1/100：ピアノ線の長さ（mm）", fontsize=8.5, weight="bold", va="top"); yy -= 4.8
fig.text(RX / 420, yy / 297, f"長さ＝上端の高さ×10 − {MOD['TOP_GAP']}（屋根を外せるように控える）＋ 差し込み {MOD['EMBED']}（床 2 層を貫く）", fontsize=5.4, va="top", color="#333333"); yy -= 4.2
WIRE = {0.05: "0.5", 0.07: "0.7", 0.1: "1.0", 0.2: "丸棒 2.0"}
rows = []
for i, t_ in enumerate(TR, 1):
    L = top(t_["v"]) * 10 - MOD["TOP_GAP"] + MOD["EMBED"]
    rows.append((i, WIRE[t_["d"]] + ("太" if t_.get("shape") == "taiko" else ""), L))
ncol = 4; per = math.ceil(len(rows) / ncol)
for c in range(ncol):
    for r in range(per):
        j = c * per + r
        if j >= len(rows): break
        i, w, L = rows[j]
        fig.text((RX + c * 45) / 420, (yy - r * 2.7) / 297, f"{i:>2}　{w:<6}　{L:.1f}", fontsize=5.2, va="top", family="Noto Sans CJK JP")
yy -= per * 2.7 + 2
tot = {w: sum(L for _, ww, L in rows if ww.rstrip("太") == w) for w in WIRE.values()}
cnt = {w: sum(1 for _, ww, _L in rows if ww.rstrip("太") == w) for w in WIRE.values()}
fig.text(RX / 420, yy / 297, "合計：" + "、".join(f"{w} ×{cnt[w]} 本（{tot[w]:.0f} mm）" for w in WIRE.values() if cnt[w]), fontsize=5.6, va="top"); yy -= 3.6
fig.text(RX / 420, yy / 297, "穴の位置は data/forest.json の xy_mm（3dm の座標）。穴の径はレーザーの焼け幅に合わせて模型のチャットで。", fontsize=5.4, va="top", color="#333333")

# legend for diameters
lx = PL; ly = 104
for k, (dd, s) in enumerate([(0.05, "φ50（ピアノ線 0.5）"), (0.07, "φ70（0.7）"), (0.1, "φ100（1.0）"), (0.2, "ぬしの木 φ200（丸棒 2.0）")]):
    fig.patches.append(matplotlib.patches.Circle(((lx + 3 + k * 38) / 420, ly / 297), 1.0 / 420, transform=fig.transFigure, fc=DCOL[dd], ec="black", lw=0.3))
    fig.text((lx + 6 + k * 38) / 420, ly / 297, s, fontsize=5.6, va="center")
fig.text((lx + 158) / 420, ly / 297, "緑の線：配膳の道　紫の矢：見通し　点線：梁（上）・越屋根の縁", fontsize=5.6, va="center", color="#444444")

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"sodachiya_forest_01.{ext}"), dpi=200 if ext == "png" else None)
print("trees", n, nd, "run", F["RESULT"]["longest_run"])
