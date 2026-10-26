# ホールの北山杉の林：幹の足もと（深いさや）と頂部 1/5、外し方、高さの決め方（A3 横）。6 版（すべて自立）
# 寸法は data/forest.json の DETAIL・PARAMS.HEIGHT。床の構成は仮（木造に確認）。
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
         "抜ける幹は差して回す金物で、真上に抜く。床の構成は仮（木造に確認）。", fontsize=6.2, va="top")
WOOD = "#E8D2A6"; STEEL = "#8C8C8C"; TRUNK = "#C9A27A"; CON = "#D5D5D5"

def ax_at(x, y, w, h, scale=5):
    ax = fig.add_axes([x / 420, y / 297, w / 420, h / 297]); ax.set_xlim(0, w * scale); ax.set_ylim(0, h * scale)
    ax.set_aspect("equal"); ax.axis("off"); return ax
def rect(ax, x, y, w, h, fc, ec="black", lw=0.5, hatch=None, z=2):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, hatch=hatch, zorder=z))
def note(ax, x, y, tx, ty, s, fs=5.2):
    ax.annotate(s, (x, y), (tx, ty), fontsize=fs, arrowprops=dict(arrowstyle="-", lw=0.35, color="#555555"), va="center", color="#222222")

d = D["d"]; so = D["socket"]; fl = D["floor"]; pier = D["pier"]; fe = D["ferrule"]

# ---------------------------------------------------------------- B: foot (section 1/5)
B = ax_at(14, 112, 200, 160)        # 1000 × 800 mm
y_fl = 640
rect(B, 0, y_fl - fl["board"], 1000, fl["board"], WOOD)
rect(B, 0, y_fl - fl["board"] - fl["base"], 1000, fl["base"], "#EFE6D2", hatch="..")
y_slab = y_fl - fl["board"] - fl["base"]
rect(B, 0, y_slab - fl["slab"], 1000, fl["slab"], CON, hatch="xx")
B.add_patch(Polygon([(0, y_slab - fl["slab"]), (1000, y_slab - fl["slab"]), (1000, 0), (0, 0)], fc="#EDE3D0", ec="none", zorder=1))   # 地盤
cx = 330
rect(B, cx - pier["d"] / 2, y_slab - fl["slab"] - pier["h"], pier["d"], pier["h"], CON, hatch="xx", z=2)   # 小さな基礎（杭）
sx0 = cx - d / 2 - so["clear"] - so["wall"]; sx1 = cx + d / 2 + so["clear"]
rect(B, sx0, y_fl - so["depth"], so["wall"], so["depth"], STEEL, z=4)
rect(B, sx1, y_fl - so["depth"], so["wall"], so["depth"], STEEL, z=4)
rect(B, sx0, y_fl - so["depth"] - 8, sx1 + so["wall"] - sx0, 8, STEEL, z=4)
for k in range(3):                                                       # さやの外のリブ（コンクリートに効かせる）
    yy_ = y_fl - so["depth"] + 40 + k * 80
    rect(B, sx0 - 25, yy_, 25, 6, STEEL, lw=0.3, z=4); rect(B, sx1 + so["wall"], yy_, 25, 6, STEEL, lw=0.3, z=4)
rect(B, cx - d / 2, y_fl - so["depth"] + 4, d, 800 - (y_fl - so["depth"] + 4), TRUNK, z=3)
rect(B, cx - d / 2 - 1, y_fl - so["depth"] + 4, d + 2, fe["h"], "#9A9A9A", z=5)
B.add_patch(Circle((cx + d / 2 + 3, y_fl - so["slot"] + 10), 5, fc="#333333", ec="none", zorder=6))
rect(B, sx0 - 18, y_fl - 6, (sx1 + so["wall"] - sx0) + 36, 6, "#C9A45A", z=6)
B.add_patch(Circle((sx1 + so["wall"] + 8, y_fl - 3), 3, fc="#333333", ec="none", zorder=7))
note(B, sx1 + so["wall"] + 8, y_fl - 3, 520, y_fl + 110, "ばね付きのピン（六角レンチで押し下げると回せる）\n抜けない幹は、ここを固定ねじに")
note(B, sx0 - 10, y_fl - 3, 20, y_fl + 70, "真鍮の輪（床と面一）")
note(B, cx + d / 2 + 3, y_fl - so["slot"] + 10, 520, y_fl + 50, f"口金の爪 2 か所が、さやの L 字の溝（上端から {so['slot']}）にかかる。差して 90° 回すと抜けない")
note(B, sx1 + so["wall"], y_fl - so["depth"] / 2, 520, 385, f"さや：鋼管 内径 φ{d + 2 * so['clear']}・深さ {so['depth']}、外にリブ。\n床の下地・土間コンクリートを貫いて小さな基礎に埋める")
note(B, cx + pier["d"] / 2, y_slab - fl["slab"] - pier["h"] / 2, 520, 250,
     f"小さな基礎：φ{pier['d']}×{pier['h']}（コンクリート、土間とつなぐ）。株立ちは一つの基礎に 2〜3 本のさや")
note(B, cx + d / 2, y_fl - so["depth"] + fe["h"] / 2, 520, 320, f"鋼の口金 h{fe['h']}（幹の根元にかぶせてピンで留める）")
B.text(520, 180, f"床板 スギ t{fl['board']}／下地 {fl['base']}／土間コンクリート t{fl['slab']}（仮）", fontsize=5.0, va="top")
B.annotate("", (cx - 80, y_fl), (cx - 80, y_fl - so["depth"]), arrowprops=dict(arrowstyle="<->", lw=0.4))
B.text(cx - 88, y_fl - so["depth"] / 2, f"{so['depth']}", fontsize=5.2, ha="right", va="center")
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
