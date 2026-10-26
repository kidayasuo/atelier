# ホールの北山杉の林：幹の足もと（深いさや）と頂部 1/5、外し方、高さの決め方（A3 横）。6 版（すべて自立）
# 寸法は data/forest.json の DETAIL・PARAMS.HEIGHT。床は全面の床下空間（10-27）。
import json, os, math, textwrap
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["pdf.fonttype"] = 42   # 文字は文字のまま（Type42、Illustrator で書体を置き換える）
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch, Wedge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
F = json.load(open(os.path.join(ROOT, "data", "forest.json")))
D = F["DETAIL"]; H = F["PARAMS"]["HEIGHT"]; TR = F["TREES"]

MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
fig.text(14 / 420, 288 / 297, "ホールの北山杉の林　足もとと頂部 1/5・高さの決め方（たたき台・6 版：すべて自立）", fontsize=11, weight="bold", va="top")
fig.text(14 / 420, 281 / 297, "上は留めない。幹は床から自立する片持ちで、根元の深いさやが曲げを受ける。高さは太さで決め（右下の表）、頂部は丸く削る。"
         "抜ける幹は差して回す金物で、真上に抜く。さやの鋼管は床下を通して底板に留める（たたき台）。", fontsize=6.2, va="top")
WOOD = "#E8D2A6"; STEEL = "#8C8C8C"; TRUNK = "#C9A27A"; CON = "#D5D5D5"

def ax_at(x, y, w, h, scale=5):
    ax = fig.add_axes([x / 420, y / 297, w / 420, h / 297]); ax.set_xlim(0, w * scale); ax.set_ylim(0, h * scale)
    ax.set_aspect("equal"); ax.axis("off"); return ax
def rect(ax, x, y, w, h, fc, ec="black", lw=0.5, hatch=None, z=2):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, hatch=hatch, zorder=z))
def note(ax, x, y, tx, ty, s, fs=5.2):
    ax.annotate(s, (x, y), (tx, ty), fontsize=fs, arrowprops=dict(arrowstyle="-", lw=0.35, color="#555555"), va="center", color="#222222",
                bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.9), zorder=8)

d = D["d"]; so = D["socket"]; fl = D["floor"]; po = D["post"]; fe = D["ferrule"]

# ---------------------------------------------------------------- B: foot (section 1/5)
# 床は全面の床下空間（10-27）：さやの鋼管を床から底板まで通した柱にし、根元の曲げを底板へ。床下は図の中で縮めて描く（破断線）
B = ax_at(14, 112, 200, 160)        # 1000 × 800 mm
VOID_DRAWN = 300                                                          # 床下 450 を 300 に縮めて描く（破断は幹の下端より下）
y_fl = 730
y_ply = y_fl - fl["board"]; y_j = y_ply - fl["ply"]; y_jb = y_j - fl["joist"]
y_st = y_jb - VOID_DRAWN; y_sb = y_st - fl["slab"]; y_gb = y_sb - fl["gravel"]
cx = 330
sx0 = cx - d / 2 - so["clear"] - so["wall"]; sx1 = cx + d / 2 + so["clear"]; sw = sx1 + so["wall"] - sx0
g = po["sleeve_gap"]
for x0, x1 in ((0, sx0 - g), (sx1 + so["wall"] + g, 1000)):                # 床板・合板はさやと縁を切る（すき間）
    rect(B, x0, y_ply, x1 - x0, fl["board"], WOOD)
    rect(B, x0, y_j, x1 - x0, fl["ply"], "#E3CFA4", hatch="////")
for xj in (90, 640):                                                      # 大引（断面）・鋼製束
    rect(B, xj, y_jb, 90, fl["joist"], WOOD)
    rect(B, xj + 38, y_st, 14, y_jb - y_st, STEEL, lw=0.3); rect(B, xj + 15, y_st, 60, 6, STEEL, lw=0.3)
rect(B, 0, y_sb, 1000, fl["slab"], CON, hatch="xx")                       # ベタ基礎の底板
rect(B, 0, y_gb, 1000, fl["gravel"], "#EDE3D0", hatch="..")               # 砕石
B.plot([0, 1000], [y_sb - 2, y_sb - 2], lw=0.6, color="#3d7fb0", zorder=5)  # 防湿シート
for yb in (y_fl - so["depth"] - 30, y_st + 45):                            # 破断線（床下を縮めた、幹の下端より下で）
    B.plot([0, 1000], [yb, yb], lw=0.3, color="#888888", ls=(0, (1, 2)), zorder=6)
B.text(990, (y_fl - so["depth"] - 30 + y_st + 45) / 2, f"床下 有効 約{fl['void']}（縮めて描いた）", fontsize=4.8, ha="right", va="center", color="#555555")
# さやの柱：鋼管を床の上面から底板まで。上の so["depth"] がさや、その下は柱
rect(B, sx0, y_st + po["plate_t"], so["wall"], y_fl - y_st - po["plate_t"], STEEL, z=4)
rect(B, sx1, y_st + po["plate_t"], so["wall"], y_fl - y_st - po["plate_t"], STEEL, z=4)
yb_trunk = y_fl - so["depth"]
rect(B, sx0, yb_trunk - 8, sw, 8, STEEL, z=4)                             # さやの底（幹の受け）
rect(B, cx - po["plate"] / 2, y_st, po["plate"], po["plate_t"], STEEL, z=4)   # ベースプレート
for xa in (cx - po["plate"] / 2 + 30, cx + po["plate"] / 2 - 30):             # アンカー
    rect(B, xa - 6, y_st - 120, 12, 120 + po["plate_t"] + 14, "#555555", lw=0.3, z=5)
for sgn in (-1, 1):                                                       # 根元のリブ（三角）
    xr = sx0 if sgn < 0 else sx1 + so["wall"]
    B.add_patch(Polygon([(xr, y_st + po["plate_t"]), (xr + sgn * 70, y_st + po["plate_t"]), (xr, y_st + po["plate_t"] + 90)],
                        fc=STEEL, ec="black", lw=0.4, zorder=4))
rect(B, cx - d / 2, yb_trunk + 4, d, 800 - (yb_trunk + 4), TRUNK, z=3)
rect(B, cx - d / 2 - 1, yb_trunk + 4, d + 2, fe["h"], "#9A9A9A", z=5)
B.add_patch(Circle((cx + d / 2 + 3, y_fl - so["slot"] + 10), 5, fc="#333333", ec="none", zorder=6))
rect(B, sx0 - 18, y_fl - 6, sw + 36, 6, "#C9A45A", z=6)                  # 真鍮の輪
B.add_patch(Circle((sx1 + so["wall"] + 8, y_fl - 3), 3, fc="#333333", ec="none", zorder=7))
note(B, sx1 + so["wall"] + 8, y_fl - 3, 520, y_fl + 50, "ばね付きのピン（六角レンチで押し下げると回せる）\n抜けない幹は、ここを固定ねじに")
note(B, sx0 - 10, y_fl - 3, 20, y_fl + 45, "真鍮の輪（床と面一）")
note(B, cx + d / 2 + 3, y_fl - so["slot"] + 10, 520, y_fl - 10, f"口金の爪 2 か所が、さやの L 字の溝（上端から {so['slot']}）にかかる。差して 90° 回すと抜けない")
note(B, sx1 + so["wall"] + g / 2, y_ply + 10, 520, y_fl - 62, f"床板・合板とはすき間 {g}（やわらかい詰め物）：幹の揺れを床に伝えない")
note(B, sx1 + so["wall"], (y_fl + yb_trunk) / 2 - 40, 520, y_fl - 115, f"さやの柱：鋼管 内径 φ{d + 2 * so['clear']}・厚さ {so['wall']}。上の {so['depth']} がさや、\n床の上面から底板まで通して、根元の曲げを底板へ")
note(B, cx + po["plate"] / 2, y_st + po["plate_t"] / 2, 520, y_st + 40, f"ベースプレート {po['plate']} 角 t{po['plate_t']}＋リブ、アンカー {po['anchor']}。\n株立ちは一枚に 2〜3 本。大引にかかる所は受け替える")
note(B, cx - d / 2, yb_trunk + fe["h"] / 2, 20, yb_trunk - 40, f"鋼の口金 h{fe['h']}")
B.text(520, y_sb + 40, f"床：スギ t{fl['board']}／合板 t{fl['ply']}／大引 {fl['joist']}（鋼製束）／床下 約{fl['void']}／底板 t{fl['slab']}／防湿／砕石 t{fl['gravel']}", fontsize=5.0, va="top", bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"), zorder=8)
B.annotate("", (cx - 80, y_fl), (cx - 80, yb_trunk), arrowprops=dict(arrowstyle="<->", lw=0.4))
B.text(cx - 88, (y_fl + yb_trunk) / 2, f"{so['depth']}", fontsize=5.2, ha="right", va="center")
B.text(1000, 790, "B　足もと（断面）1/5", fontsize=7.5, weight="bold", va="top", ha="right")
# plug inset
px, py = 820, 560
rect(B, px, py, 140, fl["board"], WOOD); rect(B, px + 40, py - 120, 60, 120, STEEL, lw=0.3)
rect(B, px + 42, py - 10, 56, fl["board"] + 10, "#D9B880", z=5)
B.text(px + 70, py + 70, "外したあと：\nスギの栓（床と面一）", fontsize=5.0, ha="center")

# ---------------------------------------------------------------- A: top (elevation 1/5)
A = ax_at(222, 172, 184, 100)       # 920 × 500
def trunk_top(ax, x, base, top, dd, label):
    r = dd / 2
    rect(ax, x - r, base, dd, top - base - r, TRUNK, z=3)
    ax.add_patch(Wedge((x, top - r), r, 0, 180, fc=TRUNK, ec="black", lw=0.5, zorder=3))
    ax.plot([x - r, x - r], [base, top - r], lw=0.5, color="black", zorder=4); ax.plot([x + r, x + r], [base, top - r], lw=0.5, color="black", zorder=4)
    ax.text(x, base - 25, label, fontsize=5.2, ha="center", va="top")
trunk_top(A, 120, 60, 420, 70, "低い木 φ70\n頂部 h0.85〜1.1")
trunk_top(A, 300, 60, 420, 100, "高い木 φ100")
# clump of 3 φ50 with steel bands
for k in range(3):
    trunk_top(A, 470 + k * 50, 60, 420, 50, "" if k != 1 else "株立ち φ50×3\n（締めて一体、同じ高さ）")
for yb in (150, 330):
    rect(A, 445, yb, 150, 18, "#9A9A9A", lw=0.4, z=5)
A.text(605, 330, "金輪（ステンレスの帯、\n何か所か）", fontsize=5.0, va="center")
# tall tree under the rafter
ra = D["rafter"]
rect(A, 700, 440, ra["b"] * 2.5, 60, WOOD); A.text(780, 480, "垂木（の下端）", fontsize=5.0, ha="center")
trunk_top(A, 780, 60, 440 - H["top_gap"] * 1000 * 0.25, 100, "高い木の頂部\n屋根の下 0.1 で止める")
A.annotate("", (840, 440), (840, 440 - H["top_gap"] * 1000 * 0.25), arrowprops=dict(arrowstyle="<->", lw=0.4))
A.text(848, 428, "100（図は縮めて描いた）", fontsize=4.6, va="center")
A.text(0, 495, "A　頂部（立面）1/5　すべて丸く（半球）削り、面を取る。ぶつかっても痛くない", fontsize=7.5, weight="bold", va="top")

# ---------------------------------------------------------------- C: removal
steps = [("①", "六角レンチで\nピンを押し下げる"), ("②", "幹を 90° 回す\n（爪が溝から外れる）"), ("③", f"真上に {so['depth'] // 10 + 5} cm 持ち上げて\n抜く（低い木だけ）"), ("④", "床の穴に栓")]
fig.text(222 / 420, 166 / 297, "C　外し方（付けるときは逆）", fontsize=7.5, weight="bold", va="top")
for k, (n, s) in enumerate(steps):
    x0 = 222 + k * 46
    ax = fig.add_axes([x0 / 420, 112 / 297, 40 / 420, 48 / 297]); ax.set_xlim(0, 40); ax.set_ylim(0, 48); ax.axis("off")
    ax.plot([2, 38], [10, 10], lw=0.8, color="black")
    ax.add_patch(Rectangle((18, 4), 4, 6, fc=STEEL, ec="none"))
    if k <= 1: ax.add_patch(Rectangle((18.5, 5), 3, 30, fc=TRUNK, ec="black", lw=0.3)); ax.add_patch(Circle((20, 35), 1.5, fc=TRUNK, ec="black", lw=0.3))
    if k == 0: ax.annotate("", (23, 10.5), (29, 17), arrowprops=dict(arrowstyle="-|>", lw=0.6))
    if k == 1: ax.add_patch(FancyArrowPatch((14, 24), (26, 24), connectionstyle="arc3,rad=-0.5", arrowstyle="-|>", mutation_scale=6, lw=0.6))
    if k == 2:
        ax.add_patch(Rectangle((18.5, 13), 3, 30, fc=TRUNK, ec="black", lw=0.3)); ax.add_patch(Circle((20, 43), 1.5, fc=TRUNK, ec="black", lw=0.3))
        ax.annotate("", (26, 44), (26, 30), arrowprops=dict(arrowstyle="-|>", lw=0.6))
    if k == 3: ax.add_patch(Rectangle((17.5, 9), 5, 2, fc="#D9B880", ec="black", lw=0.3))
    ax.text(1, 47, n, fontsize=7, va="top", weight="bold")
    fig.text((x0 + 20) / 420, 110 / 297, s, fontsize=5.6, ha="center", va="top")

# ---------------------------------------------------------------- D: how the heights are set (table + notes)
fig.text(14 / 420, 100 / 297, "D　高さの決め方（片持ちの略算）", fontsize=7.5, weight="bold", va="top")
fs = H["f_allow"]; Fk = H["F"]
rows = [("幹", "断面係数 Z（mm³）", "根元で耐える曲げ（kN·m）", f"{Fk} kN を掛けてよい高さ", "高さ（6 版）")]
def zz(dd, k=1): return k * math.pi * (dd * 1000) ** 3 / 32
for lab, dd, k, rule in [("φ50 1 本", 0.05, 1, "使わない（杭の高さ止まり）"), ("φ50 ×2 の株", 0.05, 2, "低い木 0.85〜1.1"), ("φ50 ×3 の株", 0.05, 3, "低い木 0.85〜1.1"),
                         ("φ70 1 本", 0.07, 1, "低い木 0.85〜1.1"), ("φ70 ×2 の株", 0.07, 2, "高い木（屋根の低い東側）／低い木"), ("φ70 ×3 の株", 0.07, 3, "高い木"),
                         ("φ100 1 本", 0.1, 1, "高い木（屋根の下 0.1）"), ("φ200 1 本", 0.2, 1, "高い木")]:
    Z = zz(dd, k); M = Z * fs / 1e6; a = M / Fk
    rows.append((lab, f"{Z:,.0f}", f"{M:.2f}", f"{a:.1f} m まで", rule))
cw = [24, 30, 36, 34, 62]
for i, r in enumerate(rows):
    x = 14
    for j, c in enumerate(r):
        fig.text(x / 420, (93 - i * 4.0) / 297, c, fontsize=5.6, va="top", weight="bold" if i == 0 else "normal", color="#222222")
        x += cw[j]
nt = sum(1 for t in TR if t.get("tall")); nl = len(TR) - nt
notes = [
    f"根元の曲げ＝横の力×力の掛かる高さ。こどもは幹のどこにでも手を掛けられ、登れるので、力は頂部に掛かるとみる。横の力はこどもが押す・引く・ぶら下がって揺らす 0.3 kN（仮）。スギの無等級材の曲げ Fb 22.2 N/mm² の 2/3 ＝ 短期の許容 {fs} N/mm²。",
    "株は金輪で締めても、1 本ずつの断面係数の和で数えた（安全側）。",
    f"耐える高さが屋根の下まで届けば高い木（{nt} 本）、届かなければ低い木（{nl} 本、0.85〜1.1）。低い木はこどもの目の高さ（0.9〜1.0）を隠し、先生の目の高さ（約 1.55）からはこどもの頭が上越しに見える。",
    "揺れの目安：φ100 の 3.5 m の木を 1.2 m の高さで 0.3 kN 押すと、手もとで約 5 mm（E＝7 kN/mm²）。気にならず、生きている感じがする程度。",
    "高い木は真上に抜く余裕がないので抜けない木にする（同じ金物で、ピンを固定ねじに）。",
]
yy = 93 - len(rows) * 4.0 - 2
for s in notes:
    for i, ln in enumerate(textwrap.wrap(s, 98)):
        fig.text((14 + (0 if i == 0 else 2.5)) / 420, yy / 297, ("・" if i == 0 else "") + ln, fontsize=5.6, va="top", color="#333333"); yy -= 3.0
    yy -= 0.6

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"sodachiya_forest_03.{ext}"), dpi=200 if ext == "png" else None)
print("ok")
