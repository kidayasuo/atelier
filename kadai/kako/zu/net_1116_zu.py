# -*- coding: utf-8 -*-
"""図：摺鉢ネットを動かす案（平面、2026-11-16 版1）。

座標は（u, 東から）。u は架構の番号の向き（南→北、架構kは u=3(k−1)）、
「東から」は東の壁の内面（v−1.05）から西へ測った距離（m）。
放射の曲率（半径約205 m）は省いて、架構の線を平行に描く（3 m の間隔が内の柱の列で約3.05 mになる程度の差）。
西の柱の位置は前課題の値（東の柱の芯からのスパン、概略）。k15 だけ今の略算の値（13.48）。
ネット・輪の通路・踊り場・ついたて・キャットウォークの寸法は sodachiya/kettei/yugishitsu.md から。
"""
import os
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'sodachiya', 'scripts'))
import fonts42  # noqa: F401,E402

E_COL, IN_COL = 0.15, 2.35            # 東の柱・内の柱の芯（東から）
COL = 0.30
FRAMES = {13: 12.50, 14: 12.95, 15: 13.48, 16: 11.17, 17: 7.98}   # k: 東の柱の芯→西の柱の芯（m）
OLD = (41.8, 3.25)                     # 前課題の中心（14+2.8、東から3.25）
NEW = (43.5, 4.35)                     # 案：スパン15の真ん中、東から4.35
R_RIM, R_OUT = 2.1, 2.9                # ネットの上の縁 φ4.2・輪の通路の外 φ5.8
ODORIBA = (49.5, 6.4, 0.95)            # 北西の踊り場（17+1.5、東から6.4、φ1.9）


def P(u, e):
    """（u, 東から）→図の座標（右が東、上が北）"""
    return (-e, u)


fig, ax = plt.subplots(figsize=(8.3, 11.7))
ax.set_aspect('equal')
ax.axis('off')

# 東の壁の内面とキャットウォーク
ax.plot(*zip(P(34.5, 0), P(51.3, 0)), color='#333', lw=1.4)
ax.text(*P(51.6, -0.1), '東の壁の内面（本館の側）', fontsize=7, ha='right', va='bottom')
x, y = P(36, 0.9)
ax.add_patch(Rectangle((x, y), 0.9, 51 - 36, fc='#e8dcc4', ec='#9a8a6a', lw=0.6))
ax.text(*P(37.0, 0.45), 'キャットウォーク\nh3.0・幅0.9', fontsize=6, ha='center', va='bottom', rotation=90, color='#5a4a2a')

# 架構の線・立ち上がりの帯・柱
for k, span in FRAMES.items():
    u = 3 * (k - 1)
    w = E_COL + span
    x0, y0 = P(u, w)
    ax.add_patch(Rectangle((x0, u - 0.2), w, 0.4, fc='#eeeeee', ec='none'))
    ax.plot(*zip(P(u, 0), P(u, w + 0.15)), color='#999', lw=0.5, ls=(0, (6, 3)))
    ax.text(*P(u + 0.25, w + 0.4), 'k%d' % k, fontsize=8, ha='right', va='bottom', fontweight='bold')
    for e in (E_COL, IN_COL, w):
        cx, cy = P(u, e)
        ax.add_patch(Rectangle((cx - COL / 2, cy - COL / 2), COL, COL, fc='#555', ec='none', zorder=5))
ax.text(*P(36.3, 5.5), '立ち上がりの帯（幅400、灰）', fontsize=6, color='#777')
ax.text(*P(35.4, IN_COL), '内の柱の列\n（東から2.35）', fontsize=6, ha='center', va='top')

# 北の口のついたて（u45.1〜48.1、東から1.5、南の端で東の壁へ）
ax.plot(*zip(P(45.1, 0), P(45.1, 1.5), P(48.1, 1.5)), color='#8a5a2a', lw=1.6)
ax.text(*P(47.3, 1.65), 'ついたて h2.4', fontsize=6, ha='right', va='center', color='#8a5a2a')

# 踊り場
cx, cy = P(ODORIBA[0], ODORIBA[1])
ax.add_patch(Circle((cx, cy), ODORIBA[2], fc='#e8dcc4', ec='#9a8a6a', lw=0.6))
ax.text(cx, cy, '踊り場\nh2.0', fontsize=6, ha='center', va='center', color='#5a4a2a')


def net(c, color, ls, lw, alpha):
    cx, cy = P(*c)
    ax.add_patch(Circle((cx, cy), R_OUT, fc='none', ec=color, ls=ls, lw=lw, alpha=alpha))
    ax.add_patch(Circle((cx, cy), R_RIM, fc='none', ec=color, ls=ls, lw=lw, alpha=alpha))
    ax.add_patch(Circle((cx, cy), 0.3, fc='none', ec=color, ls=ls, lw=lw * 0.8, alpha=alpha))
    ax.plot(cx, cy, '+', color=color, ms=7, alpha=alpha)


# 前課題の位置（破線）
net(OLD, '#c0392b', (0, (4, 2)), 1.0, 0.8)
ax.text(*P(38.0, 4.6), '前の位置（14+2.8、東から3.25）\n内の柱k15がネットの中に立つ', fontsize=6.5,
        color='#c0392b', ha='center')
cx, cy = P(42, IN_COL)
ax.add_patch(Circle((cx, cy), 0.35, fc='none', ec='#c0392b', lw=1.4, zorder=6))

# 案の位置（実線）
net(NEW, '#1f5fa8', '-', 1.6, 1.0)
ax.text(*P(NEW[0] - 0.55, NEW[1]), '案：スパン15の真ん中\n東から4.35', fontsize=7, color='#1f5fa8',
        ha='center', va='top', fontweight='bold')
# 柱が通路に立つ・西の2点
for u in (42, 45):
    cx, cy = P(u, IN_COL)
    ax.add_patch(Circle((cx, cy), 0.32, fc='none', ec='#1f5fa8', lw=1.2, zorder=6))
    cx, cy = P(u, 6.35)
    ax.plot(cx, cy, 'D', mfc='white', mec='#1f5fa8', ms=7, mew=1.4, zorder=7)
ax.text(*P(44.0, 7.0), '西の2点（東から6.35）\nA 梁から吊る／B 床から細い柱', fontsize=6.5, color='#1f5fa8',
        ha='right', va='center')
ax.text(*P(41.4, IN_COL + 0.4), '内の柱が\n輪の通路に立つ', fontsize=6.5, color='#1f5fa8', ha='left', va='top')

# 短い橋（キャットウォーク→通路）と吊り橋（通路→踊り場）
ax.plot(*zip(P(NEW[0], 0.9), P(NEW[0], NEW[1] - R_OUT)), color='#1f5fa8', lw=3.5, solid_capstyle='butt', alpha=0.5)
ax.text(*P(NEW[0] + 0.15, 1.15), '短い橋 0.55', fontsize=6, color='#1f5fa8', va='bottom', ha='left')


def bridge(c, color, ls, lw):
    import math
    du, de = ODORIBA[0] - c[0], ODORIBA[1] - c[1]
    d = math.hypot(du, de)
    a = (c[0] + du / d * R_OUT, c[1] + de / d * R_OUT)
    b = (ODORIBA[0] - du / d * ODORIBA[2], ODORIBA[1] - de / d * ODORIBA[2])
    ax.plot(*zip(P(*a), P(*b)), color=color, ls=ls, lw=lw)
    return math.hypot(b[0] - a[0], b[1] - a[1])


Lo = bridge(OLD, '#c0392b', (0, (4, 2)), 1.0)
Ln = bridge(NEW, '#1f5fa8', '-', 2.2)
ax.text(*P(47.4, 7.3), '吊り橋 約%.1f m\n（前は約%.1f m）' % (Ln, Lo), fontsize=6.5, color='#1f5fa8', ha='right', va='center')

# 方位・凡例・題
ax.annotate('', xy=P(52.6, 13.0), xytext=P(51.4, 13.0), arrowprops=dict(arrowstyle='->', lw=1))
ax.text(*P(52.8, 13.0), '北', fontsize=8, ha='center', va='bottom')
ax.text(*P(52.9, 6.5), '摺鉢ネットを動かす案（平面、2026-11-16 版1）', fontsize=11, ha='center', va='bottom', fontweight='bold')
ax.text(*P(33.6, 7.0),
        '円は外から：輪の通路の外φ5.8・ネットの上の縁φ4.2（通路の内）・下の口φ0.6。赤の破線は前の位置、青は案。\n'
        '■は柱300角（東の柱・内の柱・西の柱）。西の柱の位置は前課題の値（概略）。放射の曲率は省いて架構の線を平行に描いた。',
        fontsize=6, ha='center', va='top', color='#444')
ax.set_xlim(-15.2, 0.9)
ax.set_ylim(32.6, 53.6)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'net_1116')
fig.savefig(out + '.pdf', bbox_inches='tight')
fig.savefig('/tmp/net_1116.png', dpi=110, bbox_inches='tight')
print('wrote', out + '.pdf')
