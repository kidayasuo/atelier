# ホールの北山杉の林 1/100：平面＋断面（北を見る）＋模型のピアノ線の表（A3 横）。3 版
# 配列は data/forest.json（scripts/forest_gen.py が作る）。座標は本館の (u, v)。
import json, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["pdf.fonttype"] = 42   # 文字は文字のまま（Type42、Illustrator で書体を置き換える）
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
fill(U0, U1, 12, 15, C["roof"]); fill(21, 22.5, -3.4, -0.2, C["strait"], 1.2); fill(21, 22.5, 13.5, 15, C["strait"], 1.2)
# あまのがわ（10-28 案4）：北の縁はゆらゆらの曲線（data/amanogawa.json の (v, 幅)、PCHIP）、南の縁は架構の線 u21
from scipy.interpolate import PchipInterpolator as _Pchip
_AMA = json.load(open(os.path.join(ROOT, "data", "amanogawa.json"), encoding="utf-8")); _C = np.array(_AMA["CONTROL"]); _wf = _Pchip(_C[:, 0], _C[:, 1])
_vs = np.linspace(-0.2, 13.5, 280); AMA_N = [(21.0 + float(_wf(v)), v) for v in _vs]
poly([W(u, v) for u, v in [(21.0, -0.2)] + AMA_N + [(21.0, 13.5)]], C["strait"], "none", 0, 1.2)
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
line(AMA_N, lw=0.9, c=C["wood"], z=6); line([(22.5, -3.4), (22.5, -0.2)], lw=0.9, c=C["wood"], z=6)   # 框：あまのがわの北の縁（曲線）
line([(U0, 13.5), (21, 13.5)], lw=1.2, c=C["glass"]); line([(21.0 + float(_wf(13.5)), 13.5), (U1, 13.5)], lw=1.2, c=C["glass"])
line([(U0, 15), (U1, 15)], lw=0.4, c="#777777", ls=(0, (6, 3)))
for uf in (21, 24, 27, 30):
    for vc in (0, 12): box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, fc="black", ec="black", z=7)
    if uf in (24, 27):                                             # beams overhead (2 leaves)
        line([(uf - 0.14, 0), (uf - 0.14, 12)], lw=0.35, c="#555555", ls=(0, (5, 3)), z=5)
        line([(uf + 0.14, 0), (uf + 0.14, 12)], lw=0.35, c="#555555", ls=(0, (5, 3)), z=5)
for v in (0, 1.6): line([(U0, v), (U1, v)], lw=0.35, c="#999999", ls=(0, (2, 2)), z=5)
_t = np.linspace(0, 2 * math.pi, 40)
# 飛び石は無し（10-28 案4）

# ---------------------------------------------------------------- food route, channel (found after planting), pockets (not designed)
fu, fv = P["FOOD"]
poly(rect(22.5, fu, 0.0, fv), "none", C["food"], 0.4, 3, ls=(0, (1, 1.5)))
pr = [W(23.5, -3.4), W(23.6, -1.8), W(23.75, 0.6), W(23.7, 6.0), W(23.6, 11.0), W(23.3, 12.6), W(21.0 + float(_wf(12.6)) + 0.1, 12.6), W(20.6, 12.6)]   # 配膳口 → ホールの南 → 内縁側で川へ下りて渡る（10-28 案4）
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
T(SL[len(SL) // 2][0] + 0.2, SL[len(SL) // 2][1] - 0.9, "抱えて通れる道\n（あき 0.7、まっすぐ）", 4.4, c="#C0392B", z=12)
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
        ax.add_patch(Circle((x, y), d / 2, fc=DCOL[d] if t_.get("tall") else "#E8D2B0", ec="black", lw=0.5 if t_.get("tall") else 0.2, zorder=9))
    if t_.get("removable"):
        ax.add_patch(Circle((x, y), d / 2 + 0.09, fc="none", ec="#2E6FA8", lw=0.4, zorder=9))

# group labels (row direction)
for g in P["GROUPS"]:
    a = math.radians(g["ang"]); ea = np.array([math.cos(a), math.sin(a)]); c0 = np.array(g["c"])
    ax.add_patch(FancyArrowPatch(W(*(c0 - ea * 0.8)), W(*(c0 + ea * 0.8)), arrowstyle="<->", mutation_scale=5, lw=0.5, color="#8a5a2b", zorder=11, alpha=0.7))
    T(c0[0] - 0.3, c0[1], g["name"] + "（列の向き）", 4.6, c="#8a5a2b", z=12)

T(26.4, -1.9, "西館の東の帯（はだし ±0）→ 遊戯室", 4.6, c="#666666", rotation=90)
T(21.75, 9.0, "あまのがわ（土足 −150）", 5.0, c="#6b5a3a", rotation=90)
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
fig.text(PL / 420, 290 / 297, "ホールの北山杉の林　平面 1/100（たたき台・6 版：すべて自立）", fontsize=11, weight="bold", va="top")
fig.text(PL / 420, 282 / 297, f"スパン 8–10（西吹き抜け・内縁側を含む）　間伐材 {n} 本（φ50 ×{nd[0.05]}・φ70 ×{nd[0.07]}・φ100 ×{nd[0.1]}・φ200 ×{nd[0.2]}、うち株立ち {nclump} 本）。幹と幹のあき {P['GAP']} 以上。\n"
         f"うすい帯＝置いたあとで見つけた東西の筋（あき 0.9、× は抜いた木）。点線の輪＝できた空き地（決めない）", fontsize=6.2, va="top", linespacing=1.5)

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
sax.plot([13.5, 13.5], [0, 2.445], lw=1.0, color=C["glass"])
for t_ in sorted(TR, key=lambda t_: -t_["u"]):
    u, v, d = t_["u"], t_["v"], t_["d"]; k = min(1, max(0, (u - 22.8) / 6.8))
    sax.add_patch(Polygon([(v - d / 2, 0), (v + d / 2, 0), (v + d / 2, t_["h"]), (v - d / 2, t_["h"])], fc=DCOL[d], ec="none", alpha=0.3 + 0.6 * (1 - k), zorder=3 + (1 - k)))
def person(v, h, c="#555555"):
    sax.add_patch(Circle((v, h - 0.11), 0.11, fc=c, ec="none", zorder=6))
    sax.add_patch(Polygon([(v - 0.13, 0), (v + 0.13, 0), (v + 0.11, h - 0.24), (v - 0.11, h - 0.24)], fc=c, ec="none", zorder=6))
person(4.2, 1.05, "#B08D57"); person(8.6, 0.95, "#B08D57"); person(10.6, 1.6)
for z in (0, 1, 2, 3, 4): sax.text(SV0 + 0.2, z, f"{z:.0f}", fontsize=4.2, va="center", color="#888888")
sax.text(0.8, 4.75, "越屋根", fontsize=4.4, ha="center", color="#555555")
sax.text(SV0, 5.15, "断面（北を見る、林を投影、手前ほど濃い）1/100　すべて床から自立。高い木は屋根の下 0.1 まで、低い木は 0.85〜1.1（先生の目線が上を越える）。頂部は丸い", fontsize=6, va="top", weight="bold")
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
nt = sum(1 for t in TR if t.get("tall")); nl = len(TR) - nt
para("考え方（6 版）", [
    f"すべて床から自立（ユーザー）。上は留めない。高さは幹の太さ（株は締めた本数の和）で決める：こどもが横に押す・揺らす力 0.3 kN を幹のどこに掛けても、根元の曲げがスギの短期の許容（14.8 N/mm²）を超えない高さ。φ100・φ200 と太い株は屋根の下 0.1 まで届く（高い木、{nt} 本）、細い株と φ70 は低い木 0.85〜1.1（{nl} 本）。",
    "低い木は先生の目の高さ（約 1.55）より十分低く、こどもの目の高さ（0.9〜1.0）は隠れる：こどもには林、先生にはこどもの頭が上越しに見える（内縁側・東の帯・あまのがわの 3 か所から、こどもの頭の約 9 割）。",
    "頂部は丸く削る（ぶつかっても痛くない）。株立ちは 2〜3 本を触れあわせ、何か所か金輪で締めて一体にし、同じ高さで丸める。",
    f"あきは {P['GAP']} 以上（挟まらなければよい、速く動けなくてよい）。株の中は触れあう（あき 0）。よじ登ってよい。床は平らで、お掃除ロボットが回れる。",
    "決めない：集まる場所や小部屋は描かない。疎密のむらでできた空き地（点線の輪）を、こどもが見つける。",
    "疎密と向き：北西（西吹き抜けの奥）がいちばん密、南東へ疎ら。3 つの群で列の向きを変え（西の群＝東西、あまのがわの群＝南北、縁側の群＝比叡山の向き）、株立ちを列の向きに並べる（KAIT 工房に学ぶ）。",
    "どこにでも生やす：西吹き抜け（高い木は越屋根の光の中へ）と内縁側にも。生やさないのはあまのがわ・東の帯・配膳の道だけ。梁の線も区別しない（梁の下の高い木は梁の下 0.1 まで）。",
    "減速の茂み（内縁側のホールの南の端、南は 0〜2 歳の場所）：東西の列を 3 本。口はガラス戸の側にそろえ、大人はけがの子を抱えたまま内縁側に沿ってまっすぐ抜けられる（赤の点線、あき 0.7）。走ってくるこどもは列に当たってガラス戸の側へ寄せられ、細い口で減速する。",
    f"東西に抜ける筋：全体を置いてから経路を探し、幅 0.9 にかかる木を抜いた（{len(F['CHANNEL']['removed'])} 本、{F['CHANNEL']['length']:.1f} m）。床に印は付けない。",
    f"抜ける幹（青い輪、{sum(1 for t in TR if t.get('removable'))} 本）：ホールの中ほどの低い木。ピンを押して 90° 回し、真上に抜く（3 枚目）。",
])

fig.text(RX / 420, yy / 297, "模型 1/100：ピアノ線（mm）", fontsize=8.5, weight="bold", va="top"); yy -= 4.8
fig.text(RX / 420, yy / 297, f"長さ＝高さ×10 ＋ 差し込み {MOD['EMBED']}（床 2 層を貫く）。高い木は屋根の下 1 mm。株立ちは触れあわせて立て、細い糸で締める", fontsize=5.4, va="top", color="#333333"); yy -= 4.4
WIRE = {0.05: "0.5", 0.07: "0.7", 0.1: "1.0", 0.2: "丸棒 2.0"}
Ls = {}
for t_ in TR:
    L = t_["h"] * 10 + MOD["EMBED"]
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
fig.text((lx + 142) / 420, ly / 297, "濃い・太い縁＝高い木、うすい＝低い木　四角＝太鼓落とし　青い輪＝抜ける幹　緑：配膳の道　赤の点線：抱えて通れる道　点線：梁（上）", fontsize=5.6, va="center", color="#444444")

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"sodachiya_forest_01.{ext}"), dpi=200 if ext == "png" else None)
print("trees", n, nd, "clump", nclump, "run", F["RESULT"]["longest_run"], "removed", len(F["CHANNEL"]["removed"]))
