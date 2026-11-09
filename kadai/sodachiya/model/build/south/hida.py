"""遊戯室のひだ（西の壁のくぼみ・北西の丸いベンチ）の平面形を、壁の面にそろえて作る（10-31、ユーザー：居場所が斜めっている）。
西の壁（u 約23.7〜40.6）はまっすぐな線で、本館の背骨の弧の放射（u 一定の線）とは約6.5°ずれている。前は u・w の長方形
（放射の線と w 一定の弧）で作っていたので、壁に対して回って見え、背は壁から片側で離れていた。
ここでは壁の内面の線の上に、壁に平行・直角の長方形を置く。丸いベンチの両端は、壁（弧）の法線で切る。
使う所：scripts/play3d.py（取り込み用ファイル）・model/build/south/add_play.py
"""
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from uv import xy, uv

T_WALL = 150.0          # 外皮の線から壁の内面まで（mm）


def west_face(WS):
    """西の壁のまっすぐな面：外皮の線の南の端 A・北の端 B、北向きの単位接線 t、室内向きの単位法線 n"""
    cs = list(WS.exterior.coords); best = None
    for p, q in zip(cs, cs[1:]):
        if uv(*p)[1] > -10 or uv(*q)[1] > -10: continue
        L = float(np.hypot(q[0] - p[0], q[1] - p[1]))
        if best is None or L > best[0]: best = (L, np.array(p, float), np.array(q, float))
    _, a, b = best
    if uv(*a)[0] > uv(*b)[0]: a, b = b, a
    t = (b - a) / np.linalg.norm(b - a); n = np.array([-t[1], t[0]])
    if not WS.contains(Point(*((a + b) / 2 + n * 100))): n = -n
    return a, b, t, n


def niche_frame(WS, u):
    """u の放射の線と西の壁の内面の交点 F（mm）と、壁の接線 t・法線 n"""
    a, b, t, n = west_face(WS)
    f0 = a + n * T_WALL
    p0 = np.array(xy(u, -0.9)); p1 = np.array(xy(u, -30.0)); d = p1 - p0
    # f0 + s t = p0 + k d
    s, k = np.linalg.solve(np.c_[t, -d], p0 - f0)
    return f0 + s * t, t, n


def rect(F, t, n, s0, s1, d0, d1):
    """壁にそろえた長方形：接線の向きに s0〜s1、壁の内面から室内へ d0〜d1（mm）"""
    return Polygon([F + t * s0 + n * d0, F + t * s1 + n * d0, F + t * s1 + n * d1, F + t * s0 + n * d1])


def niche_parts(WS, ua, ub, N_, depth):
    """くぼみ（座・天板・袖板2枚）の平面形と高さ：[(形, z0, z1)]（mm）。真ん中は柱のあいだの真ん中（u の中点）、幅は ub−ua（m、実の長さ）"""
    F, t, n = niche_frame(WS, (ua + ub) / 2)
    h = (ub - ua) * 500.0; b = N_['board'] * 1000; D = depth * 1000
    out = [(rect(F, t, n, -h, h, 0, N_['seat_d'] * 1000), 0.0, N_['seat_h'] * 1000),
           (rect(F, t, n, -h - b, h + b, 0, D), N_['top_h'] * 1000, (N_['top_h'] + N_['board']) * 1000)]
    for s0 in (-h - b, h):
        out.append((rect(F, t, n, s0, s0 + b, 0, D), 0.0, N_['top_h'] * 1000))
    return out


def _cut(ext, u, toward_north):
    """外皮の内面の線 ext の上で u の放射が当たる所 P と、その点の接線（ベンチの側へ向く）・法線"""
    ln = LineString([xy(u, -0.9), xy(u, -30)]); x = ln.intersection(ext)
    pts = [x] if x.geom_type == 'Point' else list(getattr(x, 'geoms', []))
    P = min(pts, key=lambda p: uv(p.x, p.y)[1])                 # いちばん西
    s = ext.project(P); q0 = np.array(ext.interpolate(s - 80).coords[0]); q1 = np.array(ext.interpolate(s + 80).coords[0])
    tg = (q1 - q0) / np.linalg.norm(q1 - q0)
    Pa = np.array(P.coords[0])
    if (uv(*(Pa + tg * 100))[0] > uv(*Pa)[0]) != toward_north: tg = -tg
    return Pa, tg


def _half(Pa, tg, L=6000.0):
    nr = np.array([-tg[1], tg[0]])
    return Polygon([Pa - nr * L, Pa + nr * L, Pa + nr * L + tg * L, Pa - nr * L + tg * L])


def round_bench(WSi, u0, u1, depth, box, avoid=None, gap=20.0):
    """北西の丸い角のベンチ：壁の内面（WSi の縁）に沿う幅 depth（mm）の帯を、両端は壁の法線で切る。
    avoid（柱の形）があれば、南の端をそれから gap 離れるまで北へずらす"""
    band = WSi.difference(WSi.buffer(-depth, join_style=1)).intersection(box)
    ext = WSi.exterior
    Pb, tb = _cut(ext, u1, False)
    uu = u0
    for _ in range(80):
        Pa, ta = _cut(ext, uu, True)
        g = band.intersection(_half(Pa, ta)).intersection(_half(Pb, tb))
        if avoid is None or g.distance(avoid) >= gap: break
        uu += 0.01
    if g.geom_type != 'Polygon':
        g = max(getattr(g, 'geoms', [g]), key=lambda x: x.area)
    return g, uu
