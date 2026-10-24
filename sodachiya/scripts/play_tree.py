"""遊戯室のクスノキ（枝付きの切り株）を、骨格の線から滑らかな立体にする（西館係、10-24）。
骨格は data/play.json の stump.tree（u, w=東から, z, 半径 r、m）。
  1. 各枝の点を滑らかな曲線（Catmull-Rom）でつなぎ、先へ細くなる筒（丸い円錐）を並べる。
  2. 筒どうしを滑らかにつなぐ（smooth min）。根張りは幹から斜め下へ出る筒。樹皮は小さな凹凸。
  3. 枝の先は輪切りの切り口（先の向きに直角な平面で切る）。床（z=0）で切る。
  4. マーチングキューブで閉じた網目に → 間引き。
使い方:
  python3 scripts/play_tree.py             骨格の図（平面・立面）を out/sodachiya_play_tree_skeleton.png に
  from play_tree import tree_mesh          (V[mm, 本体の座標], F) を返す（play3d.py が85に入れる）
  python3 scripts/play_tree.py stl         3Dプリント用 STL（1/100・1/50、細い枝は太らせる）を out/ に
要るもの：numpy・scipy・scikit-image・trimesh・fast_simplification（作り直しの流れでは使わない。
play3d.py が取り込み用ファイルを作るときだけ）。
"""
import os, sys, json, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
P = json.load(open(os.path.join(ROOT, 'data', 'play.json'), encoding='utf-8'))
T = P['stump']['tree']


def catmull(pts, step=0.04):
    """点列（u,w,z,r）を滑らかに。端は延長点で。"""
    p = np.asarray(pts, float)
    if len(p) < 3:
        n = max(2, int(np.linalg.norm(p[-1, :3] - p[0, :3]) / step) + 1)
        return np.array([p[0] + (p[-1] - p[0]) * t for t in np.linspace(0, 1, n)])
    q = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(q) - 2):
        a, b, c, d = q[i - 1], q[i], q[i + 1], q[i + 2]
        n = max(2, int(np.linalg.norm(c[:3] - b[:3]) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3))
    out.append(p[-1])
    return np.array(out)


def branches(scale_min_r=0.0):
    """(名前, 曲線の点列, 切り口があるか) の並び。"""
    out = [('幹', catmull(T['trunk'], 0.05), False)]
    tr = np.array(T['trunk'][0][:2]); R = T['roots']
    for a in R['angles']:
        ar = math.radians(a)
        d = np.array([math.cos(ar), math.sin(ar)])
        p0 = [*(tr + d * 0.15), R['from_z'], R['from_r']]
        p1 = [*(tr + d * R['out'] * 0.6), (R['from_z'] + R['to_z']) / 2 + 0.02, (R['from_r'] + R['to_r']) / 2]
        p2 = [*(tr + d * R['out']), R['to_z'], R['to_r']]
        out.append(('根', catmull([p0, p1, p2], 0.04), False))
    for L in T['limbs']:
        c = catmull(L['pts'], 0.04)
        sl = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c[:, :3], axis=0), axis=1))]
        c[:, 3] *= 1 + 0.16 * np.exp(-sl / 0.14)        # 枝の付け根の首（ふくらみ）
        if scale_min_r: c[:, 3] = np.maximum(c[:, 3], scale_min_r)
        out.append((L['name'], c, True))
    return out


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def field(vox=0.025, min_r=0.0, bark=True):
    """距離の場（m）。負が木の中。"""
    BR = branches(min_r)
    allp = np.vstack([c for _, c, _ in BR])
    lo = allp[:, :3].min(0) - 0.35; hi = allp[:, :3].max(0) + 0.35; lo[2] = -0.0377   # 格子の点が床の高さに来ないように（0ちょうどだと面が潰れる）
    ax = [np.arange(lo[i], hi[i] + vox, vox) for i in range(3)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1)
    D = np.full(G.shape[:3], 9.0)
    K = 0.09                                         # 分かれ目のなめらかさ
    for name, c, cut in BR:
        Db = np.full(G.shape[:3], 9.0)
        for a, b in zip(c[:-1], c[1:]):
            r0, r1 = a[3], b[3]; m = max(r0, r1) + K + 0.02
            sl = tuple(slice(max(0, int((min(a[i], b[i]) - m - lo[i]) / vox)), int((max(a[i], b[i]) + m - lo[i]) / vox) + 2) for i in range(3))
            g = G[sl]; ab = b[:3] - a[:3]; L2 = float(ab @ ab) + 1e-12
            t = np.clip(((g - a[:3]) @ ab) / L2, 0, 1)
            off = g - (a[:3] + t[..., None] * ab)
            if name != '幹' and name != '根':       # 横に張る枝の断面は縦長の楕円（上下に約1.15倍）
                hz = 1 - abs(ab[2]) / math.sqrt(L2)
                off = off * np.array([1, 1, 1 - 0.13 * hz])
            d = np.linalg.norm(off, axis=-1) - (r0 + (r1 - r0) * t)
            Db[sl] = np.minimum(Db[sl], d)
        if cut:                                      # 先の向きに直角な平面で切る（輪切り）
            tip, prev = c[-1, :3], c[-3, :3]; n = (tip - prev) / np.linalg.norm(tip - prev)
            Db = np.maximum(Db, (G - tip) @ n)
        D = smin(D, Db, K) if name != '幹' else np.minimum(D, Db)
    c0 = np.array(T['trunk'][0][:2])                 # 幹の溝：根張りの筋が幹を上る（5本、上へ行くほど浅い）
    th = np.arctan2(G[..., 1] - c0[1], G[..., 0] - c0[0])
    amp = 0.035 * np.clip(1 - G[..., 2] / 1.1, 0, 1) * (np.hypot(G[..., 0] - c0[0], G[..., 1] - c0[1]) < 0.9)
    ang0 = math.radians(T['roots']['angles'][0])
    D = D + amp * (np.cos(5 * (th - ang0)) * -1 + 0.3)
    if bark:                                         # 樹皮：小さな凹凸（振幅 約6mm）
        rng = np.random.default_rng(7)
        from scipy.ndimage import gaussian_filter
        N = gaussian_filter(rng.standard_normal(D.shape), sigma=1.6)
        N /= N.std() + 1e-9
        D = D + 0.006 * N
    D = np.maximum(D, -G[..., 2])                     # 床で切る
    return D, lo, vox


def tree_mesh(vox=0.025, target=60000, min_r=0.0, bark=True, uvw=False):
    from skimage.measure import marching_cubes
    D, lo, vox = field(vox, min_r, bark)
    Dp = np.pad(D, 1, constant_values=1.0)
    V, F, _, _ = marching_cubes(Dp, 0.0, spacing=(vox, vox, vox))
    V = V + lo - vox
    try:
        import fast_simplification
        if len(F) > target:
            V, F = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), 1 - target / len(F))
            V = V.astype(float)
    except ImportError:
        pass
    if uvw: return V, F
    from uv import xy
    XY = np.array([xy(u, -0.9 - w) for u, w in V[:, :2]])
    return np.column_stack([XY, V[:, 2] * 1000.0]), F


# ------------------------------------------------------------------ 図のための外形（骨格の円を並べて合わせる）
def plan_shape(zmax=9.0, umax=None):
    """平面の外形（u, w の shapely 形）。zmax より上・umax より北は除く（切断面より上を描かないとき）。"""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    ds = []
    for name, c, cut in branches():
        for p in c:
            if p[2] - p[3] > zmax or (umax is not None and p[0] > umax): continue
            ds.append(Point(p[0], p[1]).buffer(max(p[3], 0.02), resolution=10))
    return unary_union(ds).buffer(0.02).buffer(-0.02)


def side_shape(wmin=-9.0, wmax=99.0):
    """東から見た外形（u, z の shapely 形）。w の範囲で枝を選ぶ（切断面の手前だけ、など）。"""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    ds = []
    for name, c, cut in branches():
        for p in c:
            if not (wmin - p[3] <= p[1] <= wmax + p[3]): continue
            ds.append(Point(p[0], p[2]).buffer(max(p[3], 0.02), resolution=10))
    g = unary_union(ds).buffer(0.02).buffer(-0.02)
    from shapely.geometry import box
    return g.intersection(box(-99, 0, 99, 99))


# ------------------------------------------------------------------ 骨格の図
def draw_skeleton(path):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = ['Hiragino Sans', 'Noto Sans CJK JP', 'IPAexGothic', 'sans-serif']
    cv = P['cave']
    fig, axs = plt.subplots(1, 2, figsize=(15, 7.2), gridspec_kw={'width_ratios': [1, 1.15]})
    BR = branches()
    col = {'幹': '#6b4a2b', '根': '#9b7a55'}
    # 平面（上が北＝u、右が西＝w）
    a = axs[0]
    def box(ax, x0, x1, y0, y1, **k): ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, **k))
    box(a, 1.19, 4.21, 29.92, 33.12, fc='#ddd', ec='0.4'); a.text(2.7, 31.5, '階段', ha='center', fontsize=9)
    box(a, 10.89, 12.82, 30.05, 33.08, fc='#ddd', ec='0.4'); a.text(11.85, 31.5, '道具入れ', ha='center', fontsize=9, rotation=90)
    box(a, 2.44, 13.0, 29.67, 30.0, fc='#999', ec='none'); a.text(8, 29.75, 'はれのまとの壁', fontsize=8, va='center', color='w')
    for u0, u1 in ((29.82, 30.18), (32.82, 33.18)):
        box(a, 0, 13.0, u0, u1, fc='#b55', ec='none', alpha=0.25)
    a.text(4.5, 33.3, '床梁（2枚組、u30・u33、下端2.23）', color='#b55', fontsize=8)
    a.add_patch(plt.Circle((P['stump']['w'], P['stump']['u']), P['stump']['soft_r'], fc='#f3e6cf', ec='#c9a', zorder=0))
    a.text(P['stump']['w'] + 1.5, P['stump']['u'] - 2.2, 'やわらかい床', fontsize=8, color='#a87')
    for name, c, cut in BR:
        a.plot(c[:, 1], c[:, 0], color=col.get(name, '#8a5a2b'), lw=1)
        for p in c[::3]:
            a.add_patch(plt.Circle((p[1], p[0]), p[3], fc=col.get(name, '#b88a5a'), ec='none', alpha=0.25))
        if cut:
            a.plot(c[-1, 1], c[-1, 0], 'o', ms=4, mfc='w', mec='#6b4a2b')
            a.text(c[-1, 1] + 0.12, c[-1, 0] + 0.1, f'{name}\nh{c[-1, 2] + c[-1, 3]:.2f}', fontsize=7)
    a.set_xlim(13.2, 0); a.set_ylim(29.3, 36.2); a.set_aspect('equal'); a.grid(alpha=0.2)
    a.set_xlabel('西館の東の面から西へ w（m）　←西　　東→'); a.set_ylabel('u（m、北へ）')
    a.set_title('平面（上が北、u30〜33が洞＝2階の床の下）', fontsize=11)
    # 立面（東から見る：横＝u、縦＝z）
    b = axs[1]
    box(b, 29.92, 33.12, 0, 3.17, fc='none', ec='none')
    b.fill_between([29.0, 33.0], 3.17, 3.25, color='#999'); b.text(29.1, 3.32, '2階の床（裏 h3.17）', fontsize=8)
    for u0, u1 in ((29.82, 29.91), (30.09, 30.18), (32.82, 32.91), (33.09, 33.18)):
        box(b, u0, u1, 2.235, 3.2, fc='#c99', ec='#a66')
    b.text(32.6, 2.1, '床梁（2枚組）', fontsize=8, color='#a66', ha='left')
    b.axhline(2.0, color='#58a', ls=':', lw=1); b.text(35.9, 2.03, '登ってよい高さ2.0', color='#58a', fontsize=8, ha='right')
    b.axvline(30.0, color='0.5', lw=3); b.axhline(0, color='k', lw=1)
    for name, c, cut in BR:
        b.plot(c[:, 0], c[:, 2], color=col.get(name, '#8a5a2b'), lw=1)
        for p in c[::3]:
            b.add_patch(plt.Circle((p[0], p[2]), p[3], fc=col.get(name, '#b88a5a'), ec='none', alpha=0.25))
    # 人（3歳 0.95、5歳 1.1、大人 1.6）
    for uu, hh, lab in ((34.6, 0.95, '3歳'), (35.3, 1.1, '5歳'), (35.9, 1.6, '大人')):
        b.plot([uu, uu], [0, hh * 0.82], color='0.3', lw=2); b.add_patch(plt.Circle((uu, hh * 0.9), hh * 0.08, fc='0.3'))
        b.text(uu, -0.18, lab, ha='center', fontsize=7)
    b.set_xlim(29.3, 36.2); b.set_ylim(-0.3, 3.6); b.set_aspect('equal'); b.grid(alpha=0.2)
    b.set_xlabel('u（m、北へ）'); b.set_ylabel('高さ（m、FL）')
    b.set_title('立面（東から見る、右が北＝高い遊戯室）', fontsize=11)
    fig.suptitle('遊戯室のクスノキ：骨格（幹φ約1.0、高さ約0.6で2本の幹に分かれ、さらに枝分かれ。先は輪切り）', fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=130)


if __name__ == '__main__':
    OUT = os.path.join(ROOT, 'out')
    if len(sys.argv) > 1 and sys.argv[1] == 'stl':
        import trimesh
        for sc, mr in ((100, 0.045), (50, 0.025)):           # 印刷の最小の太さ 約0.9mm／1.0mm
            for vx, tgt in ((0.02, 120000), (0.02, 10 ** 9), (0.019, 120000), (0.021, 120000), (0.018, 150000)):   # 閉じるまで格子と間引きを変える
                V, F = tree_mesh(vx, tgt, min_r=mr, bark=(sc == 50), uvw=True)
                V = V.copy(); V[:, 1] *= -1                   # 東から西へを右手系に（x＝北、y＝東）
                V[:, :2] -= np.array([T['trunk'][0][0], -T['trunk'][0][1]])   # 幹の中心を原点に
                m = trimesh.Trimesh(V * 1000.0 / sc, F); m.fix_normals()
                if m.is_watertight: break
            p = os.path.join(OUT, f'sodachiya_play_tree_1-{sc}.stl'); m.export(p)
            print(p, len(F), 'watertight' if m.is_watertight else 'NOT watertight', m.bounds.round(1).tolist())
    else:
        p = os.path.join(OUT, 'sodachiya_play_tree_skeleton.png'); draw_skeleton(p); print(p)
