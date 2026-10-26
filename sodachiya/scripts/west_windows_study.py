"""本館の西の壁の覗き窓（0〜2歳の西吹き抜け、スパン1〜7）の見かけを比べる（本館係、10-26、監修の項 20261026-2043 の 2）。
道路の側の立面（西から東を見る、右が南）の u0〜21 の部分を、案ごとに一段ずつ並べる。
出力：out/sodachiya_west_windows_study.pdf / .png（A3横）
"""
import os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import subprocess, matplotlib.font_manager as _fm
_TTF = os.path.expanduser('~/.cache/sodachiya_fonts')
if not os.path.exists(os.path.join(_TTF, 'NotoSansCJKjp-Bold.ttf')):
    subprocess.run([sys.executable, os.path.join(ROOT, 'present', 'tools', 'make_ttf.py'), _TTF], check=False)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
if os.path.exists(os.path.join(_TTF, 'NotoSansCJKjp-Bold.ttf')):
    for _f in ('Regular', 'Bold'): _fm.fontManager.addfont(os.path.join(_TTF, f'NotoSansCJKjp-{_f}.ttf'))
    plt.rcParams['font.family'] = _fm.FontProperties(fname=os.path.join(_TTF, 'NotoSansCJKjp-Regular.ttf')).get_name()
plt.rcParams['pdf.fonttype'] = 42
OUT = os.environ.get('OUT', os.path.join(ROOT, 'out'))

WALL_TOP = 4.592          # 西の外壁の上端（越屋根の西の立ち上がり、屋根の厚みで 270 上げた）
GL = -0.30
SPANS = range(1, 8)       # スパン1〜7（u0〜21）
C_WALL, C_GLASS, C_LINE = '#E6D2B0', '#D6E8F2', '#5b4a3a'

def lin(k, a, b):          # スパン k（1〜7）で a → b（等差）
    return a + (b - a) * (k - 1) / 6

CASES = [
    ('A　今：大きく・高く', '幅 0.60→2.00、窓台 0.3→0.9、上端 0.9→2.7。スパン7（窓口）が頂点。北の窓が大きく、面の中で窓が勝つ',
     lambda k: (lin(k, .60, 2.00), lin(k, .30, .90), lin(k, .90, 2.70))),
    ('B　同じ大きさのまま、北へ高く', '0.75×0.75 の正方形、窓台 0.25→1.15（0.15ずつ）。はう子の目（約0.35）→ 立った2歳（約0.8）→ 大人（約1.5）へ視線が上がってゆく',
     lambda k: (.75, lin(k, .25, 1.15), lin(k, .25, 1.15) + .75)),
    ('C　幅は同じ、高さが北へ伸びる', '幅 0.60、窓台 0.30 でそろえ、上端 0.9→2.4。床からの縦長の窓が育つ（背くらべ）',
     lambda k: (.60, .30, lin(k, .90, 2.40))),
    ('D　本館係の案：同じ幅で、下端と上端がずれて上がる', '幅 0.60・高さ 0.90 の縦長、窓台 0.25→1.15。Bより細く縦長で、Cより面が静か。下端は歳の目の高さを追う',
     lambda k: (.60, lin(k, .25, 1.15), lin(k, .25, 1.15) + .90)),
]

W, H = 420, 297
fig = plt.figure(figsize=(W / 25.4, H / 25.4))
fig.text(14 / W, 1 - 14 / H, '西の壁の覗き窓（0〜2歳の西吹き抜け）の見かけを比べる', fontsize=14, weight='bold')
fig.text(14 / W, 1 - 21 / H, '本館係　2026-10-26　道路の側の立面のうち u0〜21（スパン1〜7）、西から東を見る（右が南）　1/125',
         fontsize=8, color='#555')
S = 1 / 125 * 1000          # m → mm（紙）
for i, (name, note, f) in enumerate(CASES):
    col, row = i % 2, i // 2
    x0 = 22 + col * 200; top = H - 40 - row * 118
    ax = fig.add_axes([x0 / W, (top - 57) / H, 21.6 * S / W, 5.6 * S / H])
    ax.set_xlim(21.3, -0.3); ax.set_ylim(GL - 0.25, WALL_TOP + 0.3); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(Rectangle((0, GL), 21.0, WALL_TOP - GL, fc=C_WALL, ec='none', zorder=1))
    for u in np.arange(0.06, 21.0, 0.12):                                    # 大和張りの縦の線
        ax.plot([u, u], [GL, WALL_TOP], color='#b89a74', lw=0.15, zorder=2)
    ax.plot([0, 21, 21, 0, 0], [GL, GL, WALL_TOP, WALL_TOP, GL], color=C_LINE, lw=0.6, zorder=5)
    ax.plot([-0.3, 21.3], [GL, GL], color='k', lw=0.9, zorder=6)
    ax.add_patch(Rectangle((-0.35, WALL_TOP), 21.7, 0.08, fc='#cfe3ee', ec='#5b7f99', lw=0.4, zorder=5))   # 越屋根の蓋（の出）
    for kf in range(0, 8):                                                    # 架構の線（壁の裏の柱）
        ax.plot([3 * kf, 3 * kf], [GL, WALL_TOP], color='#9a8670', lw=0.3, ls=(0, (4, 3)), zorder=3)
    for k in SPANS:
        w, z0, z1 = f(k); c = 3 * k - 1.5
        ax.add_patch(Rectangle((c - w / 2, z0), w, z1 - z0, fc=C_GLASS, ec='#33475a', lw=0.6, zorder=7))
        ax.text(c, GL - 0.12, f'{k}', fontsize=5.5, ha='center', va='top', color='#777')
    for zz, lab in ((0.35, 'はう子の目 0.35'), (0.8, '2歳の目 0.8'), (1.5, '大人の目 1.5')):
        ax.plot([21.05, 21.35], [zz, zz], color='#c0392b', lw=0.5, zorder=8)
        ax.text(21.4, zz, lab, fontsize=4.6, color='#c0392b', ha='right', va='center')
    ax.plot([-0.3, 21.3], [0, 0], color='#888', lw=0.25, ls=':', zorder=4)
    fig.text(x0 / W, (top - 1) / H, name, fontsize=10, weight='bold')
    fig.text(x0 / W, (top - 6.5) / H, note, fontsize=6.3, color='#333', wrap=True)
    a_gl = sum(f(k)[0] * (f(k)[2] - f(k)[1]) for k in SPANS)
    fig.text((x0 + 21.6 * S - 2) / W, (top - 63) / H, f'窓 7 つのガラス 約 {a_gl:.1f} m²', fontsize=7, ha='right', va='top')
fig.text(14 / W, 9 / H, '窓はどれもスパンの真ん中（壁の裏の柱＝破線を避ける）。格子は付けない。左端 u21 から先は西館。'
         '数字はスパンの番号（1〜4 が0・1歳、5〜6 が2歳、7 が窓口・静養室）。', fontsize=6.5, color='#555')
os.makedirs(OUT, exist_ok=True)
for ext in ('pdf', 'png'):
    fig.savefig(os.path.join(OUT, f'sodachiya_west_windows_study.{ext}'), dpi=200 if ext == 'png' else None)
print('written', os.path.join(OUT, 'sodachiya_west_windows_study.pdf'))
