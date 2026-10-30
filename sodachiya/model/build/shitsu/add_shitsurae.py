"""本館内のしつらえ（2026-10-21、別チャットの平面図 plan01／plan02／plan04 から）を 3dm に入れる。
平面図スクリプトを P(u,v) 恒等で実行して図形を (u, v)[m] で取り出し（capture.py）、
呼び出し元の行番号ごとに高さを与えて立ち上げる。
  u：南の妻（架構 1、旧 19）から北へ、背骨 r=205 m に沿った長さ [m]
  v：背骨（西の柱の列 r=205 m）から東へ [m]（1.6＝一本の線、12＝東の柱の列、13.5＝ガラス戸、15＝軒先）
高さは FL±0 基準 [mm]（受け取り土間・地面は −300、外縁側・あまのがわは −150）。
python3 -I add_shitsurae.py SCRIPTS_DIR IN.3dm OUT.3dm"""
import sys, math, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/shitsu')
from capture import capture, prep
from shapely.geometry import Polygon as SP, box as sbox, LineString
SCR, IN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

C = np.array([194645.51027008, -41347.80985094])
TH19 = math.radians(-173.3258) + 2 * math.pi
def W(u, v):                       # (u,v)[m] → 世界座標 [mm]
    a = TH19 - u / 205.0; rr = (205.0 - v) * 1000.0
    return C + rr * np.array([math.cos(a), math.sin(a)])
def ztop_v(v): rr = (205.0 - v) * 1000; return 3000 + (rr - 193000) / 12.0 + 167.0
ROOF_IN = lambda v: ztop_v(v) - 250          # 屋根の下面のおよそ

m = r.File3dm.Read(IN)
def layer(name, rgb, visible=True):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (rgb[0], rgb[1], rgb[2], 255); L.Visible = visible
    return m.Layers.Add(L)
def attr(li, col=None):
    a = r.ObjectAttributes(); a.LayerIndex = li
    if col is not None:
        a.ObjectColor = (int(col[0] * 255), int(col[1] * 255), int(col[2] * 255), 255)
        a.ColorSource = r.ObjectColorSource.ColorFromObject
    return a
def mesh_prism(bot,top):
    """bot/top: 同じ数の 3D 点列（閉じていない多角形）。側面と上下面（earcut で三角分割、凹形も可）"""
    import mapbox_earcut as _ec
    M=r.Mesh(); n=len(bot)
    for p in list(bot)+list(top): M.Vertices.Add(float(p[0]),float(p[1]),float(p[2]))
    xy=np.array([(float(p[0]),float(p[1])) for p in bot],dtype=np.float64)
    s=0.5*np.sum(xy[:,0]*np.roll(xy[:,1],-1)-np.roll(xy[:,0],-1)*xy[:,1])
    tri=np.array(_ec.triangulate_float64(xy,np.array([n],dtype=np.uint32))).reshape(-1,3)
    for a,b,c in tri:
        a,b,c=int(a),int(b),int(c)
        if s<0: b,c=c,b
        M.Faces.AddFace(a,c,b); M.Faces.AddFace(n+a,n+b,n+c)
    for i in range(n):
        j=(i+1)%n
        if s>0: M.Faces.AddFace(i,j,n+j,n+i)
        else: M.Faces.AddFace(j,i,n+i,n+j)
    M.Normals.ComputeNormals(); M.Compact(); return M
def solid_uv(pts_uv, z0, z1, li, col=None, name=None):
    pts = [W(u, v) for u, v in pts_uv]
    if len(pts) < 3: return
    z0f = z0 if callable(z0) else (lambda u, v, z=z0: z)
    z1f = z1 if callable(z1) else (lambda u, v, z=z1: z)
    bot = [(*p, z0f(u, v)) for p, (u, v) in zip(pts, pts_uv)]
    top = [(*p, z1f(u, v)) for p, (u, v) in zip(pts, pts_uv)]
    a_ = attr(li, col)
    if name: a_.Name = name
    m.Objects.AddMesh(mesh_prism(bot, top), a_)
def clean(pts):
    g = SP(pts).buffer(0)
    if g.is_empty: return []
    g = max(getattr(g, 'geoms', [g]), key=lambda x: x.area)
    return list(g.exterior.coords)[:-1]
def panel_uv(pts_uv, z0, z1, thick, li, col=None):
    """折れ線に沿う厚さ thick[m] の板"""
    for (u0, v0), (u1, v1) in zip(pts_uv, pts_uv[1:]):
        d = np.array([u1 - u0, v1 - v0]); L = np.linalg.norm(d)
        if L < 1e-4: continue
        n = np.array([-d[1], d[0]]) / L * thick / 2
        q = [(u0 - n[0], v0 - n[1]), (u1 - n[0], v1 - n[1]), (u1 + n[0], v1 + n[1]), (u0 + n[0], v0 + n[1])]
        solid_uv(q, z0, z1, li, col)
def table_uv(pts_uv, h, li, col=None, leg=0.04, top=30):
    solid_uv(pts_uv, h - top, h, li, col)
    g = SP(pts_uv); c = np.array(g.centroid.coords[0]); b = g.minimum_rotated_rectangle
    cs = np.array(b.exterior.coords)[:-1]
    for p in cs:
        q = c + (p - c) * 0.78
        solid_uv([(q[0] - leg / 2, q[1] - leg / 2), (q[0] + leg / 2, q[1] - leg / 2), (q[0] + leg / 2, q[1] + leg / 2), (q[0] - leg / 2, q[1] + leg / 2)], 0, h - top, li, col)
def ring_uv(pts_uv, z0, z1, thick, li, col=None, gap=None):
    """多角形の周りの囲い（gap=(u0,u1,v0,v1) の範囲はあける）"""
    pts = list(pts_uv) + [pts_uv[0]]
    for a, b in zip(pts, pts[1:]):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if gap and gap[0] <= mid[0] <= gap[1] and gap[2] <= mid[1] <= gap[3]: continue
        panel_uv([a, b], z0, z1, thick, li, col)

# ---------------- レイヤー ----------------
L_F = layer('90_しつらえ_家具（スギ）', (214, 190, 150))
L_P = layer('91_しつらえ_間仕切り・框・腰壁', (200, 185, 160))
L_WC = layer('92_しつらえ_水まわり（便器・手洗い・沐浴）', (213, 235, 238))
L_T = layer('93_しつらえ_布・ござ・畳・クッション', (232, 215, 230))
L_PL = layer('94_しつらえ_遊び（山・丘・ロフト・段々）', (195, 216, 148))
L_COT = layer('95_午睡時のコット（ふだんは片付け、非表示）', (79, 107, 42), visible=False)
L_GL = layer('96_しつらえ_ガラス・窓・格子', (150, 200, 230))
L_WW = layer('97_本館_外壁（西・南北の妻）', (196, 160, 118))   # スギの大和張り（10-26、決定事項（共通）の「外壁と窓」）
L_TR = layer('98_外構_読書の庭（モミジ）', (90, 122, 58))
L_TRc = layer('98c_外構_読書の庭（モミジ）_樹冠（葉）', (120, 160, 80))   # 一つのレイヤーには一つの素材（10-27、樹冠は 67c へ）
L_HI = layer('99_しつらえ_頭上（天蓋・物干し・天袋）', (180, 160, 200))
L_HW = layer('51w_しつらえ_頭上（天袋・物干しの竿・吊り桟、木）', (196, 160, 118))   # 10-27（監修の項 20261027-1704）：一つのレイヤーには一つの素材。布の天蓋は 99（→ 51）のまま

def fc(rec):
    c = rec.get('fc')
    if c is None or (hasattr(c, '__len__') and len(c) == 4 and c[3] == 0): return None
    return c

# ---------------- 高さの表（行番号 → 立ち上げ方） ----------------
# 種類：('solid',z0,z1,layer) ／ ('table',h,layer) ／ ('panel',z0,z1,thick,layer)（線・多角形の辺）
#       ('ring',z0,z1,thick,layer,gap) ／ 関数（rec を受け取って自分で作る）
def by_u_table(rec):                 # 3〜5歳の食卓：部屋で高さを変える
    u = np.mean(rec['pts'][:, 0]); h = 400 if u < 39 else (450 if u < 48 else 500)
    table_uv([tuple(p) for p in rec['pts']], h, L_F, fc(rec))
def by_u_seat(rec, d=170):
    u = np.mean(rec['pts'][:, 0]); h = (400 if u < 39 else (450 if u < 48 else 500)) - d
    solid_uv([tuple(p) for p in rec['pts']], 0, h, L_F, fc(rec))
def quiet_desk(rec):
    u = np.mean(rec['pts'][:, 0]); h = 400 if u < 39 else (450 if u < 48 else 500)
    solid_uv(clean(rec['pts']), h - 30, h, L_F, fc(rec))
def quiet_store(rec):
    u = np.mean(rec['pts'][:, 0]); h = 400 if u < 39 else (450 if u < 48 else 500)
    solid_uv(clean(rec['pts']), 0, h - 30, L_F, (0.91, 0.87, 0.78, 1))
def loft(rec):
    pts = [tuple(p) for p in rec['pts']]
    solid_uv(pts, 1100, 1200, L_PL, (0.92, 0.86, 0.72, 1))
    g = SP(pts); u0, v0, u1, v1 = g.bounds
    for pu, pv in [(u0 + .05, v0 + .05), (u1 - .05, v0 + .05), (u0 + .05, v1 - .05), (u1 - .05, v1 - .05)]:
        solid_uv([(pu - .05, pv - .05), (pu + .05, pv - .05), (pu + .05, pv + .05), (pu - .05, pv + .05)], 0, 1100, L_PL)
    # 手すり（西の壁側をのぞく 3 辺、縦格子のすき間90以下）。10-28（監修の項 20261028-0015 の 8、安全）：h+900 → h+1,100（床 1200 から 2300）、
    # 家具階段（ロフトの東の縁 v1 の前、u0+0.25〜u0+1.05、plan04 の bx(3.4, 4.2, …)）の所は上がり口として開ける
    ga, gb = u0 + 0.25, u0 + 1.05
    for a, b in [((u0, v1), (ga, v1)), ((gb, v1), (u1, v1)), ((u0, v0), (u0, v1)), ((u1, v0), (u1, v1))]:
        panel_uv([a, b], 1200, 2300, 0.03, L_GL, (0.85, 0.75, 0.6, 1))
def loft_step(rec):                  # 家具階段 1段0.2×5（10-24）：ロフトに近い段から 1000・800・600・400・200
    pts = rec['pts']; v = np.mean(pts[:, 1])
    k = int(round((v - 3.725) / 0.25)); h = max(200, 1000 - 200 * k)
    solid_uv([tuple(p) for p in pts], 0, h, L_PL, fc(rec))

# ---- 3〜5歳の保育室の分け方（10-24、ユーザー）：西の半分を架構の線で二つの巣に、東の半分は共有 ----
L_LAT = layer('96b_しつらえ_格子・手すり（木）', (185, 150, 105))
BEAM_BOT = lambda v: 3335.0 - (v - 0.784) * 83.4        # 本館の梁（2枚）の下端 [mm]（架構の形から、v 0.8〜11.1）
def koshi_wall(rec):                 # 腰の壁 h1100（架構の線の上）＋上は梁の下まで縦格子（30角＠150）
    pts = clean(rec['pts']); solid_uv(pts, 0, 1100, L_P)
    g = SP(pts); u0, v0, u1, v1 = g.bounds; uc = (u0 + u1) / 2
    for v in np.arange(v0 + 0.1, v1 - 0.05, 0.15):
        solid_uv([(uc - .015, v - .015), (uc + .015, v - .015), (uc + .015, v + .015), (uc - .015, v + .015)],
                 1100, BEAM_BOT(v) - 10, L_LAT, (0.85, 0.75, 0.6, 1))
def canopy(rec):                     # 布の天蓋（吊り桟から、ふだんの高さ h1.8〜1.95、午睡は下ろす）
    # 10-30（ユーザー、監修の項 20261030-1331）：吊り桟が h2400 → h2000 になったので、ふだんの高さを 2.1〜2.25 → 1.8〜1.95（吊り桟の下で包まれる）。形は同じ
    pts = clean(rec['pts']); g = SP(pts); u0, v0, u1, v1 = g.bounds
    zc = lambda v: 1800 + 150 * abs(math.cos(math.pi * (v - v0) / 0.9))   # 吊り桟の下でたるむ（0.9ごと）
    vs = np.arange(v0, v1 + 1e-6, 0.15)
    for a, b in zip(vs, vs[1:]):
        solid_uv([(u0, a), (u1, a), (u1, b), (u0, b)], lambda u, v: zc(v), lambda u, v: zc(v) + 8, L_HI, (0.97, 0.95, 0.9, 1))
def hang_bar(rec):                   # 吊り桟 30×40 を h2.0 に（梁と梁のあいだ、南北に）、両端は梁の下端から φ9 の吊り棒
    # 10-30（ユーザー、監修の項 20261030-1331）：h2400 → h2000（3段の脚立の2段目に立って目の高さで結べる、子ども中心）。
    # 通す所は梁の下端が 2.03 より高い所（前は 2.43）。v2.0 から 0.9 ごとの並びのまま東の v11.9（東の柱の線の手前、桁の下）まで。
    # 桟の端は架構の線から 0.13（前 0.10：4歳の部屋の路地への引き戸（h2000、架構の線から 0.07〜0.10）の上を桟がこすらない）、吊り棒は
    # 端から 0.015（架構の線から 0.145＝梁の板（0.09〜0.19）の真ん中の下）。東の柱の手前（v11.47 から東）は梁の板が柱へ上がるので桁の下端（2420）から吊る
    (ua, v), (ub, _) = rec['pts'][0], rec['pts'][-1]
    u0, u1 = sorted([float(ua), float(ub)]); v = float(v)
    if BEAM_BOT(v) < 2030: return
    top = BEAM_BOT(v) if v < 11.47 else 2420.0
    solid_uv([(u0, v - .015), (u1, v - .015), (u1, v + .015), (u0, v + .015)], 1980, 2020, L_HW, (0.85, 0.75, 0.6, 1))
    # 10-30（ユーザー）：ロフトのすぐ脇 v4.2 の桟は家具階段の口の前を除くので、片方の端が梁の下に来ない（架構の線から 0.2 より遠い）。
    # その端は、両側の母屋（v1.79 から 455 おき、下端＝屋根の面 ROOF_Z(v)−474）の下に受け材（杉 30×40、母屋の下端に留める）を渡し、そこから φ9 で吊る
    for uu in (u0 + 0.015, u1 - 0.015):
        tp = top - 5
        if abs(uu - 3.0 * round(uu / 3.0)) > 0.2:
            pa = 1.79 + 0.455 * math.floor((v - 1.79) / 0.455); pb = pa + 0.455
            pbot = lambda u_, v_: 4150.0 - v_ * 1000.0 / 12.0 - 474.0 - 2.0
            solid_uv([(uu - .015, pa - .03), (uu + .015, pa - .03), (uu + .015, pb + .03), (uu - .015, pb + .03)],
                     lambda u_, v_: pbot(u_, v_) - 40.0, pbot, L_HW, (0.85, 0.75, 0.6, 1))
            tp = 4150.0 - v * 1000.0 / 12.0 - 474.0 - 2.0 - 40.0
        solid_uv([(uu - .0045, v - .0045), (uu + .0045, v - .0045), (uu + .0045, v + .0045), (uu - .0045, v + .0045)],
                 2020, tp, L_HW, (0.5, 0.5, 0.5, 1))
def steps01(rec):                    # 0・1歳の上り下りの段々（150×3）
    pts = rec['pts']; g = SP(pts); u0, v0, u1, v1 = g.bounds
    cuts = [u0, 7.9, 8.4, 8.9, u1]; hs = [150, 300, 450, 450]
    for (a, b), h in zip(zip(cuts, cuts[1:]), hs):
        piece = g.intersection(sbox(a, v0, b, v1))
        if not piece.is_empty: solid_uv(list(piece.exterior.coords)[:-1], 0, h, L_PL, (0.96, 0.95, 0.9, 1))
def hill(rec):                       # 2歳の山：等高線 k=1/0.66/0.33 を 0–300／300–600／600–900
    pts = clean(rec['pts']); g = SP(pts); A = g.area
    h0 = 0 if A > 6 else (300 if A > 2.5 else 600)
    # 10-28（監修の項 20261027-2346 の 46）：いちばん内の等高線（k=0.33、約0.6 m²）は一つ外（k=0.66）と同じ 600–900 で、その中にまるごと入っていた → 作らない（形は変わらない）
    if A < 1.2: return
    solid_uv(pts, h0, h0 + 300, L_PL, fc(rec))
def cot(rec):
    solid_uv([tuple(p) for p in rec['pts']], 0, 120, L_COT)
def nedoko(rec):                     # ねどこの囲い h900（u=5.6 の辺に開口）
    ring_uv([tuple(p) for p in rec['pts']], 0, 900, 0.03, L_P, (0.95, 0.93, 0.85, 1), gap=(5.5, 5.7, 5.2, 6.2))
def _orient_ccw(pg):
    from shapely.geometry.polygon import orient as _o
    return _o(pg if pg.geom_type == 'Polygon' else max(pg.geoms, key=lambda g_: g_.area), 1.0)
def hut_roof(rec):                  # 2歳の小屋の屋根（10-28、監修の項 20261028-0015 の 8、ユーザー：登れない屋根に）
    # 前は h1000 の平らな板（登れた）。小屋の形（囲い u16.9〜17.95・v3.3〜4.6、h1000）は変えず、屋根を急な切妻（60°）に：
    # 棟は v の向き（小屋の真ん中 u17.425）、軒は囲いの上端 h1000、棟 約 h1900。杉の板 t20 を勾配の面に直角に厚みをつけた平らな板 2 枚。
    import math as _mt
    g = SP(clean(rec['pts'])); _, v0, _, v1 = g.bounds
    ua, ub = 16.9, 17.95; uc = (ua + ub) / 2; zt = 1000.0 + (uc - ua) * 1000.0 * _mt.tan(_mt.radians(60))
    # 10-28（監修の項 20261028-0843 の 46）：板は真っすぐな座標（小屋の真ん中の接線 t・放射 r）で作る。前は弧の座標 W(u, v) で、
    # 上下の面が平らでなく（放射の線が寄る分）Rhino 版で三角形の面に割れていた。東の軒の板が腰の壁（38、u17.95〜）に入る分は削る段と同じく u17.95 で切る
    from shapely.geometry import box as _bx
    vm = 0.5 * (v0 + v1); Wc = W(uc, vm); tv = W(uc + 0.001, vm) - Wc; tv /= np.linalg.norm(tv); rv = W(uc, vm + 0.001) - Wc; rv /= np.linalg.norm(rv)
    Ws = lambda u, v: Wc + (u - uc) * 1000.0 * (205.0 - vm) / 205.0 * tv + (v - vm) * 1000.0 * rv
    for (u_e, u_r) in ((ua, uc), (ub, uc)):
        du = (u_r - u_e) * 1000.0; dz = zt - 1000.0; L = _mt.hypot(du, dz); nu, nz = -dz / L * np.sign(du), abs(du) / L   # 面の外向きの法線（u, z）
        prof = [(u_e, 1000.0), (u_r, zt), (u_r + nu * 20 / 1000.0, zt + nz * 20), (u_e + nu * 20 / 1000.0, 1000.0 + nz * 20)]
        pg = SP([(u * 1000.0, z) for u, z in prof]).intersection(_bx(-1e9, -1e9, 17950.0, 1e9))
        prof = [(a / 1000.0, z) for a, z in list(_orient_ccw(pg).exterior.coords)[:-1]]
        n_ = len(prof)
        V = [(*Ws(u, v), z) for v in (v0, v1) for u, z in prof]
        M = r.Mesh()
        for p_ in V: M.Vertices.Add(float(p_[0]), float(p_[1]), float(p_[2]))
        F = [(0, k, k + 1) for k in range(1, n_ - 1)] + [(n_, n_ + k + 1, n_ + k) for k in range(1, n_ - 1)] + \
            [(k, (k + 1) % n_, n_ + (k + 1) % n_, n_ + k) for k in range(n_)]
        P_ = np.array(V); vol = sum(np.dot(P_[f[0]], np.cross(P_[f[i]] - P_[f[0]], P_[f[i + 1]] - P_[f[0]])) for f in F for i in range(1, len(f) - 1))
        if vol < 0: F = [f[::-1] for f in F]
        for f in F: M.Faces.AddFace(*f)
        M.Normals.ComputeNormals(); M.Compact(); m.Objects.AddMesh(M, attr(L_PL, fc(rec) or (0.92, 0.86, 0.72, 1)))
def kubomi(rec):                    # 2歳の落ち着くくぼみ：囲い h1000、南に開口
    ring_uv([tuple(p) for p in rec['pts']], 0, 1000, 0.04, L_PL, fc(rec), gap=(16.85, 16.95, 3.55, 4.35))
def mamagoto_posts(rec): solid_uv([tuple(p) for p in rec['pts']], 0, 1400, L_F, (0.3, 0.25, 0.2, 1))
def basket(rec):  solid_uv([tuple(p) for p in rec['pts']], 400, 700, L_T, (1, 1, 1, 1))

T01 = {   # plan01（0・1歳、u ≤ 12）
    98: ('solid', -300, 3900, L_WW), 99: ('solid', -300, 3900, L_WW),
    # 100（南の妻のガラス戸）：10-26夜から south/fix_details.py の「乳児室の南の妻」で作る（ガラスの引き戸・鴨居・上の杉の壁・外の縦格子）
    106: ('solid', -300, 600, L_P),                       # 框＋腰壁 h600
    109: ('solid', -300, -150, L_F),                      # 式台 150
    110: ('panel', -150, 900, 0.04, L_F),                 # 木戸
    86: ('solid', 0, 300, L_F),                           # 窓辺の小上がり h300
    111: lambda rec: ring_uv(clean(rec['pts']), 300, 900, 0.03, L_F, fc(rec), gap=(5.99, 6.01, 0.9, 1.1)),   # 格子の手すり h600（10-28、監修の項 2346 の 37：西の端 u6.0 の短い辺は腰掛けの端の壁の中にまるごと入るので作らない）
    112: ('solid', 0, 900, L_P),
    117: ('solid', 0, 2400, L_P), 118: ('solid', 0, 2400, L_P),
    126: ('solid', 0, 850, L_WC), 129: ('solid', 0, 850, L_WC), 131: ('solid', 0, 850, L_WC),
    133: ('solid', 0, 300, L_WC), 134: ('solid', 0, 250, L_WC),
    140: ('table', 500, L_F), 141: ('solid', 0, 300, L_F),       # 先生の腰掛ける机（天板 500・座 300）
    144: ('table', 700, L_F), 145: ('solid', 0, 700, L_F),
    149: nedoko, 153: ('solid', 0, 250, L_F), 155: ('solid', 2100, 2115, L_HI),   # ねどこの天蓋（10-28、監修の項 20261028-0015 の 15：h1800 → h2100、大人の頭に当たらない、梁の下）
    158: basket, 162: ('solid', 0, 120, L_PL), 163: ('solid', 120, 200, L_PL),
    166: ('solid', 0, 600, L_F), 171: ('table', 350, L_F), 173: ('solid', 0, 200, L_F), 174: ('solid', 0, 200, L_F),
    178: cot, 180: ('solid', 0, 800, L_F), 183: ('solid', 0, 900, L_F),
    187: ('solid', 0, 850, L_WC), 189: ('solid', 0, 850, L_WC), 190: ('solid', 0, 850, L_F),
    193: ('panel', 2600, 2630, 0.03, L_HW), 195: ('solid', 2400, 2700, L_HW),
    200: steps01, 203: ('solid', 0, 150, L_PL),
    205: ('solid', 0, 12, L_WC), 206: ('solid', 0, 850, L_WC),
    209: ('panel', 0, 900, 0.03, L_P), 211: ('panel', 0, 900, 0.03, L_P), 212: ('panel', 0, 900, 0.03, L_P),
}
T02 = {   # plan02（2歳、12 ≤ u ≤ 18.07）
    80: ('solid', 0, 8, L_T),
    89: ('solid', 0, 2400, L_P), 92: ('solid', 0, 2400, L_P), 93: ('solid', 0, 2400, L_P), 94: ('solid', 0, 2400, L_P),
    98: ('solid', 0, 2400, L_P),
    103: ('solid', 0, 100, L_WC), 106: ('solid', 0, 500, L_WC), 107: ('solid', 0, 260, L_WC),
    109: ('panel', 0, 900, 0.03, L_WC), 110: ('solid', 0, 300, L_F),
    113: ('solid', 0, 900, L_F), 116: ('solid', 0, 250, L_F), 118: ('solid', 0, 900, L_F),
    120: kubomi, 123: hut_roof,                           # 小屋の屋根（10-28：急な切妻、登れない）
    125: ('solid', 0, 500, L_WC), 129: ('solid', 0, 600, L_F), 130: ('solid', 0, 15, L_T),
    133: ('table', 400, L_F), 135: ('solid', 0, 220, L_F), 136: ('solid', 0, 220, L_F),
    140: cot, 142: ('solid', 0, 15, L_T), 144: mamagoto_posts, 145: ('solid', 1400, 1430, L_F), 146: ('solid', 0, 550, L_F),
    148: ('solid', 0, 1500, L_F), 161: hill,
    166: ('panel', 300, 650, 0.06, L_PL),                 # 崖 h350
}
T04 = {   # plan04（3〜5歳、u ≥ 30）
    89: ('solid', 0, 3900, L_WW),                          # 北の妻
    95: ('solid', 0, 2400, L_P), 96: ('solid', 0, 2400, L_P),
    113: ('solid', 0, 2400, L_P), 116: ('solid', 0, 2400, L_P), 122: ('solid', 0, 2400, L_P),
    118: ('panel', 0, 2400, 0.12, L_P), 123: ('panel', 0, 2400, 0.12, L_P),
    134: ('solid', 0, 500, L_WC),                         # 143・144・147〜151（四角い個室・帯の中の流し）は 10-28 から丸いポッド（下の maru_pods）
    # 153（路地の出口の暖簾）：暖簾は外した、ユーザー 10-28
    154: ('panel', 100, 700, 0.02, L_GL),                 # 便所の東の低い窓
    170: ('solid', -150, 250, L_F),                       # 下足箱・腰掛け（外縁側の側）
    284: by_u_table, 288: by_u_seat, 295: cot,
    333: quiet_desk, 337: quiet_store, 342: by_u_seat, 345: by_u_seat,
    349: loft, 351: loft_step,
    359: ('solid', 0, 450, L_F), 358: ('table', 700, L_F),                 # 先生の席（10-24：腰の壁の東の端）
    357: koshi_wall, 363: ('solid', 0, 700, L_F),                  # 腰の壁＋格子／移動式の低い腰壁（棚）
    364: canopy, 368: hang_bar,                                 # 布の天蓋／吊り桟 h2000（10-30）
    372: ('solid', 0, 1000, L_F), 376: ('solid', 0, 900, L_F), 379: ('solid', 0, 12, L_T),
    396: ('solid', 0, 1200, L_F),                         # 絵本の通りの棚
    398: ('solid', 0, 300, L_F), 399: ('panel', 300, 1300, 0.01, L_T), 400: ('solid', 300, 420, L_T),
    406: ('panel', 0, 2000, 0.03, L_F), 407: ('solid', 0, 50, L_T), 408: ('solid', 0, 5, L_PL),
    414: ('solid', 50, 220, L_T),
    126: ('solid', 0, 1800, L_F),
    127: ('solid', 0, 1800, L_F),
    446: ('solid', 0, 1800, L_F),                         # 記録の棚（3歳の部屋の側の壁）
    # 443・445・447〜451（記録・連絡の机、応接の机・長椅子、園長の机と棚）：10-29 から一つの事務室、家具は add_hall.py の「スパン 11」
}

# ---- 0〜2歳の縁側（10-21：他と同じく縁側の中ほど r=191.5 にガラス戸。内縁側＝はだし・部屋の一部、外縁側＝土足 FL−150）----
def eng_fence(rec):      # 0・1歳｜2歳の境の低い柵（内縁側は h900、外縁側は土足の床から h900）
    v = float(np.mean(rec['pts'][:, 1]))
    if v < 13.5: solid_uv(clean(rec['pts']), 0, 900, L_P)
    else: solid_uv(clean(rec['pts']), -150, 750, L_P)
def first_step(rec):     # 二段の縁 → 外縁側が −150 になったので、地面との間は沓脱ぎ石 1 つ
    if float(np.mean(rec['pts'][:, 1])) < 15.3: solid_uv(clean(rec['pts']), -300, -200, L_F, (0.8, 0.78, 0.74, 1))
T01.update({197: eng_fence, 220: ('solid', -150, 750, L_P),          # 外縁側の外の端に格子の高欄 h900
            223: first_step,                                         # 225（「おひるね中」の暖簾）：暖簾は外した、ユーザー 10-28
            256: ('solid', -300, 0, L_F)})                           # 大きい子の縁台 h300（地面から）
T02.update({188: ('solid', -150, 750, L_P), 190: first_step})          # 191（「おひるね中」の暖簾）：暖簾は外した、ユーザー 10-28

def store_ceiling(rec):          # 教材庫：天井 h2400
    c = fc(rec)
    if c is not None and abs(c[0] - 0xE4 / 255) < 0.02 and abs(c[1] - 0xE1 / 255) < 0.02:
        solid_uv(clean(rec['pts']), 2400, 2430, L_P, c)
T04[107] = store_ceiling

import os as _os
REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'ref')
def build(name, table, umin, umax, skipclip=False):
    # 高さの表は ref/ の版（10-21）の行番号で書いてある。行の中身（文）で引き直し、スクリプトに行が足されてもずれないようにする
    # （10-27：ref/plan04.py の路地の出口の3行（116〜118）は、行の数を変えずに今の文に書き換えた。隅切りをやめてまっすぐに）
    ref = prep(_os.path.join(REF, name))
    bytext = {}
    for ln, spec in table.items():
        bytext.setdefault(ref[ln - 1].strip(), spec)
    recs, lines = capture(f'{SCR}/{name}')
    for rec in recs:
        rec['ln'] = lines[rec['ln'] - 1].strip() if rec['ln'] > 0 else ''
    table = bytext
    cnt = 0
    for rec in recs:
        spec = table.get(rec['ln'])
        if spec is None: continue
        pts = rec['pts']
        um = float(np.mean(pts[:, 0]))
        if not (umin - 1e-6 <= um <= umax + 1e-6): continue
        rec['pts'] = pts
        if callable(spec): spec(rec); cnt += 1; continue
        kind = spec[0]
        if rec['kind'] == 'line':
            if kind == 'panel': panel_uv([tuple(p) for p in pts], spec[1], spec[2], spec[3], spec[4], None)
            elif kind == 'solid': panel_uv([tuple(p) for p in pts], spec[1], spec[2], 0.1, spec[3], None)
            cnt += 1; continue
        P_ = clean(pts) if rec['kind'] == 'poly' else [tuple(p) for p in pts]
        if not P_: continue
        colr = None if spec[-1] in (L_P, L_WW) or (kind=='solid' and spec[3] in (L_P, L_WW)) else fc(rec)
        if kind == 'solid' and spec[3] == L_P and rec['kind'] == 'poly':
            # 10-29（監修の項 20261029-0928-kanshu-2 の 4）：間仕切り（91 → 38）の輪郭から一直線の上の点を除く（形は同じ）。plan04 の架構の線の
            # 壁（u39・42・48・51、厚さ 120）は輪郭の短い辺に 20 おきの点が 6 つずつ並び、板 6 枚が一つの網目のように届いていた → 一枚ずつの箱（4 角の押し出し）
            _g = SP(P_).simplify(0.0002, preserve_topology=True)
            if _g.geom_type == 'Polygon' and abs(_g.area - SP(P_).area) < 1e-6: P_ = list(_g.exterior.coords)[:-1]
        if kind == 'solid': solid_uv(P_, spec[1], spec[2], spec[3], colr)
        elif kind == 'table': table_uv(P_, spec[1], spec[2], fc(rec))
        elif kind == 'panel': ring_uv(P_, spec[1], spec[2], spec[3], spec[4], fc(rec))
        cnt += 1
    print(name, 'objects', cnt)

build('plan01.py', T01, -1, 12.0)
build('plan02.py', T02, 12.0, 18.1)
build('plan04.py', T04, 29.9, 57.4)

# ---------------- こどもの便所の丸いポッド（10-28 ユーザー、決定事項（本館）の「便所・倉庫のスパン」、検討 maru_wc2） ----------------
# スパン 14（plan04 の crank_block(39, False)、U(w) = 39 + w）と 17（crank_block(48, True)、U(w) = 51 − w）の便所の帯。局所座標 w（u の向き、
# 部屋の壁 w0 から路地 w1.5 へ）・v。個室 4 つ：内径 φ1.0・壁 t30・h1300 の円筒（路地の側 w+ に開口 約0.47）、中心 w0.59・v7.71〜11.34（すき間 150）。
# 戸：丸い引き戸 t30・h1300（閉じた位置で壁の外を回る円弧の板、開口の両側に 5°かかる）。便器は奥寄り。掃除用の流し 500×450 は帯の外へ。
# どれも閉じた押し出し（輪郭の線と円弧、メッシュにしない）。
L_DOOR = layer('19d_建具_室内の戸（木）', (165, 120, 75))
POD_RIN, POD_T, POD_H = 0.50, 0.03, 1300.0
POD_W, POD_VS = 0.59, [7.71, 8.92, 10.13, 11.34]
POD_HALF = math.degrees(math.asin(0.47 / 2 / POD_RIN)); POD_DOV = 5.0
def _ext(curve, z0, z1, li, name=None, col=None):
    e = r.Extrusion.Create(curve, float(z1 - z0), True)
    if e is None: return
    if e.GetBoundingBox().Min.Z < -1.0: e = r.Extrusion.Create(curve, -float(z1 - z0), True)
    e.Translate(r.Vector3d(0.0, 0.0, float(z0)))
    a = attr(li, col)
    if name: a.Name = name
    m.Objects.AddExtrusion(e, a)
def maru_pods(b0, flip):
    U = (lambda w: b0 + 3 - w) if flip else (lambda w: b0 + w)
    P3 = lambda q: r.Point3d(float(q[0]), float(q[1]), 0.0)
    def frame(w, v):
        c = W(U(w), v); tw = W(U(w + 0.001), v) - c; tw /= np.linalg.norm(tw); tv = W(U(w), v + 0.001) - c; tv /= np.linalg.norm(tv)
        return c, tw, tv
    def band(c, tw, tv, r0, r1, a0, a1):
        pt = lambda R_, a: c + R_ * 1000.0 * (math.cos(math.radians(a)) * tw + math.sin(math.radians(a)) * tv)
        am = 0.5 * (a0 + a1); pc = r.PolyCurve()
        pc.Append(r.Arc(P3(pt(r1, a0)), P3(pt(r1, am)), P3(pt(r1, a1))))
        pc.Append(r.LineCurve(P3(pt(r1, a1)), P3(pt(r0, a1))))
        pc.Append(r.Arc(P3(pt(r0, a1)), P3(pt(r0, am)), P3(pt(r0, a0))))
        pc.Append(r.LineCurve(P3(pt(r0, a0)), P3(pt(r1, a0))))
        return pc
    def poly_w(pts):                                     # 局所 (w, v) の多角形 → 閉じた折れ線
        q = [W(U(w), v) for w, v in pts]; q.append(q[0])
        return r.Polyline([P3(x) for x in q]).ToPolylineCurve()
    rout = POD_RIN + POD_T
    for vc in POD_VS:
        c, tw, tv = frame(POD_W, vc)
        _ext(band(c, tw, tv, POD_RIN, rout, POD_HALF, 360.0 - POD_HALF), 0.0, POD_H, L_P, 'こどもの便所の丸い個室 φ1000 t30 h1300')
        _ext(band(c, tw, tv, rout + 0.01, rout + 0.01 + POD_T, -POD_HALF - POD_DOV, POD_HALF + POD_DOV), 10.0, POD_H, L_DOOR,
             '丸い引き戸（こどもの便所） 開口470 h1300 鍵なし')
        # 便器（奥寄り）：背の箱 w0.14〜0.37・v±0.17（h550）、便器 0.42×0.32 の楕円（中心 w0.58、h260）
        _ext(poly_w([(POD_W - 0.45, vc - 0.17), (POD_W - 0.22, vc - 0.17), (POD_W - 0.22, vc + 0.17), (POD_W - 0.45, vc + 0.17)]), 0.0, 550.0, L_WC)
        _ext(poly_w([(POD_W - 0.01 + 0.21 * math.cos(t), vc + 0.16 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 48, endpoint=False)]), 0.0, 260.0, L_WC)
    # 掃除用の流し 500×450（h800）：スパン 14 は職員の個室の南西の隅、スパン 17 は教材庫の口の脇の隅（棚を 450 縮めた所）
    sk = [(1.56, 1.65), (2.06, 1.65), (2.06, 2.10), (1.56, 2.10)] if not flip else [(2.44, 1.66), (2.94, 1.66), (2.94, 2.11), (2.44, 2.11)]
    _ext(poly_w(sk), 0.0, 800.0, L_WC, '掃除用の流し 500×450')
maru_pods(39, False); maru_pods(48, True)

# ---------------- 保育室と路地のあいだの引き戸（10-29 ユーザー、決定事項（本館）の「保育室と路地のあいだに戸」） ----------------
# 口の幅いっぱい（1.2）＋両側 30 かかる、杉の框（縦框 60・上框 60・下框 90）と縦格子 30@120、h2000（床から 10）、厚さ 30。
# 部屋の側の壁の面から 10 離して走り、戸袋は部屋の側の壁に沿って東（v の大きい側、壁 v10.4〜12.0）へ。閉じた位置。建具のレイヤー 19d。
def _box_uv(u0, u1, v0, v1, z0, z1, li, name):
    q = [W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)]; q.append(q[0])
    _ext(r.Polyline([r.Point3d(float(x[0]), float(x[1]), 0.0) for x in q]).ToPolylineCurve(), z0, z1, li, name)
def roji_door(u_wall, side, v0, v1):
    t0 = u_wall + side * 0.07; t1 = t0 + side * 0.03; ua, ub = sorted([t0, t1])
    a, b = v0 - 0.03, v1 + 0.03; nm = '引き戸（保育室｜路地） W1200 h2000 杉の框・縦格子'
    _box_uv(ua, ub, a, a + 0.06, 10, 2000, L_DOOR, nm); _box_uv(ua, ub, b - 0.06, b, 10, 2000, L_DOOR, nm)
    _box_uv(ua, ub, a + 0.06, b - 0.06, 10, 100, L_DOOR, nm); _box_uv(ua, ub, a + 0.06, b - 0.06, 1940, 2000, L_DOOR, nm)
    for vv in np.arange(a + 0.06 + 0.075, b - 0.06 - 0.03, 0.12):
        _box_uv(ua, ub, vv, vv + 0.03, 100, 1940, L_DOOR, nm)
roji_door(42.0, +1, 9.2, 10.4)                                     # スパン14 の北の口 → 4歳の部屋
roji_door(48.0, -1, 9.2, 10.4)                                     # スパン17 の南の口 → 4歳の部屋
# 南の口（3歳 u39・5歳 u51、v3.6〜4.8）は部屋の側に引く所が無い（西はロフトの柱と格子、東は壁の棚 v5.2〜）。
# 10-29 夜の判断（kettei/honkan.md の「夜の判断」）：路地の側を走らせ、戸袋は路地の側の壁（v1.6〜3.6、西）へ
roji_door(39.0, +1, 3.6, 4.8)                                      # スパン14 の南の口 → 3歳の部屋（路地の側）
roji_door(51.0, -1, 3.6, 4.8)                                      # スパン17 の北の口 → 5歳の部屋（路地の側）

# ---------------- 西の外壁（u 0–57、開口つき） ----------------
OPEN = [  # (u0, u1, z0, z1)
    # 0〜2歳の西吹き抜けの窓（決定事項（本館）の「西吹き抜けの窓」）：スパン 1〜6 に一つずつ、スパンの真ん中（架構の線の柱を避ける）、
    # 幅 0.60×高さ 0.90 の縦長。10-28夜（ユーザー）：窓台はその部屋の子の目の高さから、南から 150・250・350・450（0・1歳）、500・550（2歳）。
    # 低い窓のガラスは合わせガラス（物の名前に）。スパン 7（窓口の帯の西）は柱のあいだいっぱい u18.15〜20.85、窓台 850・上端 2050（10-28夜）。
    *[(3.0 * k - 1.8, 3.0 * k - 1.2, z_, z_ + 900, 'win') for k, z_ in zip(range(1, 7), (150, 250, 350, 450, 500, 550))],
    (18.15, 20.85, 850, 2050, 'win'),
    (21.0, 30.0, -300, 99999),                                             # ホールの範囲（スパン 8–10）は西の壁を開く（10-21 夕、あまのがわの口を含む）
    (45.6, 47.6, 0, 2400),                                                 # 遊戯室の北の口（口②、10-24 柱u45・48のあいだへ、西館とそろえた）。口①は南の口にまとめて閉じた（10-21）
    (52.6, 53.85, -300, 600), (54.15, 56.4, -300, 600),                    # 本の奥の低い窓（GL まで）。架構の線 u54 の柱で二つに（10-26）
]
# すき間の倉庫（先生の道の側、u30〜40、西館係が床と棚）への口（10-25、監修の項 20261025-0710）：柱と柱のあいだごとに h2100 の口と引き違いの戸
GAP_STORE_BAYS = [(33.15, 35.85), (36.15, 38.85), (39.15, 39.95)]
# スパン11（u30〜33、柱のあいだ）は西の外壁を蓋の下まで開け、先生の道を西館へつなぐ（10-27、西館係の項 20261027-1057-nishikan。
# 西館の東の壁もキッチンの前からスパン11まで開いた。倉庫は u33.1〜39.95 に縮めた）。ふだんは開けたまま、戸は付けない
OPEN += [(30.1, 32.85, 0, 99999)]
OPEN += [(a_, b_, 0, 2100) for a_, b_ in GAP_STORE_BAYS]
rec01, _l01 = capture(f'{SCR}/plan01.py')
_k115 = prep(_os.path.join(REF, 'plan01.py'))[114].strip()
ws = [r_ for r_ in rec01 if r_['ln'] > 0 and _l01[r_['ln'] - 1].strip() == _k115]
# （10-26：前は plan01 の覗き窓の位置で 0・1歳の窓を置き換えていた。窓は上の OPEN の一つの決まりに）
ZW = ROOF_IN(0.0)
cuts = sorted(set([0.0, 57.0] + [o[0] for o in OPEN] + [o[1] for o in OPEN]))
glass = (0.6, 0.8, 0.9, 1)
for a, b in zip(cuts, cuts[1:]):
    um = (a + b) / 2
    zs = [(-300, ZW)]
    for o in OPEN:
        if o[0] <= um <= o[1]:
            new = []
            for z0, z1 in zs:
                if o[2] > z0: new.append((z0, min(o[2], z1)))
                if o[3] < z1: new.append((max(o[3], z0), z1))
            zs = new
            if (len(o) > 4 and o[4] == 'win') or o[3] <= 700:      # 窓はガラス（低い窓は合わせガラス、10-28夜）
                solid_uv([(a, -0.015), (b, -0.015), (b, 0.015), (a, 0.015)], o[2], o[3], L_GL, glass,
                         name='合わせガラス（低い窓）' if o[2] < 800 else '窓のガラス')
    us = np.linspace(a, b, max(2, int((b - a) / 1.0) + 1))
    for z0, z1 in zs:
        if z1 - z0 < 5: continue
        pts = [(u, -0.075) for u in us] + [(u, 0.075) for u in us[::-1]]
        solid_uv(pts, z0, z1, L_WW)
# すき間の倉庫の引き違い戸（木、2枚、外壁の厚さの中の2本のレール。柱は外壁の内側に立つので戸は柱の後ろを通らない）
L_GSD = layer('19e_本館_すき間の倉庫の引き戸（先生の道から）', (150, 110, 70))
for a_, b_ in GAP_STORE_BAYS:
    w_ = (b_ - a_) / 2
    for (u0_, u1_), (v0_, v1_) in (((a_, a_ + w_ + 0.02), (-0.305, -0.28)), ((b_ - w_ - 0.02, b_), (-0.27, -0.245))):
        solid_uv([(u0_, v0_), (u1_, v0_), (u1_, v1_), (u0_, v1_)], 0, 2080, L_GSD, (0.75, 0.62, 0.45, 1))
# 一本の線の上の縦格子（3〜5歳の保育室の西の壁、h2400 から屋根の下まで）
for a, b in [(33, 39), (42, 48), (51, 57)]:
    us = np.linspace(a, b, 7)
    panel_uv([(u, 1.6) for u in us], 2400, lambda u, v: ROOF_IN(1.6), 0.03, L_GL, (0.85, 0.75, 0.6, 1))
# 読書の庭のモミジ（ベニシダレ、プレゼンの準備の項 20261030-2254、u54.4, v−2.3）
c = (54.4, -2.3)
ang = np.linspace(0, 2 * np.pi, 13)[:-1]
solid_uv([(c[0] + 0.08 * np.cos(t), c[1] + 0.08 * np.sin(t)) for t in ang], -300, 2200, L_TR, (0.35, 0.25, 0.15, 1))
def crown_ell(c_uv, rad, z0, z1, li, col):     # 樹冠は縦に少しつぶれた楕円体（10-31 ユーザー：木はみな幹の円柱＋丸い樹冠、園庭の係）。外形（半径・下端・上端）は前の円柱と同じ
    _ns = r.Sphere(r.Point3d(0, 0, 0), rad * 1000).ToNurbsSurface(); _cp = _ns.Points
    for _i in range(_cp.CountU):
        for _j in range(_cp.CountV):
            _q = _cp[_i, _j]; _cp[_i, _j] = r.Point4d(_q.X, _q.Y, _q.Z * (z1 - z0) / 2 / (rad * 1000), _q.W)
    _b = r.Brep.CreateFromSurface(_ns); _x, _y = W(*c_uv)
    _b.Transform(r.Transform.Translation(_x, _y, (z0 + z1) / 2))
    m.Objects.AddBrep(_b, attr(li, col))
crown_ell(c, 1.3, 2200, 3300, L_TRc, (0.55, 0.7, 0.35, 1))
# 読書の庭のロウバイ（ユーザー 10-31、園庭の項 20261031-0008）：南の低い窓（u52.6〜53.85）の前、窓から約1.1、西館の北の窓にも近い。
# 株立ちの低木、刈り込んで h2.5・葉張り約φ1.8（1〜2月、葉のない枝に香りの花）。ベニシダレ（u54.4）の樹冠と重ならない所
c = (52.3, -1.3)
for dx, dy in ((-0.12, 0.0), (0.08, 0.1), (0.06, -0.1)):
    solid_uv([(c[0] + dx + 0.04 * np.cos(t), c[1] + dy + 0.04 * np.sin(t)) for t in ang], -300, 1300, L_TR, (0.35, 0.25, 0.15, 1))
crown_ell(c, 0.9, 1300, 2500, L_TRc, (0.86, 0.78, 0.35, 1))
# ---- 3・4歳、4・5歳のあいだの通り抜け（こどもの小径）の床を「便所・倉庫」から分ける（10-24夜、プレゼンの準備の依頼：通りの色で塗る）----
# plan04 の路地（C_LOOP の多角形、スパン14・17）で、add_floor の「59_1F_便所・倉庫」の床の板を切り分ける。形は変えない。
import colorsys as _cs
_rec4, _ = capture(f'{SCR}/plan04.py')
_loop = (0xF6 / 255, 0xDD / 255, 0xD3 / 255)
_roji = [SP([tuple(p) for p in r_['pts']]).buffer(0) for r_ in _rec4
         if r_['kind'] == 'poly' and r_.get('fc') is not None and len(r_['fc']) >= 3
         and all(abs(r_['fc'][i] - _loop[i]) < 0.01 for i in range(3))
         and (38.9 < float(np.mean(r_['pts'][:, 0])) < 42.1 or 47.9 < float(np.mean(r_['pts'][:, 0])) < 51.1)
         and float(np.mean(r_['pts'][:, 1])) > 1.6]
from shapely.ops import unary_union as _uu
_RJ = _uu(_roji) if _roji else None
_LWC = next((i for i, l in enumerate(m.Layers) if l.Name == '59_1F_便所・倉庫'), None)
if _RJ is not None and _LWC is not None:
    L_PATH = layer('59_1F_路地', (0xE9, 0xDF, 0xCF))     # 10-28（監修の項 20261028-0015 の 19）：名前は name.md の「路地」（前は「通り抜け（こどもの小径）」）
    def _uv_of(x, y):
        d = np.array([x, y]) - C; rr = np.hypot(*d); a = math.atan2(d[1], d[0]) % (2 * math.pi)
        return (TH19 - a) * 205.0, 205.0 - rr / 1000.0
    _del = []; _n = 0
    _targets = [(o.Attributes.Id, o.Geometry) for o in m.Objects if o.Attributes.LayerIndex == _LWC and isinstance(o.Geometry, r.Mesh)]
    for _id, g in _targets:
        V = [_uv_of(g.Vertices[i].X, g.Vertices[i].Y) for i in range(len(g.Vertices))]
        tris = []
        for f in g.Faces:
            # 四角の面（f[3] != f[2]）は二つの三角に分ける（前は f[0..2] だけを見て、四角の面の半分が抜けていた：
            # スパン14の便所の床 約9 m² が消えた、設計監修 10-25）
            for tri in ((f[0], f[1], f[2]),) + (((f[0], f[2], f[3]),) if f[3] != f[2] else ()):
                q = SP([V[tri[0]], V[tri[1]], V[tri[2]]])
                if q.is_valid and q.area > 1e-6: tris.append(q)
        foot = _uu(tris).buffer(0)
        if foot.is_empty or not foot.intersects(_RJ): continue
        _del.append(_id); _n += 1
        for part, li in ((foot.difference(_RJ), _LWC), (foot.intersection(_RJ), L_PATH)):
            for pg in getattr(part, 'geoms', [part]):
                if pg.geom_type == 'Polygon' and pg.area > 0.05:
                    solid_uv(list(pg.exterior.coords)[:-1], 0, 10, li)
    for i in _del: m.Objects.Delete(i)
    print('通り抜けの床を分けた', _n, round(_RJ.area, 1))
m.Write(OUT, 8)
print('written', OUT)
