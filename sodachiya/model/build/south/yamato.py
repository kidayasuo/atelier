"""本館の外壁の大和張り（杉 135×15 の上板）を 3dm に描く（10-26 / 10-27夜のユーザーの決定：3dm にも大和張りを）
使い方: python3 yamato.py IN.3dm OUT.3dm
- 外壁の外の面を下板（裏の板）とみなし、上板だけを足す：幅 135・厚さ 15、裏の面を外壁の外の面に付けて外へ 15 出す。
- 割り：平らな面ごとに、面の幅 w に n = max(1, round(w/240)) 枚、ピッチ w/n（見えの割り 約 120）。上板はピッチの中央、
  上板どうしのすき間に壁の面（下板）が見える。
- 上板は面の高さいっぱいに一本（継ぎ・押縁・胴縁は無し）。窓・戸のところは切る：上板 ＝（縦の帯）∩（穴のある外の面の輪郭）。
- 上板の厚さの層（外壁の外の面から 15）にかかる物（柱・桁・屋根・垂木・床・外構の下屋など）は、層の中の切り口を面に写して抜く
  （10-28：越屋根の立ち上がりの上の端・南の軒の下・縁側の壁の屋根の下で、上板が屋根や柱にめり込んでいた）。
  外壁の網に穴の無い戸（機械室の戸 35d など）は、戸の物を壁の面に写した形も穴として抜く。
- 上板は平らな閉じた角柱（壁の面の中の形 × 面に直角に 15）。法線は外向き。
- 面（本館だけ）：17 の西の壁（v ≈ −0.35、−v の向き）の u 0〜21 と u 51〜57.4（u 21〜51 は西館とのすき間の側なので無し）、
  北の妻（u ≈ 57.34、+u）、南の妻の上の壁と脇の壁（u ≈ 0、−u）、縁側の杉の壁（v ≈ 13.6、+v、各スパンの北の半分）。
  35 機械室：外向きの鉛直の面すべて（平面の重心から外向き）。幅 0.25 m 未満の面（壁の端の厚さの面・曲面の細かい面）と鉛直でない面は無し。
- 新しいレイヤー 17y_本館_外壁の大和張り（杉 135×15、上板）、色 (196,160,118)。ほかの物はそのまま写す。
"""
import sys, re, math, numpy as np, rhino3dm as r, trimesh
from shapely.geometry import Polygon, MultiPolygon, MultiPoint, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import mapbox_earcut as earcut
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))   # uv.py と同じ所（/tmp/claude-0/t/south の写しでも）
from uv import uv, xy

IN, OUT = sys.argv[1], sys.argv[2]
BW, BT, PITCH = 135.0, 15.0, 240.0          # 上板の幅・厚さ、目安のピッチ
MIN_W = 250.0                               # これより幅の狭い面は張らない
ANG_TOL, OFF_TOL = math.radians(0.05), 1.0  # 同じ平面とみなす：法線 0.05° 以内、位置 1 mm 以内
LNAME = '17y_本館_外壁の大和張り（杉 135×15、上板）'
ONAME = '大和張りの上板（杉 135×15）'
CEDAR = (196, 160, 118)
# 開口として抜く物（壁の網に穴の無い戸などのため）：建具・ガラス・戸（5 の逃げ）
OPEN_RE = re.compile(r'^(16[a-z]?|18|19[a-z]?|35d|48|66|89)_')

m = r.File3dm.Read(IN)
LN = {i: l.FullPath for i, l in enumerate(m.Layers)}

def mesh_vf(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))], float)
    F = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; F.append((f[0], f[1], f[2]))
        if f[3] != f[2]: F.append((f[0], f[2], f[3]))
    return V, np.array(F, int).reshape(-1, 3)

def frame_uv(x, y):
    """その点での u・v の向きの単位ベクトル（平面）"""
    u, v = uv(x, y); a = xy(u, v)
    eu = xy(u + 0.01, v) - a; ev = xy(u, v + 0.01) - a
    return eu / np.linalg.norm(eu), ev / np.linalg.norm(ev)

def planes_of(V, F):
    """鉛直の三角形を平面ごとに分ける → [dict(n, d, tris)]"""
    A = V[F]; N = np.cross(A[:, 1] - A[:, 0], A[:, 2] - A[:, 0]); L = np.linalg.norm(N, axis=1)
    ok = L > 1e-3; A, N, L = A[ok], N[ok] / L[ok, None], L[ok]
    G = []
    for i in np.where(np.abs(N[:, 2]) < 1e-4)[0]:
        n = N[i].copy(); n[2] = 0; n /= np.linalg.norm(n); d = float(n @ A[i].mean(0))
        for g in G:
            if g['n'] @ n > math.cos(ANG_TOL) and abs(d - g['d']) < OFF_TOL: g['t'].append(A[i]); break
        else: G.append(dict(n=n, d=d, t=[A[i]]))
    return G

def plane_frame(g):
    """平面の 2 次元の座標：s（面に沿って水平、h = ez × n の向きで h × ez = n）、z（上）"""
    n = g['n']; h = np.array([-n[1], n[0], 0.0]); O = n * g['d']
    return O, h

def proj(P, O, h):
    return np.c_[(P - O) @ h, P[:, 2]]

def face_poly(g, O, h):
    """三角形を写して一つの多角形（穴あり）に。細いすき間は 0.3 mm で閉じる"""
    tris = []
    for T in g['t']:
        q = proj(T, O, h)
        p = Polygon(q)
        if p.area > 1.0: tris.append(p.buffer(0))
    if not tris: return None
    P = unary_union(tris).buffer(0.3, join_style=2).buffer(-0.3, join_style=2)
    return P.simplify(0.2)

# ---- 本館の外壁（17）と機械室（35）
o17 = [o for o in m.Objects if LN[o.Attributes.LayerIndex].startswith('17_') and isinstance(o.Geometry, r.Mesh)]
o35 = [o for o in m.Objects if LN[o.Attributes.LayerIndex].startswith('35_') and isinstance(o.Geometry, r.Mesh)]

def wall_of(P2, n, kind, cen=None):
    """面の向きと位置から、張る面の名前（西・北・南・縁側・機械室）を返す。張らない面は None"""
    c = P2.mean(0)
    u, v = uv(*c[:2]); eu, ev = frame_uv(*c[:2])
    nu, nv = n[:2] @ eu, n[:2] @ ev
    if kind == '35':
        return '機械室' if n[:2] @ (c[:2] - cen) > 0 else None
    U = np.array([uv(x, y)[0] for x, y in P2[:, :2]])
    if nv < -0.99 and v < -0.3:
        if U.max() <= 21.05 or U.min() >= 50.95: return '西'
        return None                                  # u 21〜51：西館とのすき間の側
    if nu > 0.99 and u > 57.2: return '北'
    if nu < -0.99 and u < 0.03: return '南'
    if nv > 0.99 and v > 13.55: return '縁側'
    return None

FACES = []          # (壁の名前, 平面, O, h, 多角形)
for kind, objs in (('17', o17), ('35', o35)):
    for o in objs:
        V, F = mesh_vf(o.Geometry)
        cen = V[:, :2].mean(0) if kind == '35' else None
        if kind == '35':                                 # 平面の重心（面積で重み付けした床の形の重心の代わりに、全体の頂点の範囲の中央）
            cen = 0.5 * (V[:, :2].min(0) + V[:, :2].max(0))
        GS = planes_of(V, F)
        if kind == '35':
            # 機械室の網は裏返っている（体積が負）。法線は使わず、重心から外への向きにそろえ、
            # 平行な面（外の面とパラペットの内の面）は外にあるものだけを残す
            for g in GS:
                c = np.vstack(g['t'])[:, :2].mean(0)
                if g['n'][:2] @ (c - cen) < 0: g['n'] = -g['n']; g['d'] = -g['d']
            GS = [g for g in GS if not any(q is not g and q['n'] @ g['n'] > math.cos(ANG_TOL) and q['d'] > g['d'] + OFF_TOL for q in GS)]
        for g in GS:
            P3 = np.vstack(g['t'])
            name = wall_of(P3, g['n'], kind, cen)
            if name is None: continue
            O, h = plane_frame(g)
            poly = face_poly(g, O, h)
            if poly is None or poly.is_empty: continue
            s0, _, s1, _ = poly.bounds
            if s1 - s0 < MIN_W or poly.area < 0.05e6: continue    # 端の厚さの面・細い切れ端
            FACES.append(dict(wall=name, n=g['n'], O=O, h=h, poly=poly))

# ---- 上板の厚さの層（面から外へ 0〜BT）にかかる物を、面に写して抜く（上板は角柱のまま）
# 開口の物（壁の網に穴の無い戸など）は −5〜BT+5 の層で見て 5 の逃げ。ほかの物（柱・桁・屋根・垂木・床・外構の下屋など）は
# 0.5〜BT の層で、層の中の切り口を正しく写す（屋根の下面の勾配、柱の出など）。外壁そのもの（17・35）と部屋の色の板・敷地・園庭は見ない。
SKIP_RE = re.compile(r'^(0\d|17|17y|35|3[1-46]|4[1-57]|43b|5[2-79]|9\d)_')
import manifold3d as mf
def _tm(V, F):
    t = trimesh.Trimesh(V, F, process=True); t.merge_vertices(digits_vertex=1)
    t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()
    if t.is_watertight and t.volume < 0: t.invert()
    return t
OBST = []
for o in m.Objects:
    ln = LN[o.Attributes.LayerIndex]
    if SKIP_RE.match(ln) or not isinstance(o.Geometry, r.Mesh): continue
    V, F = mesh_vf(o.Geometry)
    if len(F): OBST.append(dict(ln=ln, V=V, F=F, lo=V.min(0), hi=V.max(0), open=bool(OPEN_RE.match(ln))))

def _shadow_tris(Wt, O, h):
    """三角形の網を面に写した形（三角形の和）"""
    ps = [Polygon(proj(T, O, h)) for T in Wt]
    ps = [p.buffer(0) for p in ps if p.area > 0.5]
    return unary_union(ps) if ps else None

def opening_cut(f):
    n, O, h = f['n'], f['O'], f['h']; ez = np.array([0, 0, 1.0])
    s0, z0, s1, z1 = f['poly'].bounds
    C = [O + s * h + z * ez + t * n for s in (s0 - 50, s1 + 50) for z in (z0 - 50, z1 + 50) for t in (-6, BT + 6)]
    C = np.array(C); lo, hi = C.min(0), C.max(0)
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
        tm = _tm(V, F)
        if tm.is_watertight and tm.is_winding_consistent:
            # 層の箱との積（manifold）→ 面に写す
            L = np.array([[s0 - 50, z0 - 50, ta], [s1 + 50, z1 + 50, tb]])
            bx = trimesh.creation.box(bounds=L)
            BV = O + np.outer(bx.vertices[:, 0], h) + np.outer(bx.vertices[:, 1], ez) + np.outer(bx.vertices[:, 2], n)
            try:
                Mo = mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
                Mb = mf.Manifold(mf.Mesh(vert_properties=np.asarray(BV, np.float32), tri_verts=np.asarray(bx.faces, np.uint32)))
                X = (Mo ^ Mb).to_mesh()
                XV = np.asarray(X.vert_properties)[:, :3]; XF = np.asarray(X.tri_verts)
                if len(XF): sh = _shadow_tris(XV[XF], O, h)
                else: continue
            except Exception:
                sh = None
        if sh is None:
            # 閉じていない網：層の中の頂点と切り口の凸包（前の作り方）
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
        f.setdefault('cut_by', set()).add(ob['ln'][:4].rstrip('_'))
    return unary_union(cuts) if cuts else None

# ---- 上板の網（壁の面の中の形 × 外へ BT）
def board_mesh(pg, f):
    n, O, h = f['n'], f['O'], f['h']; ez = np.array([0, 0, 1.0])
    pg = orient(pg, 1.0)
    rings = [np.asarray(pg.exterior.coords)[:-1]] + [np.asarray(x.coords)[:-1] for x in pg.interiors]
    Q = np.vstack(rings); k = len(Q)
    ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
    tri = earcut.triangulate_float64(Q, ends).reshape(-1, 3)
    W0 = O + np.outer(Q[:, 0], h) + np.outer(Q[:, 1], ez)       # 裏（壁の面に付く）
    W1 = W0 + n * BT                                              # 表
    mm = r.Mesh()
    for p in np.vstack([W0, W1]): mm.Vertices.Add(*map(float, p))
    for a, b, c in tri:
        ar = (Q[b, 0] - Q[a, 0]) * (Q[c, 1] - Q[a, 1]) - (Q[b, 1] - Q[a, 1]) * (Q[c, 0] - Q[a, 0])
        if ar < 0: b, c = c, b                                    # 反時計回りにそろえる（h × ez = n なので表の法線が外向き）
        mm.Faces.AddFace(int(a + k), int(b + k), int(c + k))      # 表
        mm.Faces.AddFace(int(a), int(c), int(b))                  # 裏
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
    mi = next((l.RenderMaterialIndex for l in m.Layers if l.FullPath.startswith('17_')), -1)
    if mi >= 0: L.RenderMaterialIndex = mi                        # 外壁（17）と同じ材質
    li = m.Layers.Add(L)
att = r.ObjectAttributes(); att.LayerIndex = li; att.Name = ONAME

nb, area, per, nface, ndrop = 0, 0.0, {}, 0, 0
for f in FACES:
    poly = f['poly']
    cut = opening_cut(f)
    if cut is not None: poly = poly.difference(cut)
    s0, z0, s1, z1 = f['poly'].bounds
    w = s1 - s0; n = max(1, round(w / PITCH)); p = w / n
    put = 0
    for i in range(n):
        c = s0 + p * (i + 0.5)
        piece = poly.intersection(box(c - BW / 2, z0 - 10, c + BW / 2, z1 + 10))
        for pg in getattr(piece, 'geoms', [piece]):
            if pg.geom_type != 'Polygon' or pg.is_empty: continue
            pg = pg.simplify(0.2)
            mr = pg.minimum_rotated_rectangle; xs = np.asarray(mr.exterior.coords)
            short = min(np.linalg.norm(xs[1] - xs[0]), np.linalg.norm(xs[2] - xs[1]))
            if pg.area < BW * 50 or short < 20: ndrop += 1; continue   # 窓の際などの細い切れ端は張らない
            m.Objects.AddMesh(board_mesh(pg, f), att)
            nb += 1; put += 1; area += pg.area; per[f['wall']] = per.get(f['wall'], 0) + 1
    if put: nface += 1

m.Write(OUT, 8)
print(f'大和張りの上板 {nb} 枚（{nface} 面、上板の見付け {area / 1e6:.1f} m²、'
      + '・'.join(f'{k} {v}' for k, v in per.items()) + f'、細い切れ端 {ndrop} 片は張らない）→ {OUT}')
