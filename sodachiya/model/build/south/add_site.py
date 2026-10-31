"""敷地の現況：高野川の護岸（崖）を敷地の南東の辺に沿って
使い方: python3 add_site.py IN.3dm OUT.3dm
決定事項「敷地の現況」（10-21 ユーザーの実測と写真）：高さ 5 m（土が積もって 4 m の所が多い）。
上から 柵（金網）の土台のコンクリートの立ち上がり → 小段（コンクリートの天端）→ 谷積みの石積み（垂直に近い）→ 草の河川敷 → 川。
10-31（アプローチ係）：育ち舎の川沿い（東の角〜公園の川の角）は柵が敷地の中の木の縦格子（外構の3dm 70k）に替わり、立ち上がりと小段は土と雑草（02_敷地_崖の上の…）。
寸法は写真からの見立て（仮）：立ち上がり 幅 0.2・GL+0.3、小段 幅 0.6・GL−0.3、石積み 勾配 1:0.3 で GL−4.0 まで、
河川敷 幅 8 m（GL−5.0 で一律、10-29）、川の水面 GL−5.5（水の板0.3、下に玉石の川底）・幅 18 m（10-26夜、配置図で向こう岸の手前まで）。z=0 は FL（GL = −300）。
01s：敷地の土の受け皿（10-29）：敷地から建物・園庭の地形90・公園を引いた範囲に、土の閉じた板（上面GL、厚さ300）。地面の抜けを残さない。
"""
import sys, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/south')
from uv import uv
from meshkit import Kit
from shapely.geometry import Polygon

IN, OUT = sys.argv[1:3]   # 3 番目に園庭の取り込み用 3dm（任意）
m = r.File3dm.Read(IN)
def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
L_RV = layer('02_敷地_高野川の護岸（現況、寸法は仮）', (140, 150, 140))
# 一つのレイヤーに一つの素材（10-29、ユーザー：川が灰色ベージュで怖い）。番号は02のまま（配置図・プレゼン・園庭の図が「02_」と高さで水・河川敷を見分けるので）、素材は名前で（data/materials.json）
L_BED = layer('02_敷地_高野川の河川敷（草）', (120, 150, 90))
L_WAT = layer('02_敷地_高野川の水', (120, 160, 200))
L_RB = layer('02_敷地_高野川の川底（玉石）', (140, 136, 126))
K = Kit(m)

# 敷地の外形（00 の大きい方）から南東の辺（u が小さく v が大きい 2 点：東の角 → 南の角）
site = None
for o in m.Objects:
    if m.Layers[o.Attributes.LayerIndex].Name.startswith('00_') and isinstance(o.Geometry, r.PolylineCurve):
        g = o.Geometry; P = np.array([[g.Point(i).X, g.Point(i).Y] for i in range(g.PointCount)])
        if site is None or Polygon(P).area > Polygon(site).area: site = P
UV = [uv(*p) for p in site]
iE = max(range(len(UV) - 1), key=lambda i: UV[i][1])               # 東の角（v がいちばん大きい）
iS = min(range(len(UV) - 1), key=lambda i: UV[i][0])               # 南の角（u がいちばん小さい）
a, b = site[iE], site[iS]
d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])
cen = site[:-1].mean(0)
if np.dot(n, cen - (a + b) / 2) > 0: n = -n                        # 敷地の外（川の側）へ
ext = 45000                                                        # 辺の両端を延ばす（配置図 A1 の紙の幅いっぱいに川と崖が続く、10-26夜 プレゼンの準備）
a2, b2 = a - d * ext, b + d * ext
GL = -300.0
def band(o0, o1):
    return Polygon([a2 + n * o0, b2 + n * o0, b2 + n * o1, a2 + n * o1])
# 崖の上（10-31、アプローチ係。ユーザー：川沿いの柵を木の縦格子にし、柵の外の崖の上は土にして雑草を生やす。一律にそろえない）：
# 育ち舎の川沿い（東の角 a から公園の川の角まで）は、金網の土台の立ち上がりと小段をやめて土（上面 GL−5、受け皿と同じ）と雑草のかたまり。
# ほか（隣地・公園の前）は現況の立ち上がりと小段のまま
_PK0 = [np.array([[o.Geometry.Point(i).X, o.Geometry.Point(i).Y] for i in range(o.Geometry.PointCount)]) for o in m.Objects
        if m.Layers[o.Attributes.LayerIndex].Name.startswith('01_') and isinstance(o.Geometry, r.PolylineCurve)]
_PK0 = min(_PK0, key=lambda P_: P_[:, 1].mean()) if _PK0 else None             # 01 の二つの外形のうち南が公園
_on = [q for q in (_PK0 if _PK0 is not None else []) if abs(np.dot(q - a, n)) < 300 and np.linalg.norm(q - b) > 1000]
pc = min(_on, key=lambda q: np.linalg.norm(q - b)) if _on else b                 # 公園の川の角（公園の北東の辺が崖の上の縁に会う所）
s_a, s_b = float(np.dot(a - a2, d)), float(np.dot(pc - a2, d))                  # 土にする範囲（a2 からの距離 mm）
def band_s(o0, o1, s0, s1):
    return Polygon([a2 + d * s0 + n * o0, a2 + d * s1 + n * o0, a2 + d * s1 + n * o1, a2 + d * s0 + n * o1])
for s0, s1 in ((0.0, s_a), (s_b, float(np.linalg.norm(b2 - a2)))):
    K.prism(band_s(0, 200, s0, s1), GL - 300, GL + 300, L_RV, (190, 190, 185))  # 柵の土台の立ち上がり（現況）
    K.prism(band_s(200, 800, s0, s1), GL - 400, GL, L_RV, (190, 190, 185))      # 小段（コンクリートの天端、現況）
L_TS = layer('02_敷地_崖の上の土（川沿いの柵の外）', (140, 116, 88))
L_TG = layer('02_敷地_崖の上の雑草（川沿いの柵の外）', (110, 140, 80))
K.prism(band_s(0, 800, s_a, s_b), GL - 400, GL - 5, L_TS, (140, 116, 88))      # 土（石積みの上に載る、厚さ約0.4）
_rng = np.random.default_rng(1031); _ng = 0
_ph = _rng.uniform(0, 2 * np.pi, 3)
def _dens(sv):                                                                  # 生え方の濃さ（場所でばらばら、ところどころ裸の土）
    v = sum(np.sin(sv / w + p_) for w, p_ in zip((900.0, 2300.0, 5100.0), _ph)) / 3
    return max(0.0, v + 0.25)
for _sv in np.arange(s_a + 60, s_b - 60, 90.0):
    if _rng.random() > _dens(_sv): continue
    for _k in range(_rng.integers(1, 4)):
        _o = _rng.uniform(80, 720); _sj = _sv + _rng.uniform(-45, 45)
        _r0 = _rng.uniform(50, 190); _nv = int(_rng.integers(5, 9))
        _ang = np.sort(_rng.uniform(0, 2 * np.pi, _nv))
        _c = a2 + d * _sj + n * _o
        _pts = [_c + _r0 * _rng.uniform(0.6, 1.0) * np.array([np.cos(t_), np.sin(t_)]) for t_ in _ang]
        _g = Polygon(_pts).buffer(0).intersection(band_s(20, 790, s_a, s_b))
        if _g.is_empty or _g.area < 2000: continue
        K.prism(_g, GL - 5, GL - 5 + _rng.uniform(80, 550), L_TG, (110, 140, 80)); _ng += 1
print('cliff top: soil %.1f m（公園の角まで）、雑草 %d かたまり' % ((s_b - s_a) / 1000, _ng))
# 谷積みの石積み（勾配 1:0.3）と河川敷・川。河川敷の土の高さは場所で 4〜5 m（ユーザー）：
# 公園の角（南の角）の階段のあたりは GL−5.0、そこから北東へ 20 m で GL−4.0 に（あいだは直線で）
top = GL - 400
def bot_at(t):
    """辺の上の位置 t（南の角からの距離 mm）→ 河川敷の上面"""
    return GL - 5000                                               # 一律に低い方の高さ（10-29、ユーザー：場所で変えると平らな板が川の上に浮いて見えた）
WM = 800 + 0.3 * (top - (GL - 5000)) + 8000                       # 河川敷の川の側の縁＝水面の箱の縁（いちばん低い河川敷の石積みの足元＋8 m）
Ltot = np.linalg.norm(b2 - a2); NSEG = 24
for k in range(NSEG):
    pa = a2 + (b2 - a2) * k / NSEG; pb = a2 + (b2 - a2) * (k + 1) / NSEG
    ta = np.linalg.norm(b - pa); tb = np.linalg.norm(b - pb)            # b が南の角
    za, zb = bot_at(ta), bot_at(tb); bmin = min(za, zb)
    W1a, W1b = 800 + 0.3 * (top - za), 800 + 0.3 * (top - zb)
    V = lambda p, off, z: [*(p + n * off), z]
    K.box8([V(pa, 500, za), V(pb, 500, zb), V(pb, W1b, zb), V(pa, W1a, za),
            V(pa, 500, top), V(pb, 500, top), V(pb, 800, top), V(pa, 800, top)], L_RV, (150, 140, 120))
    # 草の河川敷：川の側の縁は水面の箱の縁（WM）まで。前はWm＋8000で、河川敷の高い所（GL−4.0）ほど水面とのあいだに
    # 幅0〜0.3のすき間が空いていた（10-29、監修の項20261029-1457-kanshu）
    K.box8([V(pa, W1a, za - 700), V(pb, W1b, zb - 700), V(pb, WM, zb - 700), V(pa, WM, za - 700),
            V(pa, W1a, za), V(pb, W1b, zb), V(pb, WM, zb), V(pa, WM, za)], L_BED, (120, 150, 90))   # 草の河川敷（厚さ0.7で水面の下まで、浮いて見えない、10-29）
# 川：水面は一つの高さ（GL−5.5、いちばん低い河川敷 GL−5.0 の 0.5 下）、幅 18 m（向こう岸の手前まで、寸法は仮）。
# 配置図は水面の高さ（−5.7 m より下）で水の色に塗る
_RIV = Polygon([a2 + n * WM, b2 + n * WM, b2 + n * (WM + 18000), a2 + n * (WM + 18000)])
K.prism(_RIV, GL - 5500 - 300, GL - 5500, L_WAT, (120, 160, 200))                # 水（素材は水：透けて川底が見える、10-29 ユーザー：灰色で怖い）
K.prism(_RIV, GL - 5500 - 600, GL - 5500 - 300, L_RB, (140, 136, 126))          # 川底の玉石
# ---------------------------------------------------------------- 園庭（園庭のチャットの取り込み用ファイル、レイヤー 90〜98）
import os
GF = sys.argv[3] if len(sys.argv) > 3 else None
if GF and os.path.exists(GF):
    g3 = r.File3dm.Read(GF); mp = {}
    for i, l in enumerate(g3.Layers):
        nl = r.Layer(); nl.Name = l.Name; nl.Color = l.Color
        if l.Name.startswith('98_'): nl.Visible = False             # 模型の積層用の板はふだん隠す
        if not l.Visible: nl.Visible = False                         # 園庭の取り込み用ファイルで非表示のレイヤー（92f 床の噴水の水、10-31 園庭）はそのまま隠す
        mp[i] = m.Layers.Add(nl)
    cnt = 0
    for o in g3.Objects:
        a_ = o.Attributes; a_.LayerIndex = mp[a_.LayerIndex]
        m.Objects.Add(o.Geometry, a_); cnt += 1
    print('garden objects', cnt)
# ---------------------------------------------------------------- 敷地の土の受け皿（01s、10-29監修の項20261029-1457-kanshu）
# 抜けを残さない受け皿：敷地の外形（00の大きい方）から、建物の外形（本館・西館・機械室：床・外壁・機械室の平面への写し）、
# 園庭の地形90の広がり、公園（01の公園の外形）を引いた範囲に、土の閉じた板を一枚（上面GL＝−300、厚さ300）。
# 外構の舗装・芝の板（上面−290）はこの上に10載る。Rhino版（段10）で外形と穴の押し出しになる
from shapely.geometry import Polygon as _Pg
from shapely.ops import unary_union as _uu
import re as _re
L_SOIL = layer('01s_敷地_土（受け皿、上面GL−300）', (150, 128, 100))
def _code(o):
    mm_ = _re.match(r'^(\d+[a-z]?)_', m.Layers[o.Attributes.LayerIndex].Name); return mm_.group(1) if mm_ else None
def _plan(g):
    """メッシュの面を平面に写した多角形の和"""
    if not isinstance(g, r.Mesh): return None
    V = np.array([[p.X, p.Y] for p in g.Vertices]); T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; ids = [f[0], f[1], f[2]] + ([f[3]] if f[3] != f[2] else [])
        P = V[ids]
        if abs(_Pg(P).area) > 1e3: T.append(_Pg(P).buffer(0))
    return _uu(T) if T else None
BLD = ('12', '13', '14', '15', '17', '21', '35', '35d', '52', '53', '54', '56', '57', '59', '31', '32', '33', '34', '36', '36b')
FP = [_plan(o.Geometry) for o in m.Objects if _code(o) in BLD]
FP = _uu([f for f in FP if f is not None and not f.is_empty]).buffer(30, join_style=2).buffer(-30, join_style=2)
# 外形の中の穴：0.5 m²より小さいもの（壁と床の継ぎ目のすき間）は建物に。大きいもの（本館と西館のあいだの床の無い所）には土を入れる
FP = _uu([_Pg(g.exterior, [h for h in g.interiors if _Pg(h).area >= 5e5]) for g in getattr(FP, 'geoms', [FP]) if g.geom_type == 'Polygon'])
GT = [_plan(o.Geometry) for o in m.Objects if _code(o) == '90']
GT = _uu([f for f in GT if f is not None and not f.is_empty]) if GT else _Pg()
PK = [_Pg([[o.Geometry.Point(i).X, o.Geometry.Point(i).Y] for i in range(o.Geometry.PointCount)]).buffer(0)
      for o in m.Objects if _code(o) == '01' and isinstance(o.Geometry, r.PolylineCurve)]
PK = min(PK, key=lambda q: q.centroid.y) if PK else _Pg()          # 01の二つの外形のうち南が公園（北は駐車場）
SOIL = _Pg(site).buffer(0).difference(FP).difference(GT).difference(PK)
SOIL = SOIL.buffer(-3, join_style=2)                                # 輪が一点で触れる所を離す（3 mm、道路と同じ。図には出ない）
ns = 0
for g in getattr(SOIL, 'geoms', [SOIL]):
    if g.geom_type != 'Polygon' or g.area < 1e4: continue
    n0 = len(m.Objects)
    K.prism(g.simplify(5), GL - 305, GL - 5, L_SOIL)                 # 10-30 監修：上面をGLより5下げる（GLに置く62・64などの板と同じ面でちらつく、ユーザー）
    for o in list(m.Objects)[n0:]: o.Attributes.Name = '敷地の土（受け皿）'
    ns += len(m.Objects) - n0
print('soil: 建物の外形%.1f m2、園庭の地形%.1f m2、公園%.1f m2 → 受け皿%.1f m2（%d枚）'
      % (FP.area / 1e6, GT.area / 1e6, PK.area / 1e6, SOIL.area / 1e6, ns))
# 01（公園・駐車場の古い外形の線、最初の敷地のファイルから）は、公園の川の角を探すのに使ったので、ここで消す（10-31 アプローチ係、ユーザー：要る？）。
# 公園と駐車場は外構の取り込み（70〜79）に形があるので、古い線は重なって紛らわしいだけ
_del01 = [o.Attributes.Id for o in m.Objects if m.Layers[o.Attributes.LayerIndex].Name.startswith('01_')]
for _id in _del01: m.Objects.Delete(_id)
print('removed 01 outlines', len(_del01))
m.Write(OUT, 8); print('written', OUT, 'river edge from', np.round(uv(*a), 1), 'to', np.round(uv(*b), 1))
