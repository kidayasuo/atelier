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
TENON_L = 5.5                             # 布基礎 3＋中の層 3 より短く
FLOOR_CLR = J['床']['柱の穴のあき']         # 0.1
KETA = (2.0, 4.0)                         # 平竹ひご 2×4
# 描く穴の寸法（短辺×長辺）。ひごの実測 10-23：短辺 1.97〜1.99（節で 2.03〜2.05）、長辺 約 3.90。
# レーザーの切り幅（約 0.1〜0.2）で、切れた穴はこれより大きくなる。
KETA_VARIANTS = {k: tuple(v) for k, v in zip('ABCD', J['桁']['穴_試し'])}   # 描く寸法（切り幅 0.2 で実寸は +0.2）
FLOOR_T = 1.74                             # 床の柱の穴の幅（柱の厚さ方向、試し切りで決める）
MORTISE_T = 1.64                          # ほぞ穴の幅（柱の厚さ方向、試し切りで決める）
MORTISE_W = TENON_W - 0.3     # 2.1：切り幅 0.2 でほぞ（実寸 2.2）に対して穴は 2.3
FLOOR_L = 3.8                 # 床の柱の穴の長さ：柱の幅 4.0 は実寸 3.8、穴は実寸 4.0

m = r.File3dm.Read(M3)
LAY = {l.Name: i for i, l in enumerate(m.Layers)}
def objs(name):
    return [o.Geometry for o in m.Objects if o.Attributes.LayerIndex == LAY[name]]

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
        n = 2 if isinstance(s, r.LineCurve) else 60
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
class Sheet:
    def __init__(self, name, w, h, note):
        self.name, self.w, self.h, self.note = name, w, h, note
        self.cut, self.eng, self.ref = [], [], []
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
    TAB_GAP = 0.5      # つなぎ（タブ）：描く切れ目の長さ。切り幅 0.2 で、残る木は約 0.3
    TAB_MAX = 250      # これより小さい部品の外形に 2 か所のつなぎ（大きい板は付けない）
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
                ext = LineString(p.exterior.coords); Lx = ext.length; h = self.TAB_GAP / 2
                cuts = sorted([Lx * 0.25, Lx * 0.75])
                segs = [substring(ext, cuts[0] + h, cuts[1] - h), substring(ext, cuts[1] + h, Lx), substring(ext, 0, cuts[0] - h)]
                out += segs
                out += [LineString(i.coords) for i in p.interiors]
        return out

    def save(self, texts=()):
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
    segs = {'1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', 'A': 'efabcg', 'B': 'fedcg', 'C': 'afed', 'D': 'bcdeg'}
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
    for k, c in KETA_VARIANTS.items():
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


# ================= 4・5. 本館の床（1.7×2）と布基礎（3） =================
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
    dosoku = unary_union([plan('14_本館_外縁側（土足 −150）'), plan('15_本館_海峡（土足 −150）')]).intersection(A)
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
    s = Sheet('04_本館の床_シナ1.7', 841, 594, 'シナ 1.7 A1：本館の床 上の層（はだし）と下の層（はだし＋土足）。柱の穴 4.0×1.89')
    s.add(box(0, 0, 841, 594), 'ref')
    s.add(affinity.translate(U, 8, 8))
    s.add(affinity.translate(Lw, 8, 8 + h + 8))
    s.save([(8, 8 + 2 * (h + 8) + 4, '下：上の層（はだし ±0）　上：下の層（はだし＋外縁側・海峡）　受け取り土間は 2 枚とも無し', 4),
            (8, 8 + 2 * (h + 8) + 10, f'3 段目（{h:.0f} mm）は屋根の下の層のために空けておく', 4)])
    s = Sheet('05_本館の布基礎_シナ3', 841, 594, 'シナ 3 A1：本館の布基礎（床の外形＋受け取り土間）。ほぞ穴 2.4×1.79')
    s.add(box(0, 0, 841, 594), 'ref')
    s.add(affinity.translate(F, 8, 8))
    s.save([(8, h + 16, f'本館の布基礎（{w:.0f}×{h:.0f} mm）。残りは敷地・西館の布基礎に使う', 4)])
    return w, h

if __name__ == '__main__':
    test_sheets()
    frame_sheets()
    print('本館の床', floor_sheets())
    print('ok', OUT)
