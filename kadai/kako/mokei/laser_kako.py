"""構造模型（1/50、西館全体）：レーザーカッターのデータを、架構の部品 kakou の出力から作る（模型係）。

入力：data/kakou_flat.json（Rhino の Grasshopper の kakou の出力 plates・floors・cols・rays を、部品ごとにいちばん大きい
      平らな面の外形（穴を含む）として書き出したもの。実物 mm。版 kakou 2026-11-27 22:05）
出力：cut/*.svg（1 単位＝1 mm、実寸。原点は左上、切る・彫る線の左上が板の左上から 3 mm）
色：赤 #FF0000＝切る、青 #0000FF＝彫る（線）、黒＝参考（板の外形・文字。レーザーに送る前に消す）
試し切りの出力の段：1＝赤、2＝橙 #FF8000、3＝紫 #FF00FF

決まり（育ち舎の sodachiya/mokei/laser.py と同じ）：
- 切り幅は約 0.2 として、穴は 0.2 小さく、外形は 0.2 大きく描く（外形は外へ 0.1、穴は内へ 0.1）。
  → 切れた部品と穴がちょうどの寸法になる。試し切りで切り幅が分かったら KERF を直す。
- 小さい部品（250 mm 以下）は外形に 2 か所のつなぎ（切り残し）。

  python3 kadai/kako/mokei/laser_kako.py
"""
import json, math, os
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, substring
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'cut')
VERSION = 'laser_kako 2026-11-27 23:50'

S = 1 / 50                 # 実物 mm → 模型 mm
KERF = 0.2                 # 切り幅（仮。試し切りで決める）
FOOT = 450 * S             # 柱を FL から下へ延ばす長さ（立ち上がり：底板の上面 GL−150 → FL＝GL+300）
GAP = 1.2                  # 部品どうしのあき（切る線と切る線のあいだ）
MARGIN_SHEET = 4.0         # 板の縁からのあき
PIN_D = 2.0                # 位置合わせのピン（真鍮の丸棒 φ2）。穴は描くとき 0.2 小さく
KETA = (3.6, 5.2)          # 楕円の桁（実物 180×260 の 1/50）
GIRDER_CLR = 0.2           # 桁の穴＝桁＋0.2（実物の穴＋10 の 1/50）。試し切りで決める
TAB = {'maple1': 0.4, 'shina3': 0.5, 'acryl': 0.5}
COL_HOLE = 6.1             # 柱（6.0）を通す四角の穴の、切れたあとの大きさ（試し切りの T1 で決める）

D = json.load(open(os.path.join(HERE, 'data', 'kakou_flat.json')))
RAYS = D['rays']


# ---------------------------------------------------------------- 読む
def frame_of(c):
    best = None
    for i, (a, b) in enumerate(RAYS):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        sd = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / L
        if best is None or abs(sd) < abs(best[1]):
            best = (i + 8, sd)
    return best


def poly(p):
    outer = [l['p'] for l in p['loops'] if l['outer']][0]
    holes = [l['p'] for l in p['loops'] if not l['outer']]
    g = Polygon([(x * S, y * S) for x, y in outer], [[(x * S, y * S) for x, y in h] for h in holes])
    return g if g.is_valid else g.buffer(0)


def cn(p):
    return p['c'][0] * p['n'][0] + p['c'][1] * p['n'][1]


def extend(g):
    """柱の層を FL から下へ FOOT 延ばす（立ち上がりの穴に高さいっぱい差して台の上面に載る、kouhou 11-13）"""
    y0 = g.bounds[1]
    if y0 > 0.5:
        return g
    low = g.intersection(box(-1e6, y0, 1e6, y0 + 0.5))
    x0, _, x1, _ = low.bounds
    return unary_union([g, box(x0, y0 - FOOT, x1, y0 + 0.01)]).buffer(0)


def load():
    beams, floors, cols = [], [], []
    for p in D['plates']:
        k, sd = frame_of(p['c'])
        beams.append(dict(k=k, side='S' if sd < 0 else 'N', g=poly(p)))
    for p in D['floors']:
        k, sd = frame_of(p['c'])
        floors.append(dict(k=k, side='S' if sd < 0 else 'N', g=poly(p), kind='耐風梁' if k == 18 else '2階の床梁'))
    cur = None
    for p in D['cols']:
        k, sd = frame_of(p['c'])
        g = poly(p)
        if abs(sd) < 30:
            cur = dict(k=k, core=extend(g), top=[], bot=[], cn=cn(p))
            cols.append(cur)
        else:
            (cur['top'] if cn(p) > cur['cn'] else cur['bot']).append(extend(g))
    for k in range(8, 19):
        cs = sorted([c for c in cols if c['k'] == k], key=lambda c: -c['core'].centroid.x)
        for name, c in zip('EIW', cs):
            c['pos'] = name
    return beams, floors, cols


# ---------------------------------------------------------------- 板と書き出し
class Sheet:
    def __init__(self, name, w, h, note, mat):
        self.name, self.w, self.h, self.note, self.mat = name, w, h, note, mat
        self.layers = {'ref': [], 'eng': [], 'cut': []}
        self.colors = {'ref': '#000000', 'eng': '#0000FF', 'cut': '#FF0000'}
        self.texts = []
        self.tabbed_ids = set()

    def add(self, g, lay='cut', tabs=False):
        self.layers.setdefault(lay, []).append((g, tabs))

    def text(self, x, y, t, sz=3):
        self.texts.append((x, y, t, sz))

    def _tab(self, p):
        """外形の、いちばん長い 2 本の直線の辺の真ん中に切り残し"""
        h = TAB[self.mat] / 2
        ext = LineString(p.exterior.coords)
        cs = np.array(p.exterior.coords)
        segs = sorted(((math.hypot(*(cs[i + 1] - cs[i])), i) for i in range(len(cs) - 1)), reverse=True)
        L = ext.length
        picks = []
        for ln, i in segs:
            if ln < 2 * h + 0.6:
                break
            m = ext.project(Point((cs[i] + cs[i + 1]) / 2))
            if all(abs(m - q) > L * 0.2 for q in picks):
                picks.append(m)
            if len(picks) == 2:
                break
        if len(picks) < 2:
            picks = [L * 0.25, L * 0.75]
        a, b = sorted(picks)
        return [substring(ext, a + h, b - h), substring(ext, b + h, L), substring(ext, 0, a - h)] + \
               [LineString(i.coords) for i in p.interiors]

    def save(self):
        os.makedirs(OUT, exist_ok=True)
        allg = [g for lay, items in self.layers.items() if lay != 'ref' for g, _ in items]
        b = unary_union([g.envelope for g in allg]).bounds if allg else (0, 0, self.w, self.h)
        H = self.h

        def P(a):
            return 'M' + ' L'.join(f'{x:.3f},{H - y:.3f}' for x, y in a)
        L = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" viewBox="0 0 {self.w} {self.h}">',
             f'<!-- {VERSION}。{self.note} -->']
        order = ['ref', 'eng'] + [k for k in self.layers if k not in ('ref', 'eng')]
        for lay in order:
            items = self.layers.get(lay, [])
            if not items:
                continue
            L.append(f'<g id="{lay}" fill="none" stroke="{self.colors[lay]}" stroke-width="0.01">')
            for g, tabs in items:
                for p in getattr(g, 'geoms', [g]):
                    if p.geom_type == 'Polygon':
                        rings = self._tab(p) if tabs else [p.exterior] + list(p.interiors)
                        for r in rings:
                            a = np.array(r.coords)
                            closed = len(a) > 2 and np.allclose(a[0], a[-1])
                            L.append(f'<path d="{P(a)}{" Z" if closed else ""}"/>')
                    else:
                        L.append(f'<path d="{P(np.array(p.coords))}"/>')
            L.append('</g>')
        if self.texts:
            L.append('<g id="参考の文字（送る前に消す）" fill="#000000" stroke="none" font-family="sans-serif">')
            for x, y, t, sz in self.texts:
                L.append(f'<text x="{x:.2f}" y="{H - y:.2f}" font-size="{sz}">{t}</text>')
            L.append('</g>')
        L.append('</svg>')
        open(os.path.join(OUT, self.name + '.svg'), 'w').write('\n'.join(L))
        return b


def outline(g):
    """切る外形：外へ KERF/2、穴は内へ KERF/2（＝穴は 0.2 小さく、部品は 0.2 大きく描く）"""
    ext = Polygon(g.exterior.coords).buffer(KERF / 2, join_style=2)
    holes = [Polygon(h.coords).buffer(-KERF / 2, join_style=1) for h in g.interiors]
    return Polygon(ext.exterior.coords, [h.exterior.coords for h in holes if not h.is_empty])


def ellipse(cx, cy, w, h, n=72):
    return Polygon([(cx + w / 2 * math.cos(2 * math.pi * i / n), cy + h / 2 * math.sin(2 * math.pi * i / n)) for i in range(n)])


SEG = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc',
       '8': 'abcdefg', '9': 'abcdfg', '-': 'g', '.': 'p', 'E': 'afged', 'A': 'efabcg', 'B': 'fedcg', 'C': 'afed', 'D': 'bcdeg', 'W': 'fedcbh', 'I': 'bc', 'S': 'afgcd', 'N': 'efabc'}


def label(txt, x, y, h=1.6):
    """彫る文字（線の 7 セグメント）"""
    w = h * 0.55
    P = {'a': ((0, h), (w, h)), 'b': ((w, h), (w, h / 2)), 'c': ((w, h / 2), (w, 0)), 'd': ((0, 0), (w, 0)),
         'e': ((0, 0), (0, h / 2)), 'f': ((0, h / 2), (0, h)), 'g': ((0, h / 2), (w, h / 2)),
         'h': ((0, 0), (w / 2, h / 2)), 'p': ((w / 2, 0), (w / 2, 0.15))}
    out = []
    for i, ch in enumerate(txt):
        ox = x + i * (w + 0.5)
        for s in SEG.get(ch, ''):
            if s == 'h':
                out.append(LineString([(ox, 0 + y), (ox + w / 2, y + h / 2), (ox + w, y)]))
            else:
                out.append(LineString([(ox + p[0], y + p[1]) for p in P[s]]))
    return out


def raster_nest(items, W, H, res=0.25, gap=GAP, margin=MARGIN_SHEET, rots=(90, 270), keepout=None):
    """FFT の畳み込みで、下から詰める（items は優先の順。各々 (key, geom)）"""
    from numpy.fft import rfft2, irfft2
    from matplotlib.path import Path

    def rast(g, nx, ny):
        ys, xs = np.mgrid[0:ny, 0:nx]
        pts = np.c_[(xs.ravel() + 0.5) * res, (ys.ravel() + 0.5) * res]
        out = np.zeros(nx * ny, bool)
        for p in getattr(g, 'geoms', [g]):
            ins = Path(np.asarray(p.exterior.coords)).contains_points(pts)
            out |= ins
        return out.reshape(ny, nx)
    nx, ny = int(round(W / res)), int(round(H / res))
    occ = np.zeros((ny, nx), bool)
    m = int(round(margin / res))
    occ[:m, :] = occ[-m:, :] = True
    occ[:, :m] = occ[:, -m:] = True
    if keepout is not None:
        occ |= rast(keepout, nx, ny)
    res_t, fail = {}, []
    for key, g in items:
        best = None
        for r in rots:
            g0 = g if g.geom_type == 'MultiPolygon' else Polygon(g.exterior.coords)
            gr = affinity.rotate(g0, r, origin=(0, 0))
            x0, y0, x1, y1 = gr.bounds
            pw, ph = int(np.ceil((x1 - x0 + gap) / res)) + 2, int(np.ceil((y1 - y0 + gap) / res)) + 2
            if pw >= nx or ph >= ny:
                continue
            gl = affinity.translate(gr, -x0 + gap / 2, -y0 + gap / 2).buffer(gap / 2)
            mask = rast(gl, pw, ph)
            conv = irfft2(rfft2(occ.astype(np.float32)) * rfft2(mask[::-1, ::-1].astype(np.float32), s=(ny, nx)), s=(ny, nx))
            valid = conv[ph - 1:ny, pw - 1:nx] < 0.5
            idx = np.argwhere(valid)
            if len(idx) == 0:
                continue
            k = np.lexsort((idx[:, 1], idx[:, 0]))[0]
            i, j = idx[k]
            if best is None or (i, j) < best[0]:
                best = ((i, j), r, mask, x0, y0)
        if best is None:
            fail.append(key)
            continue
        (i, j), r, mask, x0, y0 = best
        ph, pw = mask.shape
        occ[i:i + ph, j:j + pw] |= mask
        res_t[key] = (r, j * res + gap / 2 - x0, i * res + gap / 2 - y0)
    return res_t, fail


def tf(g, t):
    r, dx, dy = t
    return affinity.translate(affinity.rotate(g, r, origin=(0, 0)), dx, dy)


# ---------------------------------------------------------------- 01 試し切り
def test_sheets():
    """T1：しなベニヤ3（梁・台・治具）。T2：メープル1 mm（柱）。出力を3段、各段に桁の穴 A〜D、四角の穴、20 mm 角"""
    variants = [(c, (KETA[0] + c - KERF, KETA[1] + c - KERF)) for c in (0.0, 0.1, 0.2, 0.3)]   # 穴＝桁＋c（描くのは −0.2）
    cols = [('cut', '#FF0000'), ('cut2', '#FF8000'), ('cut3', '#FF00FF')]
    for tname, mat, w, h, note in [
            ('01_試し切り_T1_しなベニヤ3', 'shina3', 106, 86, 'しなベニヤ3の端（106×86）。段1〜3×（桁の穴 A〜D、柱の四角の穴 6.0・6.1・6.2、20 mm 角）'),
            ('01_試し切り_T2_メープル1', 'maple1', 95, 86, 'メープル1 mmのSの板の端（95×86）。段1〜3×（桁の穴 A〜D、幅6.0の帯と、つなぎ0.4、20 mm 角）')]:
        s = Sheet(tname, w, h, note, mat)
        for li, (lay, col) in enumerate(cols):
            s.layers[lay] = []
            s.colors[lay] = col
            oy = h - 4 - (li + 1) * 26
            ox = 4
            s.add(unary_union(label(str(li + 1), ox, oy + 14, 2.0)), 'eng')
            x = ox + 4
            for i, (c, (hw, hh)) in enumerate(variants):
                s.add(ellipse(x + 3, oy + 10, hw, hh), lay)
                s.add(unary_union(label('ABCD'[i], x + 2.2, oy + 3.5, 1.4)), 'eng')
                x += 7.5
            if mat == 'shina3':
                for i, a in enumerate((6.0, 6.1, 6.2)):
                    d = a - KERF
                    s.add(box(x + 1, oy + 10 - d / 2, x + 1 + d, oy + 10 + d / 2), lay)
                    s.add(unary_union(label(str(i + 1), x + 2.5, oy + 3.5, 1.4)), 'eng')
                    x += 9
            else:
                strip = box(x + 1, oy + 4, x + 1 + 6.0 + KERF, oy + 16)
                s.add(strip, lay, tabs=True)
                x += 10
            q = 20 + KERF
            s.add(box(x + 2, oy + 1, x + 2 + q, oy + 1 + q), lay)
        s.text(2, h + 1.5, f'{tname}：{note}', 2.5)
        s.save()
    return variants


# ---------------------------------------------------------------- 02 柱（メープル1 mm×6枚）
LAYERS6 = ['1_外の層_下（裏返す）', '2_芯', '3_芯', '4_芯', '5_芯', '6_外の層_上']


def column_sheets(cols, beams, floors, sheetW=585.0, sheetH=95.0, batch_name='1回目', keys=None):
    """6枚の板（1枚目は裏返して一番下）。どの板も同じ位置に部品とピン穴。1台のレーザーの台に6枚を並べて一度に切る"""
    pin_y = sheetH / 2
    pins = [Point(MARGIN_SHEET + 2.5, pin_y), Point(sheetW - MARGIN_SHEET - 2.5, pin_y)]
    keep = unary_union([p.buffer(PIN_D / 2 + 1.0) for p in pins])
    # 優先：北西（k15〜k18）→ 北から
    order = sorted(cols, key=lambda c: (-c['k'], 'EIW'.index(c['pos'])))
    if keys is not None:
        order = [c for c in order if (c['k'], c['pos']) in keys]
    fps = []
    extra = spacers(beams, floors, cols)       # 芯の4枚だけに入る詰め木（4 mm の積層になる）
    for c in order:
        fp = unary_union([c['core']] + c['top'] + c['bot']).buffer(KERF / 2)
        fps.append(((c['k'], c['pos']), fp))
    t, fail = raster_nest(fps, sheetW, sheetH, keepout=keep)
    # 詰め木は、柱を置いた残りに
    if keys is None or batch_name == '1回目':
        occ = unary_union([tf(fp, t[k]).buffer(GAP / 2) for k, fp in fps if k in t] + [keep])
        t2, fail2 = raster_nest([(n, g.buffer(KERF / 2)) for n, g in extra], sheetW, sheetH, keepout=occ, rots=(0, 90))
    else:
        t2, fail2 = {}, []
    done = [c for c in order if (c['k'], c['pos']) in t]
    # 6枚を台の上に縦に並べる（板と板のあいだ 10 mm）
    bedW = sheetW + 6
    bedH = 6 * (sheetH + 10) + 6
    s = Sheet(f'02_柱_{batch_name}_メープル1_6枚', round(bedW), round(bedH),
              f'メープル1 mm の板（95×{sheetW:g}）を6枚、黒の枠に合わせて台に並べる。上から{"・".join(LAYERS6)}。'
              f'柱{len(done)}本（{", ".join(f"k{k}{p}" for k, p in sorted(t))}）＋詰め木{len(t2)}個。'
              f'1枚目（外の層の下）は、切ったあと長い辺を軸に裏返して一番下に重ねる（彫った柱脚の線が外を向く）。'
              f'ピン φ{PIN_D} で6枚を重ねる', 'maple1')
    for li, lname in enumerate(LAYERS6):
        oy = bedH - 3 - (li + 1) * (sheetH + 10) + 10
        ox = 3
        mirror = (li == 0)

        def place(g):
            if mirror:
                g = affinity.scale(g, 1, -1, origin=(0, sheetH / 2))
            return affinity.translate(g, ox, oy)
        s.add(place(box(0, 0, sheetW, sheetH)), 'ref')
        s.text(ox, oy + sheetH + 1.5, f'{li + 1}枚目：{lname}', 3)
        for p in pins:
            s.add(place(p.buffer((PIN_D - KERF) / 2, 32)), 'cut')
        for c in done:
            tt = t[(c['k'], c['pos'])]
            if lname.startswith(('2', '3', '4', '5')):
                parts_ = [c['core']]
            elif li == 0:
                parts_ = c['bot']
            else:
                parts_ = c['top']
            for g in parts_:
                s.add(place(tf(outline(g), tt)), 'cut', tabs=True)
            if li in (0, 5):        # 柱脚の線（FL、立ち上がりから出る所）：外の層の外の面に彫る
                for g in parts_:
                    if g.bounds[1] < -FOOT + 0.5:
                        x0, _, x1, _ = g.intersection(box(-1e6, -0.05, 1e6, 0.05)).bounds
                        s.add(place(tf(LineString([(x0 + 0.3, 0), (x1 - 0.3, 0)]), tt)), 'eng')
            if li == 5:             # 番号：上の外の層の、立ち上がりに隠れる足の所（FL−2〜−8）に彫る。k と 1＝東・2＝内・3＝西
                for g in parts_:
                    if g.bounds[1] < -FOOT + 0.5:
                        x0, _, x1, _ = g.intersection(box(-1e6, -5.05, 1e6, -4.95)).bounds
                        lab = f'{c["k"]}-{"EIW".index(c["pos"]) + 1}'
                        lw = len(lab) * 0.55 * 1.1 + (len(lab) - 1) * 0.5
                        s.add(place(tf(unary_union(label(lab, (x0 + x1) / 2 - lw / 2, -6.5, 1.1)), tt)), 'eng')
        if li in (1, 2, 3, 4):
            for n, g in extra:
                if n in t2:
                    s.add(place(tf(outline(g), t2[n])), 'cut', tabs=True)
    s.save()
    return done, fail, t2, fail2


def spacers(beams, floors, cols):
    """芯の4枚に入れる詰め木（4 mm）：
    - 西の外壁の中（壁の厚さ200→4 mm）：対の梁の延長のあいだ（光の筋は外壁の内の面で止まる、kettei 11-27）
    - k18 の耐風梁の対のあいだ（1 m 前後おき、kettei 11-27）"""
    out = []
    WALL = 200 * S
    for k in range(8, 19):
        bs = [b['g'] for b in beams if b['k'] == k]
        w = [c for c in cols if c['k'] == k and c['pos'] == 'W'][0]
        shaft = unary_union(w['top'] + w['bot'])
        xw = shaft.bounds[0]                       # 西の柱の外の面＝外壁の内の面
        zone = box(xw - WALL, -1e3, xw, 1e3)
        g = bs[0].intersection(bs[1]).intersection(zone).difference(w['core'].buffer(0.05))
        g = Polygon(g.exterior.coords) if g.geom_type == 'Polygon' else max(g.geoms, key=lambda q: q.area)
        out.append((f'壁{k}', Polygon(g.exterior.coords).simplify(0.02)))
    fl = [f['g'] for f in floors if f['k'] == 18]
    c18 = sorted([c for c in cols if c['k'] == 18], key=lambda c: -c['core'].centroid.x)
    xs = [unary_union(c['top'] + c['bot']).centroid.x for c in c18]   # E, I, W の芯
    both = fl[0].intersection(fl[1])
    stations = [(xs[0] + xs[1]) / 2, xs[1] + (xs[2] - xs[1]) / 3, xs[1] + 2 * (xs[2] - xs[1]) / 3]
    for i, x in enumerate(stations):
        g = both.intersection(box(x - 100 * S, -1e3, x + 100 * S, 1e3))
        g = g if g.geom_type == 'Polygon' else max(g.geoms, key=lambda q: q.area)
        out.append((f'風{i + 1}', Polygon(g.exterior.coords).simplify(0.02)))
    return out


# ---------------------------------------------------------------- 03 梁（しなベニヤ3）
def beam_sheet(beams, floors, cols, W=841.0, H=594.0, use_h=240.0):
    """A1 の上の帯（841×use_h）に、屋根の梁22・2階の床梁10・耐風梁2、台、治具。残りは底板のためにあけておく"""
    items = []
    for b in beams:
        items.append((f'{b["k"]}{b["side"]}', b['g'], 'roof'))
    for f in floors:
        items.append((f'{f["k"]}{f["side"]}{"F" if f["kind"] == "2階の床梁" else "W"}', f['g'], 'floor'))
    # 梁は上端の直線が水平になるように回してから詰める
    prep = []
    for n, g, kind in items:
        ext = np.array(g.exterior.coords)
        top = ext[ext[:, 1] > g.bounds[3] - 0.5]
        hull = g.convex_hull
        best = None
        for a in np.linspace(-35, 35, 141):
            r = affinity.rotate(hull, a, origin=(0, 0))
            hh = r.bounds[3] - r.bounds[1]
            if best is None or hh < best[0]:
                best = (hh, a)
        prep.append((n, affinity.rotate(g, best[1], origin=(0, 0)), kind))
    # 柱の台（遊戯室の中の内の柱、k11〜k18：10 mm 角、厚さ＝床の板、柱の穴）
    pads = []
    for k in range(11, 19):
        cI = [c for c in cols if c['k'] == k and c['pos'] == 'I'][0]
        pads.append((f'台{k}', box(-5, -5, 5, 5).difference(box(-COL_HOLE / 2, -COL_HOLE / 2, COL_HOLE / 2, COL_HOLE / 2)), 'pad'))
    jigs = []
    for i in range(4):     # コの字のブロック（溝 6.0＋遊び0.1、深さ 10）
        u = box(0, 0, 20, 16).difference(box(7, 6, 7 + 6.1, 16.1))
        jigs.append((f'コ{i + 1}', u, 'jig'))
    for i in range(2):     # 長い当て（GL の線）
        jigs.append((f'当て{i + 1}', box(0, 0, 300, 10), 'jig'))
    allp = prep + pads + jigs
    def fp(n, g, kind):
        o = outline(g) if g.interiors else Polygon(g.exterior.coords).buffer(KERF / 2, join_style=2)
        if kind in ('roof', 'floor'):        # 番号を彫る残りの場所（部品の左上の外、8×2）
            b = o.bounds
            o = unary_union([o, box(b[0], b[3] - 0.5, b[0] + 9, b[3] + 2.2)])
        return o
    t, fail = raster_nest([(n, fp(n, g, kind)) for n, g, kind in allp], W, use_h, res=0.5, rots=(0, 180))
    s = Sheet('03_梁と台と治具_しなベニヤ3', round(W), round(H),
              f'しなベニヤ3 A1（841×594）の上の帯 約{use_h:g} mm を使う（残りは底板のためにあけておく）。'
              f'屋根の梁22・2階の床梁10・耐風梁2・柱の台8（遊戯室の中の内の柱、k11〜k18）・コの字のブロック4・長い当て2。'
              f'梁の番号はとなりの残りに彫る（梁の面には彫らない。外したら見えない面に鉛筆で）', 'shina3')
    s.add(box(0, 0, W, H), 'ref')
    s.add(box(0, H - use_h, W, H), 'ref')
    for n, g, kind in allp:
        if n not in t:
            continue
        gg = tf(outline(g) if g.interiors else Polygon(g.exterior.coords).buffer(KERF / 2, join_style=2), t[n])
        gg = affinity.translate(gg, 0, H - use_h)
        s.add(gg, 'cut', tabs=(kind in ('pad', 'jig')) or gg.bounds[2] - gg.bounds[0] < 250)
        if kind in ('roof', 'floor'):
            b = gg.bounds
            lab = n.replace('F', '-2').replace('W', '-3') if kind == 'floor' else n
            r = t[n][0]
            # 番号は、部品を回す前の左上の外（fp で場所をあけた所）。回した向きに合わせて置き直す
            o0 = outline(g) if g.interiors else Polygon(g.exterior.coords)
            b0 = o0.bounds
            lab_g = unary_union(label(lab, b0[0] + 0.6, b0[3] + 0.6, 1.1))
            s.add(affinity.translate(tf(lab_g, t[n]), 0, H - use_h), 'eng')
    s.save()
    return t, fail


def acryl_keys(n_keys=6):
    """仮のキー：アクリル3 mm の楕円を4枚重ねて長さ12（梁＋柱＋梁）。木工用ボンドが付かない"""
    s = Sheet('04_仮のキー_アクリル3', 60, 30, f'アクリル3 mm の端（60×30）。楕円{KETA[0]}×{KETA[1]}を{4 * n_keys}枚（4枚で1本、{n_keys}本）', 'acryl')
    i = 0
    for r in range(3):
        for c in range(8):
            g = ellipse(4 + c * 6.5, 4 + r * 7.5, KETA[0] + KERF, KETA[1] + KERF)
            s.add(g, 'cut')
    s.save()


if __name__ == '__main__':
    beams, floors, cols = load()
    print(VERSION, '梁', len(beams), '床梁・耐風梁', len(floors), '柱', len(cols))
    test_sheets()
    done, fail, t2, f2 = column_sheets(cols, beams, floors)
    print('柱 1回目', len(done), 'はみ出し', fail, '詰め木', len(t2), f2)
    if fail:
        d2, fl2, _, _ = column_sheets(cols, beams, floors, sheetW=190.0, batch_name='2回目', keys=set(fail))
        print('柱 2回目', len(d2), fl2)
    t, f = beam_sheet(beams, floors, cols)
    print('梁', len(t), 'はみ出し', f)
    acryl_keys()
