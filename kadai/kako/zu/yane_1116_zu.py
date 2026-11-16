# -*- coding: utf-8 -*-
"""図：屋根の一般部の層（断面、2026-11-16 版5）。

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

# ---- 断面B：梁に平行（勾配の向き、梁と梁のあいだ）。棟の帯・スリット（冬に閉じた状態）から一般部まで
# x は東の壁の内面から西へ（mm、左が東）。帯 v−0.9〜−2.56 → x −150〜1510、スリット 1510〜1660、一般部 1660〜
# 11-16 版5：帯のガラスと排気の窓を連続の断熱の上面（＋50）にそろえ、断熱の線を一枚の平らな面にする
from matplotlib.patches import Ellipse
ax = fig.add_axes([0.02, 0.05, 0.96, 0.60])
ax.set_aspect('equal'); ax.axis('off')
XE, XW = -560, 2500
XS0, XS1 = 1510, 1660            # スリット
TH = '#7b3fa0'                   # 断熱の線
G0, G1 = 22, 50                  # 帯のガラスと窓（複層）の下と上
# 奥の梁と、梁の上の受け
ax.plot([0, XW], [0, 0], color='#a33', lw=0.8, ls=(0, (6, 3)))
ax.plot([0, XW], [-520, -520], color='#a33', lw=0.5, ls=(0, (6, 3)))
ax.text(XW - 10, -515, '奥の梁（せい400〜500）', fontsize=6.5, ha='right', va='bottom', color='#a33')
ax.add_patch(Rectangle((0, 0), XS0, G0, fc='none', ec='#a33', lw=0.6, ls=(0, (3, 2))))
ax.text(720, -40, '奥：梁の上の受け（架構の線ごと、高さ22）。帯の下は室内', fontsize=6.5, ha='center', va='center', color='#a33')
# 東の壁（断熱）と縁の材
ax.add_patch(Rectangle((-150, -540), 150, 540 + G0, fc='#efe6d2', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((-110, -540), 80, 540 + G0, fc='#f7ec9f', ec='none'))
ax.text(-190, -300, '東の壁（断熱）', fontsize=6.5, ha='center', va='center', rotation=90)
ax.add_patch(Ellipse((150, -250), 180, 260, fc=BEAM, ec='#6b5530', lw=0.8, ls=(0, (3, 2))))
ax.text(150, -250, '東の桁\n（奥・柱の頭）', fontsize=6, ha='center', va='center')
# 帯のガラス（＋22〜＋50、複層）。東へ350伸ばして軒
ax.add_patch(Rectangle((XE + 60, G0), XS0 - XE - 60, G1 - G0, fc='#d6eef8', ec='#4a90b8', lw=0.8))
ax.plot([XE + 60, XS0], [(G0 + G1) / 2, (G0 + G1) / 2], color='#4a90b8', lw=0.4)
# ルーバー（屋根の上面の高さまで、外）
for x in range(int(XE + 90), XS0, 70):
    ax.plot([x, x + 40], [100, 155], color='#777', lw=1.2)
ax.plot([XE + 60, XS0], [159, 159], color='#777', lw=0.5, ls=(0, (2, 2)))
ax.text(450, 175, 'ルーバー（日よけ、外。上の面は屋根の上面にそろう）', fontsize=6.5, ha='center', va='bottom', color='#555')
ax.text(450, 215, 'ガラスの帯 幅1.6 m（複層、＋22〜＋50）。4辺で受ける', fontsize=6.5, ha='center', va='bottom', color='#2a6a90')
ax.text(XE + 60, -30, '軒（すき間の上、350）', fontsize=6, ha='left', va='center', color='#2a6a90')
# 排気の窓（閉じた状態、＋22〜＋50）
ax.add_patch(Rectangle((XS0, G0), XS1 - XS0, G1 - G0, fc='#bfe3f2', ec='#4a90b8', lw=1.0))
# 鋼板の帯（室内側）・腕・熱を切る受け
ax.add_patch(Rectangle((XS1, -380), 12, 380 + 10, fc='#444', ec='none', zorder=5))
ax.add_patch(Rectangle((XS0 - 80, 0), XS1 - XS0 + 92, 10, fc='#444', ec='none', alpha=0.6, zorder=5))
ax.add_patch(Rectangle((XS0 - 80, 10), XS1 - XS0 + 92, G0 - 10, fc='#e9a3c9', ec='none', zorder=5))
# 雨受けの樋（窓の上、外）と防虫網
ax.add_patch(Rectangle((XS0 + 30, 60), XS1 - XS0 - 60, 30, fc='none', ec='#555', lw=0.8))
ax.plot([XS0, XS1], [144, 144], color='#555', lw=0.8, ls=(0, (1, 1.5)))
# 一般部（スリットの西）
X0 = XS1 + 12
ax.add_patch(Rectangle((X0, -174), XW - X0, 24, fc='#d9b77e', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((X0, -150), XW - X0, 150, fc='#f7ec9f', ec='#b8a640', lw=0.6))
for k in range(4):
    x = X0 + 300 + k * 455
    if x + 60 < XW:
        ax.add_patch(Rectangle((x, -150), 60, 150, fc=WOOD, ec='#6b5530', lw=0.8))
ax.add_patch(Rectangle((X0, 0), XW - X0, 50, fc='#f3e27a', ec='#b8a640', lw=0.6))
ax.add_patch(Rectangle((X0, 50), XW - X0, 45, fc=WOOD, ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((X0, 95), XW - X0, 24, fc='#c9a86a', ec='#6b5530', lw=0.6))
ax.add_patch(Rectangle((X0, 119), XW - X0, 40, fc='#8c8c8c', ec='#555', lw=0.6))
sheets(ax, X0, XW)
# 気密：合板の上（−150）から、断熱の縁に沿って窓の枠まで立ち上げる
ax.plot([X0, XW], [-150, -150], color=AIR, lw=1.6)
ax.plot([X0 + 2, X0 + 2], [-150, G1], color=AIR, lw=1.6)
# 板金（窓より上の切り口、外）と通気層の出口
ax.plot([X0 + 4, X0 + 4], [G1, 162], color='#555', lw=1.4)
ax.annotate('', xy=(X0 - 40, 72), xytext=(X0 + 220, 72), arrowprops=dict(arrowstyle='->', lw=0.8, color='#c0392b', alpha=0.7))
# 断熱の線（冬に閉じた状態）：東の壁→帯のガラス→窓→屋根の断熱の上面（一枚の平らな面）
ax.plot([-70, -70, XS1 + 12, XW], [-540, G1, G1, G1], color=TH, lw=2.0, ls=(0, (5, 2)), zorder=6)
ax.text(XS0 - 100, -150, '断熱の線（閉じた状態）：外側の面が＋50で一枚につながる', fontsize=7, ha='right', va='center', color=TH)
for x1 in (XE, XW):
    ax.plot([x1, x1], [-340, 175], color='#333', lw=0.8, ls=(0, (4, 2)))
def note(xy, xt, text):
    ax.annotate(text, xy=xy, xytext=xt, fontsize=6.5, arrowprops=dict(arrowstyle='-', lw=0.5))
note((XS0 + 75, 36), (300, -600), '① 閉じられる排気の窓（冬は閉じる。断熱・気密、熱を切った枠、自動）')
note((XS1 + 6, -300), (1750, -460), '② 鋼板の帯（南北に通る、断熱の線より下＝室内側）\n　弦・窓とガラスの西の縁の受け・天井扇の吊り')
note((XS0 - 40, 5), (300, -660), '③ 腕（1 m前後おき、室内側）')
note((XS0 - 40, 16), (300, -720), '④ 熱を切る受け（樹脂・木。断熱の線をまたぐのはここと枠の留め付けだけ）')
note((XS0 + 75, 75), (1750, -620), '⑤ 雨受けの樋（窓の上、外）')
note((XS0 + 75, 144), (1150, 330), '⑥ 防虫網（屋根の上面の15下）')
note((X0 + 4, 120), (1900, 270), '⑦ 板金で切り口を包む（外）／通気層の出口（棟換気）')
note((X0 + 2, -60), (1750, -720), '⑧ 気密シートを断熱の縁に沿って窓の枠まで立ち上げる')
ax.text(XE, 360, '東（棟）', fontsize=8, ha='left')
ax.text(XW, 360, '西（軒へ）', fontsize=8, ha='right')
ax.text(XE, -700, '層の名前は断面Aと同じ', fontsize=6.5, ha='left', va='top', color='#666')
dims(ax, XE - 160)
ax.text(XE - 520, 440, '断面B：梁に平行に切る（冬に排気の窓を閉じた状態。棟の帯・スリットから一般部へ。勾配は省いた）', fontsize=10, fontweight='bold')
ax.set_xlim(XE - 560, XW + 150); ax.set_ylim(-760, 480)

fig.text(0.5, 0.965, '屋根の一般部の層（2026-11-16 版5）　高さは梁の上端を0（mm）', fontsize=12, ha='center', fontweight='bold')
fig.text(0.5, 0.012, '育ち舎の屋根の構成に、梁の上まで断熱を連続させる約50（11-16）を足した。屋根の上面は梁の上端＋159（育ち舎は＋109）。\n'
         '版5（11-16）：帯のガラスと排気の窓を連続の断熱の上面（＋50）にそろえ、断熱の線を一枚の面にした（断面Bは冬に閉じた状態）。母屋を断熱の層の中へ上げ（上面が梁の上端とツラ）、合板をその下に張って天井にした。天井の高さと梁の見えは変わらない。気密シートは合板の上。',
         fontsize=7, ha='center', color='#444')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yane_1116')
fig.savefig(out + '.pdf')
fig.savefig('/tmp/yane_1116.png', dpi=110)
print('wrote', out + '.pdf')
