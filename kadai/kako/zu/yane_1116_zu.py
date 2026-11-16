# -*- coding: utf-8 -*-
"""図：屋根の一般部の層（断面、2026-11-16 版2）。

高さは梁の上端を0とする（mm）。育ち舎の「屋根の構成」（sodachiya/kettei/nishikan.md、kyoutsu.md）に、
11-16の決定（梁の上まで断熱を連続、約50）を足した。
  母屋 杉60×150@455 −324〜−174（梁と梁のあいだに渡す、両端は梁の側面の金物）
  合板 t24 −174〜−150（母屋の上、天井に現す、4周釘打ち）
  断熱（板状）−150〜0（梁のあいだ、梁の上端とツラ）
  連続の断熱 0〜50（梁の上端も含めて一枚、11-16）
  通気垂木 50〜95（勾配の向き。断面と間隔は仮）
  野地と屋根材 95〜159（育ち舎の64）
対の梁 160×2、梁のあいだ（光の筋）約194（柱300−2×凹み53）。下端は切って描く。
光の筋のガラスと、そのまわりの納まりは未定（形は仮に描く）。勾配は省いて水平に描いた。
"""
import os
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'sodachiya', 'scripts'))
import fonts42  # noqa: F401,E402

T, G = 160, 194                 # 梁の幅（1本）・梁のあいだ
LAY = [  # 名前, 下, 上, 色
    ('屋根材と太陽光 約40', 119, 159, '#8c8c8c'),
    ('野地 t24', 95, 119, '#c9a86a'),
    ('通気垂木 60×45（通気層）', 50, 95, None),
    ('連続の断熱 50（11-16）', 0, 50, '#f3e27a'),
    ('断熱（板状）150', -150, 0, '#f7ec9f'),
    ('構造用合板 t24（天井に現す）', -174, -150, '#d9b77e'),
    ('母屋 杉60×150@455', -324, -174, '#e6cfa0'),
]
WOOD, BEAM = '#e6cfa0', '#d8b87f'
AIR, WRB, RFG = '#d0392b', '#1f7a3a', '#1f3f8a'   # 気密シート・透湿防水シート・ルーフィング


def sheets(ax, a, b):
    ax.plot([a, b], [50, 50], color=WRB, lw=1.6, zorder=5)     # 透湿防水シート（連続の断熱の上）
    ax.plot([a, b], [119, 119], color=RFG, lw=1.6, zorder=5)   # ルーフィング（野地の上）

fig = plt.figure(figsize=(11.7, 8.3))


def dims(ax, x):
    for name, lo, hi, _ in LAY:
        ax.plot([x - 15, x + 15], [hi, hi], color='#333', lw=0.6)
        ax.text(x - 25, hi, '%+d' % hi if hi else '0', fontsize=6.5, ha='right', va='center')
    ax.plot([x - 15, x + 15], [-324, -324], color='#333', lw=0.6)
    ax.text(x - 25, -324, '−324', fontsize=6.5, ha='right', va='center')
    ax.plot([x, x], [-324, 159], color='#333', lw=0.6)
    ax.text(x - 70, -8, '（梁の上端）', fontsize=6.5, ha='right', va='top', color='#a33')


def labels(ax, x):
    for name, lo, hi, _ in LAY:
        ax.text(x, (lo + hi) / 2, name, fontsize=7, va='center')
    for y, name, c in ((119, 'ルーフィング', RFG), (50, '透湿防水シート', WRB), (-150, '気密シート\n（梁の側面で立ち上げ）', AIR)):
        ax.text(x + 600, y, '─ ' + name, fontsize=6.5, va='center', color=c)


# ---- 断面A：梁に直角（母屋の向き）
ax = fig.add_axes([0.03, 0.47, 0.94, 0.45])
ax.set_aspect('equal'); ax.axis('off')
L = 1250
bl = (-G / 2 - T, -G / 2)       # 左の梁
br = (G / 2, G / 2 + T)         # 右の梁
BOT = -520
for a, b in (bl, br):
    ax.add_patch(Rectangle((a, BOT), b - a, -BOT, fc=BEAM, ec='#6b5530', lw=1.0, zorder=3))
    ax.plot([a - 10, b + 10], [BOT, BOT], color='white', lw=3, zorder=4)
    ax.plot([a - 10, a + 40, a + 70, b + 10], [BOT + 8, BOT + 8, BOT - 12, BOT - 12], color='#6b5530', lw=0.8, zorder=5)
for side in (-1, 1):
    x0 = bl[0] if side < 0 else br[1]
    x1 = -L if side < 0 else L
    lo_, hi_ = min(x0, x1), max(x0, x1)
    # 母屋（立面で見える、梁の側面から渡る）・合板・断熱
    ax.add_patch(Rectangle((lo_, -324), hi_ - lo_, 150, fc=WOOD, ec='#6b5530', lw=0.6))
    ax.add_patch(Rectangle((lo_, -174), hi_ - lo_, 24, fc='#d9b77e', ec='#6b5530', lw=0.6))
    ax.add_patch(Rectangle((lo_, -150), hi_ - lo_, 150, fc='#f7ec9f', ec='#b8a640', lw=0.6))
    # 金物（母屋の端、梁の側面）
    gx = x0 - 6 if side < 0 else x0
    ax.add_patch(Rectangle((gx, -330), 6, 160, fc='#555', ec='none', zorder=4))
    # 連続の断熱・通気垂木の断面・野地と屋根材（光の筋の所で切れる）
    e0 = -G / 2 if side < 0 else G / 2
    lo2, hi2 = (min(e0, x1), max(e0, x1))
    ax.add_patch(Rectangle((lo2, 0), hi2 - lo2, 50, fc='#f3e27a', ec='#b8a640', lw=0.6))
    ax.add_patch(Rectangle((lo2, 95), hi2 - lo2, 24, fc='#c9a86a', ec='#6b5530', lw=0.6))
    ax.add_patch(Rectangle((lo2, 119), hi2 - lo2, 40, fc='#8c8c8c', ec='#555', lw=0.6))
    sheets(ax, lo2, hi2)
    ax.plot([lo_, hi_], [-150, -150], color=AIR, lw=1.6)
    for k in range(4):
        xr = (e0 - 120 - k * 455) if side < 0 else (e0 + 75 + k * 455)
        if abs(xr) < L - 45:
            ax.add_patch(Rectangle((xr, 50), 60, 45, fc=WOOD, ec='#6b5530', lw=0.6))
    # 破断線
    ax.plot([x1, x1], [-340, 175], color='#333', lw=0.8, ls=(0, (4, 2)))
for xb in (bl[0], br[1]):
    ax.plot([xb, xb], [-150, -2], color=AIR, lw=1.6, zorder=5)
# 光の筋：ガラス（仮）と鋼の平板
ax.add_patch(Rectangle((-G / 2 - 30, 120), G + 60, 16, fc='#bfe3f2', ec='#4a90b8', lw=0.8, zorder=6))
ax.add_patch(Rectangle((-G / 2 - 60, -6), G + 120, 6, fc='#555', ec='none', zorder=6))
ax.text(0, 175, '光の筋（ガラス、納まりは未定・仮に描く）', fontsize=7, ha='center', color='#2a6a90')
ax.text(0, -50, '梁のあいだ\n約194', fontsize=6.5, ha='center', va='top')
ax.annotate('鋼の平板6×60（約0.9 mおき、梁の上端に彫り込み）', xy=(G / 2 + 50, -3), xytext=(560, -440),
            fontsize=6.5, arrowprops=dict(arrowstyle='-', lw=0.5))
ax.annotate('母屋の端の金物（梁の側面）', xy=(bl[0] - 3, -250), xytext=(-1180, -470), fontsize=6.5,
            arrowprops=dict(arrowstyle='-', lw=0.5))
ax.text(bl[0] + T / 2, BOT + 30, '梁160', fontsize=6.5, ha='center', rotation=90, zorder=6)
ax.text(br[0] + T / 2, BOT + 30, '梁160', fontsize=6.5, ha='center', rotation=90, zorder=6)
ax.text(-700, -360, '母屋は梁と梁のあいだ（3 m）に渡る。この断面では母屋の側面が見える', fontsize=6.5, ha='center', va='top')
dims(ax, -L - 160)
labels(ax, L + 40)
ax.text(-L - 520, 260, '断面A：梁に直角に切る（母屋の向き、架構kの対の梁のところ）', fontsize=10, fontweight='bold')
ax.set_xlim(-L - 560, L + 1150); ax.set_ylim(BOT - 40, 300)

# ---- 断面B：梁に平行（勾配の向き、梁と梁のあいだ）
ax = fig.add_axes([0.03, 0.06, 0.94, 0.36])
ax.set_aspect('equal'); ax.axis('off')
L2 = 1250
ax.add_patch(Rectangle((-L2, -150), 2 * L2, 150, fc='#f7ec9f', ec='#b8a640', lw=0.6))
ax.add_patch(Rectangle((-L2, -174), 2 * L2, 24, fc='#d9b77e', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((-L2, 0), 2 * L2, 50, fc='#f3e27a', ec='#b8a640', lw=0.6))
ax.add_patch(Rectangle((-L2, 50), 2 * L2, 45, fc=WOOD, ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((-L2, 95), 2 * L2, 24, fc='#c9a86a', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((-L2, 119), 2 * L2, 40, fc='#8c8c8c', ec='#555', lw=0.6))
sheets(ax, -L2, L2)
ax.plot([-L2, L2], [-150, -150], color=AIR, lw=1.6)
ax.text(0, 72, '通気垂木（勾配の向きに通る。垂木と垂木のあいだが通気層）', fontsize=6.5, ha='center', va='center')
for k in range(-2, 3):
    x = k * 455
    ax.add_patch(Rectangle((x - 30, -324), 60, 150, fc=WOOD, ec='#6b5530', lw=0.8))
    if k < 2:
        ax.annotate('', xy=(x + 455, -360), xytext=(x, -360), arrowprops=dict(arrowstyle='<->', lw=0.5))
        ax.text(x + 227, -370, '455', fontsize=6.5, ha='center', va='top')
ax.plot([-L2, L2], [0, 0], color='#a33', lw=0.8, ls=(0, (6, 3)))
ax.text(L2 - 10, 8, '奥の梁の上端（0）', fontsize=6.5, ha='right', va='bottom', color='#a33')
ax.plot([-L2, L2], [-520, -520], color='#a33', lw=0.5, ls=(0, (6, 3)))
ax.text(L2 - 10, -515, '奥の梁（せい400〜500、下端の高さは場所で変わる）', fontsize=6.5, ha='right', va='bottom', color='#a33')
for x1 in (-L2, L2):
    ax.plot([x1, x1], [-340, 175], color='#333', lw=0.8, ls=(0, (4, 2)))
ax.text(0, -420, '母屋の断面60×150（梁に直角に渡る）', fontsize=6.5, ha='center', va='top')
dims(ax, -L2 - 160)
labels(ax, L2 + 40)
ax.text(-L2 - 520, 260, '断面B：梁に平行に切る（勾配の向き、梁と梁のあいだ。勾配は省いた）', fontsize=10, fontweight='bold')
ax.set_xlim(-L2 - 560, L2 + 1150); ax.set_ylim(-560, 300)

fig.text(0.5, 0.965, '屋根の一般部の層（2026-11-16 版2）　高さは梁の上端を0（mm）', fontsize=12, ha='center', fontweight='bold')
fig.text(0.5, 0.02, '育ち舎の屋根の構成に、梁の上まで断熱を連続させる約50（11-16）を足した。屋根の上面は梁の上端＋159（育ち舎は＋109）。\n'
         '通気垂木60×45@455・野地t24・気密シート・透湿防水シートは育ち舎の構成から。母屋の上面は梁の上端より174下（断熱の上面が梁の上端とツラ）。',
         fontsize=7, ha='center', color='#444')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yane_1116')
fig.savefig(out + '.pdf')
fig.savefig('/tmp/yane_1116.png', dpi=110)
print('wrote', out + '.pdf')
