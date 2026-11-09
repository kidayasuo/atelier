"""杉の床板（無垢、t30）の絵：data/tex/sugi_floor.png（本館係、ユーザー 10-31「床を床に」）。
実寸 2400×2400 mm の一枚で、上下左右につながる（繰り返しても継ぎ目が見えない）。板の向きは絵の横（X）。
- 板の幅 150（16 列でちょうど 2400）。乱尺：一列の中の板（2400、1600＋800、1500＋900、1200＋1200）は
  一列の周期 2400 で閉じ（1820＋580 も）、端の継ぎ目は隣の列と 300 以上ずらす（上下の繰り返しの端の列どうしも）。
- 木目は板ごとに丸太から挽いた形で：髄からの距離 R＝√(y'²＋d(x)²)（y'：髄の横の位置、d：髄から板の面までの深さ、
  丸太の細りとゆるいうねりで x に沿って変わる）。年輪の幅 3.5〜6 mm、晩材の細い帯を少し暗く（板目の山形が自然に出る）。
  赤身と白太も同じ R で：心材の半径より内は淡い赤褐色、外は淡い黄褐色（源平が素直に出る）。強さは控えめ。
- 継ぎ目は細く（約 1 mm）少し暗く。色の平均は素材の色 [212,178,132] のあたり。
python3 scripts/tex_sugi_floor.py [出力 PNG]   （乱数の種は固定）"""
import os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'tex', 'sugi_floor.png')
SEED = 20261031
TILE = 2400.0                 # mm
PX = 1.5                      # px／mm
N = int(TILE * PX)            # 3600
BW = 150.0                    # 板の幅
ROWS = int(TILE / BW)         # 16
BH = int(BW * PX)             # 225 px
SETS = [(2400,), (1600, 800), (1500, 900), (1200, 1200), (1820, 580)]
P_SET = [0.30, 0.25, 0.20, 0.15, 0.10]
SHIRO = np.array([226, 198, 152], float)    # 白太（淡い黄褐色）
AKA = np.array([202, 154, 112], float)      # 赤身（薄い赤褐色）
BASE = np.array([212, 178, 132], float)    # 素材「杉の床板 t30」の色（data/materials.json）
rng = np.random.default_rng(SEED)


def rows_layout():
    """各列の板の (始まり mm, 長さ mm)。端の継ぎ目は隣の列（上下の繰り返しも）と 300 以上離す"""
    def joints(row):
        return [s % TILE for s, _ in row]
    def far(a, b):
        return all(min(abs(x - y), TILE - abs(x - y)) >= 300 for x in a for y in b)
    for _ in range(2000):
        out = []
        for k in range(ROWS):
            for _t in range(200):
                lens = list(SETS[rng.choice(len(SETS), p=P_SET)])
                rng.shuffle(lens)
                x0 = float(rng.integers(0, int(TILE / 10))) * 10
                row, x = [], x0
                for L in lens:
                    row.append((x, float(L))); x += L
                if not out or far(joints(row), joints(out[-1])):
                    out.append(row); break
            else:
                break
        if len(out) == ROWS and far(joints(out[0]), joints(out[-1])):
            return out
    raise SystemExit('乱尺の割り付けが決まらない')


def wave(x, amp, lmin, lmax, n=4):
    """ゆるいうねり（正弦の和、板ごとに乱数）"""
    y = np.zeros_like(x)
    for _ in range(n):
        lam = rng.uniform(lmin, lmax)
        y += rng.uniform(0.3, 1.0) * np.sin(2 * np.pi * x / lam + rng.uniform(0, 2 * np.pi))
    return amp * y / n


def board(L):
    """一枚の板の絵（BH × L px、RGB float）。座標は板の中（x：長さ、y：幅、mm）"""
    W = int(round(L * PX))
    x = (np.arange(W) + 0.5) / PX
    y = (np.arange(BH) + 0.5) / PX - BW / 2
    X, Y = np.meshgrid(x, y)
    # 丸太の中の板の位置
    y0 = rng.normal(0, 45) if rng.random() < 0.7 else rng.uniform(-200, 200)   # 髄の横の位置（板の中なら板目の山形、遠いと柾目に近い筋）
    d0 = rng.uniform(20, 90)                          # 髄から板の面まで
    taper = rng.uniform(0.006, 0.016) * rng.choice([-1, 1])   # 丸太の細り（板目の山形）
    tilt = np.deg2rad(rng.uniform(-0.6, 0.6))         # 木目の向きのわずかな傾き
    yy = Y - y0 + X * np.tan(tilt) + wave(X, rng.uniform(1.0, 4.0), 300, 1500)
    d = np.maximum(3.0, d0 + taper * (X - L / 2) + wave(X, rng.uniform(1.0, 4.0), 400, 2000))
    R = np.sqrt(yy ** 2 + d ** 2)
    rw = rng.uniform(3.5, 6.0)                        # 年輪の幅（年ごとに少し揺らす）
    ph = R / rw + wave(R, 0.9, 15, 60, 3) + gaussian_filter(rng.normal(0, 1, R.shape), (1.5, 25)) * 0.15
    f = ph - np.floor(ph)
    late = np.clip((f - 0.62) / 0.22, 0, 1) * np.clip((1.0 - f) / 0.10, 0, 1)   # 晩材：早材からゆるく濃くなり、外へ切れる
    late = gaussian_filter(late, (0.8, 2.0))
    k_late = rng.uniform(0.04, 0.08)                  # 木目の強さ（板ごと、控えめ）
    # 赤身と白太
    Rh = rng.uniform(10, 130)                         # 心材の半径
    heart = np.clip((Rh - R) / 30.0 + 0.5, 0, 1)
    tint = rng.uniform(0.35, 0.75)                    # 赤身の濃さ（控えめ）
    col = SHIRO[None, None, :] * (1 - heart[..., None] * tint) + AKA[None, None, :] * (heart[..., None] * tint)
    col *= rng.uniform(0.965, 1.035)                    # 板ごとの明るさ
    shade = 1.0 - k_late * late * (1.0 + 0.3 * heart)
    # 繊維の細かいむら（長さの向きに伸ばしたノイズ）
    fib = gaussian_filter(rng.normal(0, 1, R.shape), (0.7, 12)) * 0.018
    shade = shade * (1.0 + fib)
    img = col * shade[..., None]
    # 継ぎ目：板の周り 1 px を暗く、次の 1 px を少し（約 1.3 mm の細い線）
    edge = np.ones((BH, W))
    for a, b in ((0, 0.80), (1, 0.93)):
        edge[a, :] = np.minimum(edge[a, :], b); edge[BH - 1 - a, :] = np.minimum(edge[BH - 1 - a, :], b)
        edge[:, a] = np.minimum(edge[:, a], b); edge[:, W - 1 - a] = np.minimum(edge[:, W - 1 - a], b)
    return img * edge[..., None]


def main():
    out = np.zeros((N, N, 3), float)
    for k, row in enumerate(rows_layout()):
        for x0, L in row:
            b = board(L)
            cols = (int(round(x0 * PX)) + np.arange(b.shape[1])) % N
            out[k * BH:(k + 1) * BH, cols, :] = b
    out *= BASE / out.reshape(-1, 3).mean(0)          # 平均を素材の色に合わせる（レンダリングの見えの明るさを変えない）
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img = Image.fromarray(np.clip(out + rng.uniform(-0.5, 0.5, out.shape), 0, 255).astype(np.uint8), 'RGB')
    img.save(OUT, optimize=True)
    print(OUT, img.size, '平均の色', [round(float(c)) for c in out.reshape(-1, 3).mean(0)])


if __name__ == '__main__':
    main()
