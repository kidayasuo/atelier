"""本館内のしつらえ（2026-10-21、別チャットの平面図 plan01／plan02／plan04 から）を 3dm に入れる。
平面図スクリプトを P(u,v) 恒等で実行して図形を (u, v)[m] で取り出し（capture.py）、
呼び出し元の行番号ごとに高さを与えて立ち上げる。
  u：南の妻（架構 1、旧 19）から北へ、背骨 r=205 m に沿った長さ [m]
  v：背骨（西の柱の列 r=205 m）から東へ [m]（1.6＝一本の線、12＝東の柱の列、13.5＝ガラス戸、15＝軒先）
高さは FL±0 基準 [mm]（受け取り土間・地面は −300、外縁側・海峡は −150）。
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
def solid_uv(pts_uv, z0, z1, li, col=None):
    pts = [W(u, v) for u, v in pts_uv]
    if len(pts) < 3: return
    z0f = z0 if callable(z0) else (lambda u, v, z=z0: z)
    z1f = z1 if callable(z1) else (lambda u, v, z=z1: z)
    bot = [(*p, z0f(u, v)) for p, (u, v) in zip(pts, pts_uv)]
    top = [(*p, z1f(u, v)) for p, (u, v) in zip(pts, pts_uv)]
    m.Objects.AddMesh(mesh_prism(bot, top), attr(li, col))
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
L_HI = layer('99_しつらえ_頭上（天蓋・物干し・天袋）', (180, 160, 200))

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
    for a, b in [((u0, v1), (u1, v1)), ((u0, v0), (u0, v1)), ((u1, v0), (u1, v1))]:   # 手すり（西の壁側をのぞく 3 辺）h+900（10-24、縦格子のすき間90以下）
        panel_uv([a, b], 1200, 2100, 0.03, L_GL, (0.85, 0.75, 0.6, 1))
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
def canopy(rec):                     # 布の天蓋（吊り桟から、ふだんの高さ h2.1〜2.25、午睡は下ろす）
    pts = clean(rec['pts']); g = SP(pts); u0, v0, u1, v1 = g.bounds
    zc = lambda v: 2100 + 150 * abs(math.cos(math.pi * (v - v0) / 0.9))   # 吊り桟の下でたるむ（0.9ごと）
    vs = np.arange(v0, v1 + 1e-6, 0.15)
    for a, b in zip(vs, vs[1:]):
        solid_uv([(u0, a), (u1, a), (u1, b), (u0, b)], lambda u, v: zc(v), lambda u, v: zc(v) + 8, L_HI, (0.97, 0.95, 0.9, 1))
def hang_bar(rec):                   # 吊り桟 30×40 を h2.4 に（梁と梁のあいだ、南北に）、両端は梁の下端から φ9 の吊り棒
    (ua, v), (ub, _) = rec['pts'][0], rec['pts'][-1]
    u0, u1 = sorted([float(ua), float(ub)]); v = float(v)
    if BEAM_BOT(v) < 2430: return
    solid_uv([(u0, v - .015), (u1, v - .015), (u1, v + .015), (u0, v + .015)], 2380, 2420, L_HI, (0.85, 0.75, 0.6, 1))
    for uu in (u0 + 0.035, u1 - 0.035):
        solid_uv([(uu - .0045, v - .0045), (uu + .0045, v - .0045), (uu + .0045, v + .0045), (uu - .0045, v + .0045)],
                 2420, BEAM_BOT(v) - 5, L_HI, (0.5, 0.5, 0.5, 1))
def steps01(rec):                    # 0・1歳の上り下りの段々（150×3）
    pts = rec['pts']; g = SP(pts); u0, v0, u1, v1 = g.bounds
    cuts = [u0, 7.9, 8.4, 8.9, u1]; hs = [150, 300, 450, 450]
    for (a, b), h in zip(zip(cuts, cuts[1:]), hs):
        piece = g.intersection(sbox(a, v0, b, v1))
        if not piece.is_empty: solid_uv(list(piece.exterior.coords)[:-1], 0, h, L_PL, (0.96, 0.95, 0.9, 1))
def hill(rec):                       # 2歳の山：等高線 k=1/0.66/0.33 を 0–300／300–600／600–900
    pts = clean(rec['pts']); g = SP(pts); A = g.area
    h0 = 0 if A > 6 else (300 if A > 2.5 else 600)
    solid_uv(pts, h0, h0 + 300, L_PL, fc(rec))
def cot(rec):
    solid_uv([tuple(p) for p in rec['pts']], 0, 120, L_COT)
def nedoko(rec):                     # ねどこの囲い h900（u=5.6 の辺に開口）
    ring_uv([tuple(p) for p in rec['pts']], 0, 900, 0.03, L_P, (0.95, 0.93, 0.85, 1), gap=(5.5, 5.7, 5.2, 6.2))
def kubomi(rec):                     # 2歳の落ち着くくぼみ：囲い h1000、南に開口
    ring_uv([tuple(p) for p in rec['pts']], 0, 1000, 0.04, L_PL, fc(rec), gap=(16.85, 16.95, 3.55, 4.35))
def mamagoto_posts(rec): solid_uv([tuple(p) for p in rec['pts']], 0, 1400, L_F, (0.3, 0.25, 0.2, 1))
def basket(rec):  solid_uv([tuple(p) for p in rec['pts']], 400, 700, L_T, (1, 1, 1, 1))

T01 = {   # plan01（0・1歳、u ≤ 12）
    98: ('solid', -300, 3900, L_WW), 99: ('solid', -300, 3900, L_WW),
    100: ('panel', 0, 2600, 0.03, L_GL),
    106: ('solid', -300, 600, L_P),                       # 框＋腰壁 h600
    109: ('solid', -300, -150, L_F),                      # 式台 150
    110: ('panel', -150, 900, 0.04, L_F),                 # 木戸
    86: ('solid', 0, 300, L_F),                           # 窓辺の小上がり h300
    111: ('panel', 300, 900, 0.03, L_F),                  # 格子の手すり h600
    112: ('solid', 0, 900, L_P),
    117: ('solid', 0, 2400, L_P), 118: ('solid', 0, 2400, L_P),
    126: ('solid', 0, 850, L_WC), 129: ('solid', 0, 850, L_WC), 131: ('solid', 0, 850, L_WC),
    133: ('solid', 0, 300, L_WC), 134: ('solid', 0, 250, L_WC),
    140: ('table', 500, L_F), 141: ('solid', 0, 300, L_F),       # 先生の腰掛ける机（天板 500・座 300）
    144: ('table', 700, L_F), 145: ('solid', 0, 700, L_F),
    149: nedoko, 153: ('solid', 0, 250, L_F), 155: ('solid', 1800, 1815, L_HI),
    158: basket, 162: ('solid', 0, 120, L_PL), 163: ('solid', 120, 200, L_PL),
    166: ('solid', 0, 600, L_F), 171: ('table', 350, L_F), 173: ('solid', 0, 200, L_F), 174: ('solid', 0, 200, L_F),
    178: cot, 180: ('solid', 0, 800, L_F), 183: ('solid', 0, 900, L_F),
    187: ('solid', 0, 850, L_WC), 189: ('solid', 0, 850, L_WC), 190: ('solid', 0, 850, L_F),
    193: ('panel', 2600, 2630, 0.03, L_HI), 195: ('solid', 2400, 2700, L_HI),
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
    120: kubomi, 123: ('solid', 1000, 1020, L_PL),
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
    117: ('panel', 0, 2400, 0.12, L_P), 118: ('panel', 0, 2400, 0.12, L_P), 123: ('panel', 0, 2400, 0.12, L_P),
    134: ('solid', 0, 500, L_WC), 143: ('panel', 0, 1300, 0.03, L_WC), 144: ('panel', 0, 1300, 0.03, L_WC),
    147: ('solid', 0, 550, L_WC), 148: ('solid', 0, 260, L_WC), 149: ('panel', 0, 1300, 0.03, L_WC),
    151: ('solid', 0, 800, L_WC),
    153: ('panel', 1200, 2270, 0.01, L_T),                # 路地の出口の暖簾（裾 h1200）
    154: ('panel', 100, 700, 0.02, L_GL),                 # 便所の東の低い窓
    170: ('solid', -150, 250, L_F),                       # 下足箱・腰掛け（外縁側の側）
    284: by_u_table, 288: by_u_seat, 295: cot,
    333: quiet_desk, 337: quiet_store, 342: by_u_seat, 345: by_u_seat,
    349: loft, 351: loft_step,
    359: ('solid', 0, 450, L_F), 358: ('table', 700, L_F),                 # 先生の席（10-24：腰の壁の東の端）
    357: koshi_wall, 363: ('solid', 0, 700, L_F),                  # 腰の壁＋格子／移動式の低い腰壁（棚）
    364: canopy, 368: hang_bar,                                 # 布の天蓋／吊り桟 h2400
    372: ('solid', 0, 1000, L_F), 376: ('solid', 0, 900, L_F), 379: ('solid', 0, 12, L_T),
    396: ('solid', 0, 1200, L_F),                         # 絵本の通りの棚
    398: ('solid', 0, 300, L_F), 399: ('panel', 300, 1300, 0.01, L_T), 400: ('solid', 300, 420, L_T),
    406: ('panel', 0, 2000, 0.03, L_F), 407: ('solid', 0, 50, L_T), 408: ('solid', 0, 5, L_PL),
    414: ('solid', 50, 220, L_T),
    126: ('solid', 0, 1800, L_F),
    127: ('solid', 0, 1800, L_F),
    443: ('table', 700, L_F),
    445: ('solid', 0, 450, L_F),
    446: ('solid', 0, 1800, L_F),
    447: ('table', 400, L_F),
    448: ('solid', 0, 420, L_F),
    449: ('table', 700, L_F),
    450: ('solid', 0, 450, L_F),
    451: ('solid', 0, 1800, L_F),
}

# ---- 0〜2歳の縁側（10-21：他と同じく縁側の中ほど r=191.5 にガラス戸。内縁側＝はだし・部屋の一部、外縁側＝土足 FL−150）----
def eng_fence(rec):      # 0・1歳｜2歳の境の低い柵（内縁側は h900、外縁側は土足の床から h900）
    v = float(np.mean(rec['pts'][:, 1]))
    if v < 13.5: solid_uv(clean(rec['pts']), 0, 900, L_P)
    else: solid_uv(clean(rec['pts']), -150, 750, L_P)
def first_step(rec):     # 二段の縁 → 外縁側が −150 になったので、地面との間は沓脱ぎ石 1 つ
    if float(np.mean(rec['pts'][:, 1])) < 15.3: solid_uv(clean(rec['pts']), -300, -200, L_F, (0.8, 0.78, 0.74, 1))
T01.update({197: eng_fence, 220: ('solid', -150, 750, L_P),          # 外縁側の外の端に格子の高欄 h900
            223: first_step, 225: ('panel', 1500, 2500, 0.01, L_T),  # 「おひるね中」の暖簾（高欄の戸の上の軒先）
            256: ('solid', -300, 0, L_F)})                           # 大きい子の縁台 h300（地面から）
T02.update({188: ('solid', -150, 750, L_P), 190: first_step, 191: ('panel', 1500, 2500, 0.01, L_T)})

def store_ceiling(rec):          # 教材庫：天井 h2400
    c = fc(rec)
    if c is not None and abs(c[0] - 0xE4 / 255) < 0.02 and abs(c[1] - 0xE1 / 255) < 0.02:
        solid_uv(clean(rec['pts']), 2400, 2430, L_P, c)
T04[107] = store_ceiling

import os as _os
REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'ref')
def build(name, table, umin, umax, skipclip=False):
    # 高さの表は ref/ の版（10-21）の行番号で書いてある。行の中身（文）で引き直し、スクリプトに行が足されてもずれないようにする
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
        if kind == 'solid': solid_uv(P_, spec[1], spec[2], spec[3], colr)
        elif kind == 'table': table_uv(P_, spec[1], spec[2], fc(rec))
        elif kind == 'panel': ring_uv(P_, spec[1], spec[2], spec[3], spec[4], fc(rec))
        cnt += 1
    print(name, 'objects', cnt)

build('plan01.py', T01, -1, 12.0)
build('plan02.py', T02, 12.0, 18.1)
build('plan04.py', T04, 29.9, 57.4)

# ---------------- 西の外壁（u 0–57、開口つき） ----------------
OPEN = [  # (u0, u1, z0, z1)
    # 10-26（ユーザー、監修の項 20261026-0044）：0〜2歳の西吹き抜けの窓は、南から北へ高く大きくなってゆく。
    # スパン 1〜7 に一つずつ、スパンの真ん中（架構の線の柱を避ける）。10-26夜（ユーザー、比べる絵の案D）：大きさは同じ
    # 幅 0.60×高さ 0.90 の縦長、窓台が 250 → 1150（150 ずつ）と北へ上がる。下端ははう子の目 → 立った2歳 → 大人へ、歳の目の高さを追う。
    *[(3.0 * k - 1.8, 3.0 * k - 1.2, 250 + 150 * (k - 1), 1150 + 150 * (k - 1)) for k in range(1, 8)],
    (21.0, 30.0, -300, 99999),                                             # ホールの範囲（スパン 8–10）は西の壁を開く（10-21 夕、海峡の口を含む）
    (45.6, 47.6, 0, 2400),                                                 # 遊戯室の北の口（口②、10-24 柱u45・48のあいだへ、西館とそろえた）。口①は南の口にまとめて閉じた（10-21）
    (52.6, 53.85, -300, 600), (54.15, 56.4, -300, 600),                    # 本の奥の低い窓（GL まで）。架構の線 u54 の柱で二つに（10-26）
]
# すき間の倉庫（先生の道の側、u30〜40、西館係が床と棚）への口（10-25、監修の項 20261025-0710）：柱と柱のあいだごとに h2100 の口と引き違いの戸
GAP_STORE_BAYS = [(30.1, 32.85), (33.15, 35.85), (36.15, 38.85), (39.15, 39.95)]
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
            if o[2] >= 300 or o[3] <= 700:      # 窓はガラス
                solid_uv([(a, -0.015), (b, -0.015), (b, 0.015), (a, 0.015)], o[2], o[3], L_GL, glass)
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
# 読書の庭のモミジ（u54.4, v−2.3）
c = (54.4, -2.3)
ang = np.linspace(0, 2 * np.pi, 13)[:-1]
solid_uv([(c[0] + 0.08 * np.cos(t), c[1] + 0.08 * np.sin(t)) for t in ang], -300, 2200, L_TR, (0.35, 0.25, 0.15, 1))
solid_uv([(c[0] + 1.3 * np.cos(t), c[1] + 1.3 * np.sin(t)) for t in ang], 2200, 3300, L_TR, (0.55, 0.7, 0.35, 1))
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
    L_PATH = layer('59_1F_通り抜け（こどもの小径）', (0xE9, 0xDF, 0xCF))
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
