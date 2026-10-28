"""ホールの北山杉の林（data/forest.json）、スパン 11 の割り当て（静養室ほか）、2 階の会議室の更衣・ロッカー
使い方: python3 add_hall.py IN.3dm OUT.3dm FOREST.json
- 林：TREES の (xy_mm, d, h) を床 ±0 から h まで円の押し出しで（6 版：すべて自立。10-28：頂部の半球はやめた、Rhino 版で素直な円柱に）。h が無い古い版は TOP の決まり（4.0 − v/12、西吹き抜け 4.4）。
- スパン 11（u 30–33、v 1.6–12）：静養室 v 1.6–4.3（西吹き抜けから戸、事務から見える室内窓）、記録・連絡の机 v 4.3–7.6（ホールへ開く）、
  園長室・応接 v 7.6–12。間仕切り h2400（ほかの保育室の間仕切りと同じ）。
- 2 階の会議室（43）の南の端を職員の更衣・ロッカー（約 17 m²）に仕切る（遊戯室を見渡す北の窓の側は会議に残す）。
- 大人のトイレ（ユーザー、10-23夜。3か所とも性別を示さない個室）：
  スパン 11 の v 1.6–4.3 を多目的便所（車いす・おむつ替え・オストメイト・手洗い、戸は西吹き抜けから、引き戸 1.1）。
  静養室はスパン 7 の奥（v 1.6–4.5、医務と引き込み戸、あまのがわへ戸、窓口から室内窓）。スパン 7 の手前（v 0–1.6）は
  おはようの窓口の帯（カウンターだけ、2 歳の道と配膳の道が抜ける）、飛び石は無し（10-28、案4）。
  3・4 歳のあいだ（スパン 14）の教材庫の西の端 u 40.5–42・v 1.6–3.6 を職員用の個室（戸は西吹き抜けから）。
  路地の形は変えず、路地から教材庫への口を v 3.75–4.75 へ移す。
"""
import sys, math, json, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/south')
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from uv import xy, uv
from meshkit import Kit, R

IN, OUT, FJ = sys.argv[1:4]
F = json.load(open(FJ, encoding='utf-8'))
m = r.File3dm.Read(IN)
LN = {i: l.FullPath for i, l in enumerate(m.Layers)}
hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
def lidx(prefix): return [i for i, n in LN.items() if n.startswith(prefix)][0]

L_TREE = layer('55_ホール_北山杉の林（間伐材）', (178, 140, 96))
L_REST = layer('59_1F_静養室', hexc('F7F3EA'))
L_REC = layer('59_1F_事務（記録・連絡の机）', hexc('E9DCC4'))
L_HEAD = layer('59_1F_園長室・応接', hexc('E9DCC4'))
L_LOCK = layer('43b_2F_職員の更衣・ロッカー', hexc('E3DAF0'))
L_OFF = lidx('59_1F_事務'); L_PART = lidx('38_'); L_KAIGI = lidx('43_'); L_GL = lidx('48_')
L_MPT = layer('59_1F_多目的便所', hexc('D5EBEE'))
L_SWC = layer('59_1F_便所（職員）', hexc('D5EBEE'))
L_OFF7 = lidx('59_1F_事務（スパン 7'); L_WCROOM = lidx('59_1F_便所・倉庫')
L_FURN = lidx('37_'); L_FIX = lidx('39_')
# 3・4 歳、4・5 歳のあいだ（スパン 14・17）の「便所・倉庫」の床を、便所（東、こども）と倉庫（西、教材庫）に分ける（ユーザー 10-25：
# トイレ・倉庫・廊下に分かれる。廊下＝通り抜けは add_shitsurae で分けてある）。板の重心が v 6.0 より東なら便所（設計監修 10-25）
L_KWC = layer('59_1F_便所（こども）', hexc('D5EBEE'))
L_STORE = layer('59_1F_倉庫（教材庫）', hexc('D9D3EC'))
def wc_or_store(poly):
    c = poly.centroid; return L_KWC if uv(c.x, c.y)[1] > 6.0 else L_STORE

def mesh_uv_box(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
    U = np.array([uv(x, y) for x, y in V[:, :2]])
    return U[:, 0].min(), U[:, 0].max(), U[:, 1].min(), U[:, 1].max(), V
def mesh_poly(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y] for i in range(len(g.Vertices))])
    ps = [Polygon(V[[g.Faces[i][0], g.Faces[i][1], g.Faces[i][2]]]).buffer(0) for i in range(g.Faces.Count)]
    return unary_union([p.buffer(1) for p in ps if p.area > 0]).buffer(-1)

out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
kaigi = []
wcroom14 = []                                   # スパン 14 の「便所・倉庫」の床の板（10-24夜から通り抜けを分けて二枚以上ある）
for o in m.Objects:
    g = o.Geometry; li = o.Attributes.LayerIndex
    if isinstance(g, r.Mesh):
        if li == L_OFF:
            u0, u1, v0, v1, _ = mesh_uv_box(g)
            if 29.5 < u0 and u1 < 33.5: continue                       # スパン 11 の事務の板 → 3 つに分ける
        if li == L_PART:
            u0, u1, v0, v1, _ = mesh_uv_box(g)
            if 29.9 < u0 < 30.1 and 32.9 < u1 < 33.1 and v1 - v0 < 0.2 and 1.4 < v0 < 1.7: continue   # 西の壁（戸を開けて作り直す）
        if li == L_KAIGI:
            kaigi.append(mesh_poly(g)); continue
        # ---- 大人のトイレ（10-23夜）：作り直す物を抜く
        if li == L_OFF7:
            continue                                                    # スパン 7 の事務の板 → 窓口の帯と静養室に分ける
        if li in (L_PART, L_FURN):
            u0, u1, v0, v1, _ = mesh_uv_box(g)
            if li == L_FURN and 20.5 < u0 and u1 < 21.0 and v0 > 0.1 and v1 < 2.4: continue          # おはようの窓口のカウンター
            if li == L_PART and 21.5 < u0 and u1 < 22.0 and 2.8 < v0 and v1 < 4.0: continue          # あまのがわの飛び石（帯の正面へ移す）
            if li == L_PART and 40.4 < u0 and u1 < 40.6 and 1.6 < v0 and v1 < 5.1: continue          # 路地｜教材庫の壁（口を北へ移す）
            if li == L_PART and 40.4 < u0 and u1 < 42.1 and 1.5 < v0 and v1 < 1.7: continue          # 教材庫の西の壁（職員の個室の戸）
        if li == L_WCROOM:
            u0, u1, v0, v1, _ = mesh_uv_box(g)
            if 38.9 < u0 and u1 < 42.1:
                wcroom14.append(mesh_poly(g)); continue                 # スパン 14 の床の板から職員の個室を抜く（前は一枚だけ残して、便所の床 約9 m² が消えていた、設計監修 10-25）
            o.Attributes.LayerIndex = wc_or_store(mesh_poly(g))        # スパン 17：便所と倉庫に分ける
    out.Objects.Add(g, o.Attributes)
K = Kit(out)

# ---------------------------------------------------------------- 北山杉の林
TOP = F['TOP']
n = n_cut = 0
_RZ = lambda v: 4150.0 - v * 1000.0 / 12.0            # 元の屋根の面（fix_details.py の ROOF_Z）
_CUT_DZ = -475.0                                         # 削る段の屋根の下面（合板の下 −324 から垂木の層 150 下げた −474）の 1 mm 下
def _span_plane(k):
    """スパン k の屋根の平面（fix_details.py の _plane・zpl と同じ）→ z(x, y)"""
    A_ = np.asarray(xy(3.0 * k, 0.0), float); B_ = np.asarray(xy(3.0 * (k + 1), 0.0), float); c_ = (B_ - A_) / np.linalg.norm(B_ - A_)
    h_ = np.array([c_[1], -c_[0]])
    if np.dot(h_, np.asarray(xy(3.0 * k, 1.0), float) - A_) < 0: h_ = -h_
    return lambda x_, y_: _RZ(((x_ - A_[0]) * h_[0] + (y_ - A_[1]) * h_[1]) / 1000.0)
def _trunk_cut(x, y, rr, htop, v):
    """幹の頭が削る段の屋根の下面に届くなら、その平面 z(x, y)（スパンの中、v 1.9〜11.8 の所だけ）。届かなければ None"""
    us = [uv(x + rr * math.cos(a), y + rr * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    k0, k1 = int(min(p[0] for p in us) // 3.0), int(max(p[0] for p in us) // 3.0)
    vmin, vmax = min(p[1] for p in us), max(p[1] for p in us)
    if k0 != k1 or vmin < 1.9 or vmax > 11.8: return None
    zp = _span_plane(k0); zc = lambda x_, y_: zp(x_, y_) + _CUT_DZ
    if htop <= min(zc(x + rr * math.cos(a), y + rr * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16)) + 1.0: return None
    return zc
def _trunk_mesh(x, y, rr, zc, N=72):
    """円（N 角、5°おき）の押し出し。下は床 ±0、頭は平面 zc（斜めの平らな端）"""
    mm = r.Mesh(); mm.Vertices.UseDoublePrecisionVertices = True      # 単精度だと斜めの頭が 0.01 mm 合わず Rhino 版で押し出しにならない
    P = [(x + rr * math.cos(2 * math.pi * k / N), y + rr * math.sin(2 * math.pi * k / N)) for k in range(N)]
    for px, py in P: mm.Vertices.Add(px, py, 0.0)
    for px, py in P: mm.Vertices.Add(px, py, float(zc(px, py)))
    for k in range(N): mm.Faces.AddFace(k, (k + 1) % N, N + (k + 1) % N, N + k)
    for k in range(1, N - 1): mm.Faces.AddFace(0, k + 1, k); mm.Faces.AddFace(N, N + k, N + k + 1)
    mm.Normals.ComputeNormals(); mm.Compact(); return mm
for t in F['TREES']:
    x, y = t['xy_mm']; v = t['v']; rr = t['d'] * 500; nn = 12 if t['d'] < 0.15 else 20
    if 'h' in t: top = t['h']                                         # 6 版：木ごとの高さ（床から、自立、頂部は半球）
    else: top = TOP['WEST_VOID_TOP'] if v < TOP['WEST_VOID_V'] else (4.0 - v / 12.0)
    # 10-28（監修の項 20261027-2346 の 55）：幹は円の押し出し（φd、床 ±0 から h まで）。前は円柱＋頂部の半球を帯の網目にしていて、
    # Rhino 版で 1 本 5 面の Brep（39 KB）になっていた。太さ・高さ（data/forest.json）は変えない（頂部の丸みは平らな端に）
    at_ = r.ObjectAttributes(); at_.LayerIndex = L_TREE; at_.Name = f"{t.get('group', '')} φ{int(t['d'] * 1000)} h{top:.2f}"
    # 10-28（監修の項 20261028-0843 の 55）：屋根の下面より高い幹は、削る段（clip_parts、250 の格子の屋根の下面）で頭を欠かれ、
    # 格子の段で頭が平らでなくなり Rhino 版で三角形の面になっていた。削る段が切る高さ（スパンの屋根の平面の 474 下）で、
    # ここで頭を平らな斜めの面に切っておく（削る段の差は 0.2 L 未満で、もう削られない）。形は同じ。幹が架構の線をまたぐ所、
    # 越屋根の下（v < 1.9）・桁の下（v > 11.8）など、平らに切れない所はそのまま（削る段が切る）
    cut = _trunk_cut(x, y, rr, top * 1000.0, v)
    if cut is not None:
        out.Objects.AddMesh(_trunk_mesh(x, y, rr, cut), at_); n_cut += 1
    else:
        cyl = r.Cylinder(r.Circle(r.Point3d(x, y, 0.0), rr), top * 1000.0)
        out.Objects.AddExtrusion(r.Extrusion.CreateCylinderExtrusion(cyl, True, True), at_)
    n += 1
print('trees', n, 'cut to roof plane', n_cut)

# ---------------------------------------------------------------- スパン 11
H = 2400.0
K.flat(R(30, 33, 1.6, 4.3), 10, L_MPT)                                 # 多目的便所（10-23夜、もと静養室）
K.flat(R(30, 33, 4.3, 7.6), 10, L_REC)
K.flat(R(30, 33, 7.6, 12.0), 10, L_HEAD)
def wall_v(v, u0, u1, holes=()):
    cuts = sorted(set([u0, u1] + [h[0] for h in holes] + [h[1] for h in holes]))
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2; zs = [(0.0, H)]
        for h in holes:
            if h[0] <= mid <= h[1]: zs = [(0.0, h[2]), (h[3], H)]
        for z0, z1 in zs:
            if z1 - z0 > 5: K.prism(R(a, b, v - 0.05, v + 0.05, 0.1), z0, z1, L_PART)
def wall_u(u, v0, v1, holes=()):
    cuts = sorted(set([v0, v1] + [h[0] for h in holes] + [h[1] for h in holes]))
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2; zs = [(0.0, H)]
        for h in holes:
            if h[0] <= mid <= h[1]: zs = [(0.0, h[2]), (h[3], H)]
        for z0, z1 in zs:
            if z1 - z0 > 5: K.prism(R(u - 0.05, u + 0.05, a, b, 0.02), z0, z1, L_PART)
def blk(u0, u1, v0, v1, z0, z1, li, col=None): K.prism(R(u0, u1, v0, v1, 0.05), z0, z1, li, col)
WHITE = (240, 244, 245); STEEL = (150, 150, 150); WOOD = (196, 160, 110)
wall_v(1.6, 30.0, 33.0, [(30.9, 32.0, 0, 2100)])                    # 西の壁：西吹き抜けから多目的便所へ（引き戸 1.1）
wall_u(30.0, 1.6, 4.3)                                              # 多目的便所｜ホール
wall_v(4.3, 30.0, 33.0)                                             # 多目的便所｜記録の机（戸・窓は無し）
wall_v(7.6, 30.0, 33.0, [(30.3, 31.1, 0, 2100)])                    # 記録の机｜園長室・応接
wall_u(30.0, 7.6, 12.0)                                             # 園長室｜ホール
# 多目的便所の器具（たたき台）：便器は東の壁を背に、北に L 形の手すり・南に跳ね上げの手すり、
# 南の壁に手洗いとおむつ替え台（折りたたみ）、北の壁にオストメイトの流し。中に回転の円 φ1.5
blk(32.30, 32.70, 3.60, 4.25, 0, 420, L_FIX, WHITE)                  # 便器
blk(32.30, 32.70, 4.05, 4.25, 420, 800, L_FIX, WHITE)                # 洗浄の箱（背）
blk(32.88, 32.93, 3.10, 4.20, 700, 740, L_FIX, STEEL)                # L 形の手すり（横）
blk(32.88, 32.93, 3.10, 3.15, 700, 1500, L_FIX, STEEL)               # L 形の手すり（縦）
blk(32.02, 32.07, 3.40, 4.20, 700, 740, L_FIX, STEEL)                # 跳ね上げの手すり
blk(30.05, 30.55, 2.40, 2.95, 700, 760, L_FIX, WHITE)                # 手洗い（車いすで寄れる、下を空ける）
blk(30.05, 30.45, 3.30, 4.20, 780, 820, L_FURN, WOOD)                # おむつ替え台（折りたたみ、開いた状態）
blk(32.55, 32.95, 1.80, 2.40, 0, 600, L_FIX, WHITE)                  # オストメイトの流し

# ---------------------------------------------------------------- スパン 7：おはようの窓口の帯・静養室（10-23夜）
K.flat(R(18, 21, 0.0, 1.6), 10, L_OFF7)                             # 窓口の帯（事務室に数える）
K.flat(R(18, 21, 1.6, 4.5), 10, L_REST)                             # 静養室（医務室に数える）
wall_v(1.6, 18.0, 21.0, [(18.6, 20.2, 900, 2000)])                  # 帯｜静養室：先生が見守る室内窓
K.prism(R(18.6, 20.2, 1.585, 1.615, 0.05), 900.0, 2000.0, L_GL)
wall_u(21.0, 1.6, 4.5, [(3.0, 3.9, 0, 2100)])                       # 静養室｜あまのがわ：戸（お迎えの保護者へ、框 150 は下のまま）
blk(20.60, 20.95, 0.95, 1.55, 0, 700, L_FURN, WOOD)                 # おはようの窓口（低いカウンター、あまのがわに向く）
blk(18.10, 18.80, 1.75, 3.15, 0, 400, L_FURN, (235, 228, 214))      # ベッド（こども用 0.7×1.4）
blk(19.00, 19.70, 1.75, 3.15, 0, 400, L_FURN, (235, 228, 214))      # ベッド
# 飛び石は無し（10-28 ユーザー、案4：入口の近くの飛び石は危ない。給食は内縁側で先生が川へ下りて渡る、add_floor.py の手すり）

# ---------------------------------------------------------------- スパン 14：職員用の個室（10-23夜）
for _g in wcroom14:
    _d = _g.difference(R(40.5, 42.0, 1.6, 3.6, 0.05).buffer(1))
    for _p in getattr(_d, 'geoms', [_d]):
        if _p.geom_type == 'Polygon' and _p.area > 5e4: K.flat(_p, 10, wc_or_store(_p))
K.flat(R(40.5, 42.0, 1.6, 3.6), 10, L_SWC)
wall_u(40.5, 1.65, 5.0, [(3.75, 4.75, 0, 2100)])                    # 路地｜個室・教材庫（教材庫の口を北へ移す、路地の形は同じ）
wall_v(1.6, 40.5, 42.0, [(41.15, 41.95, 0, 2100)])                  # 西吹き抜け｜個室：戸
K.prism(R(40.5, 42.0, 3.55, 3.65, 0.05), 0.0, H, L_PART)            # 個室｜教材庫
blk(40.65, 41.05, 2.90, 3.55, 0, 420, L_FIX, WHITE)                 # 便器
blk(41.55, 41.95, 3.10, 3.55, 700, 760, L_FIX, WHITE)               # 手洗い

# ---------------------------------------------------------------- 2 階：会議室の南の端を更衣・ロッカーに
if kaigi:
    K2 = unary_union(kaigi)
    zf = 3260.0
    # 南から測って約 17 m² になる u を探す
    lo, hi = 27.5, 33.0
    for _ in range(30):
        mid = (lo + hi) / 2
        a = K2.intersection(R(20, mid, -20, 0)).area / 1e6
        lo, hi = (mid, hi) if a < 17.0 else (lo, mid)
    uc = round((lo + hi) / 2, 2)
    K.flat(K2.intersection(R(20, uc, -20, 0)), zf, L_LOCK)
    K.flat(K2.difference(R(20, uc, -20, 0)), zf, L_KAIGI)
    vmin = min(uv(*p)[1] for p in K2.exterior.coords); vmax = max(uv(*p)[1] for p in K2.exterior.coords)
    cuts = [(vmax - 1.6, vmax - 0.8)]                                 # 戸（東寄り、2 階のホールの側）
    for a, b in zip(sorted([vmin, vmax] + [c for cc in cuts for c in cc])[:-1], sorted([vmin, vmax] + [c for cc in cuts for c in cc])[1:]):
        mid = (a + b) / 2; door = any(c0 <= mid <= c1 for c0, c1 in cuts)
        piece = R(uc - 0.05, uc + 0.05, a, b, 0.02).intersection(K2)
        K.prism(piece, zf + 2100 if door else zf, zf + H, L_PART) if door else K.prism(piece, zf, zf + H, L_PART)
    print('locker split at u', uc, 'area', round(K2.intersection(R(20, uc, -20, 0)).area / 1e6, 1))

out.Write(OUT, 8); print('written', OUT, len(out.Objects))
