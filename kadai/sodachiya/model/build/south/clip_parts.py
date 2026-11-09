"""優先順位で削る段（設計監修、10-24。ユーザー：部材どうしの重なりをモデルの作り方で根本から解決する）
使い方: python3 clip_parts.py IN.3dm OUT.3dm WNEW.pkl [LOG.json]      （室内の戸の後、護岸と園庭の取り込みの前）

考え方（ArchiCAD の「優先度に基づく接続」・Revit の結合と同じ）：
  部材を種類に分け（solids.py：S 構造 > E 外皮 > F 床 > D 戸 > P 間仕切り > I 家具 > X 外の付属）、
  重なったら優先の高いほうが低いほうを削る。各チャットは今までどおり部材を置けばよく、重なりはここで消える。
  1. 屋根の下面：屋根・光の筋のガラス・越屋根の蓋（10・20・10t・20t・50a・28）のいちばん下の面を「屋根の下面」とし
     （下から真上へ 250 の格子で測る。屋根は梁の上端から約420の立体＝下面が垂木の下、10-26。厚みが 300 以下の所
     ＝まだ面の屋根やガラスの蓋だけの所は、前のとおり垂木と断熱の層 150 を下げる）、
     戸・間仕切り・家具（D・P・I）はそれより上を削る（屋根を突き抜ける壁・木・遊具が無くなる）。
     10-28：切る面はスパンごとの平面（本館は架構の線 u=3k のあいだ、西館は roofw の SPANS の平面のスパン）。格子が平面に載らない所
     （越屋根・軒・北西の双一次の面など）だけ格子で切る（上端が格子に沿って折れ、Rhino 版で三角形に割れていた）。
  1c. 板の物（間仕切り・壁・格子・家具：24・38・49・37・18）は欠き込まない（10-28）。上端は物ごとに一枚の平面で切る
     （上にある屋根の層・母屋・梁・2 階の床と屋根の下面の下に収まる、いちばん高い平面）。屋根の部材・梁では削らず、
     外壁・窓・戸・柱・間仕切り・建物の外に当たる所は、段 2 で直角の鉛直の平面で端を切り落とす（寸法で止める）。
     戸・間仕切りは、部屋と床の板の外（外壁の中・外壁の外面・屋根の外）へはみ出した分も削る（外壁に間仕切りの端の筋が出ない）。
  2. 戸・間仕切り・家具・床（F・D・P・I）は、優先の高い部材（構造・外皮・床・戸）と重なる所を削る
     （壁の端が外壁の外面まで出て外から筋に見える所、梁を横切る壁の欠き込み、床に食い込む壁の足など）。
  3. 外の付属（X：下屋・外構・樋・越屋根のルーバーなど）は、外皮・構造と、建物の中（本館の床の外形・西館の外皮 WS
     を屋根の下面まで立ち上げた立体）を削る（下屋が建物に刺さらない）。
  3b. 部屋の床の板（面積の板）は外壁の帯で切る（2階の板の縁が外壁に筋で見えていた。面積は壁芯なので変わらない）。
  3c. 外壁（17・21）は屋根の上面の 30 下で止める（屋根の板の厚みの中。上へ出た分と、屋根の面に重なる上端を削る。上面もスパンごとの平面）。
  3d. 屋根材型の太陽光の面（10p）が屋根の面より下に潜っている所は、屋根の面＋20 に載せ直す。閉じた立体（西館の 20p、屋根の層の
     いちばん上）は動かさない（10-28、項 20261028-1050-solid）。
  4. 外壁（17・21）の片は、レイヤーごとに一つの立体に足し合わせる（片の継ぎ目の筋が外に出ない）。間仕切りは壁ごとの立体のまま。
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
# 1b. スパンごとの平面で切る（監修 10-28、ユーザー：架構のほかはすべて平らな板。項 20261028-0043-honkan・1244-honkan）
# 格子の面で上端を切ると、上端が格子に沿って折れ、Rhino 版で三角形の面に割れていた（38 の u12・18・33…、17・55）。
# 屋根の面はスパンごとの平面（本館：fix_details の _plane／zpl、架構の線 u=3k のあいだの弦の上。西館：roofw の SPANS の 'plane'）なので、
# 下面・上面もスパンごとに「その平面＋一定の差」になる（差は格子からスパンごとにいちばん多い値で求める）。
# 格子の点がその平面に載る所（と、架構の線の近く ±0.45 で平面より上＝梁の上・光の筋の所）は、スパンの多角形（架構の線で区切る）×
# 平面より上の柱で切る（上端は平らな面、となりのスパンとは架構の線で交わる）。平面に載らない所（越屋根・軒・北西の双一次の面・
# 光の筋のガラスなど）だけ、前のとおり格子で切る（平面の所との境は 2 ます重ねる）。
import math as _m
from uv import xy as _xy, CX as _CX, CY as _CY, RW as _RW, TH_S as _THS
import roofw as _roofw
def _uv_arr(X, Y):
    th = np.mod(np.arctan2(Y - _CY, X - _CX), 2 * np.pi)
    return (_THS - th) * _RW / 1000.0, (_RW - np.hypot(X - _CX, Y - _CY)) / 1000.0
GU, GV = _uv_arr(GX, GY)
V_SPLIT = -0.62                                   # これより西（v が小さい）は西館
def _hon_coef(k):
    """本館のスパン k（u 3k〜3k+3）の屋根の面：z = a·x + b·y + c（fix_details の _plane・zpl と同じ）"""
    A_ = _xy(3.0 * k, 0.0); B_ = _xy(3.0 * (k + 1), 0.0); c_ = (B_ - A_) / np.linalg.norm(B_ - A_)
    h_ = np.array([c_[1], -c_[0]])
    if np.dot(h_, _xy(3.0 * k, 1.0) - A_) < 0: h_ = -h_
    return (-h_[0] / 12.0, -h_[1] / 12.0, 4150.0 + (A_[0] * h_[0] + A_[1] * h_[1]) / 12.0)
_RWS = _roofw.make(pickle.load(open(WNEW, 'rb'))['WN'])
_WPL = [(ua, ub, cf) for ua, ub, kind, cf in _RWS['SPANS'] if kind == 'plane']
def _wes_coef(j):
    ua, ub, (px, py, c0, c1, c2) = _WPL[j]
    return (c1, c2, c0 - c1 * px - c2 * py)
# スパンの番号：('h', k) 本館 k=0〜18、('w', j) 西館の平面のスパン j=0〜6（u21〜42、南のけらば u<21 は j=0 を延ばす）
SPAN_U = {}
for k in range(19): SPAN_U[('h', k)] = (3.0 * k, 3.0 * (k + 1), _hon_coef(k))
for j, (ua, ub, cf) in enumerate(_WPL): SPAN_U[('w', j)] = (ua if j else -30.0, ub, _wes_coef(j))
W_U1 = _WPL[-1][1]                                # 42：これより北の西館は双一次（平面が無い）
def _span_of(u, v):
    if v < V_SPLIT:
        if u > W_U1: return None
        return ('w', int(min(len(_WPL) - 1, max(0, (u - 21.0) // 3.0))))
    return ('h', int(min(18, max(0, _m.floor(u / 3.0)))))
KEYS = list(SPAN_U); KID = {k: n for n, k in enumerate(KEYS)}
SPAN_ID = np.full(GX.shape, -1, dtype=int)
for i_ in range(GX.shape[0]):
    for j_ in range(GX.shape[1]):
        k_ = _span_of(GU[i_, j_], GV[i_, j_])
        if k_ is not None: SPAN_ID[i_, j_] = KID[k_]
def _pz(key, X, Y):
    a, b, c = SPAN_U[key][2]; return a * X + b * Y + c
PLANE_Z = np.full(GX.shape, np.nan)
for key in SPAN_U:
    msk = SPAN_ID == KID[key]
    PLANE_Z[msk] = _pz(key, GX[msk], GY[msk])
# 架構の線（2 枚の梁と光の筋）の近く。建物の中（本館の床・西館の外皮）だけ（軒の下は軒の下面が平面より高いので格子で）
_BLD = unary_union([pickle.load(open(WNEW, 'rb'))['WS']] + [Polygon(tr[:, :2]).buffer(0) for p_ in parts if p_['layer'].split('_')[0] in ('12', '13')
                                                         for tr in p_['tm'].triangles if Polygon(tr[:, :2]).area > 1]).buffer(-200, join_style=2)
FRAME_NEAR = (np.abs(GU - 3.0 * np.round(GU / 3.0)) < 0.45) & contains_xy(_BLD, GX, GY)
def _span_poly(key):
    u0, u1, _ = SPAN_U[key]
    v0, v1 = (-40.0, V_SPLIT) if key[0] == 'w' else (V_SPLIT, 20.0)
    if key[0] == 'w': u0 = max(u0, -3.0)
    us = np.linspace(u0, u1, 13)
    ring = [_xy(u, v0) for u in us] + [_xy(u, v1) for u in us[::-1]]
    return Polygon(ring).buffer(0)
SPAN_POLY = {k: _span_poly(k) for k in SPAN_U}
class PlaneCut:
    """格子の面 Zg（屋根の下面・上面）を、スパンごとの平面＋差で表す。above(bb) は bb の上の「面より上」の立体"""
    def __init__(self, Zg, name, frame=True):
        self.Zg = Zg; self.D = {}
        ok = np.isfinite(Zg) & np.isfinite(PLANE_Z) & ~FRAME_NEAR
        for key in SPAN_U:
            msk = ok & (SPAN_ID == KID[key])
            if msk.sum() < 8: continue
            d = np.round(Zg[msk] - PLANE_Z[msk], 0)
            vals, cnt = np.unique(d, return_counts=True)
            if cnt.max() < 8: continue
            d0 = vals[cnt.argmax()]; sel = np.abs(Zg[msk] - PLANE_Z[msk] - d0) < 2
            self.D[key] = float(np.median((Zg[msk] - PLANE_Z[msk])[sel]))
        self.DZ = np.full(Zg.shape, np.nan)
        for key, d in self.D.items():
            msk = SPAN_ID == KID[key]; self.DZ[msk] = PLANE_Z[msk] + d
        fin = np.isfinite(Zg) & np.isfinite(self.DZ)
        self.ON = fin & ((np.abs(Zg - self.DZ) < 3) | (frame & FRAME_NEAR & (Zg > self.DZ - 3)))
        self.RASTER = np.isfinite(Zg) & ~self.ON
        from scipy.ndimage import binary_dilation
        near = binary_dilation(self.RASTER, structure=np.ones((3, 3), bool), iterations=2)
        self.Zr = np.where(self.RASTER | (near & self.ON), Zg, np.nan)       # 格子で切る所（平面の所と 2 ます重ねる。斜めのとなりも）
        print(f'{name}：スパンの平面 {len(self.D)}（差 本館 {[round(v) for k, v in sorted(self.D.items()) if k[0] == "h"][:3]}…、'
              f'西館 {[round(v) for k, v in sorted(self.D.items()) if k[0] == "w"][:3]}…）、平面で切る格子 {int(self.ON.sum())}／格子で切る {int(self.RASTER.sum())}')
    def above(self, bb, pad=2):
        xs_, ys_, c = xs, ys, CELL
        i0 = max(0, int((bb[0][0] - xs_[0]) // c) - pad); i1 = min(len(xs_) - 1, int((bb[1][0] - xs_[0]) // c) + pad + 1)
        j0 = max(0, int((bb[0][1] - ys_[0]) // c) - pad); j1 = min(len(ys_) - 1, int((bb[1][1] - ys_[0]) // c) + pad + 1)
        if i1 - i0 < 1 or j1 - j0 < 1: return None
        ON = self.ON[i0:i1 + 1, j0:j1 + 1]; out = None; ztop = bb[1][2] + 1000
        if ON.any():
            win = box(bb[0][0] - 400, bb[0][1] - 400, bb[1][0] + 400, bb[1][1] + 400)
            h = c / 2 + 0.5
            for kid in set(SPAN_ID[i0:i1 + 1, j0:j1 + 1][ON].tolist()):
                key = KEYS[kid]; m_ = ON & (SPAN_ID[i0:i1 + 1, j0:j1 + 1] == kid)
                if key not in self.D or not m_.any(): continue
                cells = unary_union([box(GX[i0 + a, j0 + b] - h, GY[i0 + a, j0 + b] - h, GX[i0 + a, j0 + b] + h, GY[i0 + a, j0 + b] + h)
                                     for a, b in zip(*np.where(m_))])
                reg = cells.intersection(SPAN_POLY[key]).intersection(win)
                a, b_, cc = SPAN_U[key][2]; d = self.D[key]
                for pg in getattr(reg, 'geoms', [reg]):
                    if pg.geom_type != 'Polygon' or pg.area < 1e3: continue
                    pg = pg.simplify(0.1)
                    zc = [a * x + b_ * y + cc + d for x, y in pg.exterior.coords]
                    if min(zc) >= bb[1][2]: continue
                    top = max(ztop, max(zc) + 1000)
                    t = trimesh.creation.extrude_polygon(pg, 1.0)
                    V_ = np.array(t.vertices); lo = V_[:, 2] < 0.5
                    V_[lo, 2] = a * V_[lo, 0] + b_ * V_[lo, 1] + cc + d; V_[~lo, 2] = top
                    M = to_manifold(trimesh.Trimesh(V_, t.faces, process=False))
                    if M is not None: out = M if out is None else out + M
        Zl = self.Zr[i0:i1 + 1, j0:j1 + 1]
        if np.isfinite(Zl).any():
            Mr = RR.above(self.Zr, bb)
            if Mr is not None: out = Mr if out is None else out + Mr
        return out
PC_BOT = PlaneCut(Z, '屋根の下面')
PC_TOP = PlaneCut(RR.Ztop - 30, '屋根の上面−30', frame=False)     # 上面は平面に載る所だけ（光の筋の立ち上がりで壁を下げない）
def under_roof_solid(bb, ztop):
    """部材の bb の上にかかる「屋根の下面より上」の立体（スパンごとの平面、平面の無い所は格子）。無ければ None"""
    return PC_BOT.above(bb)

# ---------------------------------------------------------------- 建物の中（外の付属を削る）
W = pickle.load(open(WNEW, 'rb'))
FL = [p for p in parts if p['layer'].split('_')[0] in ('12', '13')]
def proj(t):
    ps = [Polygon(tr[:, :2]).buffer(0) for tr in t.triangles if Polygon(tr[:, :2]).area > 1]
    return unary_union(ps)
HON = unary_union([proj(p['tm']) for p in FL]).buffer(50, join_style=2).buffer(-50, join_style=2)
INSIDE = unary_union([HON, W['WS']])
# 戸・間仕切りの居てよい所：部屋と床の板（本館・西館の床、外縁側・あまのがわ、部屋の床 31〜59）と、西館の外皮 WS を外壁の厚さ 140 だけ内へ。
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
# 西館の帯は外へ 1.0 まで（2階の床・部屋の板が外皮の外面より数 mm 外へ出ている所があるので、外面の外も含める）。本館の床・あまのがわ（すき間）は除かない
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

# ---------------------------------------------------------------- 1c. 板の物は欠き込まず、上端を一枚の平面で切る（監修 10-28）
# ユーザー：架構のほかはすべて平らな板（箱か、まっすぐな角柱。屋根の下の壁は上端の斜めの面が一枚だけ）。
# 前は間仕切り・壁・格子・家具を、母屋（@455）・垂木・合板・梁・丸い柱・光の筋で真上から格子で削っていて、上端が櫛の歯や
# 弧の欠き込みになり、北の双一次の屋根の下では 250 の格子で上端が三角形に割れていた（西館の 24 は 12 → 1514 枚）。
# 板の物（PLATE）は、屋根の部材・架構・光の筋では削らない。代わりに：
#   (1) 上端：物の下から真上へ 20 おきに測った「上にある部材（屋根の層・母屋・垂木・梁・桁・2 階の床）のいちばん下の面」と
#       「屋根の下面（段 1 のスパンの平面・格子）」の下に収まる、いちばん高い一枚の平面で切る（今の上端より上げない）。
#       梁や母屋に当たる物は、欠き込まずに上端の平面ごと下げる。
#   (2) 段 2 で、外壁・窓・戸・柱・間仕切り・建物の外に当たる物は、欠き込まずに物の長さか幅の向きに直角な鉛直の平面で端を切り
#       落とす（寸法で止める、end_cut）。柱が途中に当たるときは柱の幅の 2 枚の平面で二つに分ける。床（F）は前のとおり削る。
#   (3) 段 4 で間仕切り（24）を一つの立体に足さない（壁ごとに一つの立体）。
PLATE = ('24', '38', '49', '37', '18')
TOPOBS = ('10', '20', '10r', '20r', '10t', '20t', '28', '50a', '10v', '20v', '10b', '20b', '10s', '11b', '11c', '22b', '22c', '22d', '23')
def is_plate(p): return p['layer'].split('_')[0] in PLATE
_OBS = [p for p in parts if p['layer'].split('_')[0] in TOPOBS]
OBS_TM = trimesh.util.concatenate([p['tm'] for p in _OBS])
_ori = trimesh.ray.ray_triangle.RayMeshIntersector(OBS_TM)
from scipy.optimize import linprog
def _roof_limit(X, Y):
    """屋根の下面（段 1 と同じ面：スパンの平面の所は平面＋差、ほかは格子を双一次で）"""
    fi = (X - xs[0]) / CELL; fj = (Y - ys[0]) / CELL
    i0 = np.clip(np.floor(fi).astype(int), 0, len(xs) - 2); j0 = np.clip(np.floor(fj).astype(int), 0, len(ys) - 2)
    a = np.clip(fi - i0, 0, 1); b = np.clip(fj - j0, 0, 1)
    out = np.full(len(X), np.inf)
    for G in (np.where(PC_BOT.ON, PC_BOT.DZ, np.nan), PC_BOT.Zr):
        q = [G[i0, j0], G[i0 + 1, j0], G[i0, j0 + 1], G[i0 + 1, j0 + 1]]
        Q = np.array(q); fin = np.isfinite(Q)
        z = (1 - a) * (1 - b) * q[0] + a * (1 - b) * q[1] + (1 - a) * b * q[2] + a * b * q[3]
        z = np.where(fin.all(0), z, np.where(fin.any(0), np.nanmin(np.where(fin, Q, np.inf), axis=0), np.inf))
        out = np.minimum(out, z)
    return out
def _axes(t):
    P = t.vertices[:, :2]; c = P.mean(0)
    w, v = np.linalg.eigh(np.cov((P - c).T)); ax = v[:, 1]; ax = ax / np.linalg.norm(ax)
    return c, ax, np.array([-ax[1], ax[0]])
def _halfspace(bb, cf, c, ax, pr, above=True):
    """平面 z = cf0 + cf1·s + cf2·w（s・w は c からの ax・pr の向き）より上（above）の立体"""
    pg = box(bb[0][0] - 60, bb[0][1] - 60, bb[1][0] + 60, bb[1][1] + 60)
    tt = trimesh.creation.extrude_polygon(pg, 1.0); V_ = np.array(tt.vertices); lo = V_[:, 2] < 0.5
    d = V_[:, :2] - c; zp = cf[0] + cf[1] * (d @ ax) + cf[2] * (d @ pr)
    V_[lo, 2] = zp[lo]; V_[~lo, 2] = max(bb[1][2], zp.max()) + 1000
    return to_manifold(trimesh.Trimesh(V_, tt.faces, process=False))
def _slab(bb, c, ax, s0, s1):
    """物の長さの向き ax に直角な 2 枚の平面 s0〜s1 のあいだ（柱の幅）の立体"""
    pr = np.array([-ax[1], ax[0]]); R = 1e5
    ring = [c + ax * s0 - pr * R, c + ax * s1 - pr * R, c + ax * s1 + pr * R, c + ax * s0 + pr * R]
    t = trimesh.creation.extrude_polygon(Polygon(ring), bb[1][2] - bb[0][2] + 2000); t.apply_translation([0, 0, bb[0][2] - 1000])
    return to_manifold(t)
def plate_top(Mb):
    """一つの体 Mb の上端を一枚の平面に。→ (新しい体, 下げた最大 mm) か None（変えない）"""
    V_, F_ = from_manifold(Mb); t = trimesh.Trimesh(V_, F_, process=False)
    c, ax, pr = _axes(t); d = t.vertices[:, :2] - c
    s = d @ ax; w = d @ pr
    S = np.arange(s.min() + 2, s.max() - 1, 20.0)
    if len(S) < 2: S = np.array([s.min() + 1, s.max() - 1])
    wn = max(2, int((w.max() - w.min()) / 50) + 1)
    Wd = np.linspace(w.min() + 2, w.max() - 2, wn) if w.max() - w.min() > 6 else np.array([(w.min() + w.max()) / 2])
    SS, WW = np.meshgrid(S, Wd); SS = SS.ravel(); WW = WW.ravel()
    XY = c + np.outer(SS, ax) + np.outer(WW, pr)
    z0 = t.bounds[0][2] - 10
    loc, rid, fid = trimesh.ray.ray_triangle.RayMeshIntersector(t).intersects_location(
        np.c_[XY, np.full(len(XY), z0)], np.tile([0, 0, 1.0], (len(XY), 1)), multiple_hits=True)
    if not len(loc): return None
    zb = np.full(len(XY), np.inf); zt = np.full(len(XY), -np.inf)
    np.minimum.at(zb, rid, loc[:, 2]); np.maximum.at(zt, rid, loc[:, 2])
    ok = np.isfinite(zb) & (zt - zb > 5)
    if ok.sum() < 3: return None
    XY, SS, WW, zb, zt = XY[ok], SS[ok], WW[ok], zb[ok], zt[ok]
    # 上にある部材のいちばん下の面（下から入る面だけ。物の足もとの 300 より上）
    lim = np.full(len(XY), np.inf)
    lo_, ri_, fi_ = _ori.intersects_location(np.c_[XY, zb + 1.0], np.tile([0, 0, 1.0], (len(XY), 1)), multiple_hits=True)
    if len(lo_):
        ent = (OBS_TM.face_normals[fi_][:, 2] < -1e-3) & (lo_[:, 2] > zb[ri_] + 300)
        np.minimum.at(lim, ri_[ent], lo_[ent, 2])
    lim = np.minimum(lim, _roof_limit(XY[:, 0], XY[:, 1])) - 2.0
    cap = np.minimum(zt, np.where(lim > zb + 300, lim, zt))   # 足もとのすぐ上の物（屋根の下面の格子の外れ）では下げない
    A_ = np.c_[np.ones(len(SS)), SS, WW]; cf, *_ = np.linalg.lstsq(A_, zt, rcond=None)
    stepped = np.ptp(zt - A_ @ cf) > 15                       # わざと一枚でない上端（窓の脇だけ高い壁・段のある家具など）
    if np.all(cap >= zt - 0.5):
        # 当たらない：上端がもう一枚の平面か、段のある形なら変えない
        if stepped or np.ptp(zt - A_ @ cf) < 0.6: return None
    if stepped:
        # 段のある物は、当たる所の上の部材の下に収まる平面で高い所だけを切る（低い所は平面より下なのでそのまま）
        cap = np.where(lim > zb + 300, np.minimum(lim, zt.max()), zt.max())
    A_ub = np.c_[np.ones(len(SS)), SS, WW]
    thin = np.ptp(WW) < 0.34 * np.ptp(SS)                                         # 細長い物（壁・格子）は幅の向きに傾けない（上端は長さに沿う一枚の斜めの面）
    res = linprog(c=-A_ub.sum(0), A_ub=A_ub, b_ub=cap, bounds=[(None, None), (-1.0, 1.0), (0.0, 0.0) if thin else (-1.0, 1.0)], method='highs')
    if not res.success: return None
    cf = res.x.copy()
    cf[0] -= 0.5 + 4.0 * (abs(cf[1]) + abs(cf[2]))       # 測った点は端から 2 mm 内側：端でも今の上端より下に（上端の細い残りの面を作らない）
    if np.min(A_ub @ cf - zb) < 100: return None                                 # 板がつぶれる：変えない
    H = _halfspace(t.bounds, cf, c, ax, pr)
    if H is None: return None
    R = Mb - H
    if R.is_empty(): return None
    return R, float(np.max(zt - A_ub @ cf))
def end_cut(M, C, split=False):
    """板の物 M を、当たる物 C の所で「寸法で止める」：物の長さか幅の向きに直角な鉛直の平面で、当たる側の端を切り落とす
    （欠き込まない）。当たる所が途中なら、split のときだけ 2 枚の平面のあいだを落として二つに分ける（柱）。
    → (新しい M, 落とした体積) か None（当たらない・平面で止められない＝前のとおりの削り方に任せる）"""
    X = M ^ C
    if X.is_empty() or X.volume() < 2e5: return M, 0.0
    V_, F_ = from_manifold(M); t = trimesh.Trimesh(V_, F_, process=False); c, ax, pr = _axes(t)
    Vx, Fx = from_manifold(X); bb = t.bounds; v0 = M.volume(); best = None
    # 向き：物の長さ・幅の向きと、当たる所の鉛直の面の向き（斜めに当たる外壁は、その外壁の面で止める）
    tx = trimesh.Trimesh(Vx, Fx, process=False); nx_ = tx.face_normals; ar = tx.area_faces
    dirs = [ax, pr]
    for f_ in np.argsort(-ar):
        if ar[f_] < 1e3 or len(dirs) >= 5: break
        n2 = nx_[f_][:2]
        if abs(nx_[f_][2]) > 0.05 or np.linalg.norm(n2) < 0.9: continue
        n2 = n2 / np.linalg.norm(n2)
        if all(abs(n2 @ d_) < 0.99999 for d_ in dirs): dirs.append(n2)
    for k_, d in enumerate(dirs):
        a_ = (V_[:, :2] - c) @ d; x_ = (Vx[:, :2] - c) @ d
        a0, a1, x0, x1 = a_.min(), a_.max(), x_.min(), x_.max()
        cands = []
        if x1 >= a1 - 2: cands.append((x0 - 0.5, a1 + 1000))
        if x0 <= a0 + 2: cands.append((a0 - 1000, x1 + 0.5))
        if not cands and split and k_ == 0: cands.append((x0 - 0.5, x1 + 0.5))
        for s0, s1 in cands:
            H = _slab(bb, c, d, s0, s1)
            if H is None: continue
            R = M - H
            if R.is_empty(): continue
            if (R ^ C).volume() > 2e5: continue                                # まだ当たる（斜めに当たる物など）
            if k_ >= 2 and v0 - R.volume() > 0.1 * v0: continue               # 斜めの面で止めるのは、端を少し落とすときだけ
            # 物の長さ・幅の向き（直角の端、箱のまま）を、落とす量が 3% 多いまでは先に選ぶ
            key = R.volume() + (0.03 * v0 if k_ < 2 else 0.0)
            if best is None or key > best[2]: best = (R, v0 - R.volume(), key)
    if best is None or best[1] > 0.6 * v0: return None
    return best[0], best[1]
def floor_cut(M, C):
    """板の物 M の足もとが床 C に入る所は、重なりの上端（床の上面）の水平な一枚の平面で足もとを切る（欠き込まない、監修 10-29：
    本館の 38 の u2.7 v1.68 の腰壁・37 の u6.0 の棚の板の足が床 12 の形に沿って段に欠かれ、箱でなくなっていた）。
    → 新しい M（当たらなければ M のまま）か None（重なりの外まで大きく落ちる・まだ当たる＝前のとおり削る）"""
    X = M ^ C
    if X.is_empty() or X.volume() < 2e5: return M
    b = M.bounding_box(); zf = X.bounding_box()[5]
    if zf >= b[5] - 1: return None
    H = mf.Manifold.cube([b[3] - b[0] + 200, b[4] - b[1] + 200, zf - b[2] + 100]).translate([b[0] - 100, b[1] - 100, b[2] - 100])
    R = M - H
    if R.is_empty(): return None
    if (M.volume() - R.volume()) - X.volume() > max(0.25 * X.volume(), 2e5): return None
    if (R ^ C).volume() > 2e5: return None
    return R
from rtree import index
idx = index.Index(properties=index.Property(dimension=3))
for k, p in enumerate(parts):
    b = p['bb']; idx.insert(k, (*b[0], *b[1]))
for p in parts:
    if not is_plate(p) or p['M'] is None: continue
    try:
        bodies = p['M'].decompose(); new = []; ch = False; mx = 0.0
        for Mb in bodies:
            rr = plate_top(Mb)
            if rr is None: new.append(Mb)
            else: new.append(rr[0]); ch = True; mx = max(mx, rr[1])
    except Exception as e:
        stats['plate_top_fail'] += 1; continue
    if ch:
        p['M'] = new[0] if len(new) == 1 else mf.Manifold.compose(new); p['new'] = True
        stats['plate_top'] += 1; stats['plate_top_max_mm'] = max(stats['plate_top_max_mm'], round(mx))

# ---------------------------------------------------------------- 2・3. 削る
CUTTABLE = set('FDPIX')
for p in parts:
    k = p['klass']
    if k not in CUTTABLE or p['M'] is None: continue
    if p['layer'].startswith('20p_'): continue                       # 10-29 西館係：西館の太陽光 20p は屋根材 20 と同じ板（削らない。削ると網目版で閉じない片になっていた）
    b = p['bb']; cutters = []; why = []
    for c in idx.intersection((*b[0], *b[1])):
        q = parts[c]
        if q is p or q['M'] is None: continue
        if RANK[q['klass']] >= RANK[k]: continue
        if k == 'F' and q['klass'] not in 'SE': continue
        # 床は梁・桁に載る：西館の床梁・梁・桁（22b・22c・22d）では欠き込まない（監修 10-29：2 階の床 23 を 22c で削ると、梁の側面に沿う
        # 膜 40 と三角形 約5,600 の網目になり、Rhino 版で閉じた立体に戻せなかった）。床の下面 3.17 と梁の上端 3.20 の重なり 30 は、床が梁に載る
        # 取り合いとして干渉の一覧（clash.py）で数だけにする（床の下面を上げると、西館の 1 階の壁の上端・階段の箱の開口 3170 とずれる）
        if k == 'F' and q['layer'].split('_')[0] in ('22b', '22c', '22d'): continue
        if k == 'X' and q['klass'] not in 'SE': continue              # 外の付属を削るのは構造と外皮だけ
        if is_plate(p) and q['layer'].split('_')[0] in TOPOBS: continue     # 板の物は屋根の部材・梁で削らない（段 1c の上端の平面で止めた）
        cutters.append(q['M']); why.append(q['layer'][:3])
    if k in 'DPI':
        U = under_roof_solid(b, b[1][2]) if not is_plate(p) else None
        if U is not None: cutters.append(U); why.append('屋根の下面')
        O = outside_solid(b) if k == 'P' and not p['layer'].startswith(('48', '27')) else None     # 窓のガラスは外壁の面に、外へ出る戸は外壁の開口にあってよい
        if O is not None: cutters.append(O); why.append('建物の外')
    if k == 'X' and not p['layer'].startswith(('29', '30', '50b', '50c', '20p', '10p')):     # 10-29 西館係：閉じた 20p（屋根の上）は建物の中で削らない（中の立体の上端が一番高い所の平らな面で、軒の帯のほかが消えていた）。10-29 監修：本館の 10p も同じ（本館係の依頼）
        Iin = inside_solid(b)
        if Iin is not None: cutters.append(Iin); why.append('建物の中')
    if not cutters: continue
    v0 = p['M'].volume()
    R = p['M']
    if is_plate(p):
        # 板の物：床（F）は前のとおり削る（床の上面は水平）。ほかの当たる物（外壁・窓・戸・柱・間仕切り・建物の外）は寸法で止める
        rest = []; rest_w = []; end_w = []
        todo = [(C, w_) for C, w_ in zip(cutters, why) if C is not None]
        for C, w_ in todo:
            if w_[:2] in ('12', '13', '14', '15', '23'):
                try: R2 = floor_cut(R, C)
                except Exception: R2 = None
                if R2 is None: rest.append(C); rest_w.append(w_)
                elif R2 is not R: R = R2; end_w.append(w_); stats['plate_floor'] += 1
        todo = [(C, w_) for C, w_ in todo if w_[:2] not in ('12', '13', '14', '15', '23')]
        for _pass in range(3):                     # 一つを止めると、次の物が端に当たるようになることがある（外へ出た端を切った後の外壁など）
            left = []
            for C, w_ in todo:
                try: rr = end_cut(R, C, split=w_ in ('11a', '22a'))
                except Exception: rr = None
                if rr is None: left.append((C, w_))
                elif rr[1] > 0: R = rr[0]; end_w.append(w_); stats['plate_end'] += 1
            if len(left) == len(todo): break
            todo = left
        for C, w_ in todo:
            rest.append(C); rest_w.append(w_); stats['plate_bool'] += 1; stats['plate_bool_' + p['layer'][:2] + '←' + w_[:3]] += 1
        cutters = rest
    if cutters:
        cut = cutters[0]
        for c in cutters[1:]: cut = cut + c
        R = R - cut
    # 削った後に残る厚みの無い片（体積 1e5 mm³ 未満の体：当たる物の面に沿って並ぶ膜・角の細い片）は捨てる（監修 10-29：西館の 2 階の床 23 が
    # 2 階の床梁 22c の面に沿う膜 40 個と一つの網目になり、Rhino 版で閉じた立体に戻せなかった。38 の u41.98 v1.6 の細い片も）。
    # もとから小さな体を持つ物（金物など）は触らない
    if not R.is_empty():
        bodies = R.decompose()
        small = [b_ for b_ in bodies if b_.volume() < 1e5]
        if small and len(small) < len(bodies) and not any(b_.volume() < 1e5 for b_ in p['M'].decompose()):
            R = mf.Manifold.compose([b_ for b_ in bodies if b_.volume() >= 1e5]); stats['cut_sliver_' + p['layer'].split('_')[0]] += len(small)
    v1 = R.volume()
    if v0 - v1 < 2e5: continue                                   # 0.2 L 未満の差は直さない（接するだけ）
    if v1 < 0.02 * v0 or R.is_empty():
        p['delete'] = True; stats['delete_' + k] += 1
    else:
        p['M'] = R; p['new'] = True; stats['cut_' + k] += 1
    _c = (b[0] + b[1]) / 2; _u, _v = _uv(_c[0], _c[1])
    log.append(dict(layer=p['layer'], name=p['name'], L=round((v0 - v1) / 1e6, 2), by=sorted(set(why)), deleted=bool(p.get('delete')),
                    u=round(_u, 2), v=round(_v, 2), z=round(_c[2] / 1000, 2), end=end_w if is_plate(p) else None, bool=rest_w if is_plate(p) else None))

# ---------------------------------------------------------------- 3c. 外壁の上端を屋根の上面で止める
# 外壁が屋根の上へ出ている所（西館の北西：外皮を外へ出したとき屋根は同じ面で延びて下がり、壁の上端はそのまま）を、
# 屋根の上面（屋根・光の筋・越屋根の蓋のいちばん上の面）の 30 下で切る（屋根の板の厚みの中で止める。上面ちょうどで切ると
# 壁の上端と屋根の面が同じ高さに重なり、表示がちらついてぎざぎざに見える）
for p in parts:
    if p['layer'].split('_')[0] not in ('17', '21') or p['M'] is None: continue
    U = PC_TOP.above(p['bb'])
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
    # 閉じた屋根材（西館の 20p は屋根の層のいちばん上の閉じた立体、10-27夜）は動かさない。片どうしが触れ合って一つの網目では
    # is_watertight にならない（4 面が集まる辺）ので、「開いた辺（1 面だけの辺）が無い」で閉じたとみる（項 20261028-1050-solid）
    if ln_.startswith('20p_'): continue
    _t = trimesh.Trimesh(V_, F_, process=True)
    if len(trimesh.grouping.group_rows(_t.edges_sorted, require_count=1)) == 0: continue
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
    if pre in ('17', '21') and p['M'] is not None and not p.get('delete'):     # 間仕切り（24）は足さない：壁ごとに一つの立体（10-28 監修。足すと 4 枚の面の辺 130・細い片 約70）
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
