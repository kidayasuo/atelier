"""ホールの北山杉の林（data/forest.json）、スパン 11 の割り当て（静養室ほか）、2 階の会議室の更衣・ロッカー
使い方: python3 add_hall.py IN.3dm OUT.3dm FOREST.json
- 林：TREES の (xy_mm, d, h) を床 ±0 から h まで円柱で、頂部は半球（6 版：すべて自立）。h が無い古い版は TOP の決まり（4.0 − v/12、西吹き抜け 4.4）。
- スパン 11（u 30–33、v 1.6–12）：静養室 v 1.6–4.3（西吹き抜けから戸、事務から見える室内窓）、記録・連絡の机 v 4.3–7.6（ホールへ開く）、
  園長室・応接 v 7.6–12。間仕切り h2400（ほかの保育室の間仕切りと同じ）。
- 2 階の会議室（43）の南の端を職員の更衣・ロッカー（約 17 m²）に仕切る（遊戯室を見渡す北の窓の側は会議に残す）。
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
    out.Objects.Add(g, o.Attributes)
K = Kit(out)

# ---------------------------------------------------------------- 北山杉の林
TOP = F['TOP']
n = 0
for t in F['TREES']:
    x, y = t['xy_mm']; v = t['v']; rr = t['d'] * 500; nn = 12 if t['d'] < 0.15 else 20
    if 'h' in t: top = t['h']                                         # 6 版：木ごとの高さ（床から、自立、頂部は半球）
    else: top = TOP['WEST_VOID_TOP'] if v < TOP['WEST_VOID_V'] else (4.0 - v / 12.0)
    z1 = top * 1000 - rr
    prof = [(rr, 0.0)] + [(rr * math.cos(math.radians(a)), z1 + rr * math.sin(math.radians(a))) for a in (0, 30, 55, 75)]
    mm = r.Mesh()
    for rk, zk in prof:
        for k in range(nn):
            th = 2 * math.pi * k / nn; mm.Vertices.Add(x + rk * math.cos(th), y + rk * math.sin(th), zk)
    for j in range(len(prof) - 1):
        for k in range(nn): mm.Faces.AddFace(j * nn + k, j * nn + (k + 1) % nn, (j + 1) * nn + (k + 1) % nn, (j + 1) * nn + k)
    ib = mm.Vertices.Add(x, y, 0.0); it = mm.Vertices.Add(x, y, z1 + rr)
    top_ring = (len(prof) - 1) * nn
    for k in range(nn):
        mm.Faces.AddFace(ib, (k + 1) % nn, k); mm.Faces.AddFace(top_ring + k, top_ring + (k + 1) % nn, it)
    mm.Normals.ComputeNormals(); mm.Compact()
    at_ = r.ObjectAttributes(); at_.LayerIndex = L_TREE; at_.Name = f"{t.get('group', '')} φ{int(t['d'] * 1000)} h{top:.2f}"
    out.Objects.AddMesh(mm, at_)
    n += 1
print('trees', n)

# ---------------------------------------------------------------- スパン 11
H = 2400.0
K.flat(R(30, 33, 1.6, 4.3), 10, L_REST)
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
wall_v(1.6, 30.0, 33.0, [(31.0, 31.9, 0, 2100)])                    # 西の壁：西吹き抜けから静養室へ（保護者が迎えに来る）
wall_u(30.0, 1.6, 4.3)                                              # 静養室｜ホール
wall_v(4.3, 30.0, 33.0, [(30.2, 31.0, 0, 2100), (31.3, 32.6, 900, 2000)])   # 静養室｜記録の机：戸と室内窓
K.prism(R(31.3, 32.6, 4.285, 4.315, 0.05), 900.0, 2000.0, L_GL)
wall_v(7.6, 30.0, 33.0, [(30.3, 31.1, 0, 2100)])                    # 記録の机｜園長室・応接
wall_u(30.0, 7.6, 12.0)                                             # 園長室｜ホール

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
