"""優先順位で削る段（設計監修、10-24。ユーザー：部材どうしの重なりをモデルの作り方で根本から解決する）
使い方: python3 clip_parts.py IN.3dm OUT.3dm WNEW.pkl [LOG.json]      （室内の戸の後、護岸と園庭の取り込みの前）

考え方（ArchiCAD の「優先度に基づく接続」・Revit の結合と同じ）：
  部材を種類に分け（solids.py：S 構造 > E 外皮 > F 床 > D 戸 > P 間仕切り > I 家具 > X 外の付属）、
  重なったら優先の高いほうが低いほうを削る。各チャットは今までどおり部材を置けばよく、重なりはここで消える。
  1. 屋根の下面：屋根・光の筋のガラス・越屋根の蓋（10・20・10t・20t・50a・28）のいちばん下の面を「屋根の下面」とし
     （下から真上へ 250 の格子で測る。屋根は梁の上端から約420の立体＝下面が垂木の下、10-26。厚みが 300 以下の所
     ＝まだ面の屋根やガラスの蓋だけの所は、前のとおり垂木と断熱の層 150 を下げる）、
     戸・間仕切り・家具（D・P・I）はそれより上を削る（屋根を突き抜ける壁・木・遊具が無くなる）。
     戸・間仕切りは、部屋と床の板の外（外壁の中・外壁の外面・屋根の外）へはみ出した分も削る（外壁に間仕切りの端の筋が出ない）。
  2. 戸・間仕切り・家具・床（F・D・P・I）は、優先の高い部材（構造・外皮・床・戸）と重なる所を削る
     （壁の端が外壁の外面まで出て外から筋に見える所、梁を横切る壁の欠き込み、床に食い込む壁の足など）。
  3. 外の付属（X：下屋・外構・樋・越屋根のルーバーなど）は、外皮・構造と、建物の中（本館の床の外形・西館の外皮 WS
     を屋根の下面まで立ち上げた立体）を削る（下屋が建物に刺さらない）。
  3b. 部屋の床の板（面積の板）は外壁の帯で切る（2階の板の縁が外壁に筋で見えていた。面積は壁芯なので変わらない）。
  3c. 外壁（17・21）は屋根の上面の 30 下で止める（屋根の板の厚みの中。上へ出た分と、屋根の面に重なる上端を削る）。
  3d. 屋根材型の太陽光の面（10p・20p）が屋根の面より下に潜っている所は、屋根の面＋20 に載せ直す。
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
# 読み込みで閉じた立体に直した部材（T 字の継ぎ目・厚みの無い片、solids.repair_solid）は、直した形で書き出す（10-25：Rhino で
# 梁や柱の一部が透けて見えた。閉じていない部材は削る側にも入らず、南の端の2階床梁の下の小壁が削られずに残っていた）
# 閉じているが面が内向きの部材も、外向きにして書き出す
for p in parts:
    if p.get('repaired') or p.get('inverted'): p['new'] = True
stats_rep = sum(1 for p in parts if p.get('repaired')); stats_inv = sum(1 for p in parts if p.get('inverted'))
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
# 屋根が厚みのある立体（梁の上端から約420、10-26 監修 20261026-1936）の所は、その下面がもう垂木の下＝屋根の下面。
# 厚みの無い面（下へ 60 を付けた西館の屋根など、まだ立体になっていない所）だけ、前のとおり垂木と断熱の層 150 を下げる
RAF = np.where(np.isfinite(RR.Zbot) & (RR.Ztop - RR.Zbot > 300), 0.0, RAFTER)
Z = RR.Zbot - RAF
print('屋根の下面：厚みのある屋根の格子', int((np.isfinite(RR.Zbot) & (RAF == 0)).sum()), '／ 150 下げる格子', int((np.isfinite(RR.Zbot) & (RAF > 0)).sum()))
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
# 外壁の帯（西館の外皮 WS の外面から 140 内側まで、本館の外壁 17 の上から見た形）は除く。部屋と床の板は外壁の外面まで伸びているので、
# これを除かないと外壁の中・外面に間仕切りの端が残る（10-24、ユーザーの指摘：外壁に筋）
from uv import uv as _uv
def _outer17(p):
    """本館の 17 のうち外皮の片だけ（西の外壁 v<0.5、南北の妻 u<0.5・u>56.5）。保育室などの西の壁の線（v1.6）も 17 にあるが室内の壁"""
    c = p['tm'].centroid; u_, v_ = _uv(c[0], c[1])
    return v_ < 0.5 or u_ < 0.5 or u_ > 56.5
# 西館の帯は外へ 1.0 まで（2階の床・部屋の板が外皮の外面より数 mm 外へ出ている所があるので、外面の外も含める）。本館の床・海峡（すき間）は除かない
_KAI = unary_union([proj(p['tm']) for p in parts if p['layer'].startswith('15_')] + [HON])
WALLBAND = unary_union([W['WS'].buffer(1000, join_style=2).difference(W['WS'].buffer(-140, join_style=2)).difference(_KAI)] +
                       [proj(p['tm']) for p in parts if p['layer'].startswith('17_') and _outer17(p)])
COVERED = COVERED.difference(WALLBAND)
# 部屋の床の板（面積の板、31〜59・41〜45）も外壁の帯で切る：外壁の外面まで来ていて、2階の板（h3.26）の縁が外壁に横の筋として見えていた。
# 面積は壁芯で数える（areas.py は板から壁を除いて壁の半分を足す）ので、板の端がどこでも数は変わらない
# 板の高さで外壁（西館 21・本館の外皮の 17）を水平に切った形で切る（壁の無い所＝すき間に開いた東の帯などは切らない）
_EXT = [p for p in parts if p['layer'].startswith('21_') or (p['layer'].startswith('17_') and _outer17(p))]
_WSEC = {}
def wall_section(z):
    k = round(z)
    if k not in _WSEC:
        gs = []
        for p in _EXT:
            b = p['bb']
            for dz in (-60, 60):
                if not (b[0][2] < z + dz < b[1][2]): continue
                try:
                    sec = p['tm'].section(plane_origin=[0, 0, z + dz], plane_normal=[0, 0, 1])
                    if sec is None: continue
                    P2, _ = sec.to_planar(to_2D=np.eye(4), check=False)
                    gs += [g.buffer(0) for g in P2.polygons_full]
                except Exception:
                    pass
        _WSEC[k] = unary_union(gs).buffer(2, join_style=2) if gs else Polygon()
    return _WSEC[k]
ROOM_FIX = {}
for i_, o_ in enumerate(m.Objects):
    ln_ = LN[o_.Attributes.LayerIndex]
    if not (_re.match(r'^(3[1-6]|4[1-5]|43b|5[2-9])_', ln_) and isinstance(o_.Geometry, r.Mesh)): continue
    V_, F_ = mesh_vf(o_.Geometry)
    if not len(F_) or np.ptp(V_[:, 2]) > 1: continue                  # 平らな板だけ
    pg = unary_union([Polygon(V_[f][:, :2]).buffer(0) for f in F_ if Polygon(V_[f][:, :2]).area > 1])
    z_ = float(V_[0, 2]); wb = wall_section(z_)
    if pg.intersection(wb).area < 1e3: continue
    ROOM_FIX[i_] = (pg.difference(wb), z_)
stats['room_plate_trim'] = len(ROOM_FIX)
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
    Zr = RR.Zbot[i0:i1 + 1, j0:j1 + 1]                     # 屋根の下面の上（垂木の層を足し戻した高さ＝覆いのいちばん下の面）
    zt = np.nanmax(Zr) if np.isfinite(Zr).any() else bb[1][2] + 100
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
        O = outside_solid(b) if k == 'P' and not p['layer'].startswith(('48', '27')) else None     # 窓のガラスは外壁の面に、外へ出る戸は外壁の開口にあってよい
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

# ---------------------------------------------------------------- 3c. 外壁の上端を屋根の上面で止める
# 外壁が屋根の上へ出ている所（西館の北西：外皮を外へ出したとき屋根は同じ面で延びて下がり、壁の上端はそのまま）を、
# 屋根の上面（屋根・光の筋・越屋根の蓋のいちばん上の面）の 30 下で切る（屋根の板の厚みの中で止める。上面ちょうどで切ると
# 壁の上端と屋根の面が同じ高さに重なり、表示がちらついてぎざぎざに見える）
for p in parts:
    if p['layer'].split('_')[0] not in ('17', '21') or p['M'] is None: continue
    U = RR.above(RR.Ztop - 30, p['bb'])
    if U is None: continue
    v0 = p['M'].volume(); R = p['M'] - U; v1 = R.volume()
    if v0 - v1 < 2e5 or R.is_empty(): continue
    p['M'] = R; p['new'] = True; stats['wall_top'] += 1
    log.append(dict(layer=p['layer'], name=p['name'], L=round((v0 - v1) / 1e6, 2), by=['屋根の上面'], deleted=False))

# ---------------------------------------------------------------- 3d. 屋根材型の太陽光を屋根の面に載せ直す
# 太陽光の面（10p・20p、屋根の面の 20 上の薄い面）が、屋根の面より下に潜っている所がある（西館の北西：屋根を外へ延ばした所で
# 屋根の面が上がり、太陽光の面は前の面のまま）。屋根が太陽光を突き抜けてぎざぎざに見えていた（10-24、ユーザーの指摘）。
# 面を 150 以下の三角形に細かく分け、頂点ごとに真上から屋根（10・20）の上面を測り、屋根の面＋20 より低い頂点を屋根の面＋20 に上げる
ROOF_TM = trimesh.util.concatenate([p['tm'] for p in parts if p['layer'].split('_')[0] in ('10', '20')])
_rri = trimesh.ray.ray_triangle.RayMeshIntersector(ROOF_TM)
PANEL_FIX = {}
for i_, o_ in enumerate(m.Objects):
    ln_ = LN[o_.Attributes.LayerIndex]
    if not (ln_.startswith(('10p_', '20p_')) and isinstance(o_.Geometry, r.Mesh)): continue
    V_, F_ = mesh_vf(o_.Geometry)
    if trimesh.Trimesh(V_, F_, process=True).is_watertight: continue            # 閉じた屋根材（西館の 20p は屋根の層のいちばん上、10-27夜）は動かさない
    V_, F_ = trimesh.remesh.subdivide_to_size(V_, F_, max_edge=150.0)[:2]     # 大きな三角形のあいだで曲がった屋根が抜けないよう細かく
    top = V_[:, 2].max() + 5000
    loc, rid, _ = _rri.intersects_location(np.c_[V_[:, :2], np.full(len(V_), top)], np.tile([0, 0, -1.0], (len(V_), 1)), multiple_hits=False)
    zr = np.full(len(V_), -1e9); zr[rid] = loc[:, 2]
    low = V_[:, 2] < zr + 15
    if low.any():
        V2 = V_.copy(); V2[low, 2] = zr[low] + 20
        PANEL_FIX[i_] = (V2, F_); stats['panel_lift'] += int(low.sum())

# ---------------------------------------------------------------- 4. 外壁の片をつなぐ
# 外壁（17・21）は高さ・開口ごとの片に分かれていて、片の継ぎ目が外から筋に見える。レイヤーごとに一つの立体に足し合わせる
# （同じ面に並ぶ片の継ぎ目が消える。片の厚さが違う所の段はそのまま残る）。
MERGE = {}
for p in parts:
    pre = p['layer'].split('_')[0]
    if pre in ('17', '21', '24') and p['M'] is not None and not p.get('delete'):     # 24：西館の間仕切りも一つに（壁ごとの立体は Rhino 版でつながりごとに分かれる、10-28 西館係・監修の項 2346）
        MERGE.setdefault(p['layer'], []).append(p)
for ln, L in MERGE.items():
    if len(L) < 2: continue
    U = mf.Manifold.batch_boolean([q['M'] for q in L], mf.OpType.Add)
    if U.is_empty() or U.status() != mf.Error.NoError: continue
    # 足した後に残る厚みの無い膜（片の面が 0.5 mm ほど食い違う継ぎ目にできる、体積ほぼ 0 の体）は捨てる
    # （監修 10-27 夜：西館の外壁に膜が 17、Rhino で継ぎ目が透けて見えた。本当の片は最小でも 1e6 mm³ 程度）
    bodies = U.decompose()
    keep = [b for b in bodies if b.volume() >= 1e5]
    if len(keep) < len(bodies):
        stats['merge_sliver_' + ln.split('_')[0]] += len(bodies) - len(keep)
        if not keep: continue
        U = mf.Manifold.compose(keep)
    # 4枚以上の面が集まる辺（片の継ぎ目の背中合わせの面）を数で出す：0 でなければ片の作り方を直す（担当の係）
    V_, F_ = from_manifold(U)
    tm_ = trimesh.Trimesh(V_, F_)
    _, cnt_ = np.unique(tm_.edges_sorted, axis=0, return_counts=True)
    stats['merge_nonmanifold_' + ln.split('_')[0]] = int((cnt_ > 2).sum())
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
    if i in PANEL_FIX:
        out.Objects.Add(mesh_from_vf(*PANEL_FIX[i]), o.Attributes); continue
    if i in ROOM_FIX:
        pg, z_ = ROOM_FIX[i]; Vs, Fs, off = [], [], 0
        for g_ in getattr(pg, 'geoms', [pg]):
            if g_.geom_type != 'Polygon' or g_.area < 1e3: continue
            v2, f2 = trimesh.creation.triangulate_polygon(g_, engine='earcut')
            Vs.append(np.c_[v2, np.full(len(v2), z_)]); Fs.append(f2 + off); off += len(v2)
        if Vs:
            out.Objects.Add(mesh_from_vf(np.vstack(Vs), np.vstack(Fs)), o.Attributes); continue
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
stats['repaired'] = stats_rep; stats['outward'] = stats_inv
print('clip_parts:', dict(stats))
for (ln, by), n in summ.most_common(25): print(f'  {n:4d} {ln} ← {"・".join(by)}')
if LOGJ: json.dump(dict(stats=stats, log=log), open(LOGJ, 'w'), ensure_ascii=False, indent=1)
