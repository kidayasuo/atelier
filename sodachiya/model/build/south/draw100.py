"""3dm（メッシュの版）から 1/100 の図をつくる：1 階平面（＋西館 2 階）と断面 3 つ
使い方: python3 draw100.py MODEL_MESH.3dm OUTDIR
- 平面：FL+1200 で切る。切れたものは塗り（構造・壁は黒、家具は灰、ガラスは細線）、下に見えるものは
  上のものから順に白で塗って外形を描く（隠れ線の処理）。屋根の外形は破線。
- 断面：本館の架構に直交する（中心 C を通る）鉛直面で切り、奥 3.2 m までを見えがかりで描く。
用紙は A1（平面は縦、断面は横）。PDF と PNG。
"""
import sys, os, math, re, numpy as np, rhino3dm as r
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, PathPatch
from matplotlib.path import Path
from matplotlib import font_manager
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, box
from shapely.ops import unary_union, polygonize, linemerge
import mapbox_earcut as earcut

IN, OUTD = sys.argv[1], sys.argv[2]
os.makedirs(OUTD, exist_ok=True)
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['pdf.fonttype'] = 42

C = np.array([194645.51027008, -41347.80985094])
MM = 1 / 25.4                     # mm → inch
LW = lambda mm: mm * 72 / 25.4    # 線の太さ mm → pt

# ---------------------------------------------------------------- 読み込み → 三角形
def curve_pts(c, n=48):
    if isinstance(c, r.PolylineCurve): return [c.Point(i) for i in range(c.PointCount)]
    if isinstance(c, r.LineCurve): return [c.PointAtStart, c.PointAtEnd]
    d = c.Domain; return [c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]
A3 = lambda ps: np.array([[p.X, p.Y, p.Z] for p in ps], float)

def tri_mesh(g):
    V = A3([g.Vertices[i] for i in range(len(g.Vertices))]); T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; T.append((f[0], f[1], f[2]))
        if f[3] != f[2]: T.append((f[0], f[2], f[3]))
    return V[np.array(T)] if T else np.zeros((0, 3, 3))

def cap(rings):
    """平らな輪（外＋穴）→ 三角形"""
    P = np.vstack(rings); c = P.mean(0)
    n = np.zeros(3)
    for ring in rings[:1]:
        for i in range(len(ring)): n += np.cross(ring[i] - c, ring[(i + 1) % len(ring)] - c)
    if np.linalg.norm(n) < 1e-9: return []
    n /= np.linalg.norm(n); a = np.array([1., 0, 0]) if abs(n[0]) < .9 else np.array([0, 1., 0])
    x = np.cross(n, a); x /= np.linalg.norm(x); y = np.cross(n, x)
    Q = np.c_[(P - c) @ x, (P - c) @ y]
    ends = np.cumsum([len(rg) for rg in rings]).astype(np.uint32)
    idx = earcut.triangulate_float64(Q, ends)
    return [P[idx[i:i + 3]] for i in range(0, len(idx), 3)]

def tri_extrusion(g):
    T = []
    for k in range(g.ProfileCount):
        c0, c1 = g.Profile3d(k, 0.0), g.Profile3d(k, 1.0)
        if c0 is None or c1 is None: continue
        p0, p1 = A3(curve_pts(c0)), A3(curve_pts(c1))
        for i in range(len(p0) - 1):
            T += [np.array([p0[i], p0[i + 1], p1[i + 1]]), np.array([p0[i], p1[i + 1], p1[i]])]
    for s in (0.0, 1.0):
        rings = []
        for k in range(g.ProfileCount):
            c = g.Profile3d(k, s)
            if c is not None:
                q = A3(curve_pts(c)); rings.append(q[:-1] if np.allclose(q[0], q[-1]) else q)
        if rings and g.IsClosed(0) if hasattr(g, 'IsClosed') else rings:
            try: T += cap(rings)
            except Exception: pass
    return np.array(T) if T else np.zeros((0, 3, 3))

def tri_brep(g, n=24):
    T = []
    for i in range(len(g.Surfaces)):
        s = g.Surfaces[i]; du, dv = s.Domain(0), s.Domain(1)
        G = [[s.PointAt(du.T0 + (du.T1 - du.T0) * a / n, dv.T0 + (dv.T1 - dv.T0) * b / n) for b in range(n + 1)] for a in range(n + 1)]
        G = np.array([[[p.X, p.Y, p.Z] for p in row] for row in G])
        for a in range(n):
            for b in range(n):
                T += [G[[a, a + 1, a + 1], [b, b, b + 1]], G[[a, a + 1, a], [b, b + 1, b + 1]]]
    return np.array(T) if T else np.zeros((0, 3, 3))

m = r.File3dm.Read(IN)
LAY = {i: l for i, l in enumerate(m.Layers)}
def lname(o): return LAY[o.Attributes.LayerIndex].FullPath
def lcol(o):
    c = LAY[o.Attributes.LayerIndex].Color; return (c[0] / 255, c[1] / 255, c[2] / 255)
OBJ, CURVES = [], []
for o in m.Objects:
    g = o.Geometry; ln = lname(o)
    if not LAY[o.Attributes.LayerIndex].Visible: continue
    if isinstance(g, r.Mesh): T = tri_mesh(g)
    elif isinstance(g, r.Extrusion): T = tri_extrusion(g)
    elif isinstance(g, r.Brep): T = tri_brep(g)
    elif isinstance(g, r.Curve): CURVES.append((ln, A3(curve_pts(g, 96)))); continue
    else: continue
    if len(T): OBJ.append(dict(layer=ln, T=T, col=lcol(o)))
print('objects', len(OBJ), 'curves', len(CURVES))

def num(ln):
    mm_ = re.match(r'(\d+)', ln); return int(mm_.group(1)) if mm_ else -1
def kind(ln):
    n = num(ln)
    if any(k in ln for k in ('ガラス', '室内窓')) and 'ルーバー' not in ln: return 'glass'
    if n in (37, 39, 40, 46, 51, 75) or 'しつらえ' in ln: return 'furn'
    if n in (35,): return 'volume'
    if n in (11, 22, 17, 21, 24, 38, 18, 60, 70, 72, 25, 36, 10, 20): return 'struct'
    return 'other'

# ---------------------------------------------------------------- 切断
def slice_tris(T, p0, n):
    """三角形 T（N×3×3）を平面 (p0, n) で切った線分 → [(a, b)]"""
    d = (T - p0) @ n
    segs = []
    for tri, dd in zip(T, d):
        s = np.sign(np.where(np.abs(dd) < 1e-6, 1e-6, dd))
        if s.min() > 0 or s.max() < 0: continue
        pts = []
        for i in range(3):
            j = (i + 1) % 3
            if s[i] != s[j]:
                t = dd[i] / (dd[i] - dd[j]); pts.append(tri[i] + (tri[j] - tri[i]) * t)
        if len(pts) == 2: segs.append(pts)
    return segs

def poche(segs2d):
    if not segs2d: return None
    ls = [LineString(s) for s in segs2d if np.hypot(*(np.array(s[1]) - np.array(s[0]))) > 1e-3]
    if not ls: return None
    merged = unary_union(ls)
    polys = list(polygonize(merged))
    if not polys: return None
    # 入れ子（穴）は偶奇で
    polys.sort(key=lambda p: -p.area); out = None
    for p in polys:
        out = p if out is None else out.symmetric_difference(p)
    return out

def silhouette(T2):
    ps = [Polygon(t) for t in T2]
    ps = [p.buffer(0) for p in ps if p.is_valid and p.area > 1.0]
    if not ps: return None
    u = unary_union(ps)
    return u.buffer(0.5, join_style=2).buffer(-0.5, join_style=2)

def draw_geom(ax, geom, fc='white', ec='k', lw=0.13, ls='-', z=1, alpha=1.0):
    if geom is None or geom.is_empty: return
    for g in getattr(geom, 'geoms', [geom]):
        if g.geom_type != 'Polygon' or g.area < 1: continue
        verts, codes = [], []
        for ring in [g.exterior] + list(g.interiors):
            c = np.asarray(ring.coords); verts += c.tolist(); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=LW(lw), ls=ls, zorder=z, alpha=alpha, joinstyle='miter'))

def outline(ax, geom, ec='k', lw=0.13, ls='-', z=1):
    draw_geom(ax, geom, fc='none', ec=ec, lw=lw, ls=ls, z=z)

def cut_draw(ax, ob, pc, segs):
    """切断面：塗り＋切り口の線（閉じていないメッシュでも線は出る）"""
    k = kind(ob['layer'])
    lw_line = {'glass': 0.1, 'furn': 0.15, 'volume': 0.3}.get(k, 0.3)
    if k == 'glass': draw_geom(ax, pc, fc='white', ec='k', lw=0.1, z=5)
    elif k == 'furn': draw_geom(ax, pc, fc='0.6', ec='k', lw=0.13, z=5)
    elif k == 'volume': draw_geom(ax, pc, fc='white', ec='k', lw=0.3, z=5)
    else: draw_geom(ax, pc, fc='k', ec='k', lw=0.18, z=6)
    from matplotlib.collections import LineCollection
    if segs: ax.add_collection(LineCollection([np.asarray(q) for q in segs], colors='k', linewidths=LW(lw_line), zorder=6))

# ---------------------------------------------------------------- 用紙
def sheet(w_mm, h_mm, title):
    fig = plt.figure(figsize=(w_mm * MM, h_mm * MM))
    fig.text(1 - 15 / w_mm, 12 / h_mm, title, ha='right', va='bottom', fontsize=11)
    fig.text(1 - 15 / w_mm, 7 / h_mm, 'こどもたちの育ち舎　3dm（sodachiya_exact.3dm）から自動で作図', ha='right', va='bottom', fontsize=6.5, color='0.35')
    return fig

def axes_at(fig, w_mm, h_mm, x_mm, y_mm, ext, scale=100):
    """ext=(x0,x1,y0,y1) mm（モデル）を用紙の (x_mm, y_mm) から 1/scale で置く"""
    x0, x1, y0, y1 = ext
    ww, hh = (x1 - x0) / scale, (y1 - y0) / scale
    ax = fig.add_axes([x_mm / w_mm, y_mm / h_mm, ww / w_mm, hh / h_mm])
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.axis('off')
    return ax

def scalebar(ax, x, y, unit=1000, n=5):
    for i in range(n):
        ax.add_patch(plt.Rectangle((x + i * unit, y), unit, 150, fc='k' if i % 2 == 0 else 'white', ec='k', lw=LW(0.1)))
    for i in (0, n):
        ax.text(x + i * unit, y + 300, f'{i}', ha='center', va='bottom', fontsize=5)
    ax.text(x + n * unit + 300, y + 300, 'm', ha='left', va='bottom', fontsize=5)

# ---------------------------------------------------------------- 平面
ROOM_LAYERS = lambda ln: bool(re.match(r'^(3[1-4]|36|4[1-5]|5[2-46]|59)_', ln))
def room_name(ln):
    s = re.sub(r'^\d+[a-z]?_', '', ln); s = re.sub(r'^(1F|2F)_', '', s); return re.sub(r'（.*?）', '', s)

def plan(ax, zcut, objs, roofs_dashed, label_rooms, level_z):
    below, cut = [], []
    for ob in objs:
        z = ob['T'][:, :, 2]
        if z.min() >= zcut: continue
        if z.max() > zcut: cut.append(ob)
        below.append(ob)
    below.sort(key=lambda ob: ob['T'][:, :, 2].max())
    for ob in below:
        if ROOM_LAYERS(ob['layer']): continue
        sil = silhouette(ob['T'][:, :, :2])
        fc = 'white'
        if kind(ob['layer']) == 'glass': fc = 'none'
        draw_geom(ax, sil, fc=fc, ec='0.25', lw=0.1, z=2)
    for ob in cut:
        segs = slice_tris(ob['T'], np.array([0, 0, zcut]), np.array([0, 0, 1.]))
        S2 = [(s[0][:2], s[1][:2]) for s in segs]; pc = poche(S2)
        cut_draw(ax, ob, pc, S2)
    for ob in roofs_dashed:
        outline(ax, silhouette(ob['T'][:, :, :2]), ec='0.3', lw=0.1, ls=(0, (6, 3)), z=7)
    if label_rooms:
        for ob in objs:
            if not ROOM_LAYERS(ob['layer']): continue
            z = ob['T'][:, :, 2]
            if abs(z.max() - level_z) > 1200: continue
            sil = silhouette(ob['T'][:, :, :2])
            if sil is None: continue
            for g in getattr(sil, 'geoms', [sil]):
                if g.area < 4e6: continue
                p = g.representative_point()
                ax.text(p.x, p.y, f'{room_name(ob["layer"])}\n{g.area / 1e6:.1f} m²', ha='center', va='center',
                        fontsize=5.5, zorder=9, bbox=dict(fc='white', ec='none', pad=0.6, alpha=0.85))

def unwrap(a):
    """角度を π のまわりに（建物は中心の西、±π をまたぐので）"""
    return np.pi + ((np.asarray(a) - np.pi + np.pi) % (2 * np.pi) - np.pi)

def frames_from_columns():
    th = []
    for ob in OBJ:
        if ob['layer'].startswith('11a'):
            c = ob['T'].reshape(-1, 3)[:, :2].mean(0) - C; th.append(unwrap(math.atan2(c[1], c[0])))
    th = np.unique(np.round(np.sort(th), 4))
    return th
TH = frames_from_columns()
print('frames', len(TH))

def sec_line(theta, r0=187000, r1=218000):
    u = np.array([math.cos(theta), math.sin(theta)])
    return C + u * r0, C + u * r1

# 断面の位置：スパン s の中央（s=1..19 は南から）。TH は角度の小さい方から
TH_S = sorted(TH, key=lambda a: (C + 205000 * np.array([math.cos(a), math.sin(a)]))[1])   # 南（y 小）→ 北
SGN = 1.0 if TH_S[1] > TH_S[0] else -1.0
def theta_u(u_mm): return TH_S[0] + SGN * u_mm / 205000.0      # u：南の妻（架構 1）から北へ、r=205 m に沿って
# 断面：A は保育室の中ほど（r=197 m、v=8）を弧に沿って切って展開（西を見る）、B・C は架構に平行な鉛直面（北を見る）
SECTIONS = [('A', 'arc', 197000.0, '縦断（展開）：保育室の中ほど r=197 m、西を見る'),
            ('B', 'u', 21750.0, '海峡（スパン 8+0.75）：南の入口・キッチン・2 階・縁側'),
            ('C', 'u', 46500.0, '4 歳・遊戯室（スパン 16 の中央）')]

def objs_for_plan(level):
    o1 = []
    for ob in OBJ:
        n = num(ob['layer'])
        if ob['layer'].startswith('47'): continue
        if level == 1 and n in (41, 42, 43, 44, 45, 23): continue
        o1.append(ob)
    return o1

def make_plans():
    W_, H_ = 594, 841
    fig = sheet(W_, H_, '1 階平面図・西館 2 階平面図　1/100（A1）')
    objs1 = objs_for_plan(1)
    allp = np.vstack([ob['T'].reshape(-1, 3) for ob in objs1 if num(ob['layer']) < 70])
    x0, y0 = allp[:, :2].min(0) - 2000; x1, y1 = allp[:, :2].max(0) + 2000
    ext = (x0, x1, y0, y1)
    ax = axes_at(fig, W_, H_, 25, 40, ext)
    for ln, P in CURVES:
        if num(ln) >= 70 or num(ln) < 2: ax.plot(P[:, 0], P[:, 1], color='0.55', lw=LW(0.09), zorder=1)
    roofs = [ob for ob in OBJ if num(ob['layer']) in (10, 20)]
    plan(ax, 1200, objs1, roofs, True, 0)
    for nm, kind_, val, _ in SECTIONS:
        if kind_ == 'u':
            a, b = sec_line(theta_u(val))
            ax.plot([a[0], b[0]], [a[1], b[1]], color='k', lw=LW(0.13), ls=(0, (12, 3, 2, 3)), zorder=10)
            ends = (a, b)
        else:
            th = np.linspace(theta_u(-9000), theta_u(62000), 200)
            P = C + val * np.c_[np.cos(th), np.sin(th)]
            ax.plot(P[:, 0], P[:, 1], color='k', lw=LW(0.13), ls=(0, (12, 3, 2, 3)), zorder=10)
            ends = (P[0], P[-1])
        for q in ends:
            ax.text(*q, nm, ha='center', va='center', fontsize=8, zorder=11, bbox=dict(boxstyle='circle,pad=0.2', fc='white', ec='k', lw=0.5))
    scalebar(ax, x0 + 2000, y0 + 1000)
    ax.annotate('', xy=(x1 - 2500, y1 - 1500), xytext=(x1 - 2500, y1 - 5000), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='k'))
    ax.text(x1 - 2500, y1 - 1000, 'N', ha='center', va='bottom', fontsize=8)
    ax.text(x0 + 2000, y1 - 1500, '1 階平面図　FL+1200 で切断　1/100', fontsize=9, va='top')
    # 西館 2 階：右の空きに
    objs2 = [ob for ob in OBJ if not ob['layer'].startswith('47')]
    west = np.vstack([ob['T'].reshape(-1, 3) for ob in OBJ if num(ob['layer']) in (21, 23)])
    wx0, wy0 = west[:, :2].min(0) - 1500; wx1, wy1 = west[:, :2].max(0) + 1500
    used_w = (x1 - x0) / 100
    if 25 + used_w + 10 + (wx1 - wx0) / 100 < W_ - 10:
        ax2 = axes_at(fig, W_, H_, 25 + used_w + 10, H_ - 30 - (wy1 - wy0) / 100, (wx0, wx1, wy0, wy1))
    else:
        ax2 = axes_at(fig, W_, H_, W_ - 15 - (wx1 - wx0) / 100, H_ - 60 - (wy1 - wy0) / 100, (wx0, wx1, wy0, wy1))
    o2 = [ob for ob in objs2 if (ob['T'][:, :, :2].reshape(-1, 2).min(0) > [wx0, wy0]).all() and (ob['T'][:, :, :2].reshape(-1, 2).max(0) < [wx1, wy1]).all()]
    o2 = [ob for ob in o2 if ob['T'][:, :, 2].max() > 3000 or num(ob['layer']) in (21, 22, 25)]
    plan(ax2, 3250 + 1200, o2, [ob for ob in OBJ if num(ob['layer']) == 20], True, 3250)
    ax2.text(wx0, wy1, '西館 2 階平面図　2FL+1200 で切断　1/100', fontsize=9, va='bottom')
    return fig

# ---------------------------------------------------------------- 断面
def section(ax, theta, depth=3200):
    u_r = np.array([math.cos(theta), math.sin(theta), 0.])
    u_t = np.array([-math.sin(theta), math.cos(theta), 0.])
    if (C + 205000 * np.array([math.cos(theta + 0.01), math.sin(theta + 0.01)]))[1] < (C + 205000 * u_r[:2])[1]:
        u_t = -u_t                                       # 北（y の大きい方）を奥に
    p0 = np.array([C[0], C[1], 0.])
    X = lambda P: 205000 - (P - p0) @ u_r                # 西の外壁の線 r=205 m から東へ（右が東）
    D = lambda P: (P - p0) @ u_t
    far, cut = [], []
    for ob in OBJ:
        if ob['layer'].startswith('47') or num(ob['layer']) >= 76: continue
        T = ob['T']; P = T.reshape(-1, 3); d = D(P)
        if d.max() < 0 or d.min() > depth: continue
        if d.min() < 0 < d.max(): cut.append(ob)
        dt = D(T.reshape(-1, 3)).reshape(-1, 3)
        keep = (dt.max(1) >= 0) & (dt.min(1) <= depth)
        T2 = np.stack([X(T[keep].reshape(-1, 3)).reshape(-1, 3), T[keep][:, :, 2]], -1)
        if len(T2): far.append((max(0, d.min()), ob, T2))
    far.sort(key=lambda t: -t[0])
    for dmin, ob, T2 in far:
        k = kind(ob['layer'])
        draw_geom(ax, silhouette(T2), fc='none' if k == 'glass' else 'white', ec='0.3', lw=0.1, z=2)
    for ob in cut:
        segs = slice_tris(ob['T'], p0, u_t)
        S2 = [((X(s[0]), s[0][2]), (X(s[1]), s[1][2])) for s in segs]; pc = poche(S2)
        cut_draw(ax, ob, pc, S2)
    ax.plot([-17000, 17500], [-300, -300], color='k', lw=LW(0.35), zorder=8)    # GL

def section_arc(ax, Rc, depth=30000):
    """円筒面 r=Rc で切って展開。横＝u（南の妻から北へ、r=Rc の弧長）、西を見る（奥＝r の大きい方）"""
    def RTH(P):
        d = P[..., :2] - C; return np.hypot(d[..., 0], d[..., 1]), unwrap(np.arctan2(d[..., 1], d[..., 0]))
    X = lambda th: SGN * (th - TH_S[0]) * Rc
    far, cut = [], []
    for ob in OBJ:
        if ob['layer'].startswith('47') or num(ob['layer']) >= 76: continue
        T = ob['T']; rr, th = RTH(T)
        if rr.max() < Rc or rr.min() > Rc + depth: continue
        if rr.min() < Rc < rr.max(): cut.append((ob, rr, th))
        keep = rr.max(1) >= Rc
        T2 = np.stack([X(th[keep]), T[keep][:, :, 2]], -1)
        if len(T2): far.append((max(0, rr.min() - Rc), ob, T2))
    far.sort(key=lambda t: -t[0])
    for dmin, ob, T2 in far:
        k = kind(ob['layer'])
        draw_geom(ax, silhouette(T2), fc='none' if k == 'glass' else 'white', ec='0.3', lw=0.1, z=2)
    for ob, rr, th in cut:
        f = rr - Rc; segs = []
        for tri, ff, tt in zip(ob['T'], f, th):
            sg = np.sign(np.where(np.abs(ff) < 1e-6, 1e-6, ff))
            if sg.min() > 0 or sg.max() < 0: continue
            pts = []
            for i in range(3):
                j = (i + 1) % 3
                if sg[i] != sg[j]:
                    t = ff[i] / (ff[i] - ff[j]); pts.append((X(tt[i] + (tt[j] - tt[i]) * t), tri[i][2] + (tri[j][2] - tri[i][2]) * t))
            if len(pts) == 2: segs.append(pts)
        cut_draw(ax, ob, poche(segs), segs)
    ax.plot([-12000, 66000], [-300, -300], color='k', lw=LW(0.35), zorder=8)
    for k in range(1, 20):                      # スパン番号（南から）
        um = (k - 0.5) * 3000 * Rc / 205000
        ax.text(um, -900, f'{k}', ha='center', va='center', fontsize=5.5, color='0.3')
    ax.text(-1500, -900, 'スパン', ha='right', va='center', fontsize=5.5, color='0.3')

def make_sections():
    W_, H_ = 841, 594
    fig = sheet(W_, H_, '断面図 A（縦断・展開）・B・C　1/100（A1）')
    extA = (-10000, 62000, -1500, 10500)
    ax = axes_at(fig, W_, H_, 30, H_ - 45 - 120, extA)
    section_arc(ax, SECTIONS[0][2])
    ax.text(extA[0] + 300, extA[3] - 200, f'断面 A　{SECTIONS[0][3]}', fontsize=9, va='top')
    ax.text(extA[0] + 300, -1300, '← 南', fontsize=6); ax.text(extA[1] - 300, -1300, '北 →', fontsize=6, ha='right')
    extX = (-17000, 17500, -1500, 10500)
    for i, (nm, kind_, val, cap_) in enumerate(SECTIONS[1:]):
        ax = axes_at(fig, W_, H_, 30 + i * (345 + 25), H_ - 45 - 120 - 60 - 120, extX)
        section(ax, theta_u(val))
        ax.text(extX[0] + 300, extX[3] - 200, f'断面 {nm}　{cap_}　北を見る', fontsize=9, va='top')
        for z_, t_ in ((0, 'FL±0'), (-300, 'GL−300')):
            ax.text(extX[1] - 200, z_ + 60, t_, fontsize=5, ha='right', va='bottom')
        ax.text(extX[0] + 300, -1300, '← 西', fontsize=6); ax.text(extX[1] - 300, -1300, '東 →', fontsize=6, ha='right')
        if i == 0: scalebar(ax, extX[0] + 4000, -1300)
    return fig

for name, mk in (('sodachiya_plan_1-100', make_plans), ('sodachiya_sections_1-100', make_sections)):
    fig = mk()
    fig.savefig(os.path.join(OUTD, name + '.pdf'))
    fig.savefig(os.path.join(OUTD, name + '.png'), dpi=110)
    plt.close(fig); print('written', name)
