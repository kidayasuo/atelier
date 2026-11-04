"""本館の保育室の家具（37）の候補：間仕切りになる棚と大きい家具を拾い、配置図（1/100）を書く。python3 mokei/kagu.py"""
import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
import laser
from laser import *
import kirita

def _hull(g):
    import numpy as np
    from shapely.geometry import MultiPoint
    if isinstance(g, r.Mesh):
        pts = [(g.Vertices[i].X, g.Vertices[i].Y) for i in range(len(g.Vertices))]
    else:
        try: pts = list(laser._foot(g).exterior.coords)
        except Exception: return None
    return MultiPoint(pts).convex_hull

def kagu_list():
    flo = unary_union([plan('12_本館_床（はだし ±0）'), plan('14_本館_外縁側（土足 −150）'), plan('15_本館_あまのがわ（土足 −150）')])
    out = []
    for n, g in laser._pf('37_しつらえ_家具（スギ）'):
        b = laser._bb(g)
        if b[2] > 600: continue                                   # 床から離れた物（ロフト・2 階）は除く
        P = _hull(g)
        if P is None or P.is_empty: continue
        c = P.centroid
        if not flo.buffer(200).contains(c): continue              # 本館の床の上だけ
        H = b[5] - b[2]
        L = max(b[3] - b[0], b[4] - b[1])
        out.append(dict(n=n.split('（')[0] or '棚', P=P, H=H, L=L, z0=b[2], c=c, full=n))
    return flo, out

def kagu_groups():
    import networkx as nx
    flo, K = kagu_list()
    G = nx.Graph(); G.add_nodes_from(range(len(K)))
    for i in range(len(K)):
        for j in range(i + 1, len(K)):
            if K[i]['n'] == K[j]['n'] and K[i]['P'].distance(K[j]['P']) < 30: G.add_edge(i, j)
    A = []
    for comp in nx.connected_components(G):
        ms = [K[i] for i in comp]; P = unary_union([m['P'] for m in ms]).convex_hull
        mr = P.minimum_rotated_rectangle; c = list(mr.exterior.coords)
        e = sorted([math.hypot(c[1][0] - c[0][0], c[1][1] - c[0][1]), math.hypot(c[2][0] - c[1][0], c[2][1] - c[1][1])], reverse=True)
        H = max(m['z0'] + m['H'] for m in ms) - min(m['z0'] for m in ms)
        A.append(dict(n=ms[0]['n'], k=len(ms), L=e[0], D=e[1], H=H, rect=mr, c=P.centroid))
    return flo, A

def kagu_class(a):
    if a['n'] in ('糸の衝立の脚', '糸の衝立の柱 30角 h1000', '糸の衝立の下の横木 30角', 'KAPLAの箱の縄の取っ手', 'KAPLAの箱のキャスター φ50', 'KAPLAの箱のふた'): return None
    if a['H'] >= 900 and a['L'] >= 1500 and a['D'] >= 250: return 'A'      # 間仕切りになる高さ・長さ
    if a['H'] >= 600 and a['L'] >= 1500: return 'B'                         # 腰の高さの長い棚・カウンター
    return None

def kagu_plan():
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    try: import fonts42
    except Exception:
        plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['pdf.fonttype'] = 42
    flo, A = kagu_groups()
    ang = laser.sheet_angle()
    ub = laser.to_sheet(flo, ang, (0, 0)).bounds
    off = (20 - ub[0], (594 - (ub[3] - ub[1])) / 2 - ub[1])
    ts = lambda g: affinity.translate(laser.to_sheet(g, ang, (0, 0)), *off)
    W_ = laser.assemble()
    sel = sorted([a for a in A if kagu_class(a)], key=lambda a: (kagu_class(a), -a['L']))
    for i, a in enumerate(sel, 1): a['id'] = f'F{i}'; a['cls'] = kagu_class(a)
    path = os.path.join(OUT, '15_本館の家具_配置図.pdf')
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4)); ax = fig.add_axes([0, 0, 1, 1])
        for gg in getattr(flo, 'geoms', [flo]):
            xs, ys = ts(gg).exterior.xy; ax.plot(xs, ys, color='0.75', lw=0.4)
        for R_ in W_['runs']:
            ln = ts(LineString([R_.A, R_.B])); xs, ys = ln.xy; ax.plot(xs, ys, color='tab:red', lw=1.0, alpha=0.5)
        for a in sel:
            xs, ys = ts(a['rect']).exterior.xy
            col = 'tab:blue' if a['cls'] == 'A' else 'tab:orange'
            ax.fill(xs, ys, color=col, alpha=0.45, lw=0.6, ec=col)
            q = ts(a['c']); ax.text(q.x, q.y, a['id'], fontsize=6, ha='center', va='center')
        ax.set_xlim(0, 841); ax.set_ylim(0, 594); ax.set_aspect('equal'); ax.axis('off')
        ax.text(20, 20, '本館の家具の候補（1/100、A1 に 100% で印刷すると模型と同じ大きさ）：青＝A 間仕切りになる棚（高さ 0.9 m 以上・長さ 1.5 m 以上）、橙＝B 腰の高さの長い棚（高さ 0.6 m 以上・長さ 1.5 m 以上）、赤い線＝今ある間仕切り（09）', fontsize=9)
        pdf.savefig(fig); plt.close(fig)
    return sel, path

if __name__ == '__main__':
    sel, path = kagu_plan()
    print(path)
    for a in sel:
        print(a['id'], a['cls'], a['n'], f"{a['L']/1000:.1f}×{a['D']/1000:.2f} h{a['H']/1000:.2f}", a['k'])
