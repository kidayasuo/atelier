# ホールの北山杉の林：幹の頭と足もとの納まり 1/5（A3 横）、外し方
# 寸法は data/forest.json の DETAIL。垂木・野地・床の構成は仮（木造に確認）。
import json, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
F = json.load(open(os.path.join(ROOT, "data", "forest.json")))
D = F["DETAIL"]

MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
fig.text(14 / 420, 288 / 297, "ホールの北山杉の林　幹の頭と足もと 1/5（たたき台）", fontsize=11, weight="bold", va="top")
fig.text(14 / 420, 281 / 297, "頭は深いさやに差すだけ（上下に逃げがあるので、屋根のたわみも雪も幹に掛からない＝構造ではない）。足もとは差して回すと抜けない金物。"
         "抜ける幹も抜けない幹も同じ金物で、抜けない幹はピンを固定ねじにするだけ。垂木・野地・床の構成は仮（木造に確認）。", fontsize=6.2, va="top")

WOOD = "#E8D2A6"; STEEL = "#8C8C8C"; TRUNK = "#C9A27A"; INS = "#F3E9C9"; CON = "#D5D5D5"

def ax_at(x, y, w, h, scale=5):
    """紙の上の mm で置き、中は実寸 mm（scale 分の 1）"""
    ax = fig.add_axes([x / 420, y / 297, w / 420, h / 297]); ax.set_xlim(0, w * scale); ax.set_ylim(0, h * scale)
    ax.set_aspect("equal"); ax.axis("off"); return ax
def rect(ax, x, y, w, h, fc, ec="black", lw=0.5, hatch=None, z=2):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, hatch=hatch, zorder=z))
def dim(ax, x0, y0, x1, y1, s, off=0, side="r", fs=5.2):
    ax.annotate("", (x0, y0), (x1, y1), arrowprops=dict(arrowstyle="<->", lw=0.4, color="#333333"))
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    ax.text(xm + (off if side == "r" else -off), ym, s, fontsize=fs, ha="left" if side == "r" else "right", va="center", color="#333333")
def note(ax, x, y, tx, ty, s, fs=5.4):
    ax.annotate(s, (x, y), (tx, ty), fontsize=fs, arrowprops=dict(arrowstyle="-", lw=0.35, color="#555555"), va="center", color="#222222")

d = D["d"]                        # 図は φ70 で描く
# ---------------------------------------------------------------- A: head (section across the rafters, 1/5)
A = ax_at(14, 150, 200, 122)      # 1000 × 610 mm
ra = D["rafter"]; nj = D["noji_t"]
y_noji = 400                      # 野地の下端（図の座標）
rect(A, 0, y_noji, 1000, nj, WOOD)                              # 野地
rect(A, 0, y_noji + nj, 1000, D["ins_t"], INS, hatch="////")    # 断熱
rect(A, 0, y_noji + nj + D["ins_t"], 1000, 12, "#B0B0B0")       # 屋根の仕上げ（仮）
for x in (20, 20 + ra["pitch"], 20 + ra["pitch"] + 260):
    rect(A, x, y_noji - ra["h"], ra["b"], ra["h"], WOOD)        # 垂木（3 本目は②の説明のため間隔を詰めて描く）
A.text(1000, y_noji + nj + D["ins_t"] / 2, "断熱（仮）", fontsize=5.2, ha="right", va="center")
A.text(1000, y_noji + nj / 2, "野地（仮） ", fontsize=5.2, ha="right", va="center")
# case 1: between rafters → cup on 野地
cx = 20 + ra["b"] + (ra["pitch"] - ra["b"]) / 2
cup = D["cup"]
rect(A, cx - cup["plate"] / 2, y_noji - cup["plate_t"], cup["plate"], cup["plate_t"], STEEL, z=4)
rect(A, cx - (d / 2 + cup["clear"] + cup["wall"]), y_noji - cup["plate_t"] - cup["depth"], cup["wall"], cup["depth"], STEEL, z=4)
rect(A, cx + d / 2 + cup["clear"], y_noji - cup["plate_t"] - cup["depth"], cup["wall"], cup["depth"], STEEL, z=4)
t_top = y_noji - cup["plate_t"] - cup["depth"] + cup["insert"]
rect(A, cx - d / 2, 0, d, t_top, TRUNK, z=3)
rect(A, cx - d / 2 - 1, t_top - cup["insert"] + 10, d + 2, 12, "#333333", lw=0, z=5)            # ゴムの輪
for sx in (-1, 1): A.plot([cx + sx * cup["plate"] / 2 * 0.7] * 2, [y_noji - cup["plate_t"], y_noji + nj * 0.8], lw=0.8, color="#333333", zorder=5)
dim(A, cx + 60, t_top, cx + 60, y_noji - cup["plate_t"], f"逃げ {y_noji - cup['plate_t'] - t_top:.0f}", off=6)
dim(A, cx + 100, y_noji - cup["plate_t"] - cup["depth"], cx + 100, t_top, f"差し込み {cup['insert']}", off=6)
note(A, cx - 30, y_noji - 4, 10, y_noji - 200, f"鋼板 {cup['plate']}×{cup['plate']} t{cup['plate_t']}\n木ねじ 4 本で野地に（野地を貫かない）")
note(A, cx - d / 2 - cup["clear"] - cup["wall"], y_noji - 90, 10, y_noji - 260, f"さや：鋼管 内径 φ{d + 2 * cup['clear']}・深さ {cup['depth']}（黒の焼付）")
note(A, cx - d / 2, t_top - cup["insert"] + 16, 10, y_noji - 310, "ゴムの輪（がたつき止め）")
A.text(cx, 150, f"幹 φ{d}", fontsize=5.4, ha="center", rotation=90)
A.text(cx + 40, 60, "①垂木と垂木のあいだ：\n野地に留める", fontsize=5.8, ha="center", weight="bold", color="#8a5a2b")
# case 2: under a rafter → plate on the rafter's underside
cx2 = 20 + ra["pitch"] + ra["b"] / 2 + 260
for x in (20 + ra["pitch"] + 260,): pass
yb = y_noji - ra["h"]
rect(A, cx2 - cup["plate"] / 2, yb - cup["plate_t"], cup["plate"], cup["plate_t"], STEEL, z=4)
rect(A, cx2 - (d / 2 + cup["clear"] + cup["wall"]), yb - cup["plate_t"] - cup["depth"], cup["wall"], cup["depth"], STEEL, z=4)
rect(A, cx2 + d / 2 + cup["clear"], yb - cup["plate_t"] - cup["depth"], cup["wall"], cup["depth"], STEEL, z=4)
t2 = yb - cup["plate_t"] - cup["depth"] + cup["insert"]
rect(A, cx2 - d / 2, 0, d, t2, TRUNK, z=3)
A.text(cx2 + 40, 60, "②垂木の真下に来たら：\n垂木の下面に留める", fontsize=5.8, ha="left", weight="bold", color="#8a5a2b")
A.text(1000, 590, "A　頭（垂木を横に切る断面）1/5", fontsize=7.5, weight="bold", va="top", ha="right")
A.text(1000, 565, f"垂木 {ra['b']}×{ra['h']}＠{ra['pitch']}（南北、梁と梁のあいだ 3 m に掛ける：仮）", fontsize=5.2, va="top", ha="right", color="#555555")

# ---------------------------------------------------------------- B: foot (section, 1/5)
B = ax_at(222, 150, 184, 122)     # 920 × 610
fl = D["floor"]; so = D["socket"]
y_fl = 420
rect(B, 0, y_fl - fl["board"], 920, fl["board"], WOOD)                                   # 床板
rect(B, 0, y_fl - fl["board"] - fl["base"], 920, fl["base"], "#EFE6D2", hatch="..")      # 下地（仮）
rect(B, 0, y_fl - fl["board"] - fl["base"] - fl["slab"], 920, fl["slab"], CON, hatch="xx")  # 土間コンクリート
B.text(5, y_fl - fl["board"] - fl["base"] - fl["slab"] - 18, f"床板 スギ t{fl['board']}／下地 {fl['base']}／土間コンクリート t{fl['slab']}（仮）", fontsize=5.2, va="top")
cx = 300
# socket (steel pipe with bayonet L-slot), anchored to the slab
sx0 = cx - d / 2 - so["clear"] - so["wall"]; sx1 = cx + d / 2 + so["clear"]
rect(B, sx0, y_fl - so["depth"], so["wall"], so["depth"], STEEL, z=4)
rect(B, sx1, y_fl - so["depth"], so["wall"], so["depth"], STEEL, z=4)
rect(B, sx0, y_fl - so["depth"] - 8, sx1 + so["wall"] - sx0, 8, STEEL, z=4)                # 底板
rect(B, sx0 - 40, y_fl - so["depth"] - 8 - 6, sx1 + so["wall"] - sx0 + 80, 6, STEEL, z=4)  # 受けの鋼板（スラブにアンカー）
for ax_ in (sx0 - 25, sx1 + so["wall"] + 25): rect(B, ax_ - 5, y_fl - so["depth"] - 120, 10, 110, "#555555", lw=0, z=4)
# L slot (drawn on the far wall as a dashed L)
B.plot([sx1 + so["wall"] / 2] * 2, [y_fl, y_fl - so["slot"]], lw=0.6, color="white", zorder=6)
# trunk with ferrule and lug
fe = D["ferrule"]
rect(B, cx - d / 2, y_fl - so["depth"] + 4, d, 600 - (y_fl - so["depth"] + 4), TRUNK, z=3)
rect(B, cx - d / 2 - 1, y_fl - so["depth"] + 4, d + 2, fe["h"], "#9A9A9A", z=5)              # 鋼の口金
B.add_patch(Circle((cx + d / 2 + 3, y_fl - so["slot"] + 10), 5, fc="#333333", ec="none", zorder=6))   # 爪（溝にかかる）
# brass ring + spring pin
rect(B, sx0 - 18, y_fl - 6, (sx1 + so["wall"] - sx0) + 36, 6, "#C9A45A", z=6)
B.add_patch(Circle((sx1 + so["wall"] + 8, y_fl - 3), 3, fc="#333333", ec="none", zorder=7))
note(B, sx1 + so["wall"] + 8, y_fl - 3, sx1 + 160, y_fl + 130, "ばね付きのピン（六角レンチで押し下げると回せる）\n抜けない幹は、ここを固定ねじに", fs=5.2)
note(B, sx0 - 10, y_fl - 3, 10, y_fl + 60, "真鍮の輪（床と面一）", fs=5.2)
note(B, cx + d / 2 + 3, y_fl - so["slot"] + 10, sx1 + 160, y_fl + 60, f"口金の爪 2 か所が、さやの L 字の溝（深さ {so['slot']}）にかかる\n差して 90° 回すと抜けない", fs=5.2)
note(B, sx0, y_fl - so["depth"] + 20, 10, y_fl + 120, f"さや：鋼管 内径 φ{d + 2 * so['clear']}・深さ {so['depth']}\n受けの鋼板をスラブにアンカー", fs=5.2)
note(B, cx - d / 2, y_fl - so["depth"] + fe["h"] / 2, 10, y_fl + 175, f"鋼の口金 h{fe['h']}（幹の根元にかぶせてピンで留める）", fs=5.2)
dim(B, cx + 120, y_fl - so["depth"], cx + 120, y_fl, f"{so['depth']}", off=5)
B.text(920, 600, "B　足もと（断面）1/5", ha="right", fontsize=7.5, weight="bold", va="top")
# plug (when removed), small inset
px, py = 730, 330
rect(B, px, py, 120, fl["board"], WOOD); rect(B, px + 30, py - so["depth"] + fl["board"], 60, so["depth"] - fl["board"], STEEL, lw=0.3)
rect(B, px + 32, py - 8, 56, fl["board"] + 8, "#D9B880", z=5)
B.text(px + 60, py + 120, "外したあと：スギの栓で\nふさぐ（床と面一）", fontsize=5.0, ha="center")

# ---------------------------------------------------------------- C: how to remove (pictograms)
steps = [("①", "六角レンチで\nピンを押し下げる"), ("②", "幹を 90° 回す\n（爪が溝から外れる）"), ("③", f"持ち上げる\n（頭がさやの奥へ {D['cup']['depth'] - D['cup']['insert']} 逃げる）"),
         ("④", "足を手前に振り出し\n下ろして頭を抜く"), ("⑤", "床の穴に栓")]
fig.text(14 / 420, 140 / 297, "C　外し方（付けるときは逆）", fontsize=7.5, weight="bold", va="top")
for k, (n, s) in enumerate(steps):
    x0 = 14 + k * 50
    ax = fig.add_axes([x0 / 420, 70 / 297, 44 / 420, 62 / 297]); ax.set_xlim(0, 44); ax.set_ylim(0, 62); ax.axis("off")
    ax.plot([2, 42], [8, 8], lw=0.8, color="black"); ax.plot([2, 42], [56, 56], lw=0.8, color="black")
    ax.add_patch(Rectangle((19, 50), 6, 6, fc=STEEL, ec="none"))
    if k <= 1: ax.add_patch(Rectangle((20.5, 8), 3, 44, fc=TRUNK, ec="black", lw=0.3))
    if k == 0: ax.annotate("", (26, 9), (32, 16), arrowprops=dict(arrowstyle="-|>", lw=0.6))
    if k == 1: ax.add_patch(FancyArrowPatch((15, 30), (29, 30), connectionstyle="arc3,rad=-0.5", arrowstyle="-|>", mutation_scale=6, lw=0.6))
    if k == 2:
        ax.add_patch(Rectangle((20.5, 11), 3, 44, fc=TRUNK, ec="black", lw=0.3)); ax.annotate("", (22, 58), (22, 40), arrowprops=dict(arrowstyle="-|>", lw=0.6))
    if k == 3:
        ax.add_patch(Polygon([(20.5, 54), (23.5, 54), (31, 12), (28, 12)], fc=TRUNK, ec="black", lw=0.3))
        ax.add_patch(FancyArrowPatch((26, 10), (36, 14), arrowstyle="-|>", mutation_scale=6, lw=0.6))
    if k == 4: ax.add_patch(Rectangle((19, 7), 6, 2, fc="#D9B880", ec="black", lw=0.3))
    ax.text(1, 61, n, fontsize=7, va="top", weight="bold")
    fig.text((x0 + 22) / 420, 66 / 297, s, fontsize=5.6, ha="center", va="top")

# ---------------------------------------------------------------- D: notes
yy = 140
fig.text(272 / 420, yy / 297, "D　決めたこと・確かめること", fontsize=7.5, weight="bold", va="top"); yy -= 6
import textwrap
W = [(t["d"]) for t in F["TREES"]]
notes = [
    f"抜ける幹は {sum(1 for t in F['TREES'] if t.get('removable'))} 本（平面図の青い輪）。重さの目安（スギ 4 m）：φ50 約 3 kg、φ70 約 6 kg（先生 1 人）、φ100 約 12 kg（2 人）。",
    "頭のさやは、幹の頭が上下に逃げられる長さにしてある。屋根がたわんでも（雪・人）幹は押されず、幹は屋根を支えない（構造ではない）。地震で屋根が横に動いても、細い幹はしなって追従する。",
    "頭に掛かる力は横向きだけ（こどもが揺らす・ぶら下がる、0.5 kN 程度）。鋼板を木ねじ 4 本で野地か垂木に留めれば足りる（野地は貫かない＝断熱・防水に触らない）。",
    "株立ち（2〜3 本が触れあう）は、足もとのさやを 1 枚の鋼板に 2〜3 本まとめ、頭のさやも 1 枚の鋼板にまとめる。株ごと外す。",
    "立った位置がたまたま梁（2 枚組）のあいだなら、幹はそのまま抜けて上の野地に留まる。",
    "こどもが外さないように：ピンは六角レンチでしか動かない。抜けない幹は同じ金物でピンを固定ねじに替えるだけ（あとで抜ける幹に変えられる）。",
    "確かめること（木造へ）：垂木の向き・寸法・間隔、野地の厚さ、床の構成（スギ板＋下地＋土間コンクリート）は仮。",
]
for s in notes:
    for i, ln in enumerate(textwrap.wrap(s, 50)):
        fig.text((272 + (0 if i == 0 else 2.5)) / 420, yy / 297, ("・" if i == 0 else "") + ln, fontsize=5.6, va="top", color="#333333"); yy -= 3.0
    yy -= 0.8

os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"sodachiya_forest_03.{ext}"), dpi=200 if ext == "png" else None)
print("ok")
