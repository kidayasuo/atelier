"""課題の敷地図（敷地図.pdfの2つ目の画像、課題の地図）から文字と敷地の線を抜いて線をなぞり、3dmの座標（m）の折れ線にする。
使い方：python3 trace_kadai_map.py <敷地図.pdf> <出力json>
（ユーザー、10-24：周辺の道路は課題の地図をクリーンアップして使う。不正確だが与えられた敷地にぴったり、北の用水路が波線で描かれている）"""
import sys, json
import numpy as np, cv2, fitz
from skimage.morphology import skeletonize

src, out = sys.argv[1], sys.argv[2]
d = fitz.open(src)
pix = fitz.Pixmap(d, 11)                                 # 課題の地図（1506×1412）
if pix.colorspace.n != 3:
    pix = fitz.Pixmap(fitz.csRGB, pix)
img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
H, W = g.shape

# 敷地の5つの角（地図の丸、画素）と3dmの座標（m）
PX = {"N": (891.5, 212.5), "E": (1181.5, 593.5), "S": (775.5, 929.5), "SW": (714.5, 847.5), "NW": (676.5, 386.5)}
M3 = {"N": (0.0, 0.0), "E": (34.86, -43.83), "S": (-14.44, -83.04), "SW": (-21.91, -73.65), "NW": (-25.83, -20.54)}
A = np.array([[x, y, 1] for x, y in PX.values()])
B = np.array(list(M3.values()))
T, res, *_ = np.linalg.lstsq(A, B, rcond=None)
err = np.linalg.norm(A @ T - B, axis=1)

ink = (cv2.GaussianBlur(g, (3, 3), 0) < 215).astype(np.uint8)
# 文字・方位・寸法（画素の箱）
BOXES = [(367, 112, 750, 173), (60, 0, 170, 155), (700, 268, 800, 340), (500, 298, 660, 356), (640, 282, 708, 368), (618, 356, 662, 380),
         (1015, 350, 1092, 438), (792, 545, 992, 596), (500, 530, 612, 580), (612, 520, 660, 588), (646, 584, 700, 603), (898, 718, 992, 798),
         (718, 830, 790, 902), (738, 918, 792, 962)]
for x0, y0, x1, y1 in BOXES:
    ink[y0:y1, x0:x1] = 0
cv2.line(ink, (635, 505), (639, 592), 1, 3)                           # 「公道6m」の文字の下の道の端をつなぐ
# 敷地の線（一点鎖線）と角の丸
order = ["N", "E", "S", "SW", "NW", "N"]
mask = np.zeros_like(ink)
for a, b in zip(order[:-1], order[1:]):
    cv2.line(mask, tuple(int(v) for v in PX[a]), tuple(int(v) for v in PX[b]), 1, 15)
for v in PX.values():
    cv2.circle(mask, tuple(int(t) for t in v), 17, 1, -1)
ink[mask > 0] = 0
ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
sk = skeletonize(ink > 0).astype(np.uint8)

# 骨格を折れ線に（端点・分かれ目で切る）
ys, xs = np.nonzero(sk)
P = set(zip(xs.tolist(), ys.tolist()))
N8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
nb = lambda p: [(p[0] + dx, p[1] + dy) for dx, dy in N8 if (p[0] + dx, p[1] + dy) in P]
deg = {p: len(nb(p)) for p in P}
seen_e = set()
paths = []
starts = [p for p in P if deg[p] != 2] + [p for p in P if deg[p] == 2]
for s in starts:
    for n in nb(s):
        e = (min(s, n), max(s, n))
        if e in seen_e:
            continue
        path = [s, n]
        seen_e.add(e)
        cur, prev = n, s
        while deg.get(cur, 0) == 2:
            nxt = [q for q in nb(cur) if q != prev]
            if not nxt:
                break
            q = nxt[0]
            e = (min(cur, q), max(cur, q))
            if e in seen_e:
                break
            seen_e.add(e)
            path.append(q)
            prev, cur = cur, q
        paths.append(path)
lines = []
for p in paths:
    if len(p) < 6:
        continue
    a = np.array(p, np.float32).reshape(-1, 1, 2)
    ap = cv2.approxPolyDP(a, 1.2, False).reshape(-1, 2)
    m = np.c_[ap, np.ones(len(ap))] @ T
    lines.append(np.round(m, 3).tolist())
json.dump({"note": "課題の敷地図（敷地図.pdfの2つ目の画像）をなぞった線。文字・方位・寸法・敷地の一点鎖線は抜いた。敷地の5つの角でアフィン変換（3dmのm）",
           "fit_err_m": [round(float(x), 3) for x in err], "m_per_px": float(np.sqrt(abs(np.linalg.det(T[:2])))),
           "lines": lines}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
cv2.imwrite(out.replace(".json", "_ink.png"), 255 - ink * 255)
print(f"折れ線 {len(lines)}、角のずれ {np.round(err, 2)} m、1画素 {np.sqrt(abs(np.linalg.det(T[:2]))):.3f} m")
