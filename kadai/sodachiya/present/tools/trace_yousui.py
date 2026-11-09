"""松ヶ崎の用水の図（土木遺産のページ「宝ヶ池」の図、ユーザーが見つけた）をなぞって折れ線にする。
使い方：python3 trace_yousui.py <図の画像> <出力json>
出典：http://ksdobokuisan.stars.ne.jp/80_takaragaike/takaragaike.html
色：濃い青(51,85,153)＝川・水路の線、淡い青(153,213,255)＝川の面と池、桃(204,170,204)＝松ヶ崎の範囲"""
import sys, json
import numpy as np, cv2
from PIL import Image
from skimage.morphology import skeletonize

src, out = sys.argv[1], sys.argv[2]
im = np.array(Image.open(src).convert("RGB")).astype(int)
H, W = im.shape[:2]
col = lambda c, tol=30: (np.abs(im - np.array(c)).sum(2) < tol)
dark = col((51, 85, 153)).astype(np.uint8)
light = col((153, 213, 255)).astype(np.uint8)
pink = col((204, 170, 204), 60).astype(np.uint8)
# 凡例と、青い字（川の名前）を抜く（画素の箱）
light = cv2.morphologyEx(light, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))   # 池の中の字の穴を埋める
for x0, y0, x1, y1 in [(0, 0, 100, 62), (222, 22, 265, 45), (262, 173, 302, 192), (155, 243, 172, 258),
                       (149, 258, 165, 273), (139, 271, 155, 285), (175, 0, 230, 14)]:
    for m in (dark, light, pink):
        m[y0:y1, x0:x1] = 0


def lines_of(mask, minlen=5):
    sk = skeletonize(mask > 0)
    ys, xs = np.nonzero(sk)
    P = set(zip(xs.tolist(), ys.tolist()))
    N8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    nb = lambda p: [(p[0] + dx, p[1] + dy) for dx, dy in N8 if (p[0] + dx, p[1] + dy) in P]
    deg = {p: len(nb(p)) for p in P}
    seen, paths = set(), []
    for s in [p for p in P if deg[p] != 2] + [p for p in P if deg[p] == 2]:
        for n in nb(s):
            e = (min(s, n), max(s, n))
            if e in seen:
                continue
            seen.add(e)
            path, prev, cur = [s, n], s, n
            while deg.get(cur, 0) == 2:
                nx = [q for q in nb(cur) if q != prev]
                if not nx:
                    break
                e = (min(cur, nx[0]), max(cur, nx[0]))
                if e in seen:
                    break
                seen.add(e)
                path.append(nx[0]); prev, cur = cur, nx[0]
            paths.append(path)
    res = []
    for p in paths:
        if len(p) < minlen:
            continue
        a = cv2.approxPolyDP(np.array(p, np.float32).reshape(-1, 1, 2), 0.8, False).reshape(-1, 2)
        res.append(a.tolist())
    return res


def polys_of(mask, minarea=20):
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.approxPolyDP(c, 0.8, True).reshape(-1, 2).tolist() for c in cs if cv2.contourArea(c) >= minarea]


json.dump({"note": "松ヶ崎の用水の図をなぞった線（画素、左上が原点、北が上）。出典 ksdobokuisan.stars.ne.jp の「宝ヶ池」",
           "size": [W, H], "water_lines": lines_of(cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))), "water_fills": polys_of(light),
           "boundary": lines_of(pink, 3)}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print("ok", W, H)
