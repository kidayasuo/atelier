import sys
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import fonts42   # 文字は文字のまま（Type42）
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
T(tuple((G.R0 + G.R1) / 2 - G.NRM * 0.8), "高野川の崖の上（土と雑草）→崖約4〜5 m", 7, c="#6b5a3a", rot=G.ANG)
# 川の柵：木の縦格子 h1.2（クリの心材、無塗装）。だいさんかく・しずかのもりと一続き（ユーザー 10-31、scripts/koushi.py）。緑の目隠し・のぞき窓はやめた
import koushi
_gc = koushi._gc()
_LAT = koushi.layout()
def _m(pts): return [(lambda u_v: (u_v[1], u_v[0]))(_gc.uv_of(*q)) for q in pts]
koushi.plan(_LAT, lambda pts, lw=0.5, c="k", z=3: line(_m(pts), lw=lw, c=c, z=z), lambda pts, fc: shp(G.Polygon(_m(pts)), fc=fc, ec="none", z=6.6),
            wood="#6b5a3a", lw=1.2, z=6.5, pickets_too=True)
T(tuple(G.R0 + (G.R1 - G.R0) * 0.2 - G.NRM * 0.3), "木の縦格子の柵 h1.2（クリ、すき間 0.10、横材は上と下だけ）", 6.5, c="#6b5a3a", rot=G.ANG)

# ground
shp(G.AREA, fc=C["grass"], ec="#7a8a5a", lw=0.5, z=1.5)
for h in (G.CLEAR.difference(G.EVAC),):
    shp(h, fc="none", ec=C["clear"], lw=0.0, z=1.8, hatch="//")
shp(G.EVAC, fc="#D3E3B8", ec="#5c88b8", lw=0.4, z=1.9)                      # 避難の帯：平らで固い芝（遊び場の一部、10-25）
# 避難の帯の遊び（EVAC_PLAY）：芝の川（刈り分け）・足あとの石（面一）
shp(G.GRASS_RIVER, fc="#B4D38E", ec="#86ab5e", lw=0.3, z=1.95)
_AC = {"サギ": "#7d8a99", "カモ": "#8a6d3b", "タヌキ": "#6b4f3a"}
for (xy_, a_) in G.footprints():
    ax.add_patch(Circle(xy_, G.EP["d"] / 2, fc="#E4DCCB", ec=_AC[a_], lw=0.5, zorder=2.05))
    ax.add_patch(Circle(xy_, 0.035, fc=_AC[a_], ec="none", zorder=2.06))
_fp = G.footprints()
T(tuple(np.array(_fp[4][0]) + G.NRM * 0.32), "サギ", 5.5, c=_AC["サギ"], rot=G.ANG)
T(tuple(np.array(_fp[13][0]) + G.NRM * 0.32), "カモ", 5.5, c=_AC["カモ"], rot=G.ANG)
T(tuple(np.array(_fp[24][0]) + G.NRM * 0.32), "タヌキ", 5.5, c=_AC["タヌキ"], rot=G.ANG)
cl_line = [tuple(G.R0 - G.DIR * 3 + G.NRM * D["CLEAR"]["w"]), tuple(G.R1 + G.DIR * 3 + G.NRM * D["CLEAR"]["w"])]
cl = LineString(cl_line).intersection(G.AREA)
if not cl.is_empty: line(list(cl.coords), lw=0.6, c="#5c88b8", ls=(0, (4, 3)), z=2)
mid = (np.array(cl.coords[0]) + np.array(cl.coords[-1])) / 2
T(tuple(G.R0 + (G.R1 - G.R0) * 0.74 + G.NRM * 1.32), "避難の帯 1.5（芝の川・足あとの石・はしる道、平らで固い）", 6.5, c="#2f5f8f", rot=G.ANG)
T(tuple(G.R0 + (G.R1 - G.R0) * 0.30 + G.NRM * 2.0), "空けられる帯 2.5：木と動かせない物は置かない", 6.5, c="#2f5f8f", rot=G.ANG)

# engawa, eave
shp(G.ENGAWA, fc=C["eng"], ec="#8a6a3a", lw=0.7, z=4)
T((5.0, -1.0), "南の縁側（ぽってり、土足 −150）\n縁に腰掛けて見守る", 7, c="#6a4a2a")
eave = G.ROOF.exterior
ex = [p for p in G.ROOF.exterior.coords if p[1] < -0.05]
line(sorted(ex, key=lambda p: p[0]), lw=0.6, c=C["roof"], ls=(0, (6, 2, 1, 2)), z=7)
T((9.0, -2.55), "南の軒の先（一点鎖線）", 6.2, c=C["roof"], rot=-11)

# fence (one line)
fu = D["FENCE_END_U"]; gp = G.GATE_POST_W
line([(D["FENCE_V"], 0.0), (1.41, fu), (gp[0], gp[1])], lw=1.6, c=C["red"], z=6)
# lattice h1.8 along the park edge (security line), from the gate post toward the park gate
lat = [tuple(np.array(gp) - G.PDIR * 3.2), gp]
line(lat, lw=1.6, c="#7a5a36", z=6)
T(tuple(np.array(gp) - G.PDIR * 2.4 + np.array([-0.35, 0])), "大和張りの塀 h1.8（公園との境）", 6, c="#7a5a36", rot=math.degrees(math.atan2(-G.PDIR[1], -G.PDIR[0])) - 180)
# gates: closed leaf (thick), swing arc (dashed), open position (thin)
from matplotlib.patches import Arc
for name, h, e, hh, deg in G.gates():
    line([h, e], lw=2.6, c="#5a3a1a", z=8)
    for p in (h,): ax.add_patch(MP([(p[0] - 0.07, p[1] - 0.07), (p[0] + 0.07, p[1] - 0.07), (p[0] + 0.07, p[1] + 0.07), (p[0] - 0.07, p[1] + 0.07)], fc="#333", ec="none", zorder=9))
    o = G.leaf_at(h, e, deg); line([h, o], lw=0.6, c="#5a3a1a", z=8)
    r_ = float(np.linalg.norm(np.array(e) - np.array(h)))
    a0 = math.degrees(math.atan2(e[1] - h[1], e[0] - h[0]))
    t1, t2 = (a0, a0 + deg) if deg > 0 else (a0 + deg, a0)
    ax.add_patch(Arc(h, 2 * r_, 2 * r_, theta1=t1, theta2=t2, lw=0.45, color="#5a3a1a", ls=(0, (3, 2)), zorder=8))
T((15.35, -1.75), "東の木戸 h0.9\n子扉 0.9（ふだん）\n親扉 2.2（車のとき）", 6.3, ha="left", c="#5a3a1a")
wm = np.array(G.park_pt(1.4))
T(tuple(wm + np.array([-1.55, -0.2])), "西の門 h1.8\n（非常用、外開き）\n子扉 1.2・親扉 1.55", 6.3, c="#5a3a1a")
T((16.0, -5.2), "しずかのもり →", 7, c="#4a6a3a")
T((-0.2, -10.6), "公園", 7, c="#4a6a3a")
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
fig.text(PL / PW, (PH - 22) / PH, "平面 1/50・断面 1/50（A2）　2026-10-22　寸法 data/minami.json　図 scripts/minami01.py　3dm は外構の取り込み用ファイルのレイヤー 78・79c、川の柵は 70k・70m", fontsize=8.5, color="#555", va="top")

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
# 木の縦格子 h1.2（柵の芯は崖の上の縁から inset 内側）：柱脚金物 GL+0.05、下の横材 0.10〜0.145、格子、笠木。外の崖の上は土と雑草
_R = koushi.R; _ti = t_r - _R["inset"]; _hd = _R["picket"]["d"] / 2; _tw = _R["top"]["w"] / 2
axs.add_patch(MP([(_ti - _hd, _R["bottom"]["z"]), (_ti + _hd, _R["bottom"]["z"]), (_ti + _hd, _R["h"] - _R["top"]["h"]), (_ti - _hd, _R["h"] - _R["top"]["h"])], fc="#C9A97E", ec="#6b5a3a", lw=0.5, zorder=7))
axs.add_patch(MP([(_ti - _tw, _R["h"] - _R["top"]["h"]), (_ti + _tw, _R["h"] - _R["top"]["h"]), (_ti + _tw, _R["h"]), (_ti - _tw, _R["h"])], fc="#8a6a3a", ec="#6b5a3a", lw=0.5, zorder=7.2))
axs.add_patch(MP([(_ti - _tw, _R["bottom"]["z"]), (_ti + _tw, _R["bottom"]["z"]), (_ti + _tw, _R["bottom"]["z"] + _R["bottom"]["h"]), (_ti - _tw, _R["bottom"]["z"] + _R["bottom"]["h"])], fc="#8a6a3a", ec="#6b5a3a", lw=0.5, zorder=7.2))
axs.plot([t_r, t_r + 0.8], [0, 0], color="#6b5a3a", lw=0.8)
axs.plot([t_r + 0.8, t_r + 1.1], [0, -1.0], color="#6b5a3a", lw=0.8, ls=":")
for _k in range(9):                                                              # 崖の上の雑草（ばらばらの高さ）
    _x = t_r + 0.05 + 0.08 * _k + 0.03 * math.sin(_k * 2.3); _hh = 0.12 + 0.28 * abs(math.sin(_k * 1.7 + 0.4))
    axs.plot([_x, _x + 0.03 * math.sin(_k)], [0, _hh], color="#6E9A4E", lw=0.6, zorder=6)
T((t_r + 0.1, _R["h"] + 0.1), "木の縦格子 h1.2（クリの心材、無塗装）", 6.5, a=axs, ha="left", c="#6b5a3a")
T((t_r + 0.1, -0.25), "崖の上は土と雑草", 6.0, a=axs, ha="left", c="#4f6e35")
T((_ti - 0.25, _R["h"] + 0.35), "↑上は開く：南の妻の架構・軒が川から見える", 6.2, a=axs, ha="right", c="#555")
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
 ("東の木戸", "しずかのもりとの境を木戸で分ける（ユーザー）。v 15 の線、本館の南東の角から川の柵まで 約 3.2 m。親子の両開き：子扉 0.9 をふだん使い（西へ開く）、車のときだけ親扉 2.2（足に戸車、落とし棒）も開けて、車の向きに直角に測って あき %.2f m（帯 2.5 より広い）。親扉は西へ約 120° 回して川の柵に沿わせて畳む。h0.9、スギの縦格子（すき間 80 以下、横桟なし）、掛け金は上の框の 2 段（h0.95 以上、2 歳の手が届かない）。すぐ東は雨の川（車は石の蓋で渡る）。" % G.clear_width((15, D["GATES"]["EAST"]["posts_u"][0] - 0.05), (15, D["GATES"]["EAST"]["posts_u"][1] + 0.05))),
 ("西の門", "非常用の門（避難の帯の出口）。公園の北東の辺（川に直交）の上で、川の柵から 約 2.85 m。親子の両開き：子扉 1.2（避難車が通る、外へ 90° で川の柵に沿う）＋親扉 1.55（外へ 180° で公園側の塀に沿う）、あき %.2f m。公園側の大和張りの塀と同じ h1.8。内側からは鍵なしで開く（取っ手 h1.3 以上、二段の掛け金）、開くと事務に知らせる、公園の側からは鍵（セキュリティの線）。柵 h1.2 は南の端を 約 0.35 m 縮めて門の柱へ折り返す。" % G.clear_width(G.park_pt(0.15), G.park_pt(2.8))),
 ("避難の帯で遊ぶ", "避難の帯もみなみのさんかくの大事な一部（ユーザー）。平らで固い・動かせない物を置かない、は守ったまま：①芝の川：帯の中を刈り分けた幅 0.7 の流れ（高野川の写し、刈り方で季節ごとに変えられる）。②足あとの石：芝の川に沿って面一の洗い出しの丸い板（径 0.24、0.55 ごと）、川上からサギ・カモ・タヌキの足あと。這って、歩いて、追いかける。避難車は上を通れる。③はしる道：園庭でいちばん長い平らな直線（約 14 m）、手押し車・足けりの車で（物置から出してしまう）。④川の柵は木の縦格子：這う・座る子も格子のすき間から川の水と対岸が見え、水の音が聞こえる。"),
 ("川の柵", "木の縦格子 h1.2（ユーザー 10-31）。だいさんかく・しずかのもりと一続き。クリの心材、無塗装（保護材だけ）。格子 30×75 をすき間 0.10 で、横材は上の笠木と下だけ（途中に足をかける所なし）。柱 90 角はステンレスの柱脚金物で土から離す。格子はビスで一本ずつ留め、取り替えられる。対岸から 0〜2 歳の子と座った先生が見えにくい役は格子が果たす（斜めからは重なって見えない）。つるは絡めない。上は開く：南の妻の梁・柱・軒が川から見える。柵ぎわ約 1 m には踏み台になる物を置かない。柵の外の崖の上は土と雑草。"),
 ("模型", "丘は 3 mm（h0.3）の板 1 枚か、紙粘土。砂場・小径は彩色。木は園庭と同じ作り方。3dm のレイヤー 78（地形・遊び場）・79c（ハーブ）、川の柵は 70k（木）・70m（柱脚金物）。"),
]
y = PH - 40
for h, t in notes:
    fig.text(NX / PW, y / PH, h, fontsize=8.5, weight="bold", va="top")
    import textwrap
    wrapped = "\n".join(t[i:i + 56] for i in range(0, len(t), 56))
    fig.text((NX + 2) / PW, (y - 5) / PH, wrapped, fontsize=7.6, va="top", linespacing=1.45)
    y -= 5 + 3.9 * (wrapped.count("\n") + 1) + 3.0
print("notes end y", round(y, 1))
os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, "sodachiya_minami_01." + ext), dpi=110 if ext == "png" else None)
print("check:", G.check() or "ok", "| loop %.1f m, area %.1f, clear %.1f, play %.1f" % (G.LOOP_C.length, G.AREA.area, G.CLEAR.area, G.PLAY.area))
