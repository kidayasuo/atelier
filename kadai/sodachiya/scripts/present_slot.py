"""光の筋と架構 1/20（本館係、10-28）。提出のA1の5枚目「断面と環境」の下の段の素材。
屋根の光の筋（2枚組の登り梁のあいだ180の溝）を、梁に直角に切った詳細断面（保育室の中ほど、v 約6 m、西を見る＝左が南）。
寸法は決定事項（本館「本館の骨格」「屋根の構成」「屋根：光の筋と太陽光」、共通「屋根の構成」）と
model/build/south/fix_details.py の本館の節（RT_BOT −150・RT_TOP −41・INS_BOT・PLY_BOT・PUR_BOT、10・10b・10r・10v・10m・10k・10t）。
梁のせい 600・下端 FL+2,900（v 6）は 3dm の 11b から測った値。
出力：out/sodachiya_present_slot.pdf（200×222 mm、図は実寸 1/20）・.png（確かめ用）
"""
import os, sys, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fonts42  # noqa: F401  Noto Sans CJK JP を Type42 で
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from matplotlib.font_manager import FontProperties

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
_TTF = os.path.expanduser("~/.cache/sodachiya_fonts")
FB = FontProperties(fname=os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")) if os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")) else FontProperties(family="Noto Sans CJK JP", weight="bold")

W, H = 200.0, 222.0                       # 紙（mm）
MM = 1 / 25.4
fig = plt.figure(figsize=(W * MM, H * MM))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
plt.rcParams["hatch.linewidth"] = 0.25

INK = "#222222"
S = 1 / 20.0                              # 1/20：実寸 mm → 紙 mm
FLY = 6.0                                # 紙の上の FL の高さ
BT = 3500.0                               # 梁の上端の FL からの高さ（v 6：ROOF_Z 3650 − 150）
X0 = 100.0                                # 光の筋の中心（u = 0）
def P(u, z):                              # u：筋の中心から北へ（mm）、z：梁の上端から（mm）
    return (X0 + u * S, FLY + (BT + z) * S)

# ---- 寸法（mm、z は梁の上端から）
BW, GAP = 90.0, 180.0; G2 = GAP / 2       # 2 枚の梁 90、あいだ 180
BD = 600.0                                # 梁のせい（v 6）
Z_INS, Z_PLY, Z_PUR = -150.0, -174.0, -324.0     # 断熱・合板・母屋の下
Z_VB, Z_SH, Z_RF = 45.0, 69.0, 109.0     # 通気垂木の上・野地の上・屋根の上面（梁の上 109）
UPW = 60.0                                # 立ち上がりの幅（|u| 90〜150）
Z_UP = Z_RF + 60.0                        # 立ち上がりの上面＝ガラスの下（169）
Z_FR = Z_UP - 24.0                        # 枠の下（断熱の立ち上がりの上端）
GL_IN, GL_AIR, GL_OUT = 8.0, 12.0, 6.0    # 型板の合わせ 4+4（10-30：乳白→型板）／アルゴン 12／遮熱 Low-E 6
Z_GT = Z_UP + GL_IN + GL_AIR + GL_OUT     # ガラスの上（195）
UL = 1880.0                               # 描く範囲（両端は破断）
RAF_N = [300.0 + 455.0 * i for i in range(4)]            # 通気垂木（fix_details：架構の線から 0.30 + 0.455 i）
RAF_S = [-(3000.0 - (300.0 + 455.0 * i)) for i in range(5, 1, -1)]   # 南のスパンの垂木（−425・−880…）

LW_CUT, LW_SEE, LW_THIN = 0.55, 0.25, 0.18

def poly(pts, fc="none", ec=INK, lw=LW_CUT, z=3, hatch=None, hc=None, ls="-"):
    kw = dict(closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, joinstyle="miter")
    if hatch: kw["hatch"] = hatch
    p = Polygon([P(*q) for q in pts], **kw)
    if hatch and hc is not None:
        try: p.set_hatchcolor(hc)
        except Exception: pass
    ax.add_patch(p); return p
def rect(u0, z0, u1, z1, **kw):
    return poly([(u0, z0), (u1, z0), (u1, z1), (u0, z1)], **kw)
def line(pts, lw=LW_SEE, c=INK, ls="-", z=4, paper=False):
    q = pts if paper else [P(*p) for p in pts]
    xs, ys = zip(*q); ax.plot(xs, ys, lw=lw, color=c, ls=ls, zorder=z, solid_capstyle="butt", dash_capstyle="butt")
def T(x, y, s, size=2.0, ha="left", va="baseline", c=INK, bold=False, z=9, **kw):
    pt = size / 0.3528 / 0.72
    if bold: kw["fontproperties"] = FontProperties(fname=FB.get_file(), size=pt) if hasattr(FB, "get_file") and FB.get_file() else FB
    ax.text(x, y, s, fontsize=pt, ha=ha, va=va, color=c, zorder=z, linespacing=1.25, **kw)

def wood(u0, z0, u1, z1, z=3, x=True):   # 木の断面：色＋たすき（構造材の表し方）
    rect(u0, z0, u1, z1, fc="#EBD8B2", z=z)
    if x:
        line([(u0, z0), (u1, z1)], lw=LW_THIN, z=z + 0.1); line([(u0, z1), (u1, z0)], lw=LW_THIN, z=z + 0.1)

# ================================================================ 屋根の層（両側、筋のまわりは立ち上がり）
for sg in (-1, 1):
    a, b = (G2 + BW, UL) if sg > 0 else (-UL, -(G2 + BW))
    # 合板 t24（天井に現し）
    rect(a, Z_PLY, b, Z_INS, fc="#DDBF8F", hatch="-----", hc="#A88555", lw=LW_CUT, z=3)
    # 断熱 t150 木質繊維ボード（梁のあいだ、上面＝梁の上端）
    rect(a, Z_INS, b, 0, fc="#F4EAD0", hatch="xx", hc="#C2A977", lw=LW_CUT, z=3)
    # 母屋 杉 60×150（見えがかり、梁の側面から次の梁まで）
    rect(a, Z_PUR, b, Z_PLY, fc="#F3E7D2", ec=INK, lw=LW_SEE, z=2)
    # 合板の受け材 45×45（梁の側面、断面）
    ua = G2 + BW
    wood(sg * ua if sg > 0 else -ua - 45, Z_PLY - 45, sg * ua + 45 if sg > 0 else -ua, Z_PLY, z=3.5)
    # 母屋受け金物（上下両向き、見えがかり）
    u_f = sg * ua
    rect(min(u_f, u_f + sg * 3), Z_PUR - 25, max(u_f, u_f + sg * 3), Z_PLY - 50, fc="#7A7F86", ec="#444", lw=LW_THIN, z=3.6)
    rect(min(u_f, u_f + sg * 70), Z_PUR - 4, max(u_f, u_f + sg * 70), Z_PUR, fc="#7A7F86", ec="#444", lw=LW_THIN, z=3.6)
    # 野地 t24・屋根材 40（筋の立ち上がりの外の面 |u| 150 まで）
    c0 = G2 + UPW
    a2, b2 = (c0, UL) if sg > 0 else (-UL, -c0)
    rect(a2, Z_VB, b2, Z_SH, fc="#DDBF8F", hatch="-----", hc="#A88555", lw=LW_CUT, z=3)
    # 屋根材：筋の周り ±250 は金属の屋根材、その外は屋根材型の太陽光
    pv0 = 250.0
    m_a, m_b = (c0, pv0) if sg > 0 else (-pv0, -c0)
    rect(m_a, Z_SH, m_b, Z_RF, fc="#9EA4AA", lw=LW_CUT, z=3)
    p_a, p_b = (pv0, UL) if sg > 0 else (-UL, -pv0)
    rect(p_a, Z_SH, p_b, Z_RF, fc="#2D333C", lw=LW_CUT, z=3)
    # 通気垂木 60×45（勾配の方向、断面）
    for uc in (RAF_N if sg > 0 else RAF_S):
        if abs(uc) + 30 < UL: wood(uc - 30, 0, uc + 30, Z_VB, z=3.5)
    # 筋の脇の垂木 60×45（自分で決めた：野地の端を受ける）
    e0 = c0
    wood(sg * e0 if sg > 0 else -e0 - 60, 0, sg * e0 + 60 if sg > 0 else -e0, Z_VB, z=3.5)
    # 立ち上がり：断熱を回す（木質繊維、|u| 90〜150、梁の上端から枠の下まで）
    u_in, u_out = sg * G2, sg * (G2 + UPW)
    rect(min(u_in, u_out), 0, max(u_in, u_out), Z_FR, fc="#F4EAD0", hatch="xx", hc="#C2A977", lw=LW_CUT, z=3.4)
    # 熱を切ったアルミの枠（立ち上がりの上）と押縁
    rect(min(u_in, u_out), Z_FR, max(u_in, u_out) + (sg * 12 if sg > 0 else 0) - (12 if sg < 0 else 0), Z_UP, fc="#A9B0B6", lw=0.35, z=4)
    line([(sg * (G2 + 25), Z_FR + 3), (sg * (G2 + 25), Z_UP - 3)], lw=0.5, c="#333", z=4.1)   # 断熱の切れ目（樹脂）
    cap_a, cap_b = sg * (G2 + UPW - 30), sg * (G2 + UPW + 12)
    rect(min(cap_a, cap_b), Z_GT, max(cap_a, cap_b), Z_GT + 9, fc="#A9B0B6", lw=0.35, z=4.2)
    rect(min(cap_b, cap_b - sg * 6), Z_FR, max(cap_b, cap_b - sg * 6), Z_GT, fc="#A9B0B6", lw=0.35, z=4.2)
    # 水切り板金（屋根材の上から立ち上がりの外の面を押縁の下まで）
    line([(sg * pv0, Z_RF + 2), (sg * (c0 + 14), Z_RF + 2), (sg * (c0 + 14), Z_GT - 4)], lw=0.7, c="#3B3B3B", z=4.3)
    # 透湿防水シート（断熱と梁の上に一面、立ち上がりの外の面を枠まで）：青の破線
    line([(sg * UL, 3), (sg * (G2 + UPW + 4), 3), (sg * (G2 + UPW + 4), Z_FR)], lw=0.5, c="#2F6FA8", ls=(0, (3, 1.5)), z=4.5)
    # 気密シート（合板の上、梁の側面で立ち上げ、梁の上端を渡り、立ち上がりの内側を枠まで）：赤の破線
    line([(sg * UL, Z_INS + 3), (sg * (G2 + BW + 3), Z_INS + 3), (sg * (G2 + BW + 3), -3),
          (sg * (G2 + 3), -3), (sg * (G2 + 3), Z_FR)], lw=0.5, c="#C0392B", ls=(0, (1.6, 1.2)), z=4.6)

# ================================================================ 登り梁（2 枚組、集成材 90×600）
for sg in (-1, 1):
    u0, u1 = (G2, G2 + BW) if sg > 0 else (-G2 - BW, -G2)
    rect(u0, -BD, u1, 0, fc="#EBD8B2", z=3.2)
    line([(u0, -BD), (u1, 0)], lw=LW_THIN, z=3.3); line([(u0, 0), (u1, -BD)], lw=LW_THIN, z=3.3)
    # 鏡面のアルミ t2（ガラスの下から梁の下端まで）
    rect(sg * (G2 - 2), -BD, sg * G2, Z_UP, fc="#8FA3B3", ec="#4F6475", lw=0.45, z=5)

# 鋼の平板 6×60（梁の上端に彫り込み、溝をまたぐ、見えがかり）
rect(-170, -6, 170, 0, fc="#1E1E1E", ec="#1E1E1E", lw=0.2, z=5.5)

# 複層ガラス（幅 300）：内 型板の合わせ・アルゴン・外 遮熱 Low-E
gw = 150.0
rect(-gw, Z_UP, gw, Z_UP + GL_IN, fc="#E8EEF1", lw=0.3, z=4.15)
rect(-gw, Z_UP + GL_IN, gw, Z_UP + GL_IN + GL_AIR, fc="white", lw=0.0, ec="none", z=4.1)
rect(-gw, Z_UP + GL_IN + GL_AIR, gw, Z_GT, fc="#BFDDEC", lw=0.3, z=4.15)
line([(-gw, Z_UP + GL_IN + GL_AIR / 2), (gw, Z_UP + GL_IN + GL_AIR / 2)], lw=0.1, c="#7D9AAA", ls=(0, (1, 1)), z=4.12)

# 破断線（屋根の層の両端）
for sg in (-1, 1):
    x = P(sg * UL, 0)[0]
    y0, y1 = P(0, Z_PUR - 40)[1], P(0, Z_RF + 40)[1]
    ym = 0.5 * (y0 + y1)
    ax.plot([x, x, x - 1.2 * sg, x + 1.2 * sg, x, x], [y0, ym + 1.5, ym + 0.7, ym - 0.7, ym - 1.5, y1], lw=LW_THIN, color=INK, zorder=6)
    ax.add_patch(Rectangle((x if sg > 0 else 0, y0), (W - x) if sg > 0 else x, y1 - y0, fc="white", ec="none", zorder=5.9))

# ================================================================ 床
fy = FLY
ax.plot([4, 196], [fy, fy], lw=LW_CUT, color=INK, zorder=4)
ax.add_patch(Rectangle((4, fy - 3.0), 192, 3.0, fc="#EFEAE2", ec="none", hatch="////", zorder=1))
T(5, fy + 1.0, "FL±0（はだしの床）", 1.8)

# ================================================================ 光（上のガラスから鏡面の溝を下りて床へ）
LIGHT = "#E59A1C"
ax.add_patch(Polygon([P(-G2 + 2, -BD), P(G2 - 2, -BD), P(G2 - 2, Z_UP), P(-G2 + 2, Z_UP)], closed=True, fc="#FFF2C2", ec="none", zorder=2.5))
def trace(u0, deg):
    th = math.radians(deg); du, dz = math.sin(th), -math.cos(th)
    pts = [(u0, Z_UP)]; u, z = u0, Z_UP; wl = G2 - 2
    for _ in range(40):
        t_floor = (-BD - z) / dz
        if abs(du) < 1e-9: t_wall = 1e9
        else: t_wall = ((wl if du > 0 else -wl) - u) / du
        if t_floor <= t_wall:
            u, z = u + du * t_floor, -BD; pts.append((u, z)); break
        u, z = u + du * t_wall, z + dz * t_wall; pts.append((u, z)); du = -du
    t = (-BT - z) / dz; pts.append((u + du * t, -BT))
    return pts
for u0, deg in ((-60, 6), (40, -9), (-20, 13), (70, -4), (-80, 11)):
    pts = trace(u0, deg)
    line(pts[:-1], lw=0.55, c=LIGHT, z=5.2)
    (xa, ya), (xb, yb) = P(*pts[-2]), P(*pts[-1])
    ax.annotate("", xy=(xb, yb + 0.3), xytext=(xa, ya), arrowprops=dict(arrowstyle="-|>", color=LIGHT, lw=0.55, mutation_scale=5, shrinkA=0, shrinkB=0), zorder=5.2)
# 空からの光（ガラスへ）
for u0, deg in ((-110, 22), (0, 8), (110, -12)):
    th = math.radians(deg)
    za = Z_GT + 9 + 170.0
    ua = u0 - math.tan(th) * (za - (Z_GT + 9))
    ax.annotate("", xy=P(u0, Z_GT + 12), xytext=P(ua, za), arrowprops=dict(arrowstyle="-|>", color=LIGHT, lw=0.6, mutation_scale=5, shrinkA=0, shrinkB=0), zorder=6)
# 床の光だまりと照り返し（梁の側面・合板の天井へ）
ax.add_patch(Polygon([P(-1100, -BT), P(1100, -BT), P(1100, -BT + 40), P(-1100, -BT + 40)], closed=True, fc="#FBE3A6", ec="none", zorder=3.9))
for (ua, ub, zb) in ((-650, -(G2 + BW), -420), (620, G2 + BW, -470), (-950, -800, Z_PUR - 2), (900, 760, Z_PUR - 2)):
    ax.annotate("", xy=P(ub, zb), xytext=P(ua, -BT + 40), arrowprops=dict(arrowstyle="-|>", color=LIGHT, lw=0.45, ls=(0, (2, 1.5)), mutation_scale=4, shrinkA=0, shrinkB=0), zorder=5.1)

# ================================================================ 寸法
def hdim(u0, u1, z, txt, up=True, size=1.8, ext_from=None):
    (xa, y), (xb, _) = P(u0, z), P(u1, z)
    ax.plot([xa, xb], [y, y], lw=LW_THIN, color=INK, zorder=7)
    for xx, uu in ((xa, u0), (xb, u1)):
        ax.plot([xx - 0.6, xx + 0.6], [y - 0.6, y + 0.6], lw=0.4, color=INK, zorder=7)
        if ext_from is not None:
            ye = P(uu, ext_from)[1]; ax.plot([xx, xx], [ye + (0.8 if ye < y else -0.8), y + (0.8 if ye < y else -0.8)], lw=LW_THIN, color=INK, zorder=7)
    if txt: T(0.5 * (xa + xb), y + (0.6 if up else -0.6), txt, size, ha="center", va="bottom" if up else "top", bbox=dict(fc="white", ec="none", pad=0.15))
def vdim(u, z0, z1, txt, left=True, size=1.8, ext_from=None, tz=None, bg=False):
    (x, ya), (_, yb) = P(u, z0), P(u, z1)
    ax.plot([x, x], [ya, yb], lw=LW_THIN, color=INK, zorder=7)
    for yy in (ya, yb):
        ax.plot([x - 0.6, x + 0.6], [yy - 0.6, yy + 0.6], lw=0.4, color=INK, zorder=7)
        if ext_from is not None:
            xe = P(ext_from, 0)[0]; ax.plot([xe + (0.8 if xe < x else -0.8), x + (0.8 if xe < x else -0.8)], [yy, yy], lw=LW_THIN, color=INK, zorder=7)
    ym = P(0, tz)[1] if tz is not None else 0.5 * (ya + yb)
    if txt:
        kw = dict(bbox=dict(fc="white", ec="none", pad=0.4)) if bg else {}
        T(x + (-0.7 if left else 0.7), ym, txt, size, ha="right" if left else "left", va="center", **kw)

# 溝 180・梁 90（梁の下）
zd = -BD - 120
hdim(-G2 - BW, -G2, zd, "90", ext_from=-BD); hdim(-G2, G2, zd, "180", ext_from=-BD); hdim(G2, G2 + BW, zd, "90", ext_from=-BD)
# ガラスの幅 300（上）
hdim(-gw, gw, Z_GT + 60, "300", ext_from=Z_GT + 9)
# 溝の深さ（ガラスの下から梁の下端）と梁のせい
vdim(-330, -BD, Z_UP, "溝の深さ 769", left=True, ext_from=-G2 - BW, tz=-460, bg=True)
vdim(330, -BD, 0, "梁のせい 600", left=False, ext_from=G2 + BW, tz=-460, bg=True)
# 層の厚み（右の端）
ux = 1700
for z0, z1, s, dz in ((0, Z_RF, "109", 0), (Z_INS, 0, "150", 0), (Z_PLY, Z_INS, "24", 0), (Z_PUR, Z_PLY, "150", 0)):
    vdim(ux, z0, z1, None, left=False, ext_from=1560)
    T(P(ux, 0)[0] + 0.8, 0.5 * (P(0, z0)[1] + P(0, z1)[1]) + dz, s, 1.6, va="center")
for z0, z1, s in ((Z_SH, Z_RF, "40"), (Z_VB, Z_SH, "24"), (0, Z_VB, "45")):
    vdim(ux - 120, z0, z1, None)
# 梁の上の 3 層の数字（細かいので左へ引き出す）
_xa = P(ux - 120, 0)[0]
for i, (z0, z1, s) in enumerate(((Z_SH, Z_RF, "40"), (Z_VB, Z_SH, "24"), (0, Z_VB, "45"))):
    ym_ = 0.5 * (P(0, z0)[1] + P(0, z1)[1]); yt_ = P(0, Z_RF)[1] + 4.6 - 2.0 * i
    ax.plot([_xa - 0.3, _xa - 2.0], [ym_, yt_ - 0.2], lw=LW_THIN, color=INK, zorder=7)
    T(_xa - 2.3, yt_ - 0.6, s, 1.5, ha="right")

# 高さの印
def level(u, z, txt, right=True):
    x, y = P(u, z)
    ax.add_patch(Polygon([(x, y), (x - 0.9, y + 1.4), (x + 0.9, y + 1.4)], closed=True, fc="none", ec=INK, lw=0.3, zorder=7))
    ax.plot([x - 0.9, x + (24 if right else -24)], [y + 1.4, y + 1.4], lw=LW_THIN, color=INK, zorder=7)
    T(x + (1.4 if right else -1.4), y + 2.0, txt, 1.7, ha="left" if right else "right")
level(G2 + BW + 10, -BD, "梁の下端 FL+2,900", right=True)

# ================================================================ 材料の引出し
NOTE_S = 1.75
# 右：屋根の層（一本の引出し線に点、文字は屋根の下の右の空きに）
uL = 1350
ys_layers = [(0.5 * (Z_SH + Z_RF), "屋根材型の太陽光 約40（筋の周り±250は金属の屋根材）"),
             (0.5 * (Z_VB + Z_SH), "野地 t24"),
             (0.5 * (0 + Z_VB), "通気垂木 杉 60×45 @455（勾配の方向）"),
             (3, "透湿防水シート（断熱と梁の上に一面）"),
             (0.5 * (Z_INS + 0), "断熱 木質繊維ボード t150（硬質、梁のあいだ）"),
             (Z_INS + 3, "気密シート（合板の上、梁の側面で立ち上げ）"),
             (0.5 * (Z_PLY + Z_INS), "構造用合板 t24（天井に現し、4周釘打ち）"),
             (0.5 * (Z_PUR + Z_PLY), "母屋 杉 60×150 @455（現し、見えがかり）"),
             (None, "合板の受け材 杉 45×45（梁の側面）"),
             (None, "母屋受け金物（上下両向き）")]
xL = P(uL, 0)[0]
ytop = P(0, Z_RF)[1]
ystack0 = P(0, -BD - 360)[1]
nL = 8
ax.plot([xL, xL], [ytop + 1.0, ystack0 - (nL - 1) * 2.8], lw=LW_THIN, color=INK, zorder=7)
for i, (zz, s_) in enumerate(ys_layers):
    yy = ystack0 - i * 2.8
    if zz is not None:
        ax.add_patch(plt.Circle((xL, P(0, zz)[1]), 0.35, fc=INK, ec="none", zorder=7.1))
        ax.plot([xL - 1.5, xL], [yy, yy], lw=LW_THIN, color=INK, zorder=7)
    T(xL - 2.0, yy, s_, NOTE_S, ha="right", va="center")
def lead(tx, ty, lx, ly, s, ha="left", size=NOTE_S, c=INK):
    ax.plot([tx, lx], [ty, ly], lw=LW_THIN, color=c, zorder=7)
    ax.add_patch(plt.Circle((tx, ty), 0.3, fc=c, ec="none", zorder=7.1))
    ax.plot([lx, lx + (1.2 if ha == "left" else -1.2)], [ly, ly], lw=LW_THIN, color=c, zorder=7)
    T(lx + (1.6 if ha == "left" else -1.6), ly, s, size, ha=ha, va="center", c=c)
_y8, _y9 = ystack0 - 8 * 2.8, ystack0 - 9 * 2.8
_xe = xL - 1.0
for (u_, z_), yy in (((G2 + BW + 22, Z_PLY - 22), _y8), ((G2 + BW + 40, Z_PUR - 12), _y9)):
    tx, ty = P(u_, z_)
    ax.plot([tx, _xe, xL - 1.5 + 0.5], [ty, yy, yy], lw=LW_THIN, color=INK, zorder=7)
    ax.add_patch(plt.Circle((tx, ty), 0.3, fc=INK, ec="none", zorder=7.1))

# 左上：光の筋の上の取り合い（屋根の上の空き）
xl_txt = 84.0
top_items = [
    ((-60, Z_GT - 3), "複層ガラス 幅300：外 遮熱Low-E 6・アルゴン12・内 型板の合わせ 4+4（凹凸を室内側）"),
    ((-(G2 + UPW + 9), Z_GT + 5), "熱を切ったアルミの枠・押縁（樹脂のスペーサー）"),
    ((-(G2 + UPW + 14), Z_RF + 35), "水切り板金（立ち上がり60）"),
    ((-(G2 + 45), Z_FR - 45), "断熱を立ち上がりに回して枠へ（木質繊維）"),
    ((-(G2 + 3), Z_FR - 15), "気密シートは立ち上がりの内側を枠まで"),
    ((-(G2 + UPW + 30), Z_VB - 15), "筋の脇の垂木 60×45（野地の端を受ける）"),
]
for i, ((u, z), s_) in enumerate(top_items):
    tx, ty = P(u, z)
    lead(tx, ty, xl_txt, 206.0 - 2.75 * i, s_, ha="right")
# 左下：溝と梁（梁の下の空き）
low_items = [
    ((-120, -3), "鋼の平板 6×60 L340（梁の上端に彫り込み、約0.9 mおき）"),
    ((-(G2 - 1), -300), "鏡面のアルミ t2（反射率 約0.95、ガラスの下から梁の下端まで）"),
    ((-(G2 + BW / 2), -540), "登り梁 集成材 90×600 2枚組（あいだ180）"),
]
for i, ((u, z), s_) in enumerate(low_items):
    tx, ty = P(u, z)
    lead(tx, ty, 92.0, P(0, -BD)[1] - 8.0 - 2.8 * i, s_, ha="right")

# 溝の下（光）
T(P(-130, -BD)[0], P(0, -BD - 470)[1], "溝の下の端はふさがない（溝の中は室内の空気）", 1.75, ha="right", va="top",
  bbox=dict(fc="white", ec="none", pad=0.3))
T(P(0, 0)[0], FLY + 14.0, "上のガラスに入った光が鏡面の溝で下へ運ばれ、梁の下へ\n（杉の面のままなら約1割、鏡面で約8割）", 1.8, ha="center", va="bottom", c="#9A5C00",
  bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))
T(P(-1800, 0)[0], FLY + 6.0, "床の光だまりの照り返しが\n梁の側面と合板の天井を照らす", 1.7, ha="left", va="bottom", c="#9A5C00")

# ================================================================ 表題
T(4, 215.5, "光の筋と架構", 4.2, bold=True, va="baseline")
T(44.0, 215.5, "1/20", 3.0, va="baseline")
T(4, 210.5, "保育室の中ほど（西の壁から約6 m）で梁に直角に切る、西を見る（左が南）", 1.8)
# 凡例（シート）
lx0, ly0 = 120.0, 216.5
ax.plot([lx0, lx0 + 6], [ly0, ly0], lw=0.5, color="#C0392B", ls=(0, (1.6, 1.2)))
T(lx0 + 7, ly0, "気密シート", 1.6, va="center")
ax.plot([lx0 + 25, lx0 + 31], [ly0, ly0], lw=0.5, color="#2F6FA8", ls=(0, (3, 1.5)))
T(lx0 + 32, ly0, "透湿防水シート", 1.6, va="center")
ax.annotate("", xy=(lx0 + 61, ly0), xytext=(lx0 + 55, ly0), arrowprops=dict(arrowstyle="-|>", color=LIGHT, lw=0.55, mutation_scale=5))
T(lx0 + 62, ly0, "光", 1.6, va="center")

os.makedirs(OUT, exist_ok=True)
fig.savefig(os.path.join(OUT, "sodachiya_present_slot.pdf"))
fig.savefig(os.path.join(OUT, "sodachiya_present_slot.png"), dpi=1600 / (H * MM))
print("out/sodachiya_present_slot.pdf・.png")
