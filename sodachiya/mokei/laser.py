"""育ち舎 1/100 模型：レーザーカッター用のデータを 3dm から作る（模型作成のチャット）。

入力：model/sodachiya_exact_mesh.3dm、data/mokei.json
出力：mokei/cut/*.svg と *.dxf（Illustrator で開く。1 単位 = 1 mm、実寸）
色：赤 #FF0000 = 切る、青 #0000FF = 彫る（線）、黒 = 参考（切らない、レーザーに送る前に消す）

  python3 sodachiya/mokei/laser.py
"""
import json, math, os, sys
import numpy as np
import rhino3dm as r
from shapely.geometry import Polygon, MultiPolygon, box, Point
from shapely.ops import unary_union
from shapely import affinity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M3 = os.path.join(ROOT, 'model', 'sodachiya_exact_mesh.3dm')
OUT = os.path.join(ROOT, 'mokei', 'cut')
CX, CY = 194662.93237, -41348.26335      # 本館の弧の中心（uv.py と同じ）
S = 0.01                                  # 1/100：実寸 mm → 模型 mm
GL = -300.0                               # 3dm は z=0 が FL、GL は −300

J = json.load(open(os.path.join(ROOT, 'data', 'mokei.json')))
COL_T = J['柱']['厚さ']                    # 1.6（0.8×2）
TENON_W = J['柱']['ほぞ']['幅']            # 2.4
TENON_L = 5.5                             # ベタ基礎 3＋中の層 3 より短く
FLOOR_CLR = J['床']['柱の穴のあき']         # 0.1
KETA = (2.0, 4.0)                         # 平竹ひご 2×4
# 描く穴の寸法（短辺×長辺）。ひごの実測 10-23：短辺 1.97〜1.99（節で 2.03〜2.05）、長辺 約 3.90。
# レーザーの切り幅（約 0.1〜0.2）で、切れた穴はこれより大きくなる。
KETA_VARIANTS = {k: tuple(v) for k, v in zip('ABCD', J['桁']['穴_試し'])}   # 描く寸法（切り幅 0.2 で実寸は +0.2）
FLOOR_T = 1.60                             # 床の柱の穴の幅（柱の厚さ方向、試し切りで決める）
MORTISE_T = 1.64                          # ほぞ穴の幅（柱の厚さ方向、試し切りで決める）
MORTISE_W = TENON_W - 0.3     # 2.1：切り幅 0.2 でほぞ（実寸 2.2）に対して穴は 2.3
FLOOR_L = 3.9                 # 床の柱の穴の長さ：柱の幅 4.0 は実寸 3.8、穴は実寸 約 4.1（10-26 試し：つなぎの出っ張りで引っかかった）

m = r.File3dm.Read(M3)
LAY = {l.Name: i for i, l in enumerate(m.Layers)}
def objs(name):
    return [o.Geometry for o in m.Objects if o.Attributes.LayerIndex == LAY[name]]

def objs_named(name):
    return [(o.Attributes.Name or '', o.Geometry) for o in m.Objects if o.Attributes.LayerIndex == LAY[name]]

# ---------- 形を読む ----------
def sample_curve(c, n=240):
    d = c.Domain
    return [c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]

def profile_rz(g, k):
    """押し出しの断面（柱・梁の立面）を (r, z) の点列で"""
    c = g.Profile3d(k, 0)
    segs = [c.SegmentCurve(i) for i in range(c.SegmentCount)] if isinstance(c, r.PolyCurve) else [c]
    pts = []
    for s in segs:
        n = 2 if isinstance(s, r.LineCurve) else (60 if len(segs) > 1 else 720)   # 1 本の曲線の断面は細かく（西館の梁の丸い頭、10-26）
        for p in sample_curve(s, n)[:-1]:
            pts.append((math.hypot(p.X - CX, p.Y - CY), p.Z))
    return np.array(pts)

def plan(name):
    polys = []
    for g in objs(name):
        if not isinstance(g, r.Mesh):
            continue
        V, F = g.Vertices, g.Faces
        P = np.array([[V[i].X, V[i].Y] for i in range(len(V))])
        for fi in range(len(F)):
            f = F[fi]
            idx = [f[0], f[1], f[2]] if f[2] == f[3] else [f[0], f[1], f[2], f[3]]
            pg = Polygon(P[idx])
            if pg.area > 1:
                polys.append(pg.buffer(1))
    u = unary_union(polys).buffer(-1)
    return clean(u)

def clean(u, min_area=0.5e6):
    gs = [g for g in getattr(u, 'geoms', [u]) if g.area >= min_area]
    return unary_union(gs).simplify(5)

# ---------- 架構（20 本とも同じ形） ----------
class _Pt:
    def __init__(self, x, y): self.X, self.Y, self.Z = x, y, 0.0

class MeshCol:
    """メッシュになった柱（10-23 から西の柱）を、押し出しと同じように扱うための包み"""
    def __init__(self, g):
        V, F = g.Vertices, g.Faces
        P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
        th = np.arctan2(P[:, 1] - CY, P[:, 0] - CX); ac = th.mean()
        et = np.array([-math.sin(ac), math.cos(ac)])
        # 側面だけのメッシュ（ふたが無い）：各面の手前側（接線方向の +側）の辺が、立面の輪郭の線分になる
        from shapely.ops import polygonize, linemerge
        from shapely.geometry import LineString, MultiLineString
        tt = (P[:, :2] - [CX, CY]) @ et; tmax = tt.max()
        segs = set()
        for fi in range(len(F)):
            f = F[fi]; idx = list(dict.fromkeys([f[0], f[1], f[2], f[3]]))
            fr = [i for i in idx if abs(tt[i] - tmax) < 2]
            if len(fr) == 2:
                p, q = [(round(math.hypot(P[i, 0] - CX, P[i, 1] - CY), 1), round(P[i, 2], 1)) for i in fr]
                if p != q: segs.add(tuple(sorted((p, q))))
        polys = list(polygonize(MultiLineString([list(sg) for sg in segs])))
        polys.sort(key=lambda x: -x.area)
        u = polys[0]
        if not u.interiors:
            hole = next(pg for pg in polys[1:] if Polygon(u.exterior).contains(pg.centroid))
            u = u.difference(hole)
        self.outer = np.array(u.exterior.coords)[:-1]
        self.hole = np.array(max(u.interiors, key=lambda i: Polygon(i).area).coords)[:-1]
        self.PathStart = _Pt(*P[tt.argmin(), :2]); self.PathEnd = _Pt(*P[tt.argmax(), :2])
        self.ProfileCount = 2

_profile_rz = profile_rz
def profile_rz(g, k):
    if isinstance(g, MeshCol):
        return g.outer if k == 0 else g.hole
    return _profile_rz(g, k)

cols = [g if isinstance(g, r.Extrusion) else MeshCol(g) for g in objs('11a_本館_柱')]
beams = [g for g in objs('11b_本館_梁') if isinstance(g, r.Extrusion)]
col_e = next(g for g in cols if profile_rz(g, 0)[:, 0].max() < 194000)
col_w = next(g for g in cols if profile_rz(g, 0)[:, 0].max() > 204000)
beam = beams[0]

def hole_center(g, k):
    H = profile_rz(g, k)
    return ((H[:, 0].min() + H[:, 0].max()) / 2, (H[:, 1].min() + H[:, 1].max()) / 2)

R0 = 190000.0   # 庇の先（模型の x=0）
def to_model(P):
    return np.column_stack(((P[:, 0] - R0) * S, (P[:, 1] - GL) * S))

def stadium(cx, cy, w, h):
    """縦長の長円（平竹ひごの穴）"""
    rr = w / 2
    return unary_union([box(cx - rr, cy - h / 2 + rr, cx + rr, cy + h / 2 - rr),
                     Point(cx, cy - h / 2 + rr).buffer(rr, 32),
                     Point(cx, cy + h / 2 - rr).buffer(rr, 32)])

def column_part(g, clr):
    P = to_model(profile_rz(g, 0))
    poly = Polygon(P).buffer(0)
    xmin, xmax = P[:, 0].min(), P[:, 0].max()
    foot = [x for x, y in P if y < (1500 - GL) * S]                # 柱の下の方の幅（足元の小さな面取りは無視）
    x0, x1 = min(foot), max(foot)
    poly = unary_union([poly, box(x0, (0 - GL) * S, x1, (1500 - GL) * S)])
    # FL から GL まで延ばす（肩が GL に乗る）、その下にほぞ
    ext = box(x0, 0, x1, (0 - GL) * S + 0.01)
    xc = (x0 + x1) / 2
    ten = box(xc - TENON_W / 2, -TENON_L, xc + TENON_W / 2, 0.01)
    part = unary_union([poly, ext, ten])
    hc = to_model(np.array([hole_center(g, 1)]))[0]
    part = part.difference(stadium(hc[0], hc[1], clr[0], clr[1]))
    return part, hc

def beam_part(clr, centers):
    P = to_model(profile_rz(beam, 0))
    part = Polygon(P).buffer(0)
    for hc in centers:
        part = part.difference(stadium(hc[0], hc[1], clr[0], clr[1]))
    return part

# ---------- 書き出し ----------
# 切った部品（ユーザー 10-28：本館の切った部品は変えない）。この SVG は書き出さない（設計が変わっても作り直さない）
CUT_DONE = ('01_', '02_', '03a_', '03b_', '04_', '05_', '05b_', '06a_', '06b_')
WRITE_DXF = os.environ.get('DXF') == '1'   # 10-26 ユーザー：SVG で切れるので DXF は作らない（要るときは DXF=1）

class Sheet:
    def __init__(self, name, w, h, note):
        self.name, self.w, self.h, self.note = name, w, h, note
        self.cut, self.eng, self.ref = [], [], []
        self.tab_pts = []      # つなぎの位置を指定する点（外形の近くの点。無い部品は周の 1/4・3/4）
        # レイヤー：(名前, SVG の色, DXF の色番号, 説明)。出力の試しでは切る線の色を増やす
        self.layers = [('ref', '#000000', 7, 'REF_delete', '参考（切らない・送る前に消す）'),
                       ('eng', '#0000FF', 5, 'ENGRAVE_blue', '彫る（青）'),
                       ('cut', '#FF0000', 1, 'CUT_red', '切る（赤）')]
    def add_layer(self, key, col, aci, dxfname, label):
        setattr(self, key, [])
        self.layers.append((key, col, aci, dxfname, label))
    def add(self, geom, layer='cut'):
        getattr(self, layer).append(geom)
    def rings(self, geom):
        out = []
        for g in getattr(geom, 'geoms', [geom]):
            if g.geom_type == 'Polygon':
                out.append(np.array(g.exterior.coords))
                out += [np.array(i.coords) for i in g.interiors]
            elif g.geom_type in ('LineString', 'LinearRing'):
                out.append(np.array(g.coords))
            elif g.geom_type == 'MultiLineString':
                out += [np.array(x.coords) for x in g.geoms]
        return out
    TAB_GAP = 0.5      # つなぎ（タブ）：描く切り残しの長さ。切り幅 0.2 で、残る木は約 0.3（シナ 1.7・3）
    TAB_MAX = 250      # これより小さい部品の外形に 2 か所のつなぎ（大きい板は付けない）
    def tab_gap(self):
        # 航空ベニヤ 0.8 は弱く（10-26 ユーザー：もう少し弱く）：切り残し 0.35 → 残る木 約 0.15
        return 0.35 if self.name.startswith(('01_試し切り_T1', '02_', '03', '07_')) else self.TAB_GAP
    def tabbed(self, geoms):
        """小さい部品が飛ばないように、外形に 2 か所の切り残し（周の 1/4 と 3/4、直線の所）を入れる。穴には付けない"""
        from shapely.geometry import LineString
        from shapely.ops import substring
        out = []
        for g in geoms:
            for p in getattr(g, 'geoms', [g]):
                if p.geom_type != 'Polygon' or not getattr(self, 'tabs', True):
                    out.append(p); continue
                b = p.bounds
                if max(b[2] - b[0], b[3] - b[1]) > self.TAB_MAX or p.exterior.length < 12:
                    out.append(p); continue
                ext = LineString(p.exterior.coords); Lx = ext.length; h = self.tab_gap() / 2
                mine = [q for q in self.tab_pts if ext.distance(q) < 0.6]
                cuts = sorted([ext.project(q) for q in mine]) if len(mine) >= 2 else sorted([Lx * 0.25, Lx * 0.75])
                cuts = [min(max(c, h + 0.01), Lx - h - 0.01) for c in cuts[:2]]
                segs = [substring(ext, cuts[0] + h, cuts[1] - h), substring(ext, cuts[1] + h, Lx), substring(ext, 0, cuts[0] - h)]
                out += segs
                out += [LineString(i.coords) for i in p.interiors]
        return out

    MARGIN = 3.0   # 10-26 ユーザー：どのデータも左上を原点に。切る・彫る線の左上を板の左上から 3 mm に寄せる
    def to_top_left(self, texts):
        from shapely.ops import unary_union as _uu
        keys = [k for k, *_ in self.layers if k != 'ref' and getattr(self, k)]
        allg = [g for k in keys for g in getattr(self, k)]
        if not allg: return texts
        b = _uu([g.envelope if g.geom_type != 'Point' else g for g in allg]).bounds
        dx, dy = self.MARGIN - b[0], (self.h - self.MARGIN) - b[3]
        for k in keys:
            setattr(self, k, [affinity.translate(g, dx, dy) for g in getattr(self, k)])
        self.tab_pts = [affinity.translate(q, dx, dy) for q in self.tab_pts]
        return [(x + dx, y + dy, t, sz) for x, y, t, sz in texts]

    def save(self, texts=()):
        if self.name.startswith(CUT_DONE):
            print('  切った部品なので書き出さない：', self.name); return
        texts = self.to_top_left(list(texts))
        os.makedirs(OUT, exist_ok=True)
        # SVG（mm、y は下向きに反転）
        H = self.h
        def path(a):
            return 'M' + ' L'.join(f'{x:.3f},{H - y:.3f}' for x, y in a)
        L = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" viewBox="0 0 {self.w} {self.h}">']
        L.append(f'<!-- {self.note} -->')
        for lay, col, _, _, name in self.layers:
            if not getattr(self, lay): continue
            L.append(f'<g id="{name}" fill="none" stroke="{col}" stroke-width="0.01">')
            for g in (self.tabbed(getattr(self, lay)) if lay.startswith('cut') else getattr(self, lay)):
                for a in self.rings(g):
                    closed = len(a) > 2 and np.allclose(a[0], a[-1])
                    L.append(f'<path d="{path(a)}{" Z" if closed else ""}"/>')
            L.append('</g>')
        L.append('<g id="参考の文字（送る前に消す）" fill="#000000" stroke="none" font-family="sans-serif">')
        for x, y, t, sz in texts:
            L.append(f'<text x="{x:.2f}" y="{H - y:.2f}" font-size="{sz}">{t}</text>')
        L.append('</g></svg>')
        open(os.path.join(OUT, self.name + '.svg'), 'w').write('\n'.join(L))
        if not WRITE_DXF: return
        try:
            import ezdxf
            doc = ezdxf.new(units=4)
            for lay, col, ci, ln, _ in self.layers:
                L_ = doc.layers.add(ln, color=ci)
                if col not in ('#000000',): L_.rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
            msp = doc.modelspace()
            for lay, col, ci, ln, _ in self.layers:
                for g in (self.tabbed(getattr(self, lay)) if lay.startswith('cut') else getattr(self, lay)):
                    for a in self.rings(g):
                        e = msp.add_lwpolyline([tuple(p) for p in a], dxfattribs={'layer': ln})
                        if col != '#000000': e.rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
            for x, y, t, sz in texts:
                msp.add_text(t, dxfattribs={'layer': 'REF_delete', 'height': sz}).set_placement((x, y))
            doc.saveas(os.path.join(OUT, self.name + '.dxf'))
        except ImportError:
            pass

def place(geom, x, y):
    b = geom.bounds
    return affinity.translate(geom, x - b[0], y - b[1])

def label_num(n, x, y, h=1.6):
    """彫る数字（試し切りの番号）：線の 7 セグメント"""
    segs = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg',
            'A': 'efabcg', 'B': 'fedcg', 'C': 'afed', 'D': 'bcdeg'}
    w = h * 0.55
    P = {'a': ((0, h), (w, h)), 'b': ((w, h), (w, h / 2)), 'c': ((w, h / 2), (w, 0)), 'd': ((0, 0), (w, 0)),
         'e': ((0, 0), (0, h / 2)), 'f': ((0, h / 2), (0, h)), 'g': ((0, h / 2), (w, h / 2))}
    from shapely.geometry import LineString
    return [LineString([(x + p[0], y + p[1]) for p in P[s]]) for s in segs[str(n)]]

# ================= 1. 試し切り =================
# 出力を 3 段（弱・中・強）で試す。段ごとに切る線の色を変え（1＝赤、2＝橙、3＝紫）、
# 同じ中身を 3 つ並べる。各組の左上に段の番号を彫る。レーザーのソフトで色ごとに出力を割り当てる。
TRY = J['レーザーの試し']

def _levels(s):
    for k, col in TRY['色'].items():
        if k == '1': continue
        s.add_layer(f'cut{k}', col, {'2': 30, '3': 6}[k], f'CUT_{k}', f'切る・出力{k}')
    return {'1': 'cut', '2': 'cut2', '3': 'cut3'}

def _try_sheet(name, w1, h1, note, build, mat, texts1):
    """build(s, ox, oy, layer)：1 組を (ox, oy) に描く。3 組を縦に並べる"""
    gap = 4
    s = Sheet(name, w1, 3 * h1 + 2 * gap, note)
    lay = _levels(s)
    texts = []
    for i, k in enumerate(('1', '2', '3')):
        oy = (2 - i) * (h1 + gap)
        build(s, 0, oy, lay[k])
        for l in label_num(k, 1.2, oy + h1 - 3.0, 2.0): s.add(l, 'eng')
        if w1 == 82:                                                 # 20 mm 角にも段の番号（飛んでもわかるように）
            for l in label_num(k, 63.5, oy + h1 - 3.5, 2.0): s.add(l, 'eng')
        if mat == '彫り':
            pw = TRY['彫り']['出力'][i]; sp = TRY['彫り']['速度']
        else:
            pw = TRY[mat]['出力'][i]; sp = TRY[mat]['速度']
        texts.append((w1 + 1, oy + h1 / 2, f'{k}：速度 {sp} mm/s・出力 {pw}%', 2))
    for t in texts1: texts.append(t)
    s.w = w1 + 45
    s.save(texts)

def test_sheets():
    from shapely.geometry import LineString
    # T1b：航空ベニヤ 0.8、桁の穴だけ（10-26：切り幅 0.2 を受けて小さく描き直した）。出力は 13% の 1 段
    s = Sheet('01_試し切り_T1b_桁の穴_航空ベニヤ0.8', 50, 22, '航空ベニヤ 0.8：桁の穴 A〜D（描いた寸法、実寸は約 +0.2）。速度 40・出力 13%')
    s.add(box(0, 0, 50, 22), 'ref')
    for i, (k, c) in enumerate(KETA_VARIANTS.items()):
        x = 6 + i * 11
        s.add(box(x - 4, 2, x + 5, 20))
        s.add(stadium(x + 0.5, 12, c[0], c[1]))
        for l in label_num(k, x - 0.5, 3.5): s.add(l, 'eng')
    s.save([(51, 18, 'A 1.80×3.70（実寸約 2.00×3.90）', 1.6), (51, 14, 'B 1.85×3.75（約 2.05×3.95）', 1.6),
            (51, 10, 'C 1.90×3.80（約 2.10×4.00）', 1.6), (51, 6, 'D 1.95×3.85（約 2.15×4.05）', 1.6)])
    # T2：シナ 3（ほぞ穴 4 種）
    def t2(s, ox, oy, lay):
        s.add(box(ox, oy, ox + 60, oy + 20), lay)
        s.add(box(ox + 62, oy, ox + 82, oy + 20), lay)               # 20 mm 角（切り幅）
        for i, t in enumerate(J['柱']['ほぞ穴の幅_試し']):
            x = ox + 8 + i * 13
            s.add(box(x, oy + 8, x + MORTISE_W, oy + 8 + t), lay)
            for l in label_num(i + 1, x + 0.4, oy + 3): s.add(l, 'eng')
    _try_sheet('01_試し切り_T2_シナ3', 82, 20, 'シナ 3 mm：出力 3 段 × ほぞ穴 1〜4（描いた幅 1.50／1.57／1.64／1.71 × 2.10）と 20 mm 角',
               t2, 'シナ3', [])
    # T3：シナ 1.7（床の柱の穴 4 種）
    def t3(s, ox, oy, lay):
        s.add(box(ox, oy, ox + 60, oy + 20), lay)
        s.add(box(ox + 62, oy, ox + 82, oy + 20), lay)               # 20 mm 角（切り幅）
        for i, t in enumerate(J['床']['柱の穴_試し']):
            x = ox + 8 + i * 13
            s.add(box(x, oy + 8, x + FLOOR_L, oy + 8 + t), lay)
            for l in label_num(i + 1, x + 1, oy + 3): s.add(l, 'eng')
    _try_sheet('01_試し切り_T3_シナ1.7', 82, 20, 'シナ 1.7 mm：出力 3 段 × 床の柱の穴 1〜4（描いた寸法 3.8 × 1.60／1.67／1.74／1.81）と 20 mm 角',
               t3, 'シナ1.7', [])
    # T5・T6：航空ベニヤ 0.6・1.0（10-27：室内の壁・外壁の前に）。20 mm 角と大和張りの彫りの線
    from shapely.geometry import LineString as _LS
    for nm, mat in (('01_試し切り_T5_航空ベニヤ0.6', '航空ベニヤ0.6'), ('01_試し切り_T6_航空ベニヤ1.0', '航空ベニヤ1.0')):
        def tt(s, ox, oy, lay):
            s.add(box(ox + 6, oy, ox + 26, oy + 20), lay)
            for k in range(8):
                s.add(_LS([(ox + 30 + k * 1.05, oy + 2), (ox + 30 + k * 1.05, oy + 18)]), 'eng')
            s.add(box(ox + 28, oy, ox + 40, oy + 20), lay)
        _try_sheet(nm, 40, 20, f'{mat}：出力 3 段 × 20 mm 角と、彫りの線（大和張り 1.05 間隔）の小片', tt, mat, [])
    # T4：彫りの試し（谷積みの目地、畑の線、点）。彫りの出力を 3 段に：彫る線の色を段ごとに変える
    s = Sheet('01_試し切り_T4_彫り', 115, 98, 'KROMA 1 か シナ：彫りの出力 3 段 × （谷積みの目地 45°、畑の平行線、点）')
    s.add_layer('eng2', '#00A0FF', 4, 'ENGRAVE_2', '彫る・出力2')
    s.add_layer('eng3', '#00C000', 3, 'ENGRAVE_3', '彫る・出力3')
    texts = []
    for i, (k, lay) in enumerate((('1', 'eng'), ('2', 'eng2'), ('3', 'eng3'))):
        oy = (2 - i) * 34
        s.add(box(0, oy, 70, oy + 30), 'cut')
        q = box(3, oy + 3, 27, oy + 27); lines = []
        for kk in np.arange(-30, 60, 3.5):                       # 45° の格子（石 約 35 cm）
            lines += [LineString([(kk, oy), (kk + 40, oy + 40)]), LineString([(kk + 40, oy), (kk, oy + 40)])]
        for ln in lines:
            g = ln.intersection(q)
            if not g.is_empty: s.add(g, lay)
        for kk in np.arange(31, 47, 0.6):                        # 畑の畝 60 cm
            s.add(LineString([(kk, oy + 5), (kk, oy + 25)]), lay)
        for xx in np.arange(50, 67, 1.2):                        # 砂場の点
            for yy in np.arange(oy + 5, oy + 25, 1.2):
                s.add(LineString([(xx, yy), (xx + 0.15, yy)]), lay)
        for l in label_num(k, 0.6, oy + 26.5, 2.0): s.add(l, lay)
        texts.append((71, oy + 15, f'{k}：速度 {TRY["彫り"]["速度"]}・出力 {TRY["彫り"]["出力"][i]}%', 2))
    texts.append((71, 2, '左：谷積み 中：畑 右：点。外形（赤）は切る出力で', 1.6))
    s.save(texts)

# ================= 2・3. 架構 =================
def frame_parts(clr):
    ce, hce = column_part(col_e, clr)
    cw, hcw = column_part(col_w, clr)
    bm = beam_part(clr, [hce, hcw])
    return ce, cw, bm

def frame_sheets():
    k = J['桁']['選んだ穴']['名']                     # 10-26 試し切りで D に決めた。ほかの穴の版は作らない
    for k, c in [(k, KETA_VARIANTS[k])]:
        ce, cw, bm = frame_parts(c)
        # 試作 1 本（梁 2、東の柱 2 枚、西の柱 2 枚）
        s = Sheet(f'02_架構の試作1本_桁穴{k}', 185, 52, f'航空ベニヤ 0.8：本館の架構 1 本分（桁の穴 {k}）')
        s.add(box(0, 0, 185, 52), 'ref')
        s.add(place(bm, 3, 2)); s.add(place(bm, 3, 22))
        for part, xx in zip([ce, ce, cw, cw], [159, 166, 173, 180]):
            s.add(place(part, xx - 2.5, 2))
        s.save([(3, 48, f'架構の試作 1 本：梁×2、東の柱×2 枚、西の柱×2 枚　桁の穴 {k}', 2)])
        # 梁 45 本（20 本分 40＋予備 5）：3 列 × 15 段
        s = Sheet(f'03a_架構_梁45本_桁穴{k}', 590, 295, f'航空ベニヤ 0.8 300×600 1 枚：本館の梁 45 本（20 本分＋予備）桁の穴 {k}')
        s.add(box(0, 0, 590, 295), 'ref')
        bb = bm.bounds; bw = bb[2] - bb[0]
        for row in range(15):
            for col in range(3):
                s.add(place(bm, 4 + col * (bw + 4), 4 + row * 19))
        s.save([(480, 290, f'梁 45　桁の穴 {k}', 3)])
        # 柱 東 44 枚・西 44 枚（20 本分 40＋予備 4）
        s = Sheet(f'03b_架構_柱88枚_桁穴{k}', 340, 100, f'航空ベニヤ 0.8：本館の柱 東 44 枚・西 44 枚（2 枚ずつ貼って 1 本）桁の穴 {k}')
        s.add(box(0, 0, 340, 100), 'ref')
        for i in range(44):
            s.add(place(ce, 4 + i * 7.5, 4))
            s.add(place(cw, 4 + i * 7.5, 47))
        s.save([(4, 97, f'下の段：東の柱 44 枚／上の段：西の柱 44 枚　桁の穴 {k}', 2.5)])


# ================= 4・5. 本館の床（1.7×2）とベタ基礎（3） =================
RCLIP = (189000.0, 205360.0)        # 本館だけ（西館は別の部品）

def annulus():
    th = np.linspace(-math.pi, math.pi, 4000)
    outer = Polygon(np.column_stack((CX + RCLIP[1] * np.cos(th), CY + RCLIP[1] * np.sin(th))))
    inner = Polygon(np.column_stack((CX + RCLIP[0] * np.cos(th), CY + RCLIP[0] * np.sin(th))))
    return outer.difference(inner)

def col_rect(g, rad_w, tan_w):
    """柱の位置に、半径方向 rad_w × 接線方向 tan_w（模型 mm）の穴（世界座標 mm で返す）"""
    P = profile_rz(g, 0)
    foot = P[P[:, 1] < 1]
    rc = (foot[:, 0].min() + foot[:, 0].max()) / 2
    a0 = math.atan2(g.PathStart.Y - CY, g.PathStart.X - CX)
    a1 = math.atan2(g.PathEnd.Y - CY, g.PathEnd.X - CX)
    ac = (a0 + a1) / 2
    hr, ht = rad_w / S / 2, tan_w / S / 2
    er = np.array([math.cos(ac), math.sin(ac)]); et = np.array([-math.sin(ac), math.cos(ac)])
    c = np.array([CX, CY]) + rc * er
    return Polygon([c - hr * er - ht * et, c + hr * er - ht * et, c + hr * er + ht * et, c - hr * er + ht * et])

def floors():
    A = annulus()
    hadashi = unary_union([plan('12_本館_床（はだし ±0）'), plan('13_本館_内縁側（はだし ±0）')]).intersection(A)
    dosoku = unary_union([plan('14_本館_外縁側（土足 −150）'), plan('15_本館_あまのがわ（土足 −150）')]).intersection(A)
    doma = plan('52_1F_受け取り土間').intersection(A)
    close = lambda g: g.buffer(120, join_style=2).buffer(-120, join_style=2)   # ガラス戸の下などの細いすき間を閉じる
    hadashi = close(hadashi).intersection(A)
    upper = clean(hadashi, 1e5)
    lower = clean(close(unary_union([hadashi, dosoku])).intersection(A), 1e5)
    found = clean(unary_union([hadashi, dosoku, doma]).buffer(30).buffer(-30), 1e5)
    col_hole = [col_rect(g, FLOOR_L, FLOOR_T) for g in cols]
    mortise = [col_rect(g, MORTISE_W, MORTISE_T) for g in cols]
    opn = lambda g: g.buffer(-25, join_style=2).buffer(25, join_style=2)       # 細いひげを取る
    upper, lower, found = opn(upper), opn(lower), opn(found)
    upper = upper.difference(unary_union(col_hole))
    lower = lower.difference(unary_union(col_hole))
    found = found.difference(unary_union(mortise))
    return upper, lower, found

def to_sheet(g, ang, org):
    g = affinity.scale(g, S, S, origin=(0, 0))
    g = affinity.rotate(g, ang, origin=(0, 0), use_radians=True)
    return affinity.translate(g, -org[0], -org[1])

def floor_sheets():
    upper, lower, found = floors()
    # 架構 1 と 20 の西の柱を結ぶ線を水平に
    ws = sorted([g for g in cols if profile_rz(g, 0)[:, 0].max() > 204000],
                key=lambda g: math.atan2(g.PathStart.Y - CY, g.PathStart.X - CX))
    p0 = np.array([ws[0].PathStart.X, ws[0].PathStart.Y]); p1 = np.array([ws[-1].PathStart.X, ws[-1].PathStart.Y])
    ang = -math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    def norm(g):
        g = to_sheet(g, ang, (0, 0)); b = found_s.bounds
        return affinity.translate(g, -b[0], -b[1])
    found_s = to_sheet(found, ang, (0, 0))
    U, Lw, F = norm(upper), norm(lower), norm(found)
    b = F.bounds; w, h = b[2], b[3]
    s = Sheet('04_本館の床_シナ1.7', 841, 594, 'シナ 1.7 A1：本館の床 上の層（はだし）と下の層（はだし＋土足）。柱の穴 3.9×1.60（実寸 約 4.1×1.80）')
    s.add(box(0, 0, 841, 594), 'ref')
    s.add(affinity.translate(U, 8, 8))
    s.add(affinity.translate(Lw, 8, 8 + h + 8))
    s.save([(8, 8 + 2 * (h + 8) + 4, '下：上の層（はだし ±0）　上：下の層（はだし＋外縁側・あまのがわ）　受け取り土間は 2 枚とも無し', 4),
            (8, 8 + 2 * (h + 8) + 10, f'3 段目の空きは西館の床などに使う（屋根は 06）', 4)])
    s = Sheet('05_本館のベタ基礎_シナ3', 841, 594, 'シナ 3 A1：本館のベタ基礎（床の外形＋受け取り土間）。ほぞ穴 2.1×1.64（実寸 約 2.3×1.86）')
    s.add(box(0, 0, 841, 594), 'ref')
    s.add(affinity.translate(F, 8, 8))
    s.save([(8, h + 16, f'本館のベタ基礎（{w:.0f}×{h:.0f} mm）。残りは敷地・西館のベタ基礎に使う', 4)])
    return w, h

# ================= 5b. ベタ基礎の継ぎ足し（南北の妻の柱） =================
def found_ext_sheets():
    """10-26：南北の妻の架構（1・20）の柱は、ベタ基礎の縁にまたがり、ほぞ穴が外へ切れて溝になる。
    外側の半分を受ける小さな板（シナ 3）を作り、ベタ基礎の縁に木工用ボンドで貼る。建物ごと外せるまま"""
    upper, lower, found = floors()
    from shapely.geometry import Polygon as _P
    outer = _P(found.exterior)
    ang = sheet_angle()
    pieces = []
    for g in cols:
        mo = col_rect(g, MORTISE_W, MORTISE_T)
        if outer.buffer(-1).contains(mo): continue
        blk = mo.buffer(260, join_style=2)                       # ほぞ穴のまわり 2.6 mm の板
        q = blk.difference(outer.buffer(-1)).difference(mo)     # ベタ基礎の外側の分だけ（縁に 0.01 重ねて当てる）
        q = q.difference(outer)
        if q.is_empty: continue
        q = max(getattr(q, 'geoms', [q]), key=lambda x: x.area)
        q = to_sheet(q, ang, (0, 0)); b = q.bounds
        pieces.append(affinity.translate(q, -b[0], -b[1]))
    s = Sheet('05b_ベタ基礎の継ぎ足し_シナ3', 60, 20, 'シナ 3：南北の妻の柱のほぞ穴の外半分（ベタ基礎の縁に貼る）')
    s.add(box(0, 0, 60, 20), 'ref')
    x = 0
    for q in pieces:
        s.add(affinity.translate(q, x, 0)); x += q.bounds[2] + 3
    s.save([(0, -3, f'{len(pieces)} 個：ほぞ穴の溝を外から閉じるように、ベタ基礎の縁に貼る', 2)])
    return len(pieces), [tuple(round(v, 1) for v in q.bounds[2:]) for q in pieces]

# ================= 6. 本館の屋根 =================
ROOF_GAP = 190      # 下の層の板の端：架構の中心線から（梁 2 枚の外面 180＋すき間 10、実寸 mm）。切り幅 0.1 で、すき間は片側 約 0.2
ROOF_R = (191.53e3, 203.37e3)   # 下の層の東西：縁側のガラス戸の線（191.5）から、一本の線（越屋根の東の立ち上がり、203.4）まで

def sheet_angle():
    ws = sorted([g for g in cols if profile_rz(g, 0)[:, 0].max() > 204000],
                key=lambda g: math.atan2(g.PathStart.Y - CY, g.PathStart.X - CX))
    p0 = np.array([ws[0].PathStart.X, ws[0].PathStart.Y]); p1 = np.array([ws[-1].PathStart.X, ws[-1].PathStart.Y])
    return -math.atan2(p1[1] - p0[1], p1[0] - p0[0])

def roof_parts():
    """上の層＝3dm の屋根（10）の平面（光の筋の穴 18 本つき、南の軒まで）。
    下の層＝室内の上だけ、スパンごとの板 19 枚（梁 2 枚のあいだに落とし込む。板のすき間が光の筋の下になる）"""
    up = plan('10_本館_屋根')
    slots = [Polygon(h) for h in up.interiors]
    a = sorted(math.atan2(sl.centroid.y - CY, sl.centroid.x - CX) % (2 * math.pi) for sl in slots)
    step = (a[-1] - a[0]) / (len(a) - 1)
    frames = [a[0] - step] + a + [a[-1] + step]          # 架構 1〜20 の中心線の角度（両端は妻）
    panels = []
    r1, r2 = ROOF_R
    for k in range(len(frames) - 1):
        rs = np.linspace(r1, r2, 40)
        def edge(t0, sgn):
            return [(CX + rr_ * math.cos(t0 + sgn * ROOF_GAP / rr_), CY + rr_ * math.sin(t0 + sgn * ROOF_GAP / rr_)) for rr_ in rs]
        e0 = edge(frames[k], +1); e1 = edge(frames[k + 1], -1)
        panels.append(Polygon(e0 + e1[::-1]))
    return up, panels

def roof_sheets():
    """10-26 ユーザー：床（04）の残りの帯（約 841×220）から上の層を取る → 上の層と下の層を別のファイルに"""
    up, panels = roof_parts()
    ang = sheet_angle()
    U = to_sheet(up, ang, (0, 0)); P = [to_sheet(p, ang, (0, 0)) for p in panels]
    b = U.bounds; U = affinity.translate(U, -b[0], -b[1]); P = [affinity.translate(p, -b[0], -b[1]) for p in P]
    h = U.bounds[3]
    s = Sheet('06a_本館の屋根_上の層_シナ1.7', 841, 220, 'シナ 1.7：本館の屋根 上の層（南の軒まで、光の筋の穴 18 本）。床（04）の残りの帯 841×220 から')
    s.add(box(0, 0, 841, 220), 'ref')
    s.add(U)
    s.save([(0, h + 3, '本館の屋根 上の層（南の軒まで、光の筋の穴 18 本）', 4)])
    pb = unary_union(P).bounds
    s = Sheet('06b_本館の屋根_下の層_シナ1.7', 841, 594, 'シナ 1.7：本館の屋根 下の層（スパン 1〜19 の板、梁 2 枚のあいだに落とし込む）')
    s.add(box(0, 0, 841, 594), 'ref')
    for i, p in enumerate(P):
        q = affinity.translate(p, 0, -pb[1])
        s.add(q)
        c = q.centroid                                   # スパンの番号を彫る（南から 1〜19、板の裏になる面に）
        txt = str(len(P) - i)                            # 角度の小さい方が北（左が南）
        for j, ch in enumerate(txt):
            for l in label_num(ch, c.x - len(txt) * 0.8 + j * 1.6, c.y - 0.8, 1.6): s.add(l, 'eng')
    s.save([(0, pb[3] - pb[1] + 3, '本館の屋根 下の層（スパン 1〜19、南から）。残りは西館の床に', 4)])
    return U.bounds, pb

# ================= 11. 西館の屋根（本館と同じ作り方、10-28） =================
def west_frame_lines():
    """西館の架構の線（平面、世界座標）：架構ごとに東の柱と西の柱の中心を結ぶ。返す：{架構の番号: (東の点, 西の点)}"""
    pts = {}
    for nm_, g in objs_named('22a_西館_柱'):
        if g.ProfileCount == 1: continue                   # 桁の穴の無い柱（キッチン・階段の箱）は架構の線にしない
        b = g.GetBoundingBox(); c = np.array([(b.Min.X + b.Max.X) / 2, (b.Min.Y + b.Max.Y) / 2])
        pts.setdefault(_frame_no(_ang(g)), []).append(c)
    out = {}
    for k, ps in pts.items():
        ps.sort(key=lambda c: math.hypot(c[0] - CX, c[1] - CY))
        out[k] = (ps[0], ps[-1])
    return out

def west_roof_parts():
    """上の層＝3dm の西館の屋根（20）の平面（光の筋の穴つき）。
    下の層＝室内の上だけ、架構のあいだの板（梁 2 枚のあいだに落とし込む）。板の端は架構の線（柱の中心を結ぶ線）から ROOF_GAP。
    室内＝西館の外壁（21）の内側（東の越屋根の下の帯は除く、本館の下の層が越屋根の立ち上がりまでなのと同じ）を 0.3 小さく。
    北西の角の登り梁（u43.5、120 角の幅）の所も板を分ける。北の妻の架構 17 の北は外壁まで"""
    from shapely.geometry import LineString
    up = plan('20_西館_屋根')
    wall = plan('21_西館_外壁')
    holes = [Polygon(h) for p in getattr(wall, 'geoms', [wall]) for h in p.interiors]
    room = max(holes, key=lambda q: q.area).buffer(-30, join_style=2)
    fl = west_frame_lines(); ks = sorted(fl)
    # 北は架構の番号の大きい方（角度の小さい方）。half(k, True)＝架構 k の線を北へ ROOF_GAP ずらした線より北
    def half(k, toward_north):
        e, w = fl[k]; d = (w - e) / np.linalg.norm(w - e); n = np.array([-d[1], d[0]])
        a0 = math.atan2(e[1] - CY, e[0] - CX); p = e + n * 100
        if (math.atan2(p[1] - CY, p[0] - CX) < a0) != toward_north: n = -n   # 北は角度が小さい
        c = e + n * ROOF_GAP; L_ = 1e5
        return Polygon([c - d * L_, c + d * L_, c + d * L_ + n * L_, c - d * L_ + n * L_])
    panels = []
    for i, k in enumerate(ks):
        reg = room.intersection(half(k, True))
        if i + 1 < len(ks): reg = reg.intersection(half(ks[i + 1], False))
        if reg.is_empty or reg.area < 1e5: continue
        panels.append((k, reg))
    # 北西の角の登り梁 u43.5：その線の両側 70（120 の半分＋すき間 10）を抜く
    for nm_, g in objs_named('22b_西館_梁'):
        if '登り梁' not in nm_: continue
        b = g.GetBoundingBox(); c = np.array([(b.Min.X + b.Max.X) / 2, (b.Min.Y + b.Max.Y) / 2])
        d = (c - [CX, CY]) / np.linalg.norm(c - [CX, CY])
        cut = LineString([np.array([CX, CY]) + d * 2.0e5, np.array([CX, CY]) + d * 2.3e5]).buffer(70, cap_style=2)
        new = []
        for k, reg in panels:
            q = reg.difference(cut)
            gs = sorted(getattr(q, 'geoms', [q]), key=lambda x: -x.area)
            if len(gs) > 1 and gs[1].area > 1e5:
                new += [(k, gs[0]), (k, gs[1])]
            else:
                new.append((k, gs[0]))
        panels = new
    return up, panels

def west_roof_sheets():
    up, panels = west_roof_parts()
    fl = west_frame_lines(); ks = sorted(fl)
    e0, e1 = fl[ks[0]][0], fl[ks[-1]][0]                     # 東の柱の列（架構 8 と 17）を水平に
    ang = -math.atan2(e1[1] - e0[1], e1[0] - e0[0])
    U = to_sheet(up, ang, (0, 0)); P = [(k, to_sheet(p, ang, (0, 0))) for k, p in panels]
    b = U.bounds; U = affinity.translate(U, -b[0], -b[1]); P = [(k, affinity.translate(p, -b[0], -b[1])) for k, p in P]
    nh = len(U.interiors) if U.geom_type == 'Polygon' else sum(len(q.interiors) for q in U.geoms)
    s = Sheet('11a_西館の屋根_上の層_シナ1.7', 841, 594, f'シナ 1.7：西館の屋根 上の層（3dm の屋根の平面、軒まで、光の筋の穴 {nh} 本）')
    s.add(box(0, 0, 841, 594), 'ref')
    s.add(U)
    s.save([(0, U.bounds[3] + 3, f'西館の屋根 上の層（光の筋の穴 {nh} 本）', 4)])
    pb = unary_union([p for _, p in P]).bounds
    s = Sheet('11b_西館の屋根_下の層_シナ1.7', 841, 594, f'シナ 1.7：西館の屋根 下の層（架構のあいだの板 {len(P)} 枚、梁 2 枚のあいだに落とし込む）。番号＝スパン（南の架構の番号）')
    s.add(box(0, 0, 841, 594), 'ref')
    for k, p in P:
        q = affinity.translate(p, 0, -pb[1]); s.add(q)
        c = q.representative_point(); txt = str(k)
        for j, ch in enumerate(txt):
            for l in label_num(ch, c.x - len(txt) * 0.8 + j * 1.6, c.y - 0.8, 1.6): s.add(l, 'eng')
    s.save([(0, pb[3] - pb[1] + 3, f'西館の屋根 下の層（{len(P)} 枚、番号＝スパン）', 4)])
    return (round(U.bounds[2], 1), round(U.bounds[3], 1), nh), [(k, round(p.bounds[2] - p.bounds[0], 1), round(p.bounds[3] - p.bounds[1], 1)) for k, p in P]

# ================= 7. 西館の架構 =================
def _frame_no(ang):
    """架構の番号（南から）：本館の架構 1（南の妻）の角度から 3 m ごと"""
    a = sorted(set(round(math.atan2(g.PathStart.Y - CY, g.PathStart.X - CX) % (2 * math.pi), 4) for g in cols))
    # 本館の柱の角度は東西で少しずれるので、まとめて 20 本の中心へ
    a = np.array(a); a1 = a.max(); step = (a.max() - a.min()) / 19
    return int(round((a1 - ang) / step)) + 1

def _ang(g):
    b = g.GetBoundingBox()
    return math.atan2((b.Min.Y + b.Max.Y) / 2 - CY, (b.Min.X + b.Max.X) / 2 - CX) % (2 * math.pi)

def _holes(g, clr):
    return [stadium(*to_model(np.array([hole_center(g, k)]))[0], clr[0], clr[1]) for k in range(1, g.ProfileCount)]

def west_parts(clr):
    """西館の架構の部品（柱は本館と同じ作り：0.8 を 2 枚、肩が GL、ほぞ。梁・2 階の床梁は 0.8 を 2 枚で柱を挟む）。
    返す：[(名前, 架構の番号, 形, つなぎの点)]"""
    out = []
    for nm_, g in objs_named('22a_西館_柱'):
        if '階段の箱の柱' in nm_:
            continue                                        # 階段の箱の 120 角の柱は作らない（ユーザー 10-28）
        if g.ProfileCount == 1:
            # キッチンの東の柱 180×400（10-28）：桁の穴が無い。本館の柱と同じ 0.8×2、幅は 400（4.0）、肩が GL、ほぞ
            P = profile_rz(g, 0); b_ = g.GetBoundingBox()
            x0, x1 = (P[:, 0].min() - R0) * S, (P[:, 0].max() - R0) * S
            xc = (x0 + x1) / 2
            part = unary_union([box(x0, 0, x1, (b_.Max.Z - GL) * S),
                                box(xc - TENON_W / 2, -TENON_L, xc + TENON_W / 2, 0.01)])
        else:
            part, hc = column_part(g, clr)
        b = part.bounds; xc = (b[0] + b[2]) / 2
        tabs = [Point(xc, b[1]), Point(xc, b[3])]          # つなぎはほぞの先と頭の上（長い辺には付けない、10-26）
        k = _frame_no(_ang(g))
        for _ in range(2): out.append(('柱', k, part, tabs))
    seen = set()
    for lay, nm in (('22b_西館_梁', '梁'), ('22c_西館_2階床梁', '床梁')):
        for nm_, g in objs_named(lay):
            if '出し梁' in nm_ or '登り梁' in nm_:
                continue                                    # 出し梁・北西の角の登り梁 u43.5 は 07 に入れない（10-28）
            P = to_model(profile_rz(g, 0))
            part = Polygon(P).buffer(0)
            for h_ in _holes(g, clr): part = part.difference(h_)
            if part.geom_type == 'MultiPolygon': part = max(part.geoms, key=lambda q: q.area)   # 細いかけらを捨てる
            part = part.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
            out.append((nm, _frame_no(_ang(g)), part, None))
    return out

def _upright(part):
    """細長い部品を横に寝かせる（いちばん小さい外接長方形の長い辺を水平に）"""
    mr = part.minimum_rotated_rectangle; c = np.array(mr.exterior.coords)
    e = [c[1] - c[0], c[2] - c[1]]; v = max(e, key=lambda x: np.hypot(*x))
    return -math.degrees(math.atan2(v[1], v[0]))

def west_sheets():
    clr = KETA_VARIANTS[J['桁']['選んだ穴']['名']]
    parts = west_parts(clr)
    items = []
    for nm, k, part, tabs in parts:
        if nm == '柱':
            g = part; tp = tabs
        else:
            a = _upright(part); c = part.centroid
            g = affinity.rotate(part, a, origin=c); tp = None
        b = g.bounds
        items.append((nm, k, affinity.translate(g, -b[0], -b[1]),
                      [affinity.translate(q, -b[0], -b[1]) for q in tp] if tp else None))
    # 棚に並べる（高い順）：300×600 の板（590×295 を使う）
    W, H, gap = 590, 295, 1.6
    items.sort(key=lambda it: (-(it[2].bounds[3]), it[0]))
    sheets = [[]]; x = y = rowh = 0
    for it in items:
        w, h = it[2].bounds[2], it[2].bounds[3]
        if x + w > W:
            x = 0; y += rowh + gap; rowh = 0
        if y + h > H:
            sheets.append([]); x = y = rowh = 0
        sheets[-1].append((it, x, y)); x += w + gap; rowh = max(rowh, h)
    for si, lst in enumerate(sheets):
        s = Sheet(f'07_西館の架構_{si + 1}_航空ベニヤ0.8', 600, 300,
                  f'航空ベニヤ 0.8 300×600：西館の架構（柱は 2 枚で 1 本、梁・2 階の床梁は 2 枚で柱を挟む）桁の穴 D。番号＝架構（南から）')
        s.add(box(0, 0, 600, 300), 'ref')
        for (nm, k, g, tp), x, y in lst:
            q = affinity.translate(g, x, H - y - g.bounds[3])
            s.add(q)
            if tp: s.tab_pts += [affinity.translate(t, x, H - y - g.bounds[3]) for t in tp]
            # 架構の番号を彫る（部品の中ほど、裏になる面）
            c = q.representative_point(); txt = str(k)
            if nm == '柱':
                bb = q.bounds; c = Point((bb[0] + bb[2]) / 2, bb[1] + 14)
            for j, ch in enumerate(txt):
                for l in label_num(ch, c.x - len(txt) * 0.6 + j * 1.2, c.y - 0.6, 1.2): s.add(l, 'eng')
        s.save([(0, -4, f'{len(lst)} 個', 3)])
    return [len(l) for l in sheets]

# ================= 8. 本館の外壁 =================
YAMATO = (1.35, 1.05)   # 大和張りの板の縁の線（彫り）：表の板 1.35・裏の板の見え 1.05 の交互（3dm の上板 135、割り 240。ユーザー 10-28）
def _wall_faces(name):
    g = objs(name)[0]
    V, F = g.Vertices, g.Faces
    P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
    for j in range(len(F)):
        f = F[j]; idx = list(dict.fromkeys([f[0], f[1], f[2], f[3]])); q = P[idx]
        n = np.cross(q[1] - q[0], q[2] - q[0])
        if np.linalg.norm(n) < 1e-6: continue
        n /= np.linalg.norm(n); c = q.mean(0)
        rv = np.array([c[0] - CX, c[1] - CY, 0]); rv /= np.linalg.norm(rv); tv = np.array([-rv[1], rv[0], 0])
        rr = np.hypot(q[:, 0] - CX, q[:, 1] - CY)
        th = np.arctan2(q[:, 1] - CY, q[:, 0] - CX) % (2 * np.pi)
        yield q, n @ rv, n @ tv, rr, th

RW_WALL = 205370.0      # 西の外壁を展開する半径（外面）
def honkan_walls():
    """西の外壁（弧を展開、外から見て左＝北）、北の妻壁（外から見て左＝東）、南の妻の西の端"""
    west, north, south = [], [], []
    RW = RW_WALL
    for q, nr, nt, rr, th in _wall_faces('17_本館_外壁（西・南北の妻）'):
        if abs(nr) > 0.9 and rr.mean() > 205300:
            west.append(Polygon(np.column_stack((th * RW, q[:, 2]))).buffer(0.5))
        elif abs(nt) > 0.9:
            a = math.degrees(th.mean())
            if a < 171.5: north.append(Polygon(np.column_stack((rr, q[:, 2]))).buffer(0.5))
            elif a > 186.3: south.append(Polygon(np.column_stack((-rr, q[:, 2]))).buffer(0.5))
    out = {}
    for k, L_ in (('西の外壁', west), ('北の妻', north), ('南の妻の西の端', south)):
        u = unary_union(L_).buffer(-0.5)
        u = affinity.scale(u, S, S, origin=(0, 0))
        u = unary_union([p for p in getattr(u, 'geoms', [u]) if p.minimum_rotated_rectangle.buffer(-1.0).area > 0])   # 幅 2 mm 未満のかけらを捨てる
        u = _cut_at_beam_top(u, k)          # 11-02：壁は梁の上面で止める（屋根は壁の上に載る。越屋根は無し）
        b = u.bounds
        out[k] = affinity.translate(u, -b[0], -b[1])
    # 外から見て左＝北にする（角度が大きい方が南。展開の u は南へ増える → そのままで左が北）
    return out

# 11-02 ユーザー：本館の外壁の天端は梁の上面（屋根の下面）にそろえる。屋根 1.7 は壁に足さない（屋根が壁の上に載る）。
# 越屋根は無し（06a に決まった）ので、越屋根の東の立ち上がりは作らない。
# 梁の上面は 3dm の梁（11b、切った 03a と同じ形）の断面の上辺：半径 r の一次式（東下がり 1/12）。
def _beam_top_line():
    P_ = profile_rz(beam, 0)
    k = next(i for i, p in enumerate(P_) if p[0] <= 190191.5)       # 断面の上辺の直線の部分（西の端から東の端の手前まで）
    return np.polyfit(P_[:k, 0], P_[:k, 1], 1)                       # z（FL から、実寸 mm）＝ a·r ＋ b
BEAM_TOP_A, BEAM_TOP_B = _beam_top_line()
def beam_top(r_mm):
    """半径 r（実寸 mm）での梁の上面の高さ（FL から、模型 mm）"""
    return (BEAM_TOP_A * r_mm + BEAM_TOP_B) * S

def _cut_at_beam_top(u, k):
    """展開した外壁の外形を、梁の上面の線で切る（西の外壁は r＝壁の位置で一定、妻は半径方向の位置で斜め）"""
    b = u.bounds
    if k == '西の外壁':
        yt = lambda x: beam_top(RW_WALL)
    elif k == '北の妻':
        yt = lambda x: beam_top(x / S)          # 北の妻の x ＝ 半径 × S
    else:
        yt = lambda x: beam_top(-x / S)         # 南の妻の x ＝ −半径 × S
    x0, x1 = b[0] - 1, b[2] + 1
    clip = Polygon([(x0, b[1] - 1), (x1, b[1] - 1), (x1, yt(x1)), (x0, yt(x0))])
    return u.intersection(clip)

def yamato_lines(poly):
    """大和張りの縦の線（彫り）。窓の穴は避ける"""
    from shapely.geometry import LineString
    b = poly.bounds; out = []
    xs, x, k = [], b[0] + YAMATO[0], 1
    while x < b[2]:
        xs.append(x); x += YAMATO[k % 2]; k += 1
    for x in xs:
        g = LineString([(x, b[1] - 1), (x, b[3] + 1)]).intersection(poly.buffer(-0.3))
        if not g.is_empty: out.append(g)
    return out

def wall_sheets():
    W = honkan_walls()
    s = Sheet('08_本館の外壁_航空ベニヤ1.0', 600, 300, '航空ベニヤ 1.0 300×600：本館の外壁（西は弧を展開、北の妻、南の妻の西の端）。天端は梁の上面。大和張りの線は彫り')
    s.add(box(0, 0, 600, 300), 'ref')
    y = 0; texts = []
    rows = [['西の外壁'], ['北の妻', '南の妻の西の端']]
    for row in rows:
        x = 0; rowh = 0
        for k in row:
            g = W[k]
            q = affinity.translate(g, x, 300 - y - g.bounds[3])
            s.add(q)
            for ln in yamato_lines(q): s.add(ln, 'eng')
            texts.append((x, 300 - y - g.bounds[3] - 3, k, 2.5))
            x += g.bounds[2] + 4; rowh = max(rowh, g.bounds[3])
        y += rowh + 8
    s.save(texts)
    return {k: tuple(round(v, 1) for v in g.bounds[2:]) for k, g in W.items()}


# ================= 6c. 本館の屋根の光の筋の穴を埋める差し込み小片＋小屋・機械室の屋根（11-02） =================
# 06a の光の筋の穴 18 本は、東の端が外皮の線（今の 3dm の光の筋の東の端）より約 14 mm 長い。06a は変えない。
# 穴の形は 06a の SVG から読み、外皮の線から東の部分を、シナ 1.7 の端材から切る差し込み小片にする。
# 06a は切ったときの 3dm（架構の角度が約 0.49° 違う）なので、今の 3dm の光の筋の穴を 06a の板に重ねる（剛体で合わせる）。
PLUG_GROW = 0.15   # 小片を描く大きさ：穴の描いた形（切ると実寸は +0.2 開く）より各辺 +0.15 大きく描く → 切って 0.2 小さく出て、すき間は各辺 約 0.05
SCRAP_X0 = 620.0   # 端材の板：06a を取った帯（841×220）の右の余り。06a は x 3〜617 を使う（板の左から）
T_VENEER = 1.0     # 航空ベニヤ 1.0 の厚さ（箱の板を突き合わせる寸法）

def _svg_rings(fname, H):
    import re
    t = open(os.path.join(OUT, fname)).read()
    cut = t.split('<g id="切る（赤）"')[1].split('</g>')[0]
    out = []
    for d in re.findall(r'<path d="([^"]+)"', cut):
        pts = [tuple(map(float, p.split(','))) for p in re.findall(r'[-\d.]+,[-\d.]+', d)]
        out.append(Polygon([(x, H - y) for x, y in pts]))
    return out

def roof_plugs():
    """06a の穴ごとの差し込み小片（描く形）。返す：[(南からの番号, 小片, 外皮の線の中点)]"""
    rings = _svg_rings('06a_本館の屋根_上の層_シナ1.7.svg', 220)
    old = sorted(rings[1:], key=lambda p: p.centroid.x)                  # 0＝外形、1〜＝穴
    up, _ = roof_parts(); ang = sheet_angle()
    wslots = [Polygon(h) for h in up.interiors]
    wslots.sort(key=lambda sl: to_sheet(sl, ang, (0, 0)).centroid.x)
    new = [to_sheet(sl, ang, (0, 0)) for sl in wslots]
    assert len(old) == len(new) == 18
    A, B = [], []                                                         # 西の端（外皮の線と反対）の頂点どうしで剛体を合わせる
    for a_, b_ in zip(old, new):
        ca = np.array(a_.exterior.coords)[:-1]; cb = np.array(b_.exterior.coords)[:-1]
        ha = ca[ca[:, 1] > ca[:, 1].mean()]; hb = cb[cb[:, 1] > cb[:, 1].mean()]
        A += list(hb[np.argsort(hb[:, 0])]); B += list(ha[np.argsort(ha[:, 0])])
    A, B = np.array(A), np.array(B)
    ma, mb = A.mean(0), B.mean(0)
    U_, _, Vt = np.linalg.svd((A - ma).T @ (B - mb)); R_ = Vt.T @ U_.T
    if np.linalg.det(R_) < 0:
        Vt[-1] *= -1; R_ = Vt.T @ U_.T
    t_ = mb - R_ @ ma
    assert np.abs((A @ R_.T + t_) - B).max() < 0.05
    plugs = []
    for a_, wsl, b_ in zip(old, wslots, new):
        # 外皮の線＝今の 3dm の光の筋の東の端（世界座標で半径が小さい方の 2 頂点）
        cw = np.array(wsl.exterior.coords)[:-1]; rr = np.hypot(cw[:, 0] - CX, cw[:, 1] - CY)
        east = np.argsort(rr)[:2]
        cb = np.array(b_.exterior.coords)[:-1]
        e1, e2 = [R_ @ cb[i] + t_ for i in east]
        d = (e2 - e1) / np.linalg.norm(e2 - e1); nrm = np.array([-d[1], d[0]])
        if nrm @ (np.array(a_.centroid.coords[0]) - (e1 + e2) / 2) > 0:
            nrm = -nrm                                                    # 東（余る側）へ
        big = Polygon([e1 - d * 50, e2 + d * 50, e2 + d * 50 + nrm * 50, e1 - d * 50 + nrm * 50])
        plug = a_.intersection(big)
        assert plug.geom_type == 'Polygon' and 12 < max(plug.bounds[2] - plug.bounds[0], plug.bounds[3] - plug.bounds[1]) < 17, plug.bounds
        plugs.append((plug, (e1 + e2) / 2))
    # 南から 1〜18：世界の角度が大きい方が南
    ang_w = [math.degrees(math.atan2(sl.centroid.y - CY, sl.centroid.x - CX)) % 360 for sl in wslots]
    order = np.argsort(-np.array(ang_w))
    num = {int(i): k + 1 for k, i in enumerate(order)}
    return [(num[i], plugs[i][0], plugs[i][1]) for i in range(18)]

def _upright_h(plug, mid):
    """長い辺を水平に、外皮の線（西の切り口）を右に"""
    c = np.array(plug.minimum_rotated_rectangle.exterior.coords)
    e = max(((c[i + 1] - c[i]) for i in range(2)), key=np.linalg.norm)
    a = -math.atan2(e[1], e[0])
    p = affinity.rotate(plug, a, origin=(0, 0), use_radians=True)
    m_ = affinity.rotate(Point(*mid), a, origin=(0, 0), use_radians=True)
    if m_.x < p.centroid.x:
        p = affinity.rotate(p, math.pi, origin=p.centroid, use_radians=True)
    return p

# ---- 小屋・機械室 ----
def _hut_boxes():
    """園庭の小屋（レイヤー 93）の便所・倉庫の箱（3dm のメッシュ）。
    返す：{名前: (a の長さ, d の長さ, 北東（d 小）の高さ, 南西（d 大）の高さ)}（模型 mm）。壁の上＝屋根の下面"""
    out = {}
    for nm, g in objs_named('93_園庭_小屋（便所・倉庫・コンポストの間）'):
        if not isinstance(g, r.Mesh) or ('便所' not in nm and '倉庫' not in nm):
            continue
        V = g.Vertices
        P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
        z0 = P[:, 2].min()
        xy = np.unique(np.round(P[:, :2], 1), axis=0)
        hts = {tuple(q): P[(np.abs(P[:, 0] - q[0]) < 0.6) & (np.abs(P[:, 1] - q[1]) < 0.6)][:, 2].max() - z0 for q in xy}
        hs = sorted(set(round(v) for v in hts.values()))
        assert len(hs) == 2, hs
        hi = [np.array(q) for q, v in hts.items() if round(v) == hs[1]]
        lo = [np.array(q) for q, v in hts.items() if round(v) == hs[0]]
        La = np.linalg.norm(hi[0] - hi[1])                                # 高さの等しい 2 頂点を結ぶ辺が a 方向
        Ld = min(np.linalg.norm(hi[0] - q) for q in lo)
        out[nm.split('（')[0]] = (La * S, Ld * S, hs[0] * S, hs[1] * S)
    return out

HUT_ROOF = dict(a=(20.3, 31.3), d=(1.1, 6.3), pitch=0.1)   # data/garden.json の HUT：a の両端に 0.3、北東に 0.3、南西に軒 1.5。東下がり 1/10（北東が低い）

def _kikai_ring():
    g = objs('35_機械室（本館の北）')[0]
    V, F = g.Vertices, g.Faces
    P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
    polys = []
    for j in range(len(F)):
        f = F[j]; idx = list(dict.fromkeys([f[0], f[1], f[2], f[3]])); q = P[idx]
        n = np.cross(q[1] - q[0], q[2] - q[0]); nn = np.linalg.norm(n)
        if nn < 1e-6:
            continue
        if abs(n[2] / nn) > 0.99 and abs(q[:, 2].mean() - 3200) < 1:     # 屋根の上面（z 3200）の平面形＝外形
            polys.append(Polygon(q[:, :2]).buffer(0.5))
    u = unary_union(polys).buffer(-0.5)
    big = max(getattr(u, 'geoms', [u]), key=lambda p_: p_.area)
    return big, float(P[:, 2].max())

def kikai_parts():
    """機械室（おむすび）：外形（丸い三角、角 R1300）の周を 1 枚に展開した壁（戸の開口 1.6×2.1）と、屋根の板。
    壁は 3dm のパラペット（z 3200〜3800）まで通し、屋根の板は内側に落とす（上面が z 3200）"""
    from shapely.geometry import LineString
    big, ztop = _kikai_ring()
    c = np.array(big.exterior.coords)
    ring = LineString(c); L = ring.length
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    k = int(np.argmax(seg)); s_seam = cum[k] + seg[k] / 2                 # 継ぎ目：いちばん長い直線の辺の真ん中
    pts = []
    for nm, g in objs_named('35d_機械室_戸（両開き1.6、外開き）'):
        V = g.Vertices; pts += [(V[i].X, V[i].Y) for i in range(len(V))]
    ss = sorted(ring.project(Point(p)) for p in pts)
    x = lambda s_: ((s_ - s_seam) % L) * S
    d0, d1 = sorted((x(ss[0]), x(ss[-1])))
    H = ztop * S
    wall = box(0, 0, L * S, H).difference(box(d0, 0, d1, 2100 * S))
    roof = affinity.scale(big, S, S, origin=(0, 0)).buffer(-T_VENEER, join_style=1)   # 壁の内側に落とす（描く形：壁の厚さぶん内へ）
    return wall, roof, dict(L=L * S, H=H, door_x=(d0, d1), seam=s_seam)

def _hut_wall_panels(La, Ld, h_ne, h_sw, t=T_VENEER):
    """底の開いた箱の 4 枚の壁（突き付け）：長い辺（a 方向）の 2 枚は全長、妻の 2 枚は長辺の 2 枚のあいだ（長さ Ld−2t）、上辺は北東から南西へ斜め"""
    end = Polygon([(0, 0), (Ld - 2 * t, 0), (Ld - 2 * t, h_sw), (0, h_ne)])     # 左＝北東（低い）
    return {'北東の壁': box(0, 0, La, h_ne), '南西の壁': box(0, 0, La, h_sw), '妻の壁 1': end, '妻の壁 2': Polygon(end)}

def hut_kikai_sheets():
    # ---- 06c：シナ 1.7 の端材 ----
    plugs = roof_plugs()
    b06a = _svg_rings('06a_本館の屋根_上の層_シナ1.7.svg', 220)[0].bounds
    W6 = 841 - SCRAP_X0
    s6 = Sheet('06c_屋根の差し込み小片と小屋・機械室の屋根_シナ1.7', W6, 220,
               f'シナ 1.7 の端材（06a を取った帯の右の余り、06a は x {b06a[0]:.0f}〜{b06a[2]:.0f}）：06a の光の筋の穴の東の端を埋める差し込み小片 18（南から 1〜18）、小屋の屋根、機械室の屋根')
    s6.add(box(0, 0, W6, 220), 'ref')
    pitch_x, pitch_y = 22.0, 7.0
    for i, (n_, plug, mid) in enumerate(sorted(plugs, key=lambda p: p[0])):
        col, row = i % 9, i // 9
        p = _upright_h(plug.buffer(PLUG_GROW, join_style=2), mid)
        p = place(p, col * pitch_x + 5, -row * pitch_y - 3)
        s6.add(p)
        b = p.bounds; yc = (b[1] + b[3]) / 2
        s6.tab_pts += [Point((b[0] + b[2]) / 2, b[1]), Point((b[0] + b[2]) / 2, b[3])]
        for j, ch in enumerate(str(n_)):
            for l in label_num(ch, col * pitch_x + j * 1.3 - 0.2, yc - 0.55, 1.1):
                s6.add(l, 'eng')
    # 小屋の屋根：平面（a 20.3〜31.3 × d 1.1〜6.3 m）。1/10 の斜めなので d 方向は斜めの長さ。北東（d 小）を上に、a を右に（上から見たまま）
    ra, rd = HUT_ROOF['a'], HUT_ROOF['d']
    Lr, Dr = (ra[1] - ra[0]) * 10, (rd[1] - rd[0]) * 10 * math.sqrt(1 + HUT_ROOF['pitch'] ** 2)
    yb = -(2 * pitch_y + 12)
    s6.add(place(box(0, 0, Lr, Dr), 0, yb - Dr))
    wall, kroof, kinfo = kikai_parts()
    kh = kroof.bounds[3] - kroof.bounds[1]
    s6.add(place(kroof, Lr + 8, yb - kh))                                 # 世界の向きのまま（上から見て、上＝北）
    s6.save([(0, 3, '差し込み小片 1〜18（南から）。番号の彫りは小片の左', 2.5),
             (0, yb - Dr - 3, f'小屋の屋根 {Lr:.1f}×{Dr:.2f}（上から見て：上＝北東の軒（低い）、右＝南東）', 2.5),
             (Lr + 8, yb - kh - 3, '機械室の屋根（上から見て、上＝北）', 2.5)])
    # ---- 11：航空ベニヤ 1.0 ----
    s = Sheet('11_小屋と機械室_航空ベニヤ1.0', 600, 300, '航空ベニヤ 1.0 300×600：園庭の小屋（便所・倉庫・コンポストの枠）と機械室の壁。底の開いた箱。屋根は 06c（シナ 1.7）')
    s.add(box(0, 0, 600, 300), 'ref')
    texts = []
    st = dict(x=0.0, y=0.0, rowh=0.0)
    def put(geom, label):
        w_, h_ = geom.bounds[2], geom.bounds[3]
        if st['x'] + w_ > 590:
            st['x'] = 0.0; st['y'] += st['rowh'] + 9; st['rowh'] = 0.0
        q = place(geom, st['x'], 300 - st['y'] - h_)
        s.add(q)
        texts.append((st['x'], 300 - st['y'] - h_ - 3, label, 2.2))
        st['x'] += w_ + 4; st['rowh'] = max(st['rowh'], h_)
        return q
    q = put(wall, f'機械室の壁（周を 1 枚に展開 {kinfo["L"]:.1f}×{kinfo["H"]:.1f}、大和張り、戸の開口 1.6×2.1、継ぎ目は長い辺の真ん中）')
    for ln in yamato_lines(q):
        s.add(ln, 'eng')
    st['x'] = 0.0; st['y'] += st['rowh'] + 9; st['rowh'] = 0.0
    hb = _hut_boxes()
    for nm in ('便所', '倉庫'):
        La, Ld, hne, hsw = hb[nm]
        for k, g in _hut_wall_panels(La, Ld, hne, hsw).items():
            put(g, f'{nm} {k}')
    # コンポストの枠 4 つ（全体 1.05×1.2、高さ 0.7、ふた付き）
    CP = json.load(open(os.path.join(ROOT, 'data', 'garden.json')))['COMPOST']
    fa, fd, fh = (CP['w'] - 0.1) * 10, CP['depth'] * 10, 7.0
    for lab in CP['labels']:
        for k, g in (('前の壁', box(0, 0, fa, fh - T_VENEER)), ('後ろの壁', box(0, 0, fa, fh - T_VENEER)),
                     ('横の壁 1', box(0, 0, fd - 2 * T_VENEER, fh - T_VENEER)), ('横の壁 2', box(0, 0, fd - 2 * T_VENEER, fh - T_VENEER)),
                     ('ふた', box(0, 0, fa, fd))):
            put(g, f'枠「{lab}」' if k == '前の壁' else '')
    s.save(texts)
    return dict(hut=hb, kikai=kinfo, roof=(Lr, Dr), frame=(fa, fd, fh), plugs=[(n_, [round(v, 2) for v in p_.bounds]) for n_, p_, m_ in plugs])

# ================= 9. 室内の壁（本館 38・西館 24） =================
def _panel(g):
    """薄い壁のメッシュを立面の板に：平面の長い向き（主成分）を u、高さを z（自分の下端から）にして、
    板の面を向く面だけを投影して合わせる（戸の開口が穴や切り欠きになる）。返す：(板, 平面の中心, 向き, 厚さ, 下端 z)"""
    V, F = g.Vertices, g.Faces
    P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
    c = P[:, :2].mean(0); xy = P[:, :2] - c
    _, _, vt = np.linalg.svd(xy, full_matrices=False); ax, nx = vt[0], vt[1]
    T = np.ptp(xy @ nx); H = np.ptp(P[:, 2])
    if T > 250 or H < 600: return None
    z0 = P[:, 2].min(); polys = []
    for j in range(len(F)):
        f = F[j]; idx = list(dict.fromkeys([f[0], f[1], f[2], f[3]])); q = P[idx]
        n = np.cross(q[1] - q[0], q[2] - q[0])
        if np.linalg.norm(n) < 1e-6: continue
        n /= np.linalg.norm(n)
        if abs(n[:2] @ nx) < 0.9: continue
        pg = Polygon(np.column_stack(((q[:, :2] - c) @ ax, q[:, 2] - z0)))
        if pg.area > 1: polys.append(pg.buffer(0.5))
    if not polys: return None
    u = unary_union(polys).buffer(-0.5)
    u = affinity.scale(u, S, S, origin=(0, 0))
    u = unary_union([p_ for p_ in getattr(u, 'geoms', [u]) if p_.area > 2])
    if u.is_empty: return None
    b = u.bounds
    return affinity.translate(u, -b[0], -b[1]), c, ax, T, z0

def interior_parts():
    out = []
    for lay, tag in (('38_しつらえ_間仕切り・框・腰壁', '本館'), ('24_西館_間仕切り', '西館')):
        for g in objs(lay):
            if not isinstance(g, r.Mesh): continue
            pn = _panel(g)
            if pn: out.append((tag,) + pn)
    return out

def _shelf(items, W, H, gap=2.0):
    sheets = [[]]; x = y = rowh = 0
    for it in sorted(items, key=lambda it: -it[1].bounds[3]):
        w, h = it[1].bounds[2], it[1].bounds[3]
        if x + w > W: x = 0; y += rowh + gap; rowh = 0
        if y + h > H: sheets.append([]); x = y = rowh = 0
        sheets[-1].append((it, x, y)); x += w + gap; rowh = max(rowh, h)
    return sheets

def interior_sheets():
    parts = interior_parts()
    if not any(p_[0] == '西館' for p_ in parts):
        # 10-28：今の 3dm の西館の間仕切り（24）は 1 つにつながった立体で、板に分けられない。前の 09・10 を残す
        print('  西館の間仕切りが板に分けられない（24 が 1 つの立体）ので、09・10 は書き出さない')
        return len(parts), None
    items = [(f'{i + 1}', pn[1], pn) for i, pn in enumerate(parts)]
    items = [(n, g, pn) for n, g, pn in items]
    sh = _shelf([(n, g) for n, g, _ in items], 590, 290)
    names = {}
    for si, lst in enumerate(sh):
        s = Sheet(f'09_室内の壁_{si + 1}_航空ベニヤ0.6', 600, 300,
                  '航空ベニヤ 0.6 300×600：本館と西館の室内の壁・腰壁・框（番号は 10_室内の壁の配置図 と同じ）。高さは床の上面から')
        s.add(box(0, 0, 600, 300), 'ref')
        for (n, g), x, y in lst:
            q = affinity.translate(g, x, 290 - y - g.bounds[3])
            s.add(q)
            c = q.representative_point()
            for j, ch in enumerate(n):
                for l in label_num(ch, c.x - len(n) * 0.6 + j * 1.2, c.y - 0.6, 1.2): s.add(l, 'eng')
        s.save([])
    # 配置図（1/100、平面）：壁の位置と番号
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    plt.rcParams['font.family'] = 'Noto Sans CJK JP'
    ang = sheet_angle()
    up = plan('10_本館_屋根')
    flo = unary_union([plan('12_本館_床（はだし ±0）'), plan('14_本館_外縁側（土足 −150）'), plan('15_本館_あまのがわ（土足 −150）')])
    wfl = unary_union([plan(n) for n in ('31_1F_遊戯室', '32_1F_キッチン', '33_1F_東の帯（はだし ±0、ホールと一続き）', '34_1F_食べる土間') if n in LAY])
    path = os.path.join(OUT, '10_室内の壁の配置図.pdf')
    with PdfPages(path) as pdf:
        for tag in ('本館', '西館'):
            fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4)); axp = fig.add_axes([0, 0, 1, 1])
            ub = to_sheet(unary_union([flo, wfl]), ang, (0, 0)).bounds
            off = (20 - ub[0], 60 - ub[1])
            ts = lambda g: affinity.translate(to_sheet(g, ang, (0, 0)), *off)
            for base in (flo, wfl):
                for gg in getattr(base, 'geoms', [base]):
                    q = ts(gg)
                    xs, ys = q.exterior.xy; axp.plot(xs, ys, color='0.75', lw=0.4)
            for g in list(cols) + list(objs('22a_西館_柱')):
                b_ = g.GetBoundingBox() if not isinstance(g, MeshCol) else None
                pc = Point((b_.Min.X + b_.Max.X) / 2, (b_.Min.Y + b_.Max.Y) / 2) if b_ else Point(g.PathStart.X, g.PathStart.Y)
                q = ts(pc); axp.plot([q.x], [q.y], 's', color='0.3', ms=2)
            for (n, g, pn) in items:
                if pn[0] != tag and tag == '西館' and False: pass
                tg, panel, c, ax_, T, z0 = pn
                L_ = panel.bounds[2] / S
                a = np.array(c) - ax_ * L_ / 2; b = np.array(c) + ax_ * L_ / 2
                from shapely.geometry import LineString
                ln = ts(LineString([a, b])); xs, ys = ln.xy
                col = 'tab:red' if tg == tag else '0.6'
                axp.plot(xs, ys, color=col, lw=1.2)
                mid = ln.interpolate(0.5, normalized=True)
                axp.text(mid.x, mid.y, n, fontsize=5, color=col, ha='center', va='center')
            axp.set_xlim(0, 841); axp.set_ylim(0, 594); axp.set_aspect('equal'); axp.axis('off')
            axp.text(20, 20, f'室内の壁の配置図：{tag}の壁を赤（番号＝09 の板の番号）。A1 に 100% で印刷すると模型と同じ大きさ', fontsize=10)
            pdf.savefig(fig); plt.close(fig)
    return len(parts), [len(l) for l in sh]

# ================= 台の表面（シナ 3）：建物の穴・青の彫り・塀と柵の足の溝 =================
# 10-31 の頼み（模型作成）：表面の彫りと溝は mokei/表面の彫り一覧.md のとおり。仮の出力（T7 の結果と、必須・重要の判断で直す）。
#   python3 laser.py dai        … 01台_表面_シナ3.svg と 01台_溝の試し片_シナ3.svg だけを書く（ほかの部品は触らない）
# 座標：3dm の xy（mm）。台は A1（841×594）に収めるため、DAI_ROT だけ回す（北が右上）。回して縮尺 S をかけ、左上に寄せる
DAI_ROT = -38.5                                  # 度。川側の辺を水平に（63 m × 56 m、道路の窓を足して 68×56 m → 682×560 mm）
DAI_ROAD_WIN = (-45000, -75000, -24000, -30000)  # 道路を見せる窓（3dm mm）：西の道路の、お向かいの張り出しと狭い所をふくむ所
DAI_HOLE_SHRINK = 0.11                           # 建物の穴は、切り幅の分（シナ 3：0.22）だけ小さく描く＝片側 0.11（模型 mm）
DAI_CLIFF = 800                                  # 川側の崖の上の小段・土（柵の外 0.8 m）まで台を広げる（3dm mm）
DAI_SLOT_LEN = 4.0                               # 足の溝の長さ（塀に沿う向き、模型 mm）
DAI_SLOT_W = 0.5                                 # 足の溝の幅（描く幅、仮。T7 試し片の結果で決める）
DAI_SLOT_PITCH = 40.0                            # 足のおき：30〜40 mm（この値を超えない最少の本数に等分）
DAI_SLOT_INSET = 3.0                             # 両端の足は端から 3 mm 内
DAI_TREE_MARK = 1.2                              # 木の位置（手でドリル）の十字の長さ
SITE_OUTER = [(0, 0), (34860, -43830), (-14440, -83040), (-21910, -73650), (-25830, -20540)]
SITE_INNER = [(-160, -1405), (33455, -43670), (-14280, -81635), (-20935, -73269), (-24794, -20994)]

def _pf(prefix):
    idx = {i for n, i in LAY.items() if n.startswith(prefix)}
    return [(o.Attributes.Name or '', o.Geometry) for o in m.Objects if o.Attributes.LayerIndex in idx]

def _cxy(c, n=80):
    if isinstance(c, r.PolylineCurve):
        return [(c.Point(i).X, c.Point(i).Y) for i in range(c.PointCount)]
    return [(p.X, p.Y) for p in sample_curve(c, n)]

def _foot(g):
    """立てた押し出しの、平面の輪郭"""
    return Polygon(_cxy(g.Profile3d(0, 0))).buffer(0)

def _mesh_poly(g, min_area=1.0):
    V = g.Vertices; F = g.Faces
    P = np.array([[V[i].X, V[i].Y] for i in range(len(V))])
    ps = []
    for fi in range(len(F)):
        f = F[fi]
        idx = [f[0], f[1], f[2]] if f[2] == f[3] else [f[0], f[1], f[2], f[3]]
        pg = Polygon(P[idx])
        if pg.area > min_area: ps.append(pg.buffer(1))
    return unary_union(ps).buffer(-1)

def _bb(g):
    b = g.GetBoundingBox()
    return b.Min.X, b.Min.Y, b.Min.Z, b.Max.X, b.Max.Y, b.Max.Z

def _long_axis(poly):
    """細長い輪郭の長い軸（中心線）を LineString で"""
    from shapely.geometry import LineString
    c = list(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [(math.hypot(c[(i + 1) % 4][0] - c[i][0], c[(i + 1) % 4][1] - c[i][1]), i) for i in range(4)]
    L = max(e)[1]                                    # 長い辺の一つ → その辺の向きで中点どうしを結ぶ
    a, b = np.array(c[L]), np.array(c[(L + 1) % 4]); d = np.array(c[(L + 3) % 4]) - a
    return LineString([tuple(a + d / 2), tuple(b + d / 2)])

def dai_road():
    from shapely.geometry import box as _box
    win = _box(-70000, -110000, 20000, 20000)
    ts = []
    for nm, g in _pf('03_周辺_道路'):
        V = [(v.X, v.Y) for v in g.Vertices]
        for i in range(g.Faces.Count):
            f = g.Faces[i]
            pts = [V[j] for j in dict.fromkeys(f)]
            if len(pts) < 3: continue
            P = Polygon(pts)
            if P.is_valid and P.area > 0 and P.intersects(win): ts.append(P)
    return unary_union(ts)

def dai_features():
    """台の表面に載せるものを集める。戻り：dict（名前→{kind, prio, geom（3dm mm）, layer, note}）。
    kind：hole（切る穴）／outline（外形を切る）／line（青の彫り）／slots（足の溝、runs＝中心線の列）／marks（木の位置、点）"""
    from shapely.geometry import LineString, Point as _Pt, box as _box
    F = {}
    site = Polygon(SITE_OUTER)
    # --- 建物の穴（表面＝GL に、ベタ基礎がはまる）
    up, lo, found = floors()
    close = lambda g: g.buffer(120, join_style=2).buffer(-120, join_style=2)
    west = close(unary_union([plan('31_1F_遊戯室'), plan('32_1F_キッチン'), plan('33_1F_東の帯（はだし ±0、ホールと一続き）'), plan('36_1F_階段')]))
    honkan = found
    both = unary_union([honkan, west])
    F['本館の穴'] = dict(kind='hole', prio='必須', layer='12〜15・52（床）', geom=honkan, note='05 のベタ基礎と同じ輪郭')
    F['西館の穴'] = dict(kind='hole', prio='必須', layer='31〜33・36（床）', geom=west.difference(honkan.buffer(30)), note='西館のベタ基礎（表面から抜けた板）')
    # --- 外形（台）
    road = dai_road()
    reg = road.intersection(_box(*DAI_ROAD_WIN))
    river = LineString([SITE_OUTER[1], SITE_OUTER[2]])
    nrm = np.array([-(river.coords[1][1] - river.coords[0][1]), river.coords[1][0] - river.coords[0][0]]); nrm = nrm / np.linalg.norm(nrm)
    cen = np.array(site.centroid.coords[0]); mid = np.array(river.interpolate(0.5, normalized=True).coords[0])
    if np.dot(nrm, mid - cen) < 0: nrm = -nrm
    a, b = np.array(river.coords[0]), np.array(river.coords[1])
    strip = Polygon([a, b, b + nrm * DAI_CLIFF, a + nrm * DAI_CLIFF])
    outline = unary_union([site, reg.buffer(300, join_style=2), strip]).buffer(1).buffer(-1)       # 道路の縁の線の外に、木を 3 mm 残す（縁の線は彫りで、切る線と重ねない）
    F['台の外形'] = dict(kind='outline', prio='必須', layer='00・03', geom=outline, note='敷地（外側の線）＋川側の崖の上の小段 0.8 m＋道路の窓')
    # --- 築山：バルサの等高線の一番下の輪郭（位置決め）
    mounds = []
    for nm, g in _pf('98_園庭_等高線の板'):
        z = _bb(g)[2]
        if abs(z + 100) < 5:
            P = Polygon(_cxy(g, 400)).buffer(0)
            mounds.append(P)
    mounds.sort(key=lambda p: -p.area)
    F['築山の輪郭'] = dict(kind='line', prio='必須', layer='98', geom=mounds[0].exterior, note='主の築山（バルサ 12 段の裾）')
    F['小さな丘の輪郭'] = dict(kind='line', prio='重要', layer='98', geom=unary_union([p.exterior for p in mounds[1:]]), note='おくのもりの丘・しずかのもりの土手・柳の家の脇の小丘（バルサの裾）')
    F['_mound_polys'] = mounds
    # --- 小川・滝壺・雨庭・雨の川
    lns = [(_bb(g), g) for nm, g in _pf('90l_園庭_線') if isinstance(g, r.PolylineCurve)]
    stream = min(lns, key=lambda t: abs(t[0][2] + 700))[1]   # 川床が -0.7 m まで下がる折れ線＝小川の中心線（-0.9 m は暗渠）
    sl = LineString(_cxy(stream, 400))
    F['小川'] = dict(kind='line', prio='必須', layer='90l・92', geom=sl.buffer(250, cap_style=2).exterior, note='幅 0.5 m の両岸の線（平刀で掘る）', len_center=sl.length)
    pool = [g for nm, g in _pf('92_園庭_水') if isinstance(g, r.Extrusion)]
    if pool: F['滝壺'] = dict(kind='line', prio='重要', layer='92', geom=_foot(pool[0]).exterior, note='φ1.0 の滝壺')
    rg = [_mesh_poly(g) for nm, g in _pf('92s_')]
    if rg: F['雨庭'] = dict(kind='line', prio='重要', layer='92s', geom=unary_union(rg).boundary, note='洲浜（白い玉石）の浅いくぼみ、約 21 m²')
    rr = unary_union([_mesh_poly(g) for nm, g in _pf('99_園庭_雨の川')])
    F['雨の川'] = dict(kind='line', prio='重要', layer='99', geom=rr.boundary, note='本館の雨落ちの溝（幅 0.5 m）。本館の穴の縁に重なる所は穴で切る')
    # --- 駐車・駐輪
    stalls, bikes_p, bikes_s = [], [], []
    for nm, g in _pf('74_外構_駐車'):
        if not isinstance(g, r.NurbsCurve): continue
        P = Polygon(_cxy(g)); a_ = P.area / 1e6
        (stalls if a_ > 10 else bikes_p if a_ > 1.0 else bikes_s).append(P)
    F['車室 5'] = dict(kind='line', prio='必須', layer='74', geom=unary_union([p.exterior for p in stalls]), n=len(stalls), note='2.5×5.0 m の車室（うち 1 は搬入）')
    asph = [_foot(g) for nm, g in _pf('74a_') if isinstance(g, r.Extrusion)]
    F['車路・駐車場の外形'] = dict(kind='line', prio='必須', layer='74a', geom=unary_union([p.exterior for p in asph]), note='アスファルトの範囲（車路 5.5 m）')
    F['駐輪の範囲'] = dict(kind='line', prio='重要', layer='74', geom=unary_union([unary_union(bikes_p).convex_hull.exterior, unary_union(bikes_s).convex_hull.exterior]), note=f'保護者 {len(bikes_p)} 台・職員 {len(bikes_s)} 台を、範囲の外形 2 つで（1 台ずつは彫らない）')
    F['駐輪の1台ずつ'] = dict(kind='line', prio='（省く）', layer='74', geom=unary_union([p.exterior for p in bikes_p + bikes_s]), n=len(bikes_p) + len(bikes_s), note='0.65×2.0 m の枠 21 個（6.5×20 mm）。範囲だけで足りるので省く')
    # --- 舗装の区分
    pav = []
    for nm, g in _pf('76_外構_舗装'):
        if isinstance(g, r.NurbsCurve) and g.IsClosed:
            P = Polygon(_cxy(g)).buffer(0)
            if P.area > 1.5e6: pav.append(P)
    F['舗装の区分'] = dict(kind='line', prio='重要', layer='76', geom=unary_union([p.exterior for p in pav]), n=len(pav), note='歩道 1.0・ひろば・見送りの小径・搬入路・北の小径など')
    # --- 道路（窓の中の、向かい側の縁の線）
    rb = road.boundary.intersection(_box(*DAI_ROAD_WIN)).difference(site.buffer(400))      # 窓の中の道の縁から、敷地の縁と重なる線を除く
    F['道路の縁'] = dict(kind='line', prio='必須', layer='03', geom=rb, note='窓の中の、向かい側の縁（敷地の側は台の縁）。お向かいの張り出しと道の狭い所をふくむ')
    # --- 林の範囲：樹冠（園庭の木 4 本以上が連なる所）の外形。かぜのもり・しずかのもり・おくのもりの目じるし
    cps = []
    for nm, g in _pf('94c_'):
        if '柳の家' in nm: continue
        bb_ = _bb(g); cps.append(_Pt((bb_[0] + bb_[3]) / 2, (bb_[1] + bb_[4]) / 2).buffer((bb_[3] - bb_[0]) / 2 * 0.85))
    comps = unary_union(cps)
    big = [c for c in getattr(comps, 'geoms', [comps]) if sum(1 for q in cps if q.intersects(c)) >= 4]
    F['林の範囲'] = dict(kind='line', prio='重要', layer='94c', geom=unary_union([c.buffer(300).buffer(-300).exterior for c in big]), n=len(big), note='樹冠が 4 本以上連なる所の外形（かぜのもり・しずかのもり・おくのもり）')
    # --- 塀と柵の足の溝（runs＝中心線）
    walls = []
    for nm, g in _pf('70_外構_生垣・塀・格子'):
        if isinstance(g, r.Extrusion) and _bb(g)[5] - _bb(g)[2] < 100 and abs(_bb(g)[2] + 100) < 5:
            P = _foot(g)
            if max(P.bounds[2] - P.bounds[0], P.bounds[3] - P.bounds[1]) > 500: walls.append(_long_axis(P))
    lat = []
    for nm, g in _pf('70k_'):
        if isinstance(g, r.Extrusion) and abs(_bb(g)[2] - 855) < 5:
            P = _foot(g)
            if max(P.bounds[2] - P.bounds[0], P.bounds[3] - P.bounds[1]) > 5000: lat.append(_long_axis(P))
    iron = []
    for nm, g in _pf('74p_'):
        if isinstance(g, r.Extrusion) and abs(_bb(g)[2] + 220) < 5:
            P = _foot(g)
            if max(P.bounds[2] - P.bounds[0], P.bounds[3] - P.bounds[1]) > 3000: iron.append(_long_axis(P))
    hito = [g for nm, g in _pf('60_') if isinstance(g, r.Mesh)]
    if hito:
        b = _bb(hito[0]); iron_h = LineString([((b[0] + b[3]) / 2, b[1]), ((b[0] + b[3]) / 2, b[4])])
    else: iron_h = None
    F['_walls'] = walls; F['_lattice'] = lat; F['_iron'] = iron; F['_hito'] = iron_h
    # --- 木
    trunks = _pf('94_園庭_木の幹'); crowns = _pf('94c_')
    trees = []
    for nm, g in trunks:
        b = _bb(g); cx, cy = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2
        cr = min(crowns, key=lambda c: math.hypot((_bb(c[1])[0] + _bb(c[1])[3]) / 2 - cx, (_bb(c[1])[1] + _bb(c[1])[4]) / 2 - cy))
        trees.append(dict(name=nm.split('（')[0], x=cx, y=cy, base=b[2], top=_bb(cr[1])[5], rcrown=(_bb(cr[1])[3] - _bb(cr[1])[0]) / 2, phi=(b[3] - b[0]), src='94'))
    crown77 = _pf('77c_')
    for (nm, g), lab in zip(_pf('77_外構_樹木'), ['入江の木', 'ヤマボウシ（みなみのさんかく）', 'キンモクセイ（生垣）', 'キンモクセイ（生垣）', 'キンモクセイ（生垣）', 'お向かいの張り出しの木']):
        b = _bb(g); cx, cy = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2
        cr = [c for c in crown77 if math.hypot((_bb(c[1])[0] + _bb(c[1])[3]) / 2 - cx, (_bb(c[1])[1] + _bb(c[1])[4]) / 2 - cy) < 500]
        top = _bb(cr[0][1])[5] if cr else b[5]
        trees.append(dict(name=lab, x=cx, y=cy, base=b[2], top=top, rcrown=((_bb(cr[0][1])[3] - _bb(cr[0][1])[0]) / 2 if cr else 0), phi=(b[3] - b[0]), src='77'))
    for t in json.load(open(os.path.join(ROOT, 'data', 'siteplan_approach.json')))['trees']:
        if t['name'] == 'モミジ':                                    # 読書の庭（3dm 67 は部品が多いので、配置図の位置を使う）
            trees.append(dict(name='モミジ（読書の庭）', x=t['xy'][0] * 1000, y=t['xy'][1] * 1000, base=-300, top=4200, rcrown=t['r'] * 1000, phi=120, src='67'))
    F['_trees'] = trees
    return F

def dai_slot_positions(line, inset=None):
    """線（模型 mm）に沿って、両端から inset 内、おき DAI_SLOT_PITCH 以下の最少の本数に等分した足の位置（点）"""
    inset = DAI_SLOT_INSET if inset is None else inset
    L = line.length
    L2 = max(L - 2 * inset, 0)
    n = max(1, math.ceil(L2 / DAI_SLOT_PITCH - 1e-9))
    if L2 == 0: return [line.interpolate(L / 2)]
    return [line.interpolate(inset + L2 * i / n) for i in range(n + 1)]

def dai_slot_geom(line, d, w, ln):
    """線 line 上の距離 d の所に、線に沿って ln・横に w の細長い穴"""
    p = line.interpolate(d); q = line.interpolate(min(d + 0.01, line.length)); p0 = line.interpolate(max(d - 0.01, 0))
    t = np.array([q.x - p0.x, q.y - p0.y]); t = t / np.linalg.norm(t); nn = np.array([-t[1], t[0]])
    c = np.array([p.x, p.y])
    return Polygon([c - t * ln / 2 - nn * w / 2, c + t * ln / 2 - nn * w / 2, c + t * ln / 2 + nn * w / 2, c - t * ln / 2 + nn * w / 2])

def dai_tx(g):
    """3dm mm → 回して模型 mm（原点のずれは to_top_left が直す）"""
    g = affinity.rotate(g, DAI_ROT, origin=(0, 0))
    return affinity.scale(g, S, S, origin=(0, 0))

# 塀・柵の足の溝：どれを必須にするか（一覧の案 A＝必須だけ、案 B＝重要も）
DAI_FENCE_MUST = ('川沿いの縦格子', '北の塀（読書の庭）', 'ひろば西の塀')
def dai_fence_runs(F):
    """名前つきの塀・柵の runs（3dm mm の LineString）を、長さ順に。戻り：[(名前, 線, 優先)]"""
    out = []
    for i, g in enumerate(sorted(F['_lattice'], key=lambda x: -x.length)):
        out.append((f'川沿いの縦格子 {i + 1}', g, '必須', '70k'))
    W = sorted(F['_walls'], key=lambda x: -x.length)
    def nm(g):
        x, y = g.centroid.x / 1000, g.centroid.y / 1000
        if y > -20: return ('北の塀（読書の庭）' if x < -9 else '北の塀（木戸の先）' if x < 0 else '北のもりの北の端の塀', 70)
        if y < -60: return ('公園側の塀', 70)
        return ('ひろば西の塀', 70)
    cnt = {}
    for g in W:
        n_, _ = nm(g); cnt[n_] = cnt.get(n_, 0) + 1
        pr = '必須' if n_ in ('北の塀（読書の庭）', '北の塀（木戸の先）', 'ひろば西の塀') else '重要'
        out.append((f'{n_} {cnt[n_]}', g, pr, '70'))
    for i, g in enumerate(sorted(F['_iron'], key=lambda x: -x.length)):
        out.append((f'公園の鉄柵（現況）{i + 1}', g, '重要', '74p'))
    if F['_hito'] is not None: out.append(('一本の線の延長の柵', F['_hito'], '重要', '60'))
    out.sort(key=lambda t: -t[1].length)
    return out

def dai_forest_pick(n_target=40):
    """北山杉の林 141 本（ピアノ線）を 40 本ほどに：①低い株（高さ 1.1 m 以下、93 本）は省く → 48 本（29 株）。
    ②ぬし・外周（凸包から 0.9 m 以内）・ホールの東西の筋（縁側から見通す y−37・−39・−41 の線から 0.45 m 以内）は残す。
    ③残りの内側の株を、奥（凸包から遠い順）に、本数が n_target 以下になるまで省く。戻り：(株の全部, 選んだ株, 省いた株)"""
    from shapely.geometry import MultiPoint, Point as _Pt
    pts = []
    for nm, g in _pf('55_ホール_北山杉の林'):
        b = _bb(g); pts.append(dict(x=(b[0] + b[3]) / 2, y=(b[1] + b[4]) / 2, h=b[5], name=nm))
    units = []
    for p in pts:
        for u in units:
            if math.hypot(u['x'] - p['x'], u['y'] - p['y']) < 350:
                u['n'] += 1; u['h'] = max(u['h'], p['h']); break
        else:
            units.append(dict(p, n=1))
    hull = MultiPoint([(u['x'], u['y']) for u in units]).convex_hull
    tall = [u for u in units if u['h'] > 2400]
    for u in tall:
        u['depth'] = hull.exterior.distance(_Pt(u['x'], u['y']))
        if u['name'].startswith('ぬし'): u['why'] = 'ぬし'
        elif u['depth'] < 900: u['why'] = '外周'
        elif any(abs(u['y'] - y) < 450 for y in (-37.0e3, -39.0e3, -41.0e3)): u['why'] = '筋'
        else: u['why'] = '内側'
    sel = list(tall); dropped = []
    for u in sorted([u for u in tall if u['why'] == '内側'], key=lambda u: -u['depth']):
        if sum(x['n'] for x in sel) <= n_target: break
        sel.remove(u); dropped.append(u)
    return units, sel, dropped

def dai_sheets():
    from shapely.geometry import LineString
    F = dai_features()
    holes = unary_union([F['本館の穴']['geom'].buffer(-DAI_HOLE_SHRINK / S, join_style=2), F['西館の穴']['geom'].buffer(-DAI_HOLE_SHRINK / S, join_style=2)])
    hole_keep = unary_union([F['本館の穴']['geom'], F['西館の穴']['geom']]).buffer(0)
    mound_main = F['_mound_polys'][0]
    s = Sheet('01台_表面_シナ3', 841, 594, 'シナ 3 A1：台の表面（GL）。赤＝切る（建物の穴・外形・塀の足の溝）、青＝彫る（必須）、青の別グループ「彫る（青）重要」＝重要。仮（10-31 夜、必須・重要の判断と T7 の結果で直す）')
    s.add(box(0, 0, 841, 594), 'ref')
    s.add_layer('eng2', '#0000FF', 5, 'ENGRAVE_blue_important', '彫る（青）重要')
    s.add_layer('cut2', '#FF0000', 1, 'CUT_red_important', '切る（赤）重要の塀・柵の足の溝')
    s.tabs = False
    T = dai_tx
    def line_geoms(g):
        return [x for x in getattr(g, 'geoms', [g]) if not x.is_empty]
    # 切る：建物の穴・外形
    for h in getattr(holes, 'geoms', [holes]):
        if h.area > 1e6: s.add(T(Polygon(h.exterior)).buffer(0), 'cut')
    s.add(T(F['台の外形']['geom']), 'cut')
    # 彫る
    n_eng = {}
    for k, v in F.items():
        if k.startswith('_') or v['kind'] != 'line' or v['prio'] == '（省く）': continue
        g = v['geom'].difference(hole_keep.buffer(0)) if k not in ('道路の縁',) else v['geom']
        lay = 'eng' if v['prio'] == '必須' else 'eng2'
        for x in line_geoms(g):
            if x.geom_type in ('LineString', 'LinearRing', 'MultiLineString'): s.add(T(x), lay)
        n_eng[k] = (v['prio'], round(g.length * S, 1))
    # 木の位置（手でドリルの十字）
    marks = {'必須': 0, '重要': 0, '築山の上': 0, '穴の中': 0}
    must_trees = lambda t: (t['phi'] >= 280) or t['name'] == 'お向かいの張り出しの木'
    for t in F['_trees']:
        pt = Point(t['x'], t['y'])
        if pt.within(mound_main) and t['base'] > -100:           # バルサの一段目（GL+0.2 m）より上に立つ木は、表面でなくバルサの面に立てる
            marks['築山の上'] += 1; continue
        if pt.within(hole_keep.buffer(-200)):
            marks['穴の中'] += 1; continue
        k = '必須' if must_trees(t) else '重要'
        marks[k] += 1
        c = T(pt).coords[0]; h = DAI_TREE_MARK / 2
        for seg in (LineString([(c[0] - h, c[1]), (c[0] + h, c[1])]), LineString([(c[0], c[1] - h), (c[0], c[1] + h)])):
            s.add(seg, 'eng' if k == '必須' else 'eng2')
    # 塀・柵の足の溝
    n_slot = {'必須': 0, '重要': 0}; n_skip = []
    outline_m = T(F['台の外形']['geom']); outline_m = outline_m if outline_m.geom_type == 'Polygon' else max(outline_m.geoms, key=lambda g: g.area)
    for nm_, ln, pr, _ in dai_fence_runs(F):
        L = T(ln); ps = dai_slot_positions(L)
        if min(outline_m.exterior.distance(p) for p in ps) < 2.5:            # 台の縁に重なる柵（公園の鉄柵）は溝にできない
            n_skip.append(nm_); continue
        for p in ps:
            d = L.project(p)
            s.add(dai_slot_geom(L, d, DAI_SLOT_W, DAI_SLOT_LEN), 'cut' if pr == '必須' else 'cut2')
            n_slot[pr] += 1
    # 北の矢印と文字（参考）
    b_ = T(F['台の外形']['geom']).bounds
    print('台の外形（模型 mm）', round(b_[2] - b_[0]), '×', round(b_[3] - b_[1]), '／ A1 841×594')
    s.save([(8, 8, '台の表面 シナ3（仮）：赤＝切る、青＝彫る（必須）、「彫る（青）重要」のグループ＝重要。北は右上。足の溝の幅は T7 の結果で決める', 4)])
    # 溝の試し片
    dai_trial()
    return n_eng, marks, n_slot, ('台の縁に重なり溝にしない柵', n_skip)

def dai_trial():
    """塀の足の溝の幅の試し片（シナ 3 の端、70×30）。描く幅 0.4・0.5・0.6 を各 3 本（長さ 4.0）＋ 航空ベニヤ 0.6 の足つきの帯（別の色＝別の出力）。
    シナ 3 の出力は T2 の結果（速度 12・16%）。穴に足（厚 0.6・2 mm 深）が差さるか、立って揺れないかを見る"""
    s = Sheet('01台_溝の試し片_シナ3', 70, 40, 'シナ 3 の端：塀の足の溝 描く幅 0.4・0.5・0.6（各 3 本、長さ 4.0）。橙＝航空ベニヤ 0.6 の足つきの帯（別の板で）。速度 12・出力 16%（T2）')
    s.add(box(0, 0, 70, 40), 'ref')
    s.add_layer('cut2', TRY['色']['2'], 30, 'CUT_2', '切る・出力2（航空ベニヤ 0.6 の帯）')
    s.tabs = False
    texts = []
    for i, w in enumerate((0.4, 0.5, 0.6)):
        y = 36 - i * 5
        for j in range(3):
            x = 6 + j * 8
            s.add(box(x, y - w / 2, x + DAI_SLOT_LEN, y + w / 2), 'cut')
        for l in label_num(i + 1, 1.0, y - 1.0, 2.0): s.add(l, 'eng')
        texts.append((30, y - 0.5, f'{i + 1}：描く幅 {w}', 2))
    # 足つきの帯：高さ 6、足 4.0×2.0（実際の足）、おき 8
    body = box(0, 4, 60, 10)
    feet = [box(5 + k * 8, 2, 5 + k * 8 + DAI_SLOT_LEN, 4) for k in range(7)]
    s.add(unary_union([body] + feet).buffer(0), 'cut2')
    texts.append((1, 11.5, '橙：航空ベニヤ 0.6 の帯（足 4.0×2.0・おき 8）', 2))
    s.save(texts)

if __name__ == '__main__':
    if sys.argv[1:2] == ['dai']:                       # 台の表面だけ（ほかの部品は書き換えない）
        print(dai_sheets()); sys.exit(0)
    # 01〜06（試し切り・本館の架構・床・ベタ基礎・屋根）は切った部品なので作り直さない（ユーザー 10-28、CUT_DONE）
    print('西館の架構', west_sheets())
    print('本館の外壁', wall_sheets())
    print('06c・11 小屋と機械室', hut_kikai_sheets())
    print('西館の屋根', west_roof_sheets())
    print('室内の壁', interior_sheets())
    print('ok', OUT)
