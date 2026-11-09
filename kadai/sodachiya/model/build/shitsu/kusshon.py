"""クッション（本館係、ユーザー 11-01 20:03：本読みスペースのクッション、ロフトのクッションをリアルな形に）。
四角いクッションが中身でふくらんだ形：上の面は中央で厚くふっくら、下の面は浅く（置くとつぶれる側）、縁はパイピングの細い丸い縁取り、
四隅は少しとがる（辺の中ほどを内へ少し反らせる）。布の柔らかい物なので閉じたメッシュ（自由な形の例外、一つ約360面、外向き）。
座標は mm。O は中心（下の面の平らな所から Hb 上）、E1・E2 はクッションの面の向き（幅 2a・2b）、E3 は上の面の向き。
"""
import math, numpy as np, rhino3dm as r


def outline(a, b, M=20, bow=0.035):
    """四隅から辺に沿って M 点（隅を含む、M は4の倍数）。辺の中ほどを内へ bow×半幅だけ反らす（隅が少しとがる）"""
    n = M // 4; P = []
    corners = [(a, b), (-a, b), (-a, -b), (a, -b)]
    for k in range(4):
        p0, p1 = np.array(corners[k], float), np.array(corners[(k + 1) % 4], float)
        mid = (p0 + p1) / 2; inward = -mid / np.linalg.norm(mid)
        for i in range(n):
            s = i / n; u = 2 * s - 1
            P.append(p0 + (p1 - p0) * s + inward * bow * min(a, b) * (1 - u * u))
    return np.array(P)


def cushion(O, E1, E2, E3, a, b, H, e=14.0, M=20, K=4):
    O, E1, E2, E3 = (np.asarray(x, float) for x in (O, E1, E2, E3))
    B = outline(a, b, M)
    Ht, Hb = 0.68 * H, 0.32 * H
    top = lambda s: e + (Ht - e) * (1 - s * s) ** 0.55
    bot = lambda s: -(e + (Hb - e) * (1 - s * s) ** 0.25)
    V, F = [], []
    def add(x, y, z): V.append(O + x * E1 + y * E2 + z * E3); return len(V) - 1
    it = add(0, 0, top(0)); ib = add(0, 0, bot(0))
    rt, rb = [], []
    for k in range(1, K + 1):
        s = k / K
        rt.append([add(*(B[j] * s), top(s)) for j in range(M)])
        rb.append([add(*(B[j] * s), bot(s)) for j in range(M)])
    bead = [add(*(B[j] * (1 + e / min(a, b) * 0.8)), (top(1) + bot(1)) / 2) for j in range(M)]
    for j in range(M):
        j1 = (j + 1) % M
        F.append((it, rt[0][j], rt[0][j1])); F.append((ib, rb[0][j1], rb[0][j]))
        for k in range(K - 1):
            F.append((rt[k][j], rt[k + 1][j], rt[k + 1][j1], rt[k][j1]))
            F.append((rb[k][j1], rb[k + 1][j1], rb[k + 1][j], rb[k][j]))
        F.append((rt[K - 1][j], bead[j], bead[j1], rt[K - 1][j1]))
        F.append((rb[K - 1][j1], bead[j1], bead[j], rb[K - 1][j]))
    # 向き：体積が負なら面を裏返す（外向き）
    Vn = np.array(V); vol = 0.0
    for f in F:
        tri = [f[0], f[1], f[2]] if len(f) == 3 else [f[0], f[1], f[2]]
        vol += np.dot(Vn[tri[0]], np.cross(Vn[tri[1]], Vn[tri[2]]))
        if len(f) == 4: vol += np.dot(Vn[f[0]], np.cross(Vn[f[2]], Vn[f[3]]))
    if vol < 0: F = [tuple(reversed(f)) for f in F]
    m = r.Mesh()
    for p in V: m.Vertices.Add(*map(float, p))
    for f in F:
        if len(f) == 3: m.Faces.AddFace(*f)
        else: m.Faces.AddFace(*f)
    m.Normals.ComputeNormals(); m.Compact()
    return m, Vn


def frame_flat(rot_deg, X0, Y0):
    """床に置いたクッション：面の向きを世界の X0・Y0（水平）から rot だけ回す"""
    t = math.radians(rot_deg); X0, Y0 = np.asarray(X0, float), np.asarray(Y0, float)
    E1 = math.cos(t) * X0 + math.sin(t) * Y0; E2 = -math.sin(t) * X0 + math.cos(t) * Y0
    E3 = np.cross(E1, E2)
    if E3[2] < 0: E2 = -E2; E3 = -E3
    return E1, E2, E3


def frame_lean(U, Vwall, lean_deg):
    """壁に立てかけたクッション：U は壁に沿う水平の向き、Vwall は壁へ向かう水平の向き。鉛直から lean だけ壁の側へ傾ける。E3 は部屋の側"""
    t = math.radians(lean_deg); U, Vw = np.asarray(U, float), np.asarray(Vwall, float)
    E2 = math.cos(t) * np.array([0, 0, 1.0]) + math.sin(t) * Vw
    E3 = np.cross(U, E2)
    if np.dot(E3, Vw) > 0: E3 = -E3
    return U, E2, E3
