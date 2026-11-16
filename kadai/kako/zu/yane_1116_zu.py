# -*- coding: utf-8 -*-
"""図：屋根の一般部の層（断面、2026-11-16 版4）。

高さは梁の上端を0とする（mm）。育ち舎の「屋根の構成」（sodachiya/kettei/nishikan.md、kyoutsu.md）に、
11-16の決定（梁の上まで断熱を連続、約50）を足した。
  母屋 杉60×150@455 −150〜0（11-16：断熱の層の中へ上げ、天井の中に隠す。梁と梁のあいだに渡す、両端は梁の側面の金物）
  合板 t24 −174〜−150（11-16：母屋の下に張って天井にする、4周釘打ち。気密シートはその上）
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
    ('母屋60×150@455と断熱150', -150, 0, '#f7ec9f'),
    ('構造用合板 t24（母屋の下、天井）', -174, -150, '#d9b77e'),
]
WOOD, BEAM = '#e6cfa0', '#d8b87f'
AIR, WRB, RFG = '#d0392b', '#1f7a3a', '#1f3f8a'   # 気密シート・透湿防水シート・ルーフィング


def sheets(ax, a, b):
    ax.plot([a, b], [50, 50], color=WRB, lw=1.6, zorder=5)     # 透湿防水シート（連続の断熱の上）
    ax.plot([a, b], [119, 119], color=RFG, lw=1.6, zorder=5)   # ルーフィング（野地の上）

fig = plt.figure(figsize=(11.7, 10.5))


def dims(ax, x):
    for name, lo, hi, _ in LAY:
        ax.plot([x - 15, x + 15], [hi, hi], color='#333', lw=0.6)
        ax.text(x - 25, hi, '%+d' % hi if hi else '0', fontsize=6.5, ha='right', va='center')
    ax.plot([x - 15, x + 15], [-174, -174], color='#333', lw=0.6)
    ax.text(x - 25, -174, '−174', fontsize=6.5, ha='right', va='center')
    ax.plot([x, x], [-174, 159], color='#333', lw=0.6)
    ax.text(x - 70, -8, '（梁の上端）', fontsize=6.5, ha='right', va='top', color='#a33')


def labels(ax, x):
    for name, lo, hi, _ in LAY:
        ax.text(x, (lo + hi) / 2, name, fontsize=7, va='center')
    for y, name, c in ((119, 'ルーフィング', RFG), (50, '透湿防水シート', WRB), (-150, '気密シート\n（梁の側面で立ち上げ）', AIR)):
        ax.text(x + 600, y, '─ ' + name, fontsize=6.5, va='center', color=c)


# ---- 断面A：梁に直角（母屋の向き）
ax = fig.add_axes([0.03, 0.70, 0.94, 0.24])
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
    ax.add_patch(Rectangle((lo_, -174), hi_ - lo_, 24, fc='#d9b77e', ec='#6b5530', lw=0.6))
    ax.add_patch(Rectangle((lo_, -150), hi_ - lo_, 150, fc=WOOD, ec='#6b5530', lw=0.6))
    ax.text((lo_ + hi_) / 2, -75, '母屋（奥に見える側面。母屋のあいだは断熱150）', fontsize=6.5, ha='center', va='center')
    # 金物（母屋の端、梁の側面）
    gx = x0 - 6 if side < 0 else x0
    ax.add_patch(Rectangle((gx, -156), 6, 160, fc='#555', ec='none', zorder=4))
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
ax.annotate('母屋の端の金物（梁の側面）', xy=(bl[0] - 3, -100), xytext=(-1180, -470), fontsize=6.5,
            arrowprops=dict(arrowstyle='-', lw=0.5))
ax.text(bl[0] + T / 2, BOT + 30, '梁160', fontsize=6.5, ha='center', rotation=90, zorder=6)
ax.text(br[0] + T / 2, BOT + 30, '梁160', fontsize=6.5, ha='center', rotation=90, zorder=6)
ax.text(-700, -230, '天井は合板の下面（−174）。梁は天井から下に見え、母屋は天井の中に隠れる', fontsize=6.5, ha='center', va='top')
dims(ax, -L - 160)
labels(ax, L + 40)
ax.text(-L - 520, 260, '断面A：梁に直角に切る（母屋の向き、架構kの対の梁のところ）', fontsize=10, fontweight='bold')
ax.set_xlim(-L - 560, L + 1150); ax.set_ylim(BOT - 40, 300)

# ---- 断面B：梁に平行（勾配の向き、梁と梁のあいだ）。東の端（棟）から、ガラスの帯・排気のスリット・一般部まで
# x は東の壁の内面から西へ（mm、左が東）。帯 v−0.9〜−2.56 → x −150〜1510、スリット 1510〜1660、一般部 1660〜
ax = fig.add_axes([0.02, 0.05, 0.96, 0.60])
ax.set_aspect('equal'); ax.axis('off')
XE, XW = -560, 2500
XS0, XS1 = 1510, 1660            # スリット
XP = XS1                         # 鋼板の帯の西の面に合板が付く
# 奥の梁と、梁の上の受け（架構の線）
ax.plot([0, XW], [0, 0], color='#a33', lw=0.8, ls=(0, (6, 3)))
ax.plot([0, XW], [-520, -520], color='#a33', lw=0.5, ls=(0, (6, 3)))
ax.text(XW - 10, -515, '奥の梁（せい400〜500）', fontsize=6.5, ha='right', va='bottom', color='#a33')
ax.add_patch(Rectangle((0, 0), XS0 - 60, 95, fc='none', ec='#a33', lw=0.6, ls=(0, (3, 2))))
ax.text(720, 47, '奥：梁の上の受け（架構の線ごと）', fontsize=6.5, ha='center', va='center', color='#a33')
# 東の壁と縁の材
ax.add_patch(Rectangle((-150, -540), 150, 540 + 35, fc='#efe6d2', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((-150, 35), 150, 60, fc=WOOD, ec='#6b5530', lw=0.6))
ax.text(-75, -300, '東の壁', fontsize=6.5, ha='center', va='center', rotation=90)
# 東の桁（楕円、柱の頭をつなぐ。高さは仮）
from matplotlib.patches import Ellipse
ax.add_patch(Ellipse((150, -250), 180, 260, fc=BEAM, ec='#6b5530', lw=0.8, ls=(0, (3, 2))))
ax.text(150, -250, '東の桁\n（奥・柱の頭）', fontsize=6, ha='center', va='center')
# ガラスの帯（複層、屋根の面と一つの面）。東へ350伸ばして軒
ax.add_patch(Rectangle((XE + 60, 95), XS0 - XE - 60, 64, fc='#d6eef8', ec='#4a90b8', lw=0.8))
ax.plot([XE + 60, XS0], [127, 127], color='#4a90b8', lw=0.5)
ax.text(450, 190, 'ガラスの帯 幅1.6 m（複層、屋根の上面と一つの面）\n4辺で受ける：南北の縁＝奥の梁の上の受け、東＝壁の縁の材、西＝立ち上がり',
        fontsize=6.5, ha='center', va='bottom', color='#2a6a90')
ax.text(XE + 60, 60, '軒（すき間の上、350）', fontsize=6, ha='left', va='center', color='#2a6a90')
# スリットの東の立ち上がり（ガラスの西の縁、細く断熱）
ax.add_patch(Rectangle((XS0 - 60, -150), 60, 245, fc=WOOD, ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((XS0 - 6, -150), 6, 309, fc='#777', ec='none'))
# 排気の窓（断熱の線）
ax.add_patch(Rectangle((XS0, -150), XS1 - XS0, 30, fc='#bfe3f2', ec='#4a90b8', lw=0.8))
# 鋼板の帯（室内側、南北に通る）と腕
ax.add_patch(Rectangle((XP, -380), 12, 230, fc='#444', ec='none', zorder=5))
ax.add_patch(Rectangle((XS0 - 70, -172), XP - XS0 + 82, 10, fc='#444', ec='none', alpha=0.6))
# 雨受けの樋と防虫網
ax.add_patch(Rectangle((XS0 + 30, -40), XS1 - XS0 - 60, 30, fc='none', ec='#555', lw=0.8))
ax.plot([XS0, XS1], [144, 144], color='#555', lw=0.8, ls=(0, (1, 1.5)))
# 排気の流れ
ax.annotate('', xy=((XS0 + XS1) / 2, 230), xytext=((XS0 + XS1) / 2, -330),
            arrowprops=dict(arrowstyle='->', lw=1.2, color='#c0392b', alpha=0.7))
# 一般部（スリットの西）
X0 = XP + 12
ax.add_patch(Rectangle((X0, -174), XW - X0, 24, fc='#d9b77e', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((X0, -150), XW - X0, 150, fc='#f7ec9f', ec='#b8a640', lw=0.6))
for k in range(5):
    x = X0 + 300 + k * 455
    if x + 60 < XW:
        ax.add_patch(Rectangle((x, -150), 60, 150, fc=WOOD, ec='#6b5530', lw=0.8))
ax.add_patch(Rectangle((X0, 0), XW - X0, 50, fc='#f3e27a', ec='#b8a640', lw=0.6))
ax.add_patch(Rectangle((X0, 50), XW - X0, 45, fc=WOOD, ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((X0, 95), XW - X0, 24, fc='#c9a86a', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((X0, 119), XW - X0, 40, fc='#8c8c8c', ec='#555', lw=0.6))
sheets(ax, X0, XW)
ax.plot([X0, XW], [-150, -150], color=AIR, lw=1.6)
ax.plot([X0, X0], [-150, -120], color=AIR, lw=1.6)
# 板金（スリットの西の切り口、窓の上から屋根の上面まで）
ax.plot([X0 + 3, X0 + 3], [-120, 162], color='#555', lw=1.4)
ax.annotate('', xy=(X0 - 40, 72), xytext=(X0 + 220, 72), arrowprops=dict(arrowstyle='->', lw=0.8, color='#c0392b', alpha=0.7))
for x1 in (XE, XW):
    ax.plot([x1, x1], [-340, 175], color='#333', lw=0.8, ls=(0, (4, 2)))
# 引き出しの文字（下の余白に）
def note(xy, xt, text):
    ax.annotate(text, xy=xy, xytext=xt, fontsize=6.5, arrowprops=dict(arrowstyle='-', lw=0.5))
note((XS0 - 30, -60), (300, -600), '① ガラスの西の縁の立ち上がり（細く、断熱。足元は③の腕で受ける）')
note((XP + 6, -330), (1750, -460), '② 鋼板の帯（南北に通る、窓より下＝室内側）\n　弦・窓の機構・腕・天井扇の吊り')
note((XS0 - 30, -167), (300, -680), '③ 腕（1 m前後おき、窓より下）')
note((XS0 + 75, -135), (1750, -620), '④ 閉じられる排気の窓（断熱・気密、自動）＝断熱の線')
note((XS0 + 75, -25), (1750, -720), '⑤ 雨受けの樋')
note((XS0 + 75, 144), (1150, 330), '⑥ 防虫網（屋根の上面の15下）')
note((X0 + 3, 100), (1900, 270), '⑦ 板金で切り口を包む／通気層の出口（棟換気）')
ax.text(XE, 360, '東（棟）', fontsize=8, ha='left')
ax.text(XW, 360, '西（軒へ）', fontsize=8, ha='right')
dims(ax, XE - 160)
ax.text(XE, -700, '層の名前は断面Aと同じ', fontsize=6.5, ha='left', va='top', color='#666')
ax.text(XE - 520, 440, '断面B：梁に平行に切る（勾配の向き、梁と梁のあいだ。棟の帯・スリットから一般部へ。勾配は省いた）', fontsize=10, fontweight='bold')
ax.set_xlim(XE - 560, XW + 150); ax.set_ylim(-760, 480)

fig.text(0.5, 0.965, '屋根の一般部の層（2026-11-16 版4）　高さは梁の上端を0（mm）', fontsize=12, ha='center', fontweight='bold')
fig.text(0.5, 0.012, '育ち舎の屋根の構成に、梁の上まで断熱を連続させる約50（11-16）を足した。屋根の上面は梁の上端＋159（育ち舎は＋109）。\n'
         '版3・4（11-16）：断面Bに棟の帯とスリットを足した。母屋を断熱の層の中へ上げ（上面が梁の上端とツラ）、合板をその下に張って天井にした。天井の高さと梁の見えは変わらない。気密シートは合板の上。',
         fontsize=7, ha='center', color='#444')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yane_1116')
fig.savefig(out + '.pdf')
fig.savefig('/tmp/yane_1116.png', dpi=110)
print('wrote', out + '.pdf')
