# みなみのさんかく（乳児の園庭、0〜2 歳）たたき台　平面 1/50・断面 1/50（A2 横）
# 寸法は data/minami.json、形は minami_common.py。出力 out/sodachiya_minami_01.pdf / .png
import os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Circle, FancyArrow
from shapely.geometry import LineString, Point
import minami_common as G

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT", os.path.join(os.path.dirname(HERE), "out"))
D = G.D
MM = 1 / 25.4
PW, PH = 594, 420
fig = plt.figure(figsize=(PW * MM, PH * MM))
C = dict(grass="#DCE9C4", grass2="#C9DDA8", clear="#9DB7D5", evac="#B9D3EC", eng="#F4EBDD", roof="#555555",
         sand="#EADBB0", herb="#A9C98A", water="#9CC9E6", tree="#6E9A4E", text="#222222", red="#C8372D", loop="#B08A5A")
MAT = {"芝": "#B9D59A", "土（真砂土）": "#D9BE95", "洗い出し（玉砂利を固めた）": "#C8C2B6", "丸太の輪切り（スギ）": "#C99A63",
       "スギの板（すのこ）": "#E2C08E", "砂": "#EADBB0"}

# ------------------------------------------------------------------ plan 1/50 (1 m = 20 mm)
x0, x1, y0, y1 = -1.0, 16.5, -11.8, 1.6
PL, PB = 18, 120
ax = fig.add_axes([PL / PW, PB / PH, (x1 - x0) * 20 / PW, (y1 - y0) * 20 / PH])
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")

def shp(g, fc="none", ec="black", lw=0.5, z=2, ls="-", hatch=None, alpha=1.0, a=None):
    a = a or ax
    if g.is_empty: return
    for q in ([g] if g.geom_type == "Polygon" else [h for h in getattr(g, "geoms", []) if h.geom_type == "Polygon"]):
        a.add_patch(MP(list(zip(*q.exterior.xy)), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))
        for hole in q.interiors:
            a.add_patch(MP(list(zip(*hole.xy)), closed=True, fc="white", ec=ec, lw=lw, zorder=z + 0.01))
def line(pts, lw=0.5, c="black", ls="-", z=3, a=None):
    xs, ys = zip(*pts); (a or ax).plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(p, s, size=7, c=C["text"], ha="center", va="center", rot=0, z=12, a=None, **kw):
    (a or ax).text(p[0], p[1], s, fontsize=size, color=c, ha=ha, va=va, rotation=rot, zorder=z, **kw)

# context: building south end (u 0..1.5), porch, river
line([(-1.0, 0.0), (16.5, 0.0)], lw=0.3, c="#999", ls=":")
shp(G.Polygon([(1.6, 0), (15.0, 0), (15.0, 1.6), (1.6, 1.6)]), fc="#F3F3F3", ec="#888", lw=0.4, z=1)
for v in (1.6, 4.5, 10.4, 13.5):
    pass
line([(1.75, 0.0), (11.8, 0.0)], lw=1.4, c="#5a7fa6", z=5)                    # south gable glass
line([(13.5, 0.0), (13.5, 1.6)], lw=0.6, c="#5a7fa6", z=5)                    # engawa glass doors
T((7.0, 0.8), "0・1 歳（スパン 1）　南の妻はガラス", 7.5, c="#666")
T((14.25, 0.8), "外縁側", 6.5, c="#666")
shp(G.PORCH, fc="#F7E2CC", ec="#999", lw=0.4, z=1); T((0.6, -3.0), "ポーチ", 6.5, c="#777", rot=90)
# river side (outside the area)
rv = [tuple(G.R0 - G.DIR * 3), tuple(G.R1 + G.DIR * 3)]
out = [rv[0], rv[1], tuple(np.array(rv[1]) - G.NRM * 1.6), tuple(np.array(rv[0]) - G.NRM * 1.6)]
shp(G.Polygon(out), fc="#E7E3DA", ec="none", z=0.5)
line(rv, lw=1.0, c="#6b5a3a", z=6)
T(tuple((G.R0 + G.R1) / 2 - G.NRM * 0.8), "高野川の護岸の柵（金網、現況）　→ 崖 約 4〜5 m", 7, c="#6b5a3a", rot=G.ANG)

# ground
shp(G.AREA, fc=C["grass"], ec="#7a8a5a", lw=0.5, z=1.5)
shp(G.CLEAR.difference(G.EVAC), fc="none", ec="none", hatch="////", z=1.8)
for h in (G.CLEAR.difference(G.EVAC),):
    shp(h, fc="none", ec=C["clear"], lw=0.0, z=1.8, hatch="//")
shp(G.EVAC, fc=C["evac"], ec="#5c88b8", lw=0.4, z=1.9, alpha=0.8)
cl_line = [tuple(G.R0 - G.DIR * 3 + G.NRM * D["CLEAR"]["w"]), tuple(G.R1 + G.DIR * 3 + G.NRM * D["CLEAR"]["w"])]
cl = LineString(cl_line).intersection(G.AREA)
if not cl.is_empty: line(list(cl.coords), lw=0.6, c="#5c88b8", ls=(0, (4, 3)), z=2)
mid = (np.array(cl.coords[0]) + np.array(cl.coords[-1])) / 2
T(tuple(G.R0 + (G.R1 - G.R0) * 0.62 + G.NRM * 0.75), "避難の帯 1.5（平らで固い芝、避難車）", 6.5, c="#2f5f8f", rot=G.ANG)
T(tuple(G.R0 + (G.R1 - G.R0) * 0.30 + G.NRM * 2.0), "空けられる帯 2.5：木と動かせない物は置かない", 6.5, c="#2f5f8f", rot=G.ANG)

# engawa, eave
shp(G.ENGAWA, fc=C["eng"], ec="#8a6a3a", lw=0.7, z=4)
T((5.0, -1.0), "南の縁側（ぽってり、土足 −150）\n縁に腰掛けて見守る", 7, c="#6a4a2a")
eave = G.ROOF.exterior
ex = [p for p in G.ROOF.exterior.coords if p[1] < -0.05]
line(sorted(ex, key=lambda p: p[0]), lw=0.6, c=C["roof"], ls=(0, (6, 2, 1, 2)), z=7)
T((9.0, -2.55), "南の軒の先（一点鎖線）", 6.2, c=C["roof"], rot=-11)

# fence (one line)
line([(D["FENCE_V"], 0.0), (1.4, -8.8)], lw=1.6, c=C["red"], z=6)
T((1.0, -6.4), "柵 h1.2（一本の線の延長）", 6.5, c=C["red"], rot=90)

# herbs, tree, sand, mound, loop, water
shp(G.HERB, fc=C["herb"], ec="#5a7a3a", lw=0.4, z=4)
T(((D["HERB"]["v"][0] + D["HERB"]["v"][1]) / 2, sum(D["HERB"]["u"]) / 2), "ハーブ", 6, rot=90, c="#2e4a1e")
for name, g in G.loop_parts():
    shp(g, fc=MAT[name], ec="#7a6a50", lw=0.3, z=4.2)
shp(G.MOUND, fc=C["grass2"], ec="#6a8a4a", lw=0.5, z=4.5)
for f in (0.66, 0.33):
    e = G.ellipse(D["MOUND"]["c"], D["MOUND"]["a"] * f + D["MOUND"]["top"] * (1 - f), (D["MOUND"]["a"] * f + D["MOUND"]["top"] * (1 - f)) * D["MOUND"]["b"] / D["MOUND"]["a"])
    shp(e, fc="none", ec="#6a8a4a", lw=0.3, z=4.6, ls=":")
T(G.xy(D["MOUND"]["c"]), "ころころの丘\nh0.3", 7, z=13)
shp(G.SHED, fc="#EDE6D6", ec="#666", lw=0.6, z=4.4)
T(G.SHED.centroid.coords[0], "物置", 6, rot=90)
shp(G.SAND, fc=C["sand"], ec="#8a7040", lw=0.8, z=4.4)
T(G.SAND.centroid.coords[0], "砂場\n布の覆い", 6.5)
shp(G.WATER, fc=C["water"], ec="#3d7fb0", lw=0.7, z=4.4)
T((G.WATER.centroid.x + 1.25, G.WATER.centroid.y), "水のテーブル\nh0.45", 6.5, c="#2a5f8a")
tc = G.xy(D["TREE"]["c"])
ax.add_patch(Circle(tc, D["TREE"]["r"], fc=C["tree"], ec="#3e6a2e", lw=0.5, alpha=0.25, zorder=8))
ax.add_patch(Circle(tc, 0.12, fc="#5a3a1a", ec="none", zorder=9))
T((tc[0] + 0.15, tc[1] - 0.55), D["TREE"]["name"], 7, c="#2e4a1e", z=13)

# loop material labels (leader-free: put the name beside each part)
for name, g in G.loop_parts():
    p = g.representative_point()
    c = np.array([p.x, p.y]); cc = np.array(G.xy(D["LOOP"]["c"]))
    q = c + (c - cc) / np.linalg.norm(c - cc) * 0.75
    T(tuple(q), name.split("（")[0], 5.6, c="#5a4630", z=14)

# section line
SC = np.array(G.xy(D["MOUND"]["c"]))
sa, sb = SC + G.NRM * 3.0, SC - G.NRM * (G.dist_river(SC) + 0.6)
line([tuple(sa), tuple(sb)], lw=0.6, c="#333", ls=(0, (10, 3, 2, 3)), z=15)
for p, s in ((sa, "S"), (sb, "S")): T(tuple(p + (p - SC) / np.linalg.norm(p - SC) * 0.35), s, 8, weight="bold", z=15)

# scale, north
for i in range(6):
    ax.add_patch(MP([(0 + i, -11.3), (1 + i, -11.3), (1 + i, -11.15), (0 + i, -11.15)], fc="#333" if i % 2 == 0 else "white", ec="#333", lw=0.4))
T((3.0, -11.6), "0　　　　　　　　5 m", 6.5)
nb = math.radians(-7)
ax.add_patch(FancyArrow(15.6, -10.8, 1.0 * math.sin(nb) * -1, 1.0 * math.cos(nb), width=0.05, head_width=0.3, head_length=0.35, color="#333", zorder=15))
T((15.6, -11.25), "北", 7)

fig.text(PL / PW, (PH - 14) / PH, "育ち舎　みなみのさんかく（乳児の園庭、0〜2 歳）　たたき台 1", fontsize=15, weight="medium", va="top")
fig.text(PL / PW, (PH - 22) / PH, "平面 1/50・断面 1/50（A2）　2026-10-22　寸法 data/minami.json　図 scripts/minami01.py　3dm は外構の取り込み用ファイルのレイヤー 78・79", fontsize=8.5, color="#555", va="top")

# ------------------------------------------------------------------ section S-S 1/50
sx0 = -0.3; sx1 = 9.0
NXs = 385
axs = fig.add_axes([NXs / PW, 18 / PH, (sx1 - sx0) * 20 / PW, 3.2 * 20 / PH])
axs.set_xlim(sx0, sx1); axs.set_ylim(-1.0, 2.2); axs.set_aspect("equal"); axs.axis("off")
L = np.linalg.norm(sb - sa)
ts = np.linspace(0, L, 400)
pts = [sa + (sb - sa) * t / L for t in ts]
def zg(p):
    z = 0.0
    if G.Point(p).within(G.MOUND): z = G.mound_z(*p)
    return z
zs = [zg(p) for p in pts]
# engawa part
eng = [t for t, p in zip(ts, pts) if G.Point(p).within(G.ENGAWA)]
ground = [(t, z) for t, z in zip(ts, zs)]
axs.fill_between(ts, -0.6, zs, color="#E9E2D3", zorder=1)
axs.plot(ts, zs, color="#4a3a2a", lw=1.0, zorder=3)
if eng:
    e0, e1 = min(eng), max(eng)
    axs.add_patch(MP([(e0, 0), (e1, 0), (e1, 0.15), (e0, 0.15)], fc=C["eng"], ec="#6a4a2a", lw=0.8, zorder=4))
    T(((e0 + e1) / 2, 0.38), "縁側 +0.15", 6.5, a=axs)
    # eave: roof above (approx GL+4.5 − v/12)
    zr = lambda p: 4.5 - p[0] / 12
    ex_t = [t for t, p in zip(ts, pts) if G.Point(p).within(G.ROOF)]
    if ex_t and False:
        r0, r1 = min(ex_t), max(ex_t)
        pr0, pr1 = sa + (sb - sa) * r0 / L, sa + (sb - sa) * r1 / L
        axs.plot([r0, r1], [zr(pr0), zr(pr1)], color=C["roof"], lw=2.0, zorder=4)
        T((r1 + 0.1, zr(pr1) + 0.1), "南の軒", 6.5, a=axs, ha="left")
for name, g, z0, z1, c in (("小径", G.LOOP, 0, 0.02, C["loop"]),):
    for t, p in zip(ts, pts):
        pass
def span(g):
    tt = [t for t, p in zip(ts, pts) if G.Point(p).within(g)]
    return (min(tt), max(tt)) if tt else None
s = span(G.EVAC)
if s:
    axs.add_patch(MP([(s[0], -0.03), (s[1], -0.03), (s[1], 0.0), (s[0], 0.0)], fc="#5c88b8", ec="none", zorder=5))
    T(((s[0] + s[1]) / 2, -0.28), "避難の帯 1.5", 6.2, a=axs, c="#2f5f8f")
cs = span(G.CLEAR)
if cs:
    axs.annotate("", xy=(cs[1], -0.55), xytext=(cs[0], -0.55), arrowprops=dict(arrowstyle="<->", lw=0.5, color="#2f5f8f"))
    T(((cs[0] + cs[1]) / 2, -0.75), "空けられる帯 2.5", 6.2, a=axs, c="#2f5f8f")
for g, lab in ((G.LOOP, "はだしの小径"),):
    t0 = [t for t, p in zip(ts, pts) if G.Point(p).within(g)]
    if t0:
        # two crossings
        runs, cur = [], [t0[0]]
        for a_, b_ in zip(t0, t0[1:]):
            if b_ - a_ > 0.05: runs.append(cur); cur = [b_]
            else: cur.append(b_)
        runs.append(cur)
        for r_ in runs:
            m_ = (r_[0] + r_[-1]) / 2
            axs.plot([r_[0], r_[-1]], [zg(sa + (sb - sa) * m_ / L) + 0.01] * 2, color=C["loop"], lw=3, zorder=5)
        T(((runs[0][0] + runs[0][-1]) / 2, 0.55 + zg(sa + (sb - sa) * runs[0][0] / L)), lab, 6.2, a=axs, c="#5a4630")
T((G.xy(D["MOUND"]["c"]) and (np.linalg.norm(SC - sa)), D["MOUND"]["h"] + 0.35), "ころころの丘 h0.3（勾配 1:3 くらい、芝）", 6.5, a=axs)
# fence at river
fs = np.linalg.norm(sb - sa)
d_end = G.dist_river(sb)
t_r = fs + d_end
axs.plot([t_r, t_r], [0, 1.2], color="#6b5a3a", lw=1.2)
axs.plot([t_r, t_r + 0.5], [-0.3, -0.3], color="#6b5a3a", lw=0.8)
axs.plot([t_r, t_r + 0.6], [0, -0.6], color="#6b5a3a", lw=0.8, ls=":")
T((t_r - 0.1, 1.35), "護岸の柵", 6.5, a=axs, ha="right")
# children figures (1 yr ~0.8, 2 yr ~0.9, adult eye 1.55 sitting 1.1)
def kid(t, h, lab):
    axs.add_patch(Circle((t, h - 0.08), 0.08, fc="none", ec="#444", lw=0.5, zorder=8))
    axs.plot([t, t], [h - 0.16, zg(sa + (sb - sa) * t / L) + 0.0], color="#444", lw=0.6, zorder=8)
    T((t, h + 0.12), lab, 5.5, a=axs)
kid(np.linalg.norm(SC - sa) - 1.6, 0.8 + zg(sa + (sb - sa) * (np.linalg.norm(SC - sa) - 1.6) / L), "1 歳")
kid(np.linalg.norm(SC - sa), 0.9 + D["MOUND"]["h"], "2 歳")
axs.plot([0, 9], [0, 0], lw=0)
T((sx0 + 0.05, 2.0), "断面 S–S　1/50（丘の真ん中を川に向かって切る）", 8.5, a=axs, ha="left", weight="medium")
axs.plot([sx0, sx1], [0, 0], color="#999", lw=0.3, ls=":")
T((sx1 - 0.05, 0.1), "GL", 6, a=axs, ha="right", c="#888")

# ------------------------------------------------------------------ notes
NX = 385
notes = [
 ("役割", "いちばんの役割は 0〜2 歳の園庭（ユーザー）。大きな荷物・工事の車・避難の道は「副」：川沿いの帯 2.5 を「空けられる」ことだけ守る（避難の帯 1.5＋1.0）。帯の中に木・動かせない物は置かない。少しの起伏と閉じられる砂場はよい（ユーザー）。避難の帯 1.5 は平らで固い芝（避難車が通る）。道そのものは描かない。"),
 ("広さ", "約 %.0f m²（南の縁側を除く）。そのうち空けられる帯 約 %.0f m²、帯の外 約 %.0f m²。" % (G.AREA.area, G.CLEAR.area, G.PLAY.area)),
 ("見守り", "先生はぽってりの縁側の縁（+0.15）に腰掛けて全体を見る。木は 1 本だけで、ほかは膝より低い（ハーブ・丘 h0.3）。死角なし。南の妻のガラスごしに、0・1 歳の部屋からも見える。"),
 ("ころころの丘", "h0.3、%.1f×%.1f m の楕円、芝。0 歳は這い上がり、1 歳は転がり、2 歳は駆け下りる。だいさんかくの築山（比叡の見立て）の赤ちゃん。帯 1.0 に半分掛かってよい（越えて車が通れる高さ）。" % (D["MOUND"]["a"] * 2, D["MOUND"]["b"] * 2)),
 ("はだしの小径", "丘を回る幅 0.6、一周 約 %.0f m。芝 → 土 → 洗い出し → 丸太の輪切り → スギのすのこ → 砂と、足の裏で順に触れる（本物に触れて育つ）。床と面一で段差なし。ばらの玉砂利は口に入るので使わない（洗い出しで固める）。" % G.LOOP_C.length),
 ("砂場", "%.1f×%.1f、深さ 0.3、縁 h0.15（腰掛け）。布の覆い「おやすみの布」で閉じる（猫・落ち葉・雨）。ヤマボウシの北東で、昼すぎに木陰。縁側のすぐ前なので、0 歳も縁側から手を伸ばせる。" % (D["SAND"]["l"], D["SAND"]["w"])),
 ("木陰の木", "ヤマボウシ 1 本（落葉：夏は木陰、冬は日が入る。6 月の白い花、9 月の赤い実は食べられる、紅葉）。南西の隅、柵から 1 m。枝下 2.2、帯の側は枝を上げる。毒・とげ・チャドクガの木は使わない（園庭と同じ）。"),
 ("水のテーブル", "石の水盤 1.2×0.6、h0.45（1・2 歳が立って手が届く）、水深 5 cm、上水（先生が開ける蛇口）。軒の下の東の端、外縁側のスロープの脇。排水はすぐ東の雨の川へ（園庭）。使わないときは乾かす。"),
 ("ハーブの帯", "柵の内側に幅 0.55：レモンバーム・タイム・ラムズイヤー（ふわふわの葉）・ミント（鉢を埋めて広がりを止める）・這うローズマリー。触ってちぎって香る。柵の固さを和らげる。"),
 ("軒の下", "縁側と軒の先のあいだ（約 1〜2 m）は夏の日陰。0 歳はここにござを敷いて寝ころぶ、外気浴。"),
 ("東の端", "しずかのもり（園庭）とは雨の川（雨落ちの溝）をはさんで続く。戸や柵は描いていない（要確認：分けるかどうか）。"),
 ("模型", "丘は 3 mm（h0.3）の板 1 枚か、紙粘土。砂場・小径は彩色。木は園庭と同じ作り方。3dm のレイヤー 78（地形・遊び場）・79（植物）。"),
]
y = PH - 40
for h, t in notes:
    fig.text(NX / PW, y / PH, h, fontsize=8.5, weight="bold", va="top")
    import textwrap
    wrapped = "\n".join(t[i:i + 56] for i in range(0, len(t), 56))
    fig.text((NX + 2) / PW, (y - 5) / PH, wrapped, fontsize=7.6, va="top", linespacing=1.45)
    y -= 5 + 3.9 * (wrapped.count("\n") + 1) + 3.0
os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, "sodachiya_minami_01." + ext), dpi=110 if ext == "png" else None)
print("check:", G.check() or "ok", "| loop %.1f m, area %.1f, clear %.1f, play %.1f" % (G.LOOP_C.length, G.AREA.area, G.CLEAR.area, G.PLAY.area))
