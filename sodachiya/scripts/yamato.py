# スギの大和張り（外構の塀と木戸、ユーザー 10-27：外壁と同じ）。data/approachA.json の YAMATO を読み、平面の線と 3dm の箱を作る。
# 縦の板 board_w×board_t を胴縁（厚み rail.t）の表と裏に交互に pitch おき。どちらの面も同じ顔。
import os, json
import numpy as np
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Y = json.load(open(os.path.join(_ROOT, "data", "approachA.json"), encoding="utf-8"))["YAMATO"]

def _frame(p0, p1):
    p0, p1 = np.array(p0, float), np.array(p1, float); L = float(np.linalg.norm(p1 - p0))
    t = (p1 - p0) / L; n = np.array([-t[1], t[0]]); return p0, t, n, L

def bays(p0, p1, posts=()):
    """柱で区切った張りの区間 [(q0, q1)]。posts＝[(xy, 半径)]：線から半径＋0.05 以内の柱で線を切り、柱の面（半径＋0.005）で止める。
    板と胴縁は柱の間に納める（10-27：板が柱にめり込んでいた）。柱の位置で割りは柱から始め直す。"""
    p0, t, n, L = _frame(p0, p1); cuts = []
    for xy, r in posts:
        v = np.array(xy, float) - p0; a = float(v @ t); d = abs(float(v @ n))
        if d < r + 0.05 and -r < a < L + r: cuts.append((a - r - 0.005, a + r + 0.005))
    segs, a0 = [], 0.0
    for c0, c1 in sorted(cuts):
        if c0 > a0: segs.append((a0, c0))
        a0 = max(a0, c1)
    if a0 < L: segs.append((a0, L))
    return [(tuple(p0 + t * a), tuple(p0 + t * b)) for a, b in segs if b - a > Y["board_w"] * 0.6]

def board_centers(p0, p1):
    """[(中心 xy, 表=+1／裏=-1)]。板の端が線の端からはみ出さないように並べる。"""
    p0, t, n, L = _frame(p0, p1); w = Y["board_w"]
    if L < w: return [(p0 + t * L / 2, 1)]
    k = int((L - w) // Y["pitch"]) + 1; a0 = (L - (w + (k - 1) * Y["pitch"])) / 2 + w / 2
    return [(p0 + t * (a0 + i * Y["pitch"]), 1 if i % 2 == 0 else -1) for i in range(k)]

def boards(p0, p1):
    """板の外形 [4点 xy]。"""
    _, t, n, _ = _frame(p0, p1); off = (Y["rail"]["t"] + Y["board_t"]) / 2; bw, bt = Y["board_w"] / 2, Y["board_t"] / 2
    out = []
    for c, sgn in board_centers(p0, p1):
        m = c + n * off * sgn
        out.append([tuple(m - t * bw - n * bt), tuple(m + t * bw - n * bt), tuple(m + t * bw + n * bt), tuple(m - t * bw + n * bt)])
    return out

def rail(p0, p1):
    p0, t, n, L = _frame(p0, p1); h = Y["rail"]["t"] / 2
    return [tuple(p0 - n * h), tuple(p0 + t * L - n * h), tuple(p0 + t * L + n * h), tuple(p0 + n * h)]

def plan(line, p0, p1, color, z=7.6, lw=0.9, posts=()):
    """平面：表と裏の板を短い太線で（1/200 で破線の二重線に見える）。line(pts, lw=, c=, z=)。柱の間に納める。"""
    line([tuple(p0), tuple(p1)], lw=0.3, c=color, z=z - 0.1)
    for q0, q1 in bays(p0, p1, posts):
        _, t, n, _ = _frame(q0, q1); off = (Y["rail"]["t"] + Y["board_t"]) / 2; bw = Y["board_w"] / 2
        for c, sgn in board_centers(q0, q1):
            m = c + n * off * sgn; line([tuple(m - t * bw), tuple(m + t * bw)], lw=lw, c=color, z=z)

def to3dm(slab, p0, p1, lay, h=None, foot=None, posts=()):
    """slab(pts, z0, t, lay) で板と胴縁を箱に。h は塀の高さ（既定 YAMATO.h）。posts の柱の間に納める（胴縁は柱の面で止める＝柱に留める）。"""
    h = h or Y["h"]; foot = Y["foot"] if foot is None else foot; n = 0
    for q0, q1 in bays(p0, p1, posts):
        for z in Y["rail"]["z"]:
            if z + Y["rail"]["w"] < h: slab(rail(q0, q1), z, Y["rail"]["w"], lay); n += 1
        for b in boards(q0, q1): slab(b, foot, h - foot, lay); n += 1
    return n
