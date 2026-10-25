"""面積表：3dm（メッシュの版）の部屋の床から、課題の所要室と延床面積を測る
使い方: python3 areas.py MODEL_MESH.3dm DATA_DIR OUTDIR
出力：OUTDIR/sodachiya_areas.json（数値、プレゼンの準備などが読む）・.csv・.pdf・.png（A3 横の表）
- 部屋の面積は壁芯（ユーザー、10-23）：その部屋の床の板（レイヤー 31〜36・41〜45・52〜59）を上から見た形から壁を除き、
  その部屋に接する壁（外壁 17・21、間仕切り 24、しつらえの間仕切りのうち高さ 2 m 以上の 38）の半分を足す。
  床の板の端が壁の外面・真ん中・内面のどこにあっても、壁の真ん中で数えたのと同じになる（設計監修、10-23）。
- 延床面積＝1 階の床（本館の床・内縁側・海峡と各部屋の床の和）＋西館 2 階の床（23）＋園庭の小屋の便所と倉庫（data/garden.json の HUT、10-25）。これも壁芯（床の下の間仕切りは全部、外壁は半分を数える）。外縁側（14、土足の軒下）は含めない。
- 園庭＝園庭の地形（90、だいさんかく・しずかのもり）＋みなみのさんかく（data/minami.json の AREA）。
- 駐車は決定事項_外構の台数（南 3・北 2）。駐輪は決まっていない。
課題の所要室は 2026-09-28 の課題文から。
"""
import sys, os, re, json, csv, datetime, subprocess, numpy as np, rhino3dm as r
from shapely.geometry import Polygon
from shapely.ops import unary_union
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

IN, DATA, OUTD = sys.argv[1:4]
PDFD = sys.argv[4] if len(sys.argv) > 4 else OUTD   # 面積表のPDFは sodachiya/drawings/（10-24）
os.makedirs(PDFD, exist_ok=True)
os.makedirs(OUTD, exist_ok=True)

m = r.File3dm.Read(IN)
LAY = {i: l for i, l in enumerate(m.Layers)}
def tris(g):
    if isinstance(g, r.Mesh):
        V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
        F = []
        for i in range(g.Faces.Count):
            f = g.Faces[i]
            F.append((f[0], f[1], f[2]))
            if f[2] != f[3]: F.append((f[0], f[2], f[3]))
        return V[np.array(F)] if F else np.zeros((0, 3, 3))
    return np.zeros((0, 3, 3))
def footprint(T):
    ps = [Polygon(t[:, :2]).buffer(0) for t in T]
    ps = [p for p in ps if p.area > 1.0]
    return unary_union(ps) if ps else Polygon()

FP, FZ = {}, {}
for o in m.Objects:
    ln = LAY[o.Attributes.LayerIndex].Name
    if not re.match(r'^(1[2-5]|23|3[1-6]|4[1-5]b?|5[2-9]|90)[a-z]?_', ln): continue
    T = tris(o.Geometry)
    if not len(T): continue
    FP.setdefault(ln, []).append(footprint(T)); FZ[ln] = max(FZ.get(ln, -1e9), float(T[:, :, 2].max()))
A0 = {k: unary_union(v) for k, v in FP.items()}          # 床の板そのもの
# 壁（上から見た形）：外壁 17・21、間仕切り 24、しつらえの間仕切りのうち高さ 2 m 以上の 38
# 壁は、その階の人のいる高さ（床から 2.4 m まで）にあるものだけ（2 階の間仕切りや、すき間の蓋より上の外壁が 1 階の部屋を削らないように）
WL = []           # (三角形の網, 下端, 上端, 外壁か)
def _tm_of(g):
    if isinstance(g, r.Mesh):
        V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))]); F = []
        for i in range(g.Faces.Count):
            f = g.Faces[i]; F.append((f[0], f[1], f[2]))
            if f[2] != f[3]: F.append((f[0], f[2], f[3]))
        return trimesh.Trimesh(V, np.array(F), process=False)
    T = tris(g); return trimesh.Trimesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3), process=True)
import trimesh
for o in m.Objects:
    ln = LAY[o.Attributes.LayerIndex].Name
    if not re.match(r'^(17|21|24|38)_', ln): continue
    b = o.Geometry.GetBoundingBox()
    if ln.startswith('38_') and b.Max.Z - b.Min.Z < 2000: continue
    T = tris(o.Geometry)
    if len(T): WL.append((_tm_of(o.Geometry), b.Min.Z, b.Max.Z, bool(re.match(r'^(17|21)_', ln))))
BAND = 2400
def section_xy(t, z):
    """高さ z で水平に切った形（上から見た形）。外壁は一つの立体にまとめてあるので、物の上端・下端ではなく切り口で測る（設計監修、10-24）。
    立体を z±5 の薄い板で切り取り、その上下の面を上から見た形にする（輪になった外壁の切り口でも、中を塗りつぶさない）"""
    M = _mani(t)
    if M is None: return Polygon()
    b = t.bounds
    slab = manifold3d.Manifold.cube([b[1][0] - b[0][0] + 20, b[1][1] - b[0][1] + 20, 10]).translate([b[0][0] - 10, b[0][1] - 10, z - 5])
    X = M ^ slab
    if X.is_empty(): return Polygon()
    V, F = from_manifold(X)
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    up = n[:, 2] > 0.5 * np.linalg.norm(n, axis=1)
    ps = [Polygon(tr[:, :2]).buffer(0) for tr in T[up] if Polygon(tr[:, :2]).area > 1]
    return unary_union(ps) if ps else Polygon()
import manifold3d
from solids import to_manifold, to_manifold_raw, from_manifold, by_bodies
_MC = {}
def _mani(t):
    k = id(t)
    if k not in _MC:
        M = to_manifold(t) or to_manifold_raw(t)
        if M is None: M = by_bodies(np.asarray(t.vertices), np.asarray(t.faces))
        _MC[k] = M
    return _MC[k]
_WC = {}
def walls_at(zf):
    """床の高さ zf の階の壁：(外壁, 間仕切り, 全部)。床から 0.3・1.2・2.2 m の高さで切った形の和（窓の所も壁として数える）"""
    k = round(zf / 500)
    if k not in _WC:
        we, wi = [], []
        for t, z0, z1, ext in WL:
            if not (z0 < zf + BAND and z1 > zf + 100): continue
            g = unary_union([section_xy(t, zf + dz) for dz in (300, 1200, 2200) if z0 < zf + dz < z1])
            if not g.is_empty: (we if ext else wi).append(g)
        we = unary_union(we); wi = unary_union(wi)
        _WC[k] = (we, wi, unary_union([we, wi]))
    return _WC[k]
NEAR = 250        # 部屋に接する壁を拾う幅（mm、いちばん厚い壁より広く）
def wall_center(g, zf):
    """床の板 g を壁芯の面積に：壁を除き、接する壁の半分を足す"""
    W_ALL = walls_at(zf)[2]
    inner = g.difference(W_ALL)
    half = W_ALL.intersection(inner.buffer(NEAR))
    return inner, half
class WC:
    def __init__(s, g, zf):
        s.g = g
        if g.is_empty: s.area = 0.0
        else:
            inner, half = wall_center(g, zf); s.area = inner.area + 0.5 * half.area
A = {k: (WC(g, FZ[k]) if not re.match(r'^(1[2-5]|23|90)[a-z]?_', k) else g) for k, g in A0.items()}
area = lambda g: g.area / 1e6
def S(*prefixes):
    """名前の頭がそろうレイヤーの面積の和（m²）と内訳"""
    parts = [(k, area(g)) for k, g in A.items() if k.startswith(prefixes)]
    return sum(a for _, a in parts), parts

def nm(k):
    k = re.sub(r'^\d+[a-z]?_(1F_|2F_)?', '', k)
    return re.sub(r'（[^（）]*(±|−|土足|格子)[^（）]*）', '', k)     # 床の高さなどの注は外し、部屋を分ける注（記録・連絡の机など）は残す

# ---------------------------------------------------------------- 所要室（課題文 7）
ROWS = []
def row(group, name, req, req_min, keys, note=''):
    a, parts = S(*keys) if keys else (None, [])
    if req_min is None: judge = ''
    elif '以上' in req: judge = '○' if a is not None and a >= req_min else '△'
    else: judge = '○' if a is not None and a >= req_min * 0.9 else '△'
    ROWS.append(dict(group=group, room=name, required=req, planned=None if a is None else round(a, 1),
                     parts=' ＋ '.join(f'{nm(k)} {v:.1f}' for k, v in sorted(parts)) if len(parts) > 1 else (nm(parts[0][0]) if parts else ''),
                     judge=judge, note=note))
row('保育', '乳児室（0〜1 歳）', '約 60×2', 108, ('53_',), '沐浴・調乳・ほふくを含む。0・1 歳はひと続きの部屋')
row('保育', '保育室（2 歳）', '約 60', 54, ('54_',))
row('保育', '保育室（3〜5 歳）', '約 60×3', 162, ('59_1F_3歳', '59_1F_4歳', '59_1F_5歳'))
row('保育', '遊戯室', '240 以上', 240, ('31_',), '2 階のキャットウォーク・輪の通路は数えていない')
row('保育', '便所', '適宜', None, ('59_1F_便所（こども）', '59_1F_便所・倉庫'), '3・4 歳と 4・5 歳のあいだ（スパン 14・17）のこどもの便所。通り抜け（こどもの小径）は廊下として延床だけに数える')
row('保育', '食堂', '必要に応じて', None, ('34_',), 'はれのま（食べる土間）。ふだんは各保育室でも食べる')
row('保育', '屋外プール', '適宜', None, (), '園庭の水浴び場（φ4.0）で代える（先生の了承）')
a_g = area(A.get('90_園庭_地形（0.5 m 格子）', Polygon())) if '90_園庭_地形（0.5 m 格子）' in A else S('90_')[0]
mi = json.load(open(os.path.join(DATA, 'minami.json'), encoding='utf-8'))
a_mi = Polygon(mi['AREA']).area
ROWS.append(dict(group='保育', room='園庭', required='350 以上', planned=round(a_g + a_mi, 1),
                 parts=f'だいさんかく・しずかのもり {a_g:.1f} ＋ みなみのさんかく {a_mi:.1f}', judge='○' if a_g + a_mi >= 350 else '△', note=''))
row('管理', '事務室', '約 60', 54, ('59_1F_事務', '59_1F_園長室・応接', '43_', '43b_'), '園長室・応接・更衣を含む（課題の注）。湯沸は 2 階の便所・湯沸')
row('管理', '休憩室', '約 60', 54, ('44_', '45_'), 'ぐったり休憩（横になれる）を含む')
row('管理', '医務室', '約 30', 27, ('59_1F_医務', '59_1F_静養室'))
row('管理', '調理室', '約 60', 54, ('32_', '57_'), '給食室・食品庫。調理の更衣・便所・前室を含む')
row('管理', '便所（大人用）', '適宜', None, ('42_', '59_1F_多目的便所', '59_1F_便所（職員）'), '1 階：多目的便所（スパン 11）・職員の個室（スパン 14）、2 階：便所・湯沸。3 か所とも性別なし。ほかに調理の便所')
row('管理', '機械室', '約 30', 27, ('35_',), '本館の北の外')
# 倉庫：道具入れとして確保した場所は全部数える（ユーザー、10-25）。建物の中の倉庫（教材庫）＋園庭の小屋の倉庫（data/garden.json の HUT、閉じた部屋）
_gd = json.load(open(os.path.join(DATA, 'garden.json'), encoding='utf-8')).get('HUT', {})
a_hut = (_gd['closed_a'] - _gd['split_a']) * (_gd['d'][1] - _gd['d'][0]) if all(k in _gd for k in ('closed_a', 'split_a', 'd')) else 0.0
a_st, p_st = S('59_1F_倉庫', '36b_')
p_st = sorted(p_st) + ([('園庭の小屋の倉庫', a_hut)] if a_hut else [])
a_st += a_hut
ROWS.append(dict(group='管理', room='倉庫', required='約 30', planned=round(a_st, 1),
                 parts=' ＋ '.join(f'{nm(k)} {v:.1f}' for k, v in p_st), judge='○' if a_st >= 27 else '',                                   # 足りない間は判定を空ける（検討中、ユーザーと相談、10-25）
                 note='道具入れとして確保した場所は全部数える（ユーザー 10-25）：1 階のスパン 14・17 の倉庫（教材庫）、本館と西館のすき間の倉庫、西館の階段の下の倉庫、園庭の小屋の倉庫。約 30 に足りない間は判定を空けている（検討中）'))
ROWS.append(dict(group='管理', room='駐車場', required='5 台以上', planned=None, parts='南 3 台・北 2 台（うち 1 台は搬入）', judge='○', note='決定事項_外構'))
ROWS.append(dict(group='管理', room='駐輪スペース', required='適宜', planned=None, parts='', judge='', note='未定'))
# その他（課題文：自由に加えてよい）
OTHER = []
for keys, label in ((('59_1F_ホール', '41_'), 'ホール（1・2 階）'), (('56_', '59_1F_西吹き抜け'), '西吹き抜け（先生の道・窓辺）'),
                    (('33_',), '東の帯'), (('52_',), '受け取り土間'), (('15_',), '海峡（南の入口）'), (('13_',), '内縁側'), (('36_',), '階段')):
    a, _ = S(*keys); OTHER.append(dict(room=label, planned=round(a, 1)))

# ---------------------------------------------------------------- 延床面積
def floor_wc(F, zf):
    """床の広がり F を壁芯の延床に：外壁を除いて間仕切りの下を足し、接する外壁の半分を足す"""
    W_EXT, W_INT, _ = walls_at(zf)
    inner = unary_union([F, W_INT.intersection(F.buffer(NEAR))]).difference(W_EXT)
    return Polygon() if F.is_empty else type('X', (), {'area': inner.area + 0.5 * W_EXT.intersection(inner.buffer(NEAR)).area})()
F1r = unary_union([g for k, g in A0.items() if re.match(r'^(12|13|15|3[1-6]|5[2-9])[a-z]?_', k) and not k.startswith('35_')])
F1m = floor_wc(unary_union([F1r, A0.get(next((k for k in A0 if k.startswith('35_')), ''), Polygon())]), 0.0)
Z2 = max((z for k, z in FZ.items() if k.startswith('23_')), default=3170.0)
F2 = floor_wc(unary_union([g for k, g in A0.items() if k.startswith('23_')]), Z2)
# 園庭の小屋（ユーザー、10-25、連携 20261025-1019-garden）：便所と倉庫は壁と屋根のある部屋なので延床に足す。コンポストの間（屋根だけ）は入れない
a_hut_wc = (_gd['split_a'] - _gd['a'][0]) * (_gd['d'][1] - _gd['d'][0]) if all(k in _gd for k in ('a', 'split_a', 'd')) else 0.0
a_hut_room = a_hut_wc + a_hut
TOTAL = dict(floor1=round(area(F1m), 1), floor2=round(area(F2), 1), hut=round(a_hut_room, 1),
             total=round(area(F1m) + area(F2) + a_hut_room, 1), limit=2000,
             building_area_note='壁芯（床の板から自動）。外縁側（土足の軒下）は含めない。機械室を含む。園庭の小屋の便所と倉庫を含む（コンポストの間は屋根だけなので含めない）。')

def stamp():
    h = subprocess.run(['git', '-C', os.path.dirname(os.path.abspath(IN)), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    t = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    return f'{t}（atelier {h} の次の版の 3dm）'
ST = stamp()
json.dump(dict(made=ST, rooms=ROWS, other=OTHER, floor=TOTAL, layers={k: round(area(g), 1) for k, g in sorted(A.items())}),
          open(os.path.join(OUTD, 'sodachiya_areas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open(os.path.join(OUTD, 'sodachiya_areas.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['部門', '室', '要求（m²）', '計画（m²）', '判定', '内訳', '注'])
    for rw in ROWS: w.writerow([rw['group'], rw['room'], rw['required'], rw['planned'] if rw['planned'] is not None else '', rw['judge'], rw['parts'], rw['note']])
    w.writerow([]); w.writerow(['その他', '室', '', '計画（m²）'])
    for o in OTHER: w.writerow(['その他', o['room'], '', o['planned']])
    w.writerow([]); w.writerow(['延床', '1 階', '', TOTAL['floor1']]); w.writerow(['延床', '2 階（西館）', '', TOTAL['floor2']]); w.writerow(['延床', '園庭の小屋（便所・倉庫）', '', TOTAL['hut']])
    w.writerow(['延床', '合計', '2,000 以内', TOTAL['total'], '○' if TOTAL['total'] <= 2000 else '×'])

# ---------------------------------------------------------------- 表（A3 横）
for fp in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in fp: font_manager.fontManager.addfont(fp)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['pdf.fonttype'] = 42
W_, H_ = 420, 297
fig = plt.figure(figsize=(W_ / 25.4, H_ / 25.4)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W_); ax.set_ylim(0, H_); ax.axis('off')
T = lambda x, y, t, pt=7, **kw: ax.text(x, y, t, fontsize=pt, va='center', **kw)
T(15, H_ - 15, '面積表　こどもたちの育ち舎', 13)
T(15, H_ - 22, '3dm（sodachiya_exact_mesh.3dm）の部屋の床から自動で測った値（m²、壁芯）。要求は課題文（2026-09-28）の「所要室と面積」。', 6.5, color='0.35')
cols = [15, 33, 75, 105, 130, 145, 290]
y = H_ - 34
for x, h in zip(cols, ['部門', '室', '要求', '計画', '判定', '内訳', '注']): T(x, y, h, 7, color='0.4')
ax.plot([15, W_ - 15], [y - 3.5, y - 3.5], color='k', lw=0.6)
y -= 8.5
for rw in ROWS:
    T(cols[0], y, rw['group'], 7); T(cols[1], y, rw['room'], 7.5); T(cols[2], y, rw['required'], 7)
    T(cols[3] + 18, y, '—' if rw['planned'] is None else f"{rw['planned']:.1f}", 7.5, ha='right')
    T(cols[4] + 3, y, rw['judge'], 8, color='#B03030' if rw['judge'] == '△' else 'k', ha='center')
    T(cols[5], y, rw['parts'], 5.8, color='0.25'); T(cols[6], y, rw['note'], 5.8, color='0.35')
    ax.plot([15, W_ - 15], [y - 4, y - 4], color='0.85', lw=0.3); y -= 8
y -= 4
T(15, y, 'その他の場所（課題文：必要と思う空間は自由に加えてよい）', 7.5); y -= 7
for o in OTHER:
    T(cols[1], y, o['room'], 7); T(cols[3] + 18, y, f"{o['planned']:.1f}", 7.5, ha='right'); y -= 6.5
y -= 4
ax.plot([15, 200], [y + 3, y + 3], color='k', lw=0.6)
T(cols[1], y - 2, '延床面積', 8.5)
T(cols[2], y - 2, '2,000 以内', 7.5)
T(cols[3] + 18, y - 2, f"{TOTAL['total']:,.1f}", 9, ha='right')
T(cols[4] + 3, y - 2, '○' if TOTAL['total'] <= 2000 else '×', 9, ha='center')
T(cols[5], y - 2, f"1 階 {TOTAL['floor1']:,.1f} ＋ 西館 2 階 {TOTAL['floor2']:,.1f} ＋ 園庭の小屋 {TOTAL['hut']:,.1f}。{TOTAL['building_area_note']}", 6, color='0.25')
T(15, 12, '判定：○「約」は要求の 9 割以上・「以上」は要求以上／△ 足りない（数え方を含めて検討）。空欄は要求が「適宜」など。　' + ST, 6, color='0.35')
fig.savefig(os.path.join(PDFD, 'sodachiya_areas.pdf')); fig.savefig(os.path.join(OUTD, 'sodachiya_areas.png'), dpi=130)
print('areas: total', TOTAL['total'], '→', OUTD)
for rw in ROWS: print(' ', rw['room'], rw['required'], rw['planned'], rw['judge'])
