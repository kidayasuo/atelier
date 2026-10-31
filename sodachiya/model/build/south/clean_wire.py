"""Rhino 版（sodachiya.3dm）を作る：メッシュの版の物を、Rhino で閉じたソリッド（押し出し・ポリサーフェス）に置き換える。
使い方: python3 clean_wire.py IN.3dm OUT.3dm　　（段10。ソリッド係、10-25。前は更新係）
ユーザー（10-25）：全部閉じたソリッドに。曲線は曲線で。
- 一つの物の、辺でつながる三角形の組ごとに（solidify.py）：
  1. 押し出し（角柱。両端は斜めの面でもよい）にちょうどなる → Extrusion（輪郭の円は円弧、穴は内側の輪郭）。いちばん軽い。
  2. それ以外 → 閉じた Brep（同じ平面の三角形は一枚の面、細かく分けた曲面は円柱・球・円環（管）の面に戻す）。
  3. 自由な形（クスノキ・地形・網の鉢など、三角形ごとに面になってしまうもの）→ 閉じたメッシュのまま。
- 閉じていない面（部屋の色の板・道路・太陽光の板・網・地形）は厚みをつけて閉じる（SHEET）。
- 西館の屋根の層（20・20r・20p）の片は、屋根の定義（roofw の SPANS・STRIPS・roof_line）からスパンごとの面で直接作る
  （10-28、ユーザー：屋根は平面が基本、うまくゆかない所だけ曲面。平面のスパンは平面、北西の角と筋は四隅の双一次＝次数 1×1、
  solidify.Ruled）。上下の面はスパンの境（放射の線）で分け、層は z をずらした同じ面。作れない片（軒の下面が上がる通気、
  段7fで上げられた 20p など）は前の道（log に「西館の屋根：作らなかった片」）。
- 西館の屋根（20・20p・20t）のねじれた面の片は、線織面（ruled_roof.py）の六枚の組を辺でつないで閉じる
  （平らな面でできた片は上のふつうの道で）。一枚だけの片（薄い板・太陽光）は厚みをつける。
- 開いた輪郭の押し出し（外構の塀・柵の面）は輪郭に厚み FENCE_T をつけ、ふたの無い押し出しにはふたをする。
- 二つより多くの面が集まる辺（触れあう二つの立体）は、立体ごとに分ける。
- 新しいオブジェクトはアイソカーブを表示しない（WireDensity = -1）。同じ物から出た複数の立体はグループに。
"""
import sys, os, math, numpy as np, rhino3dm as r
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ruled_roof as RR
import solidify as SD
from shapely.geometry import LineString

IN, OUT = sys.argv[1], sys.argv[2]
WELD = 0.01                      # 同じ頂点とみなす距離 (mm)。0.5 だと近くの別の立体がつながってしまう（10-25）
# 閉じていない面の厚みのつけ方（レイヤーの番号 → (向き, mm)）。'down'：鉛直に下へ、'base'：いちばん低い所からさらに下の
# 平らな底まで、'both'：面の両側に半分ずつ。無いレイヤーは DEFAULT_SHEET（部屋の色の板は床から 10 mm 上にある → 床まで）
SHEET = {'03': ('down', 100.0), '10p': ('down', 20.0), '20p': ('down', 20.0), '83': ('both', 20.0),
         '90': ('base', 100.0), '78': ('base', 50.0)}
DEFAULT_SHEET = ('down', 10.0)
FREEFORM = ('90', '92', '99')     # 自由な形（地形・水・雨の川）は閉じたメッシュのまま（監修 10-27：Brep の三角形の寄せ集めは重い、90 だけで 4.3 MB）
FENCE_T = 20.0                   # 開いた輪郭の押し出し（塀・柵・生垣の面）につける厚み (mm)

P3 = lambda p: r.Point3d(float(p[0]), float(p[1]), float(p[2]))


def mesh_arrays(g, weld):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
    key = {}; idx = []
    for p in np.round(V / weld).astype(np.int64):
        idx.append(key.setdefault(tuple(p), len(key)))
    W = np.zeros((len(key), 3))
    for i, j in enumerate(idx): W[j] = V[i]
    T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]
        a, b, c, d = (idx[f[0]], idx[f[1]], idx[f[2]], idx[f[3]])
        if len({a, b, c}) == 3: T.append((a, b, c))
        if d != c and len({a, c, d}) == 3: T.append((a, c, d))
    return W, np.array(T, int).reshape(-1, 3)


def components(T):
    """辺を共有する三角形どうしをつなぐ（頂点だけ接する箱は別の立体）"""
    par = list(range(len(T)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    E = {}
    for i, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)):
            k = (min(e), max(e))
            if k in E: par[f(i)] = f(E[k])
            else: E[k] = i
    lab = {}
    for i in range(len(T)): lab.setdefault(f(i), []).append(i)
    return [T[ix] for ix in lab.values()]


def raw_shells(g, W, T0):
    """溶接する前の頂点の番号でつながる組が、どれも閉じた立体なら、その組ごとに（触れ合う板を一つずつの立体に：
    fix_details.py の面ごとの板の階段・階段の箱、10-25）。そうでなければ None（三角形のスープは溶接でつなぐ）"""
    n = len(g.Vertices)
    if g.Faces.Count < 24: return None
    par = list(range(n))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    F = []
    for i in range(g.Faces.Count):
        q = g.Faces[i]; F.append((q[0], q[1], q[2], q[3]))
        for a_ in (q[1], q[2], q[3]): par[f(a_)] = f(q[0])
    lab = {}
    for i, q in enumerate(F): lab.setdefault(f(q[0]), []).append(i)
    if len(lab) < 2: return None
    # 溶接後の三角形を面の組ごとに：mesh_arrays と同じ規則で数え直す
    key = {}; idx = []
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(n)])
    for p in np.round(V / WELD).astype(np.int64): idx.append(key.setdefault(tuple(p), len(key)))
    out = []
    for ids in lab.values():
        T = []
        for i in ids:
            a, b, c, d = (idx[x] for x in F[i])
            if len({a, b, c}) == 3: T.append((a, b, c))
            if d != c and len({a, c, d}) == 3: T.append((a, c, d))
        T = np.array(T, int).reshape(-1, 3)
        ec = {}
        for x, y, z in T:
            for e in ((x, y), (y, z), (z, x)): kk = (min(e), max(e)); ec[kk] = ec.get(kk, 0) + 1
        if not len(T) or any(v != 2 for v in ec.values()): return None
        out.append(T)
    return out


def copy_attr(a0, grp=None):
    a = r.ObjectAttributes()
    a.LayerIndex = LMAP[a0.LayerIndex]
    for k in ('ColorSource', 'ObjectColor', 'MaterialSource', 'MaterialIndex', 'Name', 'Visible', 'PlotColorSource', 'PlotColor'):
        try: setattr(a, k, getattr(a0, k))
        except Exception: pass
    a.WireDensity = -1
    if grp is not None: a.AddToGroup(grp)
    return a


def thickness(W, T):
    """閉じた薄い片の厚み：体積 ÷ 上を向く面の面積"""
    a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]
    N = np.cross(b - a, c - a); vol = abs(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6)
    up = np.linalg.norm(N, axis=1)[N[:, 2] > 0.3 * np.linalg.norm(N, axis=1)].sum() / 2
    return vol / up if up > 0 else 10.0


def deviation(geo, W, T):
    """立体の辺の上の点が、もとのメッシュの面からいちばん離れる距離 (mm)"""
    import trimesh
    tm = trimesh.Trimesh(W, T, process=False); pts = []
    for x, k in geo:
        if not isinstance(x, (r.Brep, r.Extrusion)): continue
        b = x.ToBrep(False) if isinstance(x, r.Extrusion) else x
        for i in range(len(b.Edges)):
            e = b.Edges[i]; d = e.Domain
            for t in np.linspace(d.T0, d.T1, 5): p = e.PointAt(t); pts.append((p.X, p.Y, p.Z))
    if not pts: return 0.0
    _, dist, _ = trimesh.proximity.closest_point(tm, np.array(pts))
    return float(dist.max())


def close_extrusion(e):
    """ふたの無い押し出し → ふたをする。開いた輪郭（塀・柵の面）→ 輪郭に厚み FENCE_T。できなければ None"""
    p = e.Profile3d(0, 0.0)
    ps, pe = np.array([e.PathStart.X, e.PathStart.Y, e.PathStart.Z]), np.array([e.PathEnd.X, e.PathEnd.Y, e.PathEnd.Z])
    d = pe - ps; h = float(np.linalg.norm(d)); d = d / h
    if not p.IsClosed:
        X = np.cross(d, [1., 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1., 0]); X /= np.linalg.norm(X); Y = np.cross(d, X)
        nc = p.ToNurbsCurve(); dom = nc.Domain
        if nc.Degree == 1: pts = [nc.Points[i] for i in range(len(nc.Points))]; Q = [(q.X, q.Y, q.Z) for q in pts]
        else:
            n = max(32, 64 * nc.SpanCount); Q = [(lambda q: (q.X, q.Y, q.Z))(nc.PointAt(t)) for t in np.linspace(dom.T0, dom.T1, n + 1)]
        Q = np.array(Q); q2 = np.c_[(Q - ps) @ X, (Q - ps) @ Y]
        poly = LineString(q2).buffer(FENCE_T / 2, cap_style=2, join_style=2, mitre_limit=10)
        if poly.geom_type != 'Polygon': return None
        ring = np.array(poly.exterior.coords)[:-1]
        to3 = lambda q: ps + q[0] * X + q[1] * Y
        p = SD._profile(ring, to3, SD._arc_runs(ring))
    for k in range(2):
        if k: p.Reverse()
        x = r.Extrusion.Create(p, h, True)
        if x is None or not x.IsValid: continue
        dd = np.array([x.PathEnd.X - x.PathStart.X, x.PathEnd.Y - x.PathStart.Y, x.PathEnd.Z - x.PathStart.Z])
        if dd @ d > 0: return x
    return None


# 西館の屋根の面の関数と折れの位置（roofw.py、西館係）
# RULED_STRICT：True＝メッシュのもとの頂点がどれも面（屋根の定義＋層のずれ）から 1 mm 以内の片だけをスパンごとの面に。
# 既定 False（10-28 昼、ユーザー・監修：定義が決めた形、メッシュの弦のずれは近似）＝8 割以上がのる片は定義どおりの面に（辺のずれ 15 mm まで）
RULED_STRICT = os.environ.get('RULED_STRICT') == '1'
try:
    import pickle, roofw
    from uv import uv as _uv, xy as _xy
    _ROOT = os.environ.get('SODACHIYA_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    _RW = roofw.make(pickle.load(open(os.path.join(_ROOT, 'data', 'wnew.pkl'), 'rb'))['WN'])
    ROOF_SPEC = dict(func=_RW['roof_f'], ubreaks=[21.0, 51.0] + [f + d for f in _RW['FRAMES'][1:] for d in (-0.09, 0.09)] + list(_RW.get('KINKS', [])), vbreaks=[_RW['VRIDGE']])   # KINKS：屋根の線（梁）で面が折れる（10-27夜、西館係）
    # スパンごとの面（10-28 昼）：読むのは roofw の SPANS（(u0, u1, 'plane', (Pa.x, Pa.y, c0, c1, c2)) か (u0, u1, 'ruled', None)）・
    # STRIPS（一次で移る筋 (u0, u1)）・roof_line(u, side)（放射の線 u の上の屋根の線、棟と軒の xyz）・VRIDGE だけ。
    # 平面のスパン → 平面（四隅を平面の上に取る）、双一次のスパンと筋 → 両端の屋根の線を四隅にした双一次（solidify.Ruled）。
    # 面の受け持ちは u で：平面・双一次のスパンから筋の分を除き、筋はそれだけで一つ。西館係が SPANS・STRIPS を変えればそのまま追いつく
    _VR = _RW['VRIDGE']; _RL = _RW['roof_line']; _ST = list(_RW['STRIPS'])
    def _pt(u, v): return np.array(_xy(u, v), float).ravel()
    _SEG = []                                                 # (u0, u1, 四隅 [棟 u0, 棟 u1, 軒 u0, 軒 u1])
    for ua, ub, kind, cf in _RW['SPANS']:
        a, b = ua, ub
        for s0, s1 in _ST:
            if s0 < ua < s1: a = s1
            if s0 < ub < s1: b = s0
        if kind == 'plane':
            px, py, c0, c1, c2 = cf
            C = [np.r_[q, c0 + c1 * (q[0] - px) + c2 * (q[1] - py)] for q in (_pt(a, _VR), _pt(b, _VR), _pt(a, _VR - 10.0), _pt(b, _VR - 10.0))]
        else:
            (Ra, Ea), (Rb, Eb) = _RL(ua, 'N'), _RL(ub, 'S'); C = [Ra, Rb, Ea, Eb]
        _SEG.append((a, b, C))
    for s0, s1 in _ST:                                        # 筋（一次の移り）は、両端の屋根の線の双一次が roof_f から 0.3 mm 以内になるまで細かく
        for n_ in (1, 2, 3, 4, 6, 8):
            us_ = np.linspace(s0, s1, n_ + 1); dv_ = 0.0
            for a_, b_ in zip(us_, us_[1:]):
                Rs_ = SD.Ruled([*_RL(a_)[:1], *_RL(b_)[:1], *_RL(a_)[1:], *_RL(b_)[1:]])
                for uu in np.linspace(a_, b_, 5):
                    Rr_, Er_ = _RL(uu)
                    for t_ in np.linspace(0.0, 1.1, 12):
                        q_ = Rr_ + (Er_ - Rr_) * t_; dv_ = max(dv_, abs(Rs_.z(q_) - _RW['roof_f'](q_[0], q_[1])))
            if dv_ < 0.3: break
        for a_, b_ in zip(us_, us_[1:]):
            (Ra, Ea), (Rb, Eb) = _RL(a_), _RL(b_); _SEG.append((a_, b_, [Ra, Rb, Ea, Eb]))
    _SEG.sort(key=lambda x: x[0])
    _UB = [x[0] for x in _SEG[1:]]                            # 面の境の u（放射の線、ここでメッシュを切る）
    def _bay(x, y):
        u = float(np.ravel(_uv(x, y)[0])[0]); return int(np.searchsorted(_UB, u))
    RULED = dict(corners=lambda k: _SEG[k][2], bay=_bay, strict=RULED_STRICT, snap=2.0 if RULED_STRICT else 60.0,
                 lines=[(_pt(u_, _VR), _pt(u_, -16.0) - _pt(u_, _VR)) for u_ in _UB])
except Exception as _e:
    print('roofw を読めない（西館の屋根は前の作り方）:', _e); ROOF_SPEC = None; RULED = None
RULED_DEV = 1.0 if RULED_STRICT else 60.0      # スパンごとの面で作った片の辺が、メッシュの版から離れてよい距離 (mm、ゆるい時は大きな間違いだけを止める。光の筋（棟で段 約10 cm を 18 cm で移る）の中はメッシュの弦が 約35 mm ずれる。ずれは log に)
RULED_LOG = []                   # 作らなかった片（場所・ずれ）
RULED_DEVS = []                  # 作った片の、メッシュの版とのずれ（レイヤー・mm・(u, v)）


def ruled_piece(W, T, lname):
    """西館の屋根の層の片を、スパンごとの面（solidify.Ruled）の閉じた Brep に。できなければ None（前の道）"""
    ed = np.sort(np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
    cnt = np.unique(ed, axis=0, return_counts=True)[1]
    alts = [(W, T)] if (cnt == 2).all() else SD.via_manifold(W, T)        # 触れ合う片は manifold3d で一つの多様体に
    why = 'not manifold'
    for Wm, Tm in alts:
        n0 = len(Wm); W2, T2 = SD.split_by_lines(Wm, Tm, RULED['lines'])
        # 一定の高さにのらなくてよい頂点の割合：20p は 0.2（段7fで一部の頂点だけ +20 上げられた片を、前の道に残すため）、ほかは制限なし
        # （細い片では梁の帯で切った縁の頂点が、筋（一次の移り）の中ではほとんどの頂点が、網目の弦で定義からずれる。高さはいちばん多い値）
        spec = dict(RULED, n0=n0, report=[], share=0.2 if lname.startswith('20p') else 1.0)
        b, info = SD.solid_from_mesh(W2, T2, ruled=spec)
        if b is None or not info.startswith('curved'):
            why = info.split('/')[0][:60]; continue
        dv = deviation([(b, 'curved')], W, T)
        if dv <= RULED_DEV:
            c_ = W[np.unique(T)].mean(0); RULED_DEVS.append((lname.split('_')[0], round(dv, 1), tuple(np.round([float(np.ravel(q)[0]) for q in _uv(c_[0], c_[1])], 2))))
            return [(b, 'curved')]
        why = 'ずれ %.1f mm' % dv
    bb = W[np.unique(T)]; c = bb.mean(0)
    RULED_LOG.append((lname.split('_')[0], len(T), tuple(np.round(_uv(c[0], c[1]), 2)) if RULED else None, why))
    return None


m = r.File3dm.Read(IN)
out = r.File3dm()
out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
# ---- レイヤーの親（Rhino で親を消すと子もまとめて消える）。子は名前の順。
import uuid, re
PARENTS = [
    # 屋根の層を支える母屋（10v・20v）と光の筋をまたぐつなぎ（10k・22t）も屋根のグループに：屋根を消すと上には架構（柱・梁・桁）だけが残る（ユーザー 10-28）
    ('A 屋根・越屋根', ('10', '10r', '10t', '10p', '20', '20r', '20t', '20p', '26', '28', '29', '30', '50a', '50b', '50c', '50d', '10k', '10m', '20m', '10b', '10v', '20v', '22t', '20b')),
    ('B 頭上（ファン・天蓋・物干し）', ('51', '51w', '58', '58b')),
    ('C 架構（柱・梁・桁）', ('11a', '11b', '11c', '22a', '22b', '22c', '22d', '10s')),
    ('D 壁・建具（外壁・間仕切り・ガラス戸）', ('16', '16d', '16o', '17', '18', '19', '19b', '19c', '19d', '19e', '21', '16e', '16f', '21g', '24', '27', '35', '35b', '35d', '66', '16s', '17g', '16h', '16i', '19f', '19g', '17y', '21y', '17k')),     # 17y・21y：大和張りの上板（本館係・西館係、10-28）、17k：縁側の格子の背板（本館係、10-28）
    ('E 床・部屋の色', ('36b', '12', '13', '14', '15', '16b', '23', '25', '31', '32', '33', '34', '36', '41', '42', '43', '44', '45', '52', '53', '54', '56', '57', '59', '43b')),
    ('F しつらえ（家具・水まわり・格子）', ('37', '38', '39', '40', '40k', '40r', '40w', '46', '47', '48', '48f', '49', '55')),
    ('T 樹木（読書の庭・外構・園庭の木、ユーザー 10-28：樹木は樹木のレイヤーに。番号は係ごとのまま）', ('67', '67c', '77', '77c', '79', '79c', '94', '94b', '94c', '94g')),   # 79・79c みなみのさんかくの目隠しも（ユーザー 10-29）。94b 園庭の低木・94g 園庭の草も（ユーザー 10-31、園庭の係）
    ('G 外（本体）', ('60', '62', '63', '64')),
    ('H 外構（詳細設計）', ('70', '70h', '70k', '70m', '71', '72', '73', '73c', '74', '74a', '74w', '74p', '74s', '75', '75p', '75s', '75t', '76', '76b', '76g', '76p', '76s', '78', '78a')),
    ('I 敷地', ('00', '01', '01s', '02')),     # 01s：敷地の土の受け皿（更新係、10-29）
    ('L 周辺の道路・建物（PLATEAU、data/context_plateau.json）', ('03', '03g', '04')),     # 03g：周辺の平らな地面（更新係、10-29）
    ('J 遊戯室の遊具・しつらえ（data/play.json）', ('80', '81', '82', '83', '84', '85', '86', '87', '88', '89')),
    ('K 園庭（data/garden.json、園庭のチャット）', ('90', '90l', '91', '92', '92s', '93', '95', '95w', '95m', '95p', '95r', '95s', '96', '97', '97h', '98', '99')),   # 90l 線・95p シャワーの柱・95r 木の縁と丸太・95s 輪のシャワー・92s 雨庭の玉石（園庭、10-30）
]
# 開いたときに消しておくレイヤー（ユーザー 10-28：街の建物と樹木はデフォルトで消す）。物は入っている（表示を戻せば見える）。
# rhino/zumen.py はこのレイヤーも読む（樹冠は平面の想像線、周辺は切断の範囲）
HIDE_DEFAULT = ('04', '91', '90l')   # 91 園庭の等高線の曲線（ユーザー 10-29：レンダリングで光る）、90l 園庭の線（中心線・輪郭・道すじ、ユーザー 10-30）
# 樹木は中のレイヤーを全部点けたまま、親の「T 樹木」を消しておく（ユーザー 10-29：親を点ければ全部出る）
HIDE_PARENT = ('T 樹木',)
def code(name):
    mm_ = re.match(r'^(\d+[a-z]?)_', name); return mm_.group(1) if mm_ else None
pid = {}
# 空の作業用レイヤーを0番に（ユーザー、10-24：開いたときの現在のレイヤーが屋根のグループにならないように。
# rhino3dmは現在のレイヤーを書けないが、Rhinoは指定の無いファイルを0番のレイヤーで開く）
_d = r.Layer(); _d.Name = '既定（作業用、空）'; _d.Id = uuid.uuid4(); _d.Color = (0, 0, 0, 255)
out.Layers.Add(_d)
for pname, codes in PARENTS:
    p = r.Layer(); p.Name = pname; p.Id = uuid.uuid4(); p.Color = (90, 90, 90, 255)
    if pname.startswith(HIDE_PARENT): p.Visible = False
    out.Layers.Add(p); pid[pname] = p.Id
LMAP = {}
order = sorted(range(len(m.Layers)), key=lambda i: m.Layers[i].Name)
for i in order:
    l = m.Layers[i]; c = code(l.Name)
    for pname, codes in PARENTS:
        if c in codes: l.ParentLayerId = pid[pname]; break
    if c in HIDE_DEFAULT: l.Visible = False                 # 開いたときは消しておく（ユーザー 10-28）
    LMAP[i] = len(out.Layers); out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for gr in m.Groups: out.Groups.Add(gr)
stat = {}
SEEN = set()                 # 出した立体（レイヤー・種類・面の数・外接箱）：同じ物を二度出さない
odd = {}                     # 閉じたソリッドにならなかった物（レイヤー → 数）
def count(kind, layer):
    stat[kind] = stat.get(kind, 0) + 1
    if kind in ('mesh', 'surface', 'open', 'dropped'): odd.setdefault(layer, {}).setdefault(kind, 0); odd[layer][kind] += 1


for oi, o in enumerate(m.Objects):
    g = o.Geometry; a0 = o.Attributes; lname = m.Layers[a0.LayerIndex].Name; lc = code(lname)
    if isinstance(g, r.Extrusion) and not g.IsSolid:
        x = close_extrusion(g)
        if x is not None:
            out.Objects.AddExtrusion(x, copy_attr(a0)); count('extrusion', lname); continue
    if not isinstance(g, r.Mesh):
        a1 = a0.Duplicate() if hasattr(a0, 'Duplicate') else a0; a1.LayerIndex = LMAP[a0.LayerIndex]
        out.Objects.Add(g, a1)
        if isinstance(g, (r.Brep, r.Extrusion)): count('kept' if g.IsSolid else 'open', lname)
        continue
    sheet = SHEET.get(lc, DEFAULT_SHEET)
    geo = []
    west_roof = any(t in lname for t in ('西館_屋根', '西館_光の筋'))
    if west_roof:
        W, T0 = mesh_arrays(g, 0.5)                      # ruled_roof.py はこの溶接で作った（10-24）
        for T in components(T0):
            # 屋根の層（20・20r・20p）の大きな片：上下の面を屋根の面の関数の面（Graph、建物の座標の双 3 次、折れは節点で）に、
            # 縁は鉛直の平面・曲線の面（10-27 夜、ソリッド係：前は 300 の格子の平らな三角形の集まりで、Rhino 版で縁がぎざぎざ・約6,500面）
            if lc in ('20', '20r', '20p') and len(T) > 24 and RULED is not None:
                got = ruled_piece(W, T, lname)
                if got: geo += got; continue
            if lc in ('20', '20r', '20p') and len(T) > 500 and ROOF_SPEC is not None:
                bg, info = SD.solid_from_mesh(W, T, graph=ROOF_SPEC)
                if bg is not None and info.startswith('curved') and deviation([(bg, 'curved')], W, T) <= 15.0:
                    geo.append((bg, 'curved')); continue
                if bg is None and info.startswith('not manifold'):                # 触れ合う片：manifold3d で一つの多様体に直してから
                    done_ = False
                    for Wm, Tm in SD.via_manifold(W, T):
                        bg, info = SD.solid_from_mesh(Wm, Tm, graph=ROOF_SPEC)
                        if bg is not None and info.startswith('curved') and deviation([(bg, 'curved')], W, T) <= 15.0:
                            geo.append((bg, 'curved')); done_ = True; break
                    if done_: continue
            # 平らな面でできた片（光の筋のガラス・ふさぐ板・平らな屋根の片）は、ふつうの道でちょうどの立体に。
            # 三角形ごとに面になる（ねじれた）片だけを線織面に
            g1 = SD.to_solids(W, T, sheet)
            if all(k == 'extrusion' or (isinstance(x, r.Brep) and len(x.Faces) <= 60) for x, k in g1):
                geo += g1; continue
            gs = RR.to_surfaces(W, T)                         # 箱で近づける narrow_box は使わない（ずれが 10 cm になる、10-25）
            if not gs:
                geo += g1; continue
            srfs = [x.Faces[0].UnderlyingSurface() for x in gs if isinstance(x, r.Brep)]
            _ed = np.sort(np.vstack([np.asarray(T)[:, [0, 1]], np.asarray(T)[:, [1, 2]], np.asarray(T)[:, [2, 0]]]), axis=1)
            _closed = bool(len(_ed)) and bool((np.unique(_ed, axis=0, return_counts=True)[1] == 2).all())   # 辺がみな二つの面に共有＝閉じた片
            if lc == '20p' and not _closed: th, cen = sheet[1], False         # 太陽光の板（屋根の面 +20）→ 屋根まで（閉じた屋根材は下の道、10-27夜）
            else: th, cen = thickness(W, T), True             # 薄い片は、測った厚みで面の両側に
            g2 = SD.solids_from_surfaces(srfs, th, cen)
            for x in gs:                                      # けらばの小さなメッシュ
                if isinstance(x, r.Mesh):
                    Wm, Tm = mesh_arrays(x, WELD); g2 += SD.to_solids(Wm, Tm, sheet)
            # 線織面がもとの面から 10 mm より離れる片は、平らな面の立体（ちょうど、ただし面の数が多い）に
            geo += g2 if (lc == '20p' and not _closed) or deviation(g2, W, T) <= 10.0 else g1
    else:
        W, T0 = mesh_arrays(g, WELD)
        if len(T0) == 0: continue
        SD.MESH_ONLY = lc in FREEFORM
        for T in raw_shells(g, W, T0) or components(T0):
            g1 = SD.to_solids(W, T, sheet)
            if not g1: count('dropped', lname)                # 太さの無い針は捨てる
            geo += g1
    keep = []
    for x, kind in geo:                                   # 同じレイヤーに同じ形（種類・面の数・外接箱 0.1 mm）がもう出ていれば捨てる（10-28）
        bb = x.GetBoundingBox(); nf = len(x.Faces) if isinstance(x, (r.Brep, r.Mesh)) else 0
        kk = (a0.LayerIndex, type(x).__name__, nf) + tuple(round(v, 1) for v in (bb.Min.X, bb.Min.Y, bb.Min.Z, bb.Max.X, bb.Max.Y, bb.Max.Z))
        if kk in SEEN: count('duplicate', lname); continue
        SEEN.add(kk); keep.append((x, kind))
    geo = keep
    grp = None
    if len(geo) > 1:
        grp = len(out.Groups); out.Groups.Add(r.Group())
    for x, kind in geo:
        at = copy_attr(a0, grp); at.SetUserString('src', str(oi))      # メッシュの版の何番目の物から（確かめ用、check_solids.py）
        if isinstance(x, r.Extrusion): out.Objects.AddExtrusion(x, at)
        elif isinstance(x, r.Brep): out.Objects.AddBrep(x, at)
        else: out.Objects.AddMesh(x, at)
        count(kind, lname)
print(stat)
if RULED_LOG:
    print('西館の屋根：スパンごとの面で作らなかった片（レイヤー・三角形の数・(u, v)・わけ）:')
    for x in RULED_LOG: print('  ', x)
if RULED_DEVS:
    print('西館の屋根：スパンごとの面で作った片のずれ（大きい順、レイヤー・mm・(u, v)）:', sorted(RULED_DEVS, key=lambda x: -x[1])[:12])
print('閉じたソリッドでない物（メッシュは閉じている）:', {k: v for k, v in sorted(odd.items())})
out.Write(OUT, 8); print('written', OUT, len(out.Objects))
