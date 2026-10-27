"""西館の外壁の大和張り（杉 135×15 の上板）を 3dm に描く（10-27夜のユーザーの決定：3dm にも大和張りを。本館は yamato.py）
使い方: python3 yamato_west.py IN.3dm OUT.3dm [wnew.pkl]
- 上板は本館（yamato.py）と同じ：幅 135・厚さ 15、裏の面を外壁（21）の外の面に付けて外へ 15 出す。割り 約240（見えの割り 約120）、
  縦に足もとから外壁の上端まで一本（継がない）。窓・戸・勝手口・搬入の大戸のまわりは板を切る。細い切れ端は張らない。
- 面：西館の外皮の輪郭（wnew.pkl の WS）の上にある外壁 21 の外の面（西の面・北西の斜めの面・南北の妻・角の丸み）。
  東の面（v −0.9、本館とのすき間の側：すき間の中の室内の壁と、その上の東の高窓の帯）は張らない。
  窓の抱き・水切りの前の面・南の越屋根の妻（外皮から 30 内）は外皮の輪郭の上に無いので張らない。北の越屋根の妻は北の妻と同じ面にあるので、
  越屋根の下の列（v −2.7 より東）で屋根に切られた上の片（下の端が h6.5 より上）を張らない。
- 外壁の外の面を外皮の輪郭に沿って展開し（s：輪郭に沿う長さ、z：高さ）、まっすぐな面（妻・西・北西）と角の丸み（R 約3.1 の細かい面の並び）
  ごとに、長さ w に n = max(1, round(w/240)) 枚を等分に置く（本館と同じ：面の中央にそろう）。丸みでは板は平らなまま、板の幅の弦に沿わせ、
  輪郭のいちばん外の点に裏を付ける（丸みは板の並びで近似）。
- 開口・出し梁の欠き・外壁の上端は外壁の立体の形のまま（展開した面の穴と輪郭で切る）。南北の妻の水切り（h3.25〜3.27、外壁の立体の一部）の所は
  外の面が無いので、板は水切りで上下に分かれる。上板の厚さの層にかかるほかの物（屋根・母屋・樋・柱・大戸のレールなど）は yamato.py と同じく
  面に写して抜く。
- 新しいレイヤー 21y_西館_外壁の大和張り（杉 135×15、上板）、色 (196,160,118)、材質は外壁（21）と同じ。ほかの物はそのまま写す。
"""
import sys, os, re, math, pickle, numpy as np, rhino3dm as r, trimesh
import shapely
from shapely.geometry import Polygon, MultiPoint, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import mapbox_earcut as earcut
import manifold3d as mf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uv import uv, xy

IN, OUT = sys.argv[1], sys.argv[2]
WNPKL = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data', 'wnew.pkl')
BW, BT, PITCH = 135.0, 15.0, 240.0          # 上板の幅・厚さ、目安のピッチ（本館と同じ）
ON_TOL = 5.0                                # 外皮の輪郭の上とみなす距離（mm）
LNAME = '21y_西館_外壁の大和張り（杉 135×15、上板）'
ONAME = '大和張りの上板（杉 135×15）'
CEDAR = (196, 160, 118)
OPEN_RE = re.compile(r'^(16[a-z]?|18|19[a-z]?|35d|48|66|89)_')
SKIP_RE = re.compile(r'^(0\d|17|17y|21|21y|35|3[1-46]|4[1-57]|43b|5[2-79]|9\d)_')

m = r.File3dm.Read(IN)
LN = {i: l.FullPath for i, l in enumerate(m.Layers)}
_D = pickle.load(open(WNPKL, 'rb')); WS = _D.get('WS', _D['WN'])

def mesh_vf(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))], float)
    F = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; F.append((f[0], f[1], f[2]))
        if f[3] != f[2]: F.append((f[0], f[2], f[3]))
    return V, np.array(F, int).reshape(-1, 3)

# ---- 外皮の輪郭を、東の面の中ほど（u 36, v −0.9）から始まる線に（南の妻 → 丸み → 西 → 北西 → 北の妻 → 東の面）
ring = np.asarray(orient(WS, 1.0).exterior.coords)[:-1]
k0 = int(np.argmin([np.hypot(*(p - xy(36.0, -0.9))) for p in ring]))
ring = np.vstack([ring[k0:], ring[:k0]])
# 向き：始まりから南（u の小さい方）へ
if uv(*ring[1])[0] > uv(*ring[0])[0]: ring = np.vstack([ring[:1], ring[1:][::-1]])
RING = LineString(np.vstack([ring, ring[:1]]))
SL = RING.length
# 頂点ごとの s
sv = np.r_[0, np.cumsum(np.hypot(*np.diff(np.vstack([ring, ring[:1]]), axis=0).T))]

# ---- 段（まっすぐな辺の続き＝面、細かい辺の続き＝丸み）
def is_east(p, q):
    return uv(*p)[1] > -1.0 and uv(*q)[1] > -1.0
edges = []
for i in range(len(ring)):
    p, q = ring[i], ring[(i + 1) % len(ring)]
    edges.append(dict(a=sv[i], b=sv[i + 1], d=(q - p) / max(np.hypot(*(q - p)), 1e-9), L=np.hypot(*(q - p)), east=is_east(p, q)))
SEG = []                                   # [kind, a, b, d]
for e in edges:
    if e['east']: kind = 'east'
    elif e['L'] >= 1000: kind = 'flat'
    else: kind = 'curve'
    if SEG and SEG[-1][0] == kind and (kind == 'curve' or (kind == 'flat' and SEG[-1][3] @ e['d'] > math.cos(math.radians(0.5)))):
        SEG[-1][2] = e['b']
    else:
        SEG.append([kind, e['a'], e['b'], e['d']])
SEG = [s for s in SEG if s[0] != 'east']

# ---- 外壁 21 の外の面の三角形 → 展開（s, z）
o21 = [o for o in m.Objects if LN[o.Attributes.LayerIndex].startswith('21_') and isinstance(o.Geometry, r.Mesh)]
WSin = WS.buffer(-1.0)
tris2 = []
for o in o21:
    V, F = mesh_vf(o.Geometry)
    A = V[F]; N = np.cross(A[:, 1] - A[:, 0], A[:, 2] - A[:, 0]); L = np.linalg.norm(N, axis=1)
    ok = (L > 1e-3); A, N = A[ok], N[ok] / L[ok, None]
    ver = np.abs(N[:, 2]) < 1e-4
    A, N = A[ver], N[ver]
    C = A.mean(1)
    # 外皮の輪郭の上：三つの頂点とも輪郭から ON_TOL 以内
    dist = shapely.distance(shapely.points(A.reshape(-1, 3)[:, :2]), RING).reshape(-1, 3).max(1)
    out = ~shapely.contains_xy(WS, C[:, 0] + N[:, 0] * 300, C[:, 1] + N[:, 1] * 300)
    inn = shapely.contains_xy(WS, C[:, 0] - N[:, 0] * 300, C[:, 1] - N[:, 1] * 300)
    sel = (dist < ON_TOL) & out & inn
    for T in A[sel]:
        s = shapely.line_locate_point(RING, shapely.points(T[:, :2]))
        if s.max() - s.min() > SL / 2: continue                       # 輪郭の始まりをまたぐ（東の面だけ。無いはず）
        p = Polygon(np.c_[s, T[:, 2]])
        if p.area > 1.0: tris2.append(p.buffer(0))
DOM = unary_union(tris2).buffer(0.3, join_style=2).buffer(-0.3, join_style=2).simplify(0.2)
# 東の面の三角形は ring の東の辺の上にあるので、段から外す（SEG に無い）

def P_at(s):
    p = RING.interpolate(s % SL); return np.array([p.x, p.y])

def board_frame(c):
    """s = c の板の面：板の幅の弦に沿う向き h（s の増える向き）、外向きの n、輪郭のいちばん外の点に付く原点 O（z=0）"""
    a, b = P_at(c - BW / 2), P_at(c + BW / 2)
    h = (b - a) / np.linalg.norm(b - a)
    n = np.array([h[1], -h[0]])
    mid = (a + b) / 2
    if WS.contains(Point(*(mid + n * 300))): n = -n
    pts = [a, b] + [ring[i] for i in range(len(ring)) if c - BW / 2 < sv[i] < c + BW / 2]
    d = max(float(n @ p) for p in pts)
    O = mid + n * (d - float(n @ mid))
    # yamato.py と同じ向き：h × ez = n。s の向きと逆なら sg = −1
    h3 = np.array([-n[1], n[0], 0.0]); sg = 1.0 if h3[:2] @ h > 0 else -1.0
    return np.r_[n, 0.0], np.r_[O, 0.0], h3, sg

# ---- 上板の厚さの層にかかる物（yamato.py と同じ）
def _tm(V, F):
    t = trimesh.Trimesh(V, F, process=True); t.merge_vertices(digits_vertex=1)
    t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()
    if t.is_watertight and t.volume < 0: t.invert()
    return t
WSB = WS.buffer(1500.0).bounds
OBST = []
for o in m.Objects:
    ln = LN[o.Attributes.LayerIndex]
    if SKIP_RE.match(ln) or not isinstance(o.Geometry, r.Mesh): continue
    bb = o.Geometry.GetBoundingBox()
    if bb.Max.X < WSB[0] or bb.Min.X > WSB[2] or bb.Max.Y < WSB[1] or bb.Min.Y > WSB[3]: continue
    V, F = mesh_vf(o.Geometry)
    if len(F): OBST.append(dict(ln=ln, V=V, F=F, lo=V.min(0), hi=V.max(0), open=bool(OPEN_RE.match(ln)), tm=None))

def proj(P, O, h):
    return np.c_[(P - O) @ h, P[:, 2]]

def _shadow_tris(Wt, O, h):
    ps = [Polygon(proj(T, O, h)) for T in Wt]
    ps = [p.buffer(0) for p in ps if p.area > 0.5]
    return unary_union(ps) if ps else None

CUT_BY = {}
def opening_cut(f):
    n, O, h = f['n'], f['O'], f['h']; ez = np.array([0, 0, 1.0])
    s0, z0, s1, z1 = f['poly'].bounds
    C = np.array([O + s * h + z * ez + t * n for s in (s0 - 50, s1 + 50) for z in (z0 - 50, z1 + 50) for t in (-6, BT + 6)])
    lo, hi = C.min(0), C.max(0)
    cuts = []
    for ob in OBST:
        if (ob['lo'] > hi).any() or (ob['hi'] < lo).any(): continue
        V, F = ob['V'], ob['F']
        t = (V - O) @ n
        ta, tb = (-5.0, BT + 5.0) if ob['open'] else (0.5, BT)
        if t.max() < ta or t.min() > tb: continue
        q = proj(V, O, h)
        if q[:, 0].max() < s0 or q[:, 0].min() > s1 or q[:, 1].max() < z0 or q[:, 1].min() > z1: continue
        sh = None
        if ob['tm'] is None: ob['tm'] = _tm(V, F)
        tm = ob['tm']
        if tm.is_watertight and tm.is_winding_consistent:
            L = np.array([[s0 - 50, z0 - 50, ta], [s1 + 50, z1 + 50, tb]])
            bx = trimesh.creation.box(bounds=L)
            BV = O + np.outer(bx.vertices[:, 0], h) + np.outer(bx.vertices[:, 1], ez) + np.outer(bx.vertices[:, 2], n)
            try:
                o_ = O.copy()                                             # 原点を近くに（float32 の桁落ちを避ける）
                Mo = mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices - o_, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
                Mb = mf.Manifold(mf.Mesh(vert_properties=np.asarray(BV - o_, np.float32), tri_verts=np.asarray(bx.faces, np.uint32)))
                X = (Mo ^ Mb).to_mesh()
                XV = np.asarray(X.vert_properties)[:, :3] + o_; XF = np.asarray(X.tri_verts)
                if len(XF): sh = _shadow_tris(XV[XF], O, h)
                else: continue
            except Exception:
                sh = None
        if sh is None:
            try:
                tt = trimesh.Trimesh(V, F, process=False)
                tt = trimesh.intersections.slice_mesh_plane(tt, n, O + n * ta, cap=False)
                tt = trimesh.intersections.slice_mesh_plane(tt, -n, O + n * tb, cap=False)
                if tt is None or len(tt.vertices) < 3: continue
                W = np.asarray(tt.vertices)
            except Exception:
                W = V[(t >= ta) & (t <= tb)]
                if len(W) < 3: continue
            sh = MultiPoint([tuple(p) for p in proj(W, O, h)]).convex_hull
        if sh is None or sh.is_empty or sh.area < 100: continue
        cuts.append(sh.buffer(5 if ob['open'] else 1, join_style=2))
        k = ob['ln'][:4].rstrip('_'); CUT_BY[k] = CUT_BY.get(k, 0) + 1
    return unary_union(cuts) if cuts else None

def board_mesh(pg, f):
    n, O, h = f['n'], f['O'], f['h']; ez = np.array([0, 0, 1.0])
    pg = orient(pg, 1.0)
    rings = [np.asarray(pg.exterior.coords)[:-1]] + [np.asarray(x.coords)[:-1] for x in pg.interiors]
    Q = np.vstack(rings); k = len(Q)
    ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
    tri = earcut.triangulate_float64(Q, ends).reshape(-1, 3)
    W0 = O + np.outer(Q[:, 0], h) + np.outer(Q[:, 1], ez)
    W1 = W0 + n * BT
    mm = r.Mesh()
    for p in np.vstack([W0, W1]): mm.Vertices.Add(*map(float, p))
    for a, b, c in tri:
        ar = (Q[b, 0] - Q[a, 0]) * (Q[c, 1] - Q[a, 1]) - (Q[b, 1] - Q[a, 1]) * (Q[c, 0] - Q[a, 0])
        if ar < 0: b, c = c, b
        mm.Faces.AddFace(int(a + k), int(b + k), int(c + k))
        mm.Faces.AddFace(int(a), int(c), int(b))
    st = 0
    for e in ends:
        for i in range(st, e):
            j = i + 1 if i + 1 < e else st
            mm.Faces.AddFace(int(i), int(j), int(j + k), int(i + k))
        st = e
    mm.Normals.ComputeNormals(); mm.Compact()
    return mm

li = None
for i, l in enumerate(m.Layers):
    if l.FullPath == LNAME: li = i
if li is None:
    L = r.Layer(); L.Name = LNAME; L.Color = (*CEDAR, 255)
    mi = next((l.RenderMaterialIndex for l in m.Layers if l.FullPath.startswith('21_')), -1)
    if mi >= 0: L.RenderMaterialIndex = mi
    li = m.Layers.Add(L)
att = r.ObjectAttributes(); att.LayerIndex = li; att.Name = ONAME

def seg_name(kind, a, b):
    u_, v_ = uv(*P_at((a + b) / 2))
    if kind == 'curve': return '丸み'
    if u_ < 21.5: return '南の妻'
    if u_ > 50.5: return '北の妻'
    if v_ < -12.5 and u_ < 42: return '西'
    return '北西'

nb, area, per, ndrop, nmon = 0, 0.0, {}, 0, 0
Z_MON = 6500.0                              # 越屋根の妻の片：屋根で切られた上の片（下の端がこれより上）
z_lo, z_hi = DOM.bounds[1] - 10, DOM.bounds[3] + 10
for kind, a, b, _ in SEG:
    w = b - a; nn = max(1, round(w / PITCH)); p = w / nn; nm = seg_name(kind, a, b)
    for i in range(nn):
        c = a + p * (i + 0.5)
        piece = DOM.intersection(box(c - BW / 2, z_lo, c + BW / 2, z_hi))
        if piece.is_empty: continue
        n3, O3, h3, sg = board_frame(c)
        in_mon = uv(*P_at(c))[1] > -2.7                              # 越屋根の下の列（妻の東の端、v −0.84〜−2.56）
        # 展開の座標（s, z）→ 板の面の座標（h の向きに c から、z）
        loc = shapely.affinity.affine_transform(piece, [sg, 0, 0, 1, -sg * c, 0])
        f = dict(n=n3, O=O3, h=h3, poly=loc)
        cut = opening_cut(f)
        if cut is not None: loc = loc.difference(cut)
        for pg in getattr(loc, 'geoms', [loc]):
            if pg.geom_type != 'Polygon' or pg.is_empty: continue
            pg = pg.simplify(5.0)                                        # 5 mm 未満の小さな欠け（梁の下端の写しなど）はならす：Rhino版で押し出しにならなかった
            if pg.geom_type != 'Polygon' or pg.is_empty: continue
            mr = pg.minimum_rotated_rectangle; xs = np.asarray(mr.exterior.coords)
            short = min(np.linalg.norm(xs[1] - xs[0]), np.linalg.norm(xs[2] - xs[1]))
            if pg.area < BW * 50 or short < 20: ndrop += 1; continue   # 窓の際などの細い切れ端は張らない
            if in_mon and pg.bounds[1] > Z_MON: nmon += 1; continue   # 越屋根の妻（屋根の上、北の妻と同じ面）には張らない
            m.Objects.AddMesh(board_mesh(pg, f), att)
            nb += 1; area += pg.area; per[nm] = per.get(nm, 0) + 1

m.Write(OUT, 8)
print(f'西館の大和張りの上板 {nb} 枚（段 {len(SEG)}、上板の見付け {area / 1e6:.1f} m²、'
      + '・'.join(f'{k} {v}' for k, v in per.items()) + f'、細い切れ端 {ndrop} 片・越屋根の妻 {nmon} 片は張らない、抜いた物 '
      + ' '.join(f'{k}:{v}' for k, v in sorted(CUT_BY.items())) + f'）→ {OUT}')
