"""絵本の通りの本棚（本館係、ユーザー 11-01 20:03：棚を壁に付ける・本棚をリアルに）。区画は data/hondana.json。
  背差しの棚（sesashi）：奥行き0.30・h1.2。側板・天板・底板・棚板2枚は t20、背板 t9、台輪 h60。3段に絵本を背を見せて並べる
    （一冊ずつ薄い直方体、高さ0.20〜0.32・厚さ0.010〜0.022、段ごとに詰め方を変え、ところどころ空き、段の端の一冊は側板にもたれて斜め）。
  表紙を見せる斜めの台（mendai）：奥行き0.35・h1.2。前に18°傾いた板 t15 を3段、各段の下に本の止まる桟（棚 t20＋前の縁 h50）、
    表紙を見せた絵本（0.22〜0.27×0.26〜0.30・厚さ8）を2〜3冊ずつ立てかける。板の後ろの収納は作らない。
形はみな katachi の箱（押し出し）。棚は家具のレイヤー、本は絵本のレイヤー（物ごとに数色から、乱数の種は固定）。
区画は柱間の弦（長さ1 m 以下、弧との差 0.6 mm 以下）にそろえた直線の箱。
"""
import math, random, numpy as np
import katachi as K

BOOK_COLS = [(196, 74, 58), (222, 168, 64), (86, 128, 160), (110, 146, 92), (232, 220, 196), (150, 96, 140),
             (70, 82, 110), (208, 120, 96), (164, 180, 120), (240, 200, 150)]


def _bx(o, A, B, C, sa, sb, sc):
    """o から A に sa、B に sb、C に sc の直方体（A・B・C は直交の単位）"""
    A, B, C = (np.asarray(x, float) for x in (A, B, C))
    if np.dot(np.cross(A, B), C) > 0: return K.hako(o, A, B, sa, sb, sc)
    return K.hako(o, B, A, sb, sa, sc)


def build(m, W, J, li_shelf, li_book, seed=20261101):
    rng = random.Random(seed)
    vb, H = J['v_back'], J['h'] * 1000
    nb = 0
    for typ, u0, u1 in J['bays']:
        p0 = np.r_[W(u0, vb), 0.0]; p1 = np.r_[W(u1, vb), 0.0]
        X = p1 - p0; w = float(np.linalg.norm(X)); X /= w
        Z = np.array([0, 0, 1.0]); Y = np.cross(Z, X)
        if np.dot(np.r_[W(u0, vb + 1) - W(u0, vb), 0.0], Y) < 0: Y = -Y                 # Y は部屋の側（v の増える向き）
        D = J['depth'][typ] * 1000
        P = lambda x, y, z: p0 + x * X + y * Y + z * Z
        box = lambda x0, x1, y0, y1, z0, z1, li=li_shelf, col=None, name=None: K.add(m, _bx(P(x0, y0, z0), X, Y, Z, x1 - x0, y1 - y0, z1 - z0), li, col, name)
        t = 20.0; nm = '本棚（背差し）' if typ == 'sesashi' else '本棚（面陳の斜めの台）'
        box(0, t, 0, D, 0, H, name=nm + 'の側板'); box(w - t, w, 0, D, 0, H, name=nm + 'の側板')
        box(t, w - t, 0, D, H - t, H, name=nm + 'の天板')
        box(t, w - t, 0, 9, 80, H - t, name=nm + 'の背板')
        box(t, w - t, D - 50, D - 30, 0, 60, name=nm + 'の台輪')
        box(t, w - t, 9, D, 60, 80, name=nm + 'の底板')
        if typ == 'sesashi':
            clear = (H - t - 80 - 2 * t) / 3
            zs = [80 + k * (clear + t) for k in range(3)]
            for z in zs[1:]: box(t, w - t, 9, D, z - t, z, name=nm + 'の棚板')
            for z in zs:                                                       # 一段の本
                x = t + 2.0; xe = w - t - 2.0; fill = rng.uniform(0.55, 0.85) * (xe - x)
                gap_at = {rng.randrange(4, 30)} if rng.random() < 0.6 else set()
                k = 0; used = 0.0
                while True:
                    th = rng.uniform(10, 22); hh = rng.uniform(200, min(320, clear - 12)); dd = rng.uniform(170, min(250, D - 25))
                    if used + th > fill or x + th > xe: break
                    if k in gap_at: x += rng.uniform(40, 110)
                    if x + th > xe: break
                    col = rng.choice(BOOK_COLS)
                    box(x, x + th, 14, 14 + dd, z, z + hh, li_book, col, '絵本（背差し）'); nb += 1
                    x += th + 0.5; used += th; k += 1
                r_ = xe - x                                                     # 段の端：側板にもたれて斜めの一冊
                th = rng.uniform(10, 16); hh = rng.uniform(220, min(300, clear - 12)); dd = rng.uniform(170, min(230, D - 25))
                if 45 < r_ and r_ - 3 > th:
                    # t·cos a + h·sin a = r − 3 を a について解く
                    R_ = math.hypot(th, hh); ph = math.atan2(th, hh)
                    s = min(1.0, (r_ - 3) / R_); a = math.asin(s) - ph
                    if 0.05 < a < 0.7:
                        A = np.cos(a) * X - np.sin(a) * Z; C = np.sin(a) * X + np.cos(a) * Z
                        o = P(x + 1.0, 14, z + th * math.sin(a))
                        K.add(m, _bx(o, A, Y, C, th, dd, hh), li_book, rng.choice(BOOK_COLS), '絵本（もたれた一冊）'); nb += 1
        else:
            th_ = math.radians(18.0); T = -math.sin(th_) * Y + math.cos(th_) * Z       # 板の上向き（壁の側へ傾く）
            Nout = np.cross(X, T)
            if np.dot(Nout, Y) < 0: Nout = -Nout                                        # 板の表（部屋の側・上）
            yf = D - 60.0
            for zb in (80.0, 450.0, 820.0):
                box(t, w - t, yf - 20, D - 20, zb, zb + 20, name=nm + 'の桟')           # 本の止まる棚
                box(t, w - t, D - 40, D - 20, zb + 20, zb + 50, name=nm + 'の桟の縁')
                ob = P(t, yf, zb + 25)
                K.add(m, _bx(ob, X, T, -Nout, w - 2 * t, 330, 15), li_shelf, None, nm + 'の傾いた板')
                n = rng.choice([2, 3, 3]); ws = [rng.uniform(220, 270) for _ in range(n)]
                sp = (w - 2 * t - sum(ws)) / (n + 1)
                x = t + sp * rng.uniform(0.5, 1.0)
                for bw in ws:
                    bh = rng.uniform(260, 300)
                    K.add(m, _bx(ob + (x - t) * X + 1.0 * Nout, X, T, Nout, bw, bh, 8), li_book, rng.choice(BOOK_COLS), '絵本（表紙）'); nb += 1
                    x += bw + sp
    return nb
