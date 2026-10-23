"""3dm（メッシュの版）から 1/100 の図をつくる：1 階平面（＋西館 2 階）、断面 3 つ（A 縦断・B 海峡・C 4 歳と遊戯室）、立面 4 つ
使い方: python3 draw100.py MODEL_MESH.3dm OUTDIR
- 平面：FL+1200 で切る。切れたものは塗り（構造・壁は黒、家具は灰、ガラスは細線）。
  見えがかりは近いもの（高いもの）から順に、手前の形で後ろの線を切って描く（隠れ線を消した線だけ）。
  屋根の外形と、2 階で切れる梁は破線。通り芯（架構 1〜20、W・E）、スパンの寸法、断面の位置、部屋名と面積。
- 立面：東・西・南・北を、平面と同じ向き（北が右）に回して正投影。建物だけ、見える面だけ（近いものから手前の形で後ろを切る）。
- 断面：A は円筒面 r=197 m で切って展開（西を見る）。B・C は架構に平行な鉛直面（北を見る）、奥 3.2 m まで。
  通り芯、幅の寸法、高さの記号（GL・FL・2FL・屋根・越屋根の蓋・西館の最高）。
出力：PDF・PNG と DXF（レイヤー分け、1/100 の図を 1:1 の mm で。Rhino・LayOut で開いて手を入れる用）。
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
        c0 = g.Profile3d(k, 0.0)
        if c0 is None: continue
        dvec = np.array([g.PathEnd.X - g.PathStart.X, g.PathEnd.Y - g.PathStart.Y, g.PathEnd.Z - g.PathStart.Z])
        p0 = A3(curve_pts(c0)); p1 = p0 + dvec           # まっすぐな押し出し：上の輪は下の輪を道の分だけ動かしたもの（始点のずれでねじれない）
        for i in range(len(p0) - 1):
            T += [np.array([p0[i], p0[i + 1], p1[i + 1]]), np.array([p0[i], p1[i + 1], p1[i]])]
    dvec = np.array([g.PathEnd.X - g.PathStart.X, g.PathEnd.Y - g.PathStart.Y, g.PathEnd.Z - g.PathStart.Z])
    for s in (0.0, 1.0):
        rings = []
        for k in range(g.ProfileCount):
            c = g.Profile3d(k, 0.0)
            if c is not None:
                q = A3(curve_pts(c)) + dvec * s; rings.append(q[:-1] if np.allclose(q[0], q[-1]) else q)
        if rings and g.IsClosed(0) if hasattr(g, 'IsClosed') else rings:
            try:
                # 輪の 0 番が外形、その中にある輪は穴。外にある輪（離れた別の形）は別に塞ぐ
                P_ = np.vstack(rings); mu_ = P_.mean(0); _, _, Vt_ = np.linalg.svd(P_ - mu_); B_ = Vt_[:2]
                pol = [Polygon((rg - mu_) @ B_.T).buffer(0) for rg in rings]
                inner = [rings[0]] + [rg for rg, pg in zip(rings[1:], pol[1:]) if pol[0].contains(pg.representative_point())]
                T += cap(inner)
                for rg, pg in zip(rings[1:], pol[1:]):
                    if not pol[0].contains(pg.representative_point()): T += cap([rg])
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
    if len(T): OBJ.append(dict(layer=ln, T=T, col=lcol(o), name=o.Attributes.Name or ''))
print('objects', len(OBJ), 'curves', len(CURVES))

def num(ln):
    mm_ = re.match(r'(\d+)', ln); return int(mm_.group(1)) if mm_ else -1
def kind(ln):
    n = num(ln)
    if n == 35 or 90 <= n <= 97: return 'volume'      # 園庭の小屋などは外形だけ（塗らない）
    if 80 <= n <= 88 or n == 55: return 'furn'
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
    if not polys:
        # 端の閉じていない板（屋根のメッシュは小口が無い）：上下 2 本の線の端をつないで閉じる
        lm = linemerge(merged) if merged.geom_type == 'MultiLineString' else merged
        gs = [g for g in getattr(lm, 'geoms', [lm]) if g.geom_type == 'LineString' and g.length > 60]     # 柱（幅約190）も閉じる（押し出しの小口の面が無く、平行な 2 本の線になる）
        if len(gs) == 2:
            a_, b_ = [np.asarray(g.coords) for g in gs]
            if np.hypot(*(a_[0] - b_[0])) > np.hypot(*(a_[0] - b_[-1])): b_ = b_[::-1]
            P = Polygon(np.vstack([a_, b_[::-1]])).buffer(0)
            if P.area > 0 and P.area < 1000 * max(gs[0].length, gs[1].length): return P
        return None
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

# ================================================================ ここから描画（draw100_core.py の後に続く）
# 図は PDF・PNG と DXF（レイヤー分け、1:1 の mm）を同時に出す。DXF は Rhino・LayOut で開いて手を入れる用。
import ezdxf, subprocess, datetime
from ezdxf.enums import TextEntityAlignment
from matplotlib.collections import LineCollection
from shapely.geometry import Point
from shapely import affinity as shp_affinity

KIND_BEAM = ('11b', '11c', '22b', '22c', '22d')
def is_beam(ln): return ln.split('_')[0] in KIND_BEAM

# DXF のレイヤー：名前 → (色 ACI, 線の太さ 1/100 mm, 線種)
DL = {
    '01_切断（構造・壁）': (7, 35, 'Continuous'),
    '02_切断（家具）': (8, 18, 'Continuous'),
    '03_切断（ガラス）': (5, 13, 'Continuous'),
    '04_切断（機械室などの塊）': (7, 35, 'Continuous'),
    '05_断熱（仮）': (2, 9, 'Continuous'),
    '10_見えがかり': (7, 13, 'Continuous'),
    '11_見えがかり（家具）': (8, 9, 'Continuous'),
    '12_見えがかり（ガラス）': (5, 9, 'Continuous'),
    '20_上部（屋根の外形・梁）': (8, 9, 'DASHED'),
    '30_敷地・外構': (8, 9, 'Continuous'),
    '40_通り芯': (1, 9, 'DASHDOT'),
    '41_通り芯の符号': (1, 13, 'Continuous'),
    '50_寸法': (3, 9, 'Continuous'),
    '51_高さ': (3, 9, 'Continuous'),
    '60_部屋名・面積': (7, 13, 'Continuous'),
    '70_断面の位置': (6, 13, 'DASHDOT'),
    '80_図名・縮尺・方位': (7, 18, 'Continuous'),
    '90_図枠': (7, 25, 'Continuous'),
}
PT2MM = 0.3528   # 1 pt = 0.3528 mm（紙の上）

def git_stamp():
    try:
        h = subprocess.run(['git', '-C', os.path.dirname(os.path.abspath(IN)), 'rev-parse', '--short', 'HEAD'],
                           capture_output=True, text=True).stdout.strip()
    except Exception: h = '?'
    t = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    return f'{t}（atelier {h} の次の版の 3dm）' if h else t
STAMP = git_stamp()

class Sheet:
    """用紙（mm）。DXF は用紙の 100 倍＝1/100 の図を 1:1 の mm で置く（Rhino で 1/100 のレイアウトにそのまま使える）"""
    def __init__(s, w, h, title, scale=100):
        s.w, s.h, s.k = w, h, scale
        s.fig = plt.figure(figsize=(w * MM, h * MM))
        s.doc = ezdxf.new('R2018', setup=True); s.msp = s.doc.modelspace()
        s.doc.header['$INSUNITS'] = 4      # mm
        for name, (c, lw, lt) in DL.items():
            s.doc.layers.add(name, color=c, lineweight=lw, linetype=lt)
        s.doc.styles.add('JP', font='NotoSansCJKjp-Regular.otf')
        k = s.k
        s.msp.add_lwpolyline([(0, 0), (w * k, 0), (w * k, h * k), (0, h * k)], close=True, dxfattribs={'layer': '90_図枠'})
        s.msp.add_lwpolyline([(10 * k, 10 * k), ((w - 10) * k, 10 * k), ((w - 10) * k, (h - 10) * k), (10 * k, (h - 10) * k)], close=True, dxfattribs={'layer': '90_図枠'})
        s.fig.patches.append(plt.Rectangle((10 / w, 10 / h), 1 - 20 / w, 1 - 20 / h, transform=s.fig.transFigure, fill=False, lw=LW(0.25), ec='k'))
        s.text_paper(w - 15, 18, title, 11, ha='right')
        s.text_paper(w - 15, 13, 'こどもたちの育ち舎　3dm（sodachiya_exact.3dm）から自動で作図　' + STAMP, 6.0, ha='right', color='0.35')
    def text_paper(s, x_mm, y_mm, t, pt, ha='left', va='bottom', color='k', layer='80_図名・縮尺・方位'):
        s.fig.text(x_mm / s.w, y_mm / s.h, t, ha=ha, va=va, fontsize=pt, color=color)
        dxf_text(s.msp, x_mm * s.k, y_mm * s.k, t, pt * PT2MM * s.k, layer, ha, va)
    def axes(s, x_mm, y_mm, ext):
        return Ax(s, x_mm, y_mm, ext)
    def save(s, base):
        s.fig.savefig(base + '.pdf'); s.fig.savefig(base + '.png', dpi=110); plt.close(s.fig)
        s.doc.saveas(base + '.dxf')

def dxf_text(msp, x, y, t, h, layer, ha='left', va='bottom', rot=0):
    att = {('left', 'top'): 1, ('center', 'top'): 2, ('right', 'top'): 3, ('left', 'center'): 4, ('center', 'center'): 5,
           ('right', 'center'): 6, ('left', 'bottom'): 7, ('center', 'bottom'): 8, ('right', 'bottom'): 9}[(ha, va)]
    mt = msp.add_mtext(t.replace('\n', '\\P'), dxfattribs={'layer': layer, 'style': 'JP', 'char_height': h * 0.75,
                                                          'attachment_point': att, 'rotation': rot})
    mt.dxf.insert = (x, y)

class Ax:
    """モデルの座標（mm）で描く。matplotlib と DXF の両方へ"""
    def __init__(s, sh, x_mm, y_mm, ext):
        s.sh = sh; x0, x1, y0, y1 = ext; k = sh.k
        s.ax = sh.fig.add_axes([x_mm / sh.w, y_mm / sh.h, (x1 - x0) / k / sh.w, (y1 - y0) / k / sh.h])
        s.ax.set_xlim(x0, x1); s.ax.set_ylim(y0, y1); s.ax.set_aspect('equal'); s.ax.axis('off')
        s.ox, s.oy = x_mm * k - x0, y_mm * k - y0
        s.phi = 0.0                       # モデルの座標をこの角度だけ回して描く（平面を建物の軸に合わせる）
    def rot(s, q):
        q = np.asarray(q, float)
        if s.phi == 0.0: return q
        c, n = math.cos(s.phi), math.sin(s.phi)
        return np.c_[q[..., 0] * c - q[..., 1] * n, q[..., 0] * n + q[..., 1] * c] if q.ndim == 2 else np.array([q[0] * c - q[1] * n, q[0] * n + q[1] * c])
    def P(s, x, y): return (x + s.ox, y + s.oy)
    def lines(s, segs, layer, lw=0.13, color='k', ls='-', z=3, raw=False):
        segs = [np.asarray(q, float) for q in segs if len(q) >= 2]
        if not raw: segs = [s.rot(q) for q in segs]
        if not segs: return
        s.ax.add_collection(LineCollection(segs, colors=color, linewidths=LW(lw), linestyles=ls, zorder=z, capstyle='butt'))
        for q in segs:
            s.sh.msp.add_lwpolyline([s.P(*p) for p in q], dxfattribs={'layer': layer})
    def geom_lines(s, g, layer, **kw):
        if g is None or g.is_empty: return
        segs = []
        for gg in getattr(g, 'geoms', [g]):
            if gg.geom_type in ('LineString', 'LinearRing'): segs.append(list(gg.coords))
            elif gg.geom_type == 'Polygon':
                segs += [list(gg.exterior.coords)] + [list(h.coords) for h in gg.interiors]
            elif hasattr(gg, 'geoms'):
                for g3 in gg.geoms:
                    if g3.geom_type in ('LineString', 'LinearRing'): segs.append(list(g3.coords))
        s.lines(segs, layer, **kw)
    def fill(s, g, layer, fc='k', z=4, hatch=None, seam=False):
        if g is None or g.is_empty: return
        if s.phi: g = shp_affinity.rotate(g, s.phi, origin=(0, 0), use_radians=True)
        for gg in getattr(g, 'geoms', [g]):
            if gg.geom_type != 'Polygon' or gg.area < 1: continue
            verts, codes = [], []
            for ring in [gg.exterior] + list(gg.interiors):
                c = np.asarray(ring.coords); verts += c.tolist(); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
            s.ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec='#777777' if hatch else (fc if seam else 'none'), lw=LW(0.05), hatch=hatch, zorder=z))
            if fc == 'w' and not hatch: continue                 # 白抜き（間仕切り）は DXF では塗らない（線だけ）
            h = s.sh.msp.add_hatch(color=7 if fc == 'k' else 8, dxfattribs={'layer': layer})
            if hatch: h.set_pattern_fill('ANSI31', scale=20.0)
            h.paths.add_polyline_path([s.P(*p) for p in list(gg.exterior.coords)[:-1]], is_closed=True, flags=1)
            for ring in gg.interiors:
                h.paths.add_polyline_path([s.P(*p) for p in list(ring.coords)[:-1]], is_closed=True, flags=0)
    def text(s, x, y, t, pt, layer, ha='center', va='center', rot=0, color='k', box=False, raw=False):
        kw = dict(bbox=dict(fc='white', ec='none', pad=0.5, alpha=0.85)) if box else {}
        if not raw and s.phi:                 # rot=0 の字（部屋名など）は紙の上で水平のまま、向きのある字だけ回す
            x, y = s.rot([x, y])
            if rot: rot = ((rot + math.degrees(s.phi)) + 90) % 180 - 90
        s.ax.text(x, y, t, ha=ha, va=va, fontsize=pt, rotation=rot, color=color, zorder=12, **kw)
        dxf_text(s.sh.msp, *s.P(x, y), t, pt * PT2MM * s.sh.k, layer, ha, va, rot)
    def bubble(s, x, y, t, layer='41_通り芯の符号', rad=450, pt=6.5):
        x, y = s.rot([x, y]); th = np.linspace(0, 2 * np.pi, 33)
        s.lines([np.c_[x + rad * np.cos(th), y + rad * np.sin(th)]], layer, lw=0.13, color='#B03030', z=11, raw=True)
        s.ax.add_patch(plt.Circle((x, y), rad, fc='white', ec='none', zorder=10.5))
        s.text(x, y, t, pt, layer, color='#B03030', raw=True)

# ---------------------------------------------------------------- 隠れ線（近いものから、手前の形で後ろの線を切る）
LAYER_OF = {'struct': ('01_切断（構造・壁）', '10_見えがかり'), 'other': ('01_切断（構造・壁）', '10_見えがかり'),
            'furn': ('02_切断（家具）', '11_見えがかり（家具）'), 'glass': ('03_切断（ガラス）', '12_見えがかり（ガラス）'),
            'volume': ('04_切断（機械室などの塊）', '10_見えがかり')}
def merged(segs, pc):
    """切り口の細かい線分をつなぐ（DXF で手を入れやすいように）。塗りがあればその輪郭、なければ線をつないだもの"""
    if pc is not None and not pc.is_empty:
        out = []
        for g in getattr(pc, 'geoms', [pc]):
            if g.geom_type == 'Polygon': out += [list(g.exterior.coords)] + [list(h.coords) for h in g.interiors]
        rest = unary_union([LineString(q) for q in segs if len(q) == 2 and np.hypot(*(np.subtract(q[1], q[0]))) > 1]).difference(pc.boundary.buffer(2)) if segs else None
    else:
        out, rest = [], unary_union([LineString(q) for q in segs if np.hypot(*(np.subtract(q[1], q[0]))) > 1e-3]) if segs else None
    if rest is not None and not rest.is_empty:
        rest = linemerge(rest) if rest.geom_type == 'MultiLineString' else rest
        for g in getattr(rest, 'geoms', [rest]):
            if g.geom_type == 'LineString' and g.length > 1: out.append(list(g.coords))
    return out

JOIN_CLOSE = 60          # 壁の角の欠け・すき間をふさぐ幅の半分（mm）。開口（800 以上）はふさがない
def wall_group(ob):
    """壁としてまとめて描くもの：構造・外壁・間仕切り（struct）と、しつらえの間仕切り・腰壁（38）"""
    k = kind(ob['layer'])
    n = num(ob['layer'])
    if n in (17, 21): return 'wall'                 # 外壁：黒く塗る
    if n in (24, 18, 38): return 'partition'        # 間仕切り（間柱＋スギ板の軽い壁、10-23夜の構法 A・B・C）：白抜きの二本線
    return None
def joined(polys):
    """同じ種類の壁の切り口をひとつにし、角の欠けとすき間を閉じる（設計監修 10-23：角で壁がぶつかるだけになっていた）"""
    g = unary_union([p.buffer(0) for p in polys if p is not None and not p.is_empty])
    if g.is_empty: return g
    return g.buffer(JOIN_CLOSE, join_style=2, mitre_limit=3).buffer(-JOIN_CLOSE, join_style=2, mitre_limit=3).union(g)

def draw_cut(A, items, insul=False):
    """items=[(ob, poche, segs)] → 塗りと切り口。返り値＝隠す形（ガラス以外）
    壁（外壁・間仕切り・しつらえの間仕切り）は種類ごとにひとつにまとめて、角をつないだ輪郭を一本で描く。"""
    occ = []
    groups = {}
    for ob, pc, segs in items:
        gname = wall_group(ob)
        if gname and pc is not None and not pc.is_empty: groups.setdefault(gname, []).append(pc)
    GW = {gname: joined(polys) for gname, polys in groups.items()}
    if 'wall' in GW and 'partition' in GW:         # 角をつなぐのは外壁と間仕切りをいっしょに（間仕切りは外壁に突き当たる）
        d_ = joined(groups['wall'] + groups['partition']).difference(GW['wall'])
        GW['partition'] = unary_union([x for x in getattr(d_, 'geoms', [d_]) if x.geom_type in ('Polygon', 'MultiPolygon') and x.area > 100])
    lay = LAYER_OF['struct'][0]
    if 'partition' in GW:
        g = GW['partition']
        A.fill(g, lay, fc='w', z=5.5)
        edge = g.boundary.difference(GW['wall'].buffer(1)) if 'wall' in GW else g.boundary
        A.geom_lines(edge, lay, lw=0.2, z=6.2)
        occ.append(g)
    if 'wall' in GW:
        g = GW['wall']; A.fill(g, lay, fc='k', z=6); A.geom_lines(g.boundary, lay, lw=0.25, z=6); occ.append(g)
    for ob, pc, segs in items:
        k = kind(ob['layer']); lay = LAYER_OF[k][0]
        grouped = wall_group(ob) is not None and pc is not None and not pc.is_empty
        segs = merged(segs, pc)
        if grouped:
            pass
        elif k == 'glass':
            A.lines(segs, lay, lw=0.1, z=6)
        elif k == 'furn':
            A.fill(pc, lay, fc='0.62', z=5); A.lines(segs, lay, lw=0.15, z=6)
        elif k == 'volume':
            A.lines(segs, lay, lw=0.3, z=6)
        else:
            A.fill(pc, lay, fc='k', z=6); A.lines(segs, lay, lw=0.25, z=6)
        if pc is not None and k != 'glass': occ.append(pc.buffer(0))
        n = num(ob['layer'])
        if insul and re.match(r'^(10|20)_', ob['layer']) and segs:   # 屋根の本体だけ（10t・10p などの光の筋・太陽光の面には描かない）      # 屋根（3dm では厚みの無い面）：面の下 50〜200 に断熱（垂木の間 150、仮）
            ls_ = unary_union([LineString(q) for q in segs if len(q) >= 2])
            ls_ = linemerge(ls_) if ls_.geom_type == 'MultiLineString' else ls_
            bands = []
            for g in getattr(ls_, 'geoms', [ls_]):
                if g.geom_type != 'LineString' or g.length < 1000: continue
                bands.append(shp_affinity.translate(g, 0, -125).buffer(75, cap_style=2, join_style=2))
            if bands:
                bb = unary_union(bands); xc = getattr(A, 'insul_x', None)          # 軒の出（外）は除く
                if xc: bb = bb.intersection(box(xc[0], -1e5, xc[1], 1e5))
                A.fill(bb, '05_断熱（仮）', fc='#F3D98B', z=6.5, hatch='////')
        if insul and pc is not None and not pc.is_empty:
            band = None
            if False:
                pass
            elif n in (17, 21):                    # 外壁：壁の中（両面 25 を残して）
                band = pc.buffer(-25)
            elif n in (12, 15):                    # 床：スラブの下 50（仮）
                band = shp_affinity.translate(pc, 0, -50).difference(pc.buffer(1))
            if band is not None and not band.is_empty and band.area > 1e4:
                A.fill(band, '05_断熱（仮）', fc='#F3D98B', z=6.5, hatch='////')
    return unary_union(occ) if occ else None

def draw_visible(A, items, occ):
    """items=[(ob, silhouette)] 近い順。見える線だけ描く"""
    occ = occ if occ is not None else Polygon()
    for i, (ob, sil) in enumerate(items):
        if sil is None or sil.is_empty: continue
        k = kind(ob['layer']); lay = LAYER_OF[k][1]
        vis = sil.boundary.difference(occ.buffer(2)) if not occ.is_empty else sil.boundary
        A.geom_lines(vis, lay, lw={'furn': 0.1, 'glass': 0.09}.get(k, 0.13), color={'glass': '#3d6f9a', 'furn': '0.25'}.get(k, 'k'), z=3)
        if k != 'glass':
            occ = unary_union([occ, sil]) if not occ.is_empty else sil
            if i % 40 == 39: occ = occ.simplify(1)
    return occ

# ---------------------------------------------------------------- 平面
ROOM_LAYERS = lambda ln: bool(re.match(r'^(3[1-4]|36|4[1-5]|5[2-47]|59)[a-z]?_', ln))
def room_name(ln):
    s = re.sub(r'^\d+[a-z]?_', '', ln); s = re.sub(r'^(1F|2F)_', '', s); return re.sub(r'（.*?）', '', s)

def plan(A, zcut, objs, overhead, level_z):
    below, cut, swings, stairs = [], [], [], []
    for ob in objs:
        if ROOM_LAYERS(ob['layer']): continue
        if ob['layer'].startswith('19d') and '開き戸' in ob.get('name', ''): swings.append(ob); continue   # 開き戸は開いた形と弧で（下）
        if num(ob['layer']) == 25: stairs.append(ob); continue                                                   # 階段は踏面の線と矢印で（下）
        z = ob['T'][:, :, 2]
        if num(ob['layer']) == 94 and z.max() > zcut: overhead.append(ob); continue   # 園庭の木：樹冠を破線で
        if z.min() >= zcut: continue
        if z.max() > zcut and is_beam(ob['layer']): overhead.append(ob); continue      # 梁は上部（破線）
        if z.max() > zcut: cut.append(ob)
        else: below.append(ob)
    items = []
    for ob in cut:
        segs = slice_tris(ob['T'], np.array([0, 0, zcut]), np.array([0, 0, 1.]))
        S2 = [(s[0][:2], s[1][:2]) for s in segs]; items.append((ob, poche(S2), S2))
    occ = draw_cut(A, items)
    below.sort(key=lambda ob: -ob['T'][:, :, 2].max())
    draw_visible(A, [(ob, silhouette(ob['T'][:, :, :2])) for ob in below], occ)
    for ob in overhead:
        A.geom_lines(silhouette(ob['T'][:, :, :2]), '20_上部（屋根の外形・梁）', lw=0.09, color='0.4', ls=(0, (6, 3)), z=7)
    # 階段：踏面の輪郭（切断より下は実線、上は破線）、上り口からの矢印と「上」（2 階では降り口から「下」）
    for ob in stairs:
        T = ob['T']; flat = [t for t in T if np.ptp(t[:, 2]) < 1]
        lv = {}
        for t in flat: lv.setdefault(round(t[0, 2]), []).append(Polygon(t[:, :2]).buffer(0.5))
        steps = []
        for zz in sorted(lv):
            g = unary_union(lv[zz]).buffer(-0.5)
            if g.is_empty or g.area < 5e4: continue
            steps.append((zz, g))
            on2 = level_z > 1000
            if on2 or zz + 180 <= zcut: A.geom_lines(g.boundary, '45_階段', lw=0.1, z=6)
            elif zz <= zcut + 400: A.geom_lines(g.boundary, '45_階段', lw=0.08, color='0.4', ls=(0, (4, 2)), z=6)
        if len(steps) >= 3:
            path = np.array([np.array(g.centroid.coords[0]) for zz, g in steps if g.area < 1.0e6])
            if level_z > 1000:
                path = path[::-1]; lab = '下'
            else:
                lab = '上'
                # 切断の線（踏面の途中を斜めに切る）
                k = max(1, sum(1 for zz, g in steps if zz <= zcut) - 1)
                gk = steps[k][1]; c0 = np.array(gk.centroid.coords[0]); bb = np.array(gk.minimum_rotated_rectangle.exterior.coords)[:4]
                A.lines([[bb[0] + (bb[2] - bb[0]) * 0.15, bb[2] - (bb[2] - bb[0]) * 0.15]], '45_階段', lw=0.18, z=7)
            A.lines([path], '45_階段', lw=0.13, z=7)
            d_ = path[-1] - path[-2]; d_ = d_ / max(np.linalg.norm(d_), 1e-6); nn = np.array([-d_[1], d_[0]])
            A.lines([[path[-1] - d_ * 250 + nn * 120, path[-1], path[-1] - d_ * 250 - nn * 120]], '45_階段', lw=0.13, z=7)
            A.text(path[0][0], path[0][1], lab, 5.5, '45_階段', box=True)
    # 吹抜（2 階）：西館の 1 階の部屋の上で、2 階の床の無い所。対角の細い線と「吹抜」
    if level_z > 1000:
        f1 = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if re.match(r'^(31|32|33|34|36|57)_', ob['layer'])]
        f2 = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if re.match(r'^(23|25)_', ob['layer'])]
        f1 = unary_union([g for g in f1 if g is not None]); f2 = unary_union([g for g in f2 if g is not None])
        void = f1.difference(f2.buffer(30))
        for g in getattr(void, 'geoms', [void]):
            if g.geom_type != 'Polygon' or g.area < 3e6: continue
            mr = np.array(g.minimum_rotated_rectangle.exterior.coords)[:4]
            for a_, b_ in ((mr[0], mr[2]), (mr[1], mr[3])):
                A.geom_lines(LineString([a_, b_]).intersection(g), '45_吹抜', lw=0.07, color='0.45', z=5)
            from shapely.ops import polylabel as _pl
            q = _pl(g, 50)
            A.text(q.x, q.y, '吹抜' + ('（遊戯室）' if g.area > 50e6 else ''), 6, '45_吹抜', box=True)
    # 開き戸：開いた位置の板（90°）と、閉じた位置からの弧（3dm の戸の板の名前に吊元と開く向き、add_inner.py）
    for ob in swings:
        if abs(ob['T'][:, :, 2].min() - level_z) > 600: continue
        mm_ = re.search(r'W(\d+) 吊元 (-?[\d.]+),(-?[\d.]+) 開く (-?[\d.]+),(-?[\d.]+)', ob['name'])
        if not mm_: continue
        Wd = float(mm_.group(1)); hp = np.array([float(mm_.group(2)), float(mm_.group(3))]); od = np.array([float(mm_.group(4)), float(mm_.group(5))])
        P_ = ob['T'][:, :, :2].reshape(-1, 2); far = P_[np.argmax(np.linalg.norm(P_ - hp, axis=1))]
        cd = (far - hp) / max(np.linalg.norm(far - hp), 1e-6)
        R_ = Wd - 10
        arc = [hp + (cd * math.cos(t_) + od * math.sin(t_)) * R_ for t_ in np.linspace(0, math.pi / 2, 30)]
        A.lines([np.array(arc)], '40_建具', lw=0.08, color='0.25', z=6)
        leaf = Polygon([hp - cd * 18, hp + cd * 18, hp + cd * 18 + od * R_, hp - cd * 18 + od * R_])
        A.fill(leaf, '40_建具', fc='k', z=6)
    # 部屋名と面積（床の板から、壁芯。面積表 areas.py と同じ数え方：その階の床から 2.4 m までにある壁を除き、接する壁の半分を足す）
    WL = []
    for ob in objs:
        ln = ob['layer']
        if not re.match(r'^(17|21|24|38)_', ln): continue
        z = ob['T'][:, :, 2]
        if ln.startswith('38_') and z.max() - z.min() < 2000: continue
        if z.min() < level_z + 2400 and z.max() > level_z + 100:
            fp = silhouette(ob['T'][:, :, :2])
            if fp is not None: WL.append(fp)
    W_LV = unary_union(WL) if WL else None
    BYL = {}                                     # 同じ部屋（レイヤー）の床の板はまとめてから名前を付ける（足した床の帯に別の名前が付かないように）
    for ob in objs:
        if not ROOM_LAYERS(ob['layer']): continue
        if abs(ob['T'][:, :, 2].max() - level_z) > 1200: continue
        sil = silhouette(ob['T'][:, :, :2])
        if sil is not None and not sil.is_empty: BYL.setdefault(ob['layer'], []).append(sil.buffer(5, join_style=2))
    # 面積は面積表（areas.py → sodachiya_areas.json）の数を使う（図と表を必ず一致させる）。表に無いときと、一つのレイヤーに部屋が二つ以上あるときは同じ数え方でここで測る
    TAB = {}
    try:
        import json as _json
        TAB = _json.load(open(os.path.join(OUTD, 'sodachiya_areas.json'), encoding='utf-8')).get('layers', {})
    except Exception:
        TAB = {}
    for ln_, sils in BYL.items():
        ob = {'layer': ln_}
        sil = unary_union(sils).buffer(-5, join_style=2)
        parts = [g for g in getattr(sil, 'geoms', [sil]) if g.area >= 4e6]
        for g in parts:
            a = g.area
            if W_LV is not None:
                inner = g.difference(W_LV); a = inner.area + 0.5 * W_LV.intersection(inner.buffer(250)).area
            if len(parts) == 1 and ln_ in TAB: a = TAB[ln_] * 1e6
            from shapely.ops import polylabel as _pl
            p = _pl(g.buffer(-150) if g.buffer(-150).geom_type == 'Polygon' and not g.buffer(-150).is_empty else g, 20)   # 壁からいちばん遠い点（線に重ならない）
            nm_ = room_name(ob["layer"])
            # 字の幅（1/100、5.5pt ≒ 1 字 0.19 m）が部屋の短い方の幅の 8 割を超えたら「・」で折る
            mr_ = np.array(g.minimum_rotated_rectangle.exterior.coords); wmin = min(np.linalg.norm(mr_[1] - mr_[0]), np.linalg.norm(mr_[2] - mr_[1]))
            if len(nm_) * 190 > 0.8 * wmin and '・' in nm_:
                i_ = nm_.index('・', len(nm_) // 3) if '・' in nm_[len(nm_) // 3:] else nm_.index('・')
                nm_ = nm_[:i_ + 1] + '\n' + nm_[i_ + 1:]
            A.text(p.x, p.y, f'{nm_}\n{a / 1e6:.1f} m²', 5.5, '60_部屋名・面積', box=True)

def unwrap(a):
    """角度を π のまわりに（建物は中心の西、±π をまたぐので）"""
    return np.pi + ((np.asarray(a) - np.pi + np.pi) % (2 * np.pi) - np.pi)

def frames_from_columns():
    th = []
    for ob in OBJ:
        if ob['layer'].startswith('11a'):
            c = ob['T'].reshape(-1, 3)[:, :2].mean(0) - C; th.append(float(unwrap(math.atan2(c[1], c[0]))))
    return np.unique(np.round(np.sort(th), 4))
TH = frames_from_columns()
TH_S = sorted(TH, key=lambda a: (C + 205000 * np.array([math.cos(a), math.sin(a)]))[1])   # 架構 1（南の妻）→ 20（北の端）
SGN = 1.0 if TH_S[1] > TH_S[0] else -1.0
def theta_u(u_mm): return TH_S[0] + SGN * u_mm / 205000.0      # u：南の妻から北へ、r=205 m に沿って
def at(r_, th): return C + r_ * np.array([math.cos(th), math.sin(th)])
print('frames', len(TH))

SECTIONS = [('A', 'arc', 197000.0, '縦断（展開）　保育室の中ほど r=197 m の弧で切って平らに伸ばす、西を見る'),
            ('B', 'u', 21750.0, '海峡（スパン 8+0.75）　南の入口・キッチン・2 階・すき間・本館・縁側、北を見る'),
            ('C', 'u', 42600.0, '4 歳・遊戯室の摺鉢ネット（スパン 15+0.6）　北を見る')]

def plan_grid(A):
    """通り芯：架構 1〜20（放射）と W（西の柱 r=205 m）・E（東の柱 r=193 m）、スパンの寸法"""
    for k, th in enumerate(TH_S, 1):
        a, b = at(188200, th), at(207600, th)
        A.lines([[a, b]], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
        A.bubble(*at(186900, th), str(k))
    for nm, rr in (('W', 205000), ('E', 193000)):
        ths = np.linspace(theta_u(-1500), theta_u(58500), 120)
        A.lines([np.array([at(rr, t) for t in ths])], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
        A.bubble(*at(rr, theta_u(-2200)), nm)
    # スパンの寸法（背骨 r=205 m で 3,000）
    rd = 185300
    for k in range(19):
        t0, t1 = TH_S[k], TH_S[k + 1]
        A.lines([np.array([at(rd, t) for t in np.linspace(t0, t1, 8)])], '50_寸法', lw=0.09, color='#2E7D32')
        for t in (t0, t1): A.lines([[at(rd - 250, t), at(rd + 250, t)]], '50_寸法', lw=0.09, color='#2E7D32')
        p = at(rd - 450, (t0 + t1) / 2)
        ang = math.degrees((t0 + t1) / 2) + 90
        A.text(p[0], p[1], '3,000', 4.5, '50_寸法', rot=((ang + 90) % 180) - 90, color='#2E7D32')
    p = at(rd - 1300, (TH_S[0] + TH_S[-1]) / 2)
    A.text(p[0], p[1], '19 × 3,000 = 57,000（背骨 r=205 m で）', 5.5, '50_寸法', rot=((math.degrees((TH_S[0] + TH_S[-1]) / 2) + 180) % 180) - 90, color='#2E7D32')

def plan_vdims(A):
    """本館の幅の寸法（南の妻の外、放射の向き）：西の外壁の外面・W 通り・西吹き抜け・E 通り・内縁側・軒先"""
    th = theta_u(-4300)
    vs = [-0.35, 0.0, 1.6, 12.0, 13.5, 15.0]
    pts = [at(205000 - v * 1000, th) for v in vs]
    A.lines([[pts[0], pts[-1]]], '50_寸法', lw=0.09, color='#2E7D32')
    d_ = (pts[-1] - pts[0]) / np.linalg.norm(pts[-1] - pts[0]); nn = np.array([-d_[1], d_[0]])
    for q in pts: A.lines([[q - nn * 250, q + nn * 250]], '50_寸法', lw=0.09, color='#2E7D32')
    ang = math.degrees(math.atan2(d_[1], d_[0]))
    for v0, v1, q0, q1 in zip(vs, vs[1:], pts, pts[1:]):
        mid = (q0 + q1) / 2 + nn * 450 * (1 if (v1 - v0) > 1 else 2.2)
        A.text(mid[0], mid[1], f'{round((v1 - v0) * 1000):,}', 4.5, '50_寸法', rot=((ang + 90) % 180) - 90, color='#2E7D32')
    q = (pts[0] + pts[-1]) / 2 - nn * 900
    A.text(q[0], q[1], f'{round((vs[-1] - vs[0]) * 1000):,}（西の外壁の外面〜軒先）', 5, '50_寸法', rot=((ang + 90) % 180) - 90, color='#2E7D32')

def plan_section_marks(A):
    for nm, kind_, val, _ in SECTIONS:
        if kind_ == 'u':
            th = theta_u(val); a, b = at(184000, th), at(222000, th)
            A.lines([[a, b]], '70_断面の位置', lw=0.13, ls=(0, (12, 3, 2, 3)), z=10)
            tdir = at(205000, theta_u(val + 1)) - at(205000, th); tdir /= np.linalg.norm(tdir)
            ends = (a, b)
        else:
            ths = np.linspace(theta_u(-9000), theta_u(62000), 200)
            P = np.array([at(val, t) for t in ths])
            A.lines([P], '70_断面の位置', lw=0.13, ls=(0, (12, 3, 2, 3)), z=10)
            ends = (P[0], P[-1])
        for q in ends:
            if kind_ == 'arc':
                d = q - C; tdir = -d / np.linalg.norm(d)      # 西（r の大きい方）を見る
                tdir = d / np.linalg.norm(d)
            A.lines([[q, q + tdir * 1600]], '70_断面の位置', lw=0.35, z=11)
            A.lines([[q + tdir * 1600 + np.array([-tdir[1], tdir[0]]) * 300, q + tdir * 2100, q + tdir * 1600 - np.array([-tdir[1], tdir[0]]) * 300]], '70_断面の位置', lw=0.35, z=11)
            A.text(q[0], q[1], nm, 8, '70_断面の位置', box=True)

def objs_for_plan(level):
    out = []
    for ob in OBJ:
        n = num(ob['layer'])
        if ob['layer'].startswith('47'): continue
        if level == 1 and n in (41, 42, 43, 44, 45, 23): continue
        if n in (90, 98): continue                     # 園庭の地形のメッシュは平面では描かない（等高線 91 で）
        if n in (3, 4): continue                       # 周辺（PLATEAU）は plan_context で外形だけ
        out.append(ob)
    return out

def plan_phi():
    """平面を回す角度：建物の軸（u、北）を右へ。園庭（東）が下に来る"""
    t = at(205000, theta_u(55000)) - at(205000, theta_u(5000)); return -math.atan2(t[1], t[0])
PHI = plan_phi()
def rot_pts(P):
    c, n = math.cos(PHI), math.sin(PHI); P = np.asarray(P)[:, :2]; return np.c_[P[:, 0] * c - P[:, 1] * n, P[:, 0] * n + P[:, 1] * c]

def plan_context(A, ext):
    """周辺の道路（03）と建物（04、PLATEAU）を紙の範囲の中だけ細い線で（回した後の範囲 ext で切る）"""
    from shapely.geometry import box as _box
    clip = shp_affinity.rotate(_box(ext[0], ext[2], ext[1], ext[3]), -PHI, origin=(0, 0), use_radians=True)
    for ob in OBJ:
        n = num(ob['layer'])
        if n not in (3, 4): continue
        sil = silhouette(ob['T'][:, :, :2])
        if sil is None: continue
        sil = sil.intersection(clip)
        if sil.is_empty: continue
        if n == 4: A.fill(sil, '30_敷地・外構', fc='0.9', z=0.5); A.geom_lines(sil, '30_敷地・外構', lw=0.07, color='0.5', z=0.6)
        else: A.geom_lines(sil, '30_敷地・外構', lw=0.05, color='0.65', z=0.6)

def make_plans():
    """A1 横。建物の軸に合わせて回す（北が右、園庭が下）。上の方位の矢印が本当の北"""
    W_, H_ = 841, 594
    S = Sheet(W_, H_, '1 階平面図・西館 2 階平面図　1/100（A1）　建物の軸に合わせて回してある（北は方位の矢印）')
    objs1 = objs_for_plan(1)
    allp = rot_pts(np.vstack([ob['T'].reshape(-1, 3) for ob in objs1 if 4 < num(ob['layer']) < 70 or num(ob['layer']) in (0, 1)]))
    x0, y0 = allp.min(0) - 2000; x1, y1 = allp.max(0) + 2000
    y0 -= 2500                                     # 東（下）の通り芯の符号と寸法の分
    gx0 = (W_ - (x1 - x0) / 100) / 2
    A = S.axes(max(15, gx0), 25, (x0, x1, y0, y1)); A.phi = PHI
    for ln, P in CURVES:
        if num(ln) in (94, 98): continue
        if num(ln) == 91: A.lines([P[:, :2]], '30_敷地・外構', lw=0.05, color='0.7', z=1); continue
        if num(ln) == 92: A.lines([P[:, :2]], '30_敷地・外構', lw=0.13, color='#3d6f9a', z=1); continue
        if num(ln) >= 70 or num(ln) < 2: A.lines([P[:, :2]], '30_敷地・外構', lw=0.09, color='0.55', z=1)
    plan_context(A, (x0, x1, y0, y1))
    roofs = [ob for ob in OBJ if num(ob['layer']) in (10, 20)]
    plan(A, 1200, objs1, list(roofs), 0)
    plan_grid(A); plan_vdims(A); plan_section_marks(A)
    # 縮尺・方位（紙の上の座標＝回した後の座標で）
    for i in range(5):
        A.ax.add_patch(plt.Rectangle((x0 + 2000 + i * 1000, y0 + 1000), 1000, 150, fc='k' if i % 2 == 0 else 'white', ec='k', lw=LW(0.1), zorder=12))
    A.text(x0 + 2000, y0 + 1500, '0', 5, '80_図名・縮尺・方位', raw=True); A.text(x0 + 7000, y0 + 1500, '5 m', 5, '80_図名・縮尺・方位', raw=True)
    nd = np.array([-math.sin(PHI), math.cos(PHI)])      # 本当の北（モデルの +y）を回したもの
    pd = np.array([-nd[1], nd[0]]); c0 = np.array([x0 + 3500, y1 - 5500])
    A.lines([[c0 - nd * 1700, c0 + nd * 1700]], '80_図名・縮尺・方位', lw=0.25, raw=True)
    A.lines([[c0 + nd * 1100 + pd * 300, c0 + nd * 1700, c0 + nd * 1100 - pd * 300]], '80_図名・縮尺・方位', lw=0.25, raw=True)
    q = c0 + nd * 2300; A.text(q[0], q[1], 'N', 8, '80_図名・縮尺・方位', raw=True)
    A.text(x0 + 2000, y1 - 1000, '1 階平面図　FL+1200 で切断　1/100　（右が北の端、下が園庭）', 9, '80_図名・縮尺・方位', ha='left', va='top', raw=True)
    # 西館 2 階：上の空きに（同じ向き）
    west = rot_pts(np.vstack([ob['T'].reshape(-1, 3) for ob in OBJ if num(ob['layer']) in (21, 23)]))
    wx0, wy0 = west.min(0) - 1500; wx1, wy1 = west.max(0) + 1500
    gy = 25 + (y1 - y0) / 100 + 8
    if gy + (wy1 - wy0) / 100 > H_ - 25: gy = H_ - 25 - (wy1 - wy0) / 100
    A2 = S.axes(max(15, gx0) + (wx0 - x0) / 100, gy, (wx0, wx1, wy0, wy1)); A2.phi = PHI
    o2 = [ob for ob in OBJ if not ob['layer'].startswith('47') and num(ob['layer']) not in (90, 94, 98)]
    def inside(ob):
        q = rot_pts(ob['T'].reshape(-1, 3)); return (q.min(0) > [wx0, wy0]).all() and (q.max(0) < [wx1, wy1]).all()
    o2 = [ob for ob in o2 if inside(ob)]
    o2 = [ob for ob in o2 if ob['T'][:, :, 2].max() > 3000 or num(ob['layer']) in (21, 22, 25)]
    plan(A2, 3250 + 1200, o2, [ob for ob in OBJ if num(ob['layer']) == 20], 3250)
    A2.text(wx0, wy1, '西館 2 階平面図　2FL+1200 で切断　1/100（梁は破線）', 9, '80_図名・縮尺・方位', ha='left', va='bottom', raw=True)
    return S

# ---------------------------------------------------------------- 断面
def levels(A, cutb, x_text, has_west):
    """高さの記号。cutb：レイヤー → 切断面の (xmin, zmin, xmax, zmax)"""
    L = [('GL', -300), ('FL', 0)]
    if has_west: L.append(('2FL', 3250))
    def zmax(prefixes, xmin=None):
        zs = [b[3] for k, b in cutb.items() if k.startswith(prefixes) and (xmin is None or b[2] > xmin)]
        return max(zs) if zs else None
    z = zmax(('10_',)); z and L.append(('本館 屋根の最高', z))
    z = zmax(('50a',)); z and L.append(('本館 越屋根の蓋', z))
    if has_west:
        z = zmax(('20_', '28_')); z and L.append(('西館 最高', z))
    L.sort(key=lambda t: t[1]); last = -1e9
    for nm, z in L:
        zt = max(z, last + 420); last = zt
        A.lines([[(x_text - 300, z), (x_text, z + 260), (x_text - 600, z + 260), (x_text - 300, z)]], '51_高さ', lw=0.1, color='#2E7D32')
        A.lines([[(x_text - 900, z), (x_text + 200, z)]], '51_高さ', lw=0.09, color='#2E7D32')
        A.text(x_text + 300, zt + 60, f'{nm}　{"+" if z > 0 else "±" if z == 0 else "−"}{abs(z):,.0f}', 5, '51_高さ', ha='left', va='bottom', color='#2E7D32')

def chain_dims(A, xs, y, label_fmt='{:,.0f}'):
    xs = sorted(xs)
    A.lines([[(xs[0], y), (xs[-1], y)]], '50_寸法', lw=0.09, color='#2E7D32')
    for x in xs: A.lines([[(x, y - 200), (x, y + 200)]], '50_寸法', lw=0.09, color='#2E7D32')
    for a, b in zip(xs, xs[1:]):
        if b - a > 300: A.text((a + b) / 2, y + 150, label_fmt.format(b - a), 4.8, '50_寸法', va='bottom', color='#2E7D32')

def section_u(A, theta, depth=3200):
    u_r = np.array([math.cos(theta), math.sin(theta), 0.])
    u_t = np.array([-math.sin(theta), math.cos(theta), 0.])
    if at(205000, theta + 0.01)[1] < at(205000, theta)[1]: u_t = -u_t      # 北を奥に
    p0 = np.array([C[0], C[1], 0.])
    X = lambda P: 205000 - (P - p0) @ u_r                # v（西の外壁の線 r=205 m から東へ、mm）、右が東
    D = lambda P: (P - p0) @ u_t
    far, cuts = [], []
    for ob in OBJ:
        if ob['layer'].startswith('47') or num(ob['layer']) in (76, 77) or 91 <= num(ob['layer']) <= 98 or num(ob['layer']) in (3, 4): continue   # 園庭の木・小屋は断面に出さない（園庭の断面は園庭のチャット）
        T = ob['T']; d = D(T.reshape(-1, 3)).reshape(-1, 3)
        if d.max() < 0 or d.min() > depth: continue
        if d.min() < 0 < d.max():
            segs = slice_tris(T, p0, u_t)
            S2 = [((X(s[0]), s[0][2]), (X(s[1]), s[1][2])) for s in segs]
            cuts.append((ob, poche(S2), S2))
        if num(ob['layer']) in (2, 90): continue              # 川の護岸・園庭の地形は切り口だけ（見えがかりは長くなりすぎる）
        keep = (d.max(1) >= 0) & (d.min(1) <= depth)
        T2 = np.stack([X(T[keep].reshape(-1, 3)).reshape(-1, 3), T[keep][:, :, 2]], -1)
        if len(T2): far.append((max(0, d.min()), ob, silhouette(T2)))
    occ = draw_cut(A, cuts, insul=True)
    far.sort(key=lambda t: t[0])
    draw_visible(A, [(ob, sil) for _, ob, sil in far], occ)
    A.lines([[(-17500, -300), (17800, -300)]], '01_切断（構造・壁）', lw=0.35, z=8)   # GL
    cutb = {}
    for ob, pc, S2 in cuts:
        if not S2: continue
        P = np.vstack([np.asarray(q) for q in S2]); b = (P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max())
        o = cutb.get(ob['layer']); cutb[ob['layer']] = b if o is None else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
    return cutb

def section_arc(A, Rc, depth=30000):
    """円筒面 r=Rc で切って展開。横＝u（南の妻から北へ、r=Rc の弧長）、西を見る（奥＝r の大きい方）"""
    def RTH(P):
        d = P[..., :2] - C; return np.hypot(d[..., 0], d[..., 1]), unwrap(np.arctan2(d[..., 1], d[..., 0]))
    X = lambda th: SGN * (th - TH_S[0]) * Rc
    far, cuts = [], []
    for ob in OBJ:
        if ob['layer'].startswith('47') or num(ob['layer']) in (76, 77) or 91 <= num(ob['layer']) <= 98 or num(ob['layer']) in (3, 4): continue   # 園庭の木・小屋は断面に出さない（園庭の断面は園庭のチャット）
        T = ob['T']; rr, th = RTH(T)
        if rr.max() < Rc or rr.min() > Rc + depth: continue
        if rr.min() < Rc < rr.max():
            f = rr - Rc; segs = []
            for tri, ff, tt in zip(T, f, th):
                sg = np.sign(np.where(np.abs(ff) < 1e-6, 1e-6, ff))
                if sg.min() > 0 or sg.max() < 0: continue
                pts = []
                for i in range(3):
                    j = (i + 1) % 3
                    if sg[i] != sg[j]:
                        t = ff[i] / (ff[i] - ff[j]); pts.append((X(tt[i] + (tt[j] - tt[i]) * t), tri[i][2] + (tri[j][2] - tri[i][2]) * t))
                if len(pts) == 2: segs.append(pts)
            cuts.append((ob, poche(segs), segs))
        if num(ob['layer']) in (2, 90): continue              # 川の護岸・園庭の地形は切り口だけ
        keep = rr.max(1) >= Rc
        T2 = np.stack([X(th[keep]), T[keep][:, :, 2]], -1)
        if len(T2): far.append((max(0, rr.min() - Rc), ob, silhouette(T2)))
    occ = draw_cut(A, cuts, insul=True)
    far.sort(key=lambda t: t[0])
    draw_visible(A, [(ob, sil) for _, ob, sil in far], occ)
    A.lines([[(-5000, -300), (64000, -300)]], '01_切断（構造・壁）', lw=0.35, z=8)
    cutb = {}
    for ob, pc, S2 in cuts:
        if not S2: continue
        P = np.vstack([np.asarray(q) for q in S2]); b = (P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max())
        o = cutb.get(ob['layer']); cutb[ob['layer']] = b if o is None else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
    # 通り芯（架構 1〜20）
    for k, t in enumerate(TH_S, 1):
        x = X(t)
        A.lines([[(x, -1200), (x, 9800)]], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
        A.bubble(x, -1750, str(k))
    return cutb

def airflow(A, playroom=False):
    """換気の道（ユーザー 10-23夜）：東の地袋・腰の無双窓 → 部屋 → 屋根に沿って梁間を西へ上る → 西の壁の上（縦格子・開いた所）
    → 西吹き抜け → 越屋根のすき間。playroom：夏の夜は西館の東の覗き窓を開け、遊戯室の吹き抜けを上って西館の越屋根へ（高低差が大きい）。
    略図（断面の線は 3dm、矢印は考え方）。x＝v（mm、東が右）、z＝FL からの高さ"""
    roof = lambda v: 4000 - v / 12.0
    col = '#2F6FB0'
    def arrow(P, ls='-', lw=0.18):
        P = np.array(P, float)
        A.lines([P], '45_換気', lw=lw, color=col, ls=ls, z=9)
        d = P[-1] - P[-2]; d = d / np.linalg.norm(d); n = np.array([-d[1], d[0]])
        A.lines([[P[-1] - d * 260 + n * 120, P[-1], P[-1] - d * 260 - n * 120]], '45_換気', lw=lw, color=col, z=9)
    day = [(14700, 350), (12600, 700), (10500, roof(10500) - 450), (6000, roof(6000) - 320), (1700, roof(1700) - 320),
           (700, 3950), (-150, 4400)]
    arrow(day + [(-150, 4420), (-700, 4700)] if not playroom else day + [(-300, 4430)])
    if playroom:
        arrow([(-300, 4430), (-650, 4430), (-750, 4250), (-1250, 4100)], ls=(0, (5, 3)))
        arrow([(-1300, 4400), (-1450, 6000), (-1400, 7600), (-1400, 8900)], ls=(0, (5, 3)))
        A.text(-1700, 9050, '夏の夜：遊戯室の吹き抜けを上って西館の越屋根へ（覗き窓を夜だけ開ける）', 5, '45_換気', ha='right', va='bottom', color=col)
        A.text(400, 5300, '昼（中間期）は本館の越屋根のすき間から外へ', 5, '45_換気', ha='left', va='bottom', color=col)
    else:
        A.text(400, 5300, '本館の越屋根のすき間から外へ', 5, '45_換気', ha='left', va='bottom', color=col)
    A.text(6500, roof(6500) - 560, '梁間（梁と梁と屋根のあいだ）を西へ上る', 5, '45_換気', ha='center', va='top', color=col)
    A.text(14600, 600, '地袋・腰の無双窓', 5, '45_換気', ha='right', va='bottom', color=col)


def make_sections():
    W_, H_ = 841, 594
    S = Sheet(W_, H_, '断面図 A（縦断・展開）・B・C　1/100（A1）')
    extA = (-14500, 65500, -5600, 10500)
    A = S.axes(30, H_ - 40 - 161, extA)
    A.insul_x = (0, 57000)
    cutb = section_arc(A, SECTIONS[0][2])
    levels(A, cutb, 64300, True)
    A.text(extA[0] + 300, extA[3] - 200, f'断面 A　{SECTIONS[0][3]}', 9, '80_図名・縮尺・方位', ha='left', va='top')
    A.text(extA[0] + 300, -5400, '← 南（高野川）', 6, '80_図名・縮尺・方位', ha='left', va='bottom')
    A.text(56000, -2400, '北 →', 6, '80_図名・縮尺・方位', ha='right', va='bottom')
    A.text(-9000, -4900, '高野川の護岸（現況、寸法は仮）', 5, '80_図名・縮尺・方位', ha='center', va='bottom', color='0.35')
    extX = (-17500, 21500, -2600, 10500)
    for i, (nm, kind_, val, cap_) in enumerate(SECTIONS[1:]):
        A = S.axes(30 + i * (390 + 15), H_ - 40 - 161 - 45 - 131, extX)
        A.insul_x = (-1e5, 12000)
        cutb = section_u(A, theta_u(val))
        westx = min([b[0] for k, b in cutb.items() if k.startswith('21_')] or [-900])
        chain_dims(A, [westx, -900, 0, 1600, 12000, 13500, 15000], -900)
        for nm2, x in (('W', 0), ('E', 12000)):
            A.lines([[(x, -1200), (x, 9800)]], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
            A.bubble(x, -1750, nm2)
        levels(A, cutb, 17300, westx < -2000)
        airflow(A, playroom=(nm == 'C'))
        A.text(extX[0] + 300, extX[3] - 200, f'断面 {nm}　{cap_}', 9, '80_図名・縮尺・方位', ha='left', va='top')
        A.text(extX[0] + 300, -2400, '← 西', 6, '80_図名・縮尺・方位', ha='left', va='bottom')
        A.text(16000, -2400, '東 →', 6, '80_図名・縮尺・方位', ha='right', va='bottom')
        if i == 0:
            for j in range(5):
                A.ax.add_patch(plt.Rectangle((-9000 + j * 1000, -2450), 1000, 150, fc='k' if j % 2 == 0 else 'white', ec='k', lw=LW(0.1)))
            A.text(-9000, -2050, '0', 5, '80_図名・縮尺・方位'); A.text(-4000, -2050, '5 m', 5, '80_図名・縮尺・方位')
    return S

# ---------------------------------------------------------------- 立面
# 建物の軸に合わせた 5 面（ユーザー：東西南北より建物の軸に沿って）。どれも水平な視線の正投影。
#   園庭の側＝円弧の中心の方向から（本館の弧の真ん中 u 28.5 に正対）／道路の側＝その反対／
#   高野川の側＝川の向こうから川の辺に直角に／南の妻＝架構 1 に正対／北の妻＝架構 20 に正対。
# 描くのは建物（レイヤー 05〜69 と 89 の大戸）だけ。敷地・園庭・外構・周辺・室内の家具は描かない（GL の線だけ）。
def _unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def _tangent(u_mm): return _unit(at(205000, theta_u(u_mm + 500)) - at(205000, theta_u(u_mm - 500)))   # 北（u の大きい方）へ
def _river_dir():
    site = None
    for ln, P in CURVES:
        if num(ln) == 0 and len(P) > 3:
            pg = Polygon(P[:, :2])
            if pg.is_valid and (site is None or pg.area > Polygon(site).area): site = P[:, :2]
    def uvp(p):
        d = p - C; th = float(unwrap(math.atan2(d[1], d[0]))); return SGN * (th - TH_S[0]) * 205000, 205000 - math.hypot(*d)
    UV = [uvp(p) for p in site[:-1]]
    a = site[max(range(len(UV)), key=lambda i: UV[i][1])]; b = site[min(range(len(UV)), key=lambda i: UV[i][0])]
    d = _unit(b - a); n = np.array([-d[1], d[0]])
    if np.dot(n, site[:-1].mean(0) - (a + b) / 2) < 0: n = -n          # 川から敷地の中へ
    return n
_garden = _unit(at(205000, theta_u(28500)) - C)                         # 円弧の中心から弧の真ん中へ（西向き）
ELEV_VIEWS = [('garden', '園庭の側の立面図', '円弧の中心の方向から、弧の真ん中に正対', _garden, 'long'),
              ('road', '道路の側の立面図', '西の道路から、園庭の側の反対', -_garden, 'long'),
              ('river', '高野川の側の立面図', '川の向こうから、川の辺に直角に', _river_dir(), 'long'),
              ('south', '南の妻の立面図', '架構 1 に正対', _tangent(0), 'end'),
              ('north', '北の妻の立面図', '架構 20 に正対', -_tangent(57000), 'end')]
def _compass(v):
    a = (math.degrees(math.atan2(v[0], v[1])) + 360) % 360           # 北から時計回り
    return ['北', '北東', '東', '南東', '南', '南西', '西', '北西'][int((a + 22.5) // 45) % 8]
ELEV = {}
for key_, ttl, cap_, vd, _ in ELEV_VIEWS:
    rt = np.array([vd[1], -vd[0]])
    ELEV[key_] = (ttl, (lambda P, rt=rt: P[:, :2] @ rt), (lambda P, vd=vd: P[:, :2] @ vd),
                  f'{cap_}。{_compass(vd)}を見る、右が{_compass(rt)}')
def elev_objs():
    out = []
    for ob in OBJ:
        n = num(ob['layer']); k = kind(ob['layer'])
        if not (5 <= n <= 69 or n == 89): continue
        if ob['layer'].startswith('47') or n in (62, 63, 64): continue          # 地面の板・避難の帯
        if k == 'furn' or ROOM_LAYERS(ob['layer']): continue
        if n == 55 or '外構' in ob['layer']: continue                           # ホールの林（室内）・柵などの外構
        z = ob['T'][:, :, 2]
        if z.max() - z.min() < 60 and z.max() < -200: continue                   # 地面に張り付いた板
        out.append(ob)
    return out
ELEV_FILL = lambda ob: ('#DCE9F2' if kind(ob['layer']) == 'glass' else
                        '#BDBDBD' if num(ob['layer']) in (10, 20, 26, 28) else
                        '#E9DCC4' if num(ob['layer']) in (11, 22, 18, 30, 50) or ob['layer'].startswith(('16', '19b', '89')) and kind(ob['layer']) != 'glass' else
                        'white')
def elevation(A, mode, objs):
    _, H, D, _ = ELEV[mode]
    items = []
    for ob in objs:
        T = ob['T']
        if num(ob['layer']) in (10, 20):
            # 屋根（厚みの無い面）：見る人の側へ下がっている三角形だけ（向こうへ下がる面は棟の向こうで見えない）
            P3 = T.reshape(-1, 3)
            Q = np.concatenate([np.stack([H(P3).reshape(-1, 3), D(P3).reshape(-1, 3)], -1), T[:, :, 2:3]], -1)
            nrm = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]); nrm *= np.sign(nrm[:, 2:3] + 1e-12)
            keep = nrm[:, 1] < -1e-6 * np.linalg.norm(nrm, axis=1)      # 上向きの法線が見る人（奥行きの小さい側）を向く
            T = T[keep]
            if not len(T): continue
        P = T.reshape(-1, 3); h = H(P).reshape(-1, 3); d = D(P).reshape(-1, 3)
        T2 = np.stack([h, T[:, :, 2]], -1)
        # 長いもの（弧に沿う桁・壁・屋根）は 3 m ごとに分けて、手前・奥の順を部分ごとに（建物が弧なので端が手前に来る）
        key = np.floor(h.mean(1) / 3000.0) if h.max() - h.min() > 4000 else np.zeros(len(h))
        whole = silhouette(T2) if len(np.unique(key)) > 1 else None
        for kk in np.unique(key):
            sel = key == kk
            sil = silhouette(T2[sel])
            edge = None
            if whole is not None and sil is not None:          # 線は全体の外形から（分け目の線は描かない）
                edge = whole.boundary.intersection(sil.buffer(3))
            items.append((d[sel].min(), (ob, edge), sil))
    items.sort(key=lambda t: t[0])
    occ = Polygon()
    for i, (_, (ob, edge0), sil) in enumerate(items):
        if sil is None or sil.is_empty: continue
        k = kind(ob['layer'])
        vis = sil.difference(occ) if not occ.is_empty else sil
        if vis.is_empty: continue
        lay = LAYER_OF[k][1]
        fc = ELEV_FILL(ob)
        if fc != 'white': A.fill(vis, lay, fc=fc, z=1, seam=True)
        eb = edge0 if edge0 is not None else sil.boundary
        edge = eb.difference(occ.buffer(2)) if not occ.is_empty else eb
        A.geom_lines(edge, lay, lw={'glass': 0.09}.get(k, 0.13), color={'glass': '#3d6f9a'}.get(k, 'k'), z=3)
        if k != 'glass':
            occ = unary_union([occ, sil]) if not occ.is_empty else sil
            if i % 40 == 39: occ = occ.simplify(1)
    return items

def elev_marks(A, mode, objs, h0, h1, with_levels=True):
    """GL の線、高さの記号、通り芯（東・西は架構 1〜20、南・北は W・E）"""
    _, H, D, right = ELEV[mode]
    A.lines([[(h0 - 2500, -300), (h1 + 2500, -300)]], '01_切断（構造・壁）', lw=0.4, z=8)
    zs = {}
    for ob in objs:
        n = num(ob['layer']); zt = ob['T'][:, :, 2].max()
        key = '本館 屋根の最高' if n == 10 else '本館 越屋根の蓋' if n == 50 else '西館 最高' if n in (20, 28) else None
        if key: zs[key] = max(zs.get(key, -1e9), zt)
    L = [('GL', -300), ('FL', 0), ('2FL', 3250)] + sorted(zs.items(), key=lambda t: t[1])
    L.sort(key=lambda t: t[1]); x_text = h1 + 1800; last = -1e9
    for nm, z in (L if with_levels else []):
        zt = max(z, last + 420); last = zt
        A.lines([[(x_text - 300, z), (x_text, z + 260), (x_text - 600, z + 260), (x_text - 300, z)]], '51_高さ', lw=0.1, color='#2E7D32')
        A.lines([[(x_text - 900, z), (x_text + 200, z)]], '51_高さ', lw=0.09, color='#2E7D32')
        A.text(x_text + 300, zt + 60, f'{nm}　{"+" if z > 0 else "±" if z == 0 else "−"}{abs(z):,.0f}', 5, '51_高さ', ha='left', va='bottom', color='#2E7D32')
    if mode in ('garden', 'road', 'river'):
        for k, th in enumerate(TH_S, 1):
            x = float(H(np.array([at(205000, th)]))[0])
            A.lines([[(x, -1300), (x, -400)]], '40_通り芯', lw=0.09, color='#B03030', z=2)
            A.bubble(x, -1800, str(k), rad=380, pt=5.5)
    else:
        th = theta_u(0 if mode == 'south' else 57000)
        for nm, rr in (('W', 205000), ('E', 193000)):
            x = float(H(np.array([at(rr, th)]))[0])
            A.lines([[(x, -1300), (x, -400)]], '40_通り芯', lw=0.09, color='#B03030', z=2)
            A.bubble(x, -1800, nm, rad=380, pt=5.5)

def make_elevations(views, title, note_row):
    """views=[(mode, row, x の位置 'center' か mm, 高さの記号を描くか)]、row は上から 0, 1, 2"""
    W_, H_ = 841, 594
    S = Sheet(W_, H_, title)
    objs = elev_objs()
    allP = np.vstack([ob['T'].reshape(-1, 3) for ob in objs])
    ztop = max(ob['T'][:, :, 2].max() for ob in objs)
    zr = (-2300, ztop + 900); hgt = (zr[1] - zr[0]) / 100
    nrow = 1 + max(v[1] for v in views)
    gap = min(45, (H_ - 60 - nrow * hgt) / max(1, nrow - 1))
    top = H_ - 30 - hgt
    first = True
    for mode, row, xpos, lv in views:
        ttl, H, D, cap_ = ELEV[mode]; h = H(allP)
        ext = (h.min() - 1500, h.max() + (8500 if lv else 1500), *zr)
        x_mm = (W_ - (ext[1] - ext[0]) / 100) / 2 if xpos == 'center' else xpos
        y_mm = top - row * (hgt + gap)
        A = S.axes(x_mm, y_mm, ext)
        elevation(A, mode, objs); elev_marks(A, mode, objs, h.min(), h.max(), lv)
        A.text(ext[0] + 300, zr[1] - 100, f'{ttl}　1/100　（{cap_}）', 8.5, '80_図名・縮尺・方位', ha='left', va='top')
        if first:
            sx = h.max() + 2000
            for j in range(5):
                A.ax.add_patch(plt.Rectangle((sx + j * 1000, -2150), 1000, 150, fc='k' if j % 2 == 0 else 'white', ec='k', lw=LW(0.1)))
            A.text(sx, -1750, '0', 5, '80_図名・縮尺・方位'); A.text(sx + 5000, -1750, '5 m', 5, '80_図名・縮尺・方位')
            first = False
    S.text_paper(W_ - 15, 26, '描いているのは建物だけ（園庭・外構（柵など）・樹木・室内の家具は省いた）。灰色は屋根の面、薄い青はガラス（奥が透けて見える）。'
                 + note_row, 6, ha='right', color='0.35')
    return S

ELEV_SHEETS = [('sodachiya_elevations_1-100', lambda: make_elevations(
                    [('garden', 0, 'center', True), ('road', 1, 'center', True), ('south', 2, 'center', True)],
                    '立面図 1　園庭の側・道路の側・南の妻　1/100（A1）',
                    '\n園庭の側と道路の側は本館の弧の真ん中に正対（平面と同じ向き、架構の番号は下の丸）。南の妻は架構 1 に正対。')),
               ('sodachiya_elevations2_1-100', lambda: make_elevations(
                    [('river', 0, 'center', True), ('north', 1, 'center', True)],
                    '立面図 2　高野川の側・北の妻　1/100（A1）',
                    '\n高野川の側は川の向こうから川の辺に直角に、北の妻は架構 20 に正対。'))]

ONLY = os.environ.get('DRAW_ONLY', '')
for name, mk in (('sodachiya_plan_1-100', make_plans), ('sodachiya_sections_1-100', make_sections),
                 *ELEV_SHEETS):
    if ONLY and ONLY not in name: continue
    S = mk(); S.save(os.path.join(OUTD, name)); print('written', name)
