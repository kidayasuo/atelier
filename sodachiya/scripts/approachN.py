# 育ち舎 配置図 1/200（北半分）：西館の周り・読書の庭・機械室（A3 縦）  2026-10-24
import os, sys, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Circle, Arc, FancyArrow
from shapely.geometry import LineString, Point
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import north_common as N

ROOT = N.ROOT; OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
xmin, xmax, ymin, ymax = -28.0, 6.0, -50.0, 1.5                 # 1/200: 1 m = 5 mm
PL, PB = 14, 122
ax = fig.add_axes([PL / 297, PB / 420, (xmax - xmin) * 5 / 297, (ymax - ymin) * 5 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

C = dict(hedge="#6E9A4E", mid="#93B873", plant="#BFD9A2", moss="#7FA866", gravel="#D6D1C7", arai="#DCD3C3", rain="#B9D3E6", bld="#F2F0EC",
         fence="#7a5a36", red="#C8372D", door="#3d7fb0", line="#333333")
def poly(g, fc="none", ec="black", lw=0.4, z=2, hatch=None, ls="-"):
    for q in getattr(g, "geoms", [g]):
        if q.geom_type != "Polygon" or q.is_empty: continue
        ax.add_patch(MP(list(q.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, hatch=hatch, ls=ls))
def line(pts, lw=0.5, c="black", ls="-", z=4): xs, ys = zip(*pts); ax.plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(p, s, size=6, z=12, **kw): ax.text(p[0], p[1], s, fontsize=size, ha=kw.pop("ha", "center"), va=kw.pop("va", "center"), zorder=z, **kw)
def num(p, k): ax.add_patch(Circle(p, 0.62, fc="white", ec="black", lw=0.35, zorder=20)); T(p, str(k), 5.2, z=21)

# site, setback, roads
line(list(N.SITE.exterior.coords), 0.9)
line(list(N.SETB.exterior.coords), 0.3, "#777777", (0, (4, 3)))
ang_w = math.degrees(math.atan2(N.tt[1], N.tt[0])); ang_n = math.degrees(math.atan2(N.t2[1], N.t2[0]))
T(N.P(42, -2.2), "西の道路", 7, rotation=ang_w - 180 if ang_w > 90 else ang_w, color="#555555")
T(N.T(18, -2.0), "北西の道路（細い）", 7, rotation=ang_n, color="#555555")
T(N.P(44, 0.5), "後退の線（道路から1.0）", 4.6, rotation=ang_w - 180 if ang_w > 90 else ang_w, color="#777777")

# buildings
poly(N.WS, C["bld"], "black", 0.9, 3); poly(N.HONKAN, C["bld"], "black", 0.9, 3); poly(N.MECH, C["bld"], "black", 0.9, 3)
T(N.WS.centroid.coords[0], "西館\n（キッチン・はれのま・遊戯室）", 7.5)
T(N.W(40, 6.5), "本館", 8)
T(N.MECH.centroid.coords[0], "機械室\n（おむすび）", 6)

# ground
poly(N.LOW, C["plant"], "#5a7a3a", 0.3, 5)
poly(N.HEDGE, C["hedge"], "#3f5e2c", 0.3, 5)
poly(N.MID, C["mid"], "#4d7040", 0.3, 5)
poly(N.GAPRON, C["arai"], "#888888", 0.3, 5)
poly(N.GRAVEL, C["gravel"], "#999999", 0.25, 5)
poly(N.STAFF_PATH, C["arai"], "#888888", 0.3, 5)
poly(N.APRON, C["arai"], "#888888", 0.3, 5)
poly(N.MAPRON, C["arai"], "#888888", 0.3, 5)
poly(N.RAINGARDEN, C["rain"], "#5d8fb3", 0.3, 6)
poly(N.READ, C["moss"], "#4d7040", 0.3, 5, hatch="....")
poly(N.KOMICHI, C["arai"], "#888888", 0.3, 5)
# stepping stones on the staff path
for s in np.arange(29.6, 37.8, 0.75):
    q = Point(N.P(s, 0.45)).buffer(0.22, resolution=6)
    if q.within(N.STAFF_PATH.buffer(0.05)): poly(q, "#BFB6A6", "#777777", 0.25, 6)

# fence (board fence h1.8) + gate of 北の小径
for f in N.FENCE: line(f, 2.0, C["fence"], z=8)
g0, g1 = N.GATE
line([g0, g1], 0.5, C["fence"], (0, (2, 1.5)), 8)
v = np.array(g1) - np.array(g0); L = np.linalg.norm(v) / 2; a0 = math.degrees(math.atan2(v[1], v[0]))   # double gate, both leaves open outward
for h, th0 in ((g0, a0), (g1, a0 + 90)):
    ax.add_patch(Arc(h, 2 * L, 2 * L, theta1=th0, theta2=th0 + 90, lw=0.35, color=C["fence"], zorder=8))
    ang = a0 + 90
    line([h, (h[0] + L * math.cos(math.radians(ang)), h[1] + L * math.sin(math.radians(ang)))], 0.8, C["fence"], z=8)

# machine-room door (double, opens outward to the road)
m0, m1 = N.MDOOR; mv = np.array(m1) - np.array(m0); ml = np.linalg.norm(mv) / 2; am = math.degrees(math.atan2(mv[1], mv[0]))
mid = tuple(np.array(m0) + mv / 2)
line([m0, m1], 1.4, "white", z=9); line([m0, m1], 0.3, C["door"], (0, (1.5, 1)), z=10)
for h, a, sgn in ((m0, am, -1), (m1, am + 180, 1)):
    e = (h[0] + ml * math.cos(math.radians(a + sgn * 90)), h[1] + ml * math.sin(math.radians(a + sgn * 90)))
    line([h, e], 0.7, C["door"], z=10)
    th = sorted([a, a + sgn * 90]); ax.add_patch(Arc(h, 2 * ml, 2 * ml, theta1=th[0], theta2=th[1], lw=0.35, color=C["door"], zorder=10))

# kitchen staff door (W871, opens outward to the west)
hd = (-23.58, -36.44); dv = np.array([0.0, 0.87]); ad = 90.0
line([hd, (hd[0] - 0.87, hd[1])], 0.7, C["door"], z=10)
ax.add_patch(Arc(hd, 1.74, 1.74, theta1=90, theta2=180, lw=0.35, color=C["door"], zorder=10))

# 搬入の大戸: two sliding leaves (closed position) and arrows
d0, d1 = N.T(5.28, 0.93), N.T(8.98, 0.93)
line([d0, d1], 1.6, C["door"], z=10)
for a, b in ((N.T(7.0, 0.75), N.T(3.6, 0.75)), (N.T(7.26, 0.75), N.T(10.66, 0.75))):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", lw=0.4, color=C["door"]), zorder=11)

# windows (marks on the wall): 遊戯室の地窓・覗き窓, 遊戯室の北の窓, 本の奥の地窓
for y0, y1 in ((-30.3, -29.7), (-27.1, -26.5), (-23.9, -23.2), (-28.9, -28.6), (-28.2, -27.9), (-25.6, -25.3), (-25.0, -24.7)):
    x = -24.35 - 0.0035 * (y0 + 27); line([(x - 0.1, y0), (x - 0.1, y1)], 1.6, "#8FB8D8", z=9)
line([(-12.2, -13.92), (-10.0, -14.2)], 1.6, "#8FB8D8", z=9)
line([(-8.62, -12.7), (-8.35, -8.9)], 1.6, "#8FB8D8", z=9)

# trees: モミジ (existing in the body 3dm)
ax.add_patch(Circle(N.MOMIJI, 1.25, fc="none", ec="#B8452C", lw=0.6, zorder=9)); ax.add_patch(Circle(N.MOMIJI, 0.08, fc="#B8452C", zorder=9))

# number markers
items = [
    (N.P(40.9, 0.38), "香りの刈り込み h1.2〜1.5：キンモクセイ・ギンモクセイ（窓と戸の無い壁の前、北西の面にも）"),
    (N.P(33.0, 0.45), "調理の職員の道（飛び石と洗い出し、搬入路から戸まで）"),
    (N.P(37.0, -0.9), "調理の職員の戸（外開き0.87）"),
    (N.P(48.3, -0.9), "雨庭（北の鎖樋、浸透）。まわりと窓の前は低い香りの草 h0.3〜0.6：ローズマリー・ラベンダー・タイム・ツワブキ・ヤブラン"),
    (N.T(7.1, -0.9), "搬入の大戸の前（洗い出し）。引き戸が左右へ1.8走る所は壁ぎわを空ける"),
    (N.T(16.6, 3.0), "読書の庭：モミジ1本と苔（入らない坪庭）"),
    (N.T(16.6, 0.25), "板塀 h1.8（後退の線の上、セキュリティの線）。道路との帯に花の低木 h0.6〜1.0：ユキヤナギ・クチナシ・アベリア（機械室の脇も）"),
    (N.T(22.9, 2.3), "本館の北西の角の両開きの木戸 h1.8（外開き、鍵）：左の扉で読書の庭へ、右の扉で北の小径へ。庭師と点検の人の入口、だいさんかくの北の口"),
    (N.T(28.7, 0.45), "機械室の戸（北西の面、両開き約1.6）と前の洗い出し"),
    ((-8.0, -11.4), "本の奥の地窓（読書の庭を見る）"),
    ((-11.3, -15.2), "遊戯室の北の窓（腰掛け）"),
    ((-25.4, -27.0), "遊戯室の地窓・覗き窓（前は低い植栽）"),
    (N.P(45.0, 0.9), "壁の足もとの砂利 0.2（跳ね返り止め、点検）"),
]
for k, (p, t) in enumerate(items, 1): num(p, k)

# north arrow
ax.annotate("", xy=(3.5, -14.0), xytext=(3.5, -17.0), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
T((3.5, -13.2), "N", 8, weight="bold")
# scale bar
sb0 = (-26.0, -48.6)
for i in range(5): ax.add_patch(MP([(sb0[0] + 2 * i, sb0[1]), (sb0[0] + 2 * i + 2, sb0[1]), (sb0[0] + 2 * i + 2, sb0[1] + 0.35), (sb0[0] + 2 * i, sb0[1] + 0.35)], fc="black" if i % 2 == 0 else "white", ec="black", lw=0.3))
T((sb0[0], sb0[1] - 0.8), "0", 5); T((sb0[0] + 10, sb0[1] - 0.8), "10 m", 5)
T((-3, -47.0), "南は「配置図（南半分）」へ続く", 5.5, color="#777777")

# page text
fig.text(14 / 297, 404 / 420, "育ち舎　配置図（北半分）　西館の周り・読書の庭・機械室", fontsize=12, weight="bold")
fig.text(14 / 297, 396 / 420, "1/200（A3）　2026-10-24　西館の外は後退の帯（幅1.0）だけ。戸の前を空け、ほかは香りと花の植栽。読書の庭は板塀で閉じる坪庭、機械室は道路から。", fontsize=6.6)
LX = 196
fig.text(LX / 297, 388 / 420, "番号", fontsize=7, weight="bold")
for k, (p, t) in enumerate(items, 1):
    y = (381 - 10.2 * (k - 1)) / 420
    fig.add_artist(Circle(((LX + 2.2) / 297, y + 0.002), 0.0075, transform=fig.transFigure, fc="white", ec="black", lw=0.35))
    fig.text((LX + 2.2) / 297, y + 0.002, str(k), fontsize=5, ha="center", va="center")
    import textwrap
    fig.text((LX + 6) / 297, y + 0.006, "\n".join(textwrap.wrap(t, 40)), fontsize=5.6, va="top", linespacing=1.3)
# legend swatches
ly = 240
for c, t, h in ((C["hedge"], "香りの刈り込み h1.2〜1.5", None), (C["mid"], "花の低木 h0.6〜1.0", None), (C["plant"], "低い香りの草 h0.3〜0.6", None), (C["moss"], "苔", "...."), (C["gravel"], "砂利", None), (C["arai"], "洗い出し・飛び石", None), (C["rain"], "雨庭", None), (C["bld"], "建物", None)):
    fig.add_artist(matplotlib.patches.Rectangle((LX / 297, ly / 420), 5 / 297, 3 / 420, transform=fig.transFigure, fc=c, ec="#555555", lw=0.3, hatch=h))
    fig.text((LX + 7) / 297, (ly + 1.5) / 420, t, fontsize=5.6, va="center"); ly -= 5.5
fig.add_artist(matplotlib.lines.Line2D([LX / 297, (LX + 5) / 297], [(ly + 1.5) / 420] * 2, transform=fig.transFigure, lw=2.0, color=C["fence"]))
fig.text((LX + 7) / 297, (ly + 1.5) / 420, "板塀 h1.8", fontsize=5.6, va="center"); ly -= 5.5
fig.add_artist(matplotlib.lines.Line2D([LX / 297, (LX + 5) / 297], [(ly + 1.5) / 420] * 2, transform=fig.transFigure, lw=1.6, color="#8FB8D8"))
fig.text((LX + 7) / 297, (ly + 1.5) / 420, "窓（外を見る所）", fontsize=5.6, va="center")

P_ = N.N["PLANTS"]
PL_ = N.N["PLANTS"]
notes = ("道路沿いの帯（後退の帯、幅1.0）：壁の外面は後退の線の上。戸の前だけ空け、ほかは植栽。高木は植えない（道が細い）。毒・とげ・かぶれのある植物は使わない（園庭の決まりと同じ、ヒイラギモクセイ・ジンチョウゲ・スイセンは使わない）。\n"
         f"樹種（楽しめるもの、ユーザー：香りと花）：窓と戸の無い壁の前は{'・'.join(PL_['HEDGE']['sp'])}の刈り込み（秋の香りが道と迎えの保護者に）。板塀の前と機械室の脇は{'・'.join(PL_['MID']['sp'])}（春の白い花、初夏の香り、夏〜秋の花）。\n"
         f"遊戯室の地窓・覗き窓の前と大戸の脇は低い香りの草（{'・'.join(PL_['LOW']['sp'])}）。こどもには床の高さに花と葉が見え、道からの覗き込みも和らぐ。軒の下は乾くので乾きに強いものを。壁の足もとは砂利0.2。\n"
         f"読書の庭（約{N.READ.area:.0f}m²）：西館の北の面・本館の西の壁の北の端・板塀に囲まれた、入らない坪庭。本の奥の地窓と遊戯室の北の窓から見る。北向きで両側の建物の陰になるので苔に向く。モミジは塀の上から道にも見える。\n"
         f"板塀 h1.8（約{sum(LineString(f).length for f in N.FENCE):.0f}m）：西館の北の角から機械室まで、後退の線の上。今まで道路に開いていたセキュリティの線の切れ目を閉じる。本館の北西の角の真ん前に両開きの木戸（外開き、鍵）。左の扉で読書の庭へ、右の扉で北の小径へ（庭師の手入れは外から、建物に新しい開口は設けない）。\n"
         "機械室の戸：北東は隣家から1mを守る側なので、戸は北西の面（道路側）に。機器と蓄電池（2.0×1.2）の出し入れ・点検が、こどもの線の内側を通らずにできる。戸の形は本館係。")
fig.text(14 / 297, 112 / 420, notes, fontsize=6.0, va="top", color="#333333", linespacing=1.65, wrap=True)

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, "sodachiya_site_N_1-200." + ext), dpi=200 if ext == "png" else None)
print("plants", round(N.PLANT.area, 1), "read", round(N.READ.area, 1))
