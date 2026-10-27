"""Rhino版（sodachiya.3dm）で、Rhino が表示用のメッシュを作れない（シェーディングで消える）面の見当をつける（西館係、10-27夜）。
ユーザー（10-27夜）：Rhino のシェーディングで西館の北と西の壁が消え、レイトレースで穴ぼこが見えた。
原因は、平らな面の輪郭（ループ）が自分と交わる・輪郭どうしが触れる面（窓の角と外の縁が一点で触れるなど）。openNURBS の IsValid は
これを見ないので、check_solids.py では通ってしまう。

使い方（sodachiya/ の中で）：
  python3 model/build/south/check_faces.py sodachiya.3dm                 レイヤーごとの数
  python3 model/build/south/check_faces.py sodachiya.3dm 17 11a 13 -v    そのレイヤー（番号の頭）の悪い面を一つずつ（u・v・z）
見るのは Brep の平らな面だけ（押し出しは見ない）。ループの辺を面の平面に写した多角形が自分と交わるか、ループどうしが 0.3 mm より近いか。
"""
import sys, os, numpy as np, rhino3dm as r
from collections import Counter
from shapely.geometry import Polygon, LineString
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uv import uv

def bad_faces(b):
    """Brep b の、輪郭が自分と交わる・触れる平らな面の番号の列"""
    def epts(ei, rev):
        e = b.Edges[ei]; d = e.Domain
        P = np.array([[p.X, p.Y, p.Z] for p in (e.PointAt(t) for t in np.linspace(d.T0, d.T1, 12))])
        return P[::-1] if rev else P
    out = []
    for fi in range(len(b.Faces)):
        fc = b.Faces[fi]
        if not fc.IsPlanar(): continue
        d0, d1 = fc.Domain(0), fc.Domain(1); um, vm = (d0.T0 + d0.T1) / 2, (d1.T0 + d1.T1) / 2
        o = fc.PointAt(um, vm); n = fc.NormalAt(um, vm)
        o = np.array([o.X, o.Y, o.Z]); n = np.array([n.X, n.Y, n.Z])
        a = np.cross(n, [0, 0, 1]) if abs(n[2]) < 0.9 else np.cross(n, [1, 0, 0]); a /= np.linalg.norm(a); c = np.cross(n, a)
        rings = []
        for lp in fc.Loops:
            P = np.vstack([epts(t.EdgeIndex, t.IsReversed) for t in lp.Trims]); rings.append(np.c_[(P - o) @ a, (P - o) @ c])
        bad = any(len(x) >= 3 and not Polygon(x).is_valid for x in rings)
        if not bad:
            bad = any(LineString(rings[i]).distance(LineString(rings[j])) < 0.3 for i in range(len(rings)) for j in range(i + 1, len(rings)))
        if bad: out.append(fi)
    return out

if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if x != '-v']; verbose = '-v' in sys.argv
    f = r.File3dm.Read(args[0]); pre = tuple(p.rstrip('_') + '_' for p in args[1:])
    L = {i: l.Name for i, l in enumerate(f.Layers)}
    cnt, tot = Counter(), Counter()
    for oi, o in enumerate(f.Objects):
        ln = L[o.Attributes.LayerIndex]
        if pre and not ln.startswith(pre): continue
        b = o.Geometry
        if not isinstance(b, r.Brep): continue
        k = ln.split('_')[0]; tot[k] += len(b.Faces)
        bf = bad_faces(b); cnt[k] += len(bf)
        if verbose:
            for fi in bf:
                bb = b.Faces[fi].GetBoundingBox(); u_, v_ = uv((bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2)
                print('%-28s 物 %5d 面 %4d  u %.2f v %.2f z %.2f〜%.2f' % (ln[:28], oi, fi, u_, v_, bb.Min.Z / 1000, bb.Max.Z / 1000))
    for k in sorted(tot):
        if cnt[k]: print('%-4s %4d / %d 面' % (k, cnt[k], tot[k]))
    print('表示できない面の見当：%d（Brep の面 %d のうち）' % (sum(cnt.values()), sum(tot.values())))
