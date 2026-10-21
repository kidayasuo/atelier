# ホールの北山杉の林 1/100：平面＋断面（北を見る）＋模型のピアノ線の表（A3 横）。3 版
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

def top(v, u=None, d=0.0):
    """幹の上端：屋根の下（垂木の下端）、西吹き抜けは越屋根の中。梁の真下なら梁の下端の 0.03 手前。"""
    if u is not None and any(abs(u - uf) < P["BEAM_HALF"] + d / 2 for uf in P["FRAMES"]):
        return 4.0 - max(0.0, v) / 12.0 - 0.6 - TOPC["BEAM_GAP"]
    return TOPC["WEST_VOID_TOP"] if v < TOPC["WEST_VOID_V"] else 4.0 - v / 12.0
def top_old(v):
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

# ---------------------------------------------------------------- food route, channel (found after planting), pockets (not designed)
fu, fv = P["FOOD"]
poly(rect(22.5, fu, 0.0, fv), "none", C["food"], 0.4, 3, ls=(0, (1, 1.5)))
pr = [W(23.5, -3.4), W(23.6, -1.8), W(23.75, 0.6), W(23.3, 2.6), W(22.4, 3.3), W(21.75, 3.4), W(21.0, 3.4)]
ax.plot([p[0] for p in pr], [p[1] for p in pr], lw=1.0, color=C["food"], zorder=8, alpha=0.8)
ax.add_patch(FancyArrowPatch(pr[-2], pr[-1], arrowstyle="-|>", mutation_scale=6, lw=1.0, color=C["food"], zorder=8))
CH = F["CHANNEL"]; chl = CH["line_uv"]
from shapely.geometry import LineString as _LS
band = _LS(chl).buffer(P["CHANNEL"]["clear"] / 2, cap_style=2)
poly([W(u, v) for u, v in band.exterior.coords], "#FFF6E6", "none", 0, 2)
line(chl, lw=0.5, c="#B07A2A", ls=(0, (4, 2)), z=3)
for (u, v, d) in CH["removed"]:
    x, y = W(u, v); ax.plot([x - 0.12, x + 0.12], [y - 0.12, y + 0.12], lw=0.4, color="#B07A2A", zorder=9); ax.plot([x - 0.12, x + 0.12], [y + 0.12, y - 0.12], lw=0.4, color="#B07A2A", zorder=9)
SL = F["SLALOM"]["line_uv"]
line(SL, lw=0.9, c="#C0392B", ls=(0, (3, 1.5)), z=10)
T(SL[len(SL) // 2][0] + 0.2, SL[len(SL) // 2][1] - 0.9, "抱えて通れる道\n（あき 0.7、S 字）", 4.4, c="#C0392B", z=12)
for (r, u, v) in F["RESULT"]["pockets_r_u_v"]:
    if r < 0.8: continue
    poly([W(u + (r - 0.05) * math.cos(a), v + (r - 0.05) * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 60)], "none", "#B08D57", 0.35, 3, ls=(0, (1, 2)))

# ---------------------------------------------------------------- trees
for t_ in TR:
    u, v, d = t_["u"], t_["v"], t_["d"]
    x, y = W(u, v)
    if t_.get("shape") == "taiko":
        a = math.radians(t_["ang"]); ea = np.array([math.cos(a), math.sin(a)]); eb = np.array([-ea[1], ea[0]])
        hw, ht = d / 2, t_["t"] / 2
        poly([W(*(np.array([u, v]) + ea * sx * hw + eb * sy * ht)) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]], DCOL[d], "black", 0.2, 9)
    else:
        ax.add_patch(Circle((x, y), d / 2, fc=DCOL[d], ec="black", lw=0.2, zorder=9))
    if t_.get("removable"):
        ax.add_patch(Circle((x, y), d / 2 + 0.09, fc="none", ec="#2E6FA8", lw=0.4, zorder=9))

# group labels (row direction)
for g in P["GROUPS"]:
    a = math.radians(g["ang"]); ea = np.array([math.cos(a), math.sin(a)]); c0 = np.array(g["c"])
    ax.add_patch(FancyArrowPatch(W(*(c0 - ea * 0.8)), W(*(c0 + ea * 0.8)), arrowstyle="<->", mutation_scale=5, lw=0.5, color="#8a5a2b", zorder=11, alpha=0.7))
    T(c0[0] - 0.3, c0[1], g["name"] + "（列の向き）", 4.6, c="#8a5a2b", z=12)

T(26.4, -1.9, "西館の東の帯（はだし ±0）→ 遊戯室", 4.6, c="#666666", rotation=90)
T(21.75, 9.0, "海峡（土足 −150）", 5.0, c="#6b5a3a", rotation=90)
T(20.0, 2.0, "事務", 6, weight="bold"); T(20.0, 8.0, "医務", 6, weight="bold"); T(30.6, 7.0, "事務・静養室", 5.2, rotation=90)
T(30.6, 12.75, "内縁側", 4.6, c="#777777", rotation=90); T(30.6, 14.3, "外縁側", 4.6, c="#777777", rotation=90)
T(30.6, 0.8, "絵本の通りへ", 4.4, c="#777777", rotation=90)
T(23.5, 2.4, "配膳の道", 4.6, c=C["food"])

# scale bar + north
sx, sy = W(20.6, -4.0)
ax.plot([sx, sx + 5], [sy - 0.6, sy - 0.6], lw=1.2, color="black", zorder=20)
for k in range(6): ax.plot([sx + k, sx + k], [sy - 0.75, sy - 0.45], lw=0.5, color="black", zorder=20)
ax.text(sx + 2.5, sy - 1.1, "0　　　　5 m　　1/100", fontsize=5, ha="center", va="top")
nx, ny = W(30.2, 14.9)
northv = np.array([0, 1.0]); northv = np.array([northv[0] * ca - northv[1] * sa, northv[0] * sa + northv[1] * ca])
ax.add_patch(FancyArrowPatch((nx, ny), (nx + northv[0] * 1.2, ny + northv[1] * 1.2), arrowstyle="-|>", mutation_scale=8, lw=0.8, color="black", zorder=20))
ax.text(nx + northv[0] * 1.55, ny + northv[1] * 1.55, "N", fontsize=6, ha="center", va="center")

n = len(TR); nd = {dd: sum(1 for t_ in TR if t_["d"] == dd) for dd in DCOL}
nclump = sum(1 for t_ in TR if "株立ち" in t_["group"])
fig.text(PL / 420, 290 / 297, "ホールの北山杉の林　平面 1/100（たたき台・5 版）", fontsize=11, weight="bold", va="top")
fig.text(PL / 420, 282 / 297, f"スパン 8–10（西吹き抜け・内縁側を含む）　間伐材 {n} 本（φ50 ×{nd[0.05]}・φ70 ×{nd[0.07]}・φ100 ×{nd[0.1]}・φ200 ×{nd[0.2]}、うち株立ち {nclump} 本）。"
         f"幹と幹のあき {P['GAP']} 以上。うすい帯＝置いたあとで見つけた東西の筋（あき 0.9、× は抜いた木）。点線の輪＝できた空き地（決めない）", fontsize=6.2, va="top")

# ---------------------------------------------------------------- section (looking north): projected trunks
SB = 22; SV0, SV1 = -4.2, 15.6
sax = fig.add_axes([PL / 420, SB / 297, (SV1 - SV0) * 10 / 420, 56 / 297])
sax.set_xlim(SV0, SV1); sax.set_ylim(-0.4, 5.2); sax.set_aspect("equal"); sax.axis("off")
sax.fill_between([SV0, SV1], -0.4, -0.3, color="#BBBBBB", lw=0)
sax.plot([-3.4, 15.0], [0, 0], lw=1.0, color="black")
sax.plot([1.6, 12], [4.0 - 1.6 / 12, 3.0], lw=1.2, color="#333333"); sax.plot([12, 15], [3.0, 2.75], lw=1.2, color="#333333")
sax.plot([0, 0, 1.6, 1.6], [4.0, 4.6, 4.55, 4.0 - 1.6 / 12], lw=0.8, color="#333333")
vv = np.array([0, 12]); sax.fill(np.r_[vv, vv[::-1]], np.r_[4.0 - vv / 12, (4.0 - vv[::-1] / 12) - 0.6], color="#D9C7A8", lw=0, zorder=1)
sax.text(6, 3.1, "架構 10 の梁（2 枚組、奥）", fontsize=4.6, color="#7a6a50", ha="center")
for vc in (0, 12): sax.add_patch(Polygon([(vc - 0.2, 0), (vc + 0.2, 0), (vc + 0.2, 4.0 - vc / 12 - 0.05), (vc - 0.2, 4.0 - vc / 12 - 0.05)], fc="#CBB89A", ec="none", zorder=1))
sax.plot([-3.4, 0], [3.25, 3.25], lw=0.9, color="#777777"); sax.text(-1.7, 3.4, "西館 2 階の床", fontsize=4.4, ha="center", color="#777777")
sax.plot([13.5, 13.5], [0, 2.27], lw=1.0, color=C["glass"])
for t_ in sorted(TR, key=lambda t_: -t_["u"]):
    u, v, d = t_["u"], t_["v"], t_["d"]; k = min(1, max(0, (u - 22.8) / 6.8))
    sax.add_patch(Polygon([(v - d / 2, 0), (v + d / 2, 0), (v + d / 2, top(v, u, d)), (v - d / 2, top(v, u, d))], fc=DCOL[d], ec="none", alpha=0.3 + 0.6 * (1 - k), zorder=3 + (1 - k)))
def person(v, h, c="#555555"):
    sax.add_patch(Circle((v, h - 0.11), 0.11, fc=c, ec="none", zorder=6))
    sax.add_patch(Polygon([(v - 0.13, 0), (v + 0.13, 0), (v + 0.11, h - 0.24), (v - 0.11, h - 0.24)], fc=c, ec="none", zorder=6))
person(4.2, 1.05, "#B08D57"); person(8.6, 0.95, "#B08D57"); person(10.6, 1.6)
for z in (0, 1, 2, 3, 4): sax.text(SV0 + 0.2, z, f"{z:.0f}", fontsize=4.2, va="center", color="#888888")
sax.text(0.8, 4.75, "越屋根", fontsize=4.4, ha="center", color="#555555")
sax.text(SV0, 5.15, "断面（北を見る、林を投影、手前ほど濃い）1/100　幹の上端は屋根の下（垂木の下端）、西吹き抜けでは越屋根の中 h4.4", fontsize=6, va="top", weight="bold")
for vv_, s in [(-1.7, "東の帯"), (0.8, "西吹き抜け"), (7.0, "ホール"), (12.75, "内縁側"), (14.25, "外縁側")]:
    sax.text(vv_, -0.28, s, fontsize=4.4, ha="center", va="top", color="#555555")

# ---------------------------------------------------------------- right column
import textwrap
RX = 232; yy = 286
def para(head, body, w=50, fs=5.6):
    global yy
    if head:
        fig.text(RX / 420, yy / 297, head, fontsize=8.5, weight="bold", va="top"); yy -= 5.6
    for s in body:
        for i, ln in enumerate(textwrap.wrap(s, w)):
            fig.text((RX + (0 if i == 0 else 2.5)) / 420, yy / 297, ("・" if i == 0 else "") + ln, fontsize=fs, va="top", color="#333333"); yy -= 2.9
        yy -= 0.7
    yy -= 1.5
para("考え方（3 版）", [
    f"あきは {P['GAP']} 以上。速く動けなくてよい、挟まらなければよい（ユーザー）。頭が挟まる開口（遊具の基準でおよそ 100〜230 mm）より広く、こどもは横向きなら抜けられ、大人もからだを横にすれば入れる（けがの子に手が届く）。株の中は触れあう（あき 0）。",
    "決めない：集まる場所や小部屋は描かない。疎密のむらでできた空き地（点線の輪）を、こどもが見つける。先生が何気なく「ここに座ろうね」と言えば、そこが場所になる。",
    "疎密：北西（西吹き抜けの奥）がいちばん密な茂み、南東（縁側・海峡の側）に向かって疎ら。そこにゆるいむらを重ねる。",
    "見る向きで景色が変わる（KAIT 工房に学ぶ）：3 つの群で列の向きを変え（西の群＝東西、海峡の群＝南北、縁側の群＝比叡山の向き）、株立ちを列の向きに並べる。列に沿うと透け、横切ると詰まる。",
    "どこにでも生やす：西吹き抜け（越屋根の光の中へ伸びる）と内縁側にも。生やさないのは海峡・東の帯・配膳の道だけ。架構の線の上も区別しない：立った位置がたまたま梁（2 枚組）のあいだなら、そのまま抜けて屋根まで（梁の板に当たる位置なら少しずらす）。",
    "内縁側のホールの南の端は減速の茂み（ここから南は 0〜2 歳の場所）：東西の列を 3 本、あき 0.7 の口を左右互い違いに開けた。大人はけがの子を抱えたまま S 字に抜けられ（赤の点線）、内縁側がそのまま医務への運ぶ道になる。こどもは走ったままでは抜けられない。",
    f"抜ける幹（青い輪、{sum(1 for t in TR if t.get('removable'))} 本）：ホールの中ほどの幹は、足もとのピンを抜いてくるっと回し、持ち上げて外せる（3 枚目）。全部外すとホールの中ほどが空く（行事・大掃除）。",
    "掃除：床は平らなので、お掃除ロボットが株と株のあいだ（0.4）を回れる。"
    "よじ登ってよい：2 本のあいだで背と足を突っ張って登れる（ユーザー）。"
    f"東西に抜ける筋：全体を置いてから、東の帯の側から縁側のガラス戸まで、抜く木が少なく短い経路を探し（折れてよい）、幅 0.9 にかかる木を抜いた（{len(F['CHANNEL']['removed'])} 本、長さ {F['CHANNEL']['length']:.1f} m）。床に印は付けない。",
    f"まっすぐ走れる線（幅 0.6）：最長 {F['RESULT']['longest_run']:.1f} m。",
    "幹：北山杉の間伐材（磨き丸太、群の単木の φ70・100 は太鼓落とし）、塗らない。足もとは床の穴に沓、上は垂木に金物で留める。",
])

fig.text(RX / 420, yy / 297, "模型 1/100：ピアノ線（mm）", fontsize=8.5, weight="bold", va="top"); yy -= 4.8
fig.text(RX / 420, yy / 297, f"長さ＝上端の高さ×10 − {MOD['TOP_GAP']}（屋根を外せるように控える）＋ 差し込み {MOD['EMBED']}（床 2 層を貫く）。株立ちは触れあわせて立てる", fontsize=5.4, va="top", color="#333333"); yy -= 4.4
WIRE = {0.05: "0.5", 0.07: "0.7", 0.1: "1.0", 0.2: "丸棒 2.0"}
Ls = {}
for t_ in TR:
    L = top(t_["v"], t_["u"], t_["d"]) * 10 - MOD["TOP_GAP"] + MOD["EMBED"]
    w = WIRE[t_["d"]]; Ls.setdefault(w, []).append(L)
for w in WIRE.values():
    if w not in Ls: continue
    arr = np.array(Ls[w])
    hist = {}
    for L in arr: hist[round(L)] = hist.get(round(L), 0) + 1
    s = "、".join(f"{k} mm ×{v}" for k, v in sorted(hist.items()))
    fig.text(RX / 420, yy / 297, f"{w}：{len(arr)} 本（計 {arr.sum() / 1000:.2f} m）", fontsize=5.8, weight="bold", va="top"); yy -= 3.2
    for ln in textwrap.wrap(s, 70):
        fig.text((RX + 3) / 420, yy / 297, ln, fontsize=5.2, va="top", color="#333333"); yy -= 2.8
    yy -= 0.8
fig.text(RX / 420, yy / 297, "長さは 1 mm 刻みにまとめた。1 本ずつの位置と長さは data/forest.json（xy_mm＝3dm の座標）。穴の径は模型のチャットで。", fontsize=5.2, va="top", color="#333333")

# legend
lx = PL; ly = 104
for k, (dd, s) in enumerate([(0.05, "φ50（ピアノ線 0.5）"), (0.07, "φ70（0.7）"), (0.1, "φ100（1.0）"), (0.2, "φ200（丸棒 2.0）")]):
    fig.patches.append(matplotlib.patches.Circle(((lx + 3 + k * 34) / 420, ly / 297), 1.0 / 420, transform=fig.transFigure, fc=DCOL[dd], ec="black", lw=0.3))
    fig.text((lx + 6 + k * 34) / 420, ly / 297, s, fontsize=5.6, va="center")
fig.text((lx + 142) / 420, ly / 297, "四角＝太鼓落とし　青い輪＝抜ける幹　緑：配膳の道　赤の点線：抱えて通れる道　点線：梁（上）", fontsize=5.6, va="center", color="#444444")

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"sodachiya_forest_01.{ext}"), dpi=200 if ext == "png" else None)
print("trees", n, nd, "clump", nclump, "run", F["RESULT"]["longest_run"], "removed", len(F["CHANNEL"]["removed"]))
