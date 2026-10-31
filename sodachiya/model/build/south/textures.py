"""床の絵（テクスチャ）を毎回つくる（設計監修、10-31。本館係の項 20261031-1430、ユーザー：床を床に見せる）。

materials.py が呼ぶ。絵は決まった種（seed）から作るので、作り直すたびに同じ絵になる。継ぎ目なしで敷き詰められる（上下・左右がつながる）。
大きさは本当の寸法（data/materials.json の texture の tile、mm）。絵の横（列）＝板の幅の向き、縦（行）＝板の長さの向き。

- 杉の床板（sugi）：幅 135 の板を 16 列（2,160 mm）、長さ 1,820〜3,640 の乱尺を 7,280 mm でつなぐ。端の継ぎ目は隣の列と 300 以上ずらす。
  色は白太（淡いクリーム）から赤身（淡い桃色がかった茶）まで板ごとに少しずつ、源平（一枚に両方）も混ぜる。木目は細いまっすぐな筋を弱く、
  小さな節をまれに。継ぎ目は細い線（1 px＝2 mm を少し暗く）。無塗装・オイル仕上げの杉で、木目調の印刷のような強い模様にはしない
  （ユーザー：木目調は嫌い、素材に正直に）。
- 洗い出し（arai）：灰色のセメントの中に 3〜9 mm の玉砂利（灰・白・茶）、600 mm 角。
"""
import numpy as np
from PIL import Image

SUGI_BW = 64                                           # 板 1 枚の幅の px（135 mm → 約 2.1 mm/px）
SUGI_W, SUGI_L, SUGI_N = 2160.0, 7280.0, 16           # 幅の向き 16 枚×135、長さの向き
ARAI_MMPX = 0.6
ARAI_T = 600.0


def _smooth1d(rng, n, scale, amp):
    """長さ n の周期的なゆるい揺れ（scale px より長い波）"""
    k = np.fft.rfftfreq(n) * n
    spec = (rng.normal(size=k.size) + 1j * rng.normal(size=k.size)) * np.exp(-(k * scale / n) ** 2)
    spec[0] = 0
    s = np.fft.irfft(spec, n)
    return s / (np.abs(s).max() + 1e-9) * amp


def _cuts(rng, L, prev, first):
    """一列の端の継ぎ目（mm、周期 L）。隣の列（prev・first）と 300 以上ずらす"""
    for _ in range(2000):
        n = rng.choice([2, 3, 3, 3, 4])
        ls = rng.uniform(1820, 3640, n); ls = ls / ls.sum() * L
        if ls.min() < 1820 or ls.max() > 3640: continue
        c = (rng.uniform(0, L) + np.concatenate([[0], np.cumsum(ls)[:-1]])) % L
        ok = True
        for o in [x for x in (prev, first) if x is not None]:
            d = np.abs(c[:, None] - o[None, :]); d = np.minimum(d, L - d)
            if d.min() < 300: ok = False
        if ok: return np.sort(c)
    return np.sort(c)


def sugi(path, seed=1031):
    rng = np.random.default_rng(seed)
    bw = SUGI_BW; W = bw * SUGI_N; mmpx = SUGI_W / W              # 板 1 枚がちょうど bw px（2.11 mm/px）
    H = int(round(SUGI_L / mmpx)); Lr = H * mmpx                  # 長さの向きの本当の寸法（7,280 に近い px の整数倍）
    sap = np.array([228, 203, 162.0]); heart = np.array([201, 156, 114.0])
    img = np.zeros((H, W, 3))
    y = np.arange(H)[:, None] * mmpx
    xs = (np.arange(bw)[None, :] + 0.5) * mmpx                # 板の中の幅の位置（mm）
    cols, prev = [], None
    for j in range(SUGI_N):
        c = _cuts(rng, Lr, prev, cols[0] if j == SUGI_N - 1 and cols else None); cols.append(c); prev = c
    for j, c in enumerate(cols):
        x0 = j * bw
        seg = np.searchsorted(c, y[:, 0], side='right') % len(c)    # 行ごとの板の番号（周期の頭は最後の板の続き）
        for k in range(len(c)):
            rows = seg == k
            kind = rng.choice(['sap', 'heart', 'genpei', 'mid'], p=[0.3, 0.3, 0.25, 0.15])
            nr = int(rows.sum())
            wob = _smooth1d(rng, H, 300, rng.uniform(4, 10))[rows][:, None]      # 長さの向きのゆるい揺れ（波長 約 0.6 m〜）
            if kind == 'genpei':                                    # 一枚に白太と赤身（境はやわらかく、長さの向きに揺れる）
                b = rng.uniform(35, 100); side = rng.choice([-1, 1])
                t = 1 / (1 + np.exp(-side * (xs - b - 2.5 * wob) / 10.0)) * 0.5 + 0.15
            else:
                t = np.full((nr, bw), {'sap': rng.uniform(0.08, 0.25), 'heart': rng.uniform(0.5, 0.7), 'mid': rng.uniform(0.3, 0.45)}[kind])
                t = t + 0.04 * np.sin(xs / rng.uniform(20, 60) + wob / 6)
            lum = rng.normal(1.0, 0.025)
            base = sap * (1 - t[..., None]) + heart * t[..., None]          # (nr, bw, 3)
            # 木目：まっすぐな細い筋（年輪 4〜8 mm、晩材を少しだけ暗く、なめらかに）、長さの向きにごくゆるく揺れる
            sp = rng.uniform(4.0, 8.0); ph = rng.uniform(0, 1)
            r = (xs + 0.4 * wob) / sp + ph + 0.6 * np.sin(xs / rng.uniform(8, 20) + rng.uniform(0, 6.3))   # 年輪の間隔は一様でない
            late = 0.5 + 0.5 * np.cos(2 * np.pi * r)
            late = late ** 3
            grain = 1 - rng.uniform(0.03, 0.06) * late * (0.6 + 0.4 * t)
            streak = 1 + 0.012 * _smooth1d(rng, bw * 8, 6, 1.0)[::8][None, :bw]
            img[rows, x0:x0 + bw] = base * lum * grain[..., None] * streak[..., None]
            # まれに小さな節（φ8〜16、濃い茶、ぼかし）
            if rng.random() < 0.12:
                ry = rng.uniform(0, Lr); rx = rng.uniform(25, 110); rr = rng.uniform(4, 8)
                yy = np.where(rows)[0] * mmpx
                d = np.hypot((yy[:, None] - ry) / 1.6, xs - rx)
                kn = np.clip(1.4 - d / rr, 0, 1)[..., None]
                img[rows, x0:x0 + bw] = img[rows, x0:x0 + bw] * (1 - 0.45 * kn) + np.array([120, 82, 52.0]) * 0.45 * kn
        # 継ぎ目：長手（板の左の縁）と端
        img[:, x0] *= 0.80
        for cc in c:
            iy = int(round(cc / mmpx)) % H
            img[iy, x0:x0 + bw] *= 0.80
    img += rng.normal(0, 1.2, img.shape)                           # 細かいざらつき
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').save(path, quality=88, optimize=True)
    return SUGI_W, Lr


def arai(path, seed=1032):
    from scipy import ndimage
    rng = np.random.default_rng(seed)
    N = int(round(ARAI_T / ARAI_MMPX))
    lab = np.zeros((N, N), np.int32); hgt = np.zeros((N, N))
    cement = np.array([150, 146, 138.0])
    pal = np.array([[120, 120, 118], [150, 148, 144], [178, 176, 170], [206, 204, 198], [222, 220, 214],
                    [168, 150, 128], [140, 120, 100], [98, 96, 96], [190, 178, 160]], float)
    cols = [cement]
    n = int(ARAI_T ** 2 / 23 * 1.5)                                # 重ならないように置くので、面積のおよそ 6〜7 割が石になる
    for i in range(1, n + 1):
        r = rng.uniform(1.5, 4.5) / ARAI_MMPX; e = rng.uniform(0.65, 1.0); a = rng.uniform(0, np.pi)
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        R = int(r) + 2
        x0, y0 = int(cx) - R, int(cy) - R
        px = np.arange(x0, x0 + 2 * R + 1); py = np.arange(y0, y0 + 2 * R + 1)
        dx = px[None, :] + 0.5 - cx; dy = py[:, None] + 0.5 - cy
        u = (dx * np.cos(a) + dy * np.sin(a)) / r; v = (-dx * np.sin(a) + dy * np.cos(a)) / (r * e)
        q = u * u + v * v; msk = q <= 1
        iy = np.broadcast_to(py[:, None] % N, msk.shape)[msk]; ix = np.broadcast_to(px[None, :] % N, msk.shape)[msk]
        free = lab[iy, ix] == 0                                    # 先に置いた石の上には重ねない
        if free.sum() < 0.8 * msk.sum(): continue                  # 大きく欠ける石は置かない（石どうしが溶け合って見えないように）
        lab[iy[free], ix[free]] = i
        hgt[iy[free], ix[free]] = np.sqrt(np.clip(1 - q[msk][free], 0, 1)) * r * e * 0.6   # 石の頭（ドーム）
        cols.append(pal[rng.integers(len(pal))] * rng.normal(1, 0.05))
    cols += [cement] * (n + 1 - len(cols))
    cols = np.array(cols)
    img = cols[lab]
    stone = (lab > 0).astype(float)
    hy, hx = np.gradient(ndimage.gaussian_filter(hgt, 0.7, mode='wrap'))
    nz = 1 / np.sqrt(hx ** 2 + hy ** 2 + 1)
    Lx, Ly, Lz = -0.35, -0.35, 0.87                                # 左上から
    lam = (-hx * Lx - hy * Ly + Lz) * nz
    shade = np.where(stone > 0, 0.72 + 0.34 * lam, 1.0)
    ao = 1 - 0.18 * (1 - stone) * ndimage.gaussian_filter(stone, 1.5, mode='wrap')   # 石の際のセメントの陰
    img = img * (shade * ao)[..., None]
    img += rng.normal(0, 3, img.shape) * (1 - stone[..., None] * 0.6)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').save(path, quality=88, optimize=True)
    return ARAI_T, ARAI_T


DATA_DIR = None          # data/ の場所（materials.py が素材の表の場所から入れる。作り直しはスクリプトを /tmp に写して走らせるので __file__ からは引けない）


def sugi_a(path):
    """10-31 ユーザー：杉の床板は本館係の絵（data/tex/sugi_floor.png、2400×2400 mm、板は絵の横向き、幅150の乱尺）を使う。
    ここでの決まり（絵の横＝板の幅の向き、縦＝板の長さの向き）に合わせて90°回し、軽い JPEG にして書く"""
    import os
    from PIL import Image
    src = os.path.join(DATA_DIR or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data'), 'tex', 'sugi_floor.png')
    im = Image.open(src).convert('RGB').transpose(Image.Transpose.ROTATE_90)
    im.save(path, quality=88, optimize=True)
    return 2400.0, 2400.0


MAKERS = {'sugi': sugi_a, 'sugi_gen': sugi, 'arai': arai}
FILES = {'sugi': 'sugi_floor.jpg', 'arai': 'araidashi.jpg'}


if __name__ == '__main__':
    import sys
    for k, f in MAKERS.items(): f(sys.argv[1] + '/' + FILES[k])
