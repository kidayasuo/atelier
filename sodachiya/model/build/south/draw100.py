"""3dm（メッシュの版）から 1/100 の図をつくる：1 階平面（＋西館 2 階）、断面 3 つ（A 縦断・B あまのがわ・C 4 歳と遊戯室）、立面 4 つ
使い方: python3 draw100.py MODEL_MESH.3dm OUTDIR
- 平面：FL+1500 で切る（2 階は 2FL+1000、西館の南西の軒が低い）。切れたものは塗り（構造・壁は黒、家具は灰、ガラスは細線）。
  見えがかりは近いもの（高いもの）から順に、手前の形で後ろの線を切って描く（隠れ線を消した線だけ）。
  屋根の外形など切断より上の物は想像線（二点鎖線、梁は描かない）、部屋は決定事項の色で淡く塗る。通り芯（架構 1〜20、W・E）、スパンの寸法、断面の位置、部屋名と面積。
- 立面：東・西・南・北を、平面と同じ向き（北が右）に回して正投影。建物だけ、見える面だけ（近いものから手前の形で後ろを切る）。
- 断面：A は円筒面 r=197 m で切って展開（西を見る）。B・C は架構に平行な鉛直面（北を見る）、奥 3.2 m まで。
  D（別の紙 sodachiya_sections2_1-100）は本館だけの横断、架構 19 の線（光の筋の溝）で切る、北を見る。
  通り芯、幅の寸法、高さの記号（GL・FL・2FL・屋根・越屋根の蓋・西館の最高）。
出力：PDF・PNG と DXF（レイヤー分け、1/100 の図を 1:1 の mm で。Rhino・LayOut で開いて手を入れる用）。
"""
import sys, os, math, re, numpy as np, rhino3dm as r
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, PathPatch
from matplotlib.path import Path
from matplotlib import font_manager
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, box, Point
from shapely.ops import unary_union, polygonize, linemerge
import mapbox_earcut as earcut

IN, OUTD = sys.argv[1], sys.argv[2]
# 図のPDFは sodachiya/drawings/（ユーザーが開く、10-24）、DXF・PNGは OUTD
PDFD = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].endswith('.3dm') else OUTD   # add_inner.py がこの頭を借りるときは3つ目が3dm
if PDFD != OUTD: os.makedirs(PDFD, exist_ok=True)
os.makedirs(OUTD, exist_ok=True)
# 字は TrueType に変えた Noto を Type42 で埋め込む（scripts/fonts42.py）。システムの Noto（OTF・CFF）のまま Type42 にすると、
# Illustrator・プレビューなどで字が欠けて、字の白い地だけが四角く残っていた（10-28、ユーザー）
_SR = next((p_ for p_ in (os.environ.get('SODACHIYA_ROOT', ''), os.path.join(os.path.dirname(os.path.abspath(globals().get('__file__', 'x'))), '..', '..', '..'),   # add_inner.py・walls_spec.py が頭を exec するときは __file__ が無い
                          '/home/claude/atelier/sodachiya') if p_ and os.path.isfile(os.path.join(p_, 'scripts', 'fonts42.py'))), None)
if _SR:
    sys.path.insert(0, os.path.join(_SR, 'scripts')); import fonts42  # noqa: F401
else:
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
HAS17Y = any(ob['layer'].startswith('17y_') for ob in OBJ)     # 大和張りの上板が 3dm にある（yamato.py、10-28）
HAS21Y = any(ob['layer'].startswith('21y_') for ob in OBJ)     # 西館の上板（yamato_west.py、10-28 西館係）

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
        # ほぼ閉じた輪（メッシュの継ぎ目のわずかなすき間で端が 10 mm 以内に戻る。遊戯室の西の外壁など）は閉じる
        rings = [Polygon(g.coords).buffer(0) for g in gs if len(g.coords) > 3 and np.hypot(*(np.asarray(g.coords[0]) - np.asarray(g.coords[-1]))) < 10]
        rings = [r for r in rings if r.area > 0]
        if rings and len(rings) == len(gs): return unary_union(rings)
        if len(gs) == 2:
            a_, b_ = [np.asarray(g.coords) for g in gs]
            if np.hypot(*(a_[0] - b_[0])) > np.hypot(*(a_[0] - b_[-1])): b_ = b_[::-1]
            P = Polygon(np.vstack([a_, b_[::-1]])).buffer(0)
            if P.area > 0 and P.area < 1000 * max(gs[0].length, gs[1].length): return P
        return _close_open(merged)
    # 入れ子（穴）は偶奇で
    polys.sort(key=lambda p: -p.area); out = None
    for p in polys:
        out = p if out is None else out.symmetric_difference(p)
    # 輪にならずに残った線（一つの物にまとめた外壁は、継ぎ目で小口が抜けて閉じない所がある、10-24）
    rest = merged.difference(unary_union([q.boundary for q in polys]).buffer(1))
    extra = _close_open(rest) if not rest.is_empty and rest.length > 500 else None
    if extra is not None and not extra.is_empty: out = out.union(extra)
    return out

CLOSE_W = 80   # 閉じていない切り口：向かい合う2本の線（あき 160 以下＝壁・板の厚さ）のあいだを埋める
def _close_open(lines):
    try:
        lm_ = linemerge(lines) if lines.geom_type == 'MultiLineString' else lines
        g = lm_.buffer(CLOSE_W, cap_style=1, join_style=1).buffer(-CLOSE_W, join_style=1)
    except Exception:
        return None
    g = unary_union([q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > 2e4])
    return None if g.is_empty else g

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
# 建具（戸・障子・ガラス戸・窓）：平面・断面では細線で描く（塗らない）。製図の決まり：切断した壁は太く塗り、建具は細線（設計監修 10-24）
FIT_PREFIX = ('16_', '19', '27_', '66_', '89_', '35d')
def is_fitting(ln): return ln.startswith(FIT_PREFIX)
def is_thin(g, thin=120):
    if g is None or g.is_empty: return True
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon': continue
        mr = np.array(q.minimum_rotated_rectangle.exterior.coords)[:4]
        if min(np.linalg.norm(mr[1] - mr[0]), np.linalg.norm(mr[2] - mr[1])) > thin: return False
    return True
def centerlines(g, thin=120):
    """薄い板（戸・ガラス）の切り口 → 長い向きの中心線（1/100 では板の両面の二本線が重なってつぶれるので一本で）。厚い物は輪郭"""
    out = []
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon' or q.area < 1: continue
        mr = np.array(q.minimum_rotated_rectangle.exterior.coords)[:4]
        e0, e1 = np.linalg.norm(mr[1] - mr[0]), np.linalg.norm(mr[2] - mr[1])
        if min(e0, e1) <= thin and q.area > 0.6 * e0 * e1:
            a, b = ((mr[0] + mr[3]) / 2, (mr[1] + mr[2]) / 2) if e0 >= e1 else ((mr[0] + mr[1]) / 2, (mr[2] + mr[3]) / 2)
            out.append([a, b])
        else:
            out.append(list(q.exterior.coords))
    return out
def is_beam(ln): return ln.split('_')[0] in KIND_BEAM

# DXF のレイヤー：名前 → (色 ACI, 線の太さ 1/100 mm, 線種)
DL = {
    '01_切断（構造・壁）': (7, 35, 'Continuous'),
    '02_切断（家具）': (8, 18, 'Continuous'),
    '03_切断（ガラス）': (5, 13, 'Continuous'),
    '07_切断（建具）': (7, 18, 'Continuous'),
    '13_見えがかり（窓台・隠れた窓）': (7, 9, 'DASHED'),
    '04_切断（機械室などの塊）': (7, 35, 'Continuous'),
    '05_断熱（仮）': (2, 9, 'Continuous'),
    '06_部屋の色': (8, 0, 'Continuous'),
    '09_立面の外形': (7, 30, 'Continuous'),
    '10_見えがかり': (7, 13, 'Continuous'),
    '11_見えがかり（家具）': (8, 9, 'Continuous'),
    '12_見えがかり（ガラス）': (5, 9, 'Continuous'),
    '20_上部（屋根の外形・梁）': (8, 9, 'PHANTOM'),     # 切断より上の物：想像線（細い二点鎖線、JIS A 0150）
    '15_地盤': (8, 9, 'Continuous'),
    '14_鏡面': (8, 9, 'Continuous'),                  # 断面で奥に見える光の筋の鏡面の塗り（10-29）                  # 断面の GL の下の地盤の記号（斜線）
    '30_敷地・外構': (8, 9, 'Continuous'),
    '40_通り芯': (1, 9, 'DASHDOT'),
    '41_通り芯の符号': (1, 13, 'Continuous'),
    '50_寸法': (3, 9, 'Continuous'),
    '51_高さ': (3, 9, 'Continuous'),
    '60_部屋名・面積': (7, 13, 'Continuous'),
    '70_断面の位置': (6, 9, 'DASHDOT'),
    '80_図名・縮尺・方位': (7, 18, 'Continuous'),
    '90_図枠': (7, 25, 'Continuous'),
}
PT2MM = 0.3528   # 1 pt = 0.3528 mm（紙の上）
# 文字の層（…_文字.pdf）に残すレイヤー（注記）。ほかのレイヤーの線と塗り（建物の線）は消す。字・通り芯の丸の白・縮尺の帯・凡例の色の四角
# （ax.add_patch で直に足す物）はいつも残す。階段の矢印・破断線、GL の線は annot=True で残す
ANNOT_LAYERS = {'40_通り芯', '41_通り芯の符号', '45_換気', '45_吹抜', '50_寸法', '51_高さ', '60_部屋名・面積', '70_断面の位置',
                '80_図名・縮尺・方位', '81_注', '90_図枠'}

# JIS の製図（JIS A 0150 建築製図通則、学生の課題の範囲、ユーザー 10-28）：
# 線の太さは 3 つ（A1・1/100）：太 0.35（切断面の外形・GL）、中 0.18（建具の切り口・寸法の端の斜線）、細 0.09〜0.13（見えがかり・寸法線・中心線・かくれ線・想像線）
LW_CUT, LW_MID, LW_THIN = 0.35, 0.18, 0.09
LS_HIDDEN = (0, (3, 2))                    # かくれ線（破線）
LS_CHAIN = (0, (10, 3, 2, 3))              # 中心線・通り芯・切断線（一点鎖線）
LS_PHANTOM = (0, (14, 3, 2, 3, 2, 3))      # 想像線（二点鎖線）：切断より上にある物（屋根の外形・越屋根・2 階の床の縁・光の筋など）
# 文字の大きさ（紙の上）：図名 3.9 mm ＞ 室名 2.8 mm ＞ 寸法・高さ・注 2.5 mm
PT_TITLE, PT_ROOM, PT_DIM, PT_NOTE = 11, 8, 7.1, 7.1

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
    def __init__(s, w, h, title, scale=100, margin=10, notitle=False):
        s.w, s.h, s.k = w, h, scale
        s.fig = plt.figure(figsize=(w * MM, h * MM))
        s.views = []                       # この紙に描いた図（…_views.json に書く。Rhino の zumen.py が読む、10-28）
        s.doc = ezdxf.new('R2018', setup=True); s.msp = s.doc.modelspace()
        s.doc.header['$INSUNITS'] = 4      # mm
        for name, (c, lw, lt) in DL.items():
            s.doc.layers.add(name, color=c, lineweight=lw, linetype=lt)
        s.doc.styles.add('JP', font='NotoSansCJKjp-Regular.otf')
        k = s.k
        s.msp.add_lwpolyline([(0, 0), (w * k, 0), (w * k, h * k), (0, h * k)], close=True, dxfattribs={'layer': '90_図枠'})
        m_ = margin
        s.msp.add_lwpolyline([(m_ * k, m_ * k), ((w - m_) * k, m_ * k), ((w - m_) * k, (h - m_) * k), (m_ * k, (h - m_) * k)], close=True, dxfattribs={'layer': '90_図枠'})
        s.fig.patches.append(plt.Rectangle((m_ / w, m_ / h), 1 - 2 * m_ / w, 1 - 2 * m_ / h, transform=s.fig.transFigure, fill=False, lw=LW(0.25), ec='k'))
        if notitle:
            pass
        elif m_ >= 10:
            s.text_paper(w - 15, 18, title, 11, ha='right')
            s.text_paper(w - 15, 13, 'こどもたちの育ち舎　3dm（sodachiya.3dm）から自動で作図　' + STAMP, 6.0, ha='right', color='0.35')
        else:                                          # 余白の狭い枚（3枚目の平面）：表題は図の中に、作図の印は左下に小さく
            s.text_paper(m_ + 8, m_ + 3, 'こどもたちの育ち舎　3dm（sodachiya.3dm）から自動で作図　' + STAMP, 4.5, color='0.45')
    def text_paper(s, x_mm, y_mm, t, pt, ha='left', va='bottom', color='k', layer='80_図名・縮尺・方位'):
        s.fig.text(x_mm / s.w, y_mm / s.h, t, ha=ha, va=va, fontsize=pt, color=color)
        dxf_text(s.msp, x_mm * s.k, y_mm * s.k, t, pt * PT2MM * s.k, layer, ha, va)
    def axes(s, x_mm, y_mm, ext):
        return Ax(s, x_mm, y_mm, ext)
    def save(s, base):
        s.fig.savefig(os.path.join(PDFD, os.path.basename(base) + '.pdf')); s.fig.savefig(base + '.png', dpi=110)
        if s.views:                        # 図を描いた紙（配置図は別の _xform.json）：文字の層と、図の置き場所の json
            s.save_moji(base); s.save_views(base)
        plt.close(s.fig)
        s.doc.saveas(base + '.dxf')
    def save_moji(s, base):
        """…_文字.pdf：同じ紙・同じ位置に、文字と注記（部屋名・面積・寸法・通り芯・断面の位置・高さ・図名・方位・縮尺・凡例・注・換気・作図の印）だけ。
        建物の線と塗り（切断・見えがかり・部屋の色・断熱・地盤）は消す。Rhino 経由の線（rhino/zumen.py）の上に重ねる用（項 20261028-0911-kanshu）。
        描いたものを一度だけ描き、ここでは見せる・隠すを変えてもう一度書き出す（立面の z バッファを二度走らせない）。
        地は透明。字の白い地（box）は残す（Rhino の線の上で字が読めるように）。SODACHIYA_MOJI_BOX=0 で白い地も消す"""
        nobox = os.environ.get('SODACHIYA_MOJI_BOX', '1') == '0'
        hid = []
        for ax in s.fig.axes:
            for a in list(ax.collections) + list(ax.patches) + list(ax.texts) + list(ax.lines):
                if not getattr(a, '_moji', True) and a.get_visible(): a.set_visible(False); hid.append(a)
                if nobox and hasattr(a, 'get_bbox_patch') and a.get_bbox_patch() is not None and a.get_bbox_patch().get_visible():
                    a.get_bbox_patch().set_visible(False); hid.append(a.get_bbox_patch())
        s.fig.savefig(os.path.join(PDFD, os.path.basename(base) + '_文字.pdf'), transparent=True)
        for a in hid: a.set_visible(True)
    def view(s, A, name, kind_, **d):
        """図 A（Ax）の置き場所を記録する。A の描く座標 (X, Y) → 紙の mm（左上が原点、右へ x、下へ y）：
        x = (X + ox) / k、y = H − (Y + oy) / k。平面は (X, Y) = 回転 φ・(xy + ずらし)、断面・立面は (X, Y) = (h, z)"""
        k, H = s.k, s.h
        hz = dict(a=1 / k, b=0.0, c=A.ox / k, d=0.0, e=-1 / k, f=H - A.oy / k)    # 描く座標 (X, Y) → 紙
        x0, x1 = A.ax.get_xlim(); y0, y1 = A.ax.get_ylim()
        v = dict(name=name, kind=kind_, scale=k, draw_to_paper=hz,
                 clip_paper_mm=[(x0 + A.ox) / k, H - (y1 + A.oy) / k, (x1 + A.ox) / k, H - (y0 + A.oy) / k])   # 図の範囲（紙、左・上・右・下）
        if kind_ == 'plan':
            c_, n_ = math.cos(A.phi), math.sin(A.phi); sx, sy = d.get('shift_mm', (0.0, 0.0))
            v['rotate_deg'] = math.degrees(A.phi)
            v['model_to_paper'] = dict(a=c_ / k, b=-n_ / k, c=(c_ * sx - n_ * sy + A.ox) / k,
                                       d=-n_ / k, e=-c_ / k, f=H - (n_ * sx + c_ * sy + A.oy) / k)
        else:
            O = np.asarray(d['origin'], float); R_ = np.asarray(d['right'], float)
            m2 = [[*(R_ / k), (A.ox - O @ R_) / k], [0.0, 0.0, -1 / k, H - A.oy / k]]   # 3dm の (x, y, z, 1) → 紙 (x, y)
            v['model_to_paper_3d'] = m2
        v.update({k_: (np.asarray(x_).tolist() if isinstance(x_, (np.ndarray, tuple)) else x_) for k_, x_ in d.items()})
        s.views.append(v)
    def save_views(s, base):
        import json as _jj
        out = {'_': '3dm（sodachiya.3dm・sodachiya_exact_mesh.3dm と同じ座標、mm）→ この紙の mm（左上が原点、右へ x、下へ y）。'
                    '平面：x = a·X + b·Y + c、y = d·X + e·Y + f（X, Y は 3dm の x, y、mm。2階はずらし shift_mm を含む）。'
                    '断面・立面：h = (P − origin)·right（右へ）、上は +z、view_dir の向きを見る。紙 x = a·h + c、y = e·z + f（draw_to_paper）。'
                    'model_to_paper_3d は (x, y, z, 1) → 紙 の 2×4。clip_paper_mm は図の範囲（左・上・右・下）。'
                    'draw100.py が書く（更新係、10-28、項 20261028-0911-kanshu）。rhino/zumen.py が読む。',
               'paper_mm': [s.w, s.h], 'scale': s.k,
               'line_weights_mm': {'cut': LW_CUT, 'mid': LW_MID, 'thin': LW_THIN},
               'views': s.views}
        _jj.dump(out, open(os.path.join(PDFD, os.path.basename(base) + '_views.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

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
        s.annot_all = False               # True：この図の線と塗りはすべて注記（凡例）。文字の層（…_文字.pdf）に残す
    def rot(s, q):
        q = np.asarray(q, float)
        if s.phi == 0.0: return q
        c, n = math.cos(s.phi), math.sin(s.phi)
        return np.c_[q[..., 0] * c - q[..., 1] * n, q[..., 0] * n + q[..., 1] * c] if q.ndim == 2 else np.array([q[0] * c - q[1] * n, q[0] * n + q[1] * c])
    def P(s, x, y): return (x + s.ox, y + s.oy)
    def lines(s, segs, layer, lw=0.13, color='k', ls='-', z=3, raw=False, annot=None):
        """annot：文字の層（…_文字.pdf）に残すか。None ならレイヤーで決める（is_annot）"""
        segs = [np.asarray(q, float) for q in segs if len(q) >= 2]
        if not raw: segs = [s.rot(q) for q in segs]
        if not segs: return
        lc_ = s.ax.add_collection(LineCollection(segs, colors=color, linewidths=LW(lw), linestyles=ls, zorder=z, capstyle='butt'))
        lc_._moji = s.is_annot(layer) if annot is None else annot
        for q in segs:
            s.sh.msp.add_lwpolyline([s.P(*p) for p in q], dxfattribs={'layer': layer})
    def is_annot(s, layer): return s.annot_all or layer in ANNOT_LAYERS
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
            pp_ = s.ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec='#777777' if hatch else (fc if seam else 'none'), lw=LW(0.05), hatch=hatch, zorder=z))
            pp_._moji = s.is_annot(layer)
            if fc == 'w' and not hatch: continue                 # 白抜き（間仕切り）は DXF では塗らない（線だけ）
            h = s.sh.msp.add_hatch(color=7 if fc == 'k' else 8, dxfattribs={'layer': layer})
            if isinstance(fc, str) and fc.startswith('#') and len(fc) == 7: h.rgb = tuple(int(fc[i:i + 2], 16) for i in (1, 3, 5))
            if hatch: h.set_pattern_fill('ANSI31', scale=20.0)
            h.paths.add_polyline_path([s.P(*p) for p in list(gg.exterior.coords)[:-1]], is_closed=True, flags=1)
            for ring in gg.interiors:
                h.paths.add_polyline_path([s.P(*p) for p in list(ring.coords)[:-1]], is_closed=True, flags=0)
    def text(s, x, y, t, pt, layer, ha='center', va='center', rot=0, color='k', box=False, raw=False, dxf_only=False):
        kw = dict(bbox=dict(fc='white', ec='none', pad=0.5, alpha=0.85)) if box else {}
        if not raw and s.phi:                 # rot=0 の字（部屋名など）は紙の上で水平のまま、向きのある字だけ回す
            x, y = s.rot([x, y])
            if rot: rot = ((rot + math.degrees(s.phi)) + 90) % 180 - 90
        if not (dxf_only or getattr(s, 'dxf_only_text', False)):
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
    if ob['layer'].startswith(('17y_', '21y_')): return None  # 大和張りの上板（15 mm、外壁の外）：外壁として塗らない（本館係、10-28）
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
        if gname and segs:
            # 閉じない切り口（壁を浅い角度で切ると、小口の無い長い切り口になって塗れない。西館の南西の丸みを断面Bで切る所など）：
            # 塗れなかった線を、つながりごとに凸包で閉じる（壁の切り口は塗る、製図の決まり。設計監修 10-24）
            ls_ = unary_union([LineString(q) for q in segs if np.hypot(*(np.subtract(q[1], q[0]))) > 1e-3])
            rest = ls_.difference(pc.buffer(5)) if pc is not None and not pc.is_empty else ls_
            if not rest.is_empty and rest.length > 1500:
                add = []
                for comp in getattr(rest.buffer(40), 'geoms', [rest.buffer(40)]):
                    part = rest.intersection(comp)
                    if part.length < 1500: continue
                    hull = part.convex_hull
                    if hull.geom_type == 'Polygon' and 2e4 < hull.area < 0.25 * part.length * part.length / 4: add.append(hull)
                if add: pc = unary_union([pc] + add) if pc is not None and not pc.is_empty else unary_union(add)
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
        A.geom_lines(edge, lay, lw=LW_CUT, z=6.2)
        occ.append(g)
    if 'wall' in GW:
        g = GW['wall']; A.fill(g, lay, fc='k', z=6); A.geom_lines(g.boundary, lay, lw=LW_CUT, z=6); occ.append(g)
    # 層に分けた屋根（本館係 df33150：上の層 10_・構造用合板 10r_・垂木 10v_、西館も分けたら 20・20r・20v）は、
    # 三つを一つの切り口にまとめて屋根の構成で描く（垂木は 455 おきの仮の断面でなく 10v の本当の切り口）
    roof_done = set()
    if insul:
        parts = {}
        for ob, pc, segs in items:
            m_ = ROOF_RE.match(ob['layer'])
            if m_ and pc is not None and not pc.is_empty: parts.setdefault(m_.group(1), {}).setdefault(m_.group(2), []).append(pc)
        for key, pp in parts.items():
            if not (pp.get('r') or pp.get('v')): continue          # 分けていない屋根は今までどおり（下の roof_build）
            allpc = unary_union([g.buffer(0) for L in pp.values() for g in L])
            raf = unary_union([g.buffer(0) for g in pp.get('v', [])]) if pp.get('v') else Polygon()
            if roof_build(A, allpc, rafters=raf):
                roof_done.add(key); occ.append(allpc.buffer(0))
    FLOORS = []                                    # 断面：床（本館の床組・西館の部屋の床）は床の構成で描く（下の floor_build）
    for ob, pc, segs in items:
        m_ = ROOF_RE.match(ob['layer']) if insul else None
        if m_ and m_.group(1) in roof_done: continue
        if insul and (num(ob['layer']) in (12, 13) or re.match(r'^(31|32|33|34|57)_', ob['layer'])):
            # 床の上面（水平で FL 近く）の線の x の範囲（切り口が閉じない床組もあるので線から）
            for q in segs:
                q = np.asarray(q, float)
                if len(q) >= 2 and abs(q[:, 1]).max() < 120 and np.ptp(q[:, 1]) < 30 and np.ptp(q[:, 0]) > 50:
                    FLOORS.append((q[:, 0].min(), q[:, 0].max()))
            continue
        k = kind(ob['layer']); lay = LAYER_OF[k][0]
        grouped = wall_group(ob) is not None and pc is not None and not pc.is_empty
        segs = merged(segs, pc)
        if grouped:
            pass
        elif (is_fitting(ob['layer']) and is_thin(pc)) or k == 'glass':
            # 建具・ガラスの切り口は細線（板は中心線一本）。戸の板は 0.18、ガラスは 0.13
            cl = centerlines(pc) if pc is not None and not pc.is_empty else segs
            A.lines(cl, '07_切断（建具）' if k != 'glass' else lay, lw=0.13 if k == 'glass' else 0.18, z=6.3)
            if k != 'glass' and pc is not None: occ.append(pc.buffer(0))
            continue
        elif k == 'furn':
            A.fill(pc, lay, fc='0.62', z=5); A.lines(segs, lay, lw=LW_MID, z=6)
        elif k == 'volume':
            A.lines(segs, lay, lw=LW_CUT, z=6)
        elif insul and re.match(r'^(10|20)_', ob['layer']) and roof_build(A, pc):
            pass                                   # 厚みのある屋根の立体：屋根の構成で描いた（roof_build）
        else:
            A.fill(pc, lay, fc='k', z=6); A.lines(segs, lay, lw=LW_CUT, z=6)
        if pc is not None and k != 'glass': occ.append(pc.buffer(0))
        n = num(ob['layer'])
        if insul and re.match(r'^(10|20)_', ob['layer']) and segs and not getattr(A, '_roof_built', {}).get(id(pc)):   # 屋根の本体だけ（10t・10p などの光の筋・太陽光の面には描かない）      # 屋根（3dm では厚みの無い面）：面の下 50〜200 に断熱（垂木の間 150、仮）
            ls_ = unary_union([LineString(q) for q in segs if len(q) >= 2])
            ls_ = linemerge(ls_) if ls_.geom_type == 'MultiLineString' else ls_
            bands = []
            for g in getattr(ls_, 'geoms', [ls_]):
                if g.geom_type != 'LineString' or g.length < 1000: continue
                bands.append(shp_affinity.translate(g, 0, -125).buffer(75, cap_style=2, join_style=2))
            if bands:
                bb = unary_union(bands); xc = getattr(A, 'insul_x', None)          # 軒の出（外）は除く
                if xc: bb = bb.intersection(box(xc[0], -1e5, xc[1], 1e5))
                insul_fill(A, bb)
        if insul and pc is not None and not pc.is_empty:
            band = None
            if False:
                pass
            elif n in (17, 21) and not ob['layer'].startswith(('17y_', '21y_')):   # 外壁：壁の中（両面 25 を残して）。上板（17y・21y）は除く
                band = pc.buffer(-25)
            elif n == 15:                          # あまのがわ（土間）：スラブの下 50（仮）
                band = shp_affinity.translate(pc, 0, -50).difference(pc.buffer(1))
            if band is not None and not band.is_empty and band.area > 1e4:
                insul_fill(A, band)
    if FLOORS: occ += floor_build(A, FLOORS)
    return unary_union(occ) if occ else None

# 断熱材：JIS の保温材の記号（帯の中に細いジグザグ）。前は黄の帯に斜線（斜線は 1/100 ではコンクリートの記号に読める）。
# 黄の塗りは残す（凡例：make_sections の legend_materials）
C_INSUL = '#F3D98B'
def insul_fill(A, g, z=6.5):
    if g is None or g.is_empty: return
    A.fill(g, '05_断熱（仮）', fc=C_INSUL, z=z)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon' or q.area < 2e4: continue
        x0, y0, x1, y1 = q.bounds; horiz = (x1 - x0) >= (y1 - y0)
        L = max(x1 - x0, y1 - y0); t = q.area / max(L, 1)                 # 帯の厚さ（おおよそ）
        if t < 90: continue                                               # 薄い帯（基礎断熱 50 など）は塗りだけ
        p = min(max(t, 100), 250); pts = []
        lo, hi = (x0, x1) if horiz else (y0, y1)
        for k, s_ in enumerate(np.arange(lo + p / 2, hi, p)):
            cut = q.intersection(LineString([(s_, y0 - 1), (s_, y1 + 1)]) if horiz else LineString([(x0 - 1, s_), (x1 + 1, s_)]))
            if cut.is_empty: continue
            b = cut.bounds; a_, b_ = (b[1], b[3]) if horiz else (b[0], b[2])
            w = b_ - a_; v = a_ + 0.15 * w if k % 2 == 0 else b_ - 0.15 * w
            pts.append((s_, v) if horiz else (v, s_))
        if len(pts) >= 2:
            A.geom_lines(LineString(pts).intersection(q.buffer(1)), '05_断熱（仮）', lw=LW_THIN, color='0.3', z=z + 0.05)

# 屋根の構成（決定事項（共通）の「屋根の構成」、ユーザー 10-26夜）：上から 太陽光・野地板・通気層 97／断熱 150（外張り）／
# 気密・構造用合板 24（現し）／垂木 60×150＠455（現し）。屋根の立体（厚み約420、本館係 84299df）の切り口の中に、上面からの深さで層を描く。
# 断熱は外皮の内（A.insul_x）だけ、軒の出は断熱なし。垂木は断面 B・C（垂木を横に切る）では 455 おきの小さな断面、断面 A（垂木に沿う）は見えがかりの線
RB_LAYERS = (97, 247, 271, 421)
ROOF_RE = re.compile(r'^(10|20)([rvb]?)_')           # 10-27夜：通気垂木 10b（本館係）も屋根の切り口に
def roof_build(A, pc, rafters=None):
    """pc：屋根の切り口（閉じた形）。厚み 300 以上なら構成を描いて True、薄い（前の面だけの屋根）なら False。
    rafters：層に分けた屋根の垂木（10v・20v）の切り口。あればそれを垂木として描き、厚みは確かめない（垂木のあいだは 271）"""
    if pc is None or pc.is_empty: return False
    T_ = lambda d: shp_affinity.translate(pc, 0, -d)
    if rafters is None and pc.intersection(T_(300)).area < 0.05 * pc.area: return False
    band = lambda a, b: pc.intersection(T_(a)).difference(T_(b)) if b else pc.intersection(T_(a))
    lay = '01_切断（構造・壁）'
    A.fill(pc, lay, fc='w', z=6)
    xc = getattr(A, 'insul_x', None)
    ins = band(RB_LAYERS[0], RB_LAYERS[1])
    if xc and not ins.is_empty: ins = ins.intersection(box(xc[0], -1e5, xc[1], 1e5))
    if not ins.is_empty: insul_fill(A, ins)
    ply = band(RB_LAYERS[1], RB_LAYERS[2])
    if not ply.is_empty: A.fill(ply, lay, fc='#E9DCC4', z=6.4)
    # 層の境の細線（上面から 40＝太陽光の下、97、247、271）
    for d_ in (40, 97, 247, 271):
        ln_ = T_(d_).boundary.intersection(pc.buffer(-1))
        ln_ = ln_.difference(T_(d_ + 1).buffer(0.5)) if not ln_.is_empty else ln_
        if not ln_.is_empty: A.geom_lines(ln_, lay, lw=0.07, color='0.3', z=6.6)
    raf = band(RB_LAYERS[2], RB_LAYERS[3] + 30)
    if rafters is not None:                                       # 層に分けた屋根：垂木は 10v・20v の切り口そのもの
        if not rafters.is_empty:
            A.fill(rafters, lay, fc='#E9DCC4', z=6.55); A.geom_lines(rafters.boundary, lay, lw=0.1, z=6.6)
    elif getattr(A, 'rafter_cut', False) and not raf.is_empty:     # 垂木の断面（455 おき）
        x0, _, x1, _ = raf.bounds; rs = []
        for x in np.arange(math.floor(x0 / 455) * 455, x1, 455):
            g = box(x - 30, -1e5, x + 30, 1e5).intersection(raf)
            if not g.is_empty and g.area > 2000: rs.append(g)
        if rs:
            g = unary_union(rs); A.fill(g, lay, fc='#E9DCC4', z=6.55); A.geom_lines(g.boundary, lay, lw=0.1, z=6.6)
    A.geom_lines(pc.boundary, lay, lw=LW_CUT, z=6.7)
    A.__dict__.setdefault('_roof_built', {})[id(pc)] = True
    return True

# 床の構成（本館係 10-23夜10・西館係 10-23夜15、決定事項_本館）：スギ板t30＋合板t28／大引90・鋼製束／床下 有効約450／
# ベタ基礎の底板t200（基礎断熱の内側＝熱をためる重さ）、底板の上端 FL−0.6。基礎断熱は底盤の外周の下と立ち上がりの内側
FL_BOARD, SLAB_TOP, SLAB_T, RISE_T, INS_T, INS_W = 58, -600, 200, 150, 50, 900
def floor_build(A, pcs):
    iv = sorted([list(x) for x in pcs]); B = []
    for a, b in iv:                                # 床板の続き（すき間 1.0 まではつなぐ：本館と西館のあいだも床下はつながる）
        if B and a <= B[-1][1] + 1000: B[-1][1] = max(B[-1][1], b)
        else: B.append([a, b])
    M = []
    for a, b in B:                                 # 基礎の続き（床板の切れ目 4.0 まで＝遊戯室の穴の底は、底板を下げた皿）
        if M and a <= M[-1][1] + 4000: M[-1][1] = max(M[-1][1], b)
        else: M.append([a, b])
    occ = []
    lay = '01_切断（構造・壁）'
    for x0, x1 in M:
        if x1 - x0 < 1500: continue
        boards = [bb for bb in B if bb[0] >= x0 - 1 and bb[1] <= x1 + 1]
        for a, b in boards:
            g = box(a, -FL_BOARD, b, 0); A.fill(g, lay, fc='k', z=6); occ.append(g)
        pits = [(boards[i][1], boards[i + 1][0]) for i in range(len(boards) - 1) if boards[i + 1][0] - boards[i][1] > 2500]   # 穴の底（φ3.2）だけ。あまのがわ（1.5、土間）は下げない
        slab = [box(x0, SLAB_TOP - SLAB_T, x1, SLAB_TOP)]
        for a, b in pits:                          # 穴の底の下は底板を 0.15 下げる（皿）
            slab.append(box(a - 200, SLAB_TOP - SLAB_T - 150, b + 200, SLAB_TOP - 150))
        conc = unary_union(slab + [box(x0, SLAB_TOP - SLAB_T, x0 + RISE_T, -FL_BOARD - 90), box(x1 - RISE_T, SLAB_TOP - SLAB_T, x1, -FL_BOARD - 90)])
        for a, b in pits: conc = conc.difference(box(a - 200 + RISE_T, SLAB_TOP - 150, b + 200 - RISE_T, SLAB_TOP + 1))
        A.fill(conc, lay, fc='0.72', z=6); A.geom_lines(conc.boundary, lay, lw=LW_CUT, z=6.1); occ.append(conc)
        ins = unary_union([box(x0 + RISE_T, SLAB_TOP, x0 + RISE_T + INS_T, -FL_BOARD - 90), box(x1 - RISE_T - INS_T, SLAB_TOP, x1 - RISE_T, -FL_BOARD - 90),
                           box(x0, SLAB_TOP - SLAB_T - INS_T, x0 + INS_W, SLAB_TOP - SLAB_T), box(x1 - INS_W, SLAB_TOP - SLAB_T - INS_T, x1, SLAB_TOP - SLAB_T)])
        insul_fill(A, ins)
        for a, b in boards:
            A.lines([[(max(a, x0 + RISE_T), -FL_BOARD - 90), (min(b, x1 - RISE_T), -FL_BOARD - 90)]], '10_見えがかり', lw=0.07, color='0.4', z=5)   # 大引の下端（見えがかり）
    return occ

MIRROR_LAYERS, MIRROR_FC = ('10m_', '20m_'), '#DCE5EE'
def draw_visible(A, items, occ):
    """items=[(ob, silhouette)] 近い順。見える線だけ描く"""
    occ = occ if occ is not None else Polygon()
    for i, (ob, sil) in enumerate(items):
        if sil is None or sil.is_empty: continue
        k = kind(ob['layer']); lay = LAYER_OF[k][1]
        vis = sil.boundary.difference(occ.buffer(2)) if not occ.is_empty else sil.boundary
        if ob['layer'].startswith(MIRROR_LAYERS):             # 光の筋の鏡面（アルミ）：見える所に薄い銀の地と細い斜線（断面D、ユーザー 10-29：ここが鏡面と示す）
            mv = sil.difference(occ) if not occ.is_empty else sil
            if not mv.is_empty and mv.area > 1e4: A.fill(mv, '14_鏡面', fc=MIRROR_FC, z=2.6, hatch='/////')
        A.geom_lines(vis, lay, lw={'furn': 0.1, 'glass': 0.09}.get(k, 0.13), color={'glass': '#3d6f9a', 'furn': '0.25'}.get(k, 'k'), z=3)
        if k != 'glass':
            occ = unary_union([occ, sil]) if not occ.is_empty else sil
            if i % 40 == 39: occ = occ.simplify(1)
    return occ

# ---------------------------------------------------------------- 平面
UP_DASH = r'^(23|28|30|50a|50c|51w|82|83)_'
UP_LIGHT = r'^(10t|20t)_'                     # 光の筋：切断より上なら想像線
ROOM_RE = r'^(3[1-4]|36|4[1-5]|5[2-47]|59)[a-z]?_'     # 部屋の色の板（床の面積の板）
CUT1, FL2 = 1500, 3250                        # 1 階は FL+1500 で切る（10-27 監修）、2 階の床の高さ
CUT2 = FL2 + 1000                             # 2 階は 2FL+1000 で切る（10-26 監修）   # 切断より上でも想像線（二点鎖線、10-28 JIS）で示す物（越屋根・2階の床の縁・遊戯室の上の遊具・天袋、10-27 監修）
ROOM_LAYERS = lambda ln: bool(re.match(ROOM_RE, ln))
# 部屋の色（決定事項（共通）の「色」、プレゼンの準備 renkei/open/20261024-1927-present、ユーザー10-24夜）：
# こどもの部屋は緑のグラデーション、こどものみんなの場所、通り・つなぐ場所（はだし）とその土足、大人は一つの色相（キッチンは濃く）、水まわり
KIDS = [('0・1歳', '#E6EFC2'), ('2歳', '#C5DE9A'), ('3歳', '#9FCB84'), ('4歳', '#86BC78'), ('5歳', '#6FA96E')]
C_ALL, C_STREET, C_DOSOKU, C_ADULT, C_ADULT2, C_WATER = '#F6E3A4', '#E9DFCF', '#D8CCB8', '#D9D3EC', '#C9C1E3', '#D5EBEE'
def room_color(ln):
    n = ln.split('_')[0]
    if n in ('31', '34'): return C_ALL
    if n in ('33', '56', '41') or re.search(r'1F_(ホール|西吹き抜け|通り抜け|路地)', ln): return C_STREET
    if n in ('52',): return C_DOSOKU
    if n in ('32', '57'): return C_ADULT2
    if re.search(r'便所・倉庫|多目的便所|便所（こども）', ln): return C_WATER
    for k, c in KIDS:
        if k in ln: return c
    if n in ('36', '35', '42', '43', '43b', '44', '45') or re.search(r'事務|医務|静養室|園長室|応接|便所（職員）|倉庫', ln): return C_ADULT
    return None
# 床の板（部屋の層でない）の色：本館の床・内縁側は通りの色（部屋の色がその上に重なる）、外縁側・あまのがわは土足
SLAB_COLOR = {'12': C_STREET, '13': C_STREET, '14': C_DOSOKU, '15': C_DOSOKU}
STREET_NOLINE = ('12', '13')     # ホール・西吹き抜け・内縁側のあいだの線は描かない（こどもには一つの場所、ユーザー）

def room_name(ln):
    s = re.sub(r'^\d+[a-z]?_', '', ln); s = re.sub(r'^(1F|2F)_', '', s); return re.sub(r'（.*?）', '', s)

def plan(A, zcut, objs, overhead, level_z, rooms_also=(), void_shift=None):
    below, cut, swings, stairs = [], [], [], []
    swings2, hidden, hidden_low, sliders, up_dash = [], [], [], [], []
    for ob in objs:
        if ROOM_LAYERS(ob['layer']): continue
        if ob['layer'].startswith('19d') and '開き戸' in ob.get('name', ''): swings.append(ob); continue   # 開き戸は開いた形と弧で（下）
        if ob['layer'].startswith('35d'): swings2.append(ob); continue                                     # 機械室の両開きの戸も開いた形と弧で
        if ob['layer'].startswith(('16_', '19_')) and ob['T'][:, :, 2].min() <= level_z + 50 and np.ptp(ob['T'][:, :, 2]) > 1800 and ob['T'][:, :, 2].max() > zcut:
            sliders.append(ob); continue                                                                    # 床からの引き戸（縁側のガラス戸・南の入口）：引違いの記号で（下）
        if (kind(ob['layer']) == 'glass' or is_fitting(ob['layer'])) and not re.match(r'^(10t|20t|28|50a)_', ob['layer']):
            zz = ob['T'][:, :, 2]
            if zz.min() >= zcut and zz.min() < level_z + 3000: hidden.append(ob); continue                 # 切断より上の窓（高窓）：破線
            if zz.max() <= zcut and zz.min() >= level_z + 50: hidden_low.append(ob)                         # 切断より下の窓（地窓）：壁の中なら破線（下）
        z = ob['T'][:, :, 2]
        if re.match(r'^(10t|20t)_', ob['layer']) and z.min() >= zcut: up_dash.append(ob); continue      # 光の筋：上部の想像線（10-27 監修、10-28 二点鎖線）
        if num(ob['layer']) in (10, 20) and not (ob['layer'].startswith('10s_') and z.min() < level_z + 100): continue   # 屋根（太陽光も）は上部の外形だけ（2階では軒が切断の高さより低い所がある）。南の軒の柱（10s、床から）は切る
        if num(ob['layer']) == 25: stairs.append(ob); continue                                                   # 階段は踏面の線と矢印で（下）
        if num(ob['layer']) == 94 and z.max() > zcut: overhead.append(ob); continue   # 園庭の木：樹冠を想像線で
        # 切断より上の物は描かない。ただし越屋根・2階の床の縁（吹抜の縁）・遊戯室の上の遊具・天袋だけは破線（10-27 監修：1.5 m より上は見えない、あえて示す物は点線）
        if z.min() >= zcut:
            if re.match(UP_DASH, ob['layer']): up_dash.append(ob)
            continue
        if is_beam(ob['layer']): continue                                                # 梁は描かない（平面の切断より上、ユーザー10-24：梁は見えない）
        if z.max() > zcut: cut.append(ob)
        else: below.append(ob)
    items = []
    for ob in cut:
        segs = slice_tris(ob['T'], np.array([0, 0, zcut]), np.array([0, 0, 1.]))
        S2 = [(s[0][:2], s[1][:2]) for s in segs]; items.append((ob, poche(S2), S2))
    occ = draw_cut(A, items)
    # 窓台：壁を窓の下（床+300）でも切り、切断の高さに無い所（＝窓の下の腰壁）を細線で（製図の決まり：窓は壁の線を細く通して描く）
    wl_cut = [pc for ob, pc, sg in items if wall_group(ob) and pc is not None and not pc.is_empty]
    BLK = unary_union([pc.buffer(0) for ob, pc, sg in items if wall_group(ob) == 'wall' and pc is not None and not pc.is_empty]) if items else Polygon()
    def hidden_win(cls):
        """切断より上（高窓）・下（地窓）の窓：破線。黒く塗った外壁の中では白い破線（灰色では黒に消えて、窓が無いように見えていた、10-26 監修）"""
        for cl in cls:
            ls_ = LineString(cl)
            if ls_.length < 1: continue
            inw = ls_.intersection(BLK.buffer(-5)) if not BLK.is_empty else LineString()
            out = ls_.difference(BLK.buffer(-5)) if not BLK.is_empty else ls_
            if not inw.is_empty: A.geom_lines(inw, '13_見えがかり（窓台・隠れた窓）', lw=0.16, ls=(0, (3, 2)), color='w', z=6.4)
            if not out.is_empty and out.length > 30: A.geom_lines(out, '13_見えがかり（窓台・隠れた窓）', lw=0.1, ls=(0, (3, 2)), color='0.3', z=6.4)
    if wl_cut:
        WC = unary_union([g.buffer(0) for g in wl_cut])
        low = []
        for ob, pc, sg in items:
            if not wall_group(ob): continue
            sg2 = slice_tris(ob['T'], np.array([0, 0, level_z + 300]), np.array([0, 0, 1.]))
            pc2 = poche([(q[0][:2], q[1][:2]) for q in sg2])
            if pc2 is not None and not pc2.is_empty: low.append(pc2.buffer(0))
        if low:
            sill = unary_union(low).difference(WC.buffer(5))
            sill = unary_union([g for g in getattr(sill, 'geoms', [sill]) if g.geom_type == 'Polygon' and g.area > 2e4])
            if not sill.is_empty:
                A.geom_lines(sill.boundary.difference(WC.buffer(3)), '10_見えがかり', lw=0.1, z=5.8)
                occ = unary_union([occ, sill]) if occ is not None else sill
        # 地窓（切断より下）で壁の中に隠れる窓：破線
        for ob in hidden_low:
            fp = silhouette(ob['T'][:, :, :2])
            if fp is None or fp.is_empty or fp.intersection(WC.buffer(10)).area < 0.6 * fp.area: continue
            below[:] = [x for x in below if x is not ob]
            hidden_win(centerlines(fp))
    # 床からの引き戸（引違い）：戸の板を一枚おきに内と外のレールへ ±30 ずらし、隣と 40 重ねる（製図の引違い戸の記号。3dm では一つの面に並んでいる）
    if sliders:
        pan = []
        for ob in sliders:
            fp = silhouette(ob['T'][:, :, :2])
            if fp is None or fp.is_empty: continue
            for cl in centerlines(fp):
                if len(cl) == 2: pan.append(np.array(cl))
        uniq = []
        for l in pan:                              # ガラスと框が同じ所に二つある：一つに
            if not any(np.linalg.norm(l.mean(0) - q.mean(0)) < 60 for q in uniq): uniq.append(l)
        uniq.sort(key=lambda l: math.atan2(*(l.mean(0) - C)[::-1]))
        k_ = 0
        for i, l in enumerate(uniq):
            if i and np.linalg.norm(l.mean(0) - uniq[i - 1].mean(0)) > 1300: k_ = 0    # 離れた所は新しい並び
            d_ = (l[1] - l[0]) / np.linalg.norm(l[1] - l[0]); n_ = np.array([-d_[1], d_[0]])
            off = n_ * (30 if k_ % 2 else -30)
            A.lines([[l[0] - d_ * 20 + off, l[1] + d_ * 20 + off]], '07_切断（建具）', lw=0.18, z=6.3)
            k_ += 1
    # 高窓（切断より上の窓・ガラス）：破線。戸の真上の欄間（鴨居の上のはめ殺し）は戸の線と重なるので描かない
    below_fit = unary_union([g for g in (silhouette(ob['T'][:, :, :2]) for ob in sliders + [o for o, pc, sg in items if is_fitting(o['layer']) or kind(o['layer']) == 'glass']) if g is not None]) if (sliders or items) else Polygon()
    for ob in hidden:
        fp = silhouette(ob['T'][:, :, :2])
        if fp is not None and not fp.is_empty and not below_fit.is_empty and fp.intersection(below_fit.buffer(80)).area > 0.5 * fp.area: continue
        if fp is not None and not fp.is_empty:
            hidden_win(centerlines(fp))
    below.sort(key=lambda ob: -ob['T'][:, :, 2].max())
    draw_visible(A, [(ob, silhouette(ob['T'][:, :, :2])) for ob in below if ob['layer'].split('_')[0] not in STREET_NOLINE], occ)
    # 上部（想像線＝細い二点鎖線、JIS A 0150）：屋根は片をまとめた外形だけ（片の継ぎ目・光の筋・太陽光の線は部屋を横切るので描かない、10-24）、木の樹冠は一本ずつ
    roof_sil = [silhouette(ob['T'][:, :, :2]) for ob in overhead if num(ob['layer']) in (10, 20) and re.match(r'^(10|20)_', ob['layer'])]
    roof_sil = [g.buffer(30) for g in roof_sil if g is not None and not g.is_empty]
    if roof_sil:
        ru = unary_union(roof_sil).buffer(-30)
        ru = unary_union([Polygon(g.exterior) for g in getattr(ru, 'geoms', [ru]) if g.geom_type == 'Polygon'])   # 光の筋の穴は外形に入れない
        A.geom_lines(ru.boundary, '20_上部（屋根の外形・梁）', lw=LW_THIN, color='0.4', ls=LS_PHANTOM, z=7)
    for ob in overhead:
        if num(ob['layer']) in (10, 20): continue
        A.geom_lines(silhouette(ob['T'][:, :, :2]), '20_上部（屋根の外形・梁）', lw=LW_THIN, color='0.4', ls=LS_PHANTOM, z=7)
    # 切断より上の、あえて示す物（光の筋・越屋根・2階の床の縁＝吹抜の縁・遊戯室の上の遊具・天袋）：レイヤーごとに外形をまとめて細い二点鎖線（想像線）。切った壁の上は描かない
    WALLS = unary_union([pc.buffer(0) for ob, pc, sg in items if (wall_group(ob) or kind(ob['layer']) == 'struct') and pc is not None and not pc.is_empty]) if items else Polygon()
    byl_up = {}
    for ob in up_dash:
        g = silhouette(ob['T'][:, :, :2])
        if g is not None and not g.is_empty: byl_up.setdefault(ob['layer'], []).append(g.buffer(5))
    for ln_, gs in byl_up.items():
        g = unary_union(gs).buffer(-5)
        ln_g = g.boundary if g.geom_type in ('Polygon', 'MultiPolygon') else g
        if not WALLS.is_empty: ln_g = ln_g.difference(WALLS.buffer(5))
        A.geom_lines(ln_g, '20_上部（屋根の外形・梁）', lw=LW_THIN, color='0.45', ls=LS_PHANTOM, z=7)
    # 階段（JIS の製図の慣習、10-27 監修）：1 階は上り口から切断の位置までの踏面を実線、切断の位置に斜めの二重の破断線、その先は描かない。
    # 矢印は上り口から破断線まで「上」。2 階は階段全体を実線、降り口から矢印「下」。手すりの線（段の両脇から 60 内）も
    for ob in stairs:
        T = ob['T']; flat = [t for t in T if np.ptp(t[:, 2]) < 1]
        lv = {}
        for t in flat: lv.setdefault(round(t[0, 2]), []).append(Polygon(t[:, :2]).buffer(0.5))
        zs = sorted(lv); steps = []
        for i, zz in enumerate(zs):
            g = unary_union(lv[zz]).buffer(-0.5)
            if g.is_empty or g.area < 5e4: continue
            if steps and zz - steps[-1][0] < 80:                 # 段板の下面と上面：一つに（高さは上面、形は二つを合わせた外形）
                steps[-1] = (zz, unary_union([steps[-1][1], g]))
            else: steps.append((zz, g))
        if len(steps) < 3: continue
        on2 = level_z > 1000
        # 走り（段の続き）と踊り場（大きい板）に分ける
        flights, cur = [], []
        for zz, g in steps:
            if g.area < 1.0e6: cur.append((zz, g))
            else:
                if cur: flights.append(cur); cur = []
        if cur: flights.append(cur)
        clip = None; brk = None
        if not on2:
            # 切断の高さを走りの中で求める（最後に切断より下の段と次の段の間を高さで割り振る）
            nxt = {id(fl[-1][1]): next((zz for zz, g in steps if zz > fl[-1][0]), 1e9) for fl in flights}   # 走りの次の板（踊り場）の高さ
            for fl in flights:
                lo = [k for k, (zz, g) in enumerate(fl) if zz <= zcut]
                if not lo: break
                if len(lo) == len(fl) and nxt[id(fl[-1][1])] <= zcut: continue      # この走りと次の踊り場は切断より下：次の走りへ
                k = lo[-1]
                c = [np.array(g.centroid.coords[0]) for zz, g in fl]
                if len(c) < 2: continue
                dk = c[min(k + 1, len(c) - 1)] - c[max(k - 1, 0)]
                dk = dk / np.linalg.norm(dk); go = np.mean([np.linalg.norm(c[i + 1] - c[i]) for i in range(len(c) - 1)])
                rise = np.mean([fl[i + 1][0] - fl[i][0] for i in range(len(fl) - 1)])
                pc_ = c[k] + dk * go * min(max((zcut - fl[k][0]) / rise, 0), 1.0)
                nk = np.array([-dk[1], dk[0]])
                wid = abs((np.array(fl[k][1].convex_hull.exterior.coords) - c[k]) @ nk).max()
                brk = (pc_, dk, nk, wid, fl[:k + 1], fl)
                break
        # 段の線（上の段から順に、上の段の形で下の段の線を隠す）
        if on2: vis_steps = steps
        elif brk is not None:
            pc_, dk, nk, wid, fl_lo, fl_ = brk
            vis_steps = [(zz, g) for zz, g in steps if zz <= fl_lo[-1][0] and zz <= zcut]
            s1 = pc_ - dk * 150 - nk * (wid + 20); s2 = pc_ + dk * 150 + nk * (wid + 20)     # 破断線（斜め）
            far = 1e5
            clip = Polygon([s1, s2, s2 - dk * far, s1 - dk * far])                            # 破断線より手前（上り口の側）だけ
        else:
            vis_steps = [(zz, g) for zz, g in steps if zz <= zcut]
        occ_s = Polygon()
        for zz, g in sorted(vis_steps, key=lambda q: -q[0]):
            ln_ = g.boundary.difference(occ_s.buffer(2)) if not occ_s.is_empty else g.boundary
            if clip is not None: ln_ = ln_.intersection(clip)
            A.geom_lines(ln_, '45_階段', lw=0.1, z=6)
            occ_s = unary_union([occ_s, g])
        # 手すりの線：走りごとに、段の両脇から 60 内
        for fl in flights:
            if len(fl) < 2: continue
            c = np.array([np.array(g.centroid.coords[0]) for zz, g in fl])
            d0 = c[-1] - c[0]; d0 = d0 / np.linalg.norm(d0); n0 = np.array([-d0[1], d0[0]])
            P_ = np.vstack([np.array(g.convex_hull.exterior.coords) for zz, g in fl])
            t_ = (P_ - c[0]) @ d0; w_ = (P_ - c[0]) @ n0
            for w in (w_.min() + 60, w_.max() - 60):
                hl = LineString([c[0] + d0 * t_.min() + n0 * w, c[0] + d0 * t_.max() + n0 * w])
                if not on2:
                    if fl[0][0] > (brk[4][-1][0] if brk is not None else zcut): continue
                    if clip is not None: hl = hl.intersection(clip)
                A.geom_lines(hl, '45_階段', lw=0.07, color='0.3', z=6.2)
        # 破断線（二重）
        if brk is not None:
            for o_ in (0, 70):
                A.lines([[s1 - dk * o_, s2 - dk * o_]], '45_階段', lw=0.13, z=7, annot=True)
        # 矢印
        if on2:
            path = np.array([np.array(g.centroid.coords[0]) for zz, g in steps if g.area < 1.0e6])[::-1]; lab = '下'
        else:
            if brk is None: continue
            path = np.array([np.array(g.centroid.coords[0]) for zz, g in brk[4]] + [brk[0] - brk[1] * 80])
            lab = '上'
        if len(path) < 2: continue
        A.lines([path], '45_階段', lw=0.13, z=7, annot=True)
        d_ = path[-1] - path[-2]; d_ = d_ / max(np.linalg.norm(d_), 1e-6); nn = np.array([-d_[1], d_[0]])
        A.lines([[path[-1] - d_ * 250 + nn * 120, path[-1], path[-1] - d_ * 250 - nn * 120]], '45_階段', lw=0.13, z=7, annot=True)
        A.text(path[0][0], path[0][1], lab, PT_NOTE, '45_階段', box=True)
    # 吹抜（2 階）：西館の 1 階の部屋の上で、2 階の床の無い所。対角の細い線と「吹抜」
    if level_z > 1000:
        f1 = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if re.match(r'^(31|32|33|34|36|57)_', ob['layer'])]
        f2 = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if re.match(r'^(23|25)_', ob['layer'])]
        f1 = unary_union([g for g in f1 if g is not None]); f2 = unary_union([g for g in f2 if g is not None])
        void = f1.difference(f2.buffer(30))
        if void_shift is not None: void = shp_affinity.translate(void, *void_shift)   # 2階をずらして置くとき（3枚目の平面、10-25）
        for g in getattr(void, 'geoms', [void]):
            if g.geom_type != 'Polygon' or g.area < 3e6: continue
            mr = np.array(g.minimum_rotated_rectangle.exterior.coords)[:4]
            for a_, b_ in ((mr[0], mr[2]), (mr[1], mr[3])):
                A.geom_lines(LineString([a_, b_]).intersection(g), '45_吹抜', lw=0.07, color='0.45', z=5)
            from shapely.ops import polylabel as _pl
            q = _pl(g, 50)
            A.text(q.x, q.y, '吹抜' + ('（遊戯室）' if g.area > 50e6 else ''), PT_NOTE, '45_吹抜', box=True)
    # 開き戸：開いた位置の板（90°）と、閉じた位置からの弧（3dm の戸の板の名前に吊元と開く向き、add_inner.py）。
    # 板も弧も壁の外に（10-27 監修）：板や弧が切った壁の中に入る所は、図では吊元を壁の面へ寄せる（3dm の名前の吊元が壁の中にあるときも）
    def swing_door(hp, cd, od, R_):
        if not WALLS.is_empty:
            Wb = WALLS.buffer(-1)
            for _ in range(3):
                # 開いた板が、自分の壁（開く向きの厚さ）に入る分：開く向きへ壁の面まで
                t_ = 0.0
                while t_ < 400 and (Wb.contains(Point(*(hp + od * (t_ + 2) + cd * 18))) or Wb.contains(Point(*(hp + od * (t_ + 2) + cd * 2)))): t_ += 5
                hp = hp + od * t_
                # 開いた板が、脇の壁（開く向きに続く壁）に入る分：戸の幅の向きへ壁の面まで（戸の幅はその分だけ狭く描く）
                leaf_ = Polygon([hp, hp + cd * 36, hp + cd * 36 + od * R_, hp + od * R_])
                hit = leaf_.intersection(Wb)
                if hit.is_empty or hit.area < 50: break
                pts_ = np.vstack([np.array(g_.exterior.coords) for g_ in getattr(hit, 'geoms', [hit]) if g_.geom_type == 'Polygon'])
                sft = max(((pts_ - hp) @ cd).max(), 0) + 5
                hp = hp + cd * sft; R_ = R_ - sft
        arc = [hp + (cd * math.cos(t_) + od * math.sin(t_)) * R_ for t_ in np.linspace(0, math.pi / 2, 30)]
        sec = Polygon([hp] + arc)
        if not WALLS.is_empty and sec.intersection(WALLS.buffer(-1)).area > 2e3:
            print('  開き戸の弧が壁に入る（図では直せない、3dm で）', np.round(hp), round(sec.intersection(WALLS).area / 1e4) / 100, 'm²')
        A.lines([np.array(arc)], '40_建具', lw=0.08, color='0.25', z=6)
        A.fill(Polygon([hp, hp + cd * 36, hp + cd * 36 + od * R_, hp + od * R_]), '40_建具', fc='k', z=6)
    sh2 = np.array(void_shift) if void_shift is not None else np.zeros(2)
    for ob in swings:
        if abs(ob['T'][:, :, 2].min() - level_z) > 600: continue
        mm_ = re.search(r'W(\d+) 吊元 (-?[\d.]+),(-?[\d.]+) 開く (-?[\d.]+),(-?[\d.]+)', ob['name'])
        if not mm_: continue
        Wd = float(mm_.group(1)); hp = np.array([float(mm_.group(2)), float(mm_.group(3))]) + sh2; od = np.array([float(mm_.group(4)), float(mm_.group(5))])
        P_ = ob['T'][:, :, :2].reshape(-1, 2); far = P_[np.argmax(np.linalg.norm(P_ - hp, axis=1))]
        cd = (far - hp) / max(np.linalg.norm(far - hp), 1e-6)
        cd = cd - od * (cd @ od); cd = cd / max(np.linalg.norm(cd), 1e-6)
        swing_door(hp, cd, od, Wd - 10)
    # 機械室の両開きの戸（外開き）：扉ごとに、外の端を吊元に、機械室の外へ 90° 開いた形と弧
    if swings2:
        mach = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if re.match(r'^35_', ob['layer'])]
        mach = unary_union([g for g in mach if g is not None])
        leaves = []
        for ob in swings2:
            if abs(ob['T'][:, :, 2].min() - level_z) > 600: continue
            fp = silhouette(ob['T'][:, :, :2]); cl = centerlines(fp)
            if cl and len(cl[0]) == 2: leaves.append(np.array(cl[0]))
        if leaves:
            mid = np.mean([l.mean(0) for l in leaves], 0)
            mc = np.array(mach.centroid.coords[0]) if not mach.is_empty else mid
            for l in leaves:
                hp, far = (l[0], l[1]) if np.linalg.norm(l[0] - mid) > np.linalg.norm(l[1] - mid) else (l[1], l[0])
                cd = (far - hp) / np.linalg.norm(far - hp); od = np.array([-cd[1], cd[0]])
                if np.dot(od, l.mean(0) - mc) < 0: od = -od
                swing_door(hp, cd, od, np.linalg.norm(far - hp))
    # 引き戸（室内の片引き・引き分け、19c・19d・19e）：閉じた位置の板（切断の細線）と、引く側の線（開いた位置）。壁の中へ引き込むなら壁の中を破線（10-27 監修）。
    # 引く側は、板の端の先に壁が続く側（add_inner.py の決め方と同じ）。隣に並ぶ板（引違い・引き分けの相手）の側へは引かない
    sl_ = []
    for ob in objs:
        if not re.match(r'^(19c|19d|19e)_', ob['layer']) or '開き戸' in ob.get('name', ''): continue
        z_ = ob['T'][:, :, 2]
        if z_.min() > level_z + 300 or z_.max() < zcut: continue
        fp = silhouette(ob['T'][:, :, :2])
        if fp is None or fp.is_empty: continue
        for cl in centerlines(fp):
            if len(cl) == 2 and np.linalg.norm(np.subtract(cl[1], cl[0])) > 400: sl_.append(np.array(cl, float))
    if sl_ and not WALLS.is_empty:
        Wb = WALLS.buffer(-1)
        for i, l in enumerate(sl_):
            Lw = np.linalg.norm(l[1] - l[0]); d_ = (l[1] - l[0]) / Lw; n_ = np.array([-d_[1], d_[0]])
            best = None
            for e, sg in ((l[0], -1), (l[1], +1)):
                s_ = d_ * sg
                # 相手の板（平行で近く、この端の先にある）
                if any(j != i and abs(abs((q[1] - q[0]) @ d_) / np.linalg.norm(q[1] - q[0]) - 1) < 0.02 and abs((q.mean(0) - l.mean(0)) @ n_) < 150
                       and ((q.mean(0) - l.mean(0)) @ s_) > 0 and ((q.mean(0) - l.mean(0)) @ s_) < Lw + 200 for j, q in enumerate(sl_)): continue
                ts = np.linspace(100, Lw * 0.9, 8)
                pocket = np.mean([Wb.contains(Point(*(e + s_ * t))) for t in ts])
                along = np.mean([any(Wb.contains(Point(*(e + s_ * t + n_ * k))) for k in (-200, -120, -70, 70, 120, 200)) for t in ts])
                sc = max(pocket, along)
                if sc >= 0.6 and (best is None or sc > best[0]): best = (sc, e, s_, pocket >= 0.6)
            if best is None: continue
            sc, e, s_, pk = best
            ol = LineString([e + s_ * 30, e + s_ * Lw])
            if pk:
                A.geom_lines(ol, '40_建具', lw=0.13, color='w', ls=(0, (3, 2)), z=6.5)    # 壁の中（黒の上）は白い破線
                A.geom_lines(ol.difference(WALLS), '40_建具', lw=0.09, color='0.3', ls=(0, (3, 2)), z=6.5)
            else:
                A.geom_lines(ol, '40_建具', lw=0.09, color='0.3', z=6.3)
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
        if abs(ob['T'][:, :, 2].max() - level_z) > 1200 and not ob['layer'].startswith(rooms_also): continue
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
        fc_ = room_color(ln_)
        if fc_: A.fill(unary_union(sils).buffer(-5, join_style=2), '06_部屋の色', fc=fc_, z=0.8)
        # 医務の赤十字はやめた（10-26 監修：赤十字の標章は法律（赤十字の標章及び名称等の使用の制限に関する法律）で使える人が限られる。部屋名で足りる）
    # 0・1歳の水まわり（沐浴・小さな便器・おむつ替え）と2歳のトイレは、部屋の板の中にある（面積は保育室に含める）ので、
    # 色だけ水まわりに塗る（ユーザー 10-26：平面図の0・1歳、2歳のトイレをトイレの色に）。範囲は scripts/plan01.py の water core（u9〜12）・
    # plan02.py の toilet（u12〜14.7）、v1.6〜4.6（しつらえの段がこの二つの図から部屋を作る）
    if level_z < 1000:
        _kid = unary_union([unary_union(v) for k, v in BYL.items() if re.search(r'0・1歳|2歳', k)]) if BYL else Polygon()
        def _uvrect(u0, u1, v0, v1):
            us = np.linspace(u0, u1, 12)
            return Polygon([at(205000 - v0 * 1000, theta_u(u * 1000)) for u in us] + [at(205000 - v1 * 1000, theta_u(u * 1000)) for u in us[::-1]])
        for r_ in ((9.0, 12.0, 1.6, 4.6), (12.0, 14.7, 1.6, 4.6)):
            g_ = _uvrect(*r_).intersection(_kid.buffer(-5, join_style=2)) if not _kid.is_empty else Polygon()
            if not g_.is_empty: A.fill(g_, '06_部屋の色', fc=C_WATER, z=0.82)
    if level_z < 1000:                               # 床の板（部屋の層でない）
        for ob in objs:
            c_ = SLAB_COLOR.get(ob['layer'].split('_')[0])
            if not c_: continue
            sil = silhouette(ob['T'][:, :, :2])
            if sil is not None and not sil.is_empty: A.fill(sil, '06_部屋の色', fc=c_, z=0.7)
    for ln_, sils in BYL.items():
        if level_z > 1000 and ln_.startswith(rooms_also): continue   # 2 階から見下ろす 1 階の部屋（遊戯室）は色だけ。名前と面積は 1 階に（2 階は「吹抜（遊戯室）」、10-26 監修）
        ob = {'layer': ln_}
        sil = unary_union(sils).buffer(-5, join_style=2)
        allp = [g for g in getattr(sil, 'geoms', [sil]) if g.area >= 0.5e6]
        parts = [g for g in allp if g.area >= 2e6]                    # 2 m² 以上の部屋に名前（教材庫 約3.5 など、10-25）
        for g in parts:
            a = g.area
            if W_LV is not None:
                inner = g.difference(W_LV); a = inner.area + 0.5 * W_LV.intersection(inner.buffer(250)).area
            if len(allp) == 1 and ln_ in TAB: a = TAB[ln_] * 1e6          # 一つのレイヤーに部屋が二つ以上なら、それぞれを測る（表の数は合計）
            from shapely.ops import polylabel as _pl
            p = _pl(g.buffer(-150) if g.buffer(-150).geom_type == 'Polygon' and not g.buffer(-150).is_empty else g, 20)   # 壁からいちばん遠い点（線に重ならない）
            nm_ = room_name(ob["layer"])
            # 字の幅（1/100、PT_ROOM の 1 字）が部屋の短い方の幅の 8 割を超えたら「・」で折る
            mr_ = np.array(g.minimum_rotated_rectangle.exterior.coords); wmin = min(np.linalg.norm(mr_[1] - mr_[0]), np.linalg.norm(mr_[2] - mr_[1]))
            if len(nm_) * PT_ROOM * PT2MM * 100 > 0.8 * wmin and '・' in nm_:
                i_ = nm_.index('・', len(nm_) // 3) if '・' in nm_[len(nm_) // 3:] else nm_.index('・')
                nm_ = nm_[:i_ + 1] + '\n' + nm_[i_ + 1:]
            A.text(p.x, p.y, f'{nm_}\n{a / 1e6:.1f} m²', PT_ROOM, '60_部屋名・面積', box=True)

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
            ('B', 'u', 21750.0, 'あまのがわ（スパン 8+0.75）　南の入口・キッチン・2 階・すき間・本館・縁側、北を見る'),
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
    plan_long_dims(A)

# ---- 曲がった建物の寸法（項 20261028-1351-kanshu）：寸法は通り芯（放射の架構 1〜20・円弧の柱の列）の上に。
# 弧に沿う長さは弧の寸法（JIS：数値の前に「⌒」）で、どの円弧の上の長さかを字で書く。数はすべて 3dm から（柱・床・屋根）
def _frame_th():
    """架構の角度（柱の中心から、丸めない。TH_S は 1e-4 rad に丸めてあり、スパンが ±20 mm ずれる）。TH_S と同じ順"""
    th = np.array([float(unwrap(math.atan2(*(ob['T'].reshape(-1, 3)[:, :2].mean(0) - C)[::-1]))) for ob in OBJ if ob['layer'].startswith('11a')])
    return [float(th[np.abs(th - t) < 3e-4].mean()) for t in TH_S]
# 断面 D（項 20261029-0946-present）：本館の横断、架構 19 の線（2 枚の梁のあいだ＝光の筋の溝）で切る、5 歳の部屋（架構 18〜20）の真ん中。
# 光の筋の溝は幅約 170 mm なので、丸めた TH_S（±20 mm）でなく柱の中心から出した架構の角度で切る。紙は別（sodachiya_sections2_1-100）
SEC_D_K = 19
SEC_D_SKIP = r'^67c_'          # 読書の庭の木（本館の西の外、木は断面に出さない）。zumen.py も json から読む
SECTIONS.append(('D', 'u', SGN * (_frame_th()[SEC_D_K - 1] - TH_S[0]) * 205000.0,
                 f'本館の横断（架構{SEC_D_K}の線＝光の筋で切る、5歳）、北を見る'))
def _rows():
    """柱の列の半径（W・E、柱の中心の平均を 10 mm に丸める：網の目の中心は数 mm ずれる）"""
    r = np.array([float(np.hypot(*(ob['T'].reshape(-1, 3)[:, :2].mean(0) - C))) for ob in OBJ if ob['layer'].startswith('11a')])
    return round(float(r[r > r.mean()].mean()), -1), round(float(r[r < r.mean()].mean()), -1)
def _vmax(prefix):
    P = np.vstack([ob['T'].reshape(-1, 3)[:, :2] for ob in OBJ if ob['layer'].startswith(prefix)])
    return _uv(P)
def _rot_txt(t):
    """向き t（モデルの xy）の線に沿う字の角度"""
    return ((math.degrees(math.atan2(t[1], t[0])) + 90) % 180) - 90
def _arrow(A, tip, d, L=250, w=75):
    """塗った矢（JIS の端末記号）。tip：先、d：矢の向き"""
    d = np.asarray(d, float); d = d / np.linalg.norm(d); n = np.array([-d[1], d[0]])
    A.fill(Polygon([tip, tip - d * L + n * w, tip - d * L - n * w]), DIML, fc=DIMC, z=9)

def _uarc(A, u0, u1, v, ext=250):
    """v の線の上の u0〜u1 の弧の寸法線と両端の印"""
    A.lines([np.array([_xy(u, v) for u in np.linspace(u0, u1, max(8, int(abs(u1 - u0) / 400)))])], DIML, lw=LW_THIN, color=DIMC, z=9)
    for u in (u0, u1): dim_ends(A, [_xy(u, v)], _xy(u + 1, v) - _xy(u, v), ext=ext)
def _utxt(A, u, v, txt):
    """v の線に沿う字（u, v の所）"""
    p = _xy(u, v); A.text(p[0], p[1], txt, DIMPT, DIML, rot=_rot_txt(_xy(u + 1, v) - p), color=DIMC, box=True)
def _vtxt(A, u, v, txt):
    """放射の線に沿う字"""
    p = _xy(u, v); A.text(p[0], p[1], txt, DIMPT, DIML, rot=_rot_txt(_xy(u, v + 1) - p), color=DIMC, box=True)

# 東の外（園庭の側）の寸法の段（v、m）。紙の右の縁は北の端で v 約 17.5 まで、下の縁は南の端で v 約 19.5 まで
V_ETOT, V_WTOT, V_WSPAN, V_ESPAN = 14300, 15500, 16600, 19400

def plan_long_dims(A):
    """長手：W 通り（背骨）の上のスパンと全体、E 通りの上のスパン 1 か所と全体、放射の線のあいだの角度、背骨の弦と矢高、円弧の半径。
    寸法線は東の外（園庭の側）の弧、架構の放射の線（通り芯）がそのまま寸法補助線。字にどの円弧の上の長さかを書く"""
    th = _frame_th(); RW, RE = _rows(); n_ = len(th) - 1
    uk = [SGN * (t - th[0]) * 205000 for t in th]
    dth = [abs(b - a) for a, b in zip(th, th[1:])]
    # W 通りの上のスパン（字は外へ）
    for k in range(n_):
        _uarc(A, uk[k], uk[k + 1], V_WSPAN)
        _utxt(A, (uk[k] + uk[k + 1]) / 2, V_WSPAN + 450, f'⌒{dth[k] * RW:,.0f}')
    tot = abs(th[-1] - th[0]); um = (uk[0] + uk[-1]) / 2
    sp = sorted({round(d * RW) for d in dth})
    sps = f'{n_}×⌒{sp[0]:,}' if len(sp) == 1 else f'{n_}スパン'
    _uarc(A, uk[0], uk[-1], V_WTOT)
    _utxt(A, um, V_WTOT + 450, f'⌒{tot * RW:,.0f}　W通り（R{RW:,.0f}、背骨）の上の長さ、架構1〜{n_ + 1}（{sps}、スパンもW通りの上）')
    # E 通りの上：全体（外縁側の中、E 通りの側）と、スパン 1 か所・放射の線のあいだの角度（南の端の外）
    _uarc(A, uk[0], uk[-1], V_ETOT)
    _utxt(A, um, V_ETOT - 450, f'⌒{tot * RE:,.0f}　E通り（R{RE:,.0f}）の上の長さ、架構1〜{n_ + 1}')
    k = 1
    _uarc(A, uk[k], uk[k + 1], V_ESPAN)
    _utxt(A, (uk[k] + uk[k + 1]) / 2, V_ESPAN + 450, f'⌒{dth[k] * RE:,.0f}（E通りの上）')
    k = 2; u0, u1 = uk[k], uk[k + 1]
    A.lines([np.array([_xy(u, V_ESPAN) for u in np.linspace(u0, u1, 12)])], DIML, lw=LW_THIN, color=DIMC, z=9)
    for u, s_ in ((u0, -1), (u1, 1)):                                 # 角度の寸法は両端に矢（JIS）
        _arrow(A, _xy(u, V_ESPAN), _xy(u + s_, V_ESPAN) - _xy(u, V_ESPAN))
    _utxt(A, (u0 + u1) / 2, V_ESPAN + 450, f'{math.degrees(dth[k]):.3f}°')
    print('plan dims 長手', [round(d * RW, 1) for d in dth[:3]], round(tot * RW), round(tot * RE), round(dth[1] * RE), round(math.degrees(dth[2]), 4))
    # 背骨の弦と矢高（全体の大きさ）：弦は想像線、矢高は真ん中の放射の線の上
    p0, p1 = at(RW, th[0]), at(RW, th[-1]); pm = at(RW, (th[0] + th[-1]) / 2); cm = (p0 + p1) / 2
    ch = float(np.linalg.norm(p1 - p0)); sg = float(np.linalg.norm(pm - cm))
    A.lines([[p0, p1]], DIML, lw=LW_THIN, color=DIMC, ls=LS_PHANTOM, z=9)
    dim_ends(A, [p0, p1], p1 - p0)
    A.lines([[pm, cm]], DIML, lw=LW_THIN, color=DIMC, z=9); dim_ends(A, [pm, cm], cm - pm, ext=150)
    _utxt(A, um + 12000, 1050, f'背骨（W通り）の弦は約{ch / 1000:.1f} m・矢高は約{sg / 1000:.1f} m（二点鎖線）')
    print('plan dims 弦・矢高', round(ch), round(sg))
    # 円弧の半径（中心は敷地の外：半径の線は途中で切り、切った端に中心の向きの印）。W・E は北の端の外、東の軒先は南の端の外
    ve = float(np.round(_vmax('10_')[:, 1].max(), -2))                # 東の軒先（屋根の東の縁、100 mm に丸める）
    # 字の置き場（v の中ほど）：E 通りは矢の西（北東の隣地境界の寸法を避ける）
    for R_, u_, lab, side, L_, vt in ((RW, uk[-1] + 550, 'W通り', 1, 2600, 1300), (RE, uk[-1] + 550, 'E通り', 1, 1400, -1300),
                                      (RW - ve, uk[0] - 1000, '東の軒先', -1, 2600, 1300)):
        v0 = 205000 - R_
        a, b = _xy(u_, v0), _xy(u_, v0 + L_); dc = (b - a) / np.linalg.norm(b - a)
        A.lines([[a, b]], DIML, lw=LW_THIN, color=DIMC, z=9)
        _arrow(A, a, -dc)                                              # JIS：半径の矢は弧の側
        nn = np.array([-dc[1], dc[0]])
        A.lines([[b - dc * 220 + nn * 120, b, b - dc * 220 - nn * 120]], DIML, lw=LW_THIN, color=DIMC, z=9)   # 切った端：中心の向き
        _vtxt(A, u_ + side * 330, v0 + vt, f'R{R_:,.0f}（{lab}）')
    print('plan dims 半径', RW, RE, RW - ve)

def plan_vdims(A):
    """短手（どの架構でも同じ、1 か所）：ホールの中、架構 9 の北の放射の線に沿って。W 通り（西の外壁の線）から 西吹き抜け（＝越屋根の幅）・
    保育室・内縁側・外縁側＝東の軒先、その北に全体。数は 3dm から（部屋の床・縁側の床・越屋根の高い壁・屋根の縁。通り芯の寸法なので
    100 mm に丸める：床の縁は 5 mm 重ねてある）"""
    R = lambda x: float(np.round(x, -2))
    v1 = R(_vmax('56_')[:, 1].max())                       # 西吹き抜け（窓辺）の東の縁＝保育室の西の壁（一本の線）
    vE = R(_vmax('53_')[:, 1].max())                       # 保育室の東の縁＝E 通り
    vi = R(_vmax('13_')[:, 1].max())                       # 内縁側の東の縁（外皮の線）
    vo = R(_vmax('14_')[:, 1].max())                       # 外縁側の東の縁
    ve = R(_vmax('10_')[:, 1].max())                       # 屋根の東の縁（軒先）
    hi = np.vstack([ob['T'].reshape(-1, 3) for ob in OBJ if ob['layer'].startswith('17_')])
    qh = _uv(hi[hi[:, 2] > 3800][:, :2]); kh = qh[(qh[:, 1] > 0.5 * v1) & (qh[:, 1] < 2 * v1), 1]
    vk = R((kh.min() + kh.max()) / 2) if len(kh) else None  # 越屋根の東の壁（高い所）の芯
    vs = [0.0, v1, vE, vi, vo] + ([ve] if ve > vo + 50 else [])
    names = ['西吹き抜け' + ('＝越屋根の幅' if vk == v1 else ''), '部屋の帯（保育室・ホールなど）', '内縁側', '外縁側', '軒']
    th_ = _frame_th(); uk = [SGN * (t - th_[0]) * 205000 for t in th_]
    uc = uk[8] + 650; ut = uk[8] + 1700                    # 架構 9 の北：寸法の連なり、その北に全体
    for v0, v1_, lb, nm in zip(vs, vs[1:], [f'{(b - a):,.0f}' for a, b in zip(vs, vs[1:])], names):
        A.lines([[_xy(uc, v0), _xy(uc, v1_)]], DIML, lw=LW_THIN, color=DIMC, z=9)
        dim_ends(A, [_xy(uc, v0), _xy(uc, v1_)], _xy(uc, v1_) - _xy(uc, v0))
        _vtxt(A, uc - 300, (v0 + v1_) / 2, lb)
        _vtxt(A, uc + 300, (v0 + v1_) / 2, nm)
    A.lines([[_xy(ut, vs[0]), _xy(ut, vs[-1])]], DIML, lw=LW_THIN, color=DIMC, z=9)
    dim_ends(A, [_xy(ut, vs[0]), _xy(ut, vs[-1])], _xy(ut, 1) - _xy(ut, 0))
    _vtxt(A, ut + 300, vs[0] + 0.69 * (vs[-1] - vs[0]), f'{vs[-1] - vs[0]:,.0f}　計（W通り〜東の軒先、どの架構でも同じ）')   # 字はホールの部屋名の東
    if vk is not None and vk != v1:
        A.lines([[_xy(ut, 0), _xy(ut, vk)]], DIML, lw=LW_THIN, color=DIMC, z=9); dim_ends(A, [_xy(ut, vk)], _xy(ut, 1) - _xy(ut, 0))
        _vtxt(A, ut - 300, vk / 2, f'{vk:,.0f}　越屋根の幅')
    print('plan dims 短手', vs, vk)

def plan_more_dims(A):
    """あまのがわの幅と位置（ホールの中、架構 8 から）、南の深い軒の出（架構 1 から、東の軒先と W 通りの外の角で）"""
    th = _frame_th(); uk = [SGN * (t - th[0]) * 205000 for t in th]
    q15 = _vmax('15_'); a0, a1 = float(np.round(q15[:, 0].min(), -2)), float(np.round(q15[:, 0].max(), -2))
    kf = int(np.argmin([abs(u - a0) for u in uk]))
    vd = 10600
    _uarc(A, a0, a1, vd)
    off = f'架構{kf + 1}から{a0 - uk[kf]:,.0f}北' if abs(a0 - uk[kf]) > 1 else f'架構{kf + 1}から'
    _utxt(A, (a0 + a1) / 2, vd - 450, f'{a1 - a0:,.0f}')
    _utxt(A, (a0 + a1) / 2, vd - 900, f'あまのがわ（W通りの上、{off}）')
    print('plan dims あまのがわ', a0, a1, kf + 1)
    # 南の深い軒：屋根の南の縁の東の角（東の軒先）と西の角
    q10 = _vmax('10_'); s_ = q10[q10[:, 0] < uk[0] - 500]
    ce = s_[np.argmax(s_[:, 1])]; cw = s_[np.argmin(s_[:, 1])]
    for (ue, v), vd2, nm in (((ce[0], ce[1]), ce[1] - 1100, None), ((cw[0], cw[1]), cw[1] - 800, '南の軒の出（架構1から、東の軒先→西の角）')):
        for u in (ue, uk[0]): _ext(A, _xy(u, v + (150 if vd2 < v else -150)), _xy(u, vd2 - 250), np.zeros(2))
        _uarc(A, ue, uk[0], vd2)
        L_ = float(np.round((uk[0] - ue) * (205000 - v) / 205000, -1))    # u は背骨の上の長さ。軒の角の弧の上の長さに直す
        _utxt(A, (ue + uk[0]) / 2, vd2 - 330, f'{L_:,.0f}' + ('' if nm else '　軒の出'))
        if nm: _vtxt(A, ue - 330, vd2 + 2000, nm)
        print('plan dims 南の軒', round(v), round(ue), L_)

def _uv(P2):
    """モデルの xy（mm）→ (u, v)：u は南の妻から北へ（背骨 r=205 m の弧長）、v は西の外壁の線から東へ"""
    d = np.asarray(P2, float)[:, :2] - C; th = unwrap(np.arctan2(d[:, 1], d[:, 0]))
    return np.c_[SGN * (th - TH_S[0]) * 205000, 205000 - np.hypot(d[:, 0], d[:, 1])]
def _xy(u, v): return at(205000 - v, theta_u(u))
def _foot(prefixes):
    gs = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if ob['layer'].split('_')[0] in prefixes]
    return unary_union([g for g in gs if g is not None and not g.is_empty])
def _ext(A, p, q, sh):
    """寸法の補助線（細い緑）"""
    A.lines([[np.asarray(p) + sh, np.asarray(q) + sh]], DIML, lw=0.05, color=DIMC, z=9)
def arc_dim(A, u0, u1, v, label, sh=np.zeros(2), L=None, pt=None):
    """u0〜u1 の弧の寸法線（v の線の上）。L：書く長さ（無ければ v の線の上の弧長）"""
    P = np.array([_xy(u, v) for u in np.linspace(u0, u1, 48)]) + sh
    A.lines([P], DIML, lw=LW_THIN, color=DIMC, z=9)
    for u in (u0, u1):
        dim_ends(A, [_xy(u, v) + sh], _xy(u + 1, v) - _xy(u, v), z=9)
    um = (u0 + u1) / 2; t = _xy(um + 1, v) - _xy(um, v); ang = math.degrees(math.atan2(t[1], t[0]))
    if L is None: L = abs(u1 - u0) * (205000 - v) / 205000
    m_ = _xy(um, v - 450) + sh
    A.text(m_[0], m_[1], _dimtxt(L, label), pt or DIMPT, DIML, rot=((ang + 90) % 180) - 90, color=DIMC, box=True)

def plan_dims(A):
    """平面（1階）：西館の外形（南北の全長・東西の幅・架構の数）と、敷地の境との離れ（北東の隣地・西の道路・高野川の側）"""
    sh = np.zeros(2)
    F = _foot(('21',))
    if F.is_empty: return
    q = _uv(np.vstack([np.asarray(g.exterior.coords) for g in getattr(F, 'geoms', [F])]))
    u0, u1, vw, ve = q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max()
    uk = [SGN * (t - TH_S[0]) * 205000 for t in TH_S]
    ks = [k + 1 for k, u in enumerate(uk) if u0 - 300 <= u <= u1 + 300]
    # 南北：西の外の弧（v＝いちばん西 −2.2 m）、長さは西館の東の線（v −0.9）で測る（決定事項：西館の距離は東の線の上）
    vd = vw - 2200
    for u in (u0, u1):
        g = F.intersection(LineString([_xy(u + (60 if u == u0 else -60), 0), _xy(u + (60 if u == u0 else -60), -40000)]))
        vv = _uv(np.array([c for gg in getattr(g, 'geoms', [g]) for c in gg.coords]))[:, 1].min() if not g.is_empty else vw
        _ext(A, _xy(u, vv - 200), _xy(u, vd - 300), sh)
    lab = f'西館の南北の全長（東の線で）　架構 {ks[0]}〜{ks[-1]}・{ks[-1] - ks[0]} スパン' if ks else '西館の南北の全長（東の線で）'
    arc_dim(A, u0, u1, vd, lab, sh, L=(u1 - u0) * (205000 + 900) / 205000)
    # 東の線（東の壁の外面 v−0.9）：高窓の帯より上（z 7 m）の壁の切り口で。1 階は東の帯が本館へ開いていて壁が無い所があり、
    # 高窓の帯の枠は少し東に出ている（v−0.84）
    S21 = MultiLineString([[tuple(a_[:2]), tuple(b_[:2])] for ob in OBJ if ob['layer'].startswith('21_')
                           for a_, b_ in slice_tris(ob['T'], np.array([0, 0, 7000.0]), np.array([0, 0, 1.0]))])
    def vel_at(u):                                                     # 架構の線（放射）と壁の切り口の交わりの、いちばん東
        x = S21.intersection(LineString([_xy(u, 2000), _xy(u, -40000)]))
        P = np.array([c for gg in getattr(x, 'geoms', [x]) for c in gg.coords]) if not x.is_empty else None
        return float(_uv(P)[:, 1].max()) if P is not None else float(q[:, 1].max())
    # 東西：いちばん広い所に近い架構の線の上で（北の端の外は紙の外になる。西館の西の面は架構 15 のあたりがいちばん西）
    uw = float(q[np.argmin(q[:, 1]), 0]); kw = int(np.argmin([abs(u - uw) for u in uk])); ua = uk[kw]
    g = F.intersection(LineString([_xy(ua, 2000), _xy(ua, -40000)]))
    if not g.is_empty:
        qa = _uv(np.array([c for gg in getattr(g, 'geoms', [g]) for c in gg.coords]))
        ldim(A, _xy(ua, vel_at(ua)), _xy(ua, qa[:, 1].min()), f'西館の東西の幅（架構 {kw + 1} の線で、外壁の外面から外面）', off=-520)
    # 2 階の床の東の縁：東の線（西館の東の壁の外面）から、2 階の床がある架構の線（2 階の床の南北の真ん中に近い架構）で
    F2 = _foot(('23',))
    if not F2.is_empty:
        q2 = _uv(np.asarray(F2.convex_hull.exterior.coords)); um2 = (q2[:, 0].min() + q2[:, 0].max()) / 2
        k2 = int(np.argmin([abs(u - um2) for u in uk])); u2 = uk[k2]
        g2 = F2.intersection(LineString([_xy(u2, 2000), _xy(u2, -40000)]))
        if not g2.is_empty:
            e2 = float(_uv(np.array([c for gg in getattr(g2, 'geoms', [g2]) for c in gg.coords]))[:, 1].max())
            ve_ = float(np.round(vel_at(u2), -1)); e2 = float(np.round(e2, -1))     # 面の位置は 10 mm に丸める（網の目の誤差）
            ldim(A, _xy(u2, e2), _xy(u2, ve_), '2階の床の東の縁（東の線から）')    # 字は西館の側へ
            print('plan dims 西館 2階の床の東の縁', k2 + 1, round(ve_), round(e2))
    print('plan dims 西館', round(u0), round(u1), round(vw), round(ve), ks)
    # 敷地の境との離れ（外壁の外面から境の線まで、いちばん近い所）
    from shapely.ops import nearest_points
    E = lambda a, b: LineString([SITE_C[a], SITE_C[b]])
    for pre, (a, b), lab, off in ((('17',), ('N', 'E'), '北東の隣地境界まで（本館）', 0), (('35',), ('N', 'E'), '北東の隣地境界まで（機械室）', 0),
                                  (('21',), ('SW', 'NW'), '西の道路境界まで（西の外壁は後退の1 mの線の上）', 0),
                                  (('17',), ('E', 'S'), '高野川の側の境界まで（避難の帯）', 0)):
        # 西館の南は高野川の側の境界から約 28 m。描かない：境界に垂直な線は西館の南の妻のどこから引いても本館の部屋を横切る。
        # 本館の西の外を弧に沿って測ると約 39 m で、離れの数にならない（10-28、項 20261028-1351-kanshu で確かめた）
        fp = _foot(pre)
        if fp.is_empty: continue
        p_, q_ = nearest_points(fp, E(a, b))
        ldim(A, np.array(p_.coords[0]), np.array(q_.coords[0]), lab, off=off)
        print('plan dims 離れ', lab, round(p_.distance(q_)))

def plan2_dims(A, sh):
    """平面（2階、西の道路の外に sh ずらして置いた図）：2階の外形（南北・東西）"""
    F = _foot(('21',)); F2 = _foot(('23',))
    if F2.is_empty: return
    q2 = _uv(np.asarray(F2.convex_hull.exterior.coords))
    a0, a1, e2 = q2[:, 0].min(), q2[:, 0].max(), q2[:, 1].max()     # 2階の床：北の縁 a1、東の縁 e2
    qF = _uv(np.vstack([np.asarray(g.exterior.coords) for g in getattr(F, 'geoms', [F])]))
    s0 = qF[:, 0].min()                                               # 南の妻の外面
    def west_at(u):
        g = F.intersection(LineString([_xy(u, 0), _xy(u, -40000)]))
        return _uv(np.array([c for gg in getattr(g, 'geoms', [g]) for c in gg.coords]))[:, 1].min() if not g.is_empty else None
    w1 = west_at(a1 - 60); w0 = west_at(s0 + 60)
    if w1 is None or w0 is None: return
    vd = w1 - 1500
    _ext(A, _xy(s0, w0 - 200), _xy(s0, vd - 300), sh); _ext(A, _xy(a1, w1 - 200), _xy(a1, vd - 300), sh)
    arc_dim(A, s0, a1, vd, '2階の南北（南の妻の外面〜2階の床の北の縁、東の縁で）', sh, L=(a1 - s0) * (205000 - e2) / 205000)
    un = a1 + 1300
    _ext(A, _xy(a1 + 200, w1), _xy(un + 300, w1), sh); _ext(A, _xy(a1 + 200, e2), _xy(un + 300, e2), sh)
    ldim(A, _xy(un, e2) + sh, _xy(un, w1) + sh, '2階の東西（西の外面〜2階の床の東の縁）')
    print('plan dims 2階', round(s0), round(a1), round(w1), round(e2))

def plan_section_marks(A):
    for nm, kind_, val, _ in SECTIONS:
        if kind_ == 'u':
            r0, r1 = (189000, 209500) if nm == 'D' else (184000, 222000)      # D は本館だけ（北の端は紙の縁が近い）：外縁側の先〜西館とのすき間
            th = theta_u(val); a, b = at(r0, th), at(r1, th)
            A.lines([[a, b]], '70_断面の位置', lw=LW_THIN, ls=LS_CHAIN, z=10)
            tdir = at(205000, theta_u(val + 1)) - at(205000, th); tdir /= np.linalg.norm(tdir)
            ends = (a, b); outw = {0: a - b, 1: b - a}
            lu = (b - a) / np.linalg.norm(b - a)
            A.lines([[a, a + lu * 1500], [b, b - lu * 1500]], '70_断面の位置', lw=LW_CUT, z=11)     # 切断線の両端は太く（JIS A 0150）
        else:
            # 北の端は本館の北の妻と機械室（おにぎり）のあいだで止める（10-28 ユーザー：前は u 62 で、矢がおにぎりにぶつかっていた）
            ths = np.linspace(theta_u(-5500), theta_u(58200), 200)                      # 南の端も紙の縁から離す（前は −9 m で紙の外）
            P = np.array([at(val, t) for t in ths])
            A.lines([P], '70_断面の位置', lw=LW_THIN, ls=LS_CHAIN, z=10)
            ends = (P[0], P[-1]); outw = {0: P[0] - P[1], 1: P[-1] - P[-2]}
            k_ = max(2, int(200 * 1200 / 63700))
            A.lines([P[:k_], P[-k_:]], '70_断面の位置', lw=LW_CUT, z=11)                             # 両端を太く（約 1.2 m）
        for i_, q in enumerate(ends):
            if kind_ == 'arc':
                d = q - C; tdir = -d / np.linalg.norm(d)      # 西（r の大きい方）を見る
                tdir = d / np.linalg.norm(d)
            # 見る向きの矢：黒く塗った三角（10-28 ユーザー：いちばんよく見る形）
            nrm_ = np.array([-tdir[1], tdir[0]])
            A.lines([[q, q + tdir * 900]], '70_断面の位置', lw=LW_CUT, z=11)
            A.fill(Polygon([q + tdir * 800 + nrm_ * 380, q + tdir * 1900, q + tdir * 800 - nrm_ * 380]), '70_断面の位置', fc='k', z=11)
            o_ = outw[i_] / np.linalg.norm(outw[i_]); qt = q + o_ * 650 + tdir * 450     # 字は線の端の先、矢の脇
            A.text(qt[0], qt[1], nm, 10, '70_断面の位置', box=True)

def objs_for_plan(level):
    out = []
    for ob in OBJ:
        n = num(ob['layer'])
        if ob['layer'].startswith('47'): continue
        if level == 1 and n in (41, 42, 43, 44, 45): continue      # 2階の床（23）は 1 階では切断より上：縁を想像線で（plan）
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

# 3枚目の平面図（プレゼンの準備 renkei/open/20261024-2316-present、ユーザー10-25）：敷地全体 1/100、配置図と同じ向き
# （高野川を下辺、3dm の xy を VIEW_ROT 回す）。A1 横の一枚、余白 6 mm、敷地の南の角を紙の (203, 9) mm、東の辺を右の余白まで。
# 道路・隣地は PLATEAU の道と建物（10-26、ユーザー：課題の敷地図をなぞった線はやめた）、敷地の境は一点鎖線。
# 2階（西館）は 3dm の xy で (−22.83, −16.73) m ずらして西の道路の外に。2階で切って下に見える遊戯室（床・遊具・クスノキ）も描く、本館の屋根は描かない。
SITE_C = {k: np.array(v) * 1000 for k, v in dict(N=(0.0, 0.0), E=(34.86, -43.83), S=(-14.44, -83.04),
                                                SW=(-21.91, -73.65), NW=(-25.83, -20.54)).items()}
SHIFT2 = np.array([-22830.0, -16730.0])
def _root():
    for p_ in (os.environ.get('SODACHIYA_ROOT', ''), os.path.join(os.path.dirname(os.path.abspath(IN)), '..'),
               '/home/claude/atelier/sodachiya'):
        if p_ and os.path.isfile(os.path.join(p_, 'present', 'kadai_map.json')): return p_
    return None
def _view_rot():
    import json
    try:
        return math.radians(json.load(open(os.path.join(_root(), 'data', 'garden.json'), encoding='utf-8'))['VIEW_ROT']['deg'])
    except Exception:
        return math.radians(-38.5)

def make_plans():
    import json as _j
    W_, H_, MG = 841, 594, 6
    S = Sheet(W_, H_, '平面図　1階・2階　1/100（A1）　高野川を下に（配置図と同じ向き、北は方位の矢印）', margin=MG)
    ph = _view_rot()
    c_, n_ = math.cos(ph), math.sin(ph)
    rp = lambda P: np.c_[np.asarray(P)[:, 0] * c_ - np.asarray(P)[:, 1] * n_, np.asarray(P)[:, 0] * n_ + np.asarray(P)[:, 1] * c_]
    corners = rp(np.array(list(SITE_C.values())))
    o0 = corners.min(0)
    x0 = o0[0] - (203 - MG) * 100; y0 = o0[1] - (9 - MG) * 100
    ext = (x0, x0 + (W_ - 2 * MG) * 100, y0, y0 + (H_ - 2 * MG) * 100)
    A = S.axes(MG, MG, ext); A.phi = ph
    # 道路・隣地（課題の敷地図をなぞった線）。2階を置く所（西の道路の向かい、西の辺から 7 m より外）は描かない
    a_, b_ = SITE_C['SW'], SITE_C['NW']; t_ = (b_ - a_) / np.linalg.norm(b_ - a_); nn_ = np.array([-t_[1], t_[0]])
    if nn_ @ (SITE_C['E'] - a_) > 0: nn_ = -nn_
    # 周りは PLATEAU の道と建物（ユーザー10-26：課題の敷地図をなぞった線はやめる。向かいの住宅3軒は add_context.py で道の縁に沿わせた）。
    # 2階を置く所（西の道の向かい、西の辺から 7 m より外）は描かない
    for ob in OBJ:
        n = num(ob['layer'])
        if n not in (3, 4): continue
        sil = silhouette(ob['T'][:, :, :2])
        if sil is None or sil.is_empty: continue
        if n == 4 and ((np.array(sil.centroid.coords[0]) - a_) @ nn_) > 7000: continue
        if n == 3:
            far = Polygon([a_ + nn_ * 7000 - t_ * 3e5, a_ + nn_ * 7000 + t_ * 3e5, a_ + nn_ * 3e5 + t_ * 3e5, a_ + nn_ * 3e5 - t_ * 3e5])
            sil = sil.difference(far)
            A.fill(sil, '30_敷地・外構', fc='0.96', z=0.3); A.geom_lines(sil, '30_敷地・外構', lw=0.06, color='0.6', z=0.35)
        else:
            A.fill(sil, '30_敷地・外構', fc='0.88', z=0.5); A.geom_lines(sil, '30_敷地・外構', lw=0.06, color='0.55', z=0.6)
    site = [P for ln, P in CURVES if ln.startswith('00')]
    if site:
        P = max(site, key=len)
        A.lines([P[:, :2]], '30_敷地・外構', lw=0.25, color='#C03030', ls=(0, (12, 3, 2, 3)), z=8)
    for ln, P in CURVES:
        if num(ln) in (94, 98) or ln.startswith('00'): continue
        if num(ln) == 91: A.lines([P[:, :2]], '30_敷地・外構', lw=0.05, color='0.7', z=1); continue
        if num(ln) == 92: A.lines([P[:, :2]], '30_敷地・外構', lw=0.13, color='#3d6f9a', z=1); continue
        if num(ln) >= 70 or num(ln) < 2: A.lines([P[:, :2]], '30_敷地・外構', lw=0.09, color='0.55', z=1)
    objs1 = objs_for_plan(1)
    roofs = [ob for ob in OBJ if num(ob['layer']) in (10, 20)]
    plan(A, CUT1, objs1, list(roofs), 0)        # 1 階は FL+1500 で切る（10-27 監修）
    rules = dict(up_dash_re=UP_DASH, up_light_re=UP_LIGHT, room_re=ROOM_RE, roof_re=r'^(10|20)_', tree_re=r'^94',
                 beam_prefix=list(KIND_BEAM), fitting_prefix=list(FIT_PREFIX), glass_words=['ガラス', '室内窓'],
                 high_window_below_mm=3000,
                 _='平面の決まり（plan()）：切断より上の物は描かない。ただし up_dash・光の筋・屋根の外形（roof）・樹冠（tree）・'
                   '高窓（建具・ガラスで、下端が切断より上かつ床+high_window_below_mm より下）は想像線。部屋の色の板（room）と梁（beam）は描かない')
    S.view(A, '1階平面', 'plan', cut_z_mm=CUT1, level_z_mm=0, shift_mm=(0.0, 0.0), rules=rules)
    plan_grid(A); plan_section_marks(A); plan_dims(A); plan_vdims(A); plan_more_dims(A)
    # 2階：西の道路の外へ、同じ向きで（ずらした物で描く）
    WB = [ob for ob in OBJ if num(ob['layer']) in (21, 23)]
    wp = np.vstack([ob['T'].reshape(-1, 3) for ob in WB])[:, :2]
    wx0, wy0 = wp.min(0) - 800; wx1, wy1 = wp.max(0) + 800
    def west(ob):
        q = ob['T'].reshape(-1, 3)[:, :2]
        if num(ob['layer']) == 21: return True
        return (q.min(0) > [wx0, wy0]).all() and (q.max(0) < [wx1, wy1]).all()
    PLAY = unary_union([silhouette(ob['T'][:, :, :2]) for ob in OBJ if ob['layer'].startswith('31_')])
    o2 = []
    for ob in OBJ:
        n = num(ob['layer'])
        if ob['layer'].startswith('47') or n in (90, 94, 98) or n < 20 and not ob['layer'].startswith('19d') or n in (50, 51) or n >= 60 and n < 80 or n > 89 and n < 100: continue   # 2階の室内の戸（19d）も（10-27）
        if not west(ob): continue
        z = ob['T'][:, :, 2]
        upper = z.max() > 3000 or n in (21, 22, 25)
        if not upper:                                  # 1階の物は遊戯室（吹き抜けから見下ろす）の中だけ
            sil = silhouette(ob['T'][:, :, :2])
            if sil is None or not sil.intersects(PLAY) or sil.intersection(PLAY).area < 0.5 * sil.area: continue
        o2.append(ob)
    sh3 = np.array([SHIFT2[0], SHIFT2[1], 0.0])
    o2s = [dict(ob, T=ob['T'] + sh3) for ob in o2]
    r2 = [dict(ob, T=ob['T'] + sh3) for ob in OBJ if num(ob['layer']) == 20]
    # 2 階は 2FL+1000 で切る（10-26 監修：+1200 では西館の南西の低い軒（壁の上端 約4.3 m）より上になり、休憩室の南の壁と窓が切れずに消えていた）
    plan(A, CUT2, o2s, r2, FL2, rooms_also=('31_',), void_shift=tuple(SHIFT2))
    S.view(A, '2階平面（西館）', 'plan', cut_z_mm=CUT2, level_z_mm=FL2, shift_mm=tuple(float(x_) for x_ in SHIFT2), rules=rules,
           select_xy_mm=[float(wx0), float(wy0), float(wx1), float(wy1)],
           select_='2階に描く物：西館の外壁（21）と、xy がすべて select_xy_mm（x0, y0, x1, y1）の中の物。'
                   'z の上端が 3000 以下の物（1 階の物）は遊戯室（31_）の床の中の物だけ（吹き抜けから見下ろす）。本館の屋根（10）は描かない、西館の屋根（20）は外形')
    plan2_dims(A, SHIFT2)
    # 表題・方位・縮尺（紙の座標）
    def paper(x_mm, y_mm):
        return ext[0] + (x_mm - MG) * 100, ext[2] + (y_mm - MG) * 100
    tx, ty = paper(14, H_ - 16)
    A.text(tx, ty, '平面図　1階　FL+1500 で切断／2階（西館）2FL+1000 で切断　1/100', 11, '80_図名・縮尺・方位', ha='left', va='top', raw=True)
    tx, ty = paper(14, H_ - 26)
    A.text(tx, ty, '高野川を下に（配置図と同じ向き）。2階は西の道路の外に同じ向きで置いた（遊戯室は吹き抜けから見下ろす）。一点鎖線は敷地の境。二点鎖線は切断より上にある物（屋根の外形・越屋根・2階の床の縁など）', PT_NOTE, '80_図名・縮尺・方位', ha='left', va='top', raw=True)
    bx, by = paper(14, 40)
    for i in range(5):
        A.ax.add_patch(plt.Rectangle((bx + i * 1000, by), 1000, 150, fc='k' if i % 2 == 0 else 'white', ec='k', lw=LW(0.1), zorder=12))
    A.text(bx, by + 500, '0', PT_NOTE, '80_図名・縮尺・方位', raw=True); A.text(bx + 5000, by + 500, '5 m', PT_NOTE, '80_図名・縮尺・方位', raw=True)
    nd = np.array([-math.sin(ph), math.cos(ph)]); pd = np.array([-nd[1], nd[0]])
    c0 = np.array(paper(24, 175))
    A.lines([[c0 - nd * 1700, c0 + nd * 1700]], '80_図名・縮尺・方位', lw=0.25, raw=True)
    A.lines([[c0 + nd * 1100 + pd * 300, c0 + nd * 1700, c0 + nd * 1100 - pd * 300]], '80_図名・縮尺・方位', lw=0.25, raw=True)
    q = c0 + nd * 2300; A.text(q[0], q[1], 'N', 8, '80_図名・縮尺・方位', raw=True)
    # 色の凡例（左下）
    LEG = [('0・1歳〜5歳', None), ('こどものみんなの場所（遊戯室・はれのま）', C_ALL), ('通り・つなぐ場所（はだし）', C_STREET), ('土足の床', C_DOSOKU),
           ('大人の場所', C_ADULT), ('キッチン・調理の更衣', C_ADULT2), ('水まわり', C_WATER)]
    lx, ly = paper(14, 120)
    A.text(lx, ly + 900, '部屋の色', 7, '80_図名・縮尺・方位', ha='left', va='bottom', raw=True)
    for i, (t, c) in enumerate(LEG):
        yy = ly - i * 900
        if c is None:
            for k, (_, kc) in enumerate(KIDS):
                A.ax.add_patch(plt.Rectangle((lx + k * 260, yy), 260, 550, fc=kc, ec='none', zorder=12))
        else:
            A.ax.add_patch(plt.Rectangle((lx, yy), 1300, 550, fc=c, ec='none', zorder=12))
        A.text(lx + 1600, yy + 275, t, PT_NOTE, '80_図名・縮尺・方位', ha='left', va='center', raw=True)
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
        A.text(x_text + 300, zt + 60, f'{nm}　{"+" if z > 0 else "±" if z == 0 else "−"}{abs(z):,.0f}', PT_DIM, '51_高さ', ha='left', va='bottom', color='#2E7D32')

def chain_dims(A, xs, y, label_fmt='{:,.0f}'):
    xs = sorted(xs)
    A.lines([[(xs[0], y), (xs[-1], y)]], '50_寸法', lw=LW_THIN, color='#2E7D32')
    dim_ends(A, [(x, y) for x in xs], (1, 0), color='#2E7D32')
    for a, b in zip(xs, xs[1:]):
        if b - a > 300: A.text((a + b) / 2, y + 150, label_fmt.format(b - a), PT_DIM, '50_寸法', va='bottom', color='#2E7D32')

# ---------------------------------------------------------------- 要所の寸法（プレゼンの準備 20261027-1836、ユーザー：要求図面なので重要な所に寸法）
# 数はすべて 3dm から（切り口・見えがかり・物の三角形）。色は今の緑、字は約 2.3 mm（6.5 pt）。
DIMC, DIMPT, DIML = '#2E7D32', PT_DIM, '50_寸法'
def dim_ends(A, ends, t, layer=None, color=None, ext=180, z=9):
    """寸法の端（JIS A 0150）：寸法補助線の出（細い実線、寸法線の両側へ ext）と、端末記号の斜線（寸法線から 45°、長さ 2.5 mm、中の太さ）。
    t：寸法線の向き（モデルの座標、向きの正負はどちらでも同じ）"""
    layer = layer or DIML; color = color or DIMC
    t = np.asarray(t, float); t = t / max(np.linalg.norm(t), 1e-9); n = np.array([-t[1], t[0]]); s_ = (t + n) / math.sqrt(2)
    for e in ends:
        e = np.asarray(e, float)
        A.lines([[e - n * ext, e + n * ext]], layer, lw=LW_THIN, color=color, z=z)
        A.lines([[e - s_ * 125, e + s_ * 125]], layer, lw=LW_MID, color=color, z=z)
def _dimtxt(v, label): return f'{abs(v):,.0f}' + (f'　{label}' if label else '')
def vdim(A, x, z0, z1, label='', side=-1):
    """縦の寸法線（断面・立面の x, z）。字は線の左に、図面の右から読む向き（JIS A 0150）。side は前の名残（使わない）"""
    if z0 is None or z1 is None or abs(z1 - z0) < 20: return
    A.lines([[(x, z0), (x, z1)]], DIML, lw=LW_THIN, color=DIMC, z=9)
    dim_ends(A, [(x, z0), (x, z1)], (0, 1), z=9)
    A.text(x - 140, (z0 + z1) / 2, _dimtxt(z1 - z0, label), DIMPT, DIML, ha='right', va='center', rot=90, color=DIMC, box=True)
def hdim(A, x0, x1, z, label='', above=True):
    """横の寸法線（断面・立面）。字は線の上（JIS A 0150）。above は前の名残（使わない）"""
    if x0 is None or x1 is None or abs(x1 - x0) < 20: return
    x0, x1 = sorted((x0, x1))
    A.lines([[(x0, z), (x1, z)]], DIML, lw=LW_THIN, color=DIMC, z=9)
    dim_ends(A, [(x0, z), (x1, z)], (1, 0), z=9)
    A.text((x0 + x1) / 2, z + 130, _dimtxt(x1 - x0, label), DIMPT, DIML, va='bottom', color=DIMC, box=True)
def ldim(A, p, q, label='', off=0.0, pt=DIMPT):
    """平面の斜めの寸法線（モデルの xy、mm）。off：字を線から離す量（線の左へ +）"""
    p, q = np.asarray(p, float), np.asarray(q, float); d = q - p; L = float(np.linalg.norm(d))
    if L < 20: return
    t = d / L; n = np.array([-t[1], t[0]])
    A.lines([[p, q]], DIML, lw=LW_THIN, color=DIMC, z=9)
    dim_ends(A, [p, q], t, z=9)
    ang = math.degrees(math.atan2(t[1], t[0])); m_ = (p + q) / 2 + n * (260 + off)
    txt = _dimtxt(L, label)
    tl = sum(1.0 if ord(ch) > 255 else 0.6 for ch in txt) * pt * 0.3528 * 100      # 字の長さ（モデルの mm、1/100）
    if tl > L - 400: m_ = p - t * (tl / 2 + 400) + n * off                            # 線より字が長い：字を p の側（建物の側）の延長に
    A.text(m_[0], m_[1], txt, pt, DIML, rot=((ang + 90) % 180) - 90, color=DIMC, box=True)

# 断面の切り口（線）と見えがかり（形）を section_u・section_arc が A に残す。そこから縦の線の上の高さを読む
ROOF_G = lambda b: (lambda ln: bool(re.match(rf'^{b}[rv]?_', ln)))            # 屋根（層に分けた分も）
PRE = lambda *ps: (lambda ln: ln.split('_')[0] in ps)
def cut_z(A, test, x0, x1):
    zs = []
    for ln, segs in getattr(A, 'cutsegs', {}).items():
        if not test(ln): continue
        for q in segs:
            q = np.asarray(q, float)
            for (xa, za), (xb, zb) in zip(q[:-1], q[1:]):
                lo, hi = min(xa, xb), max(xa, xb)
                if hi < x0 or lo > x1: continue
                if hi - lo < 1e-6: zs += [za, zb]; continue
                for xx in (max(lo, x0), min(hi, x1)):
                    zs.append(za + (xx - xa) / (xb - xa) * (zb - za))
    return zs
def cut_x(A, test):
    xs = [p[0] for ln, segs in getattr(A, 'cutsegs', {}).items() if test(ln) for q in segs for p in q]
    return (min(xs), max(xs)) if xs else (None, None)
def far_z(A, test, x):
    ln_ = LineString([(x, -1e5), (x, 1e5)]); zs = []
    for ln, sil in getattr(A, 'farsil', []):
        if not test(ln) or sil is None: continue
        g = sil.intersection(ln_)
        if not g.is_empty: zs += [g.bounds[1], g.bounds[3]]
    return zs
_mn = lambda L: min(L) if L else None
_mx = lambda L: max(L) if L else None

def sec_dims_ew(A, westx, note=False):
    """断面 B・C（東西、x＝v）：高さ（GL〜FL・軒先・最高、FL〜梁の下端・屋根の下面、西館の階高）と、軒の出・縁側の奥行き"""
    R10, R20 = ROOF_G('10'), ROOF_G('20')
    # 本館（東）：軒先の上端、最高（屋根・越屋根の蓋）
    _, xe = cut_x(A, R10)
    if xe is not None:
        ze = _mx(cut_z(A, R10, xe - 150, xe))
        zmax = _mx(cut_z(A, lambda ln: R10(ln) or ln.startswith('50a'), -1e6, 1e6))
        xd = xe + 500
        vdim(A, xd, -300, 0, 'GL〜FL')
        vdim(A, xd + 700, -300, ze, '軒の高さ')
        vdim(A, xd + 1400, -300, zmax, '本館の最高')
        # 縁側の奥行き・軒の出（外皮＝縁側の中ほどのガラス戸の線から軒先）
        g0, g1 = cut_x(A, PRE('16'))                       # 縁側の中ほどの断熱ガラス戸（外皮の線）
        if g0 is None: g0, g1 = cut_x(A, PRE('17k'))       # 架構の線で切る（断面 D）：ガラス戸でなく、そのあいだの杉の壁の柱型
        xg = (g0 + g1) / 2 if g0 is not None else None
        _, xo = cut_x(A, PRE('14'))
        zt = _mx(cut_z(A, R10, 12000, xe))
        if xg is not None and zt is not None:
            hdim(A, xg, xe, zt + 600, '軒の出')                       # 内縁側 1,500 は下の寸法の列にある
            if xo is not None: hdim(A, 12000, xo, zt + 1300, '縁側の奥行き')
        # 室内：FL〜梁の下端（奥に見える架構の梁）・屋根の下面（垂木の下）
        xi = 7000
        zb = _mn(far_z(A, PRE('11b'), xi) + cut_z(A, PRE('11b'), xi - 60, xi + 60))
        zr = _mn(cut_z(A, R10, xi - 250, xi + 250))
        vdim(A, xi, 0, zb, '梁の下端', side=1)
        vdim(A, xi + 700, 0, zr, '垂木の下', side=1)
    # 西館（西）：軒先の上端、最高（第一種低層 10 m）、軒の出、階高、室内の高さ
    xw, _ = cut_x(A, R20)
    xnote = None
    if xw is not None and westx < -2000:
        zw = _mx(cut_z(A, R20, xw, xw + 150))
        zmw = _mx(cut_z(A, lambda ln: R20(ln) or ln.startswith(('28', '29', '30')), -1e6, 1e6))
        xd = xw - 800
        vdim(A, xd, -300, zw, '軒の高さ')
        vdim(A, xd - 700, -300, zmw, '西館の最高（10 m 以下）')
        xnote = xd - 1300
        if zw is not None: hdim(A, xw, westx, zw + 600, '軒の出')
        xi = westx + 2200
        z2 = _mx(cut_z(A, PRE('23'), xi - 200, xi + 200))
        zr = _mn(cut_z(A, R20, xi - 250, xi + 250))
        zb = _mn([z for z in far_z(A, PRE('22b'), xi) + cut_z(A, PRE('22b'), xi - 60, xi + 60) if z2 is None or z > z2])
        if z2 is not None and 2500 < z2 < 4000:
            vdim(A, xi, 0, z2, '階高', side=1)
            vdim(A, xi + 700, z2, zb, '梁の下端', side=1)
            vdim(A, xi + 1400, z2, zr, '垂木の下', side=1)
        else:
            vdim(A, xi, 0, zb, '梁の下端', side=1)
            vdim(A, xi + 700, 0, zr, '垂木の下', side=1)
    return xnote

def sec_dims_a(A):
    """断面 A（縦断、x＝r=197 m の弧長）：南の妻の外に高さ、南北の軒の出、室内の高さ（架構 3 の梁・スパン 3 の真ん中の屋根）"""
    R10 = ROOF_G('10')
    xs, xn = cut_x(A, R10)
    if xs is None: return
    ws, _ = cut_x(A, lambda ln: ln.startswith(('17_', '16s')))
    _, wn = cut_x(A, PRE('17'))
    zs = _mx(cut_z(A, R10, xs, xs + 150)); zn = _mx(cut_z(A, R10, xn - 150, xn))
    zmax = _mx(cut_z(A, lambda ln: R10(ln) or ln.startswith('50a'), -1e6, 1e6) +       # 越屋根は r=197 では切れない：奥に見える越屋根の上端
               [sil.bounds[3] for ln, sil in A.farsil if ln.startswith(('50a', '50c')) and sil is not None and not sil.is_empty])
    xd = xs - 500
    vdim(A, xd, -300, 0, 'GL〜FL')
    vdim(A, xd - 700, -300, zs, '南の軒先')
    vdim(A, xd - 1400, -300, zmax, '本館の最高')
    if ws is not None and zs is not None: hdim(A, xs, ws, _mx(cut_z(A, R10, xs, ws)) + 600, '南の軒の出')
    if wn is not None and zn is not None: hdim(A, wn, xn, _mx(cut_z(A, R10, wn, xn)) + 600, '北の軒の出')
    xf = SGN * (TH_S[2] - TH_S[0]) * SECTIONS[0][2]; xm = SGN * ((TH_S[2] + TH_S[3]) / 2 - TH_S[0]) * SECTIONS[0][2]
    zb = _mn(cut_z(A, PRE('11b'), xf - 150, xf + 150))
    zr = _mn(cut_z(A, R10, xm - 200, xm + 200))
    vdim(A, xf + 500, 0, zb, '梁の下端', side=1)
    rv = _mn(cut_z(A, PRE('10v'), xm - 200, xm + 200))
    vdim(A, xm, 0, zr, '垂木の下' if rv is not None and zr is not None and rv <= zr + 1 else '屋根の下面', side=1)

# 細かい繰り返し（越屋根の木のルーバー：板が 9 mm おきに重なる）は、1/100 で一枚ずつ線を引くと黒い帯に潰れる。
# 見えがかり・立面では層ごとに一つの外形にまとめる（切り口は一枚ずつのまま）。
FINE_LAYERS = ('50c_', '30_')
def merge_fine_far(far):
    out, grp = [], {}
    for dd, ob, sil in far:
        if ob['layer'].startswith(FINE_LAYERS): grp.setdefault(ob['layer'], []).append((dd, ob, sil))
        else: out.append((dd, ob, sil))
    for ln, L in grp.items():
        ss = [t[2] for t in L if t[2] is not None and not t[2].is_empty]
        if ss: out.append((min(t[0] for t in L), L[0][1], unary_union(ss).buffer(1, join_style=2).buffer(-1, join_style=2)))
    return out
def merge_fine_objs(objs):
    out, grp = [], {}
    for ob in objs:
        if ob['layer'].startswith(FINE_LAYERS): grp.setdefault(ob['layer'], []).append(ob)
        else: out.append(ob)
    for ln, L in grp.items():
        out.append(dict(L[0], T=np.concatenate([o['T'] for o in L]), name='（まとめて外形）'))
    return out

# 地盤の記号（JIS A 0150）：断面の GL の線の下に細い斜線の帯（深さ 300、間 200）。切った基礎・床の所は除く
def ground_hatch(A, x0, x1, occ, d=300, pitch=200, gl=-300):
    strip = box(x0, gl - d, x1, gl)
    if occ is not None and not occ.is_empty:
        strip = strip.difference(occ.buffer(20))
        for g in getattr(occ, 'geoms', [occ]):          # GL より下へ出る物（基礎）は、その幅の中（床下）も地盤でない
            b = g.bounds
            if b[1] < gl - 50 and b[3] > gl: strip = strip.difference(box(b[0] - 20, gl - d - 1, b[2] + 20, gl + 1))
    if strip.is_empty: return
    segs = [LineString([(x - d, gl - d), (x, gl)]) for x in np.arange(x0, x1 + d, pitch)]
    A.geom_lines(unary_union(segs).intersection(strip), '15_地盤', lw=LW_THIN, color='0.35', z=7.9)

SEC_DEPTH, SEC_A_DEPTH = 3200, 30000          # 断面の奥（B・C は 3.2 m、A は 30 m）
def section_frame(theta):
    """架構に平行な鉛直の断面（θ）：u_r（中心から外へ）、u_t（見る向き＝北を奥に）、p0（円弧の中心、z 0）"""
    u_r = np.array([math.cos(theta), math.sin(theta), 0.])
    u_t = np.array([-math.sin(theta), math.cos(theta), 0.])
    if at(205000, theta + 0.01)[1] < at(205000, theta)[1]: u_t = -u_t      # 北を奥に
    return u_r, u_t, np.array([C[0], C[1], 0.])
def section_u(A, theta, depth=SEC_DEPTH, skip=None, snap=False, far_bin=None):
    """skip：描かないレイヤーの頭（正規表現）。snap：切り口の点を 0.001 mm に丸めてからつなぐ（架構の線で柱を縦に切ると、
    切り口の線の端がわずかに食い違って輪にならず、柱の穴だけが塗られていた。断面 D）。far_bin：見えがかりを、物の三角形の
    奥行き far_bin mm ごとに分けて、近いものから描く（外壁と南北の妻が一つの物なので、切った西の外壁と一緒に、奥の北の妻の面が
    いちばん手前に来て、梁・鏡面を隠していた。断面 D）。三つとも断面 B・C では使わない（今までどおり）"""
    u_r, u_t, p0 = section_frame(theta)
    X = lambda P: 205000 - (P - p0) @ u_r                # v（西の外壁の線 r=205 m から東へ、mm）、右が東
    D = lambda P: (P - p0) @ u_t
    far, cuts = [], []
    for ob in OBJ:
        if ob['layer'].startswith('47') or num(ob['layer']) in (76, 77) or 91 <= num(ob['layer']) <= 98 or num(ob['layer']) in (3, 4): continue   # 園庭の木・小屋は断面に出さない（園庭の断面は園庭のチャット）
        if skip and re.match(skip, ob['layer']): continue
        T = ob['T']; d = D(T.reshape(-1, 3)).reshape(-1, 3)
        if d.max() < 0 or d.min() > depth: continue
        if d.min() < 0 < d.max():
            segs = slice_tris(T, p0, u_t)
            S2 = [((X(s[0]), s[0][2]), (X(s[1]), s[1][2])) for s in segs]
            if snap: S2 = [tuple(tuple(np.round(q, 3)) for q in s_) for s_ in S2]
            cuts.append((ob, poche(S2), S2))
        if num(ob['layer']) in (2, 90, 12, 13): continue      # 川の護岸・園庭の地形は切り口だけ（見えがかりは長くなりすぎる）、床組は床の構成で描く
        keep = (d.max(1) >= 0) & (d.min(1) <= depth)
        if far_bin:
            dm = np.maximum(d.min(1), 0)
            for b_ in np.unique((dm[keep] // far_bin).astype(int)):
                kb = keep & ((dm // far_bin).astype(int) == b_)
                T2 = np.stack([X(T[kb].reshape(-1, 3)).reshape(-1, 3), T[kb][:, :, 2]], -1)
                if len(T2): far.append((float(dm[kb].min()), ob, silhouette(T2)))
            continue
        T2 = np.stack([X(T[keep].reshape(-1, 3)).reshape(-1, 3), T[keep][:, :, 2]], -1)
        if len(T2): far.append((max(0, d.min()), ob, silhouette(T2)))
    A.cutsegs = {}; A.farsil = [(ob['layer'], sil) for _, ob, sil in far]    # 寸法が読む（sec_dims_ew）
    for ob, pc, S2 in cuts: A.cutsegs.setdefault(ob['layer'], []).extend(S2)
    occ = draw_cut(A, cuts, insul=True)
    far = merge_fine_far(far)
    far.sort(key=lambda t: t[0])
    draw_visible(A, [(ob, sil) for _, ob, sil in far], occ)
    A.lines([[(-17500, -300), (17800, -300)]], '01_切断（構造・壁）', lw=LW_CUT, z=8, annot=True)   # GL（3dm に無い線：文字の層にも）
    ground_hatch(A, -17500, 17800, occ)
    cutb = {}
    for ob, pc, S2 in cuts:
        if not S2: continue
        P = np.vstack([np.asarray(q) for q in S2]); b = (P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max())
        o = cutb.get(ob['layer']); cutb[ob['layer']] = b if o is None else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
    return cutb

def section_arc(A, Rc, depth=SEC_A_DEPTH):
    """円筒面 r=Rc で切って展開。横＝u（南の妻から北へ、r=Rc の弧長）、西を見る（奥＝r の大きい方）"""
    def RTH(P):
        d = P[..., :2] - C; return np.hypot(d[..., 0], d[..., 1]), unwrap(np.arctan2(d[..., 1], d[..., 0]))
    X = lambda th: SGN * (th - TH_S[0]) * Rc
    # 南は敷地の境で止める（10-26 ユーザー・監修：弧は高野川の崖を浅い角度で斜めに切るので、崖が横に引き伸ばされ、
    # 園庭の地面の線も崖の外まで出ていた。川との関係は園庭の断面に任せる）。境の外の切り口・見えがかりは描かず、境に破断線
    site_ = [P for ln, P in CURVES if ln.startswith('00')]
    XCUT = -1e9
    if site_:
        sp_ = max((Polygon(np.asarray(P)[:, :2]).buffer(0) for P in site_), key=lambda g: g.area)
        ths = TH_S[0] - SGN * np.linspace(0, 30000, 3001) / Rc
        ins = [sp_.contains(Point(*(C + Rc * np.array([math.cos(t), math.sin(t)])))) for t in ths]
        k_ = next((i for i, v in enumerate(ins) if not v), None)
        if k_: XCUT = float(X(ths[k_ - 1]))
    A.xcut = XCUT if XCUT > -1e8 else None                # …_views.json に（Rhino の zumen.py も同じ所で止める）
    CLIP = box(XCUT, -1e5, 1e6, 1e5)
    def _clipsegs(segs):
        out = []
        for q in segs:
            if min(q[0][0], q[1][0]) >= XCUT: out.append(q); continue
            if max(q[0][0], q[1][0]) <= XCUT: continue
            g = LineString(q).intersection(CLIP)
            if g.geom_type == 'LineString' and g.length > 0: out.append(list(g.coords))
        return out
    far, cuts = [], []
    for ob in OBJ:
        if ob['layer'].startswith('47') or num(ob['layer']) in (76, 77) or 91 <= num(ob['layer']) <= 98 or num(ob['layer']) in (3, 4): continue   # 園庭の木・小屋は断面に出さない（園庭の断面は園庭のチャット）
        if num(ob['layer']) == 2: continue                    # 高野川の護岸は敷地の外（上の XCUT）
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
            pc_ = poche(segs)
            if pc_ is not None and not pc_.is_empty and XCUT > -1e8: pc_ = pc_.intersection(CLIP)
            segs = _clipsegs(segs)
            if segs: cuts.append((ob, pc_, segs))
        if num(ob['layer']) in (2, 90, 12, 13): continue      # 川の護岸・園庭の地形は切り口だけ、床組は床の構成で描く
        keep = rr.max(1) >= Rc
        T2 = np.stack([X(th[keep]), T[keep][:, :, 2]], -1)
        if len(T2):
            sil_ = silhouette(T2)
            if sil_ is not None and not sil_.is_empty and XCUT > -1e8: sil_ = sil_.intersection(CLIP)
            if sil_ is not None and not sil_.is_empty: far.append((max(0, rr.min() - Rc), ob, sil_))
    A.cutsegs = {}; A.farsil = [(ob['layer'], sil) for _, ob, sil in far]    # 寸法が読む（sec_dims_a）
    for ob, pc, segs in cuts: A.cutsegs.setdefault(ob['layer'], []).extend(segs)
    occ = draw_cut(A, cuts, insul=True)
    far = merge_fine_far(far)
    far.sort(key=lambda t: t[0])
    draw_visible(A, [(ob, sil) for _, ob, sil in far], occ)
    A.lines([[(max(-5000, XCUT), -300), (64000, -300)]], '01_切断（構造・壁）', lw=LW_CUT, z=8, annot=True)
    ground_hatch(A, max(-5000, XCUT), 64000, occ)
    if XCUT > -1e8:                                       # 破断線（敷地の境）
        zz_ = [-1300, -300, 600, 900, 1200, 1500, 6500]; xx_ = [XCUT, XCUT, XCUT, XCUT - 250, XCUT + 250, XCUT, XCUT]
        A.lines([np.c_[xx_, zz_]], '10_見えがかり', lw=0.13, z=8, annot=True)
        A.text(XCUT - 300, -1100, '敷地の境', PT_NOTE, '80_図名・縮尺・方位', ha='right', va='center', color='0.35')
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
    """換気の道（ユーザー 10-23夜・10-24）。略図（断面の線は 3dm、矢印は考え方）。x＝v（mm、東が右）、z＝FL からの高さ
    昼（中間期）：縁側のガラス戸を開けて → 部屋 → 屋根に沿って梁間を西へ上る → 西吹き抜け → 本館の越屋根のすき間（実線）。
    夏の夜：外気を縁側の段（外縁側 −150 → 内縁側 ±0）の蹴込みのガラリから床下へ、底板を冷やしながら西へ、
    西の壁ぎわのスリットから部屋へ出て越屋根へ（破線）。playroom：床下はすき間の下で西館の床下へつながり、遊戯室の床から上って
    西館の越屋根へ（高低差が大きい）。東の覗き窓も夜だけ開く。"""
    roof = lambda v: 4000 - v / 12.0
    col = '#2F6FB0'
    def arrow(P, ls='-', lw=0.18):
        P = np.array(P, float)
        A.lines([P], '45_換気', lw=lw, color=col, ls=ls, z=9)
        d = P[-1] - P[-2]; d = d / np.linalg.norm(d); n = np.array([-d[1], d[0]])
        A.lines([[P[-1] - d * 260 + n * 120, P[-1], P[-1] - d * 260 - n * 120]], '45_換気', lw=lw, color=col, z=9)
    dash = (0, (5, 3))
    zf = (SLAB_TOP - FL_BOARD - 90) / 2            # 床下の真ん中の高さ
    day = [(14700, 900), (12600, 1100), (10500, roof(10500) - 450), (6000, roof(6000) - 320), (1700, roof(1700) - 320),
           (700, 3950), (-150, 4400)]
    arrow(day + [(-150, 4420), (-700, 4700)] if not playroom else day + [(-300, 4430)])
    night_in = [(15300, 250), (13900, -75), (13300, zf)]
    if playroom:
        arrow(night_in + [(-1500, zf), (-1650, 150)], ls=dash)
        arrow([(-1650, 450), (-1700, 6000), (-1500, 7600), (-1400, 8900)], ls=dash)
        arrow([(-300, 4430), (-650, 4430), (-750, 4250), (-1250, 4100)], ls=dash)
        A.text(-1900, 9050, '夏の夜：床下の冷気と覗き窓から、遊戯室の吹き抜けを上って西館の越屋根へ', PT_NOTE, '45_換気', ha='right', va='bottom', color=col, box=True)
        A.text(400, 5300, '昼（中間期）は本館の越屋根のすき間から外へ', PT_NOTE, '45_換気', ha='left', va='bottom', color=col, box=True)
    else:                                          # 断面 B はあまのがわ（土間、床下は無い）
        A.text(400, 5300, '本館の越屋根のすき間から外へ', PT_NOTE, '45_換気', ha='left', va='bottom', color=col, box=True)
    A.text(4200, 2700, '梁間（梁と梁と屋根のあいだ）を西へ上る', PT_NOTE, '45_換気', ha='center', va='top', color=col, box=True)
    A.text(14600, 800, '昼：縁側のガラス戸を開けて', PT_NOTE, '45_換気', ha='right', va='top', color=col, box=True)
    if playroom:
        A.text(12900, 120, '夏の夜：段の蹴込みのガラリから床下へ（底板を冷やす）→ すき間の下で西館の床下へ', PT_NOTE, '45_換気', ha='right', va='bottom', color=col, box=True)


WEST_WALL_NOTE = ('西館の外壁：構造用合板の耐力壁', '（窓ごと通す、開口は補強）', '西の面は室内側にも合板（両面）')
def west_wall_note(A, westx, z=2000, x_t=None):
    """西館の外壁（西の面・北西の斜め・南北の妻）の構造の注（西館係 20261027-1511、決定事項_西館の「構造」）。
    断面 B の西の外壁の外（道の側）、奥に見える西館の低い軒（約2 m）より西に字、引き出し線は壁の切り口まで"""
    x_t = (westx - 2500) if x_t is None else x_t; dz = 360     # 西館の軒先・最高の寸法線があればその外
    for j, t in enumerate(WEST_WALL_NOTE):
        A.text(x_t, z + dz * (1 - j), t, PT_NOTE, '81_注', ha='right', va='center')
    A.lines([[(x_t + 80, z), (westx + 60, z)]], '81_注', lw=0.09, color='k', z=9)
    A.ax.add_patch(plt.Circle((westx + 60, z), 45, fc='k', ec='none', zorder=9))      # 断面は回さない（phi=0）

def make_sections():
    W_, H_ = 841, 594
    S = Sheet(W_, H_, '断面図 A（縦断・展開）・B・C　1/100（A1）')
    extA = (-11500, 68500, -5600, 10500)       # 右の高さの記号の字が枠の内に入るように 3 m 左へ（10-28、左は敷地の境で止めたので空いている）
    A = S.axes(30, H_ - 40 - 161, extA)
    A.insul_x = (0, 57000)
    S.view(A, '断面' + SECTIONS[0][0], 'section_arc', rhino_supported=True, center_xy_mm=C, radius_mm=SECTIONS[0][2],
           theta0_rad=float(TH_S[0]), sign=SGN, depth_mm=SEC_A_DEPTH, origin=(0.0, 0.0, 0.0), right=(0.0, 0.0, 0.0),
           _='円筒面 r=radius で切って展開：h = sign·(θ − theta0)·radius（θ は中心からの角度を [0, 2π) に）、外（r の大きい方）を見る。'
             'model_to_paper_3d は使えない（0）。xcut_h_mm より南（h の小さい方、敷地の外）は描かない。rhino/zumen.py の draw_section_arc が読む')
    cutb = section_arc(A, SECTIONS[0][2])
    S.views[-1]['xcut_h_mm'] = A.xcut                  # 敷地の境で止める所（h、mm。無ければ None）
    levels(A, cutb, 64300, True)
    sec_dims_a(A)
    A.text(extA[0] + 300, extA[3] - 200, f'断面図 A　1/100　{SECTIONS[0][3]}', PT_TITLE, '80_図名・縮尺・方位', ha='left', va='top')
    A.text(extA[0] + 300, -5400, '← 南（高野川の側）', PT_NOTE, '80_図名・縮尺・方位', ha='left', va='bottom')
    A.text(56000, -2400, '北 →', PT_NOTE, '80_図名・縮尺・方位', ha='right', va='bottom')
    extX = (-17500, 21500, -2600, 10500)
    for i, (nm, kind_, val, cap_) in enumerate(SECTIONS[1:3]):
        A = S.axes(30 + i * (390 + 15), H_ - 40 - 161 - 45 - 131, extX)
        A.insul_x = (-1e5, 13500)                   # 外皮の線は v13.5（縁側の中ほどの杉の壁とガラス戸）
        A.rafter_cut = True                         # 東西に切る：垂木（南北）を横に切る
        th_ = theta_u(val); u_r, u_t, p0 = section_frame(th_)
        S.view(A, '断面' + nm, 'section', origin=p0 + 205000 * u_r, right=-u_r, up=(0.0, 0.0, 1.0), view_dir=u_t,
               cut_plane_point=p0 + 205000 * u_r, cut_plane_normal=u_t, depth_mm=SEC_DEPTH, u_mm=val,
               _='鉛直の面（origin を通り、法線 view_dir）で切り、view_dir の向きに depth_mm まで見る。h＝v（西の柱の列 W から東へ）')
        cutb = section_u(A, th_)
        westx = min([b[0] for k, b in cutb.items() if k.startswith('21_')] or [-900])
        chain_dims(A, [westx, -900, 0, 1600, 12000, 13500, 15000], -900)
        for nm2, x in (('W', 0), ('E', 12000)):
            A.lines([[(x, -1200), (x, 9800)]], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
            A.bubble(x, -1750, nm2)
        levels(A, cutb, 18500, westx < -2000)        # 高さの記号は寸法線（軒先・最高）の外へ
        airflow(A, playroom=(nm == 'C'))
        xnote = sec_dims_ew(A, westx)
        if i == 0 and westx < -2000: west_wall_note(A, westx, x_t=xnote)
        A.text(extX[0] + 300, extX[3] - 200, f'断面図 {nm}　1/100　{cap_}', PT_TITLE, '80_図名・縮尺・方位', ha='left', va='top')
        A.text(extX[0] + 300, -2400, '← 西', PT_NOTE, '80_図名・縮尺・方位', ha='left', va='bottom')
        A.text(16000, -2400, '東 →', PT_NOTE, '80_図名・縮尺・方位', ha='right', va='bottom')
        if i == 0:
            for j in range(5):
                A.ax.add_patch(plt.Rectangle((-9000 + j * 1000, -2450), 1000, 150, fc='k' if j % 2 == 0 else 'white', ec='k', lw=LW(0.1)))
            A.text(-9000, -2050, '0', PT_NOTE, '80_図名・縮尺・方位'); A.text(-4000, -2050, '5 m', PT_NOTE, '80_図名・縮尺・方位')
    legend_materials(S, 30, 165)
    return S

def make_sections2():
    """断面 D だけの紙（A1 横）。光の環境の説明の図（換気の矢は描かない）。範囲は本館の西の外壁の少し西（v −2 m、西の吹き抜けと
    西館とのすき間の縁）から東の軒先・外縁側の先まで。西館は奥に見えても −2 m で切る（図の範囲＝clip）"""
    W_, H_ = 841, 594
    nm, kind_, val, cap_ = SECTIONS[3]
    S = Sheet(W_, H_, '断面図 D　1/100（A1）')
    ext = (-2000, 22000, -2600, 7000)
    A = S.axes(round((W_ - (ext[1] - ext[0]) / 100) / 2), round((H_ - (ext[3] - ext[2]) / 100) / 2), ext)
    A.insul_x = (-1e5, 13500)
    A.rafter_cut = True
    th_ = theta_u(val); u_r, u_t, p0 = section_frame(th_)
    S.view(A, '断面' + nm, 'section', origin=p0 + 205000 * u_r, right=-u_r, up=(0.0, 0.0, 1.0), view_dir=u_t,
           cut_plane_point=p0 + 205000 * u_r, cut_plane_normal=u_t, depth_mm=SEC_DEPTH, u_mm=val, frame_k=SEC_D_K, skip_layers_re=SEC_D_SKIP,
           _='鉛直の面（origin を通り、法線 view_dir）で切り、view_dir の向きに depth_mm まで見る。h＝v（西の柱の列 W から東へ）。'
             '架構の線（2 枚の梁のあいだ）で切る。h が図の範囲（clip_paper_mm）より西の物（西館）は描かない')
    cutb = section_u(A, th_, skip=SEC_D_SKIP, snap=True, far_bin=400)
    cutb = {k: b for k, b in cutb.items() if b[2] > ext[0]}      # 図の範囲より西（西館）の切り口は高さ・寸法に使わない
    chain_dims(A, [-900, 0, 1600, 12000, 13500, 15000], -900)
    for nm2, x in (('W', 0), ('E', 12000)):
        A.lines([[(x, -1200), (x, 5600)]], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
        A.bubble(x, -1750, nm2)
    levels(A, cutb, 18500, False)
    sec_dims_ew(A, 0.0)                              # 西館の寸法は描かない（範囲の外）
    A.text(ext[0] + 300, ext[3] - 200, f'断面図{nm}　1/100　{cap_}', PT_TITLE, '80_図名・縮尺・方位', ha='left', va='top')
    A.text(ext[0] + 300, -2400, '← 西', PT_NOTE, '80_図名・縮尺・方位', ha='left', va='bottom')
    A.text(16000, -2400, '東 →', PT_NOTE, '80_図名・縮尺・方位', ha='right', va='bottom')
    for j in range(5):
        A.ax.add_patch(plt.Rectangle((3000 + j * 1000, -2450), 1000, 150, fc='k' if j % 2 == 0 else 'white', ec='k', lw=LW(0.1)))
    A.text(3000, -2050, '0', PT_NOTE, '80_図名・縮尺・方位'); A.text(8000, -2050, '5 m', PT_NOTE, '80_図名・縮尺・方位')
    x0, y0 = A.ox / 100 + ext[0] / 100, H_ - (A.oy + ext[3]) / 100
    print('section D', 'k', SEC_D_K, 'u', round(val), 'paper mm', round(x0), round(y0), round(x0 + (ext[1] - ext[0]) / 100), round(y0 + (ext[3] - ext[2]) / 100))
    return S

def legend_materials(S, x_mm, y_mm):
    """断面の凡例（材料構造表示記号、JIS A 0150 の 1/100 の簡略表示）。紙の (x_mm, y_mm) から右へ"""
    L = S.axes(x_mm, y_mm, (0, 40000, 0, 2000)); L.annot_all = True     # 凡例は文字の層にも全部
    L.text(0, 1700, '凡例（材料構造の表示、1/100 の簡略表示）', PT_NOTE, '80_図名・縮尺・方位', ha='left', va='center')
    lay = '01_切断（構造・壁）'; x = 0; y0, y1 = 300, 900
    def item(label, draw):
        nonlocal x
        draw(x); L.text(x + 1500, (y0 + y1) / 2, label, PT_NOTE, '80_図名・縮尺・方位', ha='left', va='center'); x += 1500 + len(label) * 260 + 700
    def cut_(x): g = box(x, y0, x + 1200, y1); L.fill(g, lay, fc='k', z=6); L.geom_lines(g.boundary, lay, lw=LW_CUT, z=6)
    def conc_(x): g = box(x, y0, x + 1200, y1); L.fill(g, lay, fc='0.72', z=6); L.geom_lines(g.boundary, lay, lw=LW_CUT, z=6.1)
    def wood_(x): g = box(x, y0, x + 1200, y1); L.fill(g, lay, fc='#E9DCC4', z=6); L.geom_lines(g.boundary, lay, lw=0.1, z=6.1)
    def ins_(x): insul_fill(L, box(x, y0 + 150, x + 1200, y1 - 150)); L.geom_lines(box(x, y0 + 150, x + 1200, y1 - 150).boundary, lay, lw=LW_THIN, z=6.6)
    def ground_(x): L.lines([[(x, y1), (x + 1200, y1)]], lay, lw=LW_CUT, z=8); ground_hatch(L, x, x + 1200, None, gl=y1)
    item('切断した構造・壁・床', cut_)
    item('基礎（コンクリート）', conc_)
    item('木（構造用合板・垂木）', wood_)
    item('断熱材（保温材）', ins_)
    item('地盤', ground_)

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
ELEV = {}; ELEV_RT = {}
for key_, ttl, cap_, vd, _ in ELEV_VIEWS:
    rt = np.array([vd[1], -vd[0]]); ELEV_RT[key_] = (np.asarray(vd, float), rt)
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
    return merge_fine_objs(out)
ELEV_FILL = lambda ob: ('#DCE9F2' if kind(ob['layer']) == 'glass' else
                        '#BDBDBD' if num(ob['layer']) in (10, 20, 26, 28) else
                        '#E9DCC4' if num(ob['layer']) in (11, 22, 18, 30, 50) or ob['layer'].startswith(('16', '19b', '89')) and kind(ob['layer']) != 'glass' else
                        'white')
YAMATO, YAMATO_P = (17, 21), 120        # 杉の大和張りの外壁（本館 17・西館 21、ほかに機械室 35_ の塊も、10-26）、見えの割り 約120
def yamato_lines(A, mode, ob, vis):
    """見る人に向く立った面ごとに、壁に沿って 120 おきの縦の線（面の上の位置で割るので、弧や斜めの壁では見えの間隔が詰まる）。
    同じ物の奥の面（反対側の壁の内側など）は手前の面で隠す。線は物の見える所（vis）だけ。"""
    _, H, D, _ = ELEV[mode]
    T = ob['T']; nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L = np.linalg.norm(nrm, axis=1)
    ok = L > 1e-6; T = T[ok]; nrm = nrm[ok] / L[ok, None]
    vd = np.array(ELEV_VIEWS[[v[0] for v in ELEV_VIEWS].index(mode)][3], float)
    face = (np.abs(nrm[:, 2]) < 0.15) & ((nrm[:, :2] @ vd) < -0.2)                # 立った面で、見る人の側に向く面（外向きの法線、10-26）
    T = T[face]; nrm = nrm[face]
    if not len(T): return
    t2 = np.stack([-nrm[:, 1], nrm[:, 0]], -1); t2 /= np.linalg.norm(t2, axis=1, keepdims=True)
    sgn = np.where(t2[:, 0] + 1e-9 * t2[:, 1] < 0, -1.0, 1.0)[:, None]; t2 *= sgn         # 面の向きの表裏を一つに
    nn = np.stack([t2[:, 1], -t2[:, 0]], -1); off = (T[:, 0, :2] * nn).sum(1)
    ang = np.round(np.degrees(np.arctan2(t2[:, 1], t2[:, 0])) / 0.3).astype(int); key = np.round(off / 15).astype(int)
    panels = {}
    for i in range(len(T)): panels.setdefault((ang[i], key[i]), []).append(i)      # 同じ平面の三角形の組（板の面）
    P = T.reshape(-1, 3); h = H(P).reshape(-1, 3); d = D(P).reshape(-1, 3)
    pl = []
    for ids in panels.values():
        ids = np.array(ids)
        polys = [Polygon(np.stack([h[i], T[i, :, 2]], -1)) for i in ids]
        g = unary_union([q.buffer(0.5) for q in polys if q.is_valid and q.area > 1])
        if g.is_empty or g.area < 2e4: continue
        pl.append((float(d[ids].mean()), g, t2[ids[0]], T[ids[0], 0]))
    pl.sort(key=lambda t: t[0])
    cover = Polygon(); segs = []
    for _, g, t, o in pl:
        vg = g.difference(cover) if not cover.is_empty else g
        cover = unary_union([cover, g]) if not cover.is_empty else g
        if vg.is_empty: continue
        z0, z1 = vg.bounds[1] - 10, vg.bounds[3] + 10
        hx0 = float(H(np.array([[*o[:2], 0.]]))[0]); dh = float(H(np.array([[*(o[:2] + t), 0.]]))[0]) - hx0   # s が 1 進むと x は dh
        if abs(dh) < 0.4: continue                          # 見る向きに対して寝た面（線が詰まって黒くなる）は描かない
        xs = vg.bounds[0], vg.bounds[2]
        s_lo, s_hi = sorted(((xs[0] - hx0) / dh + o[:2] @ t, (xs[1] - hx0) / dh + o[:2] @ t))
        for s0 in np.arange(math.ceil(s_lo / YAMATO_P), math.floor(s_hi / YAMATO_P) + 1) * YAMATO_P:
            x = hx0 + (s0 - o[:2] @ t) * dh
            seg = LineString([(x, z0), (x, z1)]).intersection(vg)
            if not seg.is_empty: segs.append(seg)
    if not segs: return
    g = unary_union(segs).intersection(vis.buffer(-8))
    if not g.is_empty: A.geom_lines(g, '09b_立面_大和張り', lw=0.05, color='0.45', z=2.5)

ELEV_RES = 10.0          # 見える所を決める格子（mm）。1/100 で 0.1 mm（水切り 20 mm の上下の縁が線になるように）
def _raster(tris_hz, depth, ids, shape, x0, z0, R, zb, ib, chunk=3_000_000, it=None):
    """三角形（見る面の (h, z) と奥行き）を格子に描き、格子ごとにいちばん手前の奥行き zb と物の番号 ib を残す（z バッファ）"""
    ny, nx = shape
    X = (tris_hz[:, :, 0] - x0) / R; Y = (tris_hz[:, :, 1] - z0) / R
    ix0 = np.clip(np.floor(X.min(1)).astype(int), 0, nx - 1); ix1 = np.clip(np.ceil(X.max(1)).astype(int), 0, nx - 1)
    iy0 = np.clip(np.floor(Y.min(1)).astype(int), 0, ny - 1); iy1 = np.clip(np.ceil(Y.max(1)).astype(int), 0, ny - 1)
    w = ix1 - ix0 + 1; h = iy1 - iy0 + 1; n = (w * h).astype(np.int64)
    ax, ay, bx, by, cx, cy = X[:, 0], Y[:, 0], X[:, 1], Y[:, 1], X[:, 2], Y[:, 2]
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    good = np.abs(den) > 1e-9
    order = np.nonzero(good)[0]
    cs = np.cumsum(n[order]); start = 0
    while start < len(order):
        end = max(start + 1, int(np.searchsorted(cs, (cs[start - 1] if start else 0) + chunk)) + 1)
        sel = order[start:end]; start = end
        cnt = n[sel]; tot = int(cnt.sum())
        if tot == 0: continue
        t = np.repeat(sel, cnt)
        k = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        px = ix0[t] + k % w[t]; py = iy0[t] + k // w[t]
        fx = px + 0.5; fy = py + 0.5
        l1 = ((by[t] - cy[t]) * (fx - cx[t]) + (cx[t] - bx[t]) * (fy - cy[t])) / den[t]
        l2 = ((cy[t] - ay[t]) * (fx - cx[t]) + (ax[t] - cx[t]) * (fy - cy[t])) / den[t]
        l3 = 1 - l1 - l2
        ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not ins.any(): continue
        t, px, py, l1, l2, l3 = t[ins], px[ins], py[ins], l1[ins], l2[ins], l3[ins]
        dd = l1 * depth[t, 0] + l2 * depth[t, 1] + l3 * depth[t, 2]
        flat = py * nx + px
        np.minimum.at(zb, flat, dd)
        win = dd <= zb[flat] + 1e-6
        ib[flat[win]] = ids[t[win]]
        if it is not None: it[flat[win]] = t[win]

def _mask_poly(mask, x0, z0, R):
    """格子の真偽 → 形（m m）。外の輪と穴は向きで分ける"""
    from skimage import measure
    if not mask.any(): return Polygon()
    M = np.pad(mask.astype(np.uint8), 1)
    outs, holes = [], []
    for c in measure.find_contours(M, 0.5):
        if len(c) < 4: continue
        pts = np.c_[x0 + (c[:, 1] - 1 + 0.5) * R, z0 + (c[:, 0] - 1 + 0.5) * R]
        pg = Polygon(pts)
        if not pg.is_valid: pg = pg.buffer(0)
        if pg.is_empty or pg.area < 4 * R * R: continue
        sa = 0.5 * np.sum(pts[:-1, 0] * pts[1:, 1] - pts[1:, 0] * pts[:-1, 1])
        (outs if sa > 0 else holes).append(pg)
    if not outs: return Polygon()
    g = unary_union(outs)
    if holes: g = g.difference(unary_union(holes))
    return g.buffer(R * 0.3, join_style=2).buffer(-R * 0.3, join_style=2)

def _fill_cracks(zb, ib, it, ny, nx, gap=50.0):
    """幅 1 ます（ELEV_RES）の割れ目をふさぐ：別々の立体に分けた壁のあいだの 1 mm ほどのすき間に格子の中心が落ちると、
    そこだけ奥が見えて、塗りの白い筋と、線の切れ端（すき間の縁）が出ていた（10-26）。両隣が手前で近い奥行きなら両隣でふさぐ。
    1/100 で 0.1 mm より細いすき間は図に描けないので、本当のすき間を消すことにはならない"""
    Z = zb.reshape(ny, nx); I = ib.reshape(ny, nx); T = it.reshape(ny, nx)
    for ax in (1, 0):
        Zs = Z if ax == 1 else Z.T; Is = I if ax == 1 else I.T; Ts = T if ax == 1 else T.T
        a, c, b = Zs[:, :-2], Zs[:, 1:-1], Zs[:, 2:]
        fin = np.isfinite(a) & np.isfinite(b)
        crk = fin & (np.abs(np.where(fin, a - b, 0)) < gap) & (c > np.maximum(a, b) + gap)
        r_, c_ = np.nonzero(crk); c_ = c_ + 1
        src = np.where(Zs[r_, c_ - 1] <= Zs[r_, c_ + 1], c_ - 1, c_ + 1)
        Zs[r_, c_] = Zs[r_, src]; Is[r_, c_] = Is[r_, src]; Ts[r_, c_] = Ts[r_, src]

ELEV_OUTLINE_ONLY = ('30_', '50c', '29_', '50b', '16b', '10p', '20p', '16e', '58', '50d', '17g')
def _feature_edges(T, vd, crease_deg=25.0):
    """物の三角形 T（3D）から、立面に描く線になる辺：折れ目（隣の面と crease_deg 以上折れる）・縁（面が片側だけ）・
    輪郭（隣の面の一方が見る人に向き、もう一方が背を向ける：丸い柱など）→ (n, 2, 3)"""
    import trimesh as _tm
    try:
        m = _tm.Trimesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3), process=False)
        m.merge_vertices(digits_vertex=1)
    except Exception:
        return np.zeros((0, 2, 3))
    if len(m.faces) == 0: return np.zeros((0, 2, 3))
    V = m.vertices; out = []
    try:
        adj = m.face_adjacency; ang = m.face_adjacency_angles; e = m.face_adjacency_edges
        fn = m.face_normals; s0 = fn[adj[:, 0]] @ vd; s1 = fn[adj[:, 1]] @ vd
        tri = m.triangles; el = np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2).max(1)
        alt = 2 * m.area_faces / np.maximum(el, 1e-9)                            # いちばん長い辺に対する高さ
        good = alt > 8.0
        big = good[adj[:, 0]] & good[adj[:, 1]]                                   # 細い三角形（面の向きが当てにならない）の折れは線にしない
        # 細い三角形の帯を挟んで同じ平面に戻る所も線にしない：両側の大きい面どうしで比べる代わりに、折れの両側が同じ平面かを頂点で確かめる
        keep = (ang > math.radians(crease_deg)) | ((s0 < 0) != (s1 < 0))      # 候補は広く取り、本当の線かは画面の上で確かめる（elevation）
        out.append(V[e[keep]])
    except Exception:
        pass
    eu = m.edges_sorted; g = _tm.grouping.group_rows(eu, require_count=1)
    if len(g): out.append(V[eu[g]])
    return np.concatenate(out) if out else np.zeros((0, 2, 3))

def elevation(A, mode, objs):
    """立面（水平な視線の正投影）。見える所は z バッファ（ELEV_RES の格子）で三角形ごとに手前・奥を決め、塗りは物ごとの見える所。
    線は物の折れ目・縁・輪郭の辺（_feature_edges）を z バッファで隠線処理して、見える所だけ（水切り・壁の出隅・軒先・窓の枠の線も出る）。
    （10-26 監修、ユーザー：製図として完全に正しく。前は物ごと・塊ごとに手前から塗り、線は物の外形だけだったので、重なる順の取り違え
    （屋根の白抜け・窓の欠け）と、物の中の線（水切りなど）の抜けがあった）。ガラスは向こうを隠さない：ガラスの奥の線は細い灰色"""
    _, H, D, _ = ELEV[mode]
    vd = np.array(ELEV_VIEWS[[v[0] for v in ELEV_VIEWS].index(mode)][3], float); vd3 = np.array([vd[0], vd[1], 0.0])
    R = ELEV_RES
    recs = []
    for ob in objs:
        T = ob['T']
        P = T.reshape(-1, 3); h = H(P).reshape(-1, 3); d = D(P).reshape(-1, 3)
        recs.append((ob, np.stack([h, T[:, :, 2]], -1), d))
    allh = np.concatenate([r_[1][:, :, 0].ravel() for r_ in recs]); allz = np.concatenate([r_[1][:, :, 1].ravel() for r_ in recs])
    x0, z0 = allh.min() - 2 * R, allz.min() - 2 * R
    nx = int(math.ceil((allh.max() - x0) / R)) + 3; ny = int(math.ceil((allz.max() - z0) / R)) + 3
    zbO = np.full(nx * ny, np.inf); ibO = np.full(nx * ny, -1, np.int32); itO = np.full(nx * ny, -1, np.int64)
    zbG = np.full(nx * ny, np.inf); ibG = np.full(nx * ny, -1, np.int32)
    GL_ = [i for i, r_ in enumerate(recs) if kind(r_[0]['layer']) == 'glass']
    OP_ = [i for i, r_ in enumerate(recs) if kind(r_[0]['layer']) != 'glass']
    NRM = np.zeros((1, 3))
    for grp, zb, ib, it in ((OP_, zbO, ibO, itO), (GL_, zbG, ibG, None)):
        if not grp: continue
        T2s = np.concatenate([recs[i][1] for i in grp]); ds = np.concatenate([recs[i][2] for i in grp])
        ids = np.concatenate([np.full(len(recs[i][1]), i, np.int32) for i in grp])
        _raster(T2s, ds, ids, (ny, nx), x0, z0, R, zb, ib, it=it)
        if it is not None:                                                       # 見えている面の向き（線の判定に使う）
            T3 = np.concatenate([recs[i][0]['T'] for i in grp]); NRM = np.cross(T3[:, 1] - T3[:, 0], T3[:, 2] - T3[:, 0])
            NRM /= np.maximum(np.linalg.norm(NRM, axis=1, keepdims=True), 1e-9)
    _fill_cracks(zbO, ibO, itO, ny, nx)
    glass_front = (zbG < zbO)
    ibO2 = ibO.reshape(ny, nx); gf2 = glass_front.reshape(ny, nx); ibG2 = ibG.reshape(ny, nx)
    GOCC = _mask_poly(gf2, x0, z0, R)
    wvis = {}; allsil = []
    present = set(np.unique(ibO[ibO >= 0]).tolist()) | set(np.unique(ibG[(ibG >= 0) & glass_front]).tolist())
    order = sorted(present, key=lambda i: float(recs[i][2].min()))
    TOL = 30.0
    for i in order:
        ob, T2, d = recs[i]; k = kind(ob['layer'])
        vis = _mask_poly(((ibG2 == i) & gf2) if k == 'glass' else (ibO2 == i), x0, z0, R)
        if vis.is_empty: continue
        sil = silhouette(T2)
        if sil is not None and not sil.is_empty: allsil.append(sil)
        fvis = vis.difference(GOCC) if (k != 'glass' and not GOCC.is_empty) else vis
        # 3dm に上板（17y、yamato.py）があれば、本館（17）と機械室（35）の合成の縦線は描かない（上板の輪郭と二重になる）。西館（21）は合成のまま
        if HAS17Y and ob['layer'].startswith(('17', '35_')): pass
        elif HAS21Y and ob['layer'].startswith(('21_', '21y_')): pass   # 西館（21）も上板（21y）があれば合成の縦線を描かない（西館係、10-28）
        elif (num(ob['layer']) in YAMATO or ob['layer'].startswith('35_')) and k != 'glass' and not fvis.is_empty: wvis.setdefault(id(ob), (ob, []))[1].append(fvis)
        lay = LAYER_OF[k][1]
        fc = ELEV_FILL(ob)
        if fc != 'white' and not fvis.is_empty: A.fill(fvis, lay, fc=fc, z=1, seam=True)
        # 細かく繰り返す物（ルーバー・LED・ガラリ・太陽光の板・天井扇・ロゴ）は、1/100 で線が詰まって黒くなるので外形だけ（前のとおり）
        if ob['layer'].startswith(ELEV_OUTLINE_ONLY):
            if sil is not None and not sil.is_empty:
                eg = sil.boundary.intersection(vis.buffer(1.5 * R))
                if not eg.is_empty: A.geom_lines(eg, lay, lw=0.09 if k == 'glass' else 0.13, color='#3d6f9a' if k == 'glass' else 'k', z=3)
            continue
        # 線：折れ目・縁・輪郭の辺を細かく区切り、z バッファで見える所だけ
        E = _feature_edges(ob['T'], vd3)
        if not len(E): continue
        P = E.reshape(-1, 3); eh = H(P).reshape(-1, 2); ed = D(P).reshape(-1, 2); ez = P[:, 2].reshape(-1, 2)
        L2 = np.hypot(eh[:, 1] - eh[:, 0], ez[:, 1] - ez[:, 0]); ok = L2 > 1.0
        eh, ed, ez, L2 = eh[ok], ed[ok], ez[ok], L2[ok]
        if not len(L2): continue
        ns_all = np.maximum(2, np.ceil(L2 / R).astype(int) + 1)
        front, back = [], []
        cs = np.cumsum(ns_all); st0 = 0
        while st0 < len(L2):                                          # 辺を区切って少しずつ（大きな物で記憶があふれないように）
            en0 = int(np.searchsorted(cs, (cs[st0 - 1] if st0 else 0) + 1_000_000)) + 1
            en0 = max(st0 + 1, min(en0, len(L2)))
            sl = slice(st0, en0); st0 = en0
            ehc, edc, ezc, L2c, ns = eh[sl], ed[sl], ez[sl], L2[sl], ns_all[sl]
            eid = np.repeat(np.arange(len(L2c)), ns); t = (np.arange(ns.sum()) - np.repeat(np.cumsum(ns) - ns, ns)) / np.repeat(ns - 1, ns)
            sh = ehc[eid, 0] + t * (ehc[eid, 1] - ehc[eid, 0]); sz = ezc[eid, 0] + t * (ezc[eid, 1] - ezc[eid, 0]); sd = edc[eid, 0] + t * (edc[eid, 1] - edc[eid, 0])
            px = np.clip(((sh - x0) / R).astype(int), 0, nx - 1); py = np.clip(((sz - z0) / R).astype(int), 0, ny - 1); fl = py * nx + px
            # 辺の両側（画面で辺に直角に 1 ます）の見えている面をくらべ、奥行きか面の向きか物が変わる所だけを線にする
            # （同じ平面がつながっている所の継ぎ目・まとめた立体の内側に残ったすき間の面は線にしない。水切りの上下の縁は奥行きが変わるので線になる）
            dh_ = (ehc[:, 1] - ehc[:, 0]) / L2c; dz_ = (ezc[:, 1] - ezc[:, 0]) / L2c
            oh = -dz_[eid] * 1.0 * R; oz = dh_[eid] * 1.0 * R
            def at_(hh, zz):
                qx = np.clip(((hh - x0) / R).astype(int), 0, nx - 1); qy = np.clip(((zz - z0) / R).astype(int), 0, ny - 1); return qy * nx + qx
            fa_, fb_ = at_(sh + oh, sz + oz), at_(sh - oh, sz - oz)
            za, zb_ = zbO[fa_], zbO[fb_]; ta, tb = itO[fa_], itO[fb_]
            na = np.where((ta >= 0)[:, None], NRM[np.maximum(ta, 0)], 0.0); nb = np.where((tb >= 0)[:, None], NRM[np.maximum(tb, 0)], 0.0)
            cosab = np.abs((na * nb).sum(1))
            zc = zbO[fl]; fin3 = np.isfinite(za) & np.isfinite(zb_) & np.isfinite(zc)
            # 奥行きの段：両側と真ん中の 2 階の差（斜めに見る壁は奥行きが一様に変わるので、両側の差だけだと段に見えて、
            # 窓の区切りで分けた壁の継ぎ目が線になっていた、10-26）
            step = np.abs(np.where(fin3, za + zb_ - 2 * np.where(fin3, zc, 0), 0)) > 8.0
            disc = ((np.isinf(za) != np.isinf(zb_)) | (np.isinf(za) != np.isinf(zc)) | step
                    | (cosab < math.cos(math.radians(20))) | (ibO[fa_] != ibO[fb_]))
            nearest = np.minimum(za, zb_)
            if k == 'glass':
                seen = (sd <= zbO[fl] + TOL) & (sd <= zbG[fl] + TOL)
                behind = np.zeros_like(seen)
            else:
                seen = (sd <= nearest + TOL) & disc                       # 物の番号では決めない（まとめた外壁は手前と奥の壁が同じ物）
                behind = seen & (zbG[fl] < sd - TOL)                      # ガラスの奥
            br = np.r_[0, np.cumsum(ns)]
            for mask, outl in ((seen & ~behind, front), (behind, back)):
                if not mask.any(): continue
                for j in np.unique(eid[mask]):
                    mm = mask[br[j]:br[j + 1]]; hh = sh[br[j]:br[j + 1]]; zz = sz[br[j]:br[j + 1]]
                    dmm = np.diff(np.r_[0, mm.astype(np.int8), 0]); st = np.nonzero(dmm == 1)[0]; en = np.nonzero(dmm == -1)[0] - 1
                    for a_, b_ in zip(st, en):
                        if b_ > a_: outl.append([(hh[a_], zz[a_]), (hh[b_], zz[b_])])
        if k == 'glass':
            if front: A.lines(front, lay, lw=0.09, color='#3d6f9a', z=3)
        else:
            if front: A.lines(front, lay, lw=0.13, color='k', z=3)
            if back: A.lines(back, lay, lw=0.06, color='0.55', z=3)
    for ob, vs in wvis.values():                                       # 外壁の大和張り：縦の板の線
        yamato_lines(A, mode, ob, unary_union(vs))
    # 建物の外形（空との境）を太い線に：見えがかり 0.13 の中で建物の形が読めるように（線の強弱）
    if allsil:
        allocc = unary_union(allsil).buffer(3, join_style=2).buffer(-3, join_style=2)
        ext = [LineString(p.exterior.coords) for p in getattr(allocc, 'geoms', [allocc]) if p.geom_type == 'Polygon' and p.area > 2e5]
        if ext: A.geom_lines(unary_union(ext), '09_立面の外形', lw=LW_CUT, color='k', z=3.5)
    return order

def elev_marks(A, mode, objs, h0, h1, with_levels=True):
    """GL の線、高さの記号、通り芯（東・西は架構 1〜20、南・北は W・E）"""
    _, H, D, right = ELEV[mode]
    A.lines([[(h0 - 2500, -300), (h1 + 2500, -300)]], '01_切断（構造・壁）', lw=LW_CUT, z=8, annot=True)   # GL
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
        A.text(x_text + 300, zt + 60, f'{nm}　{"+" if z > 0 else "±" if z == 0 else "−"}{abs(z):,.0f}', PT_DIM, '51_高さ', ha='left', va='bottom', color='#2E7D32')
    if not ELEV_GRID:
        return
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

ELEV_GRID = False                                      # 立面図に通り芯の丸と番号を描かない（ユーザー 10-27、プレゼンの準備：薄い円がたくさん見える）
EXT_LINE = ('60', '66', '70', '71', '72', '73')      # 外構：細い線だけ（塗らない）
EXT_TREE = ()                                          # 樹木は描かない（ユーザー 10-27：薄い円がたくさん見える、消す）。前は ('77', '79', '94') の淡い輪郭
def elev_exterior(A, mode, objs, h0, h1):
    """建物の手前（見る人の側）の外構と樹木を、建物の上に線だけで（10-27 プレゼンの準備 20261027-0707、ユーザー）。
    手前かどうか：物の中ほどの位置で、建物（ガラスを除く）のいちばん手前の奥行きより手前にあるもの。建物の幅の外の物は、
    建物の手前の線（建物のいちばん手前の奥行き）より手前で 25 m 以内。木は 25 m より奥を描かない（園庭の側は木が多い）"""
    _, H, D, _ = ELEV[mode]
    B = [ob for ob in objs if kind(ob['layer']) != 'glass']
    bh = np.concatenate([H(ob['T'].reshape(-1, 3)) for ob in B]); bd = np.concatenate([D(ob['T'].reshape(-1, 3)) for ob in B])
    BIN = 1000.0; kb = np.floor(bh / BIN).astype(int); front = {}
    for k_, d_ in zip(kb, bd): front[k_] = min(front.get(k_, np.inf), d_)
    d_all = float(bd.min())
    n_line = n_tree = 0; ids = {id(o) for o in objs}; parts_ = {}
    for ob in OBJ:
        ln = ob['layer']; pre = ln.split('_')[0]
        tree = pre in EXT_TREE
        if not (tree or pre in EXT_LINE): continue
        if id(ob) in ids: continue
        P = ob['T'].reshape(-1, 3); h = H(P); d = D(P)
        hc = float(np.median(h))
        if hc < h0 - 1000 or hc > h1 + 1000: continue
        fd = front.get(int(math.floor(hc / BIN)), np.inf)
        ref = fd if np.isfinite(fd) else d_all
        if float(np.median(d)) > ref - 200: continue                     # 建物の奥（または中）
        if float(np.median(d)) < ref - 25000: continue                    # 遠すぎる
        sil = silhouette(np.stack([h, P[:, 2]], -1).reshape(-1, 3, 2))
        if sil is None or sil.is_empty: continue
        sil = sil.intersection(box(h0 - 1000, -300, h1 + 1000, 1e6))      # GL より下は描かない
        if sil.is_empty: continue
        if tree:
            if float(np.median(d)) < ref - 15000: continue                # 木は手前 15 m まで
            A.geom_lines(sil.boundary, '12_立面_外構・樹木', lw=0.05, color='#9DBB88', z=4); n_tree += 1
        else:
            parts_.setdefault(pre, []).append(sil); n_line += 1
    # 塀・柵は板ごとの物（大和張りの板 135 と胴縁）なので、レイヤーごとに足し合わせた外形を線に（板ごとの外形だと 1/100 で黒く詰まる）
    for pre, L in parts_.items():
        g = unary_union([x.buffer(15) for x in L]).buffer(-15)
        if not g.is_empty: A.geom_lines(g.boundary, '12_立面_外構・樹木', lw=0.07, color='0.25', z=4)
    print('elevation', mode, '外構', n_line, '樹木', n_tree)

def _up_min_z(prefixes):
    """屋根の上を向く面のいちばん低い所（片流れの屋根の軒先の上端）"""
    zs = []
    for ob in OBJ:
        if ob['layer'].split('_')[0] not in prefixes: continue
        T = ob['T']; nz = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L = np.linalg.norm(nz, axis=1)
        up = (L > 1e-6) & (nz[:, 2] > 0.5 * np.maximum(L, 1e-9))
        if up.any(): zs.append(T[up][:, :, 2].min())
    return min(zs) if zs else None
ELEV_H = {}
def elev_heights(objs):
    """立面の高さの寸法に使う数（3dm から一度だけ）：本館・西館の軒先（GL から）と最高"""
    if ELEV_H: return ELEV_H
    west = lambda ob: float(_uv(ob['T'].reshape(-1, 3)[:, :2]).mean(0)[1]) < -400        # 西館（すき間より西）
    zmax = {'本館': -1e9, '西館': -1e9}
    for ob in objs:
        k = '西館' if west(ob) else '本館'; zmax[k] = max(zmax[k], float(ob['T'][:, :, 2].max()))
    ELEV_H.update({'本館の軒先': _up_min_z(('10',)), '西館の軒先': _up_min_z(('20',)), '本館の最高': zmax['本館'], '西館の最高': zmax['西館']})
    print('elev heights', {k: (round(v) if v is not None else None) for k, v in ELEV_H.items()})
    return ELEV_H

def elev_dims(A, mode, objs, h0, h1):
    """立面：建物の全長（GL の下に一本）と、GL から軒先・最高までの高さ（左の端の外に）"""
    E_ = elev_heights(objs)
    hdim(A, h0, h1, -1500, '建物の全長' if mode in ('garden', 'road', 'river') else '建物の幅', above=False)
    items = [('本館の軒先', '本館の軒の高さ'), ('本館の最高', '本館の最高'), ('西館の軒先', '西館の軒の高さ'), ('西館の最高', '西館の最高（10 m 以下）')]
    x = h0 - 900
    for key, lab in items:
        z = E_.get(key)
        if z is None: continue
        vdim(A, x, -300, z, lab); x -= 700

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
        ext = (h.min() - 4500, h.max() + (8500 if lv else 1500), *zr)      # 左は高さの寸法（elev_dims）
        x_mm = (W_ - (ext[1] - ext[0]) / 100) / 2 if xpos == 'center' else xpos
        y_mm = top - row * (hgt + gap)
        A = S.axes(x_mm, y_mm, ext)
        vd_, rt_ = ELEV_RT[mode]
        S.view(A, ttl, 'elevation', key=mode, origin=(0.0, 0.0, 0.0), right=(rt_[0], rt_[1], 0.0), up=(0.0, 0.0, 1.0),
               view_dir=(vd_[0], vd_[1], 0.0), _='水平な視線の正投影（奥の限りなし）。描く物は elev_objs()（建物：レイヤー 05〜69 と 89）')
        elevation(A, mode, objs); elev_exterior(A, mode, objs, h.min(), h.max()); elev_marks(A, mode, objs, h.min(), h.max(), lv)
        elev_dims(A, mode, objs, h.min(), h.max())
        print('elevation', mode, '幅（紙 mm）', round((ext[1] - ext[0]) / 100), 'x', round(x_mm))
        A.text(ext[0] + 300, zr[1] - 100, f'{ttl}　1/100　（{cap_}）', PT_TITLE, '80_図名・縮尺・方位', ha='left', va='top')
        if first:
            sx = h.max() + 2000
            for j in range(5):
                A.ax.add_patch(plt.Rectangle((sx + j * 1000, -2150), 1000, 150, fc='k' if j % 2 == 0 else 'white', ec='k', lw=LW(0.1)))
            A.text(sx, -1750, '0', PT_NOTE, '80_図名・縮尺・方位'); A.text(sx + 5000, -1750, '5 m', PT_NOTE, '80_図名・縮尺・方位')
            first = False
    S.text_paper(W_ - 15, 26, '建物と、その手前の外構（塀・柵・木戸・棚・柱、細い線）。駐車・駐輪・室内の家具は省いた。灰色は屋根の面、薄い青はガラス（奥は細い灰色の線で透けて見える）。建物の外形は太い線。'
                 + note_row, PT_NOTE, ha='right', color='0.35')
    return S

ELEV_SHEETS = [('sodachiya_elevations_1-100', lambda: make_elevations(
                    [('garden', 0, 'center', True), ('road', 1, 'center', True), ('south', 2, 'center', True)],
                    '立面図 1　園庭の側・道路の側・南の妻　1/100（A1）',
                    '\n園庭の側と道路の側は本館の弧の真ん中に正対（平面と同じ向き、架構の番号は下の丸）。南の妻は架構 1 に正対。')),
               ('sodachiya_elevations2_1-100', lambda: make_elevations(
                    [('river', 0, 'center', True), ('north', 1, 'center', True)],
                    '立面図 2　高野川の側・北の妻　1/100（A1）',
                    '\n高野川の側は川の向こうから川の辺に直角に、北の妻は架構 20 に正対。'))]


# ---------------------------------------------------------------- 配置図 1/200（監修 renkei 20261025-1747-kanshu、アプローチ係 data/siteplan_approach.json）
# 向きは3枚目の平面図と同じ（高野川を下辺）。建物は屋根伏せ、外構・園庭・周辺（PLATEAU）・課題の敷地図をなぞった線・敷地の境・方位。
# 外構の描き方・文字・記号・道すじ・注はアプローチ係の json から（座標は 3dm の m）。A1 横（10-26夜、プレゼンの準備：南へ高野川の水面まで、紙も大きく）。
def make_siteplan():
    import json as _j
    W_, H_, SC = 841, 594, 200
    S = Sheet(W_, H_, '配置図　1/200（A1）　高野川を下に（北は方位の矢印）', scale=SC, notitle=True)   # 文字は図に入れない（ユーザー10-26：素材にする、DXFの60・80のレイヤーには残す）
    ph = _view_rot(); c_, n_ = math.cos(ph), math.sin(ph)
    rp = lambda P: np.c_[np.asarray(P)[:, 0] * c_ - np.asarray(P)[:, 1] * n_, np.asarray(P)[:, 0] * n_ + np.asarray(P)[:, 1] * c_]
    cr = rp(np.array(list(SITE_C.values())))
    mid = (cr.min(0) + cr.max(0)) / 2 + np.array([-3000.0, 0.0])
    MG = 10
    w_, h_ = (W_ - 2 * MG) * SC, (H_ - 2 * MG) * SC
    ext = (mid[0] - w_ / 2, mid[0] + w_ / 2, mid[1] - h_ / 2 + 2000, mid[1] + h_ / 2 + 2000)   # A1：南は高野川の水面と向こう岸の手前まで（回した座標で y≈−31 m）、北・東・西も約20 m 広く
    A = S.axes(MG, MG, ext); A.phi = ph; A.dxf_only_text = True
    root = _root()
    SP = {}
    if root and os.path.isfile(os.path.join(root, 'data', 'siteplan_approach.json')):
        SP = _j.load(open(os.path.join(root, 'data', 'siteplan_approach.json'), encoding='utf-8'))
    M = lambda xy: np.asarray(xy, float) * 1000
    # 周辺（PLATEAU）：建物は薄い灰、道は白抜きの線
    for ob in OBJ:
        n = num(ob['layer'])
        if n not in (3, 4): continue
        sil = silhouette(ob['T'][:, :, :2])
        if sil is None: continue
        # 護岸・川（02、z 0.8〜0.9）より上に：川をまたぐ橋の道が川の上に見える
        if n == 4: A.fill(sil, '30_敷地・外構', fc='0.86', z=0.96); A.geom_lines(sil, '30_敷地・外構', lw=0.06, color='0.55', z=0.97)
        else: A.fill(sil, '30_敷地・外構', fc='0.97', z=0.94); A.geom_lines(sil, '30_敷地・外構', lw=0.06, color='0.6', z=0.95)
    # 高野川の護岸（02）：川・河川敷・石積みの崖・柵の土台（高さで分ける）
    for ob in OBJ:
        if num(ob['layer']) != 2: continue
        sil = silhouette(ob['T'][:, :, :2])
        if sil is None or sil.is_empty: continue
        z0, z1 = ob['T'][:, :, 2].min(), ob['T'][:, :, 2].max()
        if z1 <= -5700: A.fill(sil, '30_敷地・外構', fc='#CFE3EF', z=0.8)
        elif z1 - z0 < 800 and z1 < -4000: A.fill(sil, '30_敷地・外構', fc='#DDE8D0', z=0.8)
        elif z1 - z0 >= 800: A.fill(sil, '30_敷地・外構', fc='#BDB6AA', z=0.85, hatch='////')
        else: A.fill(sil, '30_敷地・外構', fc='#D8D4CC', z=0.85)
        A.geom_lines(sil, '30_敷地・外構', lw=0.05, color='0.45', z=0.9)
    # 課題の敷地図をなぞった線は描かない（ユーザー10-26：道は PLATEAU の道、向かいの住宅3軒は課題の図の道の縁に沿わせた add_context.py）
    # 敷地の境は外の一本だけ（00 には境から 1 m 内の線もある。ユーザー 10-27夜：配置図から 1 m の線を除く）
    _c00 = [P for ln, P in CURVES if ln.startswith('00') and len(P) > 2]
    _o00 = max(_c00, key=lambda P: abs(Polygon(P[:, :2]).area)) if _c00 else None
    for ln, P in CURVES:
        if ln.startswith('00'):
            if P is _o00: A.lines([P[:, :2]], '30_敷地・外構', lw=0.3, color='#C03030', ls=(0, (12, 3, 2, 3)), z=8)
            continue
        if num(ln) == 91:                              # 等高線：0.2 mごと、0.4 mごとを太く（築山がはっきり、プレゼンの準備の描き方）
            zc = float(np.mean(P[:, 2])) / 1000.0 if P.shape[1] > 2 else 0.0
            ix = abs(((zc - 0.1) / 0.4) - round((zc - 0.1) / 0.4)) < 0.05
            A.lines([P[:, :2]], '30_敷地・外構', lw=0.5 * 0.35 if ix else 0.3 * 0.35, color='#5F8049' if ix else '#7E9A68', z=1.15); continue
        if num(ln) == 92: A.lines([P[:, :2]], '30_敷地・外構', lw=0.15, color='#3d6f9a', z=1.2); continue
        if 70 <= num(ln) <= 79: A.lines([P[:, :2]], '30_敷地・外構', lw=0.09, color='0.45', z=1.1)
    LAYDEF = SP.get('layers', {})
    def lay_def(ln):
        for k, v in LAYDEF.items():
            if ln.startswith(k.split('_')[0] + '_'): return v
        return None
    # 園庭の地（data/garden.json、プレゼンの準備の描き方）：だいさんかく・しずかのもり
    GC = None
    try:
        sys.path.insert(0, os.path.join(root, 'scripts')); import garden_common as GC
    except Exception:
        GC = None
    if GC is not None:
        GX = GC.garden_poly()
        bank = [tuple(p_) for p_ in GC.G['BANK']['line']]
        shz = Polygon(GC.XS(bank + [(56.0, 18.2), (56.0, 37.0), (53.6, 36.0)] + [(a__, GC.d_edge(a__)) for a__ in np.linspace(53.4, 40.6, 20)])).buffer(0).intersection(GX)
        sc_ = lambda g: shp_affinity.scale(g, 1000, 1000, origin=(0, 0))
        A.fill(sc_(GX), '06_部屋の色', fc='#DDE9CF', z=0.4); A.fill(sc_(shz), '06_部屋の色', fc='#D0E1C2', z=0.45)
    # 駐車・駐輪に確保する場所（灰）、歩道（白）、スピードバンプ（縞）：アプローチ係の表
    for pg in SP.get('reserve', {}).get('polygons', []):
        A.fill(Polygon(M(pg)), '06_部屋の色', fc=SP['reserve'].get('fc', '#D8D8D4'), z=0.42)
    if SP.get('sidewalk'): A.fill(Polygon(M(SP['sidewalk']['pts'])), '06_部屋の色', fc='white', z=0.43)
    bp = SP.get('bump')
    if bp:
        Q = M(bp['pts']); P_ = Polygon(Q); A.fill(P_, '06_部屋の色', fc=bp.get('fc', '#8E8E8A'), z=0.44)
        e_ = [(Q[k], Q[(k + 1) % len(Q)]) for k in range(len(Q))]; a0, a1 = max(e_, key=lambda e: np.linalg.norm(e[1] - e[0]))
        dv = (a1 - a0) / np.linalg.norm(a1 - a0); L_ = np.linalg.norm(a1 - a0); pitch = bp.get('pitch', 0.45) * 1000
        nv = np.array([-dv[1], dv[0]])
        for k in range(int(L_ / pitch)):
            if k % 2: continue
            st_ = Polygon([a0 + dv * k * pitch - nv * 5e3, a0 + dv * (k + 1) * pitch - nv * 5e3, a0 + dv * (k + 1) * pitch + nv * 5e3, a0 + dv * k * pitch + nv * 5e3]).intersection(P_)
            A.fill(st_, '06_部屋の色', fc=bp.get('stripe', '#F4F4F2'), z=0.45)
    ARCH = []
    # 外構（70〜79）・園庭（90〜99）・本体の外（60〜67）
    for ob in OBJ:
        ln = ob['layer']; n = num(ln)
        if not (60 <= n <= 79 or 92 <= n <= 99): continue
        if n in (98,): continue
        sil = silhouette(ob['T'][:, :, :2])
        if sil is None or sil.is_empty: continue
        d = lay_def(ln) or {}
        dr = d.get('draw', 'outline')
        if n in (77, 79, 94) or dr == 'tree':
            A.fill(sil, '30_敷地・外構', fc='#CFE0B8', z=1.6); A.geom_lines(sil, '30_敷地・外構', lw=0.08, color='#6E8F4E', z=1.7); continue
        if n == 72 or dr == 'fill' and d.get('fc') == 'black':
            A.fill(sil, '30_敷地・外構', fc='k', z=3); continue
        if n == 76:
            A.fill(sil, '30_敷地・外構', fc='#EFE9DE', z=0.9); A.geom_lines(sil, '30_敷地・外構', lw=0.05, color='0.6', z=0.95); continue
        if n == 73:
            ARCH.append(sil); continue                 # ムベの棚：範囲全体を淡い緑に塗るだけ（下、ユーザー10-25夜）
        if n == 71:
            A.geom_lines(sil, '30_敷地・外構', lw=0.18, color='0.25', ls=(0, (4, 2)), z=2.5); continue
        if n == 70:
            A.fill(sil, '30_敷地・外構', fc='#8A6A4A', z=2.2); continue
        if n in (92, 99):
            A.fill(sil, '30_敷地・外構', fc='#CFE3EF', z=1.3); A.geom_lines(sil, '30_敷地・外構', lw=0.08, color='#3d6f9a', z=1.35); continue
        A.geom_lines(sil, '30_敷地・外構', lw=d.get('lw', 0.1), color='0.3', z=2)
    if ARCH: A.fill(unary_union([g.buffer(350) for g in ARCH]).buffer(900).buffer(-900), '30_敷地・外構', fc='#C9DFB0', z=1.4)
    # 雨の川：本館の東の軒の外の雨落ちの溝から南へ、護岸の落とし口まで（青い帯と流れの矢印、園庭の決定事項）
    if GC is not None:
        am = np.array([GC.UV(u__, GC.G['EDGE_V']) for u__ in np.linspace(57.0, 0.0, 40)]) * 1000
        amL = LineString(am).offset_curve(-300)
        if amL.is_empty or amL.length < 1000: amL = LineString(am)
        A.fill(amL.buffer(250, cap_style=2), '30_敷地・外構', fc='#C9E0EF', z=1.25)
        for f_ in np.linspace(0.08, 0.95, 9):
            p0 = np.array(amL.interpolate(f_, normalized=True).coords[0]); p1 = np.array(amL.interpolate(min(1, f_ + 0.01), normalized=True).coords[0])
            dv_ = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-6); nv_ = np.array([-dv_[1], dv_[0]])
            A.lines([[p0 - dv_ * 500 + nv_ * 280, p0, p0 - dv_ * 500 - nv_ * 280]], '30_敷地・外構', lw=0.25, color='#2F7FBF', z=1.3)
    # 建物：屋根伏せ（外形の太線、太陽光の面、光の筋、越屋根の蓋）
    def U(layers):
        g = [silhouette(ob['T'][:, :, :2]) for ob in OBJ if ob['layer'].split('_')[0] in layers]
        g = [x.buffer(20) for x in g if x is not None and not x.is_empty]
        return unary_union(g).buffer(-20) if g else None
    # 外形は光の筋（10t・20t）と越屋根の蓋も含めて一つに（10-26 監修、ユーザー：本館と西館で屋根の描かれ方が違う）。
    # 西館の屋根は光の筋ごとに別の片なので、片ごとの外形が太い線で描かれていた（本館は一枚の屋根に穴なので外形だけ）
    roof = U(('10', '20', '51', '35', '10t', '20t', '50a', '28'))
    if roof is not None:
        roof = unary_union([Polygon(x.exterior) for x in getattr(roof, 'geoms', [roof]) if x.geom_type == 'Polygon' and x.area > 1e6])
        A.fill(roof, '01_切断（構造・壁）', fc='#F2F0EC', z=3)
    pv = U(('10p', '20p'))
    if pv is not None: A.fill(pv, '10_見えがかり', fc='#5A5E66', z=3.2)
    for lay_, fc_ in ((('10t', '20t'), '#F4F1E6'), (('50a', '28', '50d'), '#D6E7F0')):
        g = U(lay_)
        if g is not None: A.fill(g, '10_見えがかり', fc=fc_, z=3.4); A.geom_lines(g, '10_見えがかり', lw=0.06, color='0.35', z=3.5)
    if roof is not None: A.geom_lines(roof, '01_切断（構造・壁）', lw=0.4, z=4)
    # 外構の記号（アプローチ係）
    for st in SP.get('parking', {}).get('stalls', []):
        q = M(st['xy']); A.text(q[0], q[1], st['mark'], 6 if st['mark'] == 'P' else 5, '60_部屋名・面積', color='#1F4E8C')
    e = SP.get('entrance')
    if e:
        q = M(e['xy']); A.ax.add_patch(plt.Circle(tuple(A.rot(q)), 350, fc='#D33A3A', ec='none', zorder=9))
    sl = SP.get('security_line')
    if sl: A.lines([M(sl['pts'])], '70_断面の位置', lw=0.25, color='#D33A3A', ls=(0, (6, 3)), z=8)
    # 道すじ（SP['walks'] の茶の破線）は描かない（ユーザー 10-29：配置図の動線は全て消す。データは残す）
    for t in SP.get('trees', []):
        q = M(t['xy']); A.text(q[0], q[1] - t.get('r', 1.5) * 1000 - 400, t['name'], 5, '60_部屋名・面積', color='#4E6B34')
    SZ = {'key': 8, 'name': 6.5, 'small': 5, 'context': 6.5}
    for lb in SP.get('labels', []):
        q = M(lb['xy']); k = lb.get('kind', 'name')
        rot = 0
        if lb.get('along'):
            v = np.array(lb['along'], float); v = A.rot(v); rot = math.degrees(math.atan2(v[1], v[0]))
            rot = ((rot + 90) % 180) - 90
            A.text(q[0], q[1], lb['text'], SZ[k], '60_部屋名・面積', rot=rot - math.degrees(ph) if False else 0, color='0.45' if k == 'context' else 'k')
        else:
            A.text(q[0], q[1], lb['text'], SZ[k], '60_部屋名・面積', color='0.45' if k == 'context' else 'k')
    # 建物の名前
    for txt, u_, v_ in (('本館', 28000, 7000), ('西館', 36000, -7000)):
        q = at(205000 - v_, theta_u(u_)); A.text(q[0], q[1], txt, 10, '60_部屋名・面積', box=True)
    # 表題・注・方位・縮尺（紙の座標）
    def paper(x_mm, y_mm): return ext[0] + (x_mm - MG) * SC, ext[2] + (y_mm - MG) * SC
    tx, ty = paper(16, H_ - 16)
    A.text(tx, ty, '配置図　1/200', 11, '80_図名・縮尺・方位', ha='left', va='top', raw=True)
    lines_ = list(SP.get('counts', [])) + [''] + list(SP.get('notes', []))
    for i, t in enumerate(lines_):
        x_, y_ = paper(16, H_ - 26 - i * 4.2)
        A.text(x_, y_, t, 5.5, '80_図名・縮尺・方位', ha='left', va='top', raw=True)
    A.dxf_only_text = False                         # 縮尺と方位の字だけは図に
    bx, by = paper(16, 18)
    for i in range(5):
        A.ax.add_patch(plt.Rectangle((bx + i * 2000, by), 2000, 300, fc='k' if i % 2 == 0 else 'white', ec='k', lw=LW(0.1), zorder=12))
    A.text(bx, by + 1000, '0', 5, '80_図名・縮尺・方位', raw=True); A.text(bx + 10000, by + 1000, '10 m', 5, '80_図名・縮尺・方位', raw=True)
    nd = np.array([-math.sin(ph), math.cos(ph)]); pd = np.array([-nd[1], nd[0]])
    c0 = np.array(paper(30, 45))
    A.lines([[c0 - nd * 3000, c0 + nd * 3000]], '80_図名・縮尺・方位', lw=0.25, raw=True)
    A.lines([[c0 + nd * 2000 + pd * 600, c0 + nd * 3000, c0 + nd * 2000 - pd * 600]], '80_図名・縮尺・方位', lw=0.25, raw=True)
    q = c0 + nd * 4000; A.text(q[0], q[1], 'N', 8, '80_図名・縮尺・方位', raw=True)
    # プレゼンの準備のための書き出し（renkei 20261026-0139-present）：線と色に分けた地の透明なPDFと、3dmのxy（m）→紙のmm（左上が原点）
    def after(base):
        from matplotlib.collections import LineCollection as _LC
        from matplotlib.patches import Patch as _P
        arts = [a for a in A.ax.get_children()]
        lines_ = [a for a in arts if isinstance(a, _LC) or a.__class__.__name__ == 'Line2D'] + list(S.fig.patches)
        fills_ = [a for a in arts if isinstance(a, _P) and a is not A.ax.patch]
        texts_ = [a for a in arts if a.__class__.__name__ == 'Text'] + list(S.fig.texts)
        def save_with(show, suffix):
            st = {a: a.get_visible() for a in lines_ + fills_ + texts_}
            for a in lines_ + fills_ + texts_: a.set_visible(a in show)
            S.fig.savefig(os.path.join(PDFD, os.path.basename(base) + suffix + '.pdf'), transparent=True)
            for a, v in st.items(): a.set_visible(v)
        save_with(set(lines_), '_線'); save_with(set(fills_), '_色')
        xf = {'_': '3dm の xy（m）→ この配置図の紙の mm（左上が原点、右へ x、下へ y）。x_mm = a·x + b·y + c、y_mm = d·x + e·y + f。'
                   ' 線と色の PDF（…_線.pdf・…_色.pdf）と元の PDF は同じ大きさ・同じ位置。地は透明、文字は入れていない（更新係、10-26）',
              'paper_mm': [W_, H_], 'scale': SC, 'rotate_deg': math.degrees(ph),
              'a': c_ * 1000 / SC, 'b': -n_ * 1000 / SC, 'c': MG - ext[0] / SC,
              'd': -n_ * 1000 / SC, 'e': -c_ * 1000 / SC, 'f': H_ - MG + ext[2] / SC}
        import json as _jj
        _jj.dump(xf, open(os.path.join(PDFD, os.path.basename(base) + '_xform.json'), 'w'), ensure_ascii=False, indent=1)
    S.after_save = after
    return S

ONLY = os.environ.get('DRAW_ONLY', '')
for name, mk in (('sodachiya_plan_1-100', make_plans), ('sodachiya_siteplan_1-200', make_siteplan), ('sodachiya_sections_1-100', make_sections), ('sodachiya_sections2_1-100', make_sections2),
                 *ELEV_SHEETS):
    if ONLY and ONLY not in name: continue
    S = mk(); S.save(os.path.join(OUTD, name))
    if hasattr(S, 'after_save'): S.after_save(os.path.join(OUTD, name))
    print('written', name)
