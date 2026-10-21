import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUT = _os.environ.get("OUT", _os.path.join(ROOT, "out"))
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Ellipse

plt.rcParams["font.family"] = "Noto Sans CJK JP"

R = 205.0
phi0 = math.radians(186.67)
phi_mid = phi0 - 43.5 / R
rot = -(phi_mid - math.pi)
cr, sr = math.cos(rot), math.sin(rot)

def raw(u, v):
    p = phi0 - u / R
    r = R - v
    x, y = r * math.cos(p), r * math.sin(p)
    return x * cr - y * sr, x * sr + y * cr

X0, Y0 = raw(30, 0)
def P(u, v):
    x, y = raw(u, v)
    return x - X0, y - Y0

def rect_pts(u0, u1, v0, v1, n=6):
    pts = [P(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)]
    pts += [P(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
    return pts

def area(u0, u1, v0, v1):
    pts = rect_pts(u0, u1, v0, v1, 12)
    s = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2

MM = 1 / 25.4
fig = plt.figure(figsize=(297 * MM, 420 * MM))
xmin, xmax = -3.5, 20.0
ymin, ymax = -2.5, 29.5
left_mm, bottom_mm = 25, 70
ax = fig.add_axes([left_mm / 297, bottom_mm / 420, (xmax - xmin) * 10 / 297, (ymax - ymin) * 10 / 420])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")

LW = 0.45
C_ROOM, C_LOOP, C_WC, C_ST, C_OTHER = "#EEF3E2", "#F6DDD3", "#D5EBEE", "#E4E1DA", "#F2F2EF"

def fill(u0, u1, v0, v1, c, z=0):
    ax.add_patch(Polygon(rect_pts(u0, u1, v0, v1), closed=True, fc=c, ec="none", zorder=z))

def box(u0, u1, v0, v1, lw=LW, fc="white", ls="-", z=3, ec="black"):
    ax.add_patch(Polygon(rect_pts(u0, u1, v0, v1), closed=True, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))

def line(pts, lw=LW, ls="-", c="black", z=3):
    xs, ys = zip(*[P(u, v) for u, v in pts])
    ax.plot(xs, ys, lw=lw, ls=ls, color=c, zorder=z, solid_capstyle="butt")

def wall(u0, u1, v0, v1):
    box(u0, u1, v0, v1, lw=0.5, fc="#444444", z=5)

def txt(u, v, s, size=6.5, **kw):
    x, y = P(u, v)
    ax.text(x, y, s, fontsize=size, ha="center", va="center", zorder=8, **kw)

def num(u, v, n):
    x, y = P(u, v)
    ax.add_patch(Circle((x, y), 0.3, fc="white", ec="black", lw=0.4, zorder=9))
    ax.text(x, y, str(n), fontsize=5.6, ha="center", va="center", zorder=10)

U0, U1 = 30.0, 57.0
# ---- fills
E, G = 12.0, 13.5
fill(U0, 33, 1.6, E, C_OTHER)
for a, b in [(33, 39), (42, 48), (51, 57)]:
    fill(a, b, 1.6, E, C_ROOM)

fill(U0, U1, 0, 1.6, C_LOOP)                 # west void (rail)
fill(U0, U1, E, G, C_LOOP)
fill(U0, U1, G, 15, "#E6DFD0")              # outer engawa (shoes, FL-150)
fill(U1, U1 + 1.2, 0, 15, "#FBEDE7")           # north path (rung, tbd)
# ---- walls & columns
wall(U0, U1, -0.075, 0.075)
wall(U1 - 0.06, U1 + 0.06, 0, 12)            # north gable
for uf in range(30, 58, 3):
    for vc in [0, 12]:
        box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, lw=0.3, fc="black", z=6)
# room west walls (h2.4 + lattice above) -- shown as thin wall
for a, b in [(30, 33), (33, 39), (42, 48), (51, 57)]:
    wall(a, b, 1.55, 1.65)
wall(32.94, 33.06, 1.6, E)                   # office / 3yr
def poly(pts, fc="none", ec="none", lw=0.0, ls="-", z=1):
    ax.add_patch(Polygon([P(u, v) for u, v in pts], closed=True, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))

def crank_block(b0, flip, labels_out):
    U = (lambda w: b0 + 3 - w) if flip else (lambda w: b0 + w)
    Q = lambda pts: [(U(w), v) for w, v in pts]
    J0, J1 = 5.0, 7.0                       # crank (jog) zone
    roji = [(0, 1.6), (1.5, 1.6), (1.5, J0), (3, J1), (3, E), (1.5, E), (1.5, J1), (0, J0)]
    store = [(1.5, 1.6), (3, 1.6), (3, J1), (1.5, J0)]
    wc = [(0, J0), (1.5, J1), (1.5, E), (0, E)]
    poly(Q(roji), C_LOOP); poly(Q(store), C_ST); poly(Q(wc), C_WC)
    def wl(w0, w1, v0, v1):
        a, b = sorted([U(w0), U(w1)]); wall(a, b, v0, v1)
    def seg(p, q, lw=2.2, c="#444444"):
        line([(U(p[0]), p[1]), (U(q[0]), q[1])], lw=lw, c=c, z=5)
    # south-room wall (w=0): door into roji west half
    wl(-0.06, 0.06, 1.6, 3.6); wl(-0.06, 0.06, 4.8, E)
    line([(U(0.1), 3.6), (U(0.1), 4.8)], lw=0.5)
    # north-room wall (w=3): door into roji east half
    wl(2.94, 3.06, 1.6, 9.2); wl(2.94, 3.06, 10.4, E)
    line([(U(2.9), 9.2), (U(2.9), 10.4)], lw=0.5)
    # store walls
    wl(1.5, 3.0, 1.55, 1.65)
    seg((1.5, 1.65), (1.5, 2.4)); seg((1.5, 3.4), (1.5, J0)); seg((1.5, J0), (3, J1))
    line([(U(1.5), 2.4), (U(1.5), 3.4)], lw=0.5)
    # handwash counter along the diagonal (wc side), 5 basins
    dw, dv = 1.5 / 2.5, 2.0 / 2.5
    nw, nv = -dv, dw                                    # normal toward wc side
    t0, t1, off = 0.45, 2.45, 0.45
    A = (dw * t0, J0 + dv * t0); B = (dw * t1, J0 + dv * t1)
    C = (B[0] + nw * off, B[1] + nv * off); D = (A[0] + nw * off, A[1] + nv * off)
    poly(Q([A, B, C, D]), fc="white", ec="black", lw=0.45, z=3)
    for k in range(5):
        t = t0 + (t1 - t0) * (k + 0.5) / 5
        w = dw * t + nw * 0.22; v = J0 + dv * t + nv * 0.22
        ax.add_patch(Ellipse(P(U(w), v), 0.26, 0.26, fc="#EEF5F7", ec="black", lw=0.3, zorder=4))
    # booths 4 x 0.9 against south-room wall, v 8.4-12.0, depth 1.05
    for i in range(1, 5):
        vv = 7.6 + 0.9 * i
        if i < 4:
            line([(U(0.06), vv), (U(1.05), vv)], lw=0.4)
    line([(U(0.06), 7.6), (U(1.05), 7.6)], lw=0.4)
    for i in range(4):
        vc = 7.6 + 0.9 * i + 0.45
        a, b = sorted([U(0.06), U(0.3)]); box(a, b, vc - 0.17, vc + 0.17, lw=0.3)
        ax.add_patch(Ellipse(P(U(0.52), vc), 0.42, 0.32, fc="white", ec="black", lw=0.3, zorder=4))
        line([(U(1.05), vc - 0.4), (U(1.05), vc + 0.05)], lw=0.5)
    # mop sink
    a, b = sorted([U(0.06), U(0.62)]); box(a, b, 7.05, 7.55, lw=0.35, fc="#F2F7F8")
    # shikidai / noren / low window
    a, b = sorted([U(0.1), U(1.45)]); box(a, b, 1.65, 1.95, lw=0.35, fc="#F7F1E6")
    line([(U(1.6), E + 0.05), (U(2.9), E + 0.05)], lw=1.6, c="#7b5ea7", z=6)
    line([(U(0.05), E), (U(1.45), E)], lw=1.4, c="#6aa6c9", z=6)
    # skylight over wc, attic over store
    poly(Q([(0.1, J0 + 0.7), (1.4, J1 + 0.1), (1.4, E - 0.1), (0.1, E - 0.1)]), ec="#3d7fb0", lw=0.6, ls=(0, (3, 2)), z=7)
    poly(Q([(1.55, 1.7), (2.95, 1.7), (2.95, J1 - 0.1), (1.55, J0 + 0.05)]), ec="#8a5a2b", lw=0.5, ls=(0, (6, 2, 1, 2)), z=7)
    labels_out += [(U(0.75), 2.9, 3), (U(2.25), 8.6, 3), (U(0.25), 6.6, 5), (U(0.6), 9.9, 6), (U(0.95), 7.3, 7),
                   (U(2.3), 3.6, 8), (U(0.75), 2.0, 10), (U(2.25), 12.5, 11), (U(0.45), 11.6, 13),
                   (U(0.1) + (-0.55 if not flip else 0.55), 4.2, 12), (U(2.9) + (0.55 if not flip else -0.55), 9.8, 12)]

blk_labels = []
crank_block(39, False, blk_labels)
crank_block(48, True, blk_labels)
# 4yr back wall at u=51? (block 17 toilet strip back wall = 5yr south wall) handled above
# north room wall at u=42/51 continuing west part (store) already by wall()
# glass line (insulated) at G with shoe cabinets on outer side; screens at E
line([(U0, G), (U1, G)], lw=1.6, c="#3d7fb0", z=6)
for a, b in [(33, 39), (42, 48), (51, 57)]:
    for c0, c1 in [(a + 0.3, a + 2.2), (a + 3.8, b - 0.3)]:
        box(c0, c1, G + 0.05, G + 0.45, lw=0.35, fc="#F7F1E6", z=6)
    line([(a + 0.05, E), (b - 0.05, E)], lw=0.9, ls=(0, (2, 1.5)), c="#7b5ea7", z=6)
# engawa edge + columns, shoe step
line([(U0, 14.9), (U1 + 1.2, 14.9)], lw=0.4)
line([(U0, 15.0), (U1, 15.0)], lw=0.3, ls=(0, (6, 3)))
# north path edge
line([(U1 + 1.2, 0), (U1 + 1.2, 15)], lw=0.4, ls=(0, (2, 1.5)))
# break line south
line([(U0, -0.3), (U0, 15.2)], lw=0.3, ls=(0, (8, 2, 1, 2)))

# ---- loop arrows (dashed) along rails
for (a, b, v) in [(31, 56.4, 0.8), (56.4, 31, 12.75)]:
    xs, ys = zip(*[P(a + (b - a) * i / 40, v) for i in range(41)])
    ax.plot(xs, ys, lw=0.7, ls=(0, (4, 2)), color="#C0522B", zorder=4)
    x1, y1 = P(b - (b - a) * 0.02, v); x2, y2 = P(b, v)
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.7, color="#C0522B"), zorder=4)

# ---- labels
txt(36, 6.8, "3歳", size=10, color="#4d6b1f", weight="medium")
txt(45, 6.8, "4歳", size=10, color="#4d6b1f", weight="medium")
txt(54, 6.8, "5歳", size=10, color="#4d6b1f", weight="medium")
for uc in [36, 45, 54]:
    txt(uc, 5.6, "（家具は次回）", size=5.5, color="#666666")
txt(31.5, 6.8, "事務", size=6.5, color="#777777")
txt(29.0, 0.8, "↓ ホール・海峡", size=5.5, color="#777777")
labels = [(35, 0.8, 1), (34.2, 12.75, 2), (57.6, 7.5, 4), (34.2, 14.3, 14), (36.0, 13.9, 15), (37.6, 12.0, 16)] + blk_labels
for u, v, n in labels:
    num(u, v, n)

# frames / dims
for uf, f in zip(range(30, 58, 3), range(9, -1, -1)):
    x, y = P(uf, -1.2)
    ax.text(x, y, f"架構{f}", fontsize=5, ha="center", va="center")
    line([(uf, -0.35), (uf, -0.85)], lw=0.25)
for s, uc in zip(range(11, 20), [31.5 + 3 * i for i in range(9)]):
    txt(uc, -1.95, f"スパン{s}", size=4.4, color="#666666")
ud = U1 + 2.2
line([(ud, 0), (ud, 15)], lw=0.3)
for vv in [0, 1.6, 12, 15]:
    line([(ud - 0.15, vv), (ud + 0.15, vv)], lw=0.5)
for a, b, s in [(0, 1.6, "1,600"), (1.6, 12, "10,400"), (12, 15, "3,000")]:
    x, y = P(ud + 0.45, (a + b) / 2)
    ax.text(x, y, s, fontsize=5, ha="center", va="center")
# roji dims (span 14)


# north arrow + scale
nx, ny = 18.0, 26.5
north = (-sr, cr)
ax.annotate("", xy=(nx + north[0] * 1.3, ny + north[1] * 1.3), xytext=(nx - north[0] * 0.6, ny - north[1] * 0.6),
            arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
ax.text(nx + north[0] * 1.8, ny + north[1] * 1.8, "N", fontsize=8, ha="center", va="center")
sx, sy = 14.0, -2.2
for i in range(5):
    ax.add_patch(Polygon([(sx + i, sy), (sx + i + 1, sy), (sx + i + 1, sy + 0.18), (sx + i, sy + 0.18)],
                         fc="black" if i % 2 == 0 else "white", ec="black", lw=0.3))
for i in [0, 1, 5]:
    ax.text(sx + i, sy - 0.3, f"{i}", fontsize=5, ha="center", va="top")
ax.text(sx + 5.4, sy + 0.09, "m", fontsize=5, va="center")

# ---- areas
A = {}
A["3"] = area(33, 39, 1.6, G); A["4"] = area(42, 48, 1.6, G); A["5"] = area(51, 57, 1.6, G)
A["in"] = area(33, 39, 1.6, E)
blk = {}
for b0, k in [(39, "14"), (48, "17")]:
    blk[k] = dict(
        roji=area(b0, b0 + 1.5, 1.6, E),
        wc=area(b0, b0 + 1.5, 7.0, E) + 1.5,
        st_in=area(b0 + 1.5, b0 + 3, 1.6, 5.0) + 1.5,
        st_out=area(b0 + 1.5, b0 + 3, 9.6, 12),
        attic=area(b0 + 1.5, b0 + 3, 1.6, 12),
    )
print(A, blk)

fig.text(25 / 297, 410 / 420, "育ち舎　3〜5歳の範囲　回遊のはしごと便・倉庫（たたき台）", fontsize=12.5, weight="medium", va="top")
fig.text(25 / 297, 402 / 420, "1/100（A3）　2026-10-19　スパン11〜19。断熱ガラス戸は縁側の中ほど（柱の列から1.5 m外）。破線の矢印は回遊、青の破線はトップライト、一点鎖線は天袋（頭上）。保育室の家具は次回。",
         fontsize=6.5, va="top", color="#444444")
legend = [
    "1　西吹き抜け（はしごの縦木。遊戯室に開く子どもの道）",
    "2　内縁側 幅1.5（はしごの縦木。はだし）",
    "3　路地 幅1.5（横木。途中で斜めに折れ、南北の側が入れ替わる）",
    "4　北の小径（機械室とのすき間。外、検討中）",
    "5　手洗い×5 h500（折れ目の溜まり。斜めのカウンター）",
    "6　便所：座る便器×4（仕切りと扉 h1300）",
    "7　汚物流し（先生用）",
    "8　教材庫 約6.6 m²（路地から。上は天袋）",
    "10　式台 150（路地の西の入口）",
    "11　暖簾（路地の東の入口）",
    "12　保育室から路地への戸（南の部屋は西寄り、北の部屋は東寄り）",
    "13　トップライト（便所の上）。東の端に縁側への低い窓",
    "14　外縁側 幅1.5（土足、FL−150。海峡から各クラスへ）",
    "15　断熱ガラス戸と下足箱・腰掛け（外縁側の側）",
    "16　保育室と内縁側の境（ふだんは開け放す吊り戸）",
    "スパン17はスパン14を南北に裏返した形（二つの路地は折れ方が逆）",
]
col_x = [25 / 297, 160 / 297]
y0, dy, half = 62 / 420, 4.3 / 420, 8
for i, s in enumerate(legend):
    c, r = (0, i) if i < half else (1, i - half)
    fig.text(col_x[c], y0 - r * dy, s, fontsize=6.2, va="top")
b = blk["14"]
fig.text(25 / 297, 28 / 420,
         f"面積（芯々、概算）　保育室 各 {A['in']:.1f} m²（要求 約60）　"
         f"便スパン1つあたり：路地 {b['roji']:.1f}、便所と手洗い {b['wc']:.1f}、教材庫 {b['st_in']:.1f} m²",
         fontsize=6.0, va="top")
fig.text(25 / 297, 23 / 420,
         "便器：3〜5歳 60人に8（7.5人に1）＋園庭の便所2〜3。手洗い10。スパン14は3歳と4歳、スパン17は4歳と5歳が使う。外遊びの道具と行事の倉庫は園庭の小屋へ。",
         fontsize=6.0, va="top", color="#444444")

fig.savefig(_os.path.join(OUT, "sodachiya_35_ladder.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_35_ladder.png"), dpi=220)
