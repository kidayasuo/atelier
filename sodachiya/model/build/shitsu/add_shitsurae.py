"""本館内のしつらえ（2026-10-21、別チャットの平面図 plan01／plan02／plan04 から）を 3dm に入れる。
平面図スクリプトを P(u,v) 恒等で実行して図形を (u, v)[m] で取り出し（capture.py）、
呼び出し元の行番号ごとに高さを与えて立ち上げる。
  u：南の妻（架構 1、旧 19）から北へ、背骨 r=205 m に沿った長さ [m]
  v：背骨（西の柱の列 r=205 m）から東へ [m]（1.6＝一本の線、12＝東の柱の列、13.5＝ガラス戸、15＝軒先）
高さは FL±0 基準 [mm]（受け取り土間・地面は −300、外縁側・あまのがわは −150）。
python3 -I add_shitsurae.py SCRIPTS_DIR IN.3dm OUT.3dm"""
import sys, math, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/shitsu')
import os as _os0
sys.path.insert(0, _os0.path.join(_os0.path.dirname(_os0.path.dirname(_os0.path.abspath(__file__))), 'south'))
from capture import capture, prep
from shapely.geometry import Polygon as SP, box as sbox, LineString
from shapely.ops import unary_union
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
L_CORK = layer('40k_しつらえ_コルク（あつまりの鉢・ほふくの丘）', (196, 160, 118))   # 10-31：コルク（やわらかい床）
CORK = (0.77, 0.63, 0.46, 1)
L_RAT = layer('40r_しつらえ_吊りかご（籐・綱）', (190, 150, 95))                  # 10-31：籐の吊りかごと綱
RATTAN = (0.75, 0.59, 0.37, 1); RAT_C = (191, 150, 94)
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
    # 10-31（ユーザー、項 20261031-1037-present）：板をやめて、上の横木 30×40（h2260〜2300）＋縦格子 30角（すき間 90 以下、芯 120 以下）
    WD = (0.85, 0.75, 0.6, 1)
    for a, b in [((u0, v1), (ga, v1)), ((gb, v1), (u1, v1)), ((u0, v0), (u0, v1)), ((u1, v0), (u1, v1))]:
        (pa, qa), (pb, qb) = a, b; L = math.hypot(pb - pa, qb - qa); du, dv = (pb - pa) / L, (qb - qa) / L
        nu, nv = -dv * 0.015, du * 0.015                      # 縁の線から両側へ 15（厚さ 30）
        solid_uv([(pa + nu, qa + nv), (pb + nu, qb + nv), (pb - nu, qb - nv), (pa - nu, qa - nv)], 2260, 2300, L_LAT, WD)
        n = max(1, math.ceil((L - 0.03) / 0.12))              # 両端に格子、芯 ≤ 0.12（すき間 ≤ 0.09）
        for k in range(n + 1):
            t = 0.015 + (L - 0.03) * k / n; cu, cv = pa + du * t, qa + dv * t
            solid_uv([(cu - .015, cv - .015), (cu + .015, cv - .015), (cu + .015, cv + .015), (cu - .015, cv + .015)], 1200, 2260, L_LAT, WD)
    # 10-31（ユーザー、項 20261031-1056-present の4）：クッション 0.5×0.5×厚0.25 を4つ。柵（u0・u1・v1 の辺）から0.6以上はなして西の壁寄り
    # （クッションに乗っても柵の上端まで0.85以上）。2×2 にすき間0.1、u は真ん中、v は西の端（v0）から0.05
    um = 0.5 * (u0 + u1)
    for cu in (um - 0.3, um + 0.3):
        for cv in (v0 + 0.30, v0 + 0.90):
            solid_uv([(cu - .25, cv - .25), (cu + .25, cv - .25), (cu + .25, cv + .25), (cu - .25, cv + .25)], 1200, 1450, L_T, (0.80, 0.72, 0.62, 1),
                     'ロフトのクッション 500×500×250')
def loft_step(rec):                  # 家具階段 1段0.2×5（10-24）：ロフトに近い段から 1000・800・600・400・200
    pts = rec['pts']; v = np.mean(pts[:, 1])
    k = int(round((v - 3.725) / 0.25)); h = max(200, 1000 - 200 * k)
    solid_uv([tuple(p) for p in pts], 0, h, L_PL, fc(rec))

# ---- 3〜5歳の保育室の分け方（10-24、ユーザー）：西の半分を架構の線で二つの巣に、東の半分は共有 ----
L_LAT = layer('96b_しつらえ_格子・手すり（木）', (185, 150, 105))
L_FG = layer('48f_しつらえ_すりガラス（2歳のトイレの西）', (220, 230, 236))   # 10-31：乳白ガラス（西館の 19g と同じ素材）
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
    g = g.difference(sbox(SLIDE_U[0], SLIDE_V[0], SLIDE_U[1], SLIDE_V[1]))   # 10-31：真ん中はすべり台（slide01）、段々は両側に
    for (a, b), h in zip(zip(cuts, cuts[1:]), hs):
        piece = g.intersection(sbox(a, v0, b, v1))
        for pc in getattr(piece, 'geoms', [piece]):
            if not pc.is_empty and pc.area > 1e-4: solid_uv(list(pc.exterior.coords)[:-1], 0, h, L_PL, (0.96, 0.95, 0.9, 1))
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
# ---- 0・1歳のしつらえの形（ユーザー 10-31 14:41、決定事項（本館）の0・1歳の「吊りかご×2、ほふくの丘」と段々のすべり台） ----
import katachi as K
def _frame(uc, vc):
    """(u, v) の点の世界座標 [mm] と、そこでの u・v の向き（水平の単位ベクトル、3 次元）"""
    c = W(uc, vc); tv = W(uc + 0.001, vc) - c; rv = W(uc, vc + 0.001) - c
    tv = np.r_[tv / np.linalg.norm(tv), 0.0]; rv = np.r_[rv / np.linalg.norm(rv), 0.0]
    return np.r_[c, 0.0], tv, rv
def _ellipse(au, av):
    """面の 2 次元の楕円（x の半径 au、y の半径 av、mm）の閉じた NURBS 曲線"""
    c = r.NurbsCurve.CreateFromCircle(r.Circle(1.0)); c.Transform(r.Transform.Scale(r.Plane.WorldXY(), float(au), float(av), 1.0)); return c
def _place(b, c, tv, z):
    """局所（x＝u の向き、y＝v の向き、z 上）で作った Brep を、点 c・高さ z へ（z まわりに回して動かす。楕円は y の向きの裏返しに関わらない）"""
    b.Transform(r.Transform.Rotation(math.atan2(tv[1], tv[0]), r.Vector3d(0, 0, 1), r.Point3d(0, 0, 0)))
    b.Transform(r.Transform.Translation(r.Vector3d(float(c[0]), float(c[1]), float(z)))); return b
def _scaled_rev(prof, sx, sy, sz):
    """z 軸まわりに一周させた面（prof は xz の面の曲線）の制御点を軸ごとに縮めた、一枚の閉じた面の Brep（K.tama と同じやり方）"""
    ns = r.RevSurface.Create(prof, r.Line(r.Point3d(0, 0, 0), r.Point3d(0, 0, 1)), 0.0, 2 * math.pi).ToNurbsSurface(); P = ns.Points
    for i in range(P.CountU):
        for j in range(P.CountV):
            p = P[i, j]; P[i, j] = r.Point4d(p.X * sx, p.Y * sy, p.Z * sz, p.W)
    b = r.Brep.CreateFromSurface(ns)
    if b is None or not b.IsSolid: raise ValueError('回転の面が閉じた立体にならない')
    return b
def _beam_bot(v):    # 架構2（u3）の2枚組の梁の下端 [mm]（s4 で測った：v8.5 で 2690、勾配 1/12 で東へ下がる）
    return 2690.0 - (v - 8.5) * 1000.0 / 12.0
def basket(rec):
    # 吊りかご（寝かしつけ用）：籐で編んだ楕円のかご。外 0.50（u）×0.85（v）、底は床から 450、深さ約 0.22（縁の上 675）。
    # 底は二段の板（内へ 35・12 入れて丸みに見せる）、側は厚さ 12 の楕円の筒（外形の押し出し−内形）、縁は丸い太めの輪（管 約φ30、楕円の円環）。
    # 綱 φ12 を縁の四隅（楕円の 45° おき）から上の一点へ4本、そこから一本で梁の下の吊り木（杉 45 角、2枚組の梁の下にまたがる）へ
    uc, vc = (float(x) for x in np.mean(rec['pts'], axis=0)); c, tv, rv = _frame(uc, vc)
    au, av, t = 250.0, 425.0, 12.0
    Yu = rv if np.cross(tv, rv)[2] > 0 else -rv                         # 押し出しは上へ（X×Y が上向き。楕円は y の裏返しに関わらない）
    nm = '吊りかご（籐、外 500×850・深さ 220、底 h450）'
    K.add(m, K.oshidashi(_ellipse(au - 35, av - 35), (), c + np.r_[0, 0, 450.0], tv, Yu, 15.0), L_RAT, RAT_C, nm)
    K.add(m, K.oshidashi(_ellipse(au - t, av - t), (), c + np.r_[0, 0, 465.0], tv, Yu, 15.0), L_RAT, RAT_C, nm)
    K.add(m, K.oshidashi(_ellipse(au, av), (_ellipse(au - t, av - t),), c + np.r_[0, 0, 480.0], tv, Yu, 180.0), L_RAT, RAT_C, nm)
    k_ = 16.0 / ((au - t / 2 + av - t / 2) / 2)                         # 円環の管の半径（単位の円環で）。管の幅は u の端で約12・v の端で約20
    sec = r.NurbsCurve.CreateFromCircle(r.Circle(r.Point3d(0, 0, 0), k_))
    sec.Transform(r.Transform.Rotation(math.pi / 2, r.Vector3d(1, 0, 0), r.Point3d(0, 0, 0))); sec.Transform(r.Transform.Translation(r.Vector3d(1, 0, 0)))
    ring = _place(_scaled_rev(sec, au - t / 2, av - t / 2, 15.0 / k_), c, tv, 660.0)
    K.add(m, ring, L_RAT, RAT_C, '吊りかごの縁（籐の太い輪 約φ30）')
    zt = _beam_bot(vc + 0.0225) - 1.0                                   # 吊り木の上（梁の下端の低い側から 1 mm）
    Y = rv if np.cross(tv, rv)[2] < 0 else -rv                          # 吊り木は下へ（X×Y が下向き）
    o = c - 210.0 * tv - 22.5 * Y
    K.add(m, K.hako(o + np.r_[0, 0, zt], tv, Y, 420.0, 45.0, 45.0), L_HW, (196, 160, 118), '吊りかごの吊り木（杉 45 角、2枚組の梁の下にまたがる）')
    apex = c + np.r_[0, 0, zt - 45.0 - 220.0]
    K.add(m, K.enchu(apex, c + np.r_[0, 0, zt - 45.0], 6.0), L_RAT, RAT_C, '吊りかごの綱 φ12')
    for a_ in (45, 135, 225, 315):
        q = c + (au - t / 2) * math.cos(math.radians(a_)) * tv + (av - t / 2) * math.sin(math.radians(a_)) * rv + np.r_[0, 0, 670.0]
        K.add(m, K.enchu(q, apex, 6.0), L_RAT, RAT_C, '吊りかごの綱 φ12')
def mound01(rec):
    # ほふくの丘：plan01 の楕円（u 1.8×v 2.4）の中に高さ 200 の滑らかな丘。縁から真ん中へ cos のゆるい曲線、縁は床に接して溶ける（接線が水平）、
    # 頂も水平。xz の面の輪郭（上の曲線＋底の線）を一周させ、制御点を u・v の半径に縮めた一枚の閉じた面の Brep。コルク（やわらかい床）
    pts = np.asarray(rec['pts']); uc, vc = (float(x) for x in pts.mean(axis=0))
    ru = (pts[:, 0].max() - pts[:, 0].min()) / 2 * 1000.0; rvv = (pts[:, 1].max() - pts[:, 1].min()) / 2 * 1000.0
    c, tv, rv = _frame(uc, vc)
    ts = np.linspace(0, 1, 9); zs = 100.0 * (1 + np.cos(np.pi * ts)); zs[1] = 200.0; zs[-2] = 0.0
    top = r.NurbsCurve.Create(False, 3, [r.Point3d(float(t_), 0.0, float(z_)) for t_, z_ in zip(ts, zs)])
    prof = r.PolyCurve(); prof.Append(top); prof.Append(r.LineCurve(r.Point3d(1, 0, 0), r.Point3d(0, 0, 0)))
    K.add(m, _place(_scaled_rev(prof, ru, rvv, 1.0), c, tv, 0.0), L_CORK, tuple(int(255 * x) for x in CORK[:3]), 'ほふくの丘 h200（コルク、やわらかい床）')
SLIDE_V = (9.745, 10.255)            # 段々の真ん中のすべり台（縁を含む、すべる面の幅 0.45）
SLIDE_U = (7.2, 9.05)                # 床の手前の水平 u7.2〜7.5、斜面 u7.5〜8.9、上の平ら u8.9〜9.05（段々の上 h450）
def _slide_z(u):
    if u <= 7.5: return 40.0
    if u >= 8.9: return 450.0
    return 40.0 + 205.0 * (1 - math.cos(math.pi * (u - 7.5) / 1.4))
def slide01():
    # すべり台：段々（h450）の上から床へ、すべる面は上で少し平ら → cos のゆるい斜面（最大約25°、長さ1.4）→ 床の手前で水平（h40）。
    # 杉の板の押し出し（u・z の面の輪郭を v の向きに）。両側に立ち上がりの縁（厚さ 30、すべる面から +100、角を丸める）
    um, vm = 0.5 * sum(SLIDE_U), 0.5 * sum(SLIDE_V); c, tv, rv = _frame(um, vm)
    sc = (205.0 - vm) / 205.0                                             # 背骨の弧の長さ → その v の所の長さ
    us = np.r_[np.linspace(SLIDE_U[0], 7.5, 3), np.linspace(7.5, 8.9, 23)[1:], SLIDE_U[1]]
    ez = np.r_[0, 0, 1.0]
    def piece(v0, v1, dz, name):
        prof = [((u - um) * 1000.0 * sc, _slide_z(u) + dz) for u in us] + [((SLIDE_U[1] - um) * 1000.0 * sc, 0.0), ((SLIDE_U[0] - um) * 1000.0 * sc, 0.0)]
        prof = prof[::-1]
        d = 1.0 if np.cross(tv, ez) @ rv > 0 else -1.0
        o = c + (v0 - vm) * 1000.0 * rv
        K.add(m, K.oshidashi(prof, (), o, tv, ez, d * (v1 - v0) * 1000.0), L_PL, (222, 196, 150), name)
    piece(SLIDE_V[0] + 0.03, SLIDE_V[1] - 0.03, 0.0, 'すべり台（杉、幅 450、h450 から床へ）')
    piece(SLIDE_V[0], SLIDE_V[0] + 0.03, 100.0, 'すべり台の縁（杉 30、すべる面から +100、角を丸める）')
    piece(SLIDE_V[1] - 0.03, SLIDE_V[1], 100.0, 'すべり台の縁（杉 30、すべる面から +100、角を丸める）')
slide01()

# ---- 2歳の部屋のしつらえ（ユーザー 10-31 15:04、決定事項（本館）の「2歳（スパン5–6）」） ----
import trimesh as _tm, manifold3d as _mf
def _tm_add(t, li, col, name):
    """trimesh（頂点は世界の mm）を閉じたメッシュとして 3dm へ"""
    M = r.Mesh()
    for p_ in t.vertices: M.Vertices.Add(float(p_[0]), float(p_[1]), float(p_[2]))
    for f in t.faces: M.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
    M.Normals.ComputeNormals(); M.Compact()
    a_ = attr(li, col); a_.Name = name; m.Objects.AddMesh(M, a_)
def _mf_of(V, F):
    t = _tm.Trimesh(V, F, process=True); t.merge_vertices(); t.fix_normals()
    if not (t.is_watertight and t.is_winding_consistent): raise ValueError('閉じていない形')
    return _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def _prism_local(poly_xy, z0, z1):
    """局所（mm）の平らな輪郭の押し出し（manifold）"""
    return _mf.Manifold.extrude(_mf.CrossSection([np.asarray(poly_xy, float)]), z1 - z0).translate((0, 0, z0))
YAMA = dict(uw=17.95, vc=9.6, ru=1.9, re=2.2, rw=1.3, H=900.0, kc=0.66, cliff=(0.58, 0.73), hc=350.0)
def _yama_z(k, t):
    """山の高さ [mm]：楕円の半径の割合 k（0＝頂、1＝裾）と角 t（0＝東、π＝西）。ドーム 1−k²（南 約1:2・東 約1:2.4）、
    肩の崖（k0.66、t 0.58π〜0.73π、両端 0.05π で消える）の外は 350 低い（切り立つ面）"""
    Y = YAMA; z = Y['H'] * (1 - k * k)
    if k > Y['kc'] + 1e-9:
        a, b = Y['cliff']; f = t / math.pi
        w = 1.0 if a <= f <= b else max(0.0, 1 - min(abs(f - a), abs(f - b)) / 0.05)
        z -= Y['hc'] * w * (1 - k) / (1 - Y['kc'])
    return max(z, 0.0)
def yama02(rec, _done=[]):
    # 2歳の山（図の11）：plan02 の等高線（hill(k)、北の壁 u17.95 に背をつけた半楕円、南 1.9・東 2.2・西 1.3）の外形のまま、滑らかな山。
    # 中は空洞のかくれ家（楕円 u0.84×v1.1、天井は山の面から 100 下で上限 h800：奥 0.8・手前 約0.6）、入口は西（幅0.5・高さ0.6、上は半円）、
    # 東に覗き穴 φ130 を2つ（h450、先生が膝をついてのぞく）。自由な形の閉じたメッシュ（やわらかい床、L_PL）。等高線の3つの輪から一度だけ作る
    if _done: return
    _done.append(1)
    Y = YAMA; uc, vc = Y['uw'], Y['vc']
    ks = sorted(set(np.r_[np.linspace(0, Y['kc'], 8), np.linspace(Y['kc'], 1, 6)]))
    ts = np.linspace(0, math.pi, 41)
    def loc(k, t):   # 局所 mm（x＝u−uw、y＝v−vc）
        rr = Y['re'] if math.cos(t) >= 0 else Y['rw']
        return (-Y['ru'] * k * math.sin(t) * 1000.0, rr * k * math.cos(t) * 1000.0)
    V = [(0.0, 0.0, Y['H'])]; idx = {}
    for i, k in enumerate(ks[1:], 1):
        for j, t in enumerate(ts):
            x, y = loc(k, t)
            if abs(k - Y['kc']) < 1e-9:      # 崖の輪：上（内）と下（外）の二つの点
                idx[(i, j, 'in')] = len(V); V.append((x, y, Y['H'] * (1 - k * k)))
                idx[(i, j, 'out')] = len(V); V.append((x, y, _yama_z(k + 1e-7, t)))
            else:
                idx[(i, j)] = len(V); V.append((x, y, _yama_z(k, t)))
    def vid(i, j, side):
        return idx.get((i, j, side), idx.get((i, j)))
    F = []
    n = len(ts); last = len(ks) - 1
    for j in range(n - 1):
        F.append((0, vid(1, j, 'in'), vid(1, j + 1, 'in')))
    for i in range(1, last):
        for j in range(n - 1):
            a, b = vid(i, j, 'out'), vid(i, j + 1, 'out'); c, d = vid(i + 1, j + 1, 'in'), vid(i + 1, j, 'in')
            F += [(a, d, c), (a, c, b)]
        if abs(ks[i] - Y['kc']) < 1e-9:       # 崖の面（内の輪 → 外の輪）
            for j in range(n - 1):
                a, b = vid(i, j, 'in'), vid(i, j + 1, 'in'); c, d = vid(i, j + 1, 'out'), vid(i, j, 'out')
                F += [(a, d, c), (a, c, b)]
    # 底（z0）と背の面（壁 u17.95 の面、t＝0 と π の縁）
    nb = len(V); 
    for j in range(n): x, y, _ = V[vid(last, j, None)]; V.append((x, y, 0.0))
    for j in range(1, n - 1): F.append((nb, nb + j + 1, nb + j))
    back = [vid(i, n - 1, s_) for i in range(last, 0, -1) for s_ in (('out', 'in') if abs(ks[i] - Y['kc']) < 1e-9 else (None,))] + [0] + \
           [vid(i, 0, s_) for i in range(1, last + 1) for s_ in (('in', 'out') if abs(ks[i] - Y['kc']) < 1e-9 else (None,))]
    # 背の面：裾の両端は底の点と同じ（z0）なので、上の縁の点の並びを扇で閉じる
    for q in range(1, len(back) - 1): F.append((back[0], back[q], back[q + 1]))
    t_ = _tm.Trimesh(np.array(V), np.array(F), process=True); t_.merge_vertices(); t_.update_faces(t_.nondegenerate_faces()); t_.fix_normals()
    if not t_.is_watertight: raise ValueError('山の網が閉じていない')
    M = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(t_.vertices, np.float32), tri_verts=np.asarray(t_.faces, np.uint32)))
    # かくれ家：楕円（中心 u17.50・v9.6、半径 u0.42・v0.55）、天井＝山の面−100（上限 800）
    cu, au, av = 17.50, 0.42, 0.55
    HV = [(( cu - uc) * 1000.0, 0.0, min(800.0, Y['H'] - 100.0))]; HF = []
    hr, ht = np.linspace(0, 1, 6)[1:], np.linspace(0, 2 * math.pi, 33)[:-1]
    def zin(x, y):
        uu = x / 1000.0; vv = y / 1000.0
        rr = Y['re'] if vv >= 0 else Y['rw']; kx = -uu / Y['ru']; ky = vv / rr
        k = math.hypot(kx, ky); t = math.atan2(kx, ky)
        return min(800.0, _yama_z(min(k, 1.0), t) - 100.0)
    for a_ in hr:
        for b_ in ht:
            x = (cu - uc) * 1000.0 + au * 1000.0 * a_ * math.cos(b_); y = av * 1000.0 * a_ * math.sin(b_)
            HV.append((x, y, zin(x, y)))
    nt_ = len(ht)
    for j in range(nt_): HF.append((0, 1 + j, 1 + (j + 1) % nt_))
    for i in range(len(hr) - 1):
        for j in range(nt_):
            a, b = 1 + i * nt_ + j, 1 + i * nt_ + (j + 1) % nt_; c, d = a + nt_, b + nt_
            HF += [(a, c, d), (a, d, b)]
    o = len(HV); edge = list(range(1 + (len(hr) - 1) * nt_, 1 + len(hr) * nt_))
    for e in edge: HV.append((HV[e][0], HV[e][1], -20.0))
    for j in range(nt_):
        a, b = edge[j], edge[(j + 1) % nt_]; c, d = o + j, o + (j + 1) % nt_
        HF += [(a, c, d), (a, d, b)]
    oc = len(HV); HV.append(((cu - uc) * 1000.0, 0.0, -20.0))
    for j in range(nt_): HF.append((oc, o + (j + 1) % nt_, o + j))
    M = M - _mf_of(np.array(HV), np.array(HF))
    # 入口（西）：幅0.5（u17.25〜17.75）、高さ0.6（箱 h350＋半径250 の半円）、v7.9〜9.3
    x0, x1 = (17.25 - uc) * 1000.0, (17.75 - uc) * 1000.0; y0, y1 = (7.9 - vc) * 1000.0, (9.3 - vc) * 1000.0
    tun = _prism_local([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], -20.0, 350.0)
    cyl = _mf.Manifold.cylinder(y1 - y0, 250.0, 250.0, 48).rotate((-90.0, 0.0, 0.0)).translate(((x0 + x1) / 2, y0, 350.0))
    M = M - (tun + cyl)
    # 覗き穴（東）：φ130 を2つ、h450、u17.35・17.68、v9.9〜12.2
    for uh in (17.35, 17.68):
        M = M - _mf.Manifold.cylinder(2300.0, 65.0, 65.0, 24).rotate((-90.0, 0.0, 0.0)).translate(((uh - uc) * 1000.0, (9.9 - vc) * 1000.0, 450.0))
    mm_ = M.to_mesh(); VV = np.asarray(mm_.vert_properties[:, :3], float); FF = np.asarray(mm_.tri_verts, int)
    W3 = np.array([(*W(uc + x / 1000.0, vc + y / 1000.0), z) for x, y, z in VV])
    t2 = _tm.Trimesh(W3, FF, process=False)
    print('山の網', len(FF), '面', '閉じている', t2.is_watertight)
    _tm_add(t2, L_PL, (0.80, 0.86, 0.66, 1), '山（頂 h900、肩に崖 h350、中はかくれ家・入口は西・東に覗き穴、やわらかい床）')
def _hk(c, tv, rv, x0, x1, y0, y1, z0, z1):
    """局所（c から u の向き x・v の向き y、mm）の直方体。上下は z（mm）。v の向きの裏返しにかかわらず y は rv の向き"""
    Yv = rv if np.cross(tv, rv)[2] > 0 else -rv; sg = 1.0 if Yv @ rv > 0 else -1.0
    ya, yb = sorted((sg * y0, sg * y1))
    return K.hako(c + x0 * tv + ya * Yv + np.r_[0, 0, z0], tv, Yv, x1 - x0, yb - ya, z1 - z0)
def tipi02(rec):
    # 落ち着くくぼみ（図の13、竪穴）の囲い h1000（kubomi）の上にティピ（ユーザー 10-31）：細い木の柱 φ30 を6本、囲いの上端の六角形の頂点から
    # 円錐に立てて頂（u17.41・v3.95、h1900）で束ね、150 上に出す。布（生成りの帆布、厚さ 4）は六角錐の6枚の平らな板。
    # 入口は南（先生の記録台・部屋から見える側）：囲いの開口（v3.55〜4.35、h1000）の上の布を三角にめくった形に開ける（h1000〜1300）
    B = [(16.9, 3.5), (17.41, 3.3), (17.92, 3.5), (17.92, 4.4), (17.41, 4.6), (16.9, 4.4)]
    A = np.r_[W(17.41, 3.95), 1900.0]; zb = 1000.0
    P3 = [np.r_[W(u, v), zb] for u, v in B]; Cax = np.r_[W(17.41, 3.95), zb]
    for i in range(6):
        p0, p1 = P3[i], P3[(i + 1) % 6]
        X = (p1 - p0) / np.linalg.norm(p1 - p0); Yr = A - p0; Yr = Yr - (Yr @ X) * X; Y = Yr / np.linalg.norm(Yr)
        q = lambda p_: ((p_ - p0) @ X, (p_ - p0) @ Y)
        poly = [q(p0), q(p1), q(A)]
        if B[i][0] == 16.9 and B[(i + 1) % 6][0] == 16.9:            # 南の面：入口の上を三角にめくる
            L_ = np.linalg.norm(p1 - p0); hA = q(A)[1]; hN = 300.0 / 900.0 * hA
            poly = [q(p0), (L_ / 2 - 250.0, 0.0), (L_ / 2, hN), (L_ / 2 + 250.0, 0.0), q(p1), q(A)]
        nrm = np.cross(X, Y); cen = (p0 + p1 + A) / 3
        h = 4.0 if nrm @ (np.r_[Cax[:2], 1400.0] - cen) > 0 else -4.0
        K.add(m, K.oshidashi(poly, (), p0, X, Y, h), L_T, (238, 232, 218), 'ティピの布（生成りの帆布）')
    for p0 in P3:
        d = A - p0; d /= np.linalg.norm(d); inw = Cax - p0; inw[2] = 0; inw /= np.linalg.norm(inw)
        K.add(m, K.enchu(p0 + 22.0 * inw, A + 150.0 * d, 15.0), L_F, (196, 160, 118), 'ティピの柱（木 φ30）')
def stool02():
    # 先生の記録台（図の14、立ち机 h900、u17.3〜17.95・v1.75〜3.0）の前に高い腰掛け（ユーザー 10-31）：座 340角 h620〜650、脚 30角×4、
    # 足掛け 20角 h300（四方）、低い背もたれ（南の辺、座から 200、h650〜850）。先生は記録台（北）を向いて座る。杉
    c, tv, rv = _frame(17.02, 2.375); W_ = (196, 160, 118); nm = '先生の高い腰掛け（座 h650、背もたれ、足掛け）'
    K.add(m, _hk(c, tv, rv, -170, 170, -170, 170, 620, 650), L_F, W_, nm)
    for x_ in (-170, 140):
        for y_ in (-170, 140):
            K.add(m, _hk(c, tv, rv, x_, x_ + 30, y_, y_ + 30, 0, 620), L_F, W_, nm)
    for y_ in (-170, 150): K.add(m, _hk(c, tv, rv, -140, 140, y_, y_ + 20, 290, 310), L_F, W_, nm)
    for x_ in (-170, 150): K.add(m, _hk(c, tv, rv, x_, x_ + 20, -140, 140, 290, 310), L_F, W_, nm)
    K.add(m, _hk(c, tv, rv, -170, -145, -150, 150, 650, 850), L_F, W_, nm)
L_CL = layer('40w_しつらえ_干した布（白）', (244, 242, 236))
def drying_poles():
    # 0・1歳（スパン4）と2歳（スパン6）の西吹き抜けの物干し（ユーザー 10-31）：竹竿 φ35 を2本ずつ、架構の線の梁（2枚組の内の板）から
    # 両端の昇降の綱 φ6 で h3100 に（越屋根の下、梁の下端 約3.3〜3.37 の下）。天井扇（羽根 h2800、各スパンの真ん中 φ1.1）をよけて、
    # 竿の両端寄りに白い布（タオル・シーツ・おむつ布、厚さ 40 で竿を包んで垂れた形）。布の下端は h1900 より上
    zp = 3100.0
    for u0, u1, poles in ((9.14, 11.86, ((0.4, [(9.22, 9.57, 350), (9.62, 9.92, 600), (11.12, 11.47, 350), (11.5, 11.8, 600)]),
                                          (1.2, [(9.2, 9.9, 700), (11.15, 11.8, 900)]))),
                          (15.14, 17.86, ((0.4, [(15.22, 15.52, 600), (15.57, 15.92, 350), (17.12, 17.42, 600), (17.47, 17.8, 350)]),
                                          (1.0, [(15.2, 15.9, 700), (17.12, 17.8, 900)])))):
        for vp, cloths in poles:
            a, b = np.r_[W(u0, vp), zp], np.r_[W(u1, vp), zp]
            K.add(m, K.enchu(a, b, 17.5), L_HW, (196, 170, 120), '物干しの竹竿 φ35')
            zt = 2690.0 - (vp - 8.5) * 1000.0 / 12.0 - 1.0
            for ue in (u0 + 0.02, u1 - 0.02):
                K.add(m, K.enchu(np.r_[W(ue, vp), zp + 17.5], np.r_[W(ue, vp), zt], 3.0), L_RAT, RAT_C, '物干しの昇降の綱 φ6')
            for ua, ub, drop in cloths:
                K.add(m, K.hako_uv(ua, ub, vp - 0.02, vp + 0.02, zp + 20.0 - drop, zp + 20.0), L_CL, (244, 242, 236), '干した布（タオル・シーツ・おむつ布）')
def toilet_wall02(rec):
    # 2歳のトイレの西の壁（西吹き抜けの側、v1.6〜1.72）：トイレの所（u12.06〜14.63）は h1200 から上をすりガラス＋木の縦格子に（ユーザー 10-31：
    # 明るく、天袋はなし）。ガラスは壁の中ほど（t10）、格子 30角・すき間 90（芯 120）を西吹き抜けの側（壁の面から 5 はなす）、上下に横木 30角
    g = SP(clean(rec['pts'])); u0, v0, u1, v1 = g.bounds
    ta, tb = 12.06, 14.63
    def bx_uv(a0, a1, b0, b1, z0, z1, li, col, name): solid_uv([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], z0, z1, li, col, name)
    for a, b in ((u0, ta), (tb, u1)):
        if b - a > 0.01: solid_uv([(a, v0), (b, v0), (b, v1), (a, v1)], 0, 2400, L_P)
    solid_uv([(ta, v0), (tb, v0), (tb, v1), (ta, v1)], 0, 1200, L_P)
    bx_uv(ta, tb, 1.655, 1.665, 1200, 2400, L_FG, (0.92, 0.94, 0.95, 1), 'すりガラス（2歳のトイレの西、h1200〜2400）')
    for z0, z1 in ((1200, 1230), (2370, 2400)):
        bx_uv(ta, tb, 1.565, 1.595, z0, z1, L_LAT, (0.85, 0.75, 0.6, 1), 'トイレの西の格子の横木（杉 30角）')
    for uu in np.arange(ta + 0.045, tb - 0.04, 0.12):
        bx_uv(uu, uu + 0.03, 1.565, 1.595, 1230, 2370, L_LAT, (0.85, 0.75, 0.6, 1), 'トイレの西の縦格子（杉 30角、すき間 90）')

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
    158: basket, 162: mound01,                            # 163（丘の上の段 h120〜200）：10-31 から mound01 の一つの滑らかな丘
    166: ('solid', 0, 600, L_F), 171: ('table', 350, L_F), 173: ('solid', 0, 200, L_F), 174: ('solid', 0, 200, L_F),
    178: cot, 180: ('solid', 0, 800, L_F), 183: ('solid', 0, 900, L_F),
    187: ('solid', 0, 850, L_WC), 189: ('solid', 0, 850, L_WC), 190: ('solid', 0, 850, L_F),
    195: ('solid', 2400, 2700, L_HW),
    200: steps01,                                         # 203（段々の南の低い台）：10-31 から真ん中のすべり台（slide01）
    205: ('solid', 0, 12, L_WC), 206: ('solid', 0, 850, L_WC),
    209: ('panel', 0, 900, 0.03, L_P), 211: ('panel', 0, 900, 0.03, L_P), 212: ('panel', 0, 900, 0.03, L_P),
}
T02 = {   # plan02（2歳、12 ≤ u ≤ 18.07）
    80: ('solid', 0, 8, L_T),
    89: ('solid', 0, 2400, L_P), 92: toilet_wall02, 93: ('solid', 0, 2400, L_P), 94: ('solid', 0, 2400, L_P),
    98: ('solid', 0, 2400, L_P),
    103: ('solid', 0, 100, L_WC), 106: ('solid', 0, 500, L_WC), 107: ('solid', 0, 260, L_WC),
    109: ('panel', 0, 900, 0.03, L_WC), 110: ('solid', 0, 300, L_F),
    113: ('solid', 0, 900, L_F), 116: ('solid', 0, 250, L_F), 118: ('solid', 0, 900, L_F),
    120: kubomi, 123: tipi02,                             # 10-31：くぼみ（竪穴）の上にティピ（前は 60°の切妻 hut_roof）
    125: ('solid', 0, 500, L_WC), 129: ('solid', 0, 600, L_F), 130: ('solid', 0, 15, L_T),
    133: ('table', 400, L_F), 135: ('solid', 0, 220, L_F), 136: ('solid', 0, 220, L_F),
    140: cot, 142: ('solid', 0, 15, L_T), 144: mamagoto_posts, 145: ('solid', 1400, 1430, L_F), 146: ('solid', 0, 550, L_F),
    148: ('solid', 0, 1500, L_F), 161: yama02,            # 10-31：山は一つの滑らかな網（崖 h350・かくれ家・入口・覗き穴を含む）。166（崖の板）は yama02 の中
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
    357: koshi_wall,                                       # 腰の壁＋格子（363 の移動式の低い腰壁はやめた、ユーザー 10-31）
    364: canopy, 368: hang_bar,                                 # 布の天蓋／吊り桟 h2000（10-30）
    372: ('solid', 0, 1000, L_F), 376: ('solid', 0, 900, L_F),        # 379（あつまりの楕円の敷物）：10-31 から下の atsumari_hachi（浅い鉢）
    396: ('solid', 0, 1200, L_F),                         # 絵本の通りの棚
    398: ('solid', 0, 300, L_F), 399: ('panel', 300, 1300, 0.01, L_T), 400: ('solid', 300, 420, L_T),
    # 406〜408（本の奥の格子の引き戸・畳・足入れ）：10-31 から下の hon_no_oku（掘りごたつの溝・畳の座・框・暖簾）
    # 414（本の奥のクッション、円柱）：10-31 から hon_no_oku の背のクッション（箱）
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
stool02(); drying_poles()                                         # 10-31：2歳の先生の腰掛け・0〜2歳の西吹き抜けの物干し（plan01 の 193 の竿の板の代わり）

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

# ---------------- 3〜5歳：糸の衝立・KAPLAの箱（10-31 ユーザー、項 20261031-1056-present の3・5、決定事項（本館）の3〜5歳） ----------------
# 部屋は plan04 の room(a, b, …, mir) と同じ（3歳 u33〜39、4歳 u42〜48、5歳 u51〜57 は鏡像）。s は机の側の間仕切りからの距離
def hexa(c8, li, col=None, name=None):          # 8点（下の4点・上の4点、同じ回り）の閉じた六面体
    M = r.Mesh()
    for q in c8: M.Vertices.Add(float(q[0]), float(q[1]), float(q[2]))
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)): M.Faces.AddFace(*f)
    M.Normals.ComputeNormals(); M.Compact()
    a_ = attr(li, col)
    if name: a_.Name = name
    m.Objects.AddMesh(M, a_)
def rod(u, v, z0, z1, rad, li, col=None, name=None):   # 縦の丸棒（閉じた押し出し）
    x, y = W(u, v); _ext(r.Circle(r.Point3d(float(x), float(y), 0.0), rad * 1000.0).ToNurbsCurve(), z0, z1, li, name, col)
def bx_uv(u0_, u1_, v0_, v1_, z0, z1, li, col=None, name=None):
    u0_, u1_ = sorted([u0_, u1_]); v0_, v1_ = sorted([v0_, v1_])
    solid_uv([(u0_, v0_), (u1_, v0_), (u1_, v1_), (u0_, v1_)], z0, z1, li, col, name)
WOODC = (0.85, 0.75, 0.6, 1); BLACK = (0.08, 0.08, 0.08, 1); THREAD = (0.93, 0.90, 0.84, 1)
# 糸の衝立（案A）：食卓の所の真ん中の梁（架構の線 s3）の下、v9.1〜11.5（食卓の2列の真ん中 v10.3 に、長さ2.4）。屏風形の木の枠 1.2×2枚（h1000、見付け30）、
# 柱 30角、上の横木 h970〜1000・下の横木 h100〜130、脚（柱ごとに s±0.15 の足、h0〜30）。枠の中に縦の糸 φ3 を 20 おき（ぐっと押し広げれば通れる）。
# 両端（南 v9.1 の手前・北 v11.5〜12）は食卓のあいだを通れるようにあける
SCR_V0, SCR_P = 9.1, 1.2
def ito_tsuitate(a, b, mir):
    S = (lambda s_: b - s_) if mir else (lambda s_: a + s_)
    us = S(3.0)
    for k in range(2):
        p0 = SCR_V0 + SCR_P * k + (0.0025 if k else 0.0); p1 = SCR_V0 + SCR_P * (k + 1) - (0.0025 if k == 0 else 0.0)
        for pv in (p0 + 0.015, p1 - 0.015):
            bx_uv(us - .015, us + .015, pv - .015, pv + .015, 0, 1000, L_F, WOODC, '糸の衝立の柱 30角 h1000')
            bx_uv(us - .15, us - .015, pv - .015, pv + .015, 0, 30, L_F, WOODC, '糸の衝立の脚')
            bx_uv(us + .015, us + .15, pv - .015, pv + .015, 0, 30, L_F, WOODC, '糸の衝立の脚')
        bx_uv(us - .015, us + .015, p0 + .03, p1 - .03, 970, 1000, L_F, WOODC, '糸の衝立の上の横木 30角')
        bx_uv(us - .015, us + .015, p0 + .03, p1 - .03, 100, 130, L_F, WOODC, '糸の衝立の下の横木 30角')
        n = int((p1 - p0 - 0.06) / 0.02)
        for i in range(n):
            vv = p0 + 0.03 + (p1 - p0 - 0.06) * (i + 0.5) / n
            rod(us, vv, 130, 970, 0.0015, L_T, THREAD, '糸の衝立の糸 φ3')
# KAPLAの箱（KAPLA 1000の木の箱、ユーザーの写真）：0.42×0.42×h0.45（キャスター含む）。デン（ロフトの下）の口（v3.6、家具階段 s3.4〜4.2 の北）の脇、
# s5.3〜5.72・v3.7〜4.12（家具階段・通り道をふさがない、個人棚 v5.2〜 の手前）。キャスター4つ φ50 h60、箱 h60〜430、ふた h430〜450、
# 黒い帯2本（幅30、厚3、h130〜160・330〜360）、両脇（u の向きの面）に縄の取っ手、部屋の側の面（v の東）に「KAPLA」（プレゼンの準備の追記 10:59）
def kapla_box(a, b, mir):
    S = (lambda s_: b - s_) if mir else (lambda s_: a + s_)
    U0, U1 = sorted([S(5.3), S(5.72)]); V0, V1 = 3.7, 4.12
    for cu in (U0 + .045, U1 - .045):
        for cv in (V0 + .045, V1 - .045): rod(cu, cv, 0, 60, 0.025, L_F, BLACK, 'KAPLAの箱のキャスター φ50')
    bx_uv(U0, U1, V0, V1, 60, 430, L_F, WOODC, 'KAPLAの箱 420×420（KAPLA 1000）')
    bx_uv(U0, U1, V0, V1, 430, 450, L_F, WOODC, 'KAPLAの箱のふた')
    t = 0.003
    for z0 in (130, 330):
        z1 = z0 + 30
        bx_uv(U0 - t, U1 + t, V0 - t, V0, z0, z1, L_T, BLACK, 'KAPLAの箱の黒い帯'); bx_uv(U0 - t, U1 + t, V1, V1 + t, z0, z1, L_T, BLACK, 'KAPLAの箱の黒い帯')
        bx_uv(U0 - t, U0, V0, V1, z0, z1, L_T, BLACK, 'KAPLAの箱の黒い帯'); bx_uv(U1, U1 + t, V0, V1, z0, z1, L_T, BLACK, 'KAPLAの箱の黒い帯')
    # 縄の取っ手：u の向きの両面の真ん中、h250〜290。面から出る2本と横の1本（12角の縄、コの字）
    vm = 0.5 * (V0 + V1)
    for uf, sg in ((U0, -1), (U1, 1)):
        for vv in (vm - .07, vm + .07):
            bx_uv(uf, uf + sg * .04, vv - .006, vv + .006, 264, 276, L_F, (0.72, 0.6, 0.4, 1), 'KAPLAの箱の縄の取っ手')
        bx_uv(uf + sg * .028, uf + sg * .04, vm - .064, vm + .064, 264, 276, L_F, (0.72, 0.6, 0.4, 1), 'KAPLAの箱の縄の取っ手')
    # 「KAPLA」：部屋の側の面（v = V1）に厚さ2の黒い字、高さ90（h195〜285）、字の幅50・字送り65、u の向きに左から右（東から見て北が右）
    hs = 0.006; Z0, Z1 = 195.0, 285.0
    def stroke(x0, z0, x1, z1):
        dx, dz = x1 - x0, (z1 - z0) / 1000.0; L = math.hypot(dx, dz); nx, nz = -dz / L * hs, dx / L * hs
        quad = [(x0 + nx, z0 + nz * 1000), (x1 + nx, z1 + nz * 1000), (x1 - nx, z1 - nz * 1000), (x0 - nx, z0 - nz * 1000)]
        bot = [(*W(xu, V1), zz) for xu, zz in quad]; top = [(*W(xu, V1 + 0.002), zz) for xu, zz in quad]
        hexa(bot + top, L_T, BLACK, 'KAPLAの箱の字')
    xs0 = 0.5 * (U0 + U1) - (5 * 0.05 + 4 * 0.015) / 2
    zm = 0.5 * (Z0 + Z1)
    glyph = {
        'K': [(0, Z0, 0, Z1), (0.012, zm, 0.05, Z1), (0.012, zm, 0.05, Z0)],
        'A': [(0, Z0, 0.025, Z1), (0.025, Z1, 0.05, Z0), (0.012, zm - 10, 0.038, zm - 10)],
        'P': [(0, Z0, 0, Z1), (0.006, Z1 - 6, 0.044, Z1 - 6), (0.044, Z1 - 6, 0.044, zm + 6), (0.044, zm + 6, 0.006, zm + 6)],
        'L': [(0, Z0, 0, Z1), (0.006, Z0 + 6, 0.05, Z0 + 6)],
    }
    for i, ch in enumerate('KAPLA'):
        x = xs0 + 0.065 * i
        for x0, z0, x1, z1 in glyph[ch]: stroke(x + x0, z0, x + x1, z1)
for _a, _b, _mir in ((33, 39, False), (42, 48, False), (51, 57, True)):
    ito_tsuitate(_a, _b, _mir); kapla_box(_a, _b, _mir)

# ---------------- あつまりの浅い鉢（ユーザー 10-31、項 20261031-1056-present の2、決定事項（本館）の「あつまりの浅い鉢」） ----------------
# 楕円の敷物（plan04 の Ellipse）の代わり。部屋の真ん中 u（3歳 36・4歳 45・5歳 54）、v7.5（腰の壁の東の端 v6.2 と食卓の椅子 v8.8 のあいだ、両側に約0.16）。
# 外径 φ2.4（正十角形の外接円、一辺 0.74＝こども2人）。縁は幅 0.35 の平らな輪 h250、そこから円錐の斜面で真ん中の平らな所 φ1.0（h12、コルク）へ下がる。
# 平らな面だけの閉じた立体（側面10・縁1・斜面10・真ん中1・底1＝23面。12角より少なくして段10で回転体・楕円にしない）。コルクのレイヤー 40k
def atsumari_hachi(uc, vc, R=1.2, Ri=0.85, Rc=0.5, h=250, hc=12, n=10):
    c = W(uc, vc); ex = W(uc + 0.01, vc) - c; ey = W(uc, vc + 0.01) - c
    ex /= np.linalg.norm(ex); ey /= np.linalg.norm(ey)
    if ex[0] * ey[1] - ex[1] * ey[0] < 0: ey = -ey                   # 上から見て反時計回りの組に
    def ring(rad, z): return [(*(c + rad * 1000.0 * (math.cos(2 * math.pi * k / n) * ex + math.sin(2 * math.pi * k / n) * ey)), z) for k in range(n)]
    M = r.Mesh()
    for q in ring(R, 0) + ring(R, h) + ring(Ri, h) + ring(Rc, hc):
        M.Vertices.Add(float(q[0]), float(q[1]), float(q[2]))
    B, T, I, Cn = (lambda k: k % n), (lambda k: n + k % n), (lambda k: 2 * n + k % n), (lambda k: 3 * n + k % n)
    for k in range(n):
        M.Faces.AddFace(B(k), B(k + 1), T(k + 1), T(k))            # 外の側面
        M.Faces.AddFace(T(k), T(k + 1), I(k + 1), I(k))            # 縁の平らな輪
        M.Faces.AddFace(I(k), I(k + 1), Cn(k + 1), Cn(k))          # 円錐の斜面
    for k in range(1, n - 1):
        M.Faces.AddFace(Cn(0), Cn(k), Cn(k + 1))                   # 真ん中の平らな所
        M.Faces.AddFace(B(0), B(k + 1), B(k))                      # 底
    M.Normals.ComputeNormals(); M.Compact()
    a_ = attr(L_CORK, CORK); a_.Name = 'あつまりの浅い鉢 φ2400（コルク、縁 h250）'
    m.Objects.AddMesh(M, a_)
for _uc in (36.0, 45.0, 54.0):
    atsumari_hachi(_uc, 7.5)

# ---------------- 本の奥（スパン18–19、西吹き抜けの北の行き止まり）（ユーザー 10-31 14:21、決定事項（本館）の「本の奥」） ----------------
# 掘りごたつの溝は窓際（西の外壁の内面 v−0.2 〜 0.72、底 −300＝低い窓の下端、南の端 u51.6〜51.9 は段 −150。床の塊は south/add_floor.py で抜く）。
# 畳の座は部屋の壁の側に一つ（v0.75〜1.54、h0〜50、u51.6〜57.0）。座の縁に角を丸めた杉の框 30（v0.72〜0.75、−450〜50）、南の段の鼻に框。
# こどもは座の縁に腰掛けて溝に足を下ろし、低い窓と読書の庭を目の前に見る。クッションは座の奥（部屋の壁 v1.54 の前）に背もたれとして6つ
# （u0.5×厚0.25×h0.5、座の上 h50〜550、壁から 10 はなす）。入口（架構51の柱の北の面 u51.12）は暖簾（幅いっぱい、竿 h2000〜2025、布 h1200〜2000、3枚）
HON_CUSH = [(0.94, 0.80, 0.72, 1), (0.91, 0.84, 0.90, 1), (0.85, 0.90, 0.80, 1)]
def hon_no_oku():
    bx_uv(51.6, 57.0, 0.75, 1.54, 0, 50, L_T, (0.86, 0.82, 0.62, 1), '本の奥の畳の座（部屋の壁の側）')
    bx_uv(51.6, 57.0, 0.72, 0.75, -450, 50, L_P, WOODC, '本の奥の座の縁の框（杉 30、角を丸める）')
    bx_uv(51.6, 51.63, -0.199, 0.72, -160, 0, L_P, WOODC, '本の奥の溝の南の段の鼻（杉 30）')
    for k, uc in enumerate((52.25, 53.1, 53.95, 54.8, 55.65, 56.5)):
        bx_uv(uc - 0.25, uc + 0.25, 1.28, 1.53, 50, 550, L_T, HON_CUSH[k % 3], '本の奥の背のクッション 500×250×h500')
    bx_uv(51.105, 51.13, -0.199, 1.539, 2000, 2025, L_F, WOODC, '本の奥の暖簾の竿')
    ws = [(-0.199, 0.375), (0.385, 0.955), (0.965, 1.539)]
    for v0_, v1_ in ws:
        bx_uv(51.115, 51.12, v0_, v1_, 1200, 2000, L_T, (0.62, 0.45, 0.58, 1), '本の奥の入口の暖簾（裾 h1200）')
hon_no_oku()

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
