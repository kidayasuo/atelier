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
    wl(2.94, 3.06, 1.6, 9.2); wl(2.94, 3.06, 10.4, E - 0.6)
    seg((3.0, E - 0.6), (3.6, E))                                   # corner cut (room side) at the roji exit
    seg((1.5, E - 0.6), (0.95, E))                                  # corner cut (toilet side)
    ax.add_patch(Circle(P(U(3.05), E - 0.75), 0.12, fc="#DDE8F0", ec="black", lw=0.4, zorder=7))   # small round mirror
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
    line([(U(1.6), E + 0.05), (U(2.9), E + 0.05)], lw=1.6, c="#7b5ea7", z=6)
    line([(U(0.05), E), (U(0.9), E)], lw=1.4, c="#6aa6c9", z=6)
    # skylight over wc, attic over store
    poly(Q([(0.1, 1.75), (1.45, 1.75), (1.45, J0), (2.9, J1), (2.9, E - 0.1), (0.1, E - 0.1)]), ec="#3d7fb0", lw=0.6, ls=(0, (3, 2)), z=7)
    labels_out += [(U(0.75), 2.9, 3), (U(2.25), 8.6, 3), (U(0.25), 6.6, 5), (U(0.6), 9.9, 6), (U(0.95), 7.3, 7),
                   (U(2.3), 3.6, 8), (U(2.25), 12.5, 11), (U(0.45), 11.6, 13),
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
line([(U0, 14.9), (U1, 14.9)], lw=0.4)
line([(U0, 15.0), (U1, 15.0)], lw=0.3, ls=(0, (6, 3)))
# north path edge
# break line south
line([(U0, -0.3), (U0, 15.2)], lw=0.3, ls=(0, (8, 2, 1, 2)))

# ---- loop arrows (dashed) along rails
for (a, b, v) in [(31, 50.4, 1.0), (56.4, 31, 12.75)]:
    xs, ys = zip(*[P(a + (b - a) * i / 40, v) for i in range(41)])
    ax.plot(xs, ys, lw=0.7, ls=(0, (4, 2)), color="#C0522B", zorder=4)
    x1, y1 = P(b - (b - a) * 0.02, v); x2, y2 = P(b, v)
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.7, color="#C0522B"), zorder=4)

# ---- labels
txt(36.0, 10.6, "3歳", size=10, color="#4d6b1f", weight="medium")
txt(45.0, 10.6, "4歳", size=10, color="#4d6b1f", weight="medium")
txt(54.0, 10.6, "5歳", size=10, color="#4d6b1f", weight="medium")
txt(31.5, 9.8, "園長室・応接", size=5.2, color="#777777")
txt(29.0, 0.8, "↓ ホール・海峡", size=5.5, color="#777777")
labels = [(35, 0.8, 1), (34.2, 12.75, 2), (54.0, 0.75, 4), (34.2, 14.3, 14), (36.0, 13.9, 15), (37.6, 12.0, 16)] + blk_labels
for u, v, n in labels:
    num(u, v, n)

# frames / dims
for uf, f in zip(range(30, 58, 3), range(11, 21)):
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

fig.text(25 / 297, 410 / 420, "育ち舎　3〜5歳の保育室　家具配置（たたき台）", fontsize=12.5, weight="medium", va="top")
fig.text(25 / 297, 402 / 420, "1/100（A3）　2026-10-20　スパン11〜19。点線のコットは午睡時（3歳20・4歳20・5歳10）。茶の一点鎖線はロフト、斜線はしずかな角の収納、青の破線はトップライト。",
         fontsize=6.5, va="top", color="#444444")
legend = [
    "1　西吹き抜け＝絵本の通り。くぼみ（床 h300、布を下ろせる）は隠れんぼの巣",
    "2　内縁側 幅1.5（はしごの縦木。はだし）",
    "3　路地 幅1.5（横木。途中で斜めに折れ、南北の側が入れ替わる）",
    "4　本の奥：畳とクッション、庭側に足を下ろせる溝（GLまで−300）、GLまでの低い窓、格子の引き戸",
    "5　手洗い×5 h500（折れ目の溜まり。斜めのカウンター）",
    "6　便所：座る便器×4（仕切りと扉 h1300）",
    "7　汚物流し（先生用）",
    "8　教材庫（路地から。天井 h2.4、その上は吹き抜け）。スパン14は西の端を職員用の個室に（10-23夜）",
    "11　路地の出口：暖簾は裾 h1200（子どもは下から先が見える）、角は隅切り＋小さな丸い鏡",
    "12　保育室から路地への戸（南の部屋は西寄り、北の部屋は東寄り）",
    "13　トップライト：路地と便所の上を屋根まで吹き抜けに（天袋なし）。東の端に低い窓",
    "14　外縁側 幅1.5（土足、FL−150。海峡から各クラスへ）",
    "15　断熱ガラス戸と下足箱・腰掛け（外縁側の側）",
    "16　保育室と内縁側の境（ふだんは開け放す吊り戸）",
    "スパン17はスパン14を南北に裏返した形（二つの路地は折れ方が逆）",
    "保育室は3室とも同じ構成。違うのは：机の高さ、コットの数、しずかな角の大きさ（3歳 小・4歳 中・5歳 中＋延長）、棚の中身。5歳は戸に合わせ反転",
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


# =================== furniture (3-5) : same room, changed only where needed ===================
WOOD = "#F7F1E6"
def t(u, v, s, size=4.6, **kw):
    txt(u, v, s, size=size, color="#333333", **kw)
def table(uc, vc, du, dv, n_u):
    g = sbox(uc - du/2, vc - dv/2, uc + du/2, vc + dv/2).buffer(-0.22, join_style=1).buffer(0.22, join_style=1)
    draw_shape(g, P, fc=WOOD, ec="black", lw=0.4, zorder=3)
    for i in range(n_u):
        uu = uc - du/2 + du*(i+0.5)/n_u
        for vv in [vc - dv/2 - 0.22, vc + dv/2 + 0.22]:
            box(uu - 0.14, uu + 0.14, vv - 0.12, vv + 0.12, lw=0.25, fc="white")
def cots(u0, u1, v0, v1, n_u, n_v, n):
    k = 0
    for i in range(n_u):
        for j in range(n_v):
            if k >= n: return
            uc = u0 + (u1 - u0)*(i+0.5)/n_u; vc = v0 + (v1 - v0)*(j+0.5)/n_v
            box(uc - 0.27, uc + 0.27, vc - 0.5, vc + 0.5, lw=0.3, ls=(0, (2, 1.5)), fc="none", ec="#4f6b2a", z=4)
            k += 1
def lockers(u0, u1, v0, v1, n):
    box(u0, u1, v0, v1, fc="white", lw=0.4)
    for i in range(1, n):
        vv = v0 + (v1 - v0)*i/n; line([(u0, vv), (u1, vv)], lw=0.2)
import math as _m
from shapely.geometry import Polygon as SPoly, Point as SPt, box as sbox
def draw_shape(g, mapf, **kw):
    xs, ys = g.exterior.xy
    ax.add_patch(Polygon([mapf(x, y) for x, y in zip(xs, ys)], closed=True, **kw))
def arc_desk(uc, vcen, r_in, r_out, half_deg, nseat):
    """desk bulges west; children sit on the concave (east) side facing west -> neighbours face slightly apart"""
    angs = [_m.radians(-half_deg + 2*half_deg*i/24) for i in range(25)]
    outer = [(uc + r_out*_m.sin(a), vcen - r_out*_m.cos(a)) for a in angs]
    inner = [(uc + r_in*_m.sin(a), vcen - r_in*_m.cos(a)) for a in angs[::-1]]
    ax.add_patch(Polygon([P(u, v) for u, v in outer + inner], closed=True, fc=WOOD, ec="black", lw=0.45, zorder=4))
    for i in range(nseat):
        a = _m.radians(-half_deg + 2*half_deg*(i+0.5)/nseat)
        u, v = uc + (r_in - 0.3)*_m.sin(a), vcen - (r_in - 0.3)*_m.cos(a)
        ax.add_patch(Circle(P(u, v), 0.16, fc="white", ec="black", lw=0.3, zorder=4))
def room(a, b, n_cot, tab_h, mir, Rc, Lp, n_leg):
    """mir=False: quiet corner SW, loft NW, lockers N, teacher S.  mir=True: mirrored (desk NW, loft SW)."""
    W = b - a
    S = (lambda s: b - s) if mir else (lambda s: a + s)       # s = distance from the 'desk-side' partition
    def bx(s0, s1, v0, v1, **kw):
        u0, u1 = sorted([S(s0), S(s1)]); box(u0, u1, v0, v1, **kw)
    def pt(s, v): return P(S(s), v)
    # ---- quiet corner desk: smooth curve, rounded ends; size by age (Rc, Lp)
    r_in = Rc - 0.55
    cs, cv = Rc, 1.6 + Rc
    ring = SPt(cs, cv).buffer(Rc, 128).difference(SPt(cs, cv).buffer(r_in, 128))
    quad = sbox(0, 1.6, cs, cv)
    band = ring.intersection(quad)
    band = band.union(sbox(cs - 0.01, 1.6, cs + 0.3, 1.6 + 0.55))
    if Lp > 0:
        band = band.union(sbox(0, cv - 0.01, 0.55, cv + Lp))
    band = band.buffer(-0.18, join_style=1).buffer(0.18, join_style=1)
    draw_shape(band, pt, fc=WOOD, ec="black", lw=0.45, zorder=4)
    stor = quad.difference(SPt(cs, cv).buffer(Rc + 0.02, 128))
    for g in getattr(stor, "geoms", [stor]):
        if not g.is_empty:
            draw_shape(g, pt, fc="#E9DDC6", ec="none", lw=0, zorder=4.5, hatch="////")
    n_arc = max(2, int(round((r_in - 0.3) * _m.pi / 2 / 0.62)))
    for i in range(n_arc):
        t_ = _m.radians(270 - 90 * (i + 0.5) / n_arc)
        x, y = cs + (r_in - 0.3) * _m.cos(t_), cv + (r_in - 0.3) * _m.sin(t_)
        ax.add_patch(Circle(pt(x, y), 0.16, fc="white", ec="black", lw=0.3, zorder=5))
    for k in range(n_leg):
        y = cv + 0.3 + 0.62 * k
        ax.add_patch(Circle(pt(0.85, y), 0.16, fc="white", ec="black", lw=0.3, zorder=5))
    xs, ys = pt(Rc * 0.55, 1.6 + Rc * 0.45)
    ax.text(xs, ys, "しずかな角", fontsize=4.2, ha="center", va="center", zorder=8, color="#333333")
    # ---- loft in the other west bay (+ den / cot storage below), furniture stair
    bx(3.15, W - 0.1, 1.68, 3.6, fc="#EADBB8", lw=0.7, ls=(0, (6, 2, 1, 2)), ec="#8a5a2b", z=3)
    for k in range(3):
        bx(3.4, 4.2, 3.6 + 0.3 * k, 3.9 + 0.3 * k, fc=WOOD, lw=0.35, z=4)
    xs, ys = pt(4.6, 2.55)
    ax.text(xs, ys, "ロフト h1200\n下はデンと\nコット収納", fontsize=4.2, ha="center", va="center", zorder=8, color="#333333")
    # ---- teacher's seat: back to the desk-side partition, faces the room; screens h1100 in front and on the active (east) side
    tv0, tv1 = 1.6 + 2.6 + max(Lp, 0) + 0.3, 1.6 + 2.6 + max(Lp, 0) + 1.3
    bx(0.1, 0.55, tv0 + 0.25, tv0 + 0.75, fc="white", lw=0.35, z=4)            # chair
    bx(0.6, 1.15, tv0, tv1, fc=WOOD, lw=0.45, z=4)                              # desk h700
    line([(S(1.2), tv0), (S(1.2), tv1)], lw=1.3, c="#8a5a2b", z=5)              # front screen
    line([(S(0.06), tv1), (S(1.2), tv1)], lw=1.3, c="#8a5a2b", z=5)             # side screen (east)
    xs, ys = pt(1.85, (tv0 + tv1) / 2)
    ax.text(xs, ys, "先生の席", fontsize=4.2, ha="center", va="center", zorder=8, color="#333333")
    # ---- lockers on the opposite partition; play shelves after the teacher on the desk-side partition
    bx(W - 0.4, W - 0.06, 5.2, 8.4, fc="white", lw=0.4)
    for i in range(1, 10):
        vv = 5.2 + 3.2 * i / 10; line([(S(W - 0.4), vv), (S(W - 0.06), vv)], lw=0.2)
    xs, ys = pt(W - 0.75, 6.8); ax.text(xs, ys, "個人棚", fontsize=4.2, ha="center", va="center", zorder=8, color="#333333")
    bx(0.06, 0.4, tv1 + 0.4, tv1 + 2.2, fc="white", lw=0.4)
    xs, ys = pt(0.8, tv1 + 1.3); ax.text(xs, ys, "遊びの棚", fontsize=4.2, ha="center", va="center", zorder=8, color="#333333")
    # ---- gathering rug + nap + tables
    ax.add_patch(Ellipse(P(a + W / 2, 6.9), 2.6, 2.4, fc="#F4E9F0", ec="#9b6f8c", lw=0.4, zorder=2))
    t(a + W / 2, 6.9, "あつまり", size=4.3)
    cots(a + 0.6, b - 0.6, 4.7, 8.7, 7, 3, n_cot)
    for uc in [a + 1.6, a + 4.4]:
        for vc in [9.5, 11.1]:
            table(uc, vc, 1.2, 0.75, 3)
    t(a + 3.0, 9.2, f"食卓 h{tab_h}", size=4.3)
room(33, 39, 20, 400, False, 2.1, 0.0, 0)
room(42, 48, 20, 450, False, 2.6, 0.0, 0)
room(51, 57, 10, 500, True, 2.6, 1.2, 2)

# ---------- picture-book street along the west void ----------
shelf_runs = [(32.9, 35.8), (36.2, 38.8), (39.2, 41.8), (42.2, 43.9), (46.3, 47.8), (48.2, 50.8)]
for a0, b0 in shelf_runs:
    box(a0, b0, 0.08, 0.38, fc="#F3E7CF", lw=0.35, z=4)
for a0, b0 in [(37.0, 38.2), (48.6, 49.8)]:                      # reading niches (deeper)
    box(a0, b0, 0.08, 0.7, fc="#F3E7CF", lw=0.45, z=5)
    line([(a0, 0.72), (b0, 0.72)], lw=1.4, c="#9b6f8c", ls=(0, (1.5, 1)), z=6)
    ax.add_patch(Ellipse(P((a0 + b0) / 2, 0.5), 0.3, 0.8, fc="#E8D7E6", ec="#9b6f8c", lw=0.3, zorder=6))
for a0, b0 in [(30.6, 32.6), (44.1, 46.1)]:                     # openings to the play hall (west building)
    box(a0, b0, -0.08, 0.08, fc="white", lw=0.0, ec="white", z=6)
    t((a0 + b0) / 2, -0.55, "遊戯室へ", size=4.4)
# reading room at the north dead end ("本の奥"): no shelves
box(51.0, 57.0, 0.0, 1.6, fc="#F1E6F0", lw=0.0, ec="none", z=0.5)
line([(51.0, 0.08), (51.0, 1.55)], lw=1.2, c="#8a5a2b", z=6)      # lattice sliding door
box(51.6, 56.9, 0.5, 1.55, fc="#EFE6D2", lw=0.45, z=4)              # tatami floor (FL)
box(52.2, 56.6, 0.08, 0.5, fc="#D9E6CF", lw=0.6, z=4)                # foot well down to GL (-300)
line([(52.6, -0.02), (56.4, -0.02)], lw=2.0, c="#3d7fb0", z=7)      # low window down to GL
import random as _r
_r.seed(3)
for k in range(14):
    uu = 51.9 + 4.8 * _r.random(); vv = 0.75 + 0.7 * _r.random()
    ax.add_patch(Circle(P(uu, vv), 0.16 + 0.08 * _r.random(), fc=["#E8D7E6", "#F3E1C7", "#D9E6CF"][k % 3], ec="#9b6f8c", lw=0.3, zorder=6))
line([(56.95, 0.3), (56.95, 1.3)], lw=0.6, z=7)                   # exit door (north)
ax.add_patch(Circle(P(54.4, -2.3), 1.3, fc="none", ec="#5a7a3a", lw=0.5, zorder=3))
ax.add_patch(Circle(P(54.4, -2.3), 0.1, fc="#5a7a3a", ec="none", zorder=3))
t(56.75, -2.6, "読書の庭（モミジ・苔）", size=4.2)
t(54.4, 0.85, "", size=4)

# ---------- 大人のトイレ（10-23夜、ユーザー：3か所とも性別を示さない個室）----------
box(30.6, 32.6, -0.075, 0.075, lw=0.5, fc="#444444", z=7)      # 口①は閉じた（10-21、南の口へまとめた）
box(30.62, 32.58, -0.75, -0.35, fc="white", lw=0, ec="white", z=9)   # 「遊戯室へ」の字を消す
# スパン11：多目的便所（v1.6–4.3）｜記録・連絡の机（4.3–7.6）｜園長室・応接（7.6–12）
fill(30.0, 33.0, 1.6, 4.3, C_WC, z=1.5)
for vv in (4.3, 7.6):
    wall(30.0, 33.0, vv - 0.05, vv + 0.05)
wall(29.95, 30.05, 1.6, 4.3); wall(29.95, 30.05, 7.6, 12.0)
box(30.9, 32.0, 1.5, 1.7, fc=C_WC, lw=0, ec=C_WC, z=6)             # 引き戸 1.1（西吹き抜けから）
line([(30.9, 1.45), (32.1, 1.45)], lw=1.0, c="#3d7fb0", z=7)
box(30.3, 31.1, 7.55, 7.65, fc="white", lw=0, ec="white", z=6)     # 記録の机｜園長室の戸
box(32.30, 32.70, 3.60, 4.25, lw=0.35)                           # 便器
ax.add_patch(Ellipse(P(32.5, 3.75), 0.32, 0.42, fc="white", ec="black", lw=0.3, zorder=4))
line([(32.9, 3.1), (32.9, 4.2)], lw=0.8, c="#666666", z=6)       # L形の手すり
line([(32.05, 3.4), (32.05, 4.2)], lw=0.8, c="#666666", z=6)     # 跳ね上げの手すり
box(30.05, 30.55, 2.40, 2.95, lw=0.35, fc="#EEF5F7")               # 手洗い
box(30.05, 30.45, 3.30, 4.20, lw=0.35, fc="#F3E7CF", ls=(0, (2, 1)))   # おむつ替え台（折りたたみ）
box(32.55, 32.95, 1.80, 2.40, lw=0.35, fc="#EEF5F7")               # オストメイトの流し
ax.add_patch(Circle(P(31.3, 2.6), 0.75, fc="none", ec="#3d7fb0", lw=0.3, ls=(0, (2, 2)), zorder=4))   # 回転の円 φ1.5
txt(31.4, 3.5, "多目的便所", size=4.8)
txt(31.5, 5.95, "記録・連絡の机", size=4.8, color="#777777")
# スパン14：職員用の個室（教材庫の西の端、u40.5–42・v1.6–3.6）。路地の形はそのまま、教材庫の口を北へ
fill(40.5, 42.0, 1.65, 3.6, C_WC, z=1.5)
box(40.44, 40.56, 2.35, 3.45, lw=0.5, fc="#444444", z=6)            # 路地｜個室（前の教材庫の口をふさぐ）
box(40.44, 40.56, 3.75, 4.75, fc=C_LOOP, lw=0, ec=C_LOOP, z=6)     # 教材庫の新しい口
wall(40.5, 42.0, 3.55, 3.65)
box(41.15, 41.95, 1.5, 1.7, fc=C_WC, lw=0, ec=C_WC, z=7)           # 戸（西吹き抜けから、内側から鍵）
line([(41.15, 1.65), (41.85, 2.3)], lw=0.4, z=7)
box(40.65, 41.05, 2.90, 3.55, lw=0.35)
ax.add_patch(Ellipse(P(40.85, 3.1), 0.3, 0.38, fc="white", ec="black", lw=0.3, zorder=4))
box(41.55, 41.95, 3.10, 3.55, lw=0.35, fc="#EEF5F7")
txt(41.25, 2.3, "職員", size=4.2)
# 換気扇（天井、梁の下端の高さ）→ ダクトを真上へ、屋根の上の換気の頭（連携 10-23夜9）。給気は戸の下のすき間から西吹き抜けの空気
for uu, vv in ((32.2, 3.1), (41.3, 3.0)):
    box(uu - 0.15, uu + 0.15, vv - 0.15, vv + 0.15, lw=0.35, fc="white", z=8)
    line([(uu - 0.15, vv - 0.15), (uu + 0.15, vv + 0.15)], lw=0.3, z=8); line([(uu - 0.15, vv + 0.15), (uu + 0.15, vv - 0.15)], lw=0.3, z=8)
txt(32.2, 2.75, "換気扇→屋根", size=3.6, color="#3d7fb0")
txt(41.3, 3.4, "換気扇→屋根", size=3.2, color="#3d7fb0")
fig.text(25 / 297, 15 / 420, "大人のトイレ（10-23夜）：多目的便所（スパン11）・職員用の個室（スパン14）・2階の便所の3か所、どれも性別を示さない個室。閉じる部屋は天井の換気扇から屋根の上へ（⊠）",
         fontsize=5.2, va="top", color="#3d7fb0")
fig.savefig(_os.path.join(OUT, "sodachiya_35_furniture.pdf"))
fig.savefig(_os.path.join(OUT, "sodachiya_35_furniture.png"), dpi=220)
