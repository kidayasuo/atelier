"""優先順位で削る段（設計監修、10-24。ユーザー：部材どうしの重なりをモデルの作り方で根本から解決する）
使い方: python3 clip_parts.py IN.3dm OUT.3dm WNEW.pkl [LOG.json]      （室内の戸の後、護岸と園庭の取り込みの前）

考え方（ArchiCAD の「優先度に基づく接続」・Revit の結合と同じ）：
  部材を種類に分け（solids.py：S 構造 > E 外皮 > F 床 > D 戸 > P 間仕切り > I 家具 > X 外の付属）、
  重なったら優先の高いほうが低いほうを削る。各チャットは今までどおり部材を置けばよく、重なりはここで消える。
  1. 屋根の下面：屋根・光の筋のガラス・越屋根の蓋（10・20・10t・20t・50a・28）のいちばん下の面から
     垂木と断熱の層 150 を下げた面を「屋根の下面」とし（下から真上へ 250 の格子で測る）、
     戸・間仕切り・家具（D・P・I）はそれより上を削る（屋根を突き抜ける壁・木・遊具が無くなる）。
     戸・間仕切りは、部屋と床の板の外（外壁の中・外壁の外面・屋根の外）へはみ出した分も削る（外壁に間仕切りの端の筋が出ない）。
  2. 戸・間仕切り・家具・床（F・D・P・I）は、優先の高い部材（構造・外皮・床・戸）と重なる所を削る
     （壁の端が外壁の外面まで出て外から筋に見える所、梁を横切る壁の欠き込み、床に食い込む壁の足など）。
  3. 外の付属（X：下屋・外構・樋・越屋根のルーバーなど）は、外皮・構造と、建物の中（本館の床の外形・西館の外皮 WS
     を屋根の下面まで立ち上げた立体）を削る（下屋が建物に刺さらない）。
  4. 外壁（17・21）の片は、レイヤーごとに一つの立体に足し合わせる（片の継ぎ目の筋が外に出ない）。
  5. 構造と外皮どうし（S・E）は削らない（梁が屋根から出ている等は設計の誤りなので、干渉の一覧 clash.py で報告する）。
  屋根（10・20）で厚みの無い面は下へ 60（本館の屋根の板 60 とそろえる）、西館の 2 階の床（23、h3.17 の面）は上へ 80 の厚みを付けて閉じた立体にする。
"""
import sys, os, json, pickle, collections, numpy as np, trimesh, manifold3d as mf, rhino3dm as r
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from shapely import contains_xy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solids import load, RANK, to_manifold, to_trimesh, from_manifold, mesh_from_vf, RoofRaster

IN, OUT, WNEW = sys.argv[1:4]; LOGJ = sys.argv[4] if len(sys.argv) > 4 else None
RAFTER = 150.0        # 垂木と断熱の層（屋根の板の下）
ROOF_T = 60.0         # 厚みの無い屋根の面に付ける厚さ（下へ）
CELL = 250.0
m, LN, parts = load(IN)
P_OF = {p['i']: p for p in parts}
stats = collections.Counter(); log = []

# ---------------------------------------------------------------- 0. 西館の屋根の面に厚み
def thicken_down(t, d):
    V = np.asarray(t.vertices); F = np.asarray(t.faces); n = len(V)
    V2 = np.vstack([V, V - [0, 0, d]])
    F2 = [F, F[:, ::-1] + n]
    eb = trimesh.grouping.group_rows(t.edges_sorted, require_count=1)
    E = t.edges_sorted[eb]
    # 境界の辺を面の向きにそろえる（面の辺 a→b のまま）
    fe = {}
    for f in F:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])): fe[(min(a, b), max(a, b))] = (a, b)
    S = []
    for e in E:
        a, b = fe[(e[0], e[1])]
        S += [(b, a, a + n), (b, a + n, b + n)]
    return to_trimesh(V2, np.vstack(F2 + [np.array(S)]))
SHEETS = {'10_': ROOF_T, '20_': ROOF_T, '23_': -80.0}        # 厚みの無い面：屋根は下へ 60、西館の 2 階の床（h3.17 の面）は上へ 80（FL 3.25 まで）
for p in parts:
    d = next((v for k_, v in SHEETS.items() if p['layer'].startswith(k_)), None)
    if d is not None and p['M'] is None:
        try:
            t2 = thicken_down(p['tm'], d)
            if t2.volume < 0: t2.invert()
            M2 = to_manifold(t2)
        except Exception:
            M2 = None
        if M2 is not None:
            p['tm'] = t2; p['M'] = M2; p['bb'] = t2.bounds.copy(); p['new'] = True; stats['sheet_thicken'] += 1
        else:
            stats['sheet_thicken_fail'] += 1

# ---------------------------------------------------------------- 1. 屋根の下面の格子（世界座標 xy、mm）
RR = RoofRaster(parts, CELL)
xs, ys, GX, GY = RR.xs, RR.ys, RR.GX, RR.GY
Z = RR.Zbot - RAFTER
print('屋根の下面の格子', GX.shape, '覆われた', int(np.isfinite(Z).sum()))
def under_roof_solid(bb, ztop):
    """部材の bb の上にかかる「屋根の下面より上」の立体（格子から、bb より 2 ます広く）。無ければ None"""
    return RR.above(Z, bb)

# ---------------------------------------------------------------- 建物の中（外の付属を削る）
W = pickle.load(open(WNEW, 'rb'))
FL = [p for p in parts if p['layer'].split('_')[0] in ('12', '13')]
def proj(t):
    ps = [Polygon(tr[:, :2]).buffer(0) for tr in t.triangles if Polygon(tr[:, :2]).area > 1]
    return unary_union(ps)
HON = unary_union([proj(p['tm']) for p in FL]).buffer(50, join_style=2).buffer(-50, join_style=2)
INSIDE = unary_union([HON, W['WS']])
# 戸・間仕切りの居てよい所：部屋と床の板（本館・西館の床、外縁側・海峡、部屋の床 31〜59）と、西館の外皮 WS を外壁の厚さ 140 だけ内へ。
# ここから出た分（外壁の外面まで来た壁の端、外壁の開口や屋根の外へ出た間仕切り）は削る。
import re as _re
from solids import mesh_vf
ROOMS = []
for i_, o_ in enumerate(m.Objects):
    ln_ = LN[o_.Attributes.LayerIndex]
    if _re.match(r'^(3[1-6]|4[1-5]|43b|5[2-9])_', ln_) and isinstance(o_.Geometry, r.Mesh):
        V_, F_ = mesh_vf(o_.Geometry)
        if len(F_): ROOMS.append(unary_union([Polygon(V_[f][:, :2]).buffer(0) for f in F_ if Polygon(V_[f][:, :2]).area > 1]))
FLOORS = [p for p in parts if p['layer'].split('_')[0] in ('12', '13', '14', '15', '23')]
COVERED = unary_union(ROOMS + [proj(p['tm']) for p in FLOORS] + [W['WS'].buffer(-140, join_style=2)]).buffer(30, join_style=2)
def outside_solid(bb):
    """bb の箱から COVERED を除いた所（戸・間仕切りが建物の外へはみ出した分を削る）"""
    bx = box(bb[0][0] - 300, bb[0][1] - 300, bb[1][0] + 300, bb[1][1] + 300)
    reg = bx.difference(COVERED)
    if reg.is_empty or reg.area < 1e3: return None
    out = None
    for pg in getattr(reg, 'geoms', [reg]):
        if pg.geom_type != 'Polygon' or pg.area < 1e3: continue
        t = trimesh.creation.extrude_polygon(pg, bb[1][2] - bb[0][2] + 2000)
        t.apply_translation([0, 0, bb[0][2] - 1000])
        M = to_manifold(t)
        if M is not None: out = M if out is None else out + M
    return out
def inside_solid(bb):
    reg = INSIDE.intersection(box(bb[0][0] - 500, bb[0][1] - 500, bb[1][0] + 500, bb[1][1] + 500))
    if reg.is_empty or reg.area < 1e4: return None
    i0 = max(0, int((bb[0][0] - xs[0]) // CELL)); i1 = min(len(xs) - 1, int((bb[1][0] - xs[0]) // CELL) + 1)
    j0 = max(0, int((bb[0][1] - ys[0]) // CELL)); j1 = min(len(ys) - 1, int((bb[1][1] - ys[0]) // CELL) + 1)
    Zl = Z[i0:i1 + 1, j0:j1 + 1]
    zt = np.nanmax(Zl) + RAFTER if np.isfinite(Zl).any() else bb[1][2] + 100
    out = None
    for pg in getattr(reg, 'geoms', [reg]):
        if pg.geom_type != 'Polygon' or pg.area < 1e4: continue
        t = trimesh.creation.extrude_polygon(pg.simplify(5), zt + 3000)
        t.apply_translation([0, 0, -3000])
        M = to_manifold(t)
        if M is not None: out = M if out is None else out + M
    return out

# ---------------------------------------------------------------- 2・3. 削る
from rtree import index
idx = index.Index(properties=index.Property(dimension=3))
for k, p in enumerate(parts):
    b = p['bb']; idx.insert(k, (*b[0], *b[1]))
CUTTABLE = set('FDPIX')
for p in parts:
    k = p['klass']
    if k not in CUTTABLE or p['M'] is None: continue
    b = p['bb']; cutters = []; why = []
    for c in idx.intersection((*b[0], *b[1])):
        q = parts[c]
        if q is p or q['M'] is None: continue
        if RANK[q['klass']] >= RANK[k]: continue
        if k == 'F' and q['klass'] not in 'SE': continue
        if k == 'X' and q['klass'] not in 'SE': continue              # 外の付属を削るのは構造と外皮だけ
        cutters.append(q['M']); why.append(q['layer'][:3])
    if k in 'DPI':
        U = under_roof_solid(b, b[1][2])
        if U is not None: cutters.append(U); why.append('屋根の下面')
        O = outside_solid(b) if k in 'DP' and not p['layer'].startswith(('48', '27')) else None     # 窓のガラスは外壁の面にあってよい
        if O is not None: cutters.append(O); why.append('建物の外')
    if k == 'X' and not p['layer'].startswith(('29', '30', '50b', '50c')):
        Iin = inside_solid(b)
        if Iin is not None: cutters.append(Iin); why.append('建物の中')
    if not cutters: continue
    v0 = p['M'].volume()
    cut = cutters[0]
    for c in cutters[1:]: cut = cut + c
    R = p['M'] - cut
    v1 = R.volume()
    if v0 - v1 < 2e5: continue                                   # 0.2 L 未満の差は直さない（接するだけ）
    if v1 < 0.02 * v0 or R.is_empty():
        p['delete'] = True; stats['delete_' + k] += 1
    else:
        p['M'] = R; p['new'] = True; stats['cut_' + k] += 1
    log.append(dict(layer=p['layer'], name=p['name'], L=round((v0 - v1) / 1e6, 2), by=sorted(set(why)), deleted=bool(p.get('delete'))))

# ---------------------------------------------------------------- 4. 外壁の片をつなぐ
# 外壁（17・21）は高さ・開口ごとの片に分かれていて、片の継ぎ目が外から筋に見える。レイヤーごとに一つの立体に足し合わせる
# （同じ面に並ぶ片の継ぎ目が消える。片の厚さが違う所の段はそのまま残る）。
MERGE = {}
for p in parts:
    pre = p['layer'].split('_')[0]
    if pre in ('17', '21') and p['M'] is not None and not p.get('delete'):
        MERGE.setdefault(p['layer'], []).append(p)
for ln, L in MERGE.items():
    if len(L) < 2: continue
    U = mf.Manifold.batch_boolean([q['M'] for q in L], mf.OpType.Add)
    if U.is_empty() or U.status() != mf.Error.NoError: continue
    L[0]['M'] = U; L[0]['new'] = True
    for q in L[1:]: q['delete'] = True
    stats['merge_' + ln.split('_')[0]] = len(L)

# ---------------------------------------------------------------- 書き出し
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for i, o in enumerate(m.Objects):
    p = P_OF.get(i)
    if p is not None and p.get('delete'): continue
    if p is not None and p.get('new'):
        if isinstance(p['M'], mf.Manifold):
            V, F = from_manifold(p['M'])
        else:
            V, F = p['tm'].vertices, p['tm'].faces
        out.Objects.Add(mesh_from_vf(V, F), o.Attributes)
    else:
        out.Objects.Add(o.Geometry, o.Attributes)
out.Write(OUT, 8)
summ = collections.Counter()
for d in log: summ[(d['layer'][:14], tuple(d['by']))] += 1
print('clip_parts:', dict(stats))
for (ln, by), n in summ.most_common(25): print(f'  {n:4d} {ln} ← {"・".join(by)}')
if LOGJ: json.dump(dict(stats=stats, log=log), open(LOGJ, 'w'), ensure_ascii=False, indent=1)
