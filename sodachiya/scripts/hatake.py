# 育ち舎　表の畑と火のオーブン（ひろばの菜園とかまど）：プレゼン4枚目の下の段の図（アプローチ係 10-28、プレゼンの準備の項 20261027-2333-present-2）
# 枠 218×143 mm（横長）。左：ひろばの平面 1/100（道路の座標 s・d、s を右へ、道路を上に）。右：一年の畑と、雨・土・火のめぐり（略図）。
# 寸法はすべて data/approachA.json（approachA.py を読み込んで同じ形を使う）。文字は Type42（scripts/fonts42.py）。
# 使い方: python3 hatake.py   → out/sodachiya_hatake.pdf（と確かめ用の .png）
import os, sys, tempfile, math
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUTD = os.path.join(ROOT, "out")
os.environ["OUT"] = tempfile.mkdtemp()          # approachA が書く図は捨てる
sys.path.insert(0, HERE)
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, FancyArrowPatch
from shapely.geometry import Polygon as SP, box
import approachA as A
plt.close("all")
import fonts42  # noqa: F401

MM = 1 / 25.4
FW, FH = 218, 143
C = dict(plaza="#F1E6CF", arai="#EDE9E1", bed="#D9E6BF", green="#5a7a3a", leaf="#8DB36A", wood="#8a5a2b", blue="#3d7fb0",
         water="#BFD9EA", fire="#D4572A", bldg="#D8D3CB", ink="#222222", sub="#555555", road="#E9E9E6", soil="#C9A97A")

def sd(p):                                      # 3dm (m) -> 図の (x, y) = (s, −d)
    s, d = A.inv(p); return (s, -d)
def sdl(pts): return [sd(p) for p in pts]
def S(s, d): return (s, -d)
def sr(s0, s1, d0, d1): return [S(s0, d0), S(s1, d0), S(s1, d1), S(s0, d1)]

fig = plt.figure(figsize=(FW * MM, FH * MM))
# ---------------------------------------------------------------- 平面 1/100
X0, X1, Y0, Y1 = 17.0, 31.4, -13.9, -4.3       # s 17.0〜31.4、d 4.3〜13.9（m）。道路の側（職員の駐輪）は外構の図に
PW, PH = (X1 - X0) * 10, (Y1 - Y0) * 10         # mm（1/100）
PLx, PLy = 6, 36
ax = fig.add_axes([PLx / FW, PLy / FH, PW / FW, PH / FH])
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.axis("off")
def poly(pts, fc="none", ec="none", lw=0.5, z=2, ls="-", alpha=1):
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, alpha=alpha))
def line(pts, c=C["ink"], lw=0.5, z=5, ls="-"):
    a = np.array(pts); ax.plot(a[:, 0], a[:, 1], c=c, lw=lw, zorder=z, ls=ls, solid_capstyle="butt")
def T(p, s, fs=5, c=C["ink"], ha="center", va="center", **k):
    ax.text(p[0], p[1], s, fontsize=fs, color=c, ha=ha, va=va, zorder=30, **k)
def shp(g):
    for q in getattr(g, "geoms", [g]):
        if q.geom_type == "Polygon" and not q.is_empty: yield sdl(list(q.exterior.coords))

# 道路と歩道（開放）
poly([S(X0 - 1, -2), S(X1 + 1, -2), S(X1 + 1, 0), S(X0 - 1, 0)], fc=C["road"], z=1)
sw = A.SIDEWALK
poly(sr(max(sw["s"][0], X0 - 1), sw["s"][1], *sw["d"]), fc="#F4F1EA", ec="none", z=1.2)
line([S(X0 - 1, 0), S(X1 + 1, 0)], c=C["ink"], lw=0.35, z=6, ls=(0, (6, 2, 1, 2)))
# 建物：西館（キッチン）と本館
for g in shp(A.WB): poly(g, fc=C["bldg"], ec=C["ink"], lw=0.9, z=3)
HK = SP(A.rect(-0.1, 57.34, -0.35, 13.5, 96))
for g in shp(HK): poly(g, fc=C["bldg"], ec=C["ink"], lw=0.9, z=3)
T(S(30.35, 7.4), "西館\nキッチン", 5.2, C["ink"], linespacing=1.2)
# 下屋（頭上、破線）
for g in shp(A.LEAN_ROOF): poly(g, fc="#E7D6BB", ec=C["sub"], lw=0.45, z=2.6, ls=(0, (3, 1.5)), alpha=0.85)
T(S(27.9, 12.7), "下屋 h2.6（破線）", 4.0, C["sub"])
# ひろば・洗い出しの道
for g in shp(A.plz): poly(g, fc=C["plaza"], z=2.2)
poly(sr(A.S_PATH0, 29.5, A.HEDGE_D + A.HW, A.WALL_D + 0.3), fc=C["arai"], z=2.3)
# 生垣・塀（道路側の大和張り）
for h in A.HEDGE:
    hh = [sd(A.P(*q)) for q in h]; line(hh, c="#6f9a4a", lw=2.2, z=6)
_pd = A.STAFF_BIKE["pocket"][2]
line([S(22.7, _pd), S(A.SX, _pd)], c=C["wood"], lw=1.4, z=6)
T(S(20.0, _pd - 0.0), "", 4.0)
T(S(22.4, 4.6), "大和張りの塀 h1.8", 4.0, C["wood"])
T(S(19.2, 4.6), "↑ 道路の側", 4.0, C["sub"])
T(S(23.0, 13.75), "本館", 5.0, C["ink"])
# 手水（屋根は無し、10-30）
poly(sr(18.9, 19.8, 10.7, 11.25), fc="#B9C2C8", ec="#555555", lw=0.5, z=8)
T(S(19.35, 12.3), "手水", 4.4)
# 菜園：畝 3 本（南から 大豆・カブとダイコン・サツマイモ）
crops = [c for c, _ in A._D["BED_CROPS"]["beds"]]
for k, (b, crop) in enumerate(zip(A.BEDS, crops)):
    poly(sr(*b), fc=C["bed"], ec=C["green"], lw=0.6, z=6)
    for d in np.arange(b[2] + 0.3, b[3], 0.5):
        ax.add_patch(Circle(S((b[0] + b[1]) / 2, d), 0.13, fc=C["leaf"], ec="none", zorder=6.1))
    T(S((b[0] + b[1]) / 2, (b[2] + b[3]) / 2), crop, 4.6, "#2f4a1e", rotation=90,
      bbox=dict(fc="#EEF3E2", ec="none", pad=0.5, alpha=0.92))
T(S(20.85, 10.35), "菜園　畝0.9×3.1・高さ0.4", 4.0, C["green"], va="top", ha="left")
# 雨水：受け桝 → 地中の雨水槽 → 手押しポンプ
R = A.RAIN; tk, ri, pm = R["S_TANK"], R["S_INLET"], R["S_PUMP"]
poly(sr(tk["s"][0], tk["s"][1], *tk["d"]), ec=C["blue"], lw=0.6, z=7, ls=(0, (2.5, 1.5)))
ax.add_patch(Circle(S(ri[0], ri[1]), ri[2], fc=C["water"], ec=C["blue"], lw=0.6, zorder=8))
line([S(tk["s"][0], (tk["d"][0] + tk["d"][1]) / 2), S(pm[0], tk["d"][1] - 0.2), S(*pm)], c=C["blue"], lw=0.5, z=7, ls=(0, (1, 1)))
ax.add_patch(Rectangle((pm[0] - 0.15, -pm[1] - 0.15), 0.3, 0.3, fc=C["blue"], ec="none", zorder=8.5))
T(S(27.2, 6.7), "地中の雨水槽 約2m³", 4.0, C["blue"], va="top")
T(S(27.0, 6.0), "石の受け桝", 3.8, C["blue"], va="top")
T(S(pm[0] + 0.3, pm[1] - 0.05), "手押しポンプ", 4.2, C["blue"], ha="left")
# かまど（火のオーブン）と薪棚
s0, s1, d0, d1 = A.KAM
ax.add_patch(Circle(S((s0 + s1) / 2, (d0 + d1) / 2), 1.3, fc="#E3D3B8", ec="none", zorder=2.5))
poly(sr(s0, s1, d0, d1), fc=C["soil"], ec="#6b4b2a", lw=0.7, z=8)
ax.add_patch(Circle(S((s0 + s1) / 2, (d0 + d1) / 2), 0.22, fc=C["fire"], ec="none", zorder=8.2))
poly(sr(*A.WOOD), fc="#a07a4c", ec=C["wood"], lw=0.3, z=8)
T(S(24.9, 8.45), "かまど（火のオーブン）", 4.6, C["fire"], weight="bold")
T(S(24.8, 5.75), "薪棚", 3.8, C["wood"], va="top")
# お茶の縁台（下屋の下）
for (va, vb) in A.TEA["benches_v"]:
    poly(sdl(A.rect(19.6, 20.5, va, vb, 2)), fc="#B98E5E", ec=C["wood"], lw=0.4, z=9)
poly(sdl(A.rect(19.3, 20.8, *A.TEA["shelf_v"], 2)), fc="#8a6a44", z=9)
_bc = sd(A.W(20.05, sum(A.TEA["benches_v"][1]) / 2)); T((_bc[0] - 0.75, _bc[1]), "お茶の縁台", 4.2, C["wood"], ha="right")
# 入江の木
tp = S(*A.inv(A.P(24.4, 9.6)))
ax.add_patch(Circle(tp, 1.9, fc="#9DBE7A", ec="#6f9a4a", lw=0.4, alpha=0.35, zorder=4))
ax.add_patch(Circle(tp, 0.12, fc=C["wood"], ec="none", zorder=4.1))
T(S(24.4, 11.0), "入江の木", 4.2, "#4f7a32")
# 「今日のごはん」の窓（キッチンから）
T(S(30.35, 9.1), "南の面に\n「今日のごはん」\nの窓", 3.8, C["sub"], linespacing=1.2)
# こどもの一巡り：育てる → 水をやる → 焼く → 食べる
loop = [S(21.2, 9.3), S(22.6, 8.1), S(24.1, 7.2), S(24.6, 5.9) if False else S(23.4, 5.6)]
steps = [(S(19.0, 7.35), "1"), (S(22.45, 8.05), "2"), (S(23.85, 6.6), "3"), ((_bc[0] + 0.15, _bc[1] - 0.75), "4")]
for (p, k) in steps:
    ax.add_patch(Circle(p, 0.33, fc="white", ec=C["fire"], lw=0.8, zorder=20))
    T(p, k, 5.2, C["fire"], weight="bold")
for a, b in zip(steps, steps[1:]):
    ax.add_patch(FancyArrowPatch(a[0], b[0], arrowstyle="-|>", mutation_scale=5, lw=0.8, color=C["fire"],
                                 connectionstyle="arc3,rad=-0.25", shrinkA=6, shrinkB=6, zorder=19))
# 方位と縮尺
nx, ny = 17.25, -5.6
ang = math.atan2(-(A.inv((0, 1))[1] - A.inv((0, 0))[1]), A.inv((0, 1))[0] - A.inv((0, 0))[0])
ax.annotate("", xy=(nx + 0.9 * math.cos(ang), ny + 0.9 * math.sin(ang)), xytext=(nx, ny),
            arrowprops=dict(arrowstyle="-|>", lw=0.7, color="black"), zorder=30)
T((nx + 1.25 * math.cos(ang), ny + 1.25 * math.sin(ang)), "N", 5.5)
bx, by = 21.6, -13.0
for i in range(5):
    ax.add_patch(Rectangle((bx + i, by), 1, 0.18, fc="black" if i % 2 == 0 else "white", ec="black", lw=0.3, zorder=30))
T((bx, by - 0.35), "0", 4.2); T((bx + 5, by - 0.35), "5 m", 4.2); T((bx - 0.25, by + 0.09), "1/100", 4.6, ha="right")

# ---------------------------------------------------------------- 表題・一年の畑（平面の下）・右の列
RX = PLx + PW + 5; RW_ = FW - RX - 4
def ftxt(x, y, s, fs=5.5, **k): fig.text(x / FW, 1 - y / FH, s, fontsize=fs, va="top", **k)
ftxt(PLx, 3.5, "表の畑と火のオーブン", 9.5, weight="bold")
ftxt(PLx + 44, 5.0, "ひろばの菜園とかまど　平面 1/100", 5.8, color=C["sub"])
# 一年の畑（4月〜3月）：平面の下の帯
GY = FH - PLy + 2.5; GH = 29
ftxt(PLx, GY, "一年の畑（行事の作物）", 6.4, weight="bold")
ftxt(PLx + 34, GY + 0.6, "大豆とカブ・ダイコンの畝は年ごとに入れ替える（大豆の根が土を肥やす）。豆殻は柊鰯の枝に。", 4.2, color=C["sub"])
NW = 20
gx = fig.add_axes([(PLx + NW) / FW, (FH - GY - GH) / FH, (PW - NW) / FW, (GH - 5) / FH])
months = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
gx.set_xlim(0, 12); gx.set_ylim(-0.45, 3.95); gx.axis("off")
RS = 1.25
for i, mo in enumerate(months):
    gx.text(i + 0.5, 3.8, f"{mo}月", fontsize=4.2, ha="center", va="center", color=C["sub"])
    gx.plot([i, i], [-0.4, 3.15], lw=0.25, color="#d8d8d8", zorder=0)
gx.plot([12, 12], [-0.4, 3.15], lw=0.25, color="#d8d8d8", zorder=0)
m = lambda mo, f=0.0: (mo - 4) % 12 + f
def bar(row, a, b, c, label="", tc="white"):
    row = row * RS
    gx.add_patch(Rectangle((a, row - 0.3), b - a, 0.6, fc=c, ec="none", zorder=2))
    if label: gx.text((a + b) / 2, row, label, fontsize=4.1, ha="center", va="center", color=tc, zorder=3)
def ev(row, x, label, ha="center"):
    row = row * RS
    gx.plot([x], [row + 0.42], marker="v", ms=2.6, color=C["fire"], zorder=4)
    gx.text(x, row + 0.55, label, fontsize=4.0, ha=ha, va="bottom", color=C["fire"], zorder=4, weight="bold")
ROWS = [(2, "大豆の畝"), (1, "カブ・ダイコンの畝"), (0, "サツマイモの畝")]
for row, name in ROWS:
    fig.text((PLx + NW - 1.5) / FW, (FH - GY - GH) / FH + (row * 1.25 + 0.45) / 4.4 * (GH - 5) / FH, name,
             fontsize=4.4, ha="right", va="center", color=C["green"])
bar(2, m(6), m(8, 0.5), "#7FA85C", "まく・育てる"); bar(2, m(8, 0.5), m(11, 0.6), "#C7B46A", "乾かす", "#3a3a1a")
ev(2, m(8, 0.4), "枝豆"); ev(2, m(2, 0.1), "節分の豆まき")
bar(1, m(4), m(8, 0.9), "#E2D9A6", "夏野菜", "#4a4a1a"); bar(1, m(9), m(1, 0.4), "#7FA85C", "カブ・ダイコン"); ev(1, m(1, 0.2), "七草がゆ")
bar(0, m(5), m(10, 0.6), "#A9799A", "苗を植える・育てる"); ev(0, m(10, 0.5), "芋掘り → かまどで焼き芋"); bar(0, m(11), 12, "#7FA85C", "葉もの（給食に）")

# 右の列：こどもの一巡り
ftxt(RX, 12, "こどもの一巡り", 6.6, weight="bold")
for k, t in enumerate(["畝で育てる", "雨の水を汲んでやる", "とれたものをかまどで焼く", "下屋の縁台でみんなで食べる"]):
    y = 19 + k * 5.2
    fig.text((RX + 2.2) / FW, 1 - y / FH, str(k + 1), fontsize=5.2, color=C["fire"], weight="bold", ha="center", va="center",
             bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec=C["fire"], lw=0.7))
    fig.text((RX + 5.5) / FW, 1 - y / FH, t, fontsize=5.2, va="center")
ftxt(RX, 39, "見える台所（「今日のごはん」の窓）の前で、\n食べものができるところを毎日見て、自分の\n手で育て、火で焼いて、食べる。", 4.6, color=C["ink"], linespacing=1.45)

# 右の列：雨・土・火のめぐり（断面の略図、縮尺なし）
SY = 52; SH = 58
ftxt(RX, SY, "雨・土・火のめぐり", 6.6, weight="bold")
ftxt(RX + 25, SY + 0.9, "断面の略図", 4.4, color=C["sub"])
SXH = RW_ * 5.6 / 10
sx = fig.add_axes([RX / FW, (FH - SY - 4 - SXH) / FH, RW_ / FW, SXH / FH])
sx.set_xlim(0, 10); sx.set_ylim(-1.9, 3.7); sx.axis("off")
sx.add_patch(Rectangle((0, -1.9), 10, 1.9, fc="#EFE6D6", ec="none", zorder=0))            # 地中
sx.plot([0, 10], [0, 0], lw=0.8, color=C["ink"], zorder=5)
sx.text(0.05, -0.12, "GL", fontsize=3.8, va="top", color=C["sub"])
sx.add_patch(Rectangle((9.2, 0), 0.8, 3.5, fc=C["bldg"], ec=C["ink"], lw=0.6, zorder=3))   # 西館の壁
sx.text(9.6, 1.8, "西館", fontsize=4.0, ha="center", rotation=90, color=C["ink"])
sx.plot([6.9, 9.2], [2.55, 2.75], lw=1.6, color="#555555", zorder=4)                       # 下屋
sx.plot([7.25, 7.25], [0, 2.58], lw=0.8, color=C["wood"], zorder=3)
sx.text(8.1, 2.95, "下屋", fontsize=4.0, ha="center", color=C["sub"])
for x0 in (7.5, 8.0, 8.5):
    sx.plot([x0, x0 - 0.12], [3.65, 3.2], lw=0.45, color=C["blue"])
sx.plot([6.95, 6.95], [2.5, 0.1], lw=1.0, color=C["blue"], ls=(0, (0.6, 0.6)), zorder=4)     # 鎖樋
sx.text(6.8, 1.5, "鎖樋", fontsize=3.9, ha="right", color=C["blue"])
sx.add_patch(Rectangle((6.6, -0.25), 0.7, 0.3, fc=C["water"], ec=C["blue"], lw=0.5, zorder=4))  # 受け桝
sx.add_patch(Rectangle((5.0, -1.55), 2.9, 1.1, fc=C["water"], ec=C["blue"], lw=0.6, zorder=3))   # 雨水槽（土かぶり 0.3）
sx.text(6.45, -1.0, "地中の雨水槽 約2m³", fontsize=3.9, ha="center", color="#1f4f75")
sx.plot([5.0, 3.95, 3.95], [-1.25, -1.25, 0.9], lw=0.6, color=C["blue"], zorder=3)
sx.add_patch(Rectangle((3.8, 0), 0.3, 0.9, fc=C["blue"], ec="none", zorder=4))
sx.plot([4.1, 4.55], [0.85, 1.05], lw=0.9, color=C["blue"], zorder=4)
sx.text(3.95, 1.2, "ポンプ", fontsize=3.9, ha="center", color=C["blue"])
sx.add_patch(Rectangle((0.4, 0), 1.7, 0.4, fc=C["soil"], ec=C["green"], lw=0.5, zorder=3))      # 畝
for x0 in np.arange(0.6, 2.1, 0.35):
    sx.add_patch(Circle((x0, 0.56), 0.17, fc=C["leaf"], ec="none", zorder=3.5))
sx.text(1.25, -0.15, "畝", fontsize=3.9, ha="center", va="top", color=C["green"])
sx.add_patch(Circle((2.85, 1.05), 0.16, fc="#F3D9B8", ec=C["ink"], lw=0.4, zorder=5))          # こども（約1.0 m）
sx.plot([2.85, 2.85], [0.89, 0.35], lw=0.8, color=C["ink"], zorder=5)
sx.plot([2.7, 2.85, 3.0], [0, 0.35, 0], lw=0.8, color=C["ink"], zorder=5)
sx.plot([2.85, 2.45], [0.72, 0.6], lw=0.8, color=C["ink"], zorder=5)
sx.add_patch(Rectangle((2.25, 0.5), 0.22, 0.2, fc=C["blue"], ec="none", zorder=5))             # じょうろ
sx.add_patch(Rectangle((4.75, 0), 1.0, 0.8, fc=C["soil"], ec="#6b4b2a", lw=0.6, zorder=3))      # かまど
sx.add_patch(Circle((5.25, 0.35), 0.18, fc=C["fire"], ec="none", zorder=4))
for k in range(3):
    sx.plot([5.05 + 0.2 * k, 5.15 + 0.2 * k], [0.95, 1.55], lw=0.4, color="#999999", zorder=2)
sx.text(5.25, 1.7, "かまど", fontsize=4.2, ha="center", color=C["fire"], weight="bold")
sx.annotate("", xy=(4.8, 0.95), xytext=(2.3, 1.5), arrowprops=dict(arrowstyle="-|>", lw=0.6, color=C["fire"], connectionstyle="arc3,rad=-0.35"))
sx.annotate("", xy=(1.3, 1.05), xytext=(4.8, 2.1), arrowprops=dict(arrowstyle="-|>", lw=0.6, color="#8a6a44", ls=(0, (2, 1.2)), connectionstyle="arc3,rad=0.35"))
sx.text(3.0, 2.55, "灰と生ごみはコンポストから土へ", fontsize=3.8, ha="center", color="#8a6a44")
ftxt(RX, SY + 6 + SXH, "雨は屋根から鎖樋・受け桝を通って地中の槽へ\n（土かぶり0.3、上は真砂土で歩ける）。こどもが\nポンプで汲んで畝へ。とれたものはかまどで焼き、\n灰と生ごみは土に返す。水やり用で、飲まない。",
     4.3, color=C["ink"], linespacing=1.45)
fig.text(PLx / FW, 1.5 / FH, "寸法は data/approachA.json（外構の図 approachA.py と同じ）。かまどは行事のときだけ使う（下屋から約2 m、建物から4 m以上）。",
         fontsize=3.9, color=C["sub"], va="bottom")

os.makedirs(OUTD, exist_ok=True)
fig.savefig(os.path.join(OUTD, "sodachiya_hatake.pdf"))
fig.savefig(os.path.join(OUTD, "sodachiya_hatake.png"), dpi=200)
print("wrote", os.path.join(OUTD, "sodachiya_hatake.pdf"))
