import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle, Ellipse

plt.rcParams["font.family"] = "Noto Sans CJK JP"
MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
# 1/50: 1 m = 20 mm
xmin, xmax, ymin, ymax = -1.5, 17.5, -1.2, 6.0
L, B = 25, 85
ax = fig.add_axes([L / 420, B / 297, (xmax - xmin) * 20 / 420, (ymax - ymin) * 20 / 297])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

def R(x0, y0, x1, y1, fc="white", ec="black", lw=0.6, ls="-", z=3, hatch=None):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, hatch=hatch))
def Ln(pts, lw=0.6, c="black", ls="-", z=3):
    xs, ys = zip(*pts); ax.plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt")
def T(x, y, s, size=7, ha="center", va="center", c="#222222", **kw):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=c, zorder=9, **kw)
def person(x, h, c="#7a8fa6", sit=False):
    head = 0.12 * h / 1.0 if h < 1.3 else 0.12
    if sit:
        R(x - 0.15, 0, x + 0.15, h * 0.55 - 2 * head, fc=c, ec="none", z=6)
        ax.add_patch(Circle((x, h * 0.55 - head), head, fc=c, ec="none", zorder=6))
    else:
        R(x - 0.13 * h, 0, x + 0.13 * h, h - 2 * head, fc=c, ec="none", z=6)
        ax.add_patch(Circle((x, h - head), head, fc=c, ec="none", zorder=6))
def person_at(x, y0, h, c="#7a8fa6"):
    head = 0.12
    R(x - 0.13 * h, y0, x + 0.13 * h, y0 + h - 2 * head, fc=c, ec="none", z=6)
    ax.add_patch(Circle((x, y0 + h - head), head, fc=c, ec="none", zorder=6))

roof = lambda x: 4.0 - x / 12.0          # beam top / roof line, x = v (m east of spine)
GL, FL = -0.3, 0.0
# ground & floor
Ln([(xmin, GL), (xmax, GL)], lw=1.0)
R(0, GL, 13.5, FL, fc="#EEEEEE", ec="black", lw=0.6, z=1)
R(13.5, GL, 15.0, -0.15, fc="#E6DFD0", ec="black", lw=0.6, z=1)      # outer engawa FL-150
# west outer wall + monitor (koshi-yane)
R(-0.15, FL, 0.0, 4.0, fc="#555555", ec="black", lw=0.5)
R(1.55, 2.4, 1.65, roof(1.6), fc="none", ec="black", lw=0.4)           # lattice zone
for y in [2.6, 2.9, 3.2, 3.5]:
    pass
for x in [1.57, 1.6, 1.63]:
    Ln([(x, 2.4), (x, roof(1.6))], lw=0.3)
R(1.55, FL, 1.65, 2.4, fc="#555555", ec="black", lw=0.5)               # room west wall h2.4
Ln([(-0.15, 4.0), (-0.15, 5.1)], lw=0.8); Ln([(1.6, roof(1.6)), (1.6, 5.05)], lw=0.8)
R(-0.15, 4.6, 0.0, 5.05, fc="none", ec="black", lw=0.4, hatch="||||")
R(1.55, 4.6, 1.65, 5.05, fc="#BFD7EA", ec="black", lw=0.4)
Ln([(-1.05, 5.2), (2.5, 5.025)], lw=1.4)                                 # cap 1/20
T(0.8, 5.55, "越屋根", 7)
# roof + beams + eave
Ln([(0, roof(0) + 0.15), (15.0, roof(15.0) + 0.15)], lw=1.4)
Ln([(0, roof(0)), (15.0, roof(15.0))], lw=0.5)
Ln([(0, roof(0) - 0.6), (12.0, roof(12.0) - 0.6), (15.0, roof(15.0) - 0.25)], lw=0.5, ls=(0, (5, 2)))
T(7.0, roof(7.0) - 0.35, "梁（2枚組、せい600）は3 mごと（破線）", 6, c="#555555")
# east column + glass line
R(11.8, FL, 12.2, roof(12.0) - 0.6, fc="#C9A97A", ec="black", lw=0.5)
gt = roof(13.5) - 0.6 + 0.05
R(13.45, FL, 13.55, gt, fc="#BFD7EA", ec="black", lw=0.5)
R(13.45, FL, 13.55, 0.45, fc="#C9A97A", ec="black", lw=0.4, hatch="||")
R(13.42, gt - 0.08, 13.58, gt, fc="#C9A97A", ec="black", lw=0.4)
Ln([(13.5, gt), (13.5, roof(13.5))], lw=0.4, c="#3d7fb0")
# book street shelves (west wall of the void) + low shelves on the room wall
R(0.0, FL, 0.3, 0.9, fc="#F3E7CF", ec="black", lw=0.5)
R(1.65, FL, 1.95, 0.9, fc="#F3E7CF", ec="black", lw=0.5)
T(0.8, 1.2, "絵本の通り", 6.5)
# loft in the next bay (beyond, dashed)
R(1.65, 1.05, 3.6, 1.2, fc="none", ec="#8a5a2b", lw=0.7, ls=(0, (5, 2)))
Ln([(1.65, 2.1), (3.6, 2.1)], lw=0.6, c="#8a5a2b", ls=(0, (5, 2)))
T(3.1, 2.35, "隣の梁間のロフト h1200（奥）", 6.0, c="#8a5a2b")
# quiet desk (outward-curved), child sits on the west side facing the wall
R(2.2, 0.45, 2.65, 0.5, fc="#F7F1E6", ec="black", lw=0.5)
Ln([(2.25, 0), (2.25, 0.45)], lw=0.5)
R(2.85, 0.25, 3.15, 0.28, fc="white", ec="black", lw=0.4)
person(3.0, 1.0, "#c58e5a", sit=True)
T(2.8, 1.55, "しずかな机\n（西を向いて座る）", 6.2, c="#555555")
# open floor: nap cot, rug figures, teacher
R(5.0, 0.0, 6.05, 0.12, fc="none", ec="#4f6b2a", lw=0.6, ls=(0, (2, 1.5)))
T(5.5, 0.3, "コット（午睡）", 6, c="#4f6b2a")
person(7.4, 1.6, "#6f86a0")
person(8.1, 1.02, "#c58e5a")
# tables
for x0 in [9.0, 10.6]:
    R(x0, 0.40, x0 + 1.2, 0.45, fc="#F7F1E6", ec="black", lw=0.5)
    Ln([(x0 + 0.1, 0), (x0 + 0.1, 0.40)], lw=0.5); Ln([(x0 + 1.1, 0), (x0 + 1.1, 0.40)], lw=0.5)
person(9.2, 1.0, "#c58e5a", sit=True); person(11.6, 1.0, "#c58e5a", sit=True)
# engawa people
person(12.9, 1.05, "#c58e5a")
person_at(14.3, -0.15, 1.05, "#c58e5a")
# labels + dims
for x, s in [(0.8, "西吹き抜け\n1,600"), (7.0, "保育室 10,400"), (12.75, "内縁側\n1,500"), (14.25, "外縁側\n1,500（土足）")]:
    T(x, -0.75, s, 7)
for x in [0, 1.6, 12.0, 13.5, 15.0]:
    Ln([(x, -0.42), (x, -0.5)], lw=0.4)
Ln([(0, -0.46), (15.0, -0.46)], lw=0.4)
T(2.65, 3.2, "西の壁の上の縦格子から\n西吹き抜けの光が落ちる", 6.2, c="#555555")
T(13.5, gt + 0.3, "引き戸（腰なし）\n段の蹴込みにガラリ", 6.2, c="#3d7fb0")
# height marks
T(-0.9, roof(0) - 0.1, "4,000", 6.2); T(12.0, roof(12.0) + 0.35, "3,000", 6.2)
fig.text(25 / 420, 285 / 297, "育ち舎　3〜5歳の保育室　断面のたたき台", fontsize=12.5, weight="medium", va="top")
fig.text(25 / 420, 277 / 297, "1/50（A3）　2026-10-20　梁と梁のあいだで切る。人の高さ：先生 1,600、5歳 約1,100、3歳 約950。",
         fontsize=7, va="top", color="#444444")
fig.text(25 / 420, 40 / 297,
         "・西から、絵本の通り（西吹き抜け）→ しずかな机 → あつまり・午睡 → 食卓 → 内縁側 → 外縁側。静から動へ、暗から明へ。\n"
         "・しずかな机は西へふくらむ弧。子どもは弧の内側から西を向いて座り、隣の子と少しそっぽを向く（ソシオフーガル）。正面は西の壁と縦格子の光。\n"
         "・西の二つの梁間のうち、片方が「しずかな角」（角のない曲線の机、奥は収納）、もう片方がロフト h1200（下はデンとコット収納）。",
         fontsize=7, va="top", color="#333333", linespacing=1.6)
fig.savefig(_os.path.join(OUT, "sodachiya_35_section.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_35_section.png"), dpi=200)
