"""育ち舎 1/100 模型：レーザーカッター用のデータを 3dm から作る（模型作成のチャット）。

入力：model/sodachiya_exact_mesh.3dm、data/mokei.json
出力：mokei/cut/*.svg と *.dxf（Illustrator で開く。1 単位 = 1 mm、実寸）
色：赤 #FF0000 = 切る、青 #0000FF = 彫る（線）、黒 = 参考（切らない、レーザーに送る前に消す）

  python3 sodachiya/mokei/laser.py
"""
import json, math, os, re, sys
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
        return 0.35 if self.name.startswith(('01_試し切り_T1', '02_', '03', '07_', '11b_機械室')) else self.TAB_GAP
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
    show_used = False   # 11-02：詰めた板は、説明文に「使う大きさ」（外接矩形、板の左上から、マージン込み）を書く
    def to_top_left(self, texts):
        from shapely.ops import unary_union as _uu
        if getattr(self, 'no_shift', False): return texts               # 別のファイルと同じ原点に合わせる（座標を最初から板の座標で渡す）
        keys = [k for k, *_ in self.layers if k != 'ref' and getattr(self, k)]
        allg = [g for k in keys for g in getattr(self, k)]
        if not allg: return texts
        b = _uu([g.envelope if g.geom_type != 'Point' else g for g in allg]).bounds
        dx, dy = self.MARGIN - b[0] + getattr(self, 'extra_dx', 0.0), (self.h - self.MARGIN) - b[3]
        self.used = (round(b[2] - b[0] + self.MARGIN, 1), round(b[3] - b[1] + self.MARGIN, 1))
        for k in keys:
            setattr(self, k, [affinity.translate(g, dx, dy) for g in getattr(self, k)])
        self.tab_pts = [affinity.translate(q, dx, dy) for q in self.tab_pts]
        return [(x + dx, y + dy, t, sz) for x, y, t, sz in texts]

    def save(self, texts=()):
        if self.name.startswith(CUT_DONE):
            print('  切った部品なので書き出さない：', self.name); return
        texts = self.to_top_left(list(texts))
        if self.show_used and getattr(self, 'used', None):
            uw, uh = self.used
            self.note += f'。使う大きさ{uw:g}×{uh:g} mm（板の左上から、マージン{self.MARGIN:g}込み。端材からこの大きさを切り出して使う）'
            texts.append((self.MARGIN, self.h - uh - 4, f'使う大きさ{uw:g}×{uh:g} mm（左上から、マージン込み）', 3))
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
        if texts:
            L.append('<g id="参考の文字（送る前に消す）" fill="#000000" stroke="none" font-family="sans-serif">')
            for x, y, t, sz in texts:
                L.append(f'<text x="{x:.2f}" y="{H - y:.2f}" font-size="{sz}">{t}</text>')
            L.append('</g>')
        L.append('</svg>')
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

# ---------- 詰め方：部品の位置だけを動かして、外接矩形を最小にする（11-02、ユーザー：端材から必要な大きさだけ切り出せるように） ----------
# 形・向き・数は変えない。位置だけ（回さない）。部品どうしの輪郭の距離≥gap（穴の中には入れない：外形で測る）。
# 手順：格子（res mm）に外形をgap/2だけ太らせて写し、左上から「スカイライン」で詰める（幅または高さを固定して、順番を変えて何度も）
#       → 外接矩形の面積が最小のものを選ぶ（同じなら辺の短いほう）→ 輪郭（Shapely）で左・上へ寄せ直す → 距離を測り直して確かめる。
import random as _random

def _nest_hull(g):
    """衝突に使う形：外形（穴は埋める）。複数の部品なら、それぞれの外形の集まり"""
    ps = [Polygon(p.exterior) for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon' and not p.is_empty]
    return ps[0] if len(ps) == 1 else MultiPolygon(ps) if ps else g

class _NestPiece:
    def __init__(self, hull, res, gap):
        import shapely
        h = affinity.scale(hull, 1, -1, origin=(0, 0))               # 計算はy下向き（左上が原点）
        b = h.bounds
        self.dx, self.dy = -b[0], -b[1]
        h = affinity.translate(h, self.dx, self.dy)
        self.hull = h
        self.w, self.h = b[2] - b[0], b[3] - b[1]
        self.area = h.area
        d = gap / 2 + res * 0.7072
        self.mc = int(math.ceil(d / res)) + 1
        nc = int(math.ceil(self.w / res)) + 2 * self.mc + 1
        nr = int(math.ceil(self.h / res)) + 2 * self.mc + 1
        xs = (np.arange(nc) + 0.5) * res - self.mc * res
        ys = (np.arange(nr) + 0.5) * res - self.mc * res
        X, Y = np.meshgrid(xs, ys)
        mask = shapely.contains_xy(h.buffer(d, quad_segs=4), X, Y)
        self.dn = self._prof(mask, self.w, self.h)                   # 下へ伸ばす：列ごとの上端・下端
        self.up = self._prof(mask[::-1], self.w, self.h)             # 上へ伸ばす（板の底に積む）：上下を反転して同じ手順
        self.rt = self._prof(mask.T, self.h, self.w)                 # 右へ伸ばす：行ごとの左端・右端（転置して同じ手順）
        self.lf = self._prof(mask.T[::-1], self.h, self.w)           # 左へ伸ばす（右の端に積む）
    @staticmethod
    def _prof(m, ext_fixed, ext_grow):
        nr, nc = m.shape
        idx = np.nonzero(m.any(axis=0))[0]
        T = np.argmax(m[:, idx], axis=0)                              # 列の上端の行
        B = nr - 1 - np.argmax(m[::-1, idx], axis=0)                  # 列の下端の行
        return dict(idx=idx, T=T, B=B, wm=nc, f=ext_fixed, g=ext_grow)

_SKY_ATTR = {'down': 'dn', 'up': 'up', 'right': 'rt', 'left': 'lf'}
def _sky_pack(pcs, order, res, cap_f, cap_g, mode, crit, best_area=None):
    """スカイライン。mode='down'：幅cap_f固定で上の端から下へ積む（高さcap_gまで）／'up'：下の端から上へ積む／'right'：高さcap_f固定で左の端から右へ（幅cap_gまで）／'left'：右の端から左へ。
    戻り：[(x, y)]（部品の外接矩形の左上、mm、y下向き）、(使う幅, 使う高さ)。入らなければNone"""
    from numpy.lib.stride_tricks import sliding_window_view
    mcm = max(p.mc for p in pcs)
    nf = int(math.floor(cap_f / res)) + 4 * mcm + 6
    S = np.full(nf, -10 ** 6, dtype=np.int64)
    pos = [None] * len(pcs)
    used_f = used_g = 0.0
    for i in order:
        p = pcs[i]; q = getattr(p, _SKY_ATTR[mode])
        mcp = p.mc
        x0 = -mcp; x1 = int(math.floor((cap_f - q['f']) / res + 1e-9)) - mcp
        if x1 < x0: return None
        win = sliding_window_view(S, q['wm'])[mcm + x0: mcm + x1 + 1]       # (候補の数, 部品の幅の格子)
        sw = win[:, q['idx']]
        y0 = np.maximum((sw + 1 - q['T']).max(axis=1), -mcp)
        if crit == 0:
            k = int(np.argmin(y0))                                          # いちばん上（次に左）
        else:
            waste = np.where(sw < -10 ** 5, 0, (y0[:, None] + q['T'] - sw - 1).clip(min=0)).sum(axis=1)
            k = int(np.argmin(y0 * 1000.0 + waste if crit == 1 else waste * 1000.0 + y0))
        y = int(y0[k]); x = x0 + k
        gend = (y + mcp) * res + q['g']
        if gend > cap_g + 1e-9: return None
        seg = S[mcm + x: mcm + x + q['wm']]
        seg[q['idx']] = np.maximum(seg[q['idx']], y + q['B'])
        fpos = (x + mcp) * res; gpos = (y + mcp) * res
        pos[i] = (fpos, gpos)
        used_f = max(used_f, fpos + q['f']); used_g = max(used_g, gend)
        if best_area is not None and used_f * used_g > best_area * 1.002: return None
    # 反転・転置を元に戻す（使う矩形の左上が(0, 0)）
    out = []
    for p, (f_, g_) in zip(pcs, pos):
        if mode == 'down': out.append((f_, g_))
        elif mode == 'up': out.append((f_, used_g - g_ - p.h))
        elif mode == 'right': out.append((g_, f_))
        else: out.append((used_g - g_ - p.w, f_))
    return out, ((used_f, used_g) if mode in ('down', 'up') else (used_g, used_f))

def _nest_orders(pcs):
    n = len(pcs); idx = range(n)
    o = [sorted(idx, key=lambda i: (-pcs[i].h, -pcs[i].w)),
         sorted(idx, key=lambda i: (-pcs[i].w, -pcs[i].h)),
         sorted(idx, key=lambda i: -pcs[i].area),
         sorted(idx, key=lambda i: (-max(pcs[i].w, pcs[i].h), -min(pcs[i].w, pcs[i].h))),
         sorted(idx, key=lambda i: -(pcs[i].w * pcs[i].h)),
         sorted(idx, key=lambda i: (-pcs[i].area / max(1.0, pcs[i].w * pcs[i].h), -pcs[i].h))]
    out = []
    for x in o:
        if x not in out: out.append(x)
    return out

def _nest_exact_ok(hs, pos, gap):
    from shapely.strtree import STRtree
    gs = [affinity.translate(h, x, y) for h, (x, y) in zip(hs, pos)]
    t = STRtree(gs)
    for i, g in enumerate(gs):
        for j in t.query(g.buffer(gap)):
            if j > i and g.distance(gs[j]) < gap - 1e-6: return False
    return True

def _nest_compact(pcs, pos, gap, passes=40, step=0.25, reach=4.0):
    """輪郭（Shapely）で、部品を左へ・上へ寄せ直す（格子の余りを詰める）。ほかの部品との距離≥gapを保つ"""
    pos = [list(p) for p in pos]
    gs = [affinity.translate(p.hull, x, y) for p, (x, y) in zip(pcs, pos)]
    bb = [g.bounds for g in gs]
    def free(i, g):
        gb = g.bounds
        for j in range(len(gs)):
            if j == i: continue
            b = bb[j]
            if b[0] - gap > gb[2] or b[2] + gap < gb[0] or b[1] - gap > gb[3] or b[3] + gap < gb[1]: continue
            if g.distance(gs[j]) < gap - 1e-9: return False
        return True
    for _ in range(passes):
        moved = 0.0
        for i in sorted(range(len(pcs)), key=lambda i: (pos[i][0] + pos[i][1], pos[i][1])):
            for ddx, ddy in ((-1, 0), (0, -1), (-1, -1)):
                t = 0.0
                while t + step <= reach:
                    nx, ny = pos[i][0] + ddx * (t + step), pos[i][1] + ddy * (t + step)
                    if nx < -1e-9 or ny < -1e-9: break
                    if not free(i, affinity.translate(pcs[i].hull, nx, ny)): break
                    t += step
                lo, hi = t, t + step
                if t + step <= reach:
                    for _k in range(6):
                        mid = (lo + hi) / 2
                        nx, ny = pos[i][0] + ddx * mid, pos[i][1] + ddy * mid
                        if nx >= -1e-9 and ny >= -1e-9 and free(i, affinity.translate(pcs[i].hull, nx, ny)): lo = mid
                        else: hi = mid
                if lo > 0:
                    pos[i][0] += ddx * lo; pos[i][1] += ddy * lo
                    gs[i] = affinity.translate(pcs[i].hull, pos[i][0], pos[i][1]); bb[i] = gs[i].bounds
                    moved += lo
        if moved < 0.05: break
    return [tuple(p) for p in pos]

def nest(shapes, W, H, gap, top=0.0, res=0.5, trials=None, verbose=False, seed=1, nsteps=24, norders=4, crits=(0, 1)):
    """shapes：部品の形（衝突を測る形。穴は無視。複数の部品のかたまりでもよい）のリスト。W×H：使ってよい最大の外接矩形。
    戻り：([(tx, ty)]、部品を動かす量（元の形のまま。使う矩形の左上がx＝0・y＝top）)、(使う幅, 使う高さ)。面積が最小、同じなら辺の短いほう"""
    hulls = [_nest_hull(g) for g in shapes]
    n = len(hulls)
    if n > 40: nsteps = min(nsteps, 14); norders = min(norders, 3)       # 部品が多いと1回が重いので、探す幅を絞る
    pcs = [_NestPiece(h, res, gap) for h in hulls]
    mw = max(p.w for p in pcs); mh = max(p.h for p in pcs)
    if mw > W + 1e-9 or mh > H + 1e-9: raise RuntimeError(f'板に入らない：部品の最大{mw:.1f}×{mh:.1f}が{W:.0f}×{H:.0f}より大きい')
    rnd = _random.Random(seed)
    ords = _nest_orders(pcs)[:norders]
    # 固定する幅・高さの候補：細かい刻み＋同じ大きさの部品の段の組み合わせ
    def cands(lo, hi, sizes):
        c = set(lo + k * max(res, (hi - lo) / nsteps) for k in range(nsteps + 1)) | {hi}
        for k in range(1, 9):
            for s_ in sorted(set(round(s, 1) for s in sizes))[-8:]:
                if k * s_ + (k - 1) * gap + 0.5 <= hi: c.add(k * s_ + (k - 1) * gap + 0.5)
        return sorted(v for v in c if v >= lo - 1e-9)
    cw = cands(mw, W, [p.w for p in pcs]); chh = cands(mh, H, [p.h for p in pcs])
    best = [None]
    def run(mode, c, order, crit):
        capf, capg = (c, H) if mode in ('down', 'up') else (c, W)
        r_ = _sky_pack(pcs, order, res, capf, capg, mode, crit, best[0][0] if best[0] else None)
        if r_ is None: return False
        pos, (uw, uh) = r_
        key = (round(uw * uh, 1), max(uw, uh))
        if best[0] is None or key < best[0][1]:
            best[0] = (uw * uh, key, pos, mode, c, list(order), crit)
            return True
        return False
    for o in ords:
        for crit in crits:
            for md in ('down', 'up'):
                for c in cw: run(md, c, o, crit)
            for md in ('right', 'left'):
                for c in chh: run(md, c, o, crit)
    if trials is None: trials = int(min(1200, max(60, 12000 / (n + 4))))
    for t in range(trials):
        _, key, pos, mode, c, o, crit = best[0]
        o = list(o)
        for _m in range(rnd.choice((1, 1, 2, 3))):
            a = rnd.randrange(n); b = rnd.randrange(n)
            if rnd.random() < 0.5: o[a], o[b] = o[b], o[a]
            else: o.insert(b, o.pop(a))
        m2 = mode if rnd.random() < 0.8 else rnd.choice(('down', 'up', 'right', 'left'))
        uw, uh = max(x + p.w for (x, y), p in zip(pos, pcs)), max(y + p.h for (x, y), p in zip(pos, pcs))
        vert = m2 in ('down', 'up')
        base = uw if vert else uh
        lo = (mw if vert else mh)
        c2 = min(W if vert else H, max(lo, base + rnd.uniform(-0.15, 0.1) * base))
        run(m2, c2, o, rnd.choice((crit, 0, 1, 2)))
    if best[0] is None: raise RuntimeError('詰められない（板に入らない）')
    _, key, pos, mode, c, o, crit = best[0]
    pos = _nest_compact(pcs, pos, gap)
    x0 = min(x for x, y in pos); y0 = min(y for x, y in pos)
    pos = [(x - x0, y - y0) for x, y in pos]
    uw = max(x + p.w for (x, y), p in zip(pos, pcs)); uh = max(y + p.h for (x, y), p in zip(pos, pcs))
    assert _nest_exact_ok([p.hull for p in pcs], pos, gap), '距離が足りない'
    if verbose: print('nest', n, mode, round(c, 1), 'crit', crit, '->', round(uw, 1), round(uh, 1), round(uw * uh))
    # 元の形（y上向き）を動かす量：x＝dx＋x、y＝top−(最大のy)−y
    return [(p.dx + x, top - p.dy - y) for (x, y), p in zip(pos, pcs)], (uw, uh)

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

# ================= 4b. 0・1歳の東の外縁側の床の帯（11-02、10-31 の決定で足された所） =================
EDGE_GAP = 10.0     # 04 の端から離す（世界 mm＝模型 0.1 mm）

def engawa_strip():
    """3dm のレイヤー13「0・1歳の東の縁側（杉の床板）」8 枚の外形の和。切った 04 上の層の外形（kirita.cut_floor('upper')）の端から 0.1 mm 離す。
    下の層は、切った 04 下がすでに外縁側（f1〜5、v 0〜1.5 m）まで入っているので作らない。
    返す：(外形（世界座標）, 04 から離す前の外形, 柱の穴, 04 の外形)"""
    polys = []
    for nm, g in objs_named('13_本館_内縁側（はだし ±0）'):
        if '東の縁側' not in nm or not isinstance(g, r.Extrusion): continue
        c = g.Profile3d(0, 0)
        polys.append(Polygon([(c.Points[i].X, c.Points[i].Y) for i in range(len(c.Points))]).buffer(1, join_style=2))
    raw = unary_union(polys).buffer(-1, join_style=2).simplify(1)
    import kirita as _K
    f04 = _K.cut_floor('upper')                              # 切った 04 上の実際の外形（3dm の floors() ではない。11-02）
    strip = raw.difference(f04.buffer(EDGE_GAP, join_style=2))
    strip = max(getattr(strip, 'geoms', [strip]), key=lambda x: x.area)
    holes = [h for h in (col_rect(g, FLOOR_L, FLOOR_T) for g in cols) if h.intersects(raw)]
    return strip, raw, holes, f04

def engawa_sheets():
    """04b：0・1歳の東の外縁側の帯。上の層だけの 1.7 を 1 枚（柱の穴つき）。04 と同じ向きで、SVG のみ・参考の黒なし"""
    strip, raw, holes, f04 = engawa_strip()
    # 向きは帯の長辺を水平に（弧の上の 12 m なので、04 の板の向きだと斜めになる）
    rc = list(strip.minimum_rotated_rectangle.exterior.coords)
    e = max(zip(rc[:-1], rc[1:]), key=lambda pq: math.hypot(pq[1][0] - pq[0][0], pq[1][1] - pq[0][1]))
    ang = -math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0])
    P = to_sheet(strip.difference(unary_union(holes)) if holes else strip, ang, (0, 0))
    b = P.bounds
    P = affinity.translate(P, -b[0], -b[1])
    w, h = P.bounds[2], P.bounds[3]
    # つなぎは、外形のうち長い辺の側（世界で v≧14.95）の 25%・75% の所
    from shapely.geometry import LineString
    sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
    from uv import RW, TH_S
    ext = list(strip.exterior.coords)
    top = []
    for p, q in zip(ext[:-1], ext[1:]):
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        if (RW - math.hypot(mx - CX, my - CY)) / 1000 > 14.95:
            top.append(Point((mx, my)))
    top.sort(key=lambda q: math.atan2(q.y - CY, q.x - CX))
    sel = [top[round((len(top) - 1) * f)] for f in (0.25, 0.75)]
    sel = [affinity.translate(to_sheet(q, ang, (0, 0)), -b[0], -b[1]) for q in sel]
    M = Sheet.MARGIN
    s = Sheet('04b_0・1歳の外縁側の床_シナ1.7', w + 2 * M, h + 2 * M, 'シナ 1.7：0・1歳の東の外縁側の床の帯（上の層だけ 1 枚。下の層は切った 04 下に入っている）。切った 04 上の端から 0.1 mm 離す')
    s.add(P)
    s.tab_pts = sel
    s.save()
    return dict(w=round(w, 2), h=round(h, 2), sheet=(round(w + 2 * M, 1), round(h + 2 * M, 1)), holes=len(holes))

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
        if not (nm_ == '' or nm_.startswith('骨格の柱')):
            continue                                        # 架構の柱（名前なし）とキッチンの東の骨格の柱だけ（west_cols と同じ）。階段の箱の 120 角の柱（ユーザー 10-28）・壁の中の 120 角の柱・柱の受け材は作らない
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
            if nm_ != '':
                continue                                    # 架構の梁（名前なし）だけ。出し梁・北西の角の一枚の梁 u43.5（10-28）・腕木・楔の受け材は 07 に入れない
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
    # 詰める（11-02）：外接矩形が最小になるように位置だけを動かす（向きは元のまま：柱は縦、梁は横）。入らなければ棚に並べる（高い順、板は590×295を使う）
    W, H, gap = 590, 295, 1.6
    items.sort(key=lambda it: (-(it[2].bounds[3]), it[0]))
    try:
        mv, (uw, uh) = nest([it[2] for it in items], 600 - 2 * Sheet.MARGIN, 300 - 2 * Sheet.MARGIN, gap, top=H)
        sheets = [[(it, tx, ty) for it, (tx, ty) in zip(items, mv)]]
    except RuntimeError:
        sheets = [[]]; x = y = rowh = 0
        for it in items:
            w, h = it[2].bounds[2], it[2].bounds[3]
            if x + w > W:
                x = 0; y += rowh + gap; rowh = 0
            if y + h > H:
                sheets.append([]); x = y = rowh = 0
            sheets[-1].append((it, x, H - y - h)); x += w + gap; rowh = max(rowh, h)
    for si, lst in enumerate(sheets):
        s = Sheet(f'07_西館の架構_{si + 1}_航空ベニヤ0.8', 600, 300,
                  f'航空ベニヤ 0.8 300×600：西館の架構（柱は 2 枚で 1 本、梁・2 階の床梁は 2 枚で柱を挟む）桁の穴 D。番号＝架構（南から）。向きは元のまま、外接矩形が最小になるように詰めた（部品の間{gap} mm以上）')
        s.show_used = True
        s.add(box(0, 0, 600, 300), 'ref')
        for (nm, k, g, tp), x, y in lst:
            q = affinity.translate(g, x, y)
            s.add(q)
            if tp: s.tab_pts += [affinity.translate(t, x, y) for t in tp]
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
    s = Sheet('08_本館の外壁_航空ベニヤ1.0', 600, 300, '航空ベニヤ 1.0 300×600：本館の外壁（西は弧を展開、北の妻、南の妻の西の端）。天端は梁の上面。大和張りの線は彫り。向きは元のまま、外接矩形が最小になるように詰めた（板どうし4 mm以上）')
    s.show_used = True
    s.add(box(0, 0, 600, 300), 'ref')
    # 部品＝ひと続きの板。戸のすき間などで離れた板（西の外壁は2枚＋かけら）は別々に動かす。4 mmより近い板（かけらなど）は、今の並びのまま1組。
    # 大和張りの線は壁ごとの位置（左端から1.35・1.05の交互）のまま、組ごとに分ける
    gap = 4.0
    pieces = []
    for k in ('西の外壁', '北の妻', '南の妻の西の端'):
        g = W[k]; ps = list(getattr(g, 'geoms', [g])); lines = yamato_lines(g)
        grp = list(range(len(ps)))                                   # 近い板をまとめる（距離<gap）
        for i in range(len(ps)):
            for j in range(i):
                if ps[i].distance(ps[j]) < gap and grp[i] != grp[j]:
                    old = grp[i]; grp = [grp[j] if v == old else v for v in grp]
        groups = sorted(set(grp), key=lambda v: min(ps[i].bounds[0] for i in range(len(ps)) if grp[i] == v))
        for gi, v in enumerate(groups):
            mem = [ps[i] for i in range(len(ps)) if grp[i] == v]
            u = unary_union(mem); inner = u.buffer(-0.3)
            ln = [x for x in (l.intersection(inner) for l in lines) if not x.is_empty]
            pieces.append((k if len(groups) == 1 else f'{k} {gi + 1}/{len(groups)}', u, ln))
    mv, (uw, uh) = nest([p for _, p, _ in pieces], 600 - 2 * Sheet.MARGIN, 300 - 2 * Sheet.MARGIN, gap, top=300)
    texts = []
    for (nm, p, ln), (tx, ty) in zip(pieces, mv):
        q = affinity.translate(p, tx, ty)
        for pp in getattr(q, 'geoms', [q]): s.add(pp)
        for l in ln: s.add(affinity.translate(l, tx, ty), 'eng')
        texts.append((q.bounds[0], q.bounds[1] - 3, nm, 2.5))
    s.save(texts)
    return {k: tuple(round(v, 1) for v in g.bounds[2:]) for k, g in W.items()}


# ================= 8w. 西館の外壁（14w、11-02） =================
# 本館の 08 と同じ作り：航空ベニヤ 1.0 の長い帯（外面の長さで展開、外から見て左→右）、大和張りの線は彫り、開口は切り。
# 形は 3dm の 21（外壁の一つの立体）の外面の三角形を、外皮の輪郭 WS（data/wnew.pkl）の外周の長さ s と高さ z に開いたもの。
# 天端は 3dm の外壁の天端（＝屋根の線＝梁の上面。22b の梁の上端と ±5 mm（北の妻の角で 20 mm）で一致を確かめた）。
# 下端は GL（−300、07 の柱の肩・本館の 08 と同じ）。3dm の外壁は FL（0）から立つが、基礎の立ち上がりは 3dm に描かれていないので、
# 模型はベタ基礎の上（GL）に立て、FL までの 3 mm は帯（開口の下は FL まで）。
# 外周は、北の妻と東の面の角（NE）から反時計回りに：北の妻→北東の丸み→北西の壁→北西の丸み→西の壁→南西の丸み→南の妻→（南東の角）→東の面。
# 丸みは R 約 3.1〜3.3 m（模型 31〜33 mm、内側も 15 mm 以上）なので航空ベニヤ 1.0 を湿らせて巻く。直角の角は南東・北東の 2 か所だけ。
# 帯 A＝北の妻から南の妻まで（大和張り）。帯 B＝東の面（すき間側、大和張りは張らない）。B は A の端の内側に突き当てる（両端を 1.0 ずつ短く）。
WW_TOL = 15.0          # 外面の三角形を拾う許し（外周から、実寸 mm。丸みの弦の矢高は約 3.4）
WW_ARM_W, WW_ARM_H = 150.0, 260.0   # 腕木（鼻母屋を受ける 120×240）の穴：模型に腕木が無いので埋める
WW_SLIT = 25.0         # 水切りの接する所にできる細い隙間（高さ 20）は埋める
WW_SKIRT = 0.0         # 開口の下端は FL（床がある）

def _west_wall_su():
    """(外周の線 ring（反時計回り、NE の角から）, 全周の長さ L, 南東の角の s, (s, z) の平面の外壁の形)"""
    import pickle
    sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
    from uv import uv as uv_
    from shapely.geometry import LineString
    WS = pickle.load(open(os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb'))['WS']
    c = np.array(WS.simplify(0.3).exterior.coords)[:-1]
    k = [0]
    for i in range(1, len(c)):
        if np.hypot(*(c[i] - c[k[-1]])) > 1.0: k.append(i)
    c = c[k]
    if not WS.exterior.is_ccw: c = c[::-1]
    uvs = np.array([uv_(*p) for p in c])
    i0 = int(np.argmin(np.hypot(uvs[:, 0] - 51.0, uvs[:, 1] + 0.9)))        # 北東の角（北の妻と東の面）
    c = np.roll(c, -i0, axis=0)
    ring = LineString(np.vstack([c, c[:1]])); Lr = ring.length
    i1 = int(np.argmin([np.hypot(uv_(*p)[0] - 21.0, uv_(*p)[1] + 0.9) for p in c]))   # 南東の角
    sSE = ring.project(Point(c[i1]))
    g = objs('21_西館_外壁')[0]
    V, F = g.Vertices, g.Faces
    P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
    polys = []
    for j in range(len(F)):
        f = F[j]; q = P[[f[0], f[1], f[2]]]
        n = np.cross(q[1] - q[0], q[2] - q[0]); nn = np.linalg.norm(n)
        if nn < 1e-9 or abs(n[2]) / nn > 0.2: continue                       # 立っている面だけ
        if max(ring.distance(Point(p[0], p[1])) for p in q) > WW_TOL: continue   # 外面だけ（内面は 150 内、水切りは 30 外）
        s = np.array([ring.project(Point(p[0], p[1])) for p in q])
        if s.max() - s.min() > Lr / 2: s = np.where(s > Lr / 2, s - Lr, s)      # 北東の角をまたぐ三角形
        pg = Polygon([(s[i], q[i, 2]) for i in range(3)])
        if pg.area > 1e-3: polys.append(pg.buffer(0.01))
    U = unary_union(polys).buffer(-0.01)
    def _clean(p_):                                      # 3dm の作り直しで外壁が 2 つ以上の塊になったことがある（11-02）：塊ごとに、細いすき間と小さな穴を埋める
        return Polygon(p_.exterior, [h for h in p_.interiors
                                     if not (min(Polygon(h).bounds[2] - Polygon(h).bounds[0], Polygon(h).bounds[3] - Polygon(h).bounds[1]) <= WW_SLIT
                                             or (Polygon(h).bounds[2] - Polygon(h).bounds[0] < WW_ARM_W and Polygon(h).bounds[3] - Polygon(h).bounds[1] < WW_ARM_H))])
    U = unary_union([_clean(p_) for p_ in getattr(U, 'geoms', [U]) if p_.area > 1.0])
    U = U.union(box(-0.5, GL, Lr + 0.5, 1.0))           # GL から FL までの帯（開口の下は FL まで）
    return ring, Lr, sSE, U

WW_MIZUKIRI_Z = 3260.0      # 水切り（2 階の床の高さ、t20）の高さの中心：彫りの線だけ（南北の妻と丸みだけ）
def west_wall_pieces():
    """帯 A（北の妻→南の妻、大和張り）、帯 B（東の面）。(x 右へ、y 上へ、mm、左下が原点)。返す：dict、水切りの線の (x0, x1) の列"""
    ring, Lr, sSE, U = _west_wall_su()
    sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
    from uv import xy as xy_
    T = T_VENEER / S                                    # 100（実寸 mm）：B は A の端の内側に突き当てる
    parts = {'A': (0.0, sSE), 'B': (sSE + T, Lr - T)}
    out = {}
    for k, (s0, s1) in parts.items():
        g = U.intersection(box(s0, GL - 1, s1, 20000))
        g = affinity.scale(g, S, S, origin=(0, 0)); g = affinity.translate(g, -s0 * S, -GL * S)
        g = unary_union([p for p in getattr(g, 'geoms', [g]) if p.area > 0.5]).simplify(0.02)
        out[k] = g
    # 水切り：南北の妻と丸みの外周の s の範囲（3dm の add_west_south.py の box_：北 u50.08〜51.1、南 u20.9〜23.65）
    mz = []
    for u0, u1, v0, v1 in ((50.08, 51.1, -7.9, -0.92), (20.9, 23.65, -13.1, -0.92)):
        pg = Polygon([xy_(u0, v0), xy_(u1, v0), xy_(u1, v1), xy_(u0, v1)])
        hit = ring.intersection(pg)
        ss = [ring.project(Point(c_)) for g_ in getattr(hit, 'geoms', [hit]) for c_ in g_.coords]
        mz.append((min(ss) * S, max(ss) * S))
    return out, mz

def west_wall_sheets():
    pcs, mz = west_wall_pieces()
    yFL = (0.0 - GL) * S
    s = Sheet('14w_西館の外壁_航空ベニヤ1.0', 600, 300,
              '航空ベニヤ 1.0 300×600：西館の外壁（A＝北の妻→北東の丸み→北西の壁→北西の丸み→西の壁→南西の丸み→南の妻、外から見て左＝北、湿らせて巻く／B＝東の面）。'
              '天端は梁の上面、下端は GL（FL までの 3 mm は帯）。大和張りの線（1.05 間隔）は A だけ彫り。開口は切り（ガラスの面は PET を貼る）。向きは元のまま、外接矩形が最小になるように詰めた（A・Bの間14 mm以上）')
    s.show_used = True
    s.add(box(0, 0, 600, 300), 'ref')
    # 詰める（11-02）：A・Bの位置だけを動かして外接矩形を最小に（向きは元のまま。Aの上の山なりのくぼみにBが入る）。間は今までの14 mm
    items = {}; res = {}
    for k in ('A', 'B'):
        g = pcs[k]; b = g.bounds
        q = affinity.translate(g, -b[0], -b[1])                      # 左下を原点に（この中で、下端y＝0）
        eng = []
        if k == 'A':
            for ln in yamato_lines(q):
                ln = ln.intersection(box(-1, yFL, 700, 400))     # FL までの帯には彫らない
                if not ln.is_empty: eng.append(ln)
            for x0, x1 in mz:
                ln = LineString([(x0 - b[0], (WW_MIZUKIRI_Z - GL) * S), (x1 - b[0], (WW_MIZUKIRI_Z - GL) * S)]).intersection(q.buffer(-0.3))
                if not ln.is_empty: eng.append(ln)
        items[k] = (q, eng)
        res[k] = (round(b[2] - b[0], 1), round(b[3] - b[1], 1), len(getattr(g, 'geoms', [g])))
    mv, (uw, uh) = nest([items[k][0] for k in ('A', 'B')], 600 - 2 * Sheet.MARGIN, 300 - 2 * Sheet.MARGIN, 14.0, top=300)
    texts = []
    for k, (tx, ty) in zip(('A', 'B'), mv):
        q, eng = items[k]
        q = affinity.translate(q, tx, ty)
        for p in getattr(q, 'geoms', [q]): s.add(p)
        for ln in eng: s.add(affinity.translate(ln, tx, ty), 'eng')
        texts.append((q.bounds[0], q.bounds[1] - 5, {'A': 'A 西の外壁一周（左＝北、湿らせて巻く）', 'B': 'B 東の面（すき間側、外から見て左＝南）'}[k], 2.5))
    s.save(texts)
    return res


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

KIKAI_KERF06 = J.get('切り幅', {}).get('航空ベニヤ0.6', 0.20)   # 航空ベニヤ 0.6 の切り幅（T5、11-02 実測 19.85〜19.9 → 0.125）

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
    kw = KIKAI_KERF06 / 2                                                 # 11b（航空ベニヤ 0.6）：戸の開口は切り幅の分だけ小さく描く（片側 0.1）
    wall06 = box(0, 0, L * S, H).difference(box(d0 + kw, -1, d1 - kw, 2100 * S - kw))
    roof = affinity.scale(big, S, S, origin=(0, 0)).buffer(-T_VENEER, join_style=1)   # 壁の内側に落とす（描く形：壁の厚さぶん内へ）
    return wall, roof, dict(L=L * S, H=H, door_x=(d0, d1), seam=s_seam, wall06=wall06)

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
               f'シナ 1.7 の端材（06a を取った帯の右の余り、06a は x {b06a[0]:.0f}〜{b06a[2]:.0f}）：06a の光の筋の穴の東の端を埋める差し込み小片 18（南から 1〜18）、小屋の屋根、機械室の屋根。向きは元のまま、外接矩形が最小になるように詰めた（5 mm以上）')
    s6.show_used = True
    s6.add(box(0, 0, W6, 220), 'ref')
    # 詰める（11-02）：小片18（番号の彫りは小片の左）・小屋の屋根・機械室の屋根の位置だけを動かし、外接矩形を最小に（向きは元のまま）。間は5 mm以上
    items = []                                                       # (切る形, [彫る線], [つなぎの点], [(文字の位置x, y, 文字, 大きさ)]、衝突を測る形)
    for i, (n_, plug, mid) in enumerate(sorted(plugs, key=lambda p: p[0])):
        p = _upright_h(plug.buffer(PLUG_GROW, join_style=2), mid)
        p = place(p, 5, 0)
        b = p.bounds; yc = (b[1] + b[3]) / 2
        eng = []
        for j, ch in enumerate(str(n_)):
            eng += label_num(ch, j * 1.3 - 0.2, yc - 0.55, 1.1)
        tabs = [Point((b[0] + b[2]) / 2, b[1]), Point((b[0] + b[2]) / 2, b[3])]
        lab = unary_union(eng).buffer(0.3, cap_style=2, join_style=2).envelope
        items.append((p, eng, tabs, [], unary_union([p, lab])))
    # 小屋の屋根：平面（a 20.3〜31.3 × d 1.1〜6.3 m）。1/10 の斜めなので d 方向は斜めの長さ。北東（d 小）を上に、a を右に（上から見たまま）
    ra, rd = HUT_ROOF['a'], HUT_ROOF['d']
    Lr, Dr = (ra[1] - ra[0]) * 10, (rd[1] - rd[0]) * 10 * math.sqrt(1 + HUT_ROOF['pitch'] ** 2)
    wall, kroof, kinfo = kikai_parts()
    kh = kroof.bounds[3] - kroof.bounds[1]
    g1 = box(0, 0, Lr, Dr)
    items.append((g1, [], [], [(0, -3, f'小屋の屋根 {Lr:.1f}×{Dr:.2f}（上から見て：上＝北東の軒（低い）、右＝南東）', 2.5)], g1))
    g2 = place(kroof, 0, 0)                                          # 世界の向きのまま（上から見て、上＝北）
    items.append((g2, [], [], [(0, -3, '機械室の屋根（上から見て、上＝北）', 2.5)], g2))
    gap6 = 5.0
    mv, (uw, uh) = nest([it[4] for it in items], W6 - 2 * Sheet.MARGIN, 220 - 2 * Sheet.MARGIN, gap6, top=220)
    for (p, eng, tabs, txs, _), (tx, ty) in zip(items, mv):
        s6.add(affinity.translate(p, tx, ty))
        s6.tab_pts += [affinity.translate(t, tx, ty) for t in tabs]
        for l in eng: s6.add(affinity.translate(l, tx, ty), 'eng')
    t6 = [(0, 220 + 3, '差し込み小片 1〜18（南から）。番号の彫りは小片の左', 2.5)]
    for (p, eng, tabs, txs, _), (tx, ty) in zip(items, mv):
        for x_, y_, t_, z_ in txs:
            bb = affinity.translate(p, tx, ty).bounds
            t6.append((bb[0] + x_, bb[1] + y_, t_, z_))
    s6.save(t6)
    # ---- 11：航空ベニヤ 1.0 ----
    s = Sheet('11_小屋と機械室_航空ベニヤ1.0', 600, 300, '航空ベニヤ 1.0 300×600：園庭の小屋（便所・倉庫・コンポストの枠）と底の開いた箱。屋根は 06c（シナ 1.7）。機械室の壁は 11b（航空ベニヤ 0.6）。向きは元のまま、外接矩形が最小になるように詰めた（板どうし4 mm以上）')
    s.show_used = True
    s.add(box(0, 0, 600, 300), 'ref')
    pend = []                                                       # (形, 文字)：あとで外接矩形が最小になるように詰める（11-02、向きは元のまま、板どうし4 mm以上）
    def put(geom, label):
        pend.append((geom, label))
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
    mv, _ = nest([g for g, _ in pend], 600 - 2 * Sheet.MARGIN, 300 - 2 * Sheet.MARGIN, 4.0, top=300)
    texts = []
    for (g, label), (tx, ty) in zip(pend, mv):
        q = affinity.translate(g, tx, ty)
        s.add(q)
        texts.append((q.bounds[0], q.bounds[1] - 3, label, 2.2))
    s.save(texts)
    # ---- 11b：航空ベニヤ 0.6（機械室の壁。角の半径が 13 mm で 1.0 の板では巻けない） ----
    s2 = Sheet('11b_機械室の壁_航空ベニヤ0.6', 600, 300, '航空ベニヤ 0.6 300×600：機械室（おむすび）の壁。周を 1 枚に展開（大和張り、戸の開口 1.6×2.1）。切り幅 0.20 と仮定し、戸の開口は 0.2 小さく描く。屋根は 06c（シナ 1.7）')
    s2.show_used = True
    s2.add(box(0, 0, 600, 300), 'ref')
    w2 = place(kinfo['wall06'], 0, 300 - kinfo['H'])
    s2.add(w2)
    for ln in yamato_lines(w2):
        s2.add(ln, 'eng')
    s2.save([(0, 300 - kinfo['H'] - 3, f'機械室の壁（周を 1 枚に展開 {kinfo["L"]:.1f}×{kinfo["H"]:.1f}、大和張り、戸の開口 1.6×2.1、継ぎ目は長い辺の真ん中）', 2.2)])
    return dict(hut=hb, kikai=kinfo, roof=(Lr, Dr), frame=(fa, fd, fh), plugs=[(n_, [round(v, 2) for v in p_.bounds]) for n_, p_, m_ in plugs])

# ================= 9. 室内の壁（本館 38） =================
# 10-31 監修の頼み：組み立ては ①間仕切りを床に立てる（壁どうしを半欠きでかみ合わせて自立）→ ②架構を上から下ろす → ③外壁。
# だから間仕切りは、柱（頭の丸みも）と重ならず、梁の下面・桁より低く、架構の下を通れる形でなければならない。
# 板の形と交点は kabe.py。ここは 3dm から板を読み、架構との干渉を測って直す。
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kabe
from shapely.geometry import LineString
from uv import uv as _uv

RW_ = 205017.7                   # 背骨（v 0）の半径 mm
V_EDGE = -0.3423                 # 床 04 の西の端の v（半径 205 360 の弧）
CLEAR_TOP = 50.0                 # 梁の下面・桁の下面との余裕（実寸 mm、模型 0.5 mm）
HOLE_R, HOLE_T = 205.0, 90.0     # 床の柱の穴（実寸の半分：半径方向 4.1／2、接線方向 1.8／2）
PLATE_IN, PLATE_OUT = 87.5, 190.0   # 梁の板が架構の線から占める範囲（接線方向、実寸 mm）
KETA_BANDS = (('西の桁', -100.0, 100.0, 3420.0), ('東の桁', 11900.0, 12100.0, 2420.0))   # v の範囲(mm)・下面の高さ
WALL_KERF = J.get('切り幅', {}).get('航空ベニヤ0.6', kabe.KERF)
_W = J.get('室内の壁', {})
CUT_W = _W.get('切り込みの幅_描く', kabe.T_BOARD - WALL_KERF)      # T5 の結果があれば mokei.json の「室内の壁」に

def _panel_ex(g, hmin=600):
    """薄い壁のメッシュ → 立面の板と、壁の線（A→B、実寸 mm の世界座標）"""
    V, F = g.Vertices, g.Faces
    P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
    c = P[:, :2].mean(0); xy = P[:, :2] - c
    _, _, vt = np.linalg.svd(xy, full_matrices=False); ax, nx = vt[0], vt[1]
    nn = xy @ nx
    T = np.ptp(nn); H = np.ptp(P[:, 2])
    if T > 250 or H < hmin: return None
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
    base = c + nx * (nn.min() + nn.max()) / 2
    A = base + ax * b[0] / S; B = base + ax * b[2] / S
    return dict(poly=affinity.translate(u, -b[0], -b[1]), A=A, B=B, T=T, z0=z0, H=b[3] / S, ax=ax)

def honkan_pieces():
    """本館の 1 階の間仕切り（38 のうち v>0.3 m）。番号は 3dm の並び順（interior_parts と同じ）"""
    out = []; k = 0
    for lay, tag in (('38_しつらえ_間仕切り・框・腰壁', '本館'), ('24_西館_間仕切り', '西館')):
        for g in objs(lay):
            if not isinstance(g, r.Mesh): continue
            pn = _panel_ex(g)
            if not pn: continue
            k += 1
            if tag != '本館': continue
            um, vm = _uv(*((pn['A'] + pn['B']) / 2))
            if vm < 0.3: continue                     # 西館の 2 階の壁（v<0）
            pn['num'] = k; out.append(pn)
    return out

def _col_info(g):
    P = profile_rz(g, 0)
    foot = P[P[:, 1] < 1]
    rc = (foot[:, 0].min() + foot[:, 0].max()) / 2
    a0 = math.atan2(g.PathStart.Y - CY, g.PathStart.X - CX); a1 = math.atan2(g.PathEnd.Y - CY, g.PathEnd.X - CX)
    ac = (a0 + a1) / 2
    return dict(rc=rc, ac=ac, prof=Polygon(P).buffer(0), east=rc < RW_ - 6000)

def _polar_rect(ac, r0, r1, t):
    er = np.array([math.cos(ac), math.sin(ac)]); et = np.array([-math.sin(ac), math.cos(ac)])
    C = np.array([CX, CY])
    return Polygon([C + r0 * er - t * et, C + r1 * er - t * et, C + r1 * er + t * et, C + r0 * er + t * et])

COLS = None
def col_infos():
    global COLS
    if COLS is None:
        COLS = sorted([_col_info(g) for g in cols], key=lambda d: (d['east'], -d['ac']))
        # 架構の番号：南（角度が大きい）から 1〜20
        for east in (False, True):
            lst = sorted([d for d in COLS if d['east'] == east], key=lambda d: -(d['ac'] % (2 * math.pi)))
            for i, d in enumerate(lst): d['frame'] = i + 1
    return COLS

def col_keepout(d, zlo, zhi):
    """柱の置き場所（平面）：高さ zlo〜zhi（実寸 mm）で柱が占める半径の範囲 ＋ 床の穴"""
    I = d['prof'].intersection(box(0, zlo, 1e7, zhi))
    rr = []
    if zlo <= 300: rr += [d['rc'] - HOLE_R, d['rc'] + HOLE_R]
    if not I.is_empty: rr += [I.bounds[0], I.bounds[2]]
    rl, rh = min(rr), max(rr)
    return _polar_rect(d['ac'], rl, rh, HOLE_T)

def plate_bands():
    out = []
    for d in col_infos():
        if d['east']: continue
        for sgn in (-1, 1):
            t0, t1 = sorted((sgn * PLATE_IN, sgn * PLATE_OUT))
            er = np.array([math.cos(d['ac']), math.sin(d['ac'])]); et = np.array([-math.sin(d['ac']), math.cos(d['ac'])])
            C = np.array([CX, CY]); r0, r1 = RW_ - 15500, RW_ + 600
            out.append((d['frame'], '北' if sgn * 1 > 0 else '南', Polygon([C + r0 * er + t0 * et, C + r1 * er + t0 * et, C + r1 * er + t1 * et, C + r0 * er + t1 * et]), d['ac']))
    return out
_BEAM = None
def beam_under(rr):
    """梁の板の下面の高さ（実寸 mm）、半径 rr（mm）で"""
    global _BEAM
    if _BEAM is None: _BEAM = Polygon(profile_rz(beam, 0)).buffer(0)
    ln = _BEAM.intersection(LineString([(rr, -1e4), (rr, 1e5)]))
    return ln.bounds[1] if not ln.is_empty else 1e9

def footprint(A, B, t=kabe.T_BOARD / S):
    return LineString([A, B]).buffer(t / 2, cap_style=2)

def check_wall(A, B, zlo, ztop, with_hole=True):
    """壁の線 A→B（高さ zlo〜ztop、実寸 mm）と架構の干渉。返す：柱の重なり、梁、桁、最小の離れ"""
    fp = footprint(A, B); res = dict(col=[], beam=[], keta=[], dist=1e9)
    for d in col_infos():
        ko = col_keepout(d, zlo if with_hole else 400, ztop)
        res['dist'] = min(res['dist'], fp.distance(ko))
        ov = fp.intersection(ko)
        if ov.area > 0.5:
            res['col'].append((d['frame'], '東' if d['east'] else '西', ov, ko))
    for fr, side, band, ac in plate_bands():
        ov = fp.intersection(band)
        if ov.area > 0.5:
            rs = [math.hypot(x - CX, y - CY) for x, y in ov.exterior.coords]
            under = min(beam_under(x) for x in np.linspace(min(rs), max(rs), 25))
            vv = (RW_ - np.mean(rs)) / 1000
            res['beam'].append((fr, side, under, vv))
    ring = lambda v0, v1: Point(CX, CY).buffer(RW_ - v0, 512).difference(Point(CX, CY).buffer(RW_ - v1, 512))
    for nm, v0, v1, zb in KETA_BANDS:
        if fp.intersection(ring(v0, v1)).area > 0.5: res['keta'].append((nm, zb))
    return res

def build_walls(pcs_fn=None, chk=None, endfix=None):
    """pcs_fn・chk を渡すと別の建物（西館）の板と干渉の測りで同じ手順を回す。省くと本館"""
    pcs = (pcs_fn or honkan_pieces)()
    chk = chk or check_wall
    runs = kabe.make_runs(pcs)
    tiny = [R_ for R_ in runs if R_.L < 3.0]                  # 幅 3 mm 未満の板（隣の壁にほぼ含まれる）は作らない
    runs = [R_ for R_ in runs if R_.L >= 3.0]
    runs.sort(key=lambda R_: (min(_uv(*R_.A)[0], _uv(*R_.B)[0]), _uv(*R_.A)[1]))
    for i, R_ in enumerate(runs): R_.id = i + 1
    t3 = {}
    for R_ in runs:
        t3[R_.id] = float(np.mean([p['T'] for p in pcs if p['num'] in R_.members]))
    # --- 架構との干渉を直す（柱の手前で止める／梁・桁より低くする）
    for R_ in runs:
        for _ in range(4):
            zlo, ztop = R_.bottom(), R_.top()
            cw = chk(R_.A, R_.B, zlo, ztop)
            if not cw['col']: break
            fr, sd, ov, ko = cw['col'][0]
            Ls = np.linalg.norm(R_.B - R_.A)
            ss = [(np.array(p) - R_.A) @ R_.e for p in ov.exterior.coords]
            s0, s1 = min(ss), max(ss)
            ks = [(np.array(p) - R_.A) @ R_.e for p in ko.exterior.coords]
            if s0 <= 1.0:
                x0, x1 = s1 * S, R_.poly.bounds[2]; where = '南端' if True else ''
            elif s1 >= Ls - 1.0:
                x0, x1 = 0.0, s0 * S; where = '北端'
            else:
                R_.notes.append(f'！壁の途中で柱{fr}{sd}に当たる（要判断）'); break
            oldL = R_.poly.bounds[2] - R_.poly.bounds[0]
            R_.poly = R_.poly.intersection(box(x0, -1e4, x1, 1e4)); R_.poly = unary_union(kabe._parts(R_.poly)); R_.reframe()
            R_.notes.append(f"柱{fr}{sd}の手前で止めた（{(oldL - (R_.poly.bounds[2] - R_.poly.bounds[0])) / S / 1000:.3f} m短く）")
        if endfix:                                   # 西館：梁の板・桁の下はその部分だけ切り欠く（壁全体は下げない）
            endfix(R_); continue
        cw = chk(R_.A, R_.B, R_.bottom(), R_.top())
        lim = min([u_ - CLEAR_TOP for (_, _, u_, _) in cw['beam']] + [zb - CLEAR_TOP for (_, zb) in cw['keta']] + [1e9])
        if R_.top() > lim:
            old = R_.top()
            R_.poly = R_.poly.intersection(box(-1e4, -1e4, 1e4, R_.y_of(lim)))
            R_.poly = unary_union(kabe._parts(R_.poly))
            R_.notes.append(f'上端を{old / 1000:.2f} mから{lim / 1000:.2f} mに下げた（下面−{CLEAR_TOP / 1000:.2f} m）')
    return pcs, runs, t3, tiny

def assemble(pcs_fn=None, chk=None):
    """間仕切りを壁にまとめ、架構との干渉を直し、交点に半欠きを入れ、孤立した壁に足をつける"""
    chk = chk or check_wall
    pcs, runs, t3, tiny = build_walls(pcs_fn, chk)
    Jt = kabe.find_joints(runs, t3); kabe.classify(Jt)
    ext = kabe.extend_stems(Jt); kabe.apply_extensions(runs, ext)
    comps = kabe.components(runs, Jt)
    feet, fj = [], []
    nid = len(runs) + 1
    for c in comps:
        if kabe.is_braced(c): continue
        for R_ in c:
            for f, j in kabe.make_feet(R_, nid):
                feet.append(f); fj.append(j); nid += 1
    allj = Jt + fj
    kabe.cut_joints(allj, WALL_KERF, CUT_W)
    # 足・伸ばした端が架構や別の壁に当たらないかを確かめる
    probs = []
    for R_ in runs + feet:
        cw = chk(R_.A, R_.B, R_.bottom(), R_.top())
        bad = [f'柱{fr}{sd}' for fr, sd, _, _ in cw['col']]
        bad += [f'梁{fr}{sd}（下面{u_ / 1000:.2f} m）' for fr, sd, u_, _ in cw['beam'] if R_.top() > u_ - CLEAR_TOP + 1e-6]
        bad += [f'{nm}' for nm, zb in cw['keta'] if R_.top() > zb - CLEAR_TOP + 1e-6]
        if bad: probs.append((R_, bad))
    for f in feet:
        fp = footprint(f.A, f.B)
        for R_ in runs:
            if R_.id != f.foot_of and fp.intersection(footprint(R_.A, R_.B)).area > 1.0:
                probs.append((f, [f'壁{R_.id}と重なる']))
    return dict(pcs=pcs, runs=runs, feet=feet, joints=allj, comps=comps, tiny=tiny, probs=probs, t3=t3)

def pin(P):
    """壁の線上の点 → (架構の番号, 架構の線から北へ mm（模型）, 西の縁から mm（模型）, u, v)"""
    u, v = _uv(*P)
    k = int(round(u / 3.0))
    a = (u - 3.0 * k) * (RW_ - v * 1000) / RW_ * 10
    b = (v - V_EDGE) * 10
    return k + 1, a, b, u, v

def _label_pos(poly, n, h=1.2):
    w = len(n) * h * 0.6 + (len(n) - 1) * (1.2 - h * 0.6) + h * 0.1
    best = None
    b = poly.bounds
    inner = poly.buffer(-0.35)
    for x in np.arange(b[0], b[2] - w, 0.4):
        for y in np.arange(b[1], b[3] - h, 0.4):
            if inner.contains(box(x, y, x + w, y + h)):
                d = Point(x + w / 2, y + h / 2).distance(poly.boundary)
                if best is None or d > best[0]: best = (d, x, y)
    return best

def _tab_points(poly):
    """つなぎ（切り残し）の位置：外形のいちばん長い水平の辺の中点を、下側と上側に 1 つずつ"""
    pts = []
    ring = list(poly.exterior.coords)
    segs = [(ring[i], ring[i + 1]) for i in range(len(ring) - 1) if abs(ring[i][1] - ring[i + 1][1]) < 1e-6 and abs(ring[i][0] - ring[i + 1][0]) > 1.4]
    if not segs: return pts
    ymid = (poly.bounds[1] + poly.bounds[3]) / 2
    for half in (lambda y: y <= ymid, lambda y: y > ymid):
        cand = [s for s in segs if half(s[0][1])]
        if cand:
            s_ = max(cand, key=lambda s: abs(s[0][0] - s[1][0]))
            pts.append(Point((s_[0][0] + s_[1][0]) / 2, s_[0][1]))
    return pts

# ================= 足の突起と床の短い溝（11-02、ユーザー承認） =================
# 孤立した壁の T 字の足の下に、突起（長さ FOOT_TAB_L、深さ FOOT_TAB_D、板厚 0.6）を付け、床のいちばん上の 1.7 の層に短い溝（描く 4.0×0.4）を切る。
# 壁の高さは変えない（足の下の面 y=0 は床の上面のまま、突起だけが 1.5 mm 床に入る）。溝は床の上の層だけの貫通（深さ 1.7 > 突起 1.5）。
# 足が基礎の上（zref −300、土足の低い所）に立つ 2 本は溝を切れない（基礎は 3.0）ので突起なし：針の印で置く
FOOT_TAB_L = 4.0
FOOT_TAB_D = 1.5
FOOT_SLOT_W = 0.4

def foot_tab_x(f, ok=None):
    """突起の中心の局所 x（足の芯 4.0 に近い順に探す）。ok(f, x) は溝が床の内側（縁から 0.8 以上）に入るか。入る所がなければ None"""
    if f.zref < -151.0: return None
    b = f.poly.bounds; m = FOOT_TAB_L / 2 + 0.2
    lo, hi = b[0] + m, b[2] - m
    if lo > hi + 1e-9: return None
    c0 = min(max(kabe.FOOT_LEN / 2, lo), hi)
    cands = sorted({round(min(max(c0 + k * 0.1, lo), hi), 3) for k in range(-40, 41)}, key=lambda x: abs(x - c0))
    for x in cands:
        seg = box(x - FOOT_TAB_L / 2, 0, x + FOOT_TAB_L / 2, 0.3)
        if f.poly.intersection(seg).area < FOOT_TAB_L * 0.3 - 1e-6: continue
        if ok is None or ok(f, x): return x
    return None

class _Tabbed:
    """足に突起を付けた板（番号の彫りや並べ替えは poly だけを見る）"""
    def __init__(self, f, ok=None):
        self.f = f; x = foot_tab_x(f, ok)
        self.x = x
        self.poly = f.poly if x is None else unary_union([f.poly, box(x - FOOT_TAB_L / 2, -FOOT_TAB_D, x + FOOT_TAB_L / 2, 0)])

def foot_slot_world(f, ok=None):
    """溝の中心（世界座標、実寸 mm）と、足の向きの単位ベクトル。溝なしなら None"""
    x = foot_tab_x(f, ok)
    if x is None: return None
    return f.world(x), f.e

_OK = {}
def foot_ok_h():
    """本館の足の溝：床の上の層（FL＋0、天の川で 2 枚に分かれる。柱の穴あり）の縁・穴から 0.8 以上内側で、窪みの円と離れる。戻り：(T, ok)"""
    if 'h' not in _OK:
        out, T, F = dai_outline_sheet()
        upper = floors()[0]
        um = affinity.scale(upper, S, S, origin=(0, 0)).buffer(-0.8)
        txm = lambda P: Point(P.x * S, P.y * S)
        circ = unary_union([Point(*_uv_xy(u, 7.5) * S).buffer(1200.0 * S + 0.8) for u in (36.0, 45.0, 54.0)])
        _OK['h'] = (T, lambda f, x: um.contains(foot_slot_poly(f.world(x), f.e, txm)) and not foot_slot_poly(f.world(x), f.e, txm).intersects(circ))
    return _OK['h']

def foot_ok_w():
    """西館の足の溝が、1 階の上の層の縁・穴から 0.8 以上内側に入るか"""
    if 'w' not in _OK:
        upper = west_floors()[0]
        um = affinity.scale(upper, S, S, origin=(0, 0)).buffer(-0.8)
        tx = lambda P: Point(P.x * S, P.y * S)
        _OK['w'] = lambda f, x: um.contains(foot_slot_poly(f.world(x), f.e, tx))
    return _OK['w']

def foot_slot_poly(c, d, tx):
    """溝の長方形：c 中心、d 向き。tx は世界座標→板の座標の変換（点→点）。描く寸法 FOOT_TAB_L×FOOT_SLOT_W（長い辺が足の向き）"""
    P = tx(Point(*c)); Q = tx(Point(*(np.asarray(c) + np.asarray(d) * 1000.0)))
    v = np.array([Q.x - P.x, Q.y - P.y]); v /= np.linalg.norm(v); w = np.array([-v[1], v[0]])
    a, b = FOOT_TAB_L / 2, FOOT_SLOT_W / 2
    return Polygon([tuple(np.array([P.x, P.y]) + v * sx + w * sy) for sx, sy in ((-a, -b), (a, -b), (a, b), (-a, b))])

# --- かみ合った壁の組（事務室・トイレ・倉庫など）の位置決め：組ごとに 2 か所、壁の下に突起、床に溝（11-02、ユーザー）
WALL_TAB_MARGIN = 2.5

def _wall_tab_candidates(R_, ok):
    """壁 R_ の下面（床に接する面）で、突起 4.0 を付けられる局所 x の候補。両側 WALL_TAB_MARGIN まで板があること"""
    b = R_.poly.bounds
    if R_.z_of(b[1]) < -151.0: return []
    out = []
    x = b[0] + WALL_TAB_MARGIN
    while x <= b[2] - WALL_TAB_MARGIN + 1e-9:
        seg = box(x - WALL_TAB_MARGIN, b[1], x + WALL_TAB_MARGIN, b[1] + 0.3)
        if R_.poly.intersection(seg).area > 2 * WALL_TAB_MARGIN * 0.3 - 1e-6 and ok(R_, x):
            out.append(round(x, 2))
        x += 0.5
    return out

def wall_tab_plan(W_, ok):
    """戻り：{壁の番号: [局所 x, …]}。足のない組（支え合う組）ごとに、いちばん離れた 2 か所（別々の壁を優先）"""
    plan = {}
    for c in W_['comps']:
        if not kabe.is_braced(c): continue
        cand = [(R_, x, R_.world(x)) for R_ in c for x in _wall_tab_candidates(R_, ok)]
        if len(cand) < 2: continue
        best = None
        for i in range(len(cand)):
            for j in range(i + 1, len(cand)):
                d = float(np.linalg.norm(cand[i][2] - cand[j][2])) * S
                if cand[i][0] is cand[j][0]: d *= 0.6
                if best is None or d > best[0]: best = (d, i, j)
        if best is None or best[0] < 6.0: continue
        for k in best[1:]:
            R_, x, _ = cand[k]; plan.setdefault(R_.id, []).append(x)
    return plan

class _WallTabbed:
    def __init__(self, R_, xs):
        self.R = R_; self.xs = xs
        b = R_.poly.bounds
        self.poly = unary_union([R_.poly] + [box(x - FOOT_TAB_L / 2, b[1] - FOOT_TAB_D, x + FOOT_TAB_L / 2, b[1]) for x in xs])

def foot_ok_h_wall():
    """本館の壁の溝：足と同じ条件（壁 R_ と局所 x）"""
    return foot_ok_h()[1]

def interior_sheets():
    W_ = assemble()
    runs, feet = W_['runs'], W_['feet']
    items = []
    wplan = wall_tab_plan(W_, foot_ok_h_wall())
    for R_ in runs:
        items.append((str(R_.id), _WallTabbed(R_, wplan[R_.id]) if R_.id in wplan else R_))
    for f in feet:
        par = next(r_ for r_ in runs if r_.id == f.foot_of)
        items.append((f'{par.id}{"A" if f.side == "A" else "B"}', _Tabbed(f, foot_ok_h()[1])))
    shelf = kabe_layout(items)
    nsheet = 0
    miss = []
    for si, lst in enumerate(shelf):
        s = Sheet(f'09_室内の壁_{si + 1}_航空ベニヤ0.6', 600, 300,
                  '航空ベニヤ 0.6 300×600：本館の1階の間仕切り（番号は 10_室内の壁の配置図 と同じ。足は番号に A・B）。高さは床の上面から。半欠きは切り込み（上から／下から）。向きは元のまま、外接矩形が最小になるように詰めた（壁どうし2.5 mm以上）')
        s.tabs = True; s.show_used = True
        for n, tx, ty in lst:
            R_ = dict(items)[n]
            q = affinity.translate(R_.poly, tx, ty)
            for pp in kabe._parts(q):
                s.add(pp)
                s.tab_pts += _tab_points(pp)
            lp = max(kabe._parts(q), key=lambda p_: p_.area)
            pos = _label_pos(lp, n, 1.2) or _label_pos(lp, n, 0.9)
            hh = 1.2 if _label_pos(lp, n, 1.2) else 0.9
            if pos:
                _, lx, ly = pos
                for j, ch in enumerate(n):
                    for l in label_num(ch, lx + j * (hh * 0.6 + (1.2 - 1.2 * 0.6) * (hh / 1.2)), ly, hh): s.add(l, 'eng')
            else:
                miss.append(n)
        s.save()
        nsheet += 1
    plan_pdf(W_)
    write_table(W_, miss)
    return dict(壁=len(runs), 足=len(feet), 板=len(W_['pcs']), 交点=len(W_['joints']), 枚=nsheet, 番号を彫れない=miss, 問題=[(r_.id, b_) for r_, b_ in W_['probs']])

def kabe_shelf(items, W, H, gap=2.5):
    sheets = [[]]; x = y = rowh = 0
    for n, g in sorted(items, key=lambda it: -it[1].bounds[3]):
        w, h = g.bounds[2], g.bounds[3]
        if x + w > W: x = 0; y += rowh + gap; rowh = 0
        if y + h > H: sheets.append([]); x = y = rowh = 0
        sheets[-1].append(((n, g), x, y)); x += w + gap; rowh = max(rowh, h)
    return sheets

def kabe_layout(items, gap=2.5):
    """間仕切りの板の並べ方（11-02）：壁（と足）ごとのひとかたまりを、外接矩形が最小になるように詰める（向きは元のまま）。
    戻り：板ごとの[(番号, 動かす量x, y)]。1枚に入らなければ今までの棚詰め"""
    try:
        mv, _ = nest([R_.poly for n, R_ in items], 600 - 2 * Sheet.MARGIN, 300 - 2 * Sheet.MARGIN, gap, top=290)
        return [[(n, tx, ty) for (n, R_), (tx, ty) in zip(items, mv)]]
    except RuntimeError:
        shelf = kabe_shelf([(n, R_.poly) for n, R_ in items], 590, 290, gap)
        return [[(n, x - g.bounds[0], 290 - y - g.bounds[3]) for (n, g), x, y in lst] for lst in shelf]

def plan_pdf(W_):
    """配置図（1/100、平面）：壁の線と番号、針の印の点、架構の番号"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    try:
        import fonts42                       # Type42（文字のまま埋め込む）、無ければ前のまま
    except Exception:
        plt.rcParams['font.family'] = 'Noto Sans CJK JP'
        plt.rcParams['pdf.fonttype'] = 42
    ang = sheet_angle()
    flo = unary_union([plan('12_本館_床（はだし ±0）'), plan('14_本館_外縁側（土足 −150）'), plan('15_本館_あまのがわ（土足 −150）')])
    ub = to_sheet(flo, ang, (0, 0)).bounds
    off = (20 - ub[0], (594 - (ub[3] - ub[1])) / 2 - ub[1])
    ts = lambda g: affinity.translate(to_sheet(g, ang, (0, 0)), *off)
    path = os.path.join(OUT, '10_室内の壁の配置図.pdf')
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4)); axp = fig.add_axes([0, 0, 1, 1])
        for gg in getattr(flo, 'geoms', [flo]):
            xs, ys = ts(gg).exterior.xy; axp.plot(xs, ys, color='0.75', lw=0.4)
        for d in col_infos():
            q = ts(Point(CX + d['rc'] * math.cos(d['ac']), CY + d['rc'] * math.sin(d['ac'])))
            axp.plot([q.x], [q.y], 's', color='0.3', ms=2)
            if not d['east']:
                axp.text(q.x - 0.5, q.y + 2.5, str(d['frame']), fontsize=6, color='0.2', ha='right', va='bottom', rotation=0)
        for R_ in W_['runs'] + W_['feet']:
            foot = R_.foot_of is not None
            ln = ts(LineString([R_.A, R_.B])); xs, ys = ln.xy
            axp.plot(xs, ys, color='tab:blue' if foot else 'tab:red', lw=0.9 if foot else 1.4, solid_capstyle='butt')
            if not foot:
                mid = ln.interpolate(0.5, normalized=True)
                axp.text(mid.x, mid.y, str(R_.id), fontsize=5, color='tab:red', ha='center', va='center', bbox=dict(fc='white', ec='none', pad=0.3, alpha=0.8))
        for j in W_['joints']:
            q = ts(Point(*j.X)); axp.plot([q.x], [q.y], 'o', color='k', ms=1.6)
        axp.set_xlim(0, 841); axp.set_ylim(0, 594); axp.set_aspect('equal'); axp.axis('off')
        axp.text(20, 20, '室内の壁の配置図（本館の1階）：壁の線を赤、足を青、交点を黒の点。番号は 09 の板の番号、上の数字は架構の番号（南から）。A1 に 100% で印刷すると模型と同じ大きさ', fontsize=9)
        pdf.savefig(fig); plt.close(fig)

def _jdesc(j, run):
    frm, x, w, removed, desc = j.cut[run.id]
    return f'{j.R.id if run is j.S else j.S.id}と{j.kind}（{"上から" if frm == "top" else "下から"}）'

def foot_note_lines(W_, okfn, where):
    """位置表に入れる、足の突起と床の溝の書き出し（溝のある足・ない足）"""
    yes, no = [], []
    for f in W_['feet']:
        lab = f'{f.foot_of}{"A" if f.side == "A" else "B"}'
        (yes if foot_slot_world(f, okfn) else no).append(lab)
    return [f'- **足の突起と床の溝**（11-02）：足の下に突起（{FOOT_TAB_L:.1f}×深さ{FOOT_TAB_D} mm、板厚0.6）、{where}に短い溝（描く{FOOT_TAB_L:.1f}×{FOOT_SLOT_W}）。溝のある足（{len(yes)}）：{"・".join(yes) or "なし"}。針の印で置く足（突起なし、{len(no)}）：{"・".join(no) or "なし"}（床の縁・穴に近い所か、基礎の上に立つ所で、溝を切れない）。']

def write_table(W_, miss):
    runs, feet, joints = W_['runs'], W_['feet'], W_['joints']
    pcs, probs = W_['pcs'], W_['probs']
    byid = {r_.id: r_ for r_ in runs}
    runof = {}
    for R_ in runs:
        for m_ in R_.members: runof[m_] = R_
    o = []
    o.append('# 室内の壁（本館1階）の位置表と干渉の確かめ\n')
    o.append('作った所：`mokei/laser.py` の「9. 室内の壁」と `mokei/kabe.py`（`python3 mokei/laser.py` で09・10とこの表を書き直す）。模型作成。\n')
    o.append('## 前提\n')
    o.append('- 組み立ての順：①間仕切り（航空ベニヤ0.6）を床に立てる（壁どうしを半欠きでかみ合わせて自立）→②架構を上から下ろす→③外壁。')
    o.append(f'- 板の厚さ0.6、切り幅{WALL_KERF}。切り込みの描く幅は、両側に木が残る所＝0.6−{WALL_KERF}＝{CUT_W:.2f}、壁の端の切り込み＝相手の厚さ−{WALL_KERF / 2:.1f}。T5（航空ベニヤ0.6の試し切り）の結果が`data/mokei.json`に無いので仮の値。結果が出たら`切り幅`の`航空ベニヤ0.6`か`室内の壁`の`切り込みの幅_描く`に入れて作り直す。')
    o.append('- 切り込みの高さの境は、組む所の材の高さの真ん中。上端が高いほうの壁に下から、低いほうに上から入れる。T・Lで端になる壁は、相手の壁の向こう側の面まで伸ばして面をそろえる（相手は模型では0.6の薄さ）。')
    o.append(f'- 梁の下面・桁の下面との余裕は{CLEAR_TOP / 10:.1f} mm（実寸{CLEAR_TOP / 1000:.2f} m）。柱の置き場所は、柱の厚さ1.75・幅4.0と頭の丸み、床の柱の穴（実寸1.8×4.1）。')
    o += foot_note_lines(W_, foot_ok_h()[1], '本館の床の上の層（1.7）')
    wp = wall_tab_plan(W_, foot_ok_h_wall())
    nocomp = ['・'.join(str(r_.id) for r_ in c) for c in W_['comps'] if kabe.is_braced(c) and not any(r_.id in wp for r_ in c)]
    o.append('- **かみ合った壁の組の突起と溝**（11-02）：組ごとに2か所、壁の下に突起、床に溝。壁と局所x（壁の端から mm）：' + '、'.join(f'壁{k}（x={"・".join(f"{x:.1f}" for x in v)}）' for k, v in sorted(wp.items())) + f'。突起のない組（針の印で置く）：{"、".join(nocomp) or "なし"}。')
    o.append(f'- 針の印の座標：架構の番号（南から、架構1＝南の妻）、その架構の線から北へ何mm（弧に沿って、南は−）、西の縁（床04の西の端、西の外壁の線より3.4 mm外）から何mm（半径方向、東へ）。単位は模型のmm。印は壁の線（厚さの真ん中）の上。\n')
    # --- 干渉の確かめ
    o.append('## 1. 干渉の確かめ（3dmの板ごと）\n')
    o.append('a＝柱（頭の丸みと床の穴を含む）との重なり／b＝梁の板の下面との余裕（交わる梁の板の下面−板の上端、実寸m）／c＝桁・他の部材。直しは壁（まとめた板）につけた。\n')
    o.append('| 板 | 場所（u, v m） | 高さ（m） | a 柱 | b 梁 | c 桁・他 | 壁 | 直し |')
    o.append('|---|---|---|---|---|---|---|---|')
    others = _others_hits(pcs)
    for p in pcs:
        zlo, zt = p['z0'], p['z0'] + p['H']
        cw = check_wall(p['A'], p['B'], zlo, zt)
        ua, va = _uv(*p['A']); ub, vb = _uv(*p['B'])
        a_ = '、'.join(f'柱{fr}{sd}に重なる' for fr, sd, _, _ in cw['col']) or f'なし（離れ{cw["dist"] * S:.1f} mm）'
        if cw['beam']:
            b_ = '、'.join(f'梁{fr}{sd}の下面{u_ / 1000:.2f}（余裕{(u_ - zt) / 1000:+.2f}）' for fr, sd, u_, _ in cw['beam'])
        else:
            b_ = '梁の板と交わらない'
        c_ = '、'.join(f'{nm}（下面{zb / 1000:.2f}）' for nm, zb in cw['keta']) or '桁なし'
        if others is not None:
            oh = others.get(p['num'])
            c_ += '／他：' + ('、'.join(f'{k}×{v}' for k, v in sorted(oh.items())) if oh else 'なし')
        R_ = runof.get(p['num'])
        fix = '、'.join(R_.notes) if R_ and R_.notes else ''
        o.append(f'| {p["num"]} | u{ua:.2f}〜{ub:.2f}, v{va:.2f}〜{vb:.2f} | {zlo / 1000:.2f}〜{zt / 1000:.2f} | {a_} | {b_} | {c_} | {R_.id if R_ else "（作らない）"} | {fix} |')
    o.append('')
    o.append('他の部材の列は、3dmの板の中に他のレイヤー（ロフト・家具・格子・ガラス・戸・縁側の框など。屋根・架構・床・外壁は除く）の面の点が入っているかの粗い測り。数字は入った物の数。窓のガラス（48）・縦格子（49）・格子手すりは、板の穴や仕上げとして別に作るので、壁の形は変えない。母屋（10v）などの屋根の部材は模型の屋根（06、3dmより3.11 mm高い）に無い。\n')
    o.append('### 直したもの（壁ごと）\n')
    for R_ in runs:
        if R_.notes:
            o.append(f'- 壁{R_.id}（板{"・".join(map(str, R_.members))}）：' + '；'.join(R_.notes))
    for R_ in W_['tiny']:
        o.append(f'- 板{"・".join(map(str, R_.members))}：幅{R_.L:.1f} mmの細い板（隣の壁にほぼ含まれる）は作らない。要判断')
    o.append('')
    # --- 壁と交点
    o.append('## 2. 壁と半欠きのかみ合い\n')
    o.append('| 壁 | 板 | 長さ×高さ（模型mm） | 高さ（床の上、m） | 交点（相手・形・自分の切り込み） |')
    o.append('|---|---|---|---|---|')
    for R_ in runs + feet:
        js = []
        for (j, frm, x, w, removed) in R_.joints:
            oth = j.S if R_ is j.R else j.R
            lab = oth.id if oth.foot_of is None else f'{oth.foot_of}{"A" if oth.side == "A" else "B"}'
            js.append(f'{lab}（{j.kind}・{"上から" if frm == "top" else "下から"}・x={x:.1f}・幅{w:.2f}）' + ('' if removed > 0.05 else '！材が無い'))
        b = R_.poly.bounds
        nm = str(R_.id) if R_.foot_of is None else f'{R_.foot_of}{"A" if R_.side == "A" else "B"}（足）'
        o.append(f'| {nm} | {"・".join(map(str, R_.members)) or "—"} | {b[2]:.1f}×{b[3]:.1f} | {R_.bottom() / 1000:.2f}〜{R_.top() / 1000:.2f} | {"、".join(js) or "なし"} |')
    o.append('')
    iso = [c for c in W_['comps'] if not kabe.is_braced(c)]
    o.append(f'### 孤立した壁と足\n')
    o.append(f'向きの違う壁と組まない壁（{sum(len(c) for c in iso)}枚）に、T字の足（長さ{kabe.FOOT_LEN:.0f} mm、高さは壁の端の半分で6 mmまで）をつけた。長さ15 mm未満の壁は、A端（番号の若い側＝壁の線のA→B の始め）だけ。足は番号にAかBをつけて09に入れてある。')
    o.append('孤立した壁：' + '、'.join(str(r_.id) for c in iso for r_ in c))
    o.append('')
    if probs:
        o.append('### 要判断（まだ当たる所）\n')
        for R_, b_ in probs:
            o.append(f'- 壁{R_.id}：{"、".join(b_)}')
        o.append('')
    # --- 針の印
    o.append('## 3. 針の印の表\n')
    o.append('床04に鉛筆の針で打つ点。壁の線（厚さの真ん中）の端と交点。A→B は壁の線の向き。「確かめ」は隣の印との距離（ものさしで）。\n')
    o.append('| 壁 | 点 | 架構 | 架構の線から北へ（mm） | 西の縁から（mm） | u, v（m） |')
    o.append('|---|---|---|---|---|---|')
    for R_ in runs + feet:
        nm = str(R_.id) if R_.foot_of is None else f'{R_.foot_of}{"A" if R_.side == "A" else "B"}'
        pts = [('A端', R_.A), ('B端', R_.B)]
        for (j, frm, x, w, removed) in R_.joints:
            oth = j.S if R_ is j.R else j.R
            lab = oth.id if oth.foot_of is None else f'{oth.foot_of}{"A" if oth.side == "A" else "B"}'
            pts.append((f'交点{lab}', j.X))
        pts_sorted = sorted(pts, key=lambda t: (t[1] - R_.A) @ R_.e)
        for lab, P in pts_sorted:
            k, a, b, u, v = pin(P)
            o.append(f'| {nm} | {lab} | {k} | {a:+.1f} | {b:.1f} | {u:.2f}, {v:.2f} |')
    o.append('')
    if miss:
        o.append('番号を彫れなかった板：' + '、'.join(miss))
    txt = '\n'.join(o) + '\n'
    open(os.path.join(ROOT, 'mokei', '室内の壁_位置表.md'), 'w').write(txt)

def _others_hits(pcs):
    """板の中に入る他のレイヤーの面の点（粗い）。tri（rhino の形→三角形）が使えなければ None"""
    try:
        sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'view'))
        import tri as _tri
    except Exception:
        return None
    skip = ('10', '11', '12', '13', '14', '15', '17', '38', '24', '52', '00', '01', '20', '21', '22', '23', '25', '27', '30', '31', '32', '33', '34', '35', '36', '41', '42', '43', '44', '45', '53', '54', '56', '58', '59', '60', '62', '64', '66', '67', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '96', '97', '98', '99', '19b', '19g', '19c', '19', '21g', '21y', '16', '35b', '35d', '55', '39', '40', '47', '57')
    import re as _re
    P_ = []
    for o_ in m.Objects:
        nm = m.Layers[o_.Attributes.LayerIndex].Name
        code = nm.split('_')[0]
        if not (code.startswith(('37', '46', '48', '49', '51', '18', '19d', '17g', '16d', '16h', '16i', '16o', '19e'))): continue
        g = o_.Geometry
        try:
            if isinstance(g, r.Mesh): T = _tri.tri_mesh(g)
            elif isinstance(g, r.Extrusion): T = _tri.tri_extrusion(g)
            elif isinstance(g, r.Brep): T = _tri.tri_brep(g)
            else: continue
        except Exception:
            continue
        T = np.asarray(T).reshape(-1, 3, 3)
        if not len(T): continue
        pts = np.vstack([T.reshape(-1, 3), T.mean(1), (T[:, 0] + T[:, 1]) / 2, (T[:, 1] + T[:, 2]) / 2, (T[:, 0] + T[:, 2]) / 2])
        P_.append((code, pts))
    out = {}
    for p in pcs:
        A, B = p['A'], p['B']; e = _unit_(B - A); n = np.array([-e[1], e[0]]); L_ = np.linalg.norm(B - A)
        hits = {}
        for code, pts in P_:
            rel = pts[:, :2] - A
            s_ = rel @ e; t_ = rel @ n
            mk = (s_ > 20) & (s_ < L_ - 20) & (np.abs(t_) < p['T'] / 2 - 10) & (pts[:, 2] > p['z0'] + 20) & (pts[:, 2] < p['z0'] + p['H'] - 20)
            if mk.any(): hits[code] = hits.get(code, 0) + 1
        out[p['num']] = hits
    return out

def _unit_(v):
    return v / np.linalg.norm(v)

# ================= 9w. 西館の室内の壁（1階。西館 24） =================
# 11-02 の頼み（模型作成）：本館の 09 と同じ手順（kabe.py）で、西館の 1 階の間仕切りを作る。遊戯室はしつらえなので壁だけ。
# 組み立ての順は本館と同じ：間仕切りを先に床に立てる（壁どうしの半欠きで自立）→ 架構（07 の西館の架構、接着せず差す）を上から下ろす → 外壁。
# だから間仕切りは柱（頭の丸みも・床の穴も）を通れず、梁の板の下は局所的に切り欠く（3dm が梁の板の下を H2400 の小壁にしているのと同じ）。
# 西館の床（1.7×2＋ベタ基礎 3）はまだ作らないので切り溝は使わず、針の印の位置表で立てる。2 階の間仕切りは数えて一覧にするだけ。
#   python3 -c "import laser; print(laser.interior_sheets_w())"  … 09w・10w と位置表の西館の節だけを書く（本館の 09・10 は触らない）
W_FLOOR_TOP = 3170.0             # 2 階の床の下面（1 階の間仕切りの天端）。階段の箱の壁など、1・2 階ひと続きの板はここで切る
W_HMIN = 200                     # 腰壁（h450）・戸の上の小壁（h250）も拾う（本館は 600 以上）
WALL_NAME_W = '09w_西館の室内の壁_航空ベニヤ0.6'

def west_pieces():
    """西館 24 の間仕切りのうち 1 階の分（床から 3170 まで）。返す：(1 階の板, 2 階の分の板)。番号は 24 のレイヤーの並び順"""
    one, two = [], []
    for k, g in enumerate(objs('24_西館_間仕切り'), 1):
        if not isinstance(g, r.Mesh): continue
        pn = _panel_ex(g, W_HMIN)
        if not pn: continue
        pn['num'] = k
        top = pn['z0'] + pn['H']
        if pn['z0'] >= W_FLOOR_TOP - 100:
            two.append(pn); continue
        if top > W_FLOOR_TOP + 1:
            up = dict(pn); up['z0'] = W_FLOOR_TOP; up['H'] = top - W_FLOOR_TOP; up['from1F'] = True
            two.append(up)
            pn['poly'] = unary_union(kabe._parts(pn['poly'].intersection(box(-1e4, -1e4, 1e4, (W_FLOOR_TOP - pn['z0']) * S))))
            pn['H'] = W_FLOOR_TOP - pn['z0']; pn['clip'] = top
        one.append(pn)
    return one, two

def _box_cols():
    """階段の箱の柱（120 角、07 に入れない）→ 壁の一部の板にする（箱の壁は柱を含めて続いているので、柱の所に 1.2 mm のすき間を作らない）"""
    out = []
    for i, (nm_, g) in enumerate(((n_, g_) for n_, g_ in objs_named('22a_西館_柱') if '階段の箱' in n_)):
        b = g.GetBoundingBox(); c = np.array([(b.Min.X + b.Max.X) / 2, (b.Min.Y + b.Max.Y) / 2])
        u0, v0 = _uv(*c)
        # 弧の接線方向（正確に）：中心から c への向きに直角
        er = (c - np.array([CX, CY])) / np.linalg.norm(c - np.array([CX, CY])); et = np.array([-er[1], er[0]])
        if _uv(*(c + et * 10.0))[0] < u0: et = -et
        out.append(dict(poly=box(0, 0, 120 * S, (b.Max.Z - b.Min.Z) * S), A=c - et * 60, B=c + et * 60, T=120.0, z0=b.Min.Z, H=b.Max.Z - b.Min.Z, ax=et, num=1001 + i, boxcol=True))
    return out

def _pc_dir(p):
    d = np.array(p['B'], float) - np.array(p['A'], float); L_ = np.linalg.norm(d)
    return d / L_ if L_ > 1e-6 else np.array([1.0, 0.0]), L_

def _collinear_adjacent(c, e, L_, q, off_tol=45.0, gap_tol=40.0):
    """中心 c・向き e・長さ L_ の小さな板が、板 q の線の上で q に接している（端どうしが gap_tol 以内）か"""
    eq, Lq = _pc_dir(q)
    if abs(e @ eq) < 0.97: return False
    Aq = np.array(q['A'], float); nq = np.array([-eq[1], eq[0]])
    if abs((c - Aq) @ nq) > off_tol: return False
    s0, s1 = sorted([(np.array(q['A']) - Aq) @ eq, (np.array(q['B']) - Aq) @ eq])
    sc = (c - Aq) @ eq
    gap = max(s0 - (sc + L_ / 2), (sc - L_ / 2) - s1)
    return gap <= gap_tol

def reorient_stubs(pcs):
    """柱の際・梁の板の通り道の小さな板（長さが壁の厚さ 120 より短い）は、3dm の板の長い軸と壁の線の向きが合わないことがある
    （梁の板の下の H2400 の小壁：厚さ 91・長さ 120 など）。元の向きで隣の板と同じ線に続かず、90 度回すと続くなら回す。
    回した板が隣の板より 100 mm 以上高い所（窓の方立てなど、ガラスの縦材）は回さない（細いひれになるので作らない）"""
    for _ in range(5):
        changed = False
        anchors = {m_ for R_ in kabe.make_runs(pcs) if R_.L >= 3.0 for m_ in R_.members}      # 3 mm（実寸 300）以上の壁にまとまる板
        for p in pcs:
            e, L_ = _pc_dir(p)
            if L_ >= 300 or p.get('boxcol'): continue
            c = (np.array(p['A'], float) + np.array(p['B'], float)) / 2
            others = [q for q in pcs if q is not p and (q['num'] in anchors or q.get('reoriented'))]   # 続き先になれるのは、壁にまとまる板と向きを直した板だけ
            if any(_collinear_adjacent(c, e, L_, q) for q in others): continue
            e2 = np.array([-e[1], e[0]]); L2 = p['T']
            nb = [q for q in others if _collinear_adjacent(c, e2, L2, q)]
            if not nb: continue
            top = p['z0'] + p['H']
            if all(top > q['z0'] + q['H'] + 100 for q in nb): continue
            p['A'] = c - e2 * L2 / 2; p['B'] = c + e2 * L2 / 2
            p['poly'] = box(0, 0, L2 * S, p['H'] * S); p['T'] = L_; p['reoriented'] = True
            changed = True
        if not changed: break
    return pcs

def west_pieces_1f():
    one = west_pieces()[0] + _box_cols()
    return reorient_stubs(one)

# ---- 西館の架構（07 で作る物）との干渉
WCOLS = None
def west_col_infos():
    global WCOLS
    if WCOLS is None:
        WCOLS = []
        for nm_, g in objs_named('22a_西館_柱'):
            if '階段の箱' in nm_ or '受け材' in nm_: continue           # 階段の箱の 120 角・柱の受け材は 07 に入れない
            d = _col_info(g); d['frame'] = _frame_no(_ang(g)); d['name'] = nm_
            P = profile_rz(g, 0); foot = P[P[:, 1] < 1]
            d['foot'] = (foot[:, 0].min(), foot[:, 0].max())
            if g.ProfileCount == 1:                                   # 桁の穴の無い柱（キッチンの東の柱 180×400・外壁の 120 角）：断面は水平。半径の幅×頭までの箱
                d['prof'] = box(P[:, 0].min(), 0, P[:, 0].max(), g.GetBoundingBox().Max.Z)
                d['rc'] = (P[:, 0].min() + P[:, 0].max()) / 2
                d['ac'] = _ang(g)                                          # 道の始点は断面の隅なので、外接箱の中心の角度を使う
                d['foot'] = (P[:, 0].min(), P[:, 0].max())
            d['east'] = d['rc'] < RW_ + 5000
            WCOLS.append(d)
    return WCOLS

def west_col_keepout(d, zlo, zhi):
    """柱の置き場所（平面）：高さ zlo〜zhi で柱が占める半径の範囲 ＋ 床の穴（幅は足もとの幅＋10、厚さは 1.8）"""
    I = d['prof'].intersection(box(0, zlo, 1e7, zhi))
    rr = []
    if zlo <= 300: rr += [d['foot'][0] - 10, d['foot'][1] + 10]
    if not I.is_empty: rr += [I.bounds[0], I.bounds[2]]
    return _polar_rect(d['ac'], min(rr), max(rr), HOLE_T)

WPLATES = None
def west_plates():
    """梁の板（2 階の床梁 22c・梁 22b のうち 3.3 m より下に届くもの）と、低い桁（22d）。
    板：平面の長方形と、(s, z) の断面（s＝板の面の上で架構の線に沿う距離）。桁：平面の形と下面の高さ"""
    global WPLATES
    if WPLATES is not None: return WPLATES
    C = np.array([CX, CY]); out = []
    sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'view'))
    import tri as _tri
    fl = west_frame_lines()
    for lay in ('22c_西館_2階床梁', '22b_西館_梁'):
        for nm_, g in objs_named(lay):
            if '受け材' in nm_ or '出し梁' in nm_ or '登り梁' in nm_: continue
            P = profile_rz(g, 0)
            if P[:, 1].min() > 3300: continue
            p0 = np.array([g.PathStart.X, g.PathStart.Y]); p1 = np.array([g.PathEnd.X, g.PathEnd.Y])
            n = p1 - p0; th = np.linalg.norm(n); n = n / th
            er = np.array([-n[1], n[0]])
            if (p0 - C) @ er < 0: er = -er
            d_ = (p0 - C) @ n
            s = np.sqrt(np.maximum(P[:, 0] ** 2 - d_ ** 2, 0))
            prof = Polygon(np.column_stack((s, P[:, 1]))).buffer(0)
            sa, sb = s.min(), s.max()
            rect = Polygon([C + er * sa + n * d_, C + er * sb + n * d_, C + er * sb + n * (d_ + th), C + er * sa + n * (d_ + th)])
            k = _frame_no(_ang(g))
            ang_p = math.atan2(p0[1] - CY, p0[0] - CX); e_, w_ = fl.get(k, (None, None))
            ang_f = math.atan2(*(((e_ + w_) / 2 - C)[::-1])) if e_ is not None else ang_p
            out.append(dict(kind='板', name=nm_, frame=k, side='北' if ang_p < ang_f else '南', rect=rect, prof=prof, er=er, C=C, lay=lay))
    for nm_, g in objs_named('22d_西館_桁'):
        if nm_: continue
        b = g.GetBoundingBox()
        if b.Min.Z > 3300: continue
        T = _tri.tri_extrusion(g).reshape(-1, 3, 3)
        polys = [Polygon(t[:, :2]) for t in T if Polygon(t[:, :2]).area > 1.0]
        fp = unary_union([p_.buffer(0.5) for p_ in polys]).buffer(-0.5)
        u_, v_ = _uv((b.Min.X + b.Max.X) / 2, (b.Min.Y + b.Max.Y) / 2)
        out.append(dict(kind='桁', name='桁', frame=_frame_no(_ang(g)), fp=fp, zb=b.Min.Z, zt=b.Max.Z, v=v_))
    WPLATES = out
    return out

def west_hits(A, B, zlo, ztop, t=kabe.T_BOARD / S):
    """壁の線 A→B（厚さ t）が当たる梁の板・桁。返す：[(種類, 名前, 重なりの平面, 材の下面の高さ（実寸 mm、重なりの範囲の最低）, 番号, 側)]"""
    fp = footprint(A, B, t); out = []
    for pl in west_plates():
        if pl['kind'] == '板':
            ov = fp.intersection(pl['rect'])
            if ov.area <= 0.5: continue
            ss = [(np.array(q) - pl['C']) @ pl['er'] for q in ov.exterior.coords]
            xs = np.linspace(min(ss), max(ss), 25)
            under = min((lambda ln: ln.bounds[1] if not ln.is_empty else 1e9)(pl['prof'].intersection(LineString([(x, -1e4), (x, 1e5)]))) for x in xs)
            out.append(('板', pl['name'], ov, under, pl['frame'], pl['side'], 1e9))
        else:
            ov = fp.intersection(pl['fp'])
            if ov.area <= 0.5: continue
            out.append(('桁', '桁', ov, pl['zb'], pl['frame'], '', pl['zt']))
    return out

def check_wall_w(A, B, zlo, ztop, with_hole=True):
    """check_wall の西館版（build_walls に渡す）。柱は止める、梁の板・桁は endfix_w で局所的に切り欠くので、beam・keta は空で返す"""
    fp = footprint(A, B); res = dict(col=[], beam=[], keta=[], dist=1e9)
    for d in west_col_infos():
        ko = west_col_keepout(d, zlo if with_hole else 400, ztop)
        res['dist'] = min(res['dist'], fp.distance(ko))
        ov = fp.intersection(ko)
        if ov.area > 0.5:
            res['col'].append((d['frame'], '東' if d['east'] else '西', ov, ko))
    return res

def endfix_w(R_):
    """梁の板の下は、その部分だけ天端を（下面−5.0 mm）まで切り欠く（壁全体は下げない）。
    桁（平竹ひご）は、3dm の壁にある桁の通り道（穴）に合わせ、桁の高さ（下面〜上面）の材を重なる幅だけ抜く"""
    hits = west_hits(R_.A, R_.B, R_.bottom(), R_.top(), kabe.T_BOARD / S)
    for kind, nm_, ov, under, fr, sd, top in sorted(hits, key=lambda h: (h[2].centroid.x, h[2].centroid.y)):
        ss = [(np.array(q) - R_.A) @ R_.e for q in ov.exterior.coords]
        x0, x1 = min(ss) * S, max(ss) * S
        if kind == '板':
            lim = under - CLEAR_TOP
            cut = box(x0, R_.y_of(lim), x1, 1e4)
            what = f'梁{fr}{sd}の板の下（下面{under / 1000:.2f} m）は天端を{lim / 1000:.2f} mまで切り欠いた（x={x0:.1f}〜{x1:.1f}）'
        else:
            cut = box(x0, R_.y_of(under), x1, R_.y_of(top))
            what = f'桁の通り道（高さ{under / 1000:.2f}〜{top / 1000:.2f} m、x={x0:.1f}〜{x1:.1f}）を抜いた'
        reg = R_.poly.intersection(cut)
        if reg.is_empty or reg.area < 1e-3: continue
        R_.poly = unary_union(kabe._parts(R_.poly.difference(cut)))
        R_.notes.append(what)

def west_problems(runs, feet):
    """当たりが残っていないか。柱は重なり、梁の板・桁は切り欠いた後に材が残っていないか"""
    probs = []
    for R_ in runs + feet:
        bad = []
        bb = R_.poly.bounds; A_, B_ = R_.world(bb[0]), R_.world(bb[2])          # 足は短くしてあるので、板の形の端を使う
        cw = check_wall_w(A_, B_, R_.bottom(), R_.top())
        bad += [f'柱{fr}{sd}' for fr, sd, _, _ in cw['col']]
        for kind, nm_, ov, under, fr, sd, top in west_hits(R_.A, R_.B, R_.bottom(), R_.top()):
            ss = [(np.array(q) - R_.A) @ R_.e for q in ov.exterior.coords]
            y0 = R_.y_of(under - CLEAR_TOP) if kind == '板' else R_.y_of(under)
            y1 = 1e4 if kind == '板' else R_.y_of(top)
            if R_.poly.intersection(box(min(ss) * S, y0 + 1e-6, max(ss) * S, y1 - 1e-6)).area > 1e-3:
                bad.append(f'{"梁" + str(fr) + sd if kind == "板" else "桁"}')
        if bad: probs.append((R_, bad))
    return probs

def trim_foot_w(f, runs):
    """足が柱（床の穴を含む）や別の壁に重なるときは、重なる所を除いて壁の芯（x=4）を含む部分だけにする"""
    fp = footprint(f.A, f.B)
    ko = [('柱%d' % d['frame'], west_col_keepout(d, f.bottom(), f.top())) for d in west_col_infos()]
    ko += [('壁%d' % R_.id, footprint(R_.A, R_.B)) for R_ in runs if R_.id != f.foot_of]
    cuts = []
    for nm_, K in ko:
        ov = fp.intersection(K)
        if ov.area > 0.5:
            ss = [(np.array(q) - f.A) @ f.e * S for q in getattr(ov, 'geoms', [ov])[0].exterior.coords]
            cuts.append((min(ss), max(ss), nm_))
    if not cuts: return
    poly = f.poly
    for a_, b_, nm_ in cuts: poly = poly.difference(box(a_, -1, b_, 100))
    keep = [p_ for p_ in kabe._parts(poly) if p_.distance(Point(kabe.FOOT_LEN / 2, 0.1)) < 0.35]
    if keep:
        f.poly = unary_union(keep)
        f.notes.append('足を' + '・'.join(n_ for _, _, n_ in cuts) + 'を避けて短くした')

def assemble_w():
    """西館の 1 階の間仕切りを壁にまとめ、柱の手前で止め、梁の板・桁の下を切り欠き、交点に半欠きを入れ、孤立した壁に足をつける"""
    pcs, runs, t3, tiny = build_walls(west_pieces_1f, check_wall_w, endfix_w)
    Jt = kabe.find_joints(runs, t3); kabe.classify(Jt)
    ext = kabe.extend_stems(Jt); kabe.apply_extensions(runs, ext)
    for R_ in runs: endfix_w(R_)                       # 伸ばした所が梁の板に当たるなら、また切り欠く
    comps = kabe.components(runs, Jt)
    feet, fj = [], []
    nid = len(runs) + 1
    for c in comps:
        if kabe.is_braced(c): continue
        for R_ in c:
            for f, j in kabe.make_feet(R_, nid):
                trim_foot_w(f, runs)
                feet.append(f); fj.append(j); nid += 1
    allj = Jt + fj
    kabe.cut_joints(allj, WALL_KERF, CUT_W)
    probs = west_problems(runs, feet)
    for f in feet:
        bb = f.poly.bounds; fp = footprint(f.world(bb[0]), f.world(bb[2]))
        for R_ in runs:
            if R_.id != f.foot_of and fp.intersection(footprint(R_.A, R_.B)).area > 1.0:
                probs.append((f, [f'壁{R_.id}と重なる']))
    return dict(pcs=pcs, runs=runs, feet=feet, joints=allj, comps=comps, tiny=tiny, probs=probs, t3=t3, ext=ext)

def pin_w(P):
    """壁の線上の点 → (架構の番号, 架構の線から北へ mm（模型、弧に沿って）, 西の縁から mm（模型、半径方向）, u, v)
    架構の線＝西館の架構（柱の中心を結ぶ線）のうち角度がいちばん近いもの。西の縁＝西館の外壁（21）の外面の西の端（その点を通る半径の線の上）"""
    C = np.array([CX, CY]); fl = west_frame_lines()
    ang = {k: math.atan2(*(((e + w) / 2 - C)[::-1])) for k, (e, w) in fl.items()}
    aP = math.atan2(P[1] - CY, P[0] - CX); rP = math.hypot(P[0] - CX, P[1] - CY)
    wrap = lambda x: (x + math.pi) % (2 * math.pi) - math.pi          # 西は角度が ±π の境
    k = min(ang, key=lambda k_: abs(wrap(ang[k_] - aP)))
    a = wrap(ang[k] - aP) * rP * S                       # 北は角度の小さい方
    ray = LineString([C, C + np.array([math.cos(aP), math.sin(aP)]) * 3.0e5])
    ip = west_outer().exterior.intersection(ray)
    rs = [math.hypot(q.x - CX, q.y - CY) for q in getattr(ip, 'geoms', [ip])]
    b = (max(rs) - rP) * S if rs else float('nan')
    u, v = _uv(*P)
    return k, a, b, u, v

WOUTER = None
def west_outer():
    global WOUTER
    if WOUTER is None:
        w = plan('21_西館_外壁')
        w = max(getattr(w, 'geoms', [w]), key=lambda q: q.area)
        WOUTER = Polygon(w.exterior)
    return WOUTER

def interior_sheets_w():
    W_ = assemble_w()
    runs, feet = W_['runs'], W_['feet']
    items = [(str(R_.id), R_) for R_ in runs]
    for f in feet:
        par = next(r_ for r_ in runs if r_.id == f.foot_of)
        items.append((f'{par.id}{"A" if f.side == "A" else "B"}', _Tabbed(f, foot_ok_w())))
    shelf = kabe_layout(items)
    nsheet = 0; miss = []
    for si, lst in enumerate(shelf):
        nm = WALL_NAME_W if len(shelf) == 1 else f'{WALL_NAME_W}_{si + 1}'
        s = Sheet(nm, 600, 300,
                  '航空ベニヤ 0.6 300×600：西館の1階の間仕切り（番号は 10w_西館の室内の壁の配置図 と同じ。足は番号に A・B）。高さは床の上面から。半欠きは切り込み（上から／下から）。切り幅は0.20と仮定（T5 の結果が mokei.json に入るまで）。向きは元のまま、外接矩形が最小になるように詰めた（壁どうし2.5 mm以上）')
        s.tabs = True; s.show_used = True
        for n, tx, ty in lst:
            R_ = dict(items)[n]
            q = affinity.translate(R_.poly, tx, ty)
            for pp in kabe._parts(q):
                s.add(pp)
                s.tab_pts += _tab_points(pp)
            lp = max(kabe._parts(q), key=lambda p_: p_.area)
            pos = _label_pos(lp, n, 1.2) or _label_pos(lp, n, 0.9)
            hh = 1.2 if _label_pos(lp, n, 1.2) else 0.9
            if pos:
                _, lx, ly = pos
                for j, ch in enumerate(n):
                    for l in label_num(ch, lx + j * (hh * 0.6 + (1.2 - 1.2 * 0.6) * (hh / 1.2)), ly, hh): s.add(l, 'eng')
            else:
                miss.append(n)
        s.save()
        nsheet += 1
    plan_pdf_w(W_)
    write_table_w(W_, miss)
    return dict(壁=len(runs), 足=len(feet), 板=len(W_['pcs']), 交点=len(W_['joints']), 枚=nsheet, 番号を彫れない=miss, 問題=[(r_.id, b_) for r_, b_ in W_['probs']])

def plan_pdf_w(W_):
    """配置図（1/100、平面）：壁の線と番号、足、交点、柱と架構の番号。A3 に 100% で印刷すると模型と同じ大きさ"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    try:
        import fonts42
    except Exception:
        plt.rcParams['font.family'] = 'Noto Sans CJK JP'
        plt.rcParams['pdf.fonttype'] = 42
    fl = west_frame_lines(); ks = sorted(fl)
    e0, e1 = fl[ks[0]][0], fl[ks[-1]][0]
    ang = -math.atan2(e1[1] - e0[1], e1[0] - e0[0])
    out = west_outer()
    ub = to_sheet(out, ang, (0, 0)).bounds
    W_mm, H_mm = 420.0, 297.0
    off = (20 - ub[0], (H_mm - (ub[3] - ub[1])) / 2 - ub[1] + 6)
    ts = lambda g: affinity.translate(to_sheet(g, ang, (0, 0)), *off)
    path = os.path.join(OUT, '10w_西館の室内の壁の配置図.pdf')
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(W_mm / 25.4, H_mm / 25.4)); axp = fig.add_axes([0, 0, 1, 1])
        xs, ys = ts(out).exterior.xy; axp.plot(xs, ys, color='0.75', lw=0.5)
        for d in west_col_infos():
            q = ts(Point(CX + d['rc'] * math.cos(d['ac']), CY + d['rc'] * math.sin(d['ac'])))
            axp.plot([q.x], [q.y], 's', color='0.3', ms=2)
        for k in ks:
            e, w = fl[k]
            q = ts(Point(*e)); axp.text(q.x, q.y + 4.5, str(k), fontsize=6, color='0.2', ha='center', va='bottom')
            ln = ts(LineString([e, w])); xs, ys = ln.xy; axp.plot(xs, ys, color='0.85', lw=0.4, ls=':')
        for R_ in W_['runs'] + W_['feet']:
            foot = R_.foot_of is not None
            ln = ts(LineString([R_.A, R_.B])); xs, ys = ln.xy
            axp.plot(xs, ys, color='tab:blue' if foot else 'tab:red', lw=0.9 if foot else 1.4, solid_capstyle='butt')
            if not foot:
                mid = ln.interpolate(0.5, normalized=True)
                axp.text(mid.x, mid.y, str(R_.id), fontsize=5, color='tab:red', ha='center', va='center', bbox=dict(fc='white', ec='none', pad=0.3, alpha=0.8))
        for j in W_['joints']:
            q = ts(Point(*j.X)); axp.plot([q.x], [q.y], 'o', color='k', ms=1.6)
        axp.set_xlim(0, W_mm); axp.set_ylim(0, H_mm); axp.set_aspect('equal'); axp.axis('off')
        axp.text(20, 8, '室内の壁の配置図（西館の1階）：壁の線を赤、足を青、交点を黒の点。番号は 09w の板の番号、上の数字は西館の架構の番号（南から）。A3 に 100% で印刷すると模型と同じ大きさ', fontsize=7)
        pdf.savefig(fig); plt.close(fig)

def _two_floor_list():
    """2 階の間仕切り（数えるだけ）。24 のうち 2 階の分と、1・2 階ひと続きの板の 2 階の分、38 のうち西館の 2 階の壁"""
    _, two = west_pieces()
    L_ = []
    for p in two:
        ua, va = _uv(*p['A']); ub, vb = _uv(*p['B'])
        L_.append(('24', p['num'], ua, va, ub, vb, p['z0'], p['z0'] + p['H'], p['T'], p.get('from1F', False)))
    k = 0
    for g in objs('38_しつらえ_間仕切り・框・腰壁'):
        k += 1
        if not isinstance(g, r.Mesh): continue
        pn = _panel_ex(g, W_HMIN)
        if not pn: continue
        um, vm = _uv(*((pn['A'] + pn['B']) / 2))
        if vm >= 0.3 or pn['z0'] < W_FLOOR_TOP - 100: continue
        ua, va = _uv(*pn['A']); ub, vb = _uv(*pn['B'])
        L_.append(('38', k, ua, va, ub, vb, pn['z0'], pn['z0'] + pn['H'], pn['T'], False))
    return L_

W_MARK = '## 西館の1階'
def write_table_w(W_, miss):
    runs, feet, joints = W_['runs'], W_['feet'], W_['joints']
    pcs, probs = W_['pcs'], W_['probs']
    runof = {}
    for R_ in runs:
        for m_ in R_.members: runof[m_] = R_
    o = []
    o.append(f'{W_MARK}（09w・10w）\n')
    o.append('作った所：`mokei/laser.py` の「9w. 西館の室内の壁」（`python3 -c "import laser; print(laser.interior_sheets_w())"` を `mokei/` で。09w・10w とこの節だけを書き直す。本館の節は触らない）。模型作成。\n')
    o.append('### 前提\n')
    o.append('- 組み立ての順は本館と同じ：①間仕切りを床に立てる（壁どうしの半欠きで自立）→②架構（07 の西館の架構、接着せず差す）を上から下ろす→③外壁を貼る。だから間仕切りは柱（頭の丸みと床の穴を含む）を通れず、柱の手前の面で止める。柱は 07 に入る物（階段の箱の 120 角の柱・柱の受け材は作らないので避けない）。')
    o.append(f'- 材は航空ベニヤ0.6、切り幅{WALL_KERF}（0.6の試し切り T5 の結果が `data/mokei.json` に無いので仮の値。入れて作り直す）。切り込みの描く幅は、両側に木が残る所＝{kabe.T_BOARD}−{WALL_KERF}＝{CUT_W:.2f}、壁の端＝相手の厚さ−{WALL_KERF / 2:.1f}。切り込みの高さの境、T・L の面そろえ、足（T 字、長さ{kabe.FOOT_LEN:.0f} mm、高さは壁の端の半分で6 mmまで、長さ15 mm未満の壁はA端だけ）は本館の09と同じ。')
    o.append(f'- 天端は 2 階の床の下面（3.17 m）。3dm が 1・2 階ひと続きの板（階段の箱の壁 u30・u33、高さ約6.7 m）にしている所は、2 階の床の下で切って 1 階の分にした（2 階の分は下の一覧）。腰壁（h450）も拾う（本館は 600 以上だけ）。')
    o.append(f'- 梁の板・桁の下：2 階の床梁（22c）の板の下は、その部分だけ天端を（板の下面−{CLEAR_TOP / 10:.1f} mm）まで切り欠く（3dm が梁の板の下を H2400 の小壁にしているのと同じ形。壁全体は下げない）。')
    o += foot_note_lines(W_, foot_ok_w(), '12w の1階 上の層')
    o.append('- 西館の床（1.7×2＋基礎3）は未作成なので切り溝は使わない。**床の柱の穴は仮**：柱の足もとの幅＋0.2、厚さ1.8（本館の床の穴と同じ考え）。床ができたら `west_col_keepout` を合わせる。')
    o.append('- 針の印の座標：架構の番号（西館の架構、南から。架構8＝u21.33、9＝u24、…、17＝u48、18＝u50.57）、その架構の線（柱の中心を結ぶ線）から北へ何mm（弧に沿って、南は−）、西の縁から何mm（半径方向、東へ）。単位は模型のmm。印は壁の線（厚さの真ん中）の上。**西の縁＝西館の外壁（21）の外面の西の端**（その点を通る半径の線の上。西館の床の外形が決まったらそちらに替える）。\n')
    o.append('### 1. 3dmの板（24）と壁\n')
    o.append('| 板 | 場所（u, v m） | 高さ（m） | 厚さ | 壁 | 直し |')
    o.append('|---|---|---|---|---|---|')
    for p in pcs:
        zlo, zt = p['z0'], p['z0'] + p['H']
        ua, va = _uv(*p['A']); ub, vb = _uv(*p['B'])
        R_ = runof.get(p['num'])
        fix = '、'.join(R_.notes) if R_ and R_.notes else ''
        if p.get('clip'): fix = (fix + '；' if fix else '') + f'3dmは{p["clip"] / 1000:.2f} mまで。2階の床の下（{W_FLOOR_TOP / 1000:.2f} m）で切った'
        o.append(f'| {p["num"]} | u{ua:.2f}〜{ub:.2f}, v{va:.2f}〜{vb:.2f} | {zlo / 1000:.2f}〜{zt / 1000:.2f} | {p["T"]:.0f} | {R_.id if R_ else "（作らない）"} | {fix} |')
    o.append('')
    o.append('### 作らない板（要判断のもの）\n')
    for R_ in W_['tiny']:
        o.append(f'- 板{"・".join(map(str, R_.members))}：長さ{R_.L:.1f} mm（模型）の細い板（柱の際・戸の脇の小さな壁）。幅3 mm未満は作らない（本館と同じ）')
    o.append('')
    o.append('### 直したもの（壁ごと）\n')
    for R_ in runs:
        if R_.notes:
            o.append(f'- 壁{R_.id}（板{"・".join(map(str, R_.members))}）：' + '；'.join(R_.notes))
    o.append('')
    o.append('### 2. 壁と半欠きのかみ合い\n')
    o.append('| 壁 | 板 | 長さ×高さ（模型mm） | 高さ（床の上、m） | 交点（相手・形・自分の切り込み） |')
    o.append('|---|---|---|---|---|')
    for R_ in runs + feet:
        js = []
        for (j, frm, x, w, removed) in R_.joints:
            oth = j.S if R_ is j.R else j.R
            lab = oth.id if oth.foot_of is None else f'{oth.foot_of}{"A" if oth.side == "A" else "B"}'
            js.append(f'{lab}（{j.kind}・{"上から" if frm == "top" else "下から"}・x={x:.1f}・幅{w:.2f}）' + ('' if removed > 0.05 else '！材が無い'))
        b = R_.poly.bounds
        nm = str(R_.id) if R_.foot_of is None else f'{R_.foot_of}{"A" if R_.side == "A" else "B"}（足）'
        o.append(f'| {nm} | {"・".join(map(str, R_.members)) or "—"} | {b[2]:.1f}×{b[3]:.1f} | {R_.bottom() / 1000:.2f}〜{R_.top() / 1000:.2f} | {"、".join(js) or "なし"} |')
    o.append('')
    iso = [c for c in W_['comps'] if not kabe.is_braced(c)]
    o.append(f'孤立した壁（向きの違う壁と組まない、{sum(len(c) for c in iso)}枚）に足をつけた：' + ('、'.join(str(r_.id) for c in iso for r_ in c) or 'なし'))
    o.append('')
    if probs:
        o.append('### 要判断（まだ当たる所）\n')
        for R_, b_ in probs:
            o.append(f'- 壁{R_.id if R_.foot_of is None else str(R_.foot_of) + R_.side}：{"、".join(b_)}')
        o.append('')
    o.append('### 3. 針の印の表\n')
    o.append('西館の床に鉛筆の針で打つ点（床ができたら）。壁の線の端と交点。A→B は壁の線の向き。\n')
    o.append('| 壁 | 点 | 架構 | 架構の線から北へ（mm） | 西の縁から（mm） | u, v（m） |')
    o.append('|---|---|---|---|---|---|')
    for R_ in runs + feet:
        nm = str(R_.id) if R_.foot_of is None else f'{R_.foot_of}{"A" if R_.side == "A" else "B"}'
        pts = [('A端', R_.A), ('B端', R_.B)]
        for (j, frm, x, w, removed) in R_.joints:
            oth = j.S if R_ is j.R else j.R
            lab = oth.id if oth.foot_of is None else f'{oth.foot_of}{"A" if oth.side == "A" else "B"}'
            pts.append((f'交点{lab}', j.X))
        for lab, P in sorted(pts, key=lambda t: (t[1] - R_.A) @ R_.e):
            k, a, b, u, v = pin_w(P)
            o.append(f'| {nm} | {lab} | {k} | {a:+.1f} | {b:.1f} | {u:.2f}, {v:.2f} |')
    o.append('')
    if miss:
        o.append('番号を彫れなかった板：' + '、'.join(miss) + '\n')
    two = _two_floor_list()
    o.append(f'### 4. 2階の間仕切り（作らない・数えただけ。1階が済んでから別に判断）\n')
    o.append(f'{len(two)}枚（24：{sum(1 for t in two if t[0] == "24")}、38：{sum(1 for t in two if t[0] == "38")}。「ひと続き」＝3dm では1階から続く板の2階の分）。\n')
    o.append('| レイヤー | 板 | 場所（u, v m） | 高さ（m） | 厚さ | 備考 |')
    o.append('|---|---|---|---|---|---|')
    for lay, num, ua, va, ub, vb, z0, z1, T_, cont in two:
        o.append(f'| {lay} | {num} | u{ua:.2f}〜{ub:.2f}, v{va:.2f}〜{vb:.2f} | {z0 / 1000:.2f}〜{z1 / 1000:.2f} | {T_:.0f} | {"1階からひと続き" if cont else ""} |')
    o.append('')
    o.append('1階の板で拾わなかったもの：38 の 103・104（階段の二つの列のあいだの柵、厚さ約30、縦格子の扱い）。24 の小さな柱・戸まわりの板は上の「作らない板」。')
    o.append('')
    sec = '\n'.join(o) + '\n'
    path = os.path.join(ROOT, 'mokei', '室内の壁_位置表.md')
    txt = open(path).read() if os.path.exists(path) else ''
    if W_MARK in txt: txt = txt[:txt.index(W_MARK)].rstrip('\n') + '\n\n'
    elif txt: txt = txt.rstrip('\n') + '\n\n'
    open(path, 'w').write(txt + sec)

# ================= 台の表面（シナ 3）：建物の穴・青の彫り・塀と柵の足の溝 =================
# 10-31 の頼み（模型作成）：表面の彫りと溝は mokei/表面の彫り一覧.md のとおり。仮の出力（T7 の結果と、必須・重要の判断で直す）。
#   python3 laser.py dai        … 01台_表面_シナ3.svg と 01台_溝の試し片_シナ3.svg だけを書く（ほかの部品は触らない）
# 座標：3dm の xy（mm）。台は A1（841×594）に収めるため、DAI_ROT だけ回す（北が右上）。回して縮尺 S をかけ、左上に寄せる
SAN_SHEET = (841, 594)                           # 台の板（A1）。dai_outline_sheet() が使う（桟をやめたとき定数が消えて dai-naka が動かなくなっていた：11-02）
DAI_ROT = -38.5                                  # 度。川側の辺を水平に（63 m × 56 m、道路の窓を足して 68×56 m → 682×560 mm）
DAI_ROAD_WIN = (-45000, -75000, -24000, -30000)  # 道路を見せる窓（3dm mm）：西の道路の、お向かいの張り出しと狭い所をふくむ所
DAI_HOLE_SHRINK = 0.11                           # 建物の穴は、切り幅の分（シナ 3：0.22）だけ小さく描く＝片側 0.11（模型 mm）
# 台の板は長方形（11-02、ユーザー）：横＝敷地の南西の辺（12 m）の線から、さらに 8 m 西（道路の向こう側）まで、東は敷地の東の辺まで。
# 縦＝A1 いっぱい（板の縁から 3 mm ずつ残して 588）：下に護岸の谷積み、上に道を数 mm（敷地境界の線）。数字は dai_tx で回したあとの模型 mm（北の角が原点、川側の辺が y＝−560）
DAI_RECT_X = (-730.0, 0.0)                 # 西は 10 m（横断歩道を渡りきる所まで。8 m では帯が板の縁で切れる：11-02）
DAI_SHIFT_X = 20.0                               # 板の左右にガムテープで止める余白（11-02、ユーザー）：表面・中の層・窪みの 3 つとも、右へ 20 mm ずらす（同じ原点を保つ）
DAI_RECT_TOP = 4.0                               # 敷地の北の辺より上に出す（道と敷地境界の線を見せる）
DAI_RECT_H = 588.0                               # 594 − 3×2
DAI_RECT = (DAI_RECT_X[0], DAI_RECT_TOP - DAI_RECT_H, DAI_RECT_X[1], DAI_RECT_TOP)
DAI_ROAD_NEAR = 100                              # 道路の縁のうち、敷地境界と重なる線（これ（3dm mm）以内）は彫らない。南西の角から先、境界から離れていく縁（橋の袂の三角形の道の側の辺）は彫る
DAI_TREE_CROWN_ROAD = ('お向かいの張り出しの木',)
DAI_SLOT_LEN = 4.0                               # 足の溝の長さ（塀に沿う向き、模型 mm）
DAI_SLOT_W = 0.4                                 # 足の溝の幅（描く幅）。11-02 の試し片：0.4＝ぎちぎちだが入る、0.5＝簡単に抜ける、0.6＝がばがば → 0.4
DAI_SLOT_PITCH = 40.0                            # 足のおき：30〜40 mm（この値を超えない最少の本数に等分）
DAI_SLOT_HOLE_MIN = 3.0                          # 北の塀（読書の庭）の足の溝は、建物の穴（描く穴）の縁から溝の縁まで 3 mm 以上離す（塀の線に沿って穴から遠ざける。足のおきは DAI_SLOT_PITCH 以下、端から DAI_SLOT_INSET 以上）
DAI_SLOT_HOLE_WEST = 3.5                          # ひろば西の塀は 3.5 mm（11-02、ユーザー：3 mm 以上、できれば 3.5）
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

def dai_inv(g):
    """dai_tx の逆：回して縮めた模型 mm → 3dm mm"""
    return affinity.rotate(affinity.scale(g, 1 / S, 1 / S, origin=(0, 0)), -DAI_ROT, origin=(0, 0))

def dai_rect_3dm():
    from shapely.geometry import box as _box
    return dai_inv(_box(*DAI_RECT))

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

def dai_zebra(road, BAR=4.5, GAP=4.5, LEN=40.0, EDGE=3.0):
    """横断歩道の帯（模型 mm、回したあとの座標で作って 3dm に戻す）。橋の袂の三角形：敷地の南西の角（−630, −440）から、道の近い側の縁が川側の辺（y −560）まで続く線。その長さの半分の所から、縁に直角に道を渡る"""
    from shapely.geometry import LineString as _LS, Polygon as _Pg
    rb = dai_tx(road.boundary)
    reg = box(-720, -560, -628, -436)
    segs = [g for g in getattr(rb.intersection(reg), 'geoms', [rb.intersection(reg)]) if g.geom_type == 'LineString']
    E = None
    for s_ in segs:
        cs = [c for c in s_.coords]
        for i, c in enumerate(cs):
            if abs(c[0] + 630) < 0.5 and abs(c[1] + 440) < 0.5: E = _LS(cs[i:]); break
        if E is not None: break
    assert E is not None, '近い側の縁が見つからない'
    P0 = np.array(E.interpolate(0.5, normalized=True).coords[0])
    cs = np.array(E.coords); L_ = 0.0; r_ = None
    for a_, b_ in zip(cs[:-1], cs[1:]):
        d_ = np.linalg.norm(b_ - a_)
        if L_ + d_ >= E.length / 2 - 1e-9: r_ = (b_ - a_) / d_; break
        L_ += d_
    n_ = np.array([r_[1], -r_[0]])
    if n_[0] > 0: n_ = -n_                                           # 道の中（西）へ
    far = rb.difference(E.buffer(1.0))
    ray = _LS([tuple(P0 + n_ * 0.5), tuple(P0 + n_ * 400)])
    hit = ray.intersection(far)
    hs = [np.linalg.norm(np.array(g.coords[0]) - P0) for g in getattr(hit, 'geoms', [hit]) if not g.is_empty and g.geom_type == 'Point']
    W = min(hs)
    N = int((W - 2 * EDGE + GAP) // (BAR + GAP)); t0 = (W - (N * (BAR + GAP) - GAP)) / 2
    bars = []
    for k in range(N):
        c0 = P0 + n_ * (t0 + k * (BAR + GAP)); c1 = P0 + n_ * (t0 + k * (BAR + GAP) + BAR)
        bars.append(_Pg([tuple(c0 - r_ * LEN / 2), tuple(c1 - r_ * LEN / 2), tuple(c1 + r_ * LEN / 2), tuple(c0 + r_ * LEN / 2)]).exterior)
    print('横断歩道：P0', [round(v, 1) for v in P0], '渡る長さ', round(W / 10, 2), 'm、帯', N, '本、向き', round(math.degrees(math.atan2(r_[1], r_[0])), 1), '°')
    return dai_inv(unary_union(bars))

def dai_features():
    """台の表面に載せるものを集める。戻り：dict（名前→{kind, prio, geom（3dm mm）, layer, note}）。
    kind：hole（切る穴）／outline（外形を切る）／line（青の彫り）／slots（足の溝、runs＝中心線の列）／marks（木の位置、点）"""
    from shapely.geometry import LineString, Point as _Pt, box as _box
    F = {}
    site = Polygon(SITE_OUTER)
    # --- 建物の穴（表面＝GL に、ベタ基礎がはまる）
    import kirita as _K
    found = _K.cut_found()          # 本館の穴は、今の 3dm の floors() の found ではなく、切った 05＋05b の外形（11-02：切ったものは今の 3dm と 15 mm 違い、島が 3 つできる）
    close = lambda g: g.buffer(120, join_style=2).buffer(-120, join_style=2)
    west = close(unary_union([plan('31_1F_遊戯室'), plan('32_1F_キッチン'), plan('33_1F_東の帯（はだし ±0、ホールと一続き）'), plan('36_1F_階段')]))
    honkan = found
    both = unary_union([honkan, west])
    F['本館の穴'] = dict(kind='hole', prio='必須', layer='12〜15・52（床）', geom=honkan, note='切った 05＋05b のベタ基礎の外形（kirita.cut_found()）')
    F['西館の穴'] = dict(kind='hole', prio='必須', layer='31〜33・36（床）', geom=Polygon(west_f1_outline().exterior).difference(honkan.buffer(30)), note='西館のベタ基礎（表面から抜けた板）：西館の床（12w）の 1 階の外形（更衣 57 を含む）と同じ外周（11-02）')
    # --- 外形（台）
    road = dai_road()
    rect = dai_rect_3dm()
    outline = rect
    F['台の外形'] = dict(kind='outline', prio='必須', layer='00・03', geom=outline, note='長方形：横＝敷地の南西の辺の線から 8 m 西〜東の辺、縦＝A1 いっぱい（下＝護岸、上＝道を数 mm）')
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
    rb = road.boundary.intersection(rect).difference(site.buffer(DAI_ROAD_NEAR)).difference(dai_inv(box(DAI_RECT[0], DAI_RECT[1], DAI_RECT[2], -560.0)))      # 道の向こう側の縁だけ（近い側の縁は敷地境界と二重になる）
    F['道路の縁'] = dict(kind='line', prio='必須', layer='03', geom=rb, note='道の向こう側の縁（板の範囲で切る）。お向かいの張り出しと道の狭い所をふくむ')
    sb = LineString(SITE_OUTER + [SITE_OUTER[0]]).difference(rect.exterior.buffer(150))     # 板の縁と重なる辺（東の辺）は線にしない
    F['敷地境界'] = dict(kind='line', prio='必須', layer='00', geom=sb, note='敷地境界（外側の線）。道・護岸との境')
    # --- 護岸の谷積み（川側の辺の外、板の下の縁まで）：45° の格子、石 約 35 cm（T4 の谷積みと同じ）
    x0, y0, x1, y1 = DAI_RECT
    ry = -560.0                                                      # 川側の辺（回したあと）
    bank = box(x0, y0, x1, ry); lns = []
    for kk in np.arange(x0 - (ry - y0) - 3.5, x1 + 3.5, 3.5):
        lns += [LineString([(kk, y0), (kk + (ry - y0), ry)]), LineString([(kk + (ry - y0), y0), (kk, ry)])]
    pat = unary_union([l.intersection(bank.buffer(-0.5)) for l in lns])
    top = LineString([(x0, ry), (-630.0, ry)])                        # 川側の辺の線（敷地境界の続き、南西の辺より西）
    F['護岸の谷積み'] = dict(kind='line', prio='必須', layer='02', geom=unary_union([dai_inv(pat), dai_inv(top)]), note='川側の辺の外の護岸を上から見た模様（谷積み、45° の格子）')
    # --- 横断歩道（配置図 1/200 と同じ決め：西の道、橋の袂の三角形の道の側の辺の中ほどから道に直角、帯 0.45・すき間 0.45・長さ 4.0 m、向こう側の縁まで、道の真ん中にそろえる。present/tools/oudan.py）
    F['横断歩道'] = dict(kind='line', prio='必須', layer='03', geom=dai_zebra(road), note='白い帯の輪郭（帯 4.5×40 mm）')
    # --- 道の向こう側の樹冠（お向かい）
    cr = [(nm, g) for nm, g in _pf('77c_') if isinstance(g, r.Brep) and (_bb(g)[0] < -26000 and _bb(g)[3] < -20000)]
    F['お向かいの樹冠'] = dict(kind='line', prio='必須', layer='77c', geom=unary_union([Point((_bb(g)[0] + _bb(g)[3]) / 2, (_bb(g)[1] + _bb(g)[4]) / 2).buffer((_bb(g)[3] - _bb(g)[0]) / 2, 32).exterior for _, g in cr]), n=len(cr), note='道の向かい側の木の樹冠（線）')
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
    s.extra_dx = DAI_SHIFT_X
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
    # 西館の柱のほぞ穴（11-02）：西館のベタ基礎＝この「西館の穴」（西館の床 12w の外形、更衣を含む）から抜けた板。柱 24 本（本館の 05 と同じ描き寸法 1.64×2.1）を、切り抜き片の内側に。
    # 穴の外になるのは架構 u21.33 の南東の柱 1 本だけ（床が無い所）：その 1 本は表面の板に直接切る（下の print）
    hs_w = F['西館の穴']['geom'].buffer(-DAI_HOLE_SHRINK / S, join_style=2)
    for mo, (g_, kind_, top_) in zip(dai_west_mortises(T), west_cols()):
        s.add(mo, 'cut')
        m3 = _wcol_rect(g_, MORTISE_W, MORTISE_T)
        if not hs_w.contains(m3):
            print('西館のほぞ穴が切り抜き片の外（表面の板に直接）：', kind_, [round(v_, 2) for v_ in _uv_of(m3.centroid.x, m3.centroid.y)])
    # 彫る
    n_eng = {}
    for k, v in F.items():
        if k.startswith('_') or v['kind'] != 'line' or v['prio'] == '（省く）': continue
        g = v['geom'].difference(hole_keep.buffer(0)) if k not in ('道路の縁',) else v['geom']
        g = g.intersection(dai_rect_3dm())
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
    holes_m = T(holes)
    outline_m = T(F['台の外形']['geom']); outline_m = outline_m if outline_m.geom_type == 'Polygon' else max(outline_m.geoms, key=lambda g: g.area)
    for nm_, ln, pr, _ in dai_fence_runs(F):
        L = T(ln); ps = dai_slot_positions(L)
        if min(outline_m.exterior.distance(p) for p in ps) < 2.5:            # 台の縁に重なる柵（公園の鉄柵）は溝にできない
            n_skip.append(nm_); continue
        dd = [L.project(p) for p in ps]
        if nm_.startswith('北の塀（読書の庭）') or nm_.startswith('ひろば西の塀'):                                  # 穴の縁に近い足は、塀の線に沿って穴から遠ざける（近いほうの向きに、最小の動きで）
            hd = lambda d: holes_m.distance(dai_slot_geom(L, d, DAI_SLOT_W, DAI_SLOT_LEN))
            for i, d0 in enumerate(dd):
                hmin = DAI_SLOT_HOLE_WEST if nm_.startswith('ひろば西の塀') else DAI_SLOT_HOLE_MIN
                if hd(d0) >= DAI_SLOT_HOLE_MIN: continue
                lo = dd[i - 1] if i > 0 else None; hi = dd[i + 1] if i + 1 < len(dd) else None
                for k in range(1, 400):
                    ok = None
                    for sg in (1, -1):
                        d = d0 + sg * 0.05 * k
                        if d < DAI_SLOT_INSET or d > L.length - DAI_SLOT_INSET: continue
                        if (lo is not None and d - lo > DAI_SLOT_PITCH) or (hi is not None and hi - d > DAI_SLOT_PITCH): continue
                        if hd(d) >= hmin: ok = d; break
                    if ok is not None: break
                assert ok is not None, (nm_, i)
                print('足の溝を穴から遠ざけた：', nm_, i, f'{d0:.2f} → {ok:.2f}（動き {ok - d0:+.2f}）穴の縁から {hd(d0):.2f} → {hd(ok):.2f}')
                dd[i] = ok
        for d in dd:
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
    s = Sheet('01台_溝の試し片_シナ3', 70, 40, 'シナ 3 の端：塀の足の溝 描く幅 0.4・0.5・0.6（各 3 本、長さ 4.0）。足つきの帯は別ファイル（01台_溝の試し片_帯_航空ベニヤ0.6、材が違うので）。速度 12・出力 16%（T2）')
    s.add(box(0, 0, 70, 40), 'ref')
    s.tabs = False
    texts = []
    for i, w in enumerate((0.4, 0.5, 0.6)):
        y = 36 - i * 5
        for j in range(3):
            x = 6 + j * 8
            s.add(box(x, y - w / 2, x + DAI_SLOT_LEN, y + w / 2), 'cut')
        for l in label_num(i + 1, 1.0, y - 1.0, 2.0): s.add(l, 'eng')
        texts.append((30, y - 0.5, f'{i + 1}：描く幅 {w}', 2))
    s.save(texts)
    # 足つきの帯：高さ 6、足 4.0×2.0（実際の足）、おき 8。材が違う（航空ベニヤ 0.6）ので別ファイル＝原点合わせを分ける（ユーザー 11-02）
    s2 = Sheet('01台_溝の試し片_帯_航空ベニヤ0.6', 70, 14, '航空ベニヤ 0.6 の端：塀の足つきの帯（足 4.0×2.0・おき 8）。赤＝切る、速度 40・出力 10%（T5）')
    s2.add(box(0, 0, 70, 14), 'ref')
    s2.tabs = False
    body = box(0, 4, 60, 10)
    feet = [box(5 + k * 8, 2, 5 + k * 8 + DAI_SLOT_LEN, 4) for k in range(7)]
    s2.add(unary_union([body] + feet).buffer(0), 'cut')
    s2.save([(1, 11.5, '足 4.0×2.0・おき 8', 2)])


# ================= 天の川の縁（床の上の層 FL+0）を、今の設計の形に合わせる（11-02、ユーザーの案） =================
# 切った 04 の上の層は、天の川の縁が直線。今の 3dm は天の川をかたどった曲線。
#   天の川が広い所（切った板に材があり、今の設計には無い）：今から切り取る（01台_本館の窪みと足の溝 に赤の線）
#   天の川が狭い所（今の設計にあって、切った板に無い）：別の板（12w のシナ 1.7）で継ぎ足し片を切る
def laser_uv_of_poly(g):
    c = g.centroid
    return _uv_of(c.x, c.y)

AMANO_FULL = True                       # 天の川の曲線を端から端まで切る（False なら曲線より材が出る所だけ）
AMANO_EXT = 500.0                       # 切り取る線の端を、道の縁より先へ延ばす量（実寸 mm＝模型 5 mm）。11-02：切った板の縁が、図の縁より約 3 mm 先にあった

def amano_edit():
    """戻り：(切り取る線の LineString の列（3dm の座標、実寸 mm、端は板の外へ少し延ばす）, 継ぎ足し片の Polygon の列（3dm の座標）)"""
    import kirita as _K
    cu = _K.cut_floor('upper'); nu = floors()[0]
    pits = unary_union([Point(*_uv_xy(u, 7.5)).buffer(1500) for u in (36.0, 45.0, 54.0)])
    op = lambda g: g.buffer(-100).buffer(100)
    ex = op(cu.difference(nu)).difference(pits); mi = op(nu.difference(cu)).difference(pits)
    ex = [g for g in getattr(ex, 'geoms', [ex]) if g.area > 2e4]
    mi = [g for g in getattr(mi, 'geoms', [mi]) if g.area > 2e4]
    from shapely.ops import linemerge
    lines = []
    if AMANO_FULL:
        # 11-02 ユーザーの案：天の川の北の縁の曲線を、端から端まで全部切る（材のある所だけが切れ、縁の位置の誤差に左右されない）。
        # 線は切り幅の半分（模型 0.1 mm）だけ天の川の側へ寄せる：残る板（北）の縁が曲線に来る
        a_ = plan('15_本館_あまのがわ（土足 −150）').intersection(annulus())
        a_ = max(getattr(a_, 'geoms', [a_]), key=lambda g: g.area)
        north = max(getattr(nu, 'geoms', [nu]), key=lambda g: _uv_of(g.centroid.x, g.centroid.y)[0])
        ring = a_.buffer(-10).exterior.intersection(north.exterior.buffer(40))
        mm = linemerge(ring) if ring.geom_type == 'MultiLineString' else ring
        for ln in [max(([mm] if mm.geom_type == 'LineString' else list(mm.geoms)), key=lambda q: q.length)]:   # 角の細かい切れ端は捨て、いちばん長い 1 本
            c = list(ln.coords)
            a0 = np.array(c[0]) - np.array(c[3]); a1 = np.array(c[-1]) - np.array(c[-4])
            c = [tuple(np.array(c[0]) + a0 / np.linalg.norm(a0) * AMANO_EXT)] + c + [tuple(np.array(c[-1]) + a1 / np.linalg.norm(a1) * AMANO_EXT)]
            lines.append(LineString(c))
        return lines, mi
    for g in ex:
        ring = g.buffer(-10).exterior                       # 切り幅の半分（模型 0.1 mm）だけ、切り取る側へ寄せた線：残る板の縁が設計線に来る
        path = ring.difference(cu.boundary.buffer(15))      # 切った板の縁に沿う所は切らない
        for ln in ([path] if path.geom_type == 'LineString' else [q for q in path.geoms if q.geom_type == 'LineString'] if path.geom_type in ('MultiLineString', 'GeometryCollection') else []):
            c = list(ln.coords)
            if len(c) < 2: continue
            a0 = np.array(c[0]) - np.array(c[1]); a1 = np.array(c[-1]) - np.array(c[-2])
            c = [tuple(np.array(c[0]) + a0 / np.linalg.norm(a0) * AMANO_EXT)] + c + [tuple(np.array(c[-1]) + a1 / np.linalg.norm(a1) * AMANO_EXT)]
            lines.append(LineString(c))
    return lines, mi

def dai_pit_sheets():
    """本館 3〜5歳の「あつまりの皿」（φ2.4 m、u36・45・54、v7.5）を、床の塊（上の層 1.7・下の層 1.7・基礎 3.0）に貫通して切るデータ（11-02、ユーザーの案）。
    手順：表面（01台_表面）を切る→本館の穴の切り抜き片を外し、切った本館の床（剥がして 1 枚ずつ）を穴にはめる→この円を、表面と同じ原点で、材ごとの出力で切る。
    表面・中の層と同じ座標（dai_outline_sheet）。黒＝参考（板の外形・本館の穴、送る前に消す）、赤＝切る（円 3 つ）。穴は切り幅の分だけ小さく描く"""
    out, T, F = dai_outline_sheet()
    s = Sheet('01台_本館の窪みと足の溝_シナ1.7', 841, 594, '本館の床の窪み（あつまりの皿 φ2.4 m）の円 3 つ。表面と同じ原点・同じ位置。表面の本館の穴にはめた床 1 枚ずつ（上の層 1.7・下の層 1.7・基礎 3.0）を、材ごとの出力で切る。黒は参考')
    s.add(box(0, 0, 841, 594), 'ref')
    s.tabs = False; s.no_shift = True
    s.add(out.exterior, 'ref')
    h_ = T(F['本館の穴']['geom'])
    for g in getattr(h_, 'geoms', [h_]): s.add(g.exterior, 'ref')
    # 参考：切った床 04 の上の層（FL+0）の板の輪郭（実際に切った形。天の川の縁は直線）と、天の川（通り土間、土足 −150）の輪郭。位置合わせの確認用（切らない）
    import kirita as _Kr
    ref_u = T(_Kr.cut_floor('upper')); ref_a = T(unary_union([plan('15_本館_あまのがわ（土足 −150）')]).intersection(annulus()))
    for g in getattr(ref_u, 'geoms', [ref_u]):
        s.add(g.exterior, 'ref')
    for g in getattr(ref_a, 'geoms', [ref_a]):
        if g.geom_type == 'Polygon': s.add(g.exterior, 'ref')
    R = 1200.0 * S - 0.1                                              # 半径 12.0 − 切り幅の半分（0.1、1.7 は 0.20・3.0 は 0.22）
    cs = []
    for u in (36.0, 45.0, 54.0):
        c = T(Point(*_uv_xy(u, 7.5))).coords[0]; cs.append(c)
        s.add(Point(*c).buffer(R, 128).exterior, 'cut')
    # 足の溝（短い溝）：孤立した壁の足の下。床のいちばん上の 1.7 の層だけ貫通
    W_ = assemble(); slots = []
    for f in W_['feet']:
        sw = foot_slot_world(f, foot_ok_h()[1])
        if sw is None: continue
        sl = foot_slot_poly(sw[0], sw[1], T)
        slots.append((f.id, sl)); s.add(sl.exterior, 'cut')
    wp = wall_tab_plan(W_, foot_ok_h_wall()); nw = 0
    for R_ in W_['runs']:
        for x in wp.get(R_.id, []):
            sl = foot_slot_poly(R_.world(x), R_.e, T); slots.append(('壁%d' % R_.id, sl)); s.add(sl.exterior, 'cut'); nw += 1
    # 原点の目印（11-02 ユーザー承認）：板の左上の角（表面の切る線の角と同じ点）に、1 mm の斜めの彫り。切る線の範囲の角を板の角にそろえる
    ob = out.bounds
    s.add(LineString([(ob[0], ob[3]), (ob[0] + 1.0, ob[3] - 1.0)]), 'eng')
    am_lines, am_patch = amano_edit()
    for ln in am_lines:
        s.add(T(ln), 'cut')
    s.save([(8, 8, '本館の窪み 円 3 つ（φ23.8 を描く＝実際 φ24.0）と、足・壁の溝 %d か所（4.0×0.4）、天の川の曲線 %d 本。左上の角の彫りは原点の目印（彫り 123/12%%）。1.7 は 20/13%%' % (len(slots), len(am_lines)), 4)])
    inside = [i for i, sl in slots if h_.buffer(0).contains(sl)]
    return dict(天の川の切り取り線=len(am_lines), 継ぎ足し片=[round(g.area / 1e4, 1) for g in am_patch], 足と壁の溝=len(slots), うち壁=nw, 穴の中=len(inside), 穴の外=[i for i, _ in slots if i not in inside], 円と重なる=[i for i, sl in slots if any(sl.intersects(Point(*c).buffer(1200.0 * S)) for c in cs)], 中心=[tuple(round(v, 2) for v in c) for c in cs], 描く直径=round(2 * R, 2), 本館の穴の中=all(h_.buffer(0).contains(Point(*c).buffer(1200.0 * S)) for c in cs))

# ================= 台の中の層（シナ 3）と桟（シナ 3 の縦の板） =================
# 11-02 の頼み（模型作成）：表面（01台_表面）の下に中の層（ほぞ穴のみ）。
#   python3 laser.py dai-naka   … 01台_中の層_シナ3.svg だけ
# 向き・位置：どちらも表面と同じ（DAI_ROT、外形の左上を板の左上から 3 mm）。外形は dai_features() の「台の外形」そのまま。
# 桟は作らない（ユーザー 11-02）。台は表面 3 ＋ 共通地盤 3 の貼り合わせ
def dai_outline_sheet():
    """台の外形を、表面・中の層・桟に共通の板の座標（模型 mm、y 上向き、左上から 3 mm）で。戻り：(外形 Polygon, 変換 g→板の座標)"""
    F = dai_features()
    o = dai_tx(F['台の外形']['geom'])
    if o.geom_type != 'Polygon': o = max(o.geoms, key=lambda g: g.area)
    b = o.bounds
    dx, dy = Sheet.MARGIN - b[0] + DAI_SHIFT_X, (SAN_SHEET[1] - Sheet.MARGIN) - b[3]
    T = lambda g: affinity.translate(dai_tx(g), dx, dy)
    return T(F['台の外形']['geom']), T, F

def dai_mortises(T):
    """本館の柱 40 本のほぞ穴（切った 05 と同じ位置・描いた寸法 1.64×2.1。南北の妻の 4 本は 05b の継ぎ足しの所の穴）を、板の座標で"""
    import kirita as _K
    return [T(_K.mortise_world(side, k)) for side in 'EW' for k in range(1, 21)]

def dai_west_mortises(T):
    """西館の柱 24 本（架構の柱 22＋キッチンの東の骨格の柱 2）のほぞ穴（1.64×2.1）を、板の座標で。表面・中の層に同じ位置"""
    return [T(mo) for mo in west_mortises()]

def dai_naka_sheets():
    out, T, F = dai_outline_sheet()
    ms = dai_mortises(T)
    wm = dai_west_mortises(T)
    ms = ms + wm
    assert all(abs(m.area - laser_mortise_area()) < 1e-6 for m in ms)
    s = Sheet('01台_中の層_シナ3', 841, 594, 'シナ 3 A1：台の中の層。外形は表面（01台_表面）と同じ形・同じ向き・同じ位置。穴は柱のほぞ穴だけ：本館 40（切った 05 と同じ 1.64×2.1）＋西館 24（同じ描き寸法、表面の西館の穴と同じ位置）')
    s.add(box(0, 0, 841, 594), 'ref')
    s.extra_dx = DAI_SHIFT_X
    s.tabs = False
    s.add(out.difference(unary_union(ms)), 'cut')
    s.save([(8, 8, '台の中の層 シナ3：外形は表面と同じ。ほぞ穴 64（本館 40・西館 24）。北は右上。表面とは別の A1（同じ板から切れない）', 4)])
    b = out.bounds
    return dict(外形=(round(b[2] - b[0], 1), round(b[3] - b[1], 1)), ほぞ穴=len(ms), 切る長さ=round(out.exterior.length + sum(m.exterior.length for m in ms), 1))

def laser_mortise_area():
    return MORTISE_T * MORTISE_W

def svg_cut_length(fname, groups=('切る',)):
    t = open(os.path.join(OUT, fname), encoding='utf-8').read()
    tot = {}
    for gm in re.finditer(r'<g id="([^"]+)"[^>]*>(.*?)</g>', t, re.S):
        L = 0.0
        for d in re.findall(r'<path d="([^"]+)"', gm.group(2)):
            pts = [tuple(map(float, q.split(','))) for q in re.findall(r'[-\d.]+,[-\d.]+', d)]
            L += sum(math.dist(a, b) for a, b in zip(pts[:-1], pts[1:]))
        tot[gm.group(1)] = L
    return tot

# ================= 12w. 西館の床（シナ 1.7）・13w. 西館の階段（航空ベニヤ 0.6）・西館の柱のほぞ穴 =================
# 11-02 の頼み（模型作成）。西館は切った部品ではないので今の 3dm のまま。本館と同じ積み重ね：
#   2 階の床 1.7（2 階の床梁の上）／ 1 階の床の上の層 1.7（FL）＋下の層 1.7 ／ 基礎 3（GL、台の表面の西館の穴から抜けた板）／ 共通地盤 3（台の中の層）
# 柱は床の穴（1.60×3.9）を貫いて、基礎と共通地盤のほぞ穴（1.64×2.1）に刺さる。
#   python3 -c "import laser; print(laser.west_floor_sheets())"  … 12w だけ
#   python3 -c "import laser; print(laser.west_stair_sheets())"  … 13w だけ
RW0 = 205017.7                                                   # 本館の (u, v) の定数（model/build/south/uv.py と同じ）
TH_S0 = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)
WEST_V_EAST = -0.35                                              # v −0.35（本館の西の外壁の外面）から西が西館。床はここより東に出さない
WEST_F1_LAYERS = ('31_1F_遊戯室', '32_1F_キッチン', '33_1F_東の帯（はだし ±0、ホールと一続き）', '36_1F_階段', '36b_1F_倉庫（階段の下）', '57_1F_調理の更衣・便所・前室')
WEST_Z2F = 3250.0                                                # 2 階の床の上面（3dm、レイヤー 23）。これより上に出る柱だけ 2 階の床を貫く
WEST_SLIVER = 0.8                                                # 床の穴と縁のあいだがこれ（模型 mm）より細いと割れやすいので、縁まで開けて切り欠きにする

def _uv_xy(u, v):
    th = TH_S0 - u * 1000 / RW0; rr = RW0 - v * 1000
    return np.array([CX + rr * math.cos(th), CY + rr * math.sin(th)])

def _uv_of(x, y):
    th = math.atan2(y - CY, x - CX) % (2 * math.pi)
    return (TH_S0 - th) * RW0 / 1000, (RW0 - math.hypot(x - CX, y - CY)) / 1000

def west_cols():
    """西館の構造の柱：[(g, 種類, 頭の高さ)]。架構の柱（名前なし、桁の穴あり）22 本＋キッチンの東の骨格の柱 180×400 の 2 本。
    階段の箱の 120 角・鼻母屋の 120 角・柱の受け材は作らない（07 と同じ）"""
    out = []
    for nm, g in objs_named('22a_西館_柱'):
        if nm == '': kind = '架構'
        elif nm.startswith('骨格の柱'): kind = '骨格'
        else: continue
        out.append((g, kind, g.GetBoundingBox().Max.Z))
    return out

def _rect_at(c, ac, rad_w, tan_w):
    hr, ht = rad_w / S / 2, tan_w / S / 2
    er = np.array([math.cos(ac), math.sin(ac)]); et = np.array([-math.sin(ac), math.cos(ac)])
    c = np.asarray(c, float)
    return Polygon([c - hr * er - ht * et, c + hr * er - ht * et, c + hr * er + ht * et, c - hr * er + ht * et])

def _wcol_rect(g, rad_w, tan_w):
    """西館の柱の足の位置に、半径方向 rad_w × 接線方向 tan_w（模型 mm）の長方形（3dm の mm）。
    骨格の柱（押し出しの経路が角から始まる）は、col_rect だと接線の中心が半分ずれるので、足の平面の輪郭の中心から取る"""
    if g.ProfileCount == 1:
        f = _foot(g); c = np.array([f.centroid.x, f.centroid.y])
        return _rect_at(c, math.atan2(c[1] - CY, c[0] - CX), rad_w, tan_w)
    return col_rect(g, rad_w, tan_w)

def west_mortises():
    """西館の柱 24 本のほぞ穴（描いた寸法 1.64×2.1、3dm の mm）。基礎（台の表面から抜けた板）と共通地盤（台の中の層）に同じ位置"""
    return [_wcol_rect(g, MORTISE_W, MORTISE_T) for g, kind, top in west_cols()]

def _close_(g, r_=120):
    return g.buffer(r_, join_style=2).buffer(-r_, join_style=2)

def _east_clip():
    """v ≤ −0.35（半径 ≥ RW0 + 350）の側の広い領域"""
    circ = Point(CX, CY).buffer(RW0 - WEST_V_EAST * 1000, 1440)
    return box(-40000, -60000, 0, 0).difference(circ)

def _drill(fl, cols, slivers, tag):
    """床 fl に、柱 cols の穴（1.60×3.9）を開ける。縁に近くて細く残る所は、縁まで開けて切り欠きにする"""
    from shapely.geometry import LineString
    out = fl
    for g, kind, top in cols:
        h = _wcol_rect(g, FLOOR_L, FLOOR_T)
        if not out.intersects(h): continue
        if out.contains(h) and not out.contains(h.buffer(WEST_SLIVER / S)):
            from shapely.ops import nearest_points
            d = out.boundary.distance(h) * S
            c = h.centroid
            q = nearest_points(out.boundary, c)[0]
            v_ = np.array([q.x - c.x, q.y - c.y]); v_ = v_ / np.linalg.norm(v_)
            e_ = np.array([q.x, q.y]) + v_ * (FLOOR_T / S)                  # 縁を越えて少し先まで（縁ぴったりで終わらせない）
            h = unary_union([h, LineString([(c.x, c.y), tuple(e_)]).buffer(FLOOR_T / S / 2, cap_style=2)])
            slivers.append((tag, kind, round(d, 2)))
        out = out.difference(h)
        out = unary_union([g for g in getattr(out, 'geoms', [out]) if g.geom_type == 'Polygon'])
    return out

def west_f1_outline():
    """西館の 1 階の床の外形（3dm の mm、柱の穴を開ける前。摺鉢の穴φ3.2 m だけ内側の輪郭に残す）。12w の上の層・下の層と、台の表面の「西館の穴」（基礎の切り抜き片）の元"""
    parts = []
    for k in WEST_F1_LAYERS: parts += [_mesh_poly(g) for g in objs(k)]
    f1 = _close_(unary_union(parts))
    f1 = f1.intersection(_east_clip())
    f1 = max(getattr(f1, 'geoms', [f1]), key=lambda g: g.area)
    return Polygon(f1.exterior, [h for h in f1.interiors if Polygon(h).area > 1e6])          # 摺鉢の穴だけ残す（細いすき間は埋める）

def west_floors():
    """西館の床（3dm の mm）。戻り：(1 階の上の層, 下の層, 2 階の床, 情報)。
    1 階：レイヤー 31・32・33・36・36b（階段の下の倉庫）・57 はすべて z＝10（FL、はだし）で、土足・段のレイヤーは西館に無い → 上の層と下の層は同じ形。
    遊戯室の穴（φ3.2 m の摺鉢）は両方の層を抜く。v −0.35 より東（本館とのすき間）は出さない。
    柱の穴は床用 1.60×3.9（柱 24 本、骨格の柱 2 本も床を貫く）。
    2 階：レイヤー 23 の輪郭（3dm の柱の穴 170×400 は埋めて、頭が 2 階の床より上に出る柱 22 本だけ 1.60×3.9 に。骨格の柱は床の下で止まる）"""
    f1 = west_f1_outline()
    f2 = unary_union([_mesh_poly(g) for g in objs('23_西館_2階床')])
    f2 = max(getattr(f2, 'geoms', [f2]), key=lambda g: g.area)
    f2 = _close_(Polygon(f2.exterior))
    info = dict(slivers=[], 摺鉢の穴=len(f1.interiors), 面積_m2=dict(f1=round(f1.area / 1e6, 1), f2=round(f2.area / 1e6, 1)))
    cols = west_cols()
    u = _drill(f1, cols, info['slivers'], '1F')
    f2d = _drill(f2, [c for c in cols if c[2] > WEST_Z2F], info['slivers'], '2F')
    return u, u, f2d, info

def _west_ang():
    """板の上の向き：西館の u（南 u21 → 北 u51）を水平に（04 と同じ向きの約束：回すだけで裏返さない）"""
    p0 = _uv_xy(21, -8); p1 = _uv_xy(51, -8)
    return -math.atan2(p1[1] - p0[1], p1[0] - p0[0])

def _to_w(g, ang):
    g = affinity.scale(g, S, S, origin=(0, 0))
    return affinity.rotate(g, ang, origin=(0, 0), use_radians=True)

def _longest_mid_pts(poly, n=2):
    c = list(poly.exterior.coords)
    es = sorted(((math.dist(c[i], c[i + 1]), i) for i in range(len(c) - 1)), reverse=True)[:n]
    return [Point((c[i][0] + c[i + 1][0]) / 2, (c[i][1] + c[i + 1][1]) / 2) for _, i in es]

def _west_slot(sw, ang, b0, mv):
    """西館の溝：世界座標 → 12w の板の座標（_to_w、上の層の左下を原点、nest の移動）"""
    def tx(P):
        q = _to_w(P, ang)
        return Point(q.x - b0[0] + mv[0], q.y - b0[1] + mv[1])
    return foot_slot_poly(sw[0], sw[1], tx)

def west_floor_sheets():
    upper, lower, f2, info = west_floors()
    ang = _west_ang()
    WF = assemble_w(); g_raw = {}; slot_bad = []; n_slot = 0; placed = []
    items = []
    for nm, g in (('1階 上の層（はだし FL）', upper), ('1階 下の層（上と同じ形）', lower), ('2階の床', f2)):
        g = _to_w(g, ang); b = g.bounds; g_raw[nm] = (b[0], b[1])
        items.append((nm, affinity.translate(g, -b[0], -b[1])))
    # 置き方：06bのA1の残り841×444。11-02：3枚の位置だけを動かして、外接矩形が最小になるように詰める（向きは元のまま、間は今までの6 mm以上）
    W, H, gap = 841, 444, 6
    s = Sheet('12w_西館の床_シナ1.7', W, H, 'シナ 1.7：西館の床。1階の上の層（FL）と下の層（同じ形：西館に土足・段の所は無い）、2階の床。柱の穴 1.60×3.9（実寸 約 1.80×4.1）、遊戯室の摺鉢の穴は 1階の 2枚とも抜く。v −0.35 より東（本館とのすき間）は出さない。向きは元のまま、外接矩形が最小になるように詰めた（板どうし6 mm以上）')
    s.show_used = True
    s.add(box(0, 0, W, H), 'ref')
    mv, (uw, uh) = nest([g for _, g in items], W - 2 * Sheet.MARGIN, H - 2 * Sheet.MARGIN, gap, top=H)
    pos = []
    for (nm, g), (tx, ty) in zip(items, mv):
        q = affinity.translate(g, tx, ty)
        if nm.startswith('1階 上'):
            for f in WF['feet']:
                sw = foot_slot_world(f, foot_ok_w())
                if sw is None: continue
                sl_w = _west_slot(sw, ang, g_raw[nm], (tx, ty))
                if not q.contains(sl_w): slot_bad.append(f.id)
                q = q.difference(sl_w); n_slot += 1
        s.add(q); placed.append(q)
        if nm.startswith('2階'): s.tab_pts += _longest_mid_pts(Polygon(q.exterior))
        pos.append((nm, round(g.bounds[2], 1), round(g.bounds[3], 1), round(q.bounds[0], 1), round(H - q.bounds[3], 1)))
    # 天の川の縁の継ぎ足し片（本館の床の上の層。amano_edit）。切り幅の分だけ大きく描く。置き場所は板の下半分の空き
    patches = []
    occ = unary_union(placed)                                  # 並べた板（穴の中は空き）
    bx = occ.envelope.bounds                                    # 板の外接矩形の中に置く（11-02：大きな板のあいだの空きに）
    GAPP = 3.0
    for k, g in enumerate(amano_edit()[1]):
        gs = affinity.scale(g.buffer(10), S, S, origin=(0, 0)); b = gs.bounds
        occb = occ.buffer(GAPP); put = None
        for yy in np.arange(bx[3] - (b[3] - b[1]) - 0.5, bx[1] - 0.01, -0.5):
            for xx in np.arange(bx[0] + 0.5, bx[2] - (b[2] - b[0]), 0.5):
                q = affinity.translate(gs, xx - b[0], yy - b[1])
                if not q.intersects(occb): put = q; break
            if put is not None: break
        if put is None:                                          # 矩形の中に空きが無ければ、矩形の下に
            put = affinity.translate(gs, bx[0] + 5 + 20 * k - b[0], bx[1] - 8 - (b[3] - b[1]) - b[1] + b[1])
        s.add(put); occ = unary_union([occ, put])
        patches.append((k + 1, round(b[2] - b[0], 1), round(b[3] - b[1], 1), tuple(round(v, 2) for v in laser_uv_of_poly(g)), tuple(round(v, 1) for v in put.bounds[:2])))
    s.save([(0, -4, '1階 上の層・1階 下の層（同じ形）・2階の床。位置は外接矩形が最小になるように詰めた。小片 2 つは本館の天の川の縁の継ぎ足し（仮、大きな板のあいだの空きに置いた）', 3)])
    return dict(継ぎ足し片=patches, 足の溝=n_slot, 溝が床の外=slot_bad, sheet=(W, H), 並べ方=pos, 使う幅=round(uw + Sheet.MARGIN, 1), 使う高さ=round(uh + Sheet.MARGIN, 1), info=info)

def west_stair_treads():
    """階段（レイヤー 25、面のメッシュ。段板は厚 40）の踏面：[(高さ z（3dm の mm）, 平面の形（3dm の mm）)]、低い順。
    上を向く水平の面を高さごとに集め、面積 0.2 m² 以上（踏面 260×1200＝0.31）だけ取る。踊り場（z 1625）も 1 つ。階段は 17 段＋踊り場、18 段目は 2 階の床"""
    byz = {}
    for g in objs('25_西館_階段'):
        if not isinstance(g, r.Mesh): continue
        V, F = g.Vertices, g.Faces
        P = np.array([[V[i].X, V[i].Y, V[i].Z] for i in range(len(V))])
        for fi in range(F.Count):
            f = F[fi]; idx = list(dict.fromkeys([f[0], f[1], f[2], f[3]]))
            q = P[idx]
            n = np.cross(q[1] - q[0], q[2] - q[0])
            if np.linalg.norm(n) < 1e-6 or n[2] / np.linalg.norm(n) < 0.99: continue
            byz.setdefault(int(round(q[:, 2].mean())), []).append(Polygon(q[:, :2]).buffer(1))
    out = []
    for z in sorted(byz):
        pg = unary_union(byz[z]).buffer(-1)
        if pg.area >= 0.2e6: out.append((z, pg))
    return out

STAIR_T = 0.6                              # 階段の板（航空ベニヤ 0.6）の厚さ
STAIR_RISE = 180.6                          # 蹴上（実寸 mm）。0.6 の板 3 枚＝1.8 ≈ 蹴上 1.806

def west_stair_plates():
    """段を 0.6 の板の積み重ね（等高線の積層）で作る。踏面 k（上面の高さ z）の上には、板が n＝round(z×S／0.6)（＝3k）枚。
    板 m（下から数えて m 枚目）の形＝n ≥ m の踏面の和。戻り：([(m, 形（3dm の mm））], [(n, 踏面の形)])"""
    T = west_stair_treads()
    ns = [(int(round(z * S / STAIR_T)), pg) for z, pg in T]
    N = max(n for n, _ in ns)
    cl = lambda g: g.buffer(5, join_style=2).buffer(-5, join_style=2)       # 踏面を 1 mm ずつ縮めたすき間（面の継ぎ目）を閉じる
    return [(m, cl(unary_union([pg for n, pg in ns if n >= m]))) for m in range(1, N + 1)], ns

def west_stair_sheets():
    plates, ns = west_stair_plates()
    ang = _west_ang()
    items = []
    for m, g in plates:
        g = _to_w(g, ang)
        assert g.geom_type == 'Polygon', (m, g.geom_type)
        g = g.simplify(0.005)
        b = g.bounds
        items.append((m, affinity.translate(g, -b[0], -b[1])))
    W, H, gap = 600, 300, 1.6
    s = Sheet('13w_西館の階段_航空ベニヤ0.6', W, H, f'航空ベニヤ 0.6 300×600：西館の階段（階段 1 段＝板 3 枚の積層）。板 m 枚目の形＝高さが 0.6×m 以上の踏面の和（踊り場を含む）。板は下から 1〜{len(items)}、番号を彫る。向きは元のまま、外接矩形が最小になるように詰めた（板どうし{gap} mm以上）')
    s.show_used = True
    s.add(box(0, 0, W, H), 'ref')
    items.sort(key=lambda it: (-it[1].bounds[3], it[0]))
    mv, (uw, uh) = nest([g for _, g in items], W - 2 * Sheet.MARGIN, H - 2 * Sheet.MARGIN, gap, top=H)
    for (m, g), (tx, ty) in zip(items, mv):
        q = affinity.translate(g, tx, ty)
        s.add(q); s.tab_pts += _longest_mid_pts(q)
        c = q.representative_point(); txt = str(m)
        for j, ch in enumerate(txt):
            for l in label_num(ch, c.x - len(txt) * 0.6 + j * 1.2, c.y - 0.6, 1.2): s.add(l, 'eng')
    s.tab_gap = lambda: 0.35                                     # 0.8 の弱い設定に準じる（ユーザー 11-02）
    s.save([(0, -4, f'{len(items)} 枚。番号＝下から何枚目', 3)])
    return dict(板=len(items), 踏面=len(ns), 踏面の板数=[n for n, _ in ns], 使う幅=round(uw + Sheet.MARGIN, 1), 使う高さ=round(uh + Sheet.MARGIN, 1), 板の最大=(round(max(g.bounds[2] for _, g in items), 1), round(max(g.bounds[3] for _, g in items), 1)))

if __name__ == '__main__':
    if sys.argv[1:2] == ['04b']:                       # 0・1歳の外縁側の床の帯だけ
        print(engawa_sheets()); sys.exit(0)
    if sys.argv[1:2] == ['dai']:                       # 台の表面だけ（ほかの部品は書き換えない）
        print(dai_sheets()); sys.exit(0)
    if sys.argv[1:2] == ['west-floor']:                # 西館の床（12w）だけ
        print(west_floor_sheets()); sys.exit(0)
    if sys.argv[1:2] == ['west-stair']:                # 西館の階段（13w）だけ
        print(west_stair_sheets()); sys.exit(0)
    if sys.argv[1:2] == ['dai-pit']:                   # 本館の窪みの円 3 つだけ
        print(dai_pit_sheets()); sys.exit(0)
    if sys.argv[1:2] == ['dai-naka']:                  # 台の中の層だけ
        print(dai_naka_sheets()); sys.exit(0)
    if sys.argv[1:2] == ['14w']:                       # 西館の外壁だけ
        print(west_wall_sheets()); sys.exit(0)
    # 01〜06（試し切り・本館の架構・床・ベタ基礎・屋根）は切った部品なので作り直さない（ユーザー 10-28、CUT_DONE）
    print('西館の架構', west_sheets())
    print('本館の外壁', wall_sheets())
    print('西館の外壁 14w', west_wall_sheets())
    print('06c・11 小屋と機械室', hut_kikai_sheets())
    print('西館の屋根', west_roof_sheets())
    print('室内の壁', interior_sheets())
    print('西館の室内の壁', interior_sheets_w())
    print('ok', OUT)
