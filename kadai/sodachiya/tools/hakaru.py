#!/usr/bin/env python3
"""3dm の物を測る：レイヤーで選んで、u・v・z の範囲と大きさ、二つの選びのすき間を出す（効率化委員会、10-31）。
使い捨てのスクリプトを書かずに、まずこれで測る。

  python3 tools/hakaru.py 20v                     レイヤー20vの物を一つ一行で（u・v・z の範囲と大きさ）
  python3 tools/hakaru.py 20,22a --matome         レイヤーごとにまとめて一行
  python3 tools/hakaru.py 22a --box 30,40,-10,-1  u 30〜40・v −10〜−1 にかかる物だけ（,z0,z1 も付けられる）
  python3 tools/hakaru.py 20r --aida 22b          20r と 22b のいちばん近い所（すき間）と、その二点
  python3 tools/hakaru.py 屋根 --file /tmp/claude-0/out/preview/model/sodachiya_exact_mesh.3dm

レイヤーの選び方（, で並べる）：
  - 番号（20・20v・11a）：レイヤーの番号の部分（_ の前）がそれで始まり、残りが英字だけのもの。
    「20」は20・20t・20v…（200は入らない）。「20v」は20vだけ。
  - それ以外：レイヤー名に含まれる語（例「屋根」「西館_柱」）。
  - --name 語：物の名前にその語を含むものだけ。

座標：u・v・z は m。model/build/south/uv.py と同じ変換（本館の背骨＝半径 205 m の弧）。
  u＝南の妻から背骨に沿って北へ、v＝本館の西の外壁の線から東へ（西館は負）、z＝FL ±0 から上。
  du は背骨（v 0）の上で測った長さ。v が大きい所では弧の実の長さと少し違う（v 10で約5 %短い）。
  すき間（--aida）は世界座標（mm）で測った実の距離（頂点と面の上の点から相手の面への最短）。
読むだけ。3dm は変わらない。既定のファイルは model/sodachiya_exact_mesh.3dm（--publish 済みのもの）。
"""
import argparse, math, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A, 'model/build/view'))
sys.path.insert(0, os.path.join(A, 'model/build/south'))
DEFAULT = os.path.join(A, 'model/sodachiya_exact_mesh.3dm')
from uv import CX, CY, RW, TH_S  # noqa: E402


def uv_arr(P):
    """世界座標（mm、N×3）→ u・v・z（m、N×3）"""
    th = np.mod(np.arctan2(P[:, 1] - CY, P[:, 0] - CX), 2 * math.pi)
    return np.c_[(TH_S - th) * RW / 1000, (RW - np.hypot(P[:, 0] - CX, P[:, 1] - CY)) / 1000, P[:, 2] / 1000]


def code(name):
    return name.split('_')[0]


def pick_layers(m, spec):
    """spec（, 区切り）に合うレイヤーの番号の集まり"""
    out = set()
    for s in [x for x in spec.split(',') if x]:
        for i, L in enumerate(m.Layers):
            nm = L.FullPath if hasattr(L, 'FullPath') else L.Name
            if re.fullmatch(r'\d+[a-z]*', s):
                c = code(L.Name)
                if c.startswith(s) and re.fullmatch(r'[a-z]*', c[len(s):]):
                    out.add(i)
            elif s in nm:
                out.add(i)
    return out


def tris(g):
    """物の形 → 三角形（T×3×3、mm）。線は点の並び（N×3）を返す"""
    import rhino3dm as r, tri
    if isinstance(g, r.Mesh):
        return tri.tri_mesh(g), None
    if isinstance(g, r.Extrusion):
        return tri.tri_extrusion(g), None
    if isinstance(g, r.Brep):
        return tri.tri_brep(g), None
    if isinstance(g, r.Curve):
        return None, tri.A3(tri.curve_pts(g))
    return None, None


def gather(m, layers, box, namepat):
    """選んだ物：(レイヤー名, 物の名前, 三角形 or None, 点 mm, 点 uvz)"""
    res = []
    for o in m.Objects:
        li = o.Attributes.LayerIndex
        if li not in layers:
            continue
        nm = o.Attributes.Name or ''
        if namepat and namepat not in nm:
            continue
        T, P = tris(o.Geometry)
        if T is not None:
            if len(T) == 0:
                continue
            P = np.asarray(T).reshape(-1, 3)
        if P is None or len(P) == 0:
            continue
        Q = uv_arr(P)
        if box is not None:
            lo, hi = Q.min(0), Q.max(0)
            b = box
            if hi[0] < b[0] or lo[0] > b[1] or hi[1] < b[2] or lo[1] > b[3]:
                continue
            if len(b) == 6 and (hi[2] < b[4] or lo[2] > b[5]):
                continue
        res.append((m.Layers[li].Name, nm, T, P, Q))
    return res


def rng(Q):
    lo, hi = Q.min(0), Q.max(0)
    return (f"u {lo[0]:7.2f}〜{hi[0]:7.2f}  v {lo[1]:6.2f}〜{hi[1]:6.2f}  z {lo[2]:6.2f}〜{hi[2]:6.2f}"
            f"  大きさ {hi[0] - lo[0]:.2f}×{hi[1] - lo[1]:.2f}×{hi[2] - lo[2]:.2f}")


def short(s, n=28):
    return s if len(s) <= n else s[:n - 1] + '…'


def clearance(a, b):
    """二つの選びのいちばん近い二点（mm）と距離"""
    import trimesh

    def mesh_of(items):
        T = [np.asarray(t) for _, _, t, _, _ in items if t is not None and len(t)]
        if not T:
            return None
        T = np.vstack(T)
        return trimesh.Trimesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3), process=False)

    def pts_of(items, mesh):
        P = np.vstack([p for _, _, _, p, _ in items])
        if mesh is not None and mesh.area > 0:
            n = int(min(20000, max(2000, mesh.area / 2.5e4)))   # 約 150 mm おきの点
            P = np.vstack([P, trimesh.sample.sample_surface(mesh, n, seed=0)[0]])
        return np.unique(P.round(1), axis=0)

    ma, mb = mesh_of(a), mesh_of(b)
    best = (np.inf, None, None)
    for src, own, dst_mesh, dst_items, flip in ((a, ma, mb, b, False), (b, mb, ma, a, True)):
        P = pts_of(src, own)
        if dst_mesh is not None:
            C, d, _ = trimesh.proximity.closest_point(dst_mesh, P)
        else:   # 相手が線だけ：点どうし
            from scipy.spatial import cKDTree
            D = np.vstack([p for _, _, _, p, _ in dst_items])
            d, k = cKDTree(D).query(P); C = D[k]
        i = int(np.argmin(d))
        if d[i] < best[0]:
            best = (d[i], (C[i], P[i]) if flip else (P[i], C[i]), None)
    return best[0], best[1]


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('layers', nargs='?')
    ap.add_argument('--file', default=DEFAULT)
    ap.add_argument('--box')
    ap.add_argument('--name')
    ap.add_argument('--matome', action='store_true')
    ap.add_argument('--aida')
    ap.add_argument('--max', type=int, default=40)
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args()
    if a.help or not a.layers:
        print(__doc__); return 2
    import rhino3dm as r
    if not os.path.exists(a.file):
        print(f"ファイルが無い：{a.file}"); return 1
    m = r.File3dm.Read(a.file)
    box = [float(x) for x in a.box.split(',')] if a.box else None
    if box is not None and len(box) not in (4, 6):
        print("--box は u0,u1,v0,v1 か u0,u1,v0,v1,z0,z1"); return 2
    LA = pick_layers(m, a.layers)
    if not LA:
        print(f"レイヤーに「{a.layers}」が無い"); return 1
    sa = gather(m, LA, box, a.name)
    print(f"{os.path.basename(a.file)}：「{a.layers}」レイヤー{len(LA)}・物{len(sa)}"
          + (f"（box {a.box}）" if box else ''))
    if not sa:
        return 1
    if a.matome:
        by = {}
        for it in sa:
            by.setdefault(it[0], []).append(it)
        rows = [f"{short(ln, 36)}（{len(v)}）  {rng(np.vstack([x[4] for x in v]))}" for ln, v in sorted(by.items())]
    else:
        rows = [f"{short(code(ln) + ' ' + (nm or '—'), 30)}  {rng(Q)}" for ln, nm, _, _, Q in sa]
    for x in rows[:a.max]:
        print(x)
    if len(rows) > a.max:
        print(f"…ほか{len(rows) - a.max}行（--matome か --box で絞る、--max で増やす）")
    Qa = np.vstack([x[4] for x in sa])
    if len(rows) > 1:
        print(f"全体  {rng(Qa)}")
    if a.aida:
        LB = pick_layers(m, a.aida)
        sb = gather(m, LB, box, None) if LB else []
        if not sb:
            print(f"--aida「{a.aida}」に物が無い"); return 1
        d, (p, q) = clearance(sa, sb)
        U = uv_arr(np.array([p, q]))
        print(f"すき間「{a.layers}」〜「{a.aida}」（物{len(sb)}）：{d / 1000:.3f} m"
              f"（{d:.0f} mm）  Δz {U[1, 2] - U[0, 2]:+.3f}")
        print(f"  {a.layers} 側 u {U[0, 0]:.3f} v {U[0, 1]:.3f} z {U[0, 2]:.3f}"
              f"  ／ {a.aida} 側 u {U[1, 0]:.3f} v {U[1, 1]:.3f} z {U[1, 2]:.3f}")
        if d < 1:
            print("  （0 m＝触れているか、重なっている）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
