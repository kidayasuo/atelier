"""西館の間仕切り（24）を一枚ずつの直方体（立面の形×厚さ 120）に作り直す（西館係、10-28 夜。段 7i、削る段・大和張りの後）
使い方: python3 west_walls.py IN.3dm OUT.3dm WNEW.pkl

ユーザー（10-28 夜、Rhino の画面）：「2階の間仕切りが摩訶不思議な形になっている。間仕切りは必ず直方体のはず。直方体でない部分を修正して」
（10-27 夜：「壁やガラスは必ず長方形の押し出しのはず」「妻のところは三角形があるので長方形とは限らないが、必ず平面」「曲線が見られるのは架構のみ」）。

崩れていた所（段ごとに 24 の三角形の面を数えた）：
  7c2 add_inner.py walls：2 階の壁は四隅ごとに真上の面の高さを測った箱で、上端が四隅でねじれる（三角形 2 枚に割れる）。
  7c3 walls_spec.py・7d join_walls.py：上端を直線にそろえ・端を延ばすが、ねじれ・斜めの端が残る（1 階の壁にも三角形）。
  7f clip_parts.py：屋根の下面（スパンの平面・250 の格子）・梁・柱・床で削り、24 を一つに足す → 千を超える面・三角形の片。
そこで、削る段の後で西館の 24 を全部捨て、元の表から一枚ずつ作り直す（本館の _square と同じ考え：最後に「立面の形×厚み」）：
  - 一枚＝平面がまっすぐな帯（芯の線分×厚さ 120）×立面の形（多角形、穴は長方形）。弧に沿う壁（v 一定）は架構の線（u＝3 の倍数）で
    分けた弦ごとの一枚（弦のずれ 3 m で約 5 mm）。
  - 立面の形：床から上端まで。上端は一本のまっすぐな線（決定事項「間仕切りの構法」）：
      1 階（2 階の床の下まで）：3170 の水平（元のまま）。
      2 階・階段の箱：A 架構の線（u＝3 の倍数）の壁は両脇の梁の下端、B ほかは屋根の下面・梁・桁の下（壁の厚みの中の 5 本の線で 50 ごと）
      に収まるいちばん高い直線。その直線と水平の差が 150 未満なら水平。
  - 10-29 昼（監修の項 20261029-0928 の 2）：欠き込みはしない。戸・窓の開口と、構造・外皮・床・戸（削る段で間仕切りより優先の物）に
    重なる所（重なりの外接の範囲、厚み全体とみる）では、壁を縦の帯に分けて箱を短くし、突き当てる。一片はいつも 8 頂点の箱
    （上端が勾配の壁は上の面だけ傾く）。前は立面から欠き、厚みの一部にかかる物は浅い箱で欠いて、段・自分と交わる輪郭ができていた。
  - 壁の端：外壁の内面で止める。ほかの間仕切りの芯に当たる端は厚みの半分（60）延ばす（L 字の角・T 字。重なりはそのまま）。
読む表（同じ形を二度書かない）：1 階＝add_west_south.py の wall_u・wall_v の呼び出し、2 階＝add_inner.py の WALLS2、
階段の箱と 2 階の北の壁（u33）は下の表（fix_details.py の西館の節と同じ寸法）。
"""
import sys, os, ast, math, pickle, numpy as np, rhino3dm as r, trimesh, manifold3d as mf
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from uv import uv, xy
from solids import load, to_manifold

IN, OUT, WNPKL = sys.argv[1:4]
T = 120.0; H_ = T / 2
WN = pickle.load(open(WNPKL, 'rb'))['WN']; WNi = WN.buffer(-150.0, join_style=2)

# ---------------------------------------------------------------- 壁の表
def _src(fn): return open(os.path.join(HERE, fn), encoding='utf-8').read()
WALLS = []     # dict(kind='u'|'v', c=座標, a=(から, まで), holes=[(から, まで, 下, 上)], z0, top='1F'|'rule', name, cap=[(から, まで, 上)])
_ns = {}
_tree = ast.parse(_src('add_west_south.py'))
for nd in _tree.body:
    if isinstance(nd, ast.Assign) and len(nd.targets) == 1 and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id in ('KN', 'CB', 'GLK', 'H'):
        _ns[nd.targets[0].id] = eval(compile(ast.Expression(nd.value), 'a', 'eval'), {}, dict(_ns))
for nd in _tree.body:
    if isinstance(nd, ast.Expr) and isinstance(nd.value, ast.Call) and getattr(nd.value.func, 'id', '') in ('wall_u', 'wall_v'):
        a_ = [eval(compile(ast.Expression(x), 'a', 'eval'), {}, dict(_ns)) for x in nd.value.args]
        WALLS.append(dict(kind=nd.value.func.id[-1], c=float(a_[0]), a=(float(a_[1]), float(a_[2])), holes=list(a_[3]) if len(a_) > 3 else [],
                          z0=0.0, top='1F', H=float(_ns['H']), name='1階の間仕切り'))
N1 = len(WALLS)
_ia = _src('add_inner.py'); _t2 = ast.parse(_ia)
for nd in _t2.body:
    if isinstance(nd, ast.Assign) and getattr(nd.targets[0], 'id', '') in ('WALLS2', 'FL2', 'DOOR_H'):
        _ns[nd.targets[0].id] = eval(compile(ast.Expression(nd.value), 'a', 'eval'), {'dict': dict}, {})
FL2, DOOR_H = float(_ns['FL2']), float(_ns['DOOR_H'])
for w in _ns['WALLS2']:
    if isinstance(w.get('u'), float): kind, c, a = 'u', w['u'], w['v']
    else: kind, c, a = 'v', w['v'], w['u']
    holes = [(d0, d1, FL2, FL2 + DOOR_H) for d0, d1 in w.get('doors', [])]
    if kind == 'v' and abs(c + 5.0) < 1e-6 and a == (29.69, 33.0):
        a = (29.69, 29.94)          # 会議室｜階段：u30〜33 は階段の箱の西の壁（同じ線）と重なる → 箱の壁の端（29.94）まで
    WALLS.append(dict(kind=kind, c=float(c), a=(float(a[0]), float(a[1])), holes=holes, z0=FL2, top='rule', name='2階の間仕切り'))
N2 = len(WALLS) - N1
# 2 階の更衣｜会議室（u29.69、add_hall.py が会議室の南の端を更衣に仕切った線。10-29 夕：この段で 24 を作り直すときに表に無く、消えていた）。
# 戸は通路から会議室へ（v−6.6〜−5.8、h2100、add_hall.py と同じ）
WALLS.append(dict(kind='u', c=29.69, a=(-14.5, -5.0), holes=[(-6.6, -5.8, FL2, FL2 + DOOR_H)], z0=FL2, top='rule', name='2階の間仕切り（更衣・通路｜会議室）'))
# 更衣（職員のロッカー室、u27.75〜29.69・v−7.0〜−13.3）の室内窓（10-29 夕、ユーザー：更衣が暗いので室内窓、屋根に穴は開けない）：
# となりの明るい部屋（休憩室 u27.75・会議室 u29.69・通路 v−7.0）との間仕切りの上に、すりガラスのはめ殺しの欄間。2FL＋2.1（戸の上端にそろえる、
# ロッカー h1.8 より上）から間仕切りの上端（屋根・梁の下）まで、幅は更衣に面する長さなり、2.0 m 以下の板に分ける。間仕切りはその上を除いた箱
TRANSOM = {('u', 27.75): (-14.5, -7.06), ('u', 29.69): (-14.5, -7.06), ('v', -7.0): (27.81, 29.63)}
TR_Z0 = FL2 + DOOR_H
for w in WALLS:
    k_ = (w['kind'], round(w['c'], 2))
    if k_ in TRANSOM and w['z0'] >= FL2 - 1:
        w['transom'] = TRANSOM[k_]; w['holes'] = list(w['holes']) + [(TRANSOM[k_][0], TRANSOM[k_][1], TR_Z0, 1e5)]
# 階段の箱（fix_details.py の西館の節：芯 u30・u33.9・v−5.0・v−2.99、床から屋根の下まで）。開口：1 階の登り口（東の面 u30.06〜30.9、h3170）、
# 2 階の着き口（南の面、箱の内面のあいだ v−4.94〜−3.05、3170〜5350）、階段の下の倉庫の戸（西の面 u30.30〜31.50、h2100）
SB = dict(u0=30.0, u1=33.9, v0=-5.0, v1=-2.99)
WALLS += [dict(kind='u', c=30.0, a=(-5.0, -2.99), holes=[(-4.94, -3.05, 3170.0, 3250.0 + 2100.0)], z0=0.0, top='rule', name='階段の箱の壁（南、架構の線）'),
          dict(kind='u', c=33.9, a=(-5.0, -2.99), holes=[], z0=0.0, top='rule', name='階段の箱の壁（北）'),
          dict(kind='v', c=-2.99, a=(30.0, 33.9), holes=[(30.06, 30.9, 0.0, 3170.0)], z0=0.0, top='rule', name='階段の箱の壁（東）'),
          dict(kind='v', c=-5.0, a=(30.0, 33.9), holes=[(30.30, 31.50, 0.0, 2100.0)], z0=0.0, top='rule', name='階段の箱の壁（西）')]
# 2 階の北の壁（u33、会議室｜遊戯室）：v−13.87（外壁）〜−5.0。v−10.721 から東は腰 850（3250〜4100、上は室内窓 27）
WALLS += [dict(kind='u', c=33.0, a=(-14.5, -10.721), holes=[], z0=3250.0, top='rule', name='2階の北の壁（会議室｜遊戯室）'),
          dict(kind='u', c=33.0, a=(-10.721, -5.0), holes=[], z0=3250.0, top='1F', H=4100.0, name='2階の北の腰壁（会議室｜遊戯室、上は室内窓）')]

# ---------------------------------------------------------------- モデル
m, LN, parts = load(IN)
L24 = [i for i, l in enumerate(m.Layers) if l.Name.startswith('24_')][0]
def is_west24(p):
    if not p['layer'].split('::')[-1].startswith('24_'): return False
    c = p['bb'].mean(0); return uv(c[0], c[1])[1] < -0.9
DROP = {p['i'] for p in parts if is_west24(p)}
DROP |= {i for i, o in enumerate(m.Objects) if o.Attributes.LayerIndex == L24 and uv(*[(lambda b: ((b.Min.X + b.Max.X) / 2, (b.Min.Y + b.Max.Y) / 2))(o.Geometry.GetBoundingBox())][0])[1] < -0.9}
ATTR0 = next((m.Objects[i].Attributes for i in sorted(DROP)), None)
ABOVE = [p for p in parts if p['layer'].split('::')[-1].split('_')[0] in ('20', '20r', '20v', '20b', '20t', '22b', '22d')]
_TA = np.vstack([np.asarray(p['tm'].triangles) for p in ABOVE])
I_ALL = trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.Trimesh(**trimesh.triangles.to_kwargs(_TA)))
_TB = np.vstack([np.asarray(p['tm'].triangles) for p in ABOVE if p['layer'].split('::')[-1].startswith(('22b', '20'))])
I_BEAM = trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.Trimesh(**trimesh.triangles.to_kwargs(_TB)))
CUT = [p for p in parts if p['klass'] in 'SEFD' and p['M'] is not None and p['i'] not in DROP]
from rtree import index
_idx = index.Index(properties=index.Property(dimension=3))
for k, p in enumerate(CUT): _idx.insert(k, (*p['bb'][0], *p['bb'][1]))

def up(I, P, z0):
    loc, ir, _ = I.intersects_location(np.c_[P, np.full(len(P), z0)], np.tile([0, 0, 1.0], (len(P), 1)), multiple_hits=True)
    h = np.full(len(P), np.inf)
    for q, k in zip(loc, ir):
        if q[2] > z0 + 1: h[k] = min(h[k], q[2])
    return h

# ---------------------------------------------------------------- 一枚ずつ（弧の壁は架構の線で分けた弦）
def pieces(w):
    a0, a1 = sorted(w['a'])
    if w['kind'] == 'u':
        return [(a0, a1, False, False)]
    cuts = [3.0 * k for k in range(int(math.ceil(a0 / 3.0 + 1e-6)), int(math.floor(a1 / 3.0 - 1e-6)) + 1)
            if a0 + 0.3 < 3.0 * k < a1 - 0.3 and not any(min(h[0], h[1]) - 0.05 < 3.0 * k < max(h[0], h[1]) + 0.05 for h in w['holes'])]
    b = [a0] + cuts + [a1]
    return [(b[i], b[i + 1], i > 0, i < len(b) - 2) for i in range(len(b) - 1)]
def P_of(w, a): return np.ravel(xy(w['c'], a) if w['kind'] == 'u' else xy(a, w['c'])).astype(float)

SEGS = []          # (wall, 端の点 2 つ（world）) … 端を延ばす相手を探す
for w in WALLS:
    for a0, a1, j0, j1 in pieces(w): SEGS.append((w, P_of(w, a0), P_of(w, a1)))
def meets_other(w, E, d):
    """端 E（向き d で外へ）が、ほかの壁の芯の近く（70 以内、ほぼ直角）にあるか"""
    for w2, A, B in SEGS:
        if w2 is w: continue
        e = B - A; L_ = np.linalg.norm(e); e /= L_
        if abs(e @ d) > 0.3: continue
        t = (E - A) @ e
        if -70 <= t <= L_ + 70 and abs((E - A) @ np.array([-e[1], e[0]])) < 70: return True
    return False

CUTLOG = []; out_objs = []; TR_GLASS = []; stat = dict(walls=0, pieces=0, full=0, part=0, horiz=0, slope=0); info = []
for w in WALLS:
    for a0, a1, j0, j1 in pieces(w):
        P0, P1 = P_of(w, a0), P_of(w, a1)
        if w['kind'] == 'v':        # 弦を弧の平均の位置へ（弧から外へ矢高の 2/3）：部屋の面積（壁芯）が弧の壁と変わらない
            from uv import CX, CY
            mid = (P0 + P1) / 2; ro = mid - np.array([CX, CY]); ro /= np.linalg.norm(ro)
            sag = np.linalg.norm(P1 - P0) ** 2 / (8.0 * np.hypot(*(P0 - np.array([CX, CY])))); P0 = P0 + ro * sag * 2 / 3; P1 = P1 + ro * sag * 2 / 3
        d = P1 - P0; Lc = np.linalg.norm(d); d /= Lc; n = np.array([-d[1], d[0]])
        # 芯の線分を外壁の内面で止める
        seg = LineString([P0, P1]).intersection(WNi)
        if seg.is_empty: continue
        if seg.geom_type != 'LineString': seg = max(getattr(seg, 'geoms', [seg]), key=lambda g: g.length)
        q = np.array(seg.coords); s_a, s_b = sorted(((q - P0) @ d).tolist())
        ext0 = s_a > 1.0; ext1 = s_b < Lc - 1.0             # 外壁で止めた端
        if j0: s_a -= 2.0                                   # 弦のつなぎ（となりの弦と 2 mm 重ねる）
        elif not ext0 and meets_other(w, P0 + d * s_a, -d): s_a -= H_
        if j1: s_b += 2.0
        elif not ext1 and meets_other(w, P0 + d * s_b, d): s_b += H_
        S_of = lambda a: float((P_of(w, a) - P0) @ d)
        z0 = w['z0']
        # 上端
        if w['top'] == '1F':
            c0, c1 = w['H'], 0.0
        else:
            Ss = np.linspace(s_a, s_b, max(3, int((s_b - s_a) / 50) + 1))
            zs = 3600.0 if z0 < 1000 else z0 + 300.0
            P_ = np.array([P0 + d * s + n * t for t in (-H_ + 2, -30, 0, 30, H_ - 2) for s in Ss])
            Hs = up(I_ALL, P_, zs)
            isA = w['kind'] == 'u' and abs(w['c'] / 3.0 - round(w['c'] / 3.0)) < 1e-6
            if isA:      # A：両脇の梁の下端
                Pb = np.array([P0 + d * s + n * t for t in (-140.0, 140.0) for s in Ss])
                Hs = np.r_[Hs, up(I_BEAM, Pb, zs)]; P_ = np.r_[P_, Pb]
            ok = np.isfinite(Hs); sP = (P_[ok] - P0) @ d; hP = Hs[ok] - 10.0
            if not ok.any(): raise RuntimeError('上が測れない：' + w['name'])
            from scipy.optimize import linprog
            res = linprog(c=[-len(sP), -sP.sum()], A_ub=np.c_[np.ones(len(sP)), sP], b_ub=hP, bounds=[(None, None), (-1.0, 1.0)])
            if not res.success: raise RuntimeError('上端が決まらない：' + w['name'])
            c0, c1 = res.x; zh = hP.min()
            if max(c0 + c1 * s_a, c0 + c1 * s_b) - zh < 150.0: c0, c1 = zh, 0.0
            stat['horiz' if c1 == 0 else 'slope'] += 1
            info.append('%s u%.2f v%.2f %s %.0f〜%.0f' % (w['name'], *uv(*(P0 + d * (s_a + s_b) / 2)), 'A' if isA else 'B', c0 + c1 * s_a, c0 + c1 * s_b))
        # 10-29 昼（監修の項 20261029-0928 の 2、ユーザー：間仕切りは必ず直方体）：壁は直方体の箱だけ。開口と、優先の物（構造・外皮・床・戸）に
        # 当たる所は、欠き込まず、壁を縦の帯に分けて箱を短くし突き当てる（帯の境＝開口・当たる物の端。上端が勾配の壁は上の面だけ傾いた箱）。
        # 前は立面の形から欠き、厚みの一部にかかる物は浅い箱で欠いたので、厚みの面に 2.5〜8.6 の段・自分と交わる輪郭ができていた。
        top = lambda s: c0 + c1 * s
        tr_rng = None
        if w.get('transom'):                                             # 欄間は、上端が 2FL＋2.1 より 300 以上高い所だけ（西の低い軒の側は壁のまま）
            ta_, tb_ = sorted((S_of(w['transom'][0]), S_of(w['transom'][1]))); ta_, tb_ = max(ta_, s_a), min(tb_, s_b)
            if abs(c1) > 1e-9:
                sx_ = (TR_Z0 + 300.0 - c0) / c1
                if c1 > 0: ta_ = max(ta_, sx_)
                else: tb_ = min(tb_, sx_)
            elif c0 < TR_Z0 + 300.0: tb_ = ta_
            if tb_ - ta_ > 300.0: tr_rng = (ta_, tb_)
        obst = []                                                    # (s0, s1, z0, z1)：箱を置かない所
        for h in w['holes']:
            if h[3] >= 1e5:                                              # 欄間の穴
                if tr_rng is not None: obst.append((tr_rng[0], tr_rng[1], TR_Z0, 1e5))
                continue
            sa, sb = sorted((S_of(h[0]), S_of(h[1])))
            obst.append((sa, sb, h[2] if h[2] > z0 + 1 else z0 - 500.0, h[3]))
        def frame_pts(Pw): return np.c_[(Pw[:, :2] - P0) @ d, (Pw[:, :2] - P0) @ n, Pw[:, 2]]
        def to_world(L):
            return np.c_[P0[0] + L[:, 0] * d[0] + L[:, 1] * n[0], P0[1] + L[:, 0] * d[1] + L[:, 1] * n[1], L[:, 2]]
        def pieces_of(obst):
            br = sorted(set([s_a, s_b] + [x for o in obst for x in (o[0], o[1]) if s_a + 0.5 < x < s_b - 0.5]))
            strips = []
            for a, b in zip(br, br[1:]):
                if b - a < 0.5: continue
                cov = sorted([(o[2], o[3]) for o in obst if o[0] < b - 0.25 and o[1] > a + 0.25])
                tlo = min(top(a), top(b)); iv = []; lo = z0
                for c_lo, c_hi in cov:
                    if c_hi <= lo + 0.5: continue
                    if c_lo >= tlo - 0.5: break
                    if c_lo > lo + 0.5: iv.append((round(lo, 1), round(c_lo, 1)))
                    lo = max(lo, c_hi)
                if lo < tlo - 0.5: iv.append((round(lo, 1), 'T'))
                if strips and strips[-1][2] == iv: strips[-1][1] = b      # となりの帯と同じ高さの並びなら一つに
                else: strips.append([a, b, iv])
            out_ = []
            for a, b, iv in strips:
                if b - a < 20.0: continue                                # 20 未満の細い帯は置かない
                for lo, hi in iv:
                    if hi == 'T': q = [(a, lo), (b, lo), (b, top(b)), (a, top(a))]
                    else: q = [(a, lo), (b, lo), (b, hi), (a, hi)]
                    if min(q[2][1], q[3][1]) - lo < 20.0: continue
                    out_.append(q)
            return out_
        def box_tm(q):
            L_ = np.array([[x_, -H_, z_] for x_, z_ in q] + [[x_, H_, z_] for x_, z_ in q])     # (s, w, z)
            F_ = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
            t_ = trimesh.Trimesh(to_world(L_), F_, process=False)
            if t_.volume < 0: t_ = trimesh.Trimesh(to_world(L_), F_[:, ::-1], process=False)
            return t_
        for it in range(5):
            Q = pieces_of(obst); hit_ = False
            for q in Q:
                Mw = to_manifold(box_tm(q))
                if Mw is None: continue
                for k in _idx.intersection(tuple(Mw.bounding_box())):
                    X = Mw ^ CUT[k]['M']
                    if X.is_empty() or X.volume() < 1e5: continue
                    gx = X.to_mesh(); Lx = frame_pts(np.asarray(gx.vert_properties)[:, :3].astype(float))
                    lo, hi = Lx.min(0), Lx.max(0); hit_ = True
                    CUTLOG.append('%s %s %s s%.0f〜%.0f w%.0f〜%.0f z%.0f〜%.0f' % (w['name'][:8], round(uv(*P0)[0], 2), CUT[k]['layer'].split('::')[-1][:12], lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
                    obst.append((lo[0], hi[0], lo[2], hi[2])); stat['full'] += 1
            if not hit_: break
        else:
            raise RuntimeError('重なりが消えない：' + w['name'])
        for q in Q:
            t_ = box_tm(q); Vw = np.asarray(t_.vertices); Fw = np.asarray(t_.faces)
            mm = r.Mesh()
            for x_, y_, z_ in Vw: mm.Vertices.Add(float(x_), float(y_), float(z_))
            for a_, b_, c_ in Fw: mm.Faces.AddFace(int(a_), int(b_), int(c_))
            mm.Normals.ComputeNormals(); mm.Compact()
            at = r.ObjectAttributes(); at.LayerIndex = L24; at.Name = w['name']
            if ATTR0 is not None:
                for k_ in ('ColorSource', 'ObjectColor', 'MaterialSource', 'MaterialIndex'):
                    try: setattr(at, k_, getattr(ATTR0, k_))
                    except Exception: pass
            out_objs.append((mm, at)); stat['pieces'] += 1
        if tr_rng is not None:                                           # 欄間のガラス（t12、壁の芯、平らな板の押し出し）
            ta_, tb_ = tr_rng
            if tb_ - ta_ > 100.0:
                npn_ = int(math.ceil((tb_ - ta_) / 2000.0)); edges_ = np.linspace(ta_, tb_, npn_ + 1)
                for e0_, e1_ in zip(edges_, edges_[1:]):
                    q_ = [(e0_, TR_Z0), (e1_, TR_Z0), (e1_, top(e1_)), (e0_, top(e0_))]
                    L_ = np.array([[x_, -6.0, z_] for x_, z_ in q_] + [[x_, 6.0, z_] for x_, z_ in q_])
                    Fq_ = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
                    tq_ = trimesh.Trimesh(to_world(L_), Fq_, process=False)
                    if tq_.volume < 0: tq_ = trimesh.Trimesh(to_world(L_), Fq_[:, ::-1], process=False)
                    mg_ = r.Mesh()
                    for x_, y_, z_ in np.asarray(tq_.vertices): mg_.Vertices.Add(float(x_), float(y_), float(z_))
                    for a_, b_, c_ in np.asarray(tq_.faces): mg_.Faces.AddFace(int(a_), int(b_), int(c_))
                    mg_.Normals.ComputeNormals(); mg_.Compact()
                    TR_GLASS.append((mg_, w['name'])); stat['transom'] = stat.get('transom', 0) + 1
    stat['walls'] += 1

# 優先の低い物（家具 I・外の付属 X）は、作り直した壁と重なる所を削る（削る段と同じ決まり。弦にした壁が家具に数 mm 食い込む所）
from solids import from_manifold, mesh_from_vf
WM = [to_manifold(trimesh.Trimesh(np.array([[v.X, v.Y, v.Z] for v in mm.Vertices]), np.array([[f[0], f[1], f[2]] for f in mm.Faces]), process=False)) for mm, _ in out_objs]
WM = [x for x in WM if x is not None]
_wi = index.Index(properties=index.Property(dimension=3))
for k, x in enumerate(WM): _wi.insert(k, tuple(x.bounding_box()))
FIX = {}
for p in parts:
    if p['klass'] not in 'IX' or p['M'] is None or p['i'] in DROP: continue
    hits = [WM[k] for k in _wi.intersection((*p['bb'][0], *p['bb'][1]))]
    if not hits: continue
    R_ = p['M']; cut_ = False
    for C in hits:                                   # 壁ごとに引く（重なった壁を足してから引くと、足した立体が崩れて引けない所があった）
        X = R_ ^ C
        if X.is_empty() or X.volume() < 1e4: continue
        R_ = R_ - C; cut_ = True
    if not cut_ or R_.is_empty() or p['M'].volume() - R_.volume() < 1e5: continue
    FIX[p['i']] = mesh_from_vf(*from_manifold(R_)); stat['cut_I'] = stat.get('cut_I', 0) + 1
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for i, o in enumerate(m.Objects):
    if i in DROP: continue
    out.Objects.Add(FIX.get(i, o.Geometry), o.Attributes)
for mm, at in out_objs: out.Objects.AddMesh(mm, at)
if TR_GLASS:                                                             # すりガラスの室内窓（欄間）のレイヤー（一つのレイヤーに一つの素材：27 は透明、27f はすりガラス）
    lf_ = r.Layer(); lf_.Name = '27f_西館_室内窓（すりガラス、欄間）'; lf_.Color = (205, 222, 232, 255)
    L27F = out.Layers.Add(lf_)
    for mg_, nm_ in TR_GLASS:
        at = r.ObjectAttributes(); at.LayerIndex = L27F; at.Name = '室内窓（欄間、すりガラス t12、はめ殺し、更衣の明かり、' + nm_ + '）'
        out.Objects.AddMesh(mg_, at)
out.Write(OUT, 8)
print(f'west_walls: 西館の間仕切り {len(DROP)} 物を捨て、壁 {stat["walls"]} 枚（1 階 {N1}・2 階 {N2}・階段の箱 4・北の壁と腰壁 2）を {stat["pieces"]} 片の直方体に'
      f'（上端 水平 {stat["horiz"]}・勾配 {stat["slope"]}、開口・優先の物で箱を分けた所 {stat["full"]}、壁で削った家具 {stat.get("cut_I", 0)}、更衣の欄間のガラス {stat.get("transom", 0)} 枚）')
for x in info: print('  ', x)
if os.environ.get('WW_LOG'):
    for x in CUTLOG: print('   cut', x)
print('written', OUT, len(out.Objects))
