"""干渉の一覧（設計監修、10-24。ユーザー：部材どうしの重なりを根本から）
使い方: python3 clash.py IN.3dm OUT.json [OUT.txt]

部材（solids.py の種類 S 構造・E 外皮・F 床・D 戸・P 間仕切り・I 家具・X 外の付属）の閉じた立体どうしで、
見て分かる誤りになるものを数える（作り直しのたびに 0 へ）：
  1. 屋根から出る：屋根の上面（屋根・光の筋・越屋根の蓋のいちばん上の面）より 20 以上上へ出た部材
     （屋根の上に載るもの＝屋根・蓋・越屋根のルーバー・LED・屋根材の太陽光・室外機置場・樋は除く）。
  1b. 屋根の外へ出る構造：柱・梁・桁（S）のうち、屋根の覆う範囲の外にある部分（軒の先から出た梁の端など）。
  2. 埋まったガラス：ガラス（16・19・27・48）の半分以上が外壁（17・21）の中にある（壁に開口が無い）。
  3. 種類をまたぐ食い込み：優先の低いほうが削られずに残っている重なり（削る段 clip_parts.py の後は 0 のはず）。
     構造どうし・構造と外皮・外皮どうし（S・E）の重なりは、仕口・壁に載る屋根など設計どおりの取り合いが多いので
     「取り合い」として数だけ（はみ出しは 1 で出る）。床が梁・桁に載る所（F × 22b・22c・22d）も取り合い（10-29）。
  4. 同じ種類どうし（家具と家具など）の重なりは数だけ。
閉じていない物（面だけ）は数に入れず、数だけ書く。
"""
import sys, os, json, collections, numpy as np
from rtree import index
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solids import load, RANK, RoofRaster
from uv import uv

VMIN = 5e5          # 0.5 L 未満は数えない（接するだけ・数 mm の食い込み）
ON_ROOF = ('10', '20', '10t', '20t', '28', '50a', '50b', '50c', '29', '30', '10p', '20p', '26', '21g')
GLASS = ('16', '19', '27', '48')

def where(bbmin, bbmax):
    cx, cy, cz = [(bbmin[i] + bbmax[i]) / 2 for i in range(3)]
    u, v = uv(cx, cy)
    return dict(u=round(u, 2), v=round(v, 2), z=round(cz), dz=round(bbmax[2] - bbmin[2]))

def run(path):
    m, LN, parts = load(path)
    RR = RoofRaster(parts)
    import trimesh as _tm
    from shapely.geometry import box as _box
    from solids import to_manifold as _tom
    # 屋根の覆う範囲：覆いの層（屋根・光の筋のガラス・越屋根の蓋）の三角形をそのまま平面に落とした和（10-25 監修、本館係の指摘）。
    # 前の RR.covered_poly() は 250 の格子のますの和で、軒先・けらばで実際の縁より最大約 125 内側になり、縁にそろえた梁の端が
    # 「屋根の外へ出る構造」と誤って出ていた
    from solids import COVER_LAYERS as _CL
    from shapely.geometry import Polygon as _Pg
    from shapely.ops import unary_union as _uu
    _tris = []
    for q in parts:
        if q['layer'].split('_')[0] not in _CL: continue
        T = np.asarray(q['tm'].triangles)[:, :, :2]
        _tris += [_Pg(t) for t in T if abs((t[1, 0] - t[0, 0]) * (t[2, 1] - t[0, 1]) - (t[2, 0] - t[0, 0]) * (t[1, 1] - t[0, 1])) > 2.0]
    ROOFED = _uu([t.buffer(0.5) for t in _tris]).buffer(-0.5) if _tris else RR.covered_poly()
    out_s = []
    idx = index.Index(properties=index.Property(dimension=3))
    for k, p in enumerate(parts):
        b = p['bb']; idx.insert(k, (*b[0], *b[1]))
    poke, buried, cross, joint, same = [], [], collections.Counter(), collections.Counter(), collections.Counter()
    cross_list = []
    open_ = collections.Counter(p['layer'][:14] for p in parts if p['M'] is None)
    for a, p in enumerate(parts):
        if p['M'] is None: continue
        pre = p['layer'].split('_')[0]
        # 1. 屋根から出る
        if pre not in ON_ROOF:
            U = RR.above(RR.Ztop + 20, p['bb'])
            if U is not None:
                X = p['M'] ^ U; v = X.volume()
                if v > VMIN:
                    bb = X.bounding_box()
                    poke.append(dict(layer=p['layer'], name=p['name'], L=round(v / 1e6, 2), **where(bb[:3], bb[3:])))
        b = p['bb']
        if p['klass'] == 'S':
            reg = _box(b[0][0] - 10, b[0][1] - 10, b[1][0] + 10, b[1][1] + 10).difference(ROOFED.buffer(50))
            for pg in getattr(reg, 'geoms', [reg]):
                if pg.geom_type != 'Polygon' or pg.area < 1e3: continue
                t_ = _tm.creation.extrude_polygon(pg, b[1][2] - b[0][2] + 200); t_.apply_translation([0, 0, b[0][2] - 100])
                O = _tom(t_)
                if O is None: continue
                X = p['M'] ^ O; v = X.volume()
                if v > VMIN:
                    bb = X.bounding_box()
                    out_s.append(dict(layer=p['layer'], name=p['name'], L=round(v / 1e6, 2), **where(bb[:3], bb[3:])))
        for c in idx.intersection((*b[0], *b[1])):
            if c <= a: continue
            q = parts[c]
            if q['M'] is None: continue
            X = p['M'] ^ q['M']; v = X.volume()
            if v <= VMIN: continue
            pq = (p, q) if RANK[p['klass']] <= RANK[q['klass']] else (q, p)
            hi, lo = pq
            # 2. 埋まったガラス
            g = next((x for x in (p, q) if x['layer'].split('_')[0] in GLASS), None)
            w = next((x for x in (p, q) if x['layer'].split('_')[0] in ('17', '21')), None)
            if g is not None and w is not None and v > 0.5 * g['M'].volume():
                bb = X.bounding_box()
                buried.append(dict(glass=g['layer'], wall=w['layer'], L=round(v / 1e6, 2), **where(bb[:3], bb[3:])))
                continue
            if hi['klass'] == lo['klass']:
                same[(hi['layer'][:14], lo['layer'][:14])] += 1; continue
            if hi['klass'] in 'SE' and lo['klass'] in 'SE':
                joint[(hi['layer'][:14], lo['layer'][:14])] += 1; continue
            # 床が梁・桁に載る所（西館の 2 階の床 23 × 22b・22c・22d）も取り合い。削る段は床を梁で欠き込まない（監修 10-29、clip_parts.py）
            if lo['klass'] == 'F' and hi['layer'].split('_')[0] in ('22b', '22c', '22d'):
                joint[(hi['layer'][:14], lo['layer'][:14])] += 1; continue
            bb = X.bounding_box()
            cross[(hi['layer'][:14], lo['layer'][:14])] += 1
            cross_list.append(dict(hi=hi['layer'], lo=lo['layer'], hi_name=hi['name'], lo_name=lo['name'], L=round(v / 1e6, 2), **where(bb[:3], bb[3:])))
    return dict(n_parts=len(parts), open=open_, out_s=sorted(out_s, key=lambda d: -d['L']), poke=sorted(poke, key=lambda d: -d['L']), buried=buried,
                cross=sorted(cross_list, key=lambda d: -d['L']), cross_by=cross, joint=joint, same=same)

if __name__ == '__main__':
    IN, OJ = sys.argv[1:3]; OT = sys.argv[3] if len(sys.argv) > 3 else None
    R = run(IN)
    js = dict(R); js['open'] = dict(R['open'])
    for k in ('cross_by', 'joint', 'same'): js[k] = {' × '.join(a): b for a, b in R[k].items()}
    json.dump(js, open(OJ, 'w'), ensure_ascii=False, indent=1)
    L = [f"clash: 物 {R['n_parts']}（閉じていない {sum(R['open'].values())}）　"
         f"屋根から出る {len(R['poke'])}・屋根の外へ出る構造 {len(R['out_s'])}・埋まったガラス {len(R['buried'])}・種類をまたぐ食い込み {len(R['cross'])}　"
         f"（取り合い {sum(R['joint'].values())}・同じ種類どうし {sum(R['same'].values())} は数だけ）"]
    if R['poke']:
        L.append('屋根から出る（屋根の上面より上の体積）：')
        for d in R['poke'][:40]: L.append(f"  {d['L']:8.2f} L  {d['layer'][:16]} {d['name'][:20]}  u{d['u']} v{d['v']} z{d['z']}")
    if R['out_s']:
        L.append('屋根の外へ出る構造（屋根の覆う範囲の外の体積）：')
        for d in R['out_s'][:40]: L.append(f"  {d['L']:8.2f} L  {d['layer'][:16]} {d['name'][:20]}  u{d['u']} v{d['v']} z{d['z']}")
    if R['buried']:
        L.append('埋まったガラス（壁に開口が無い）：')
        for d in R['buried']: L.append(f"  {d['L']:8.2f} L  {d['glass'][:16]} が {d['wall'][:12]} の中  u{d['u']} v{d['v']} z{d['z']} 高さ{d['dz']}")
    if R['cross']:
        L.append('種類をまたぐ食い込み：')
        for d in R['cross'][:40]: L.append(f"  {d['L']:8.2f} L  {d['hi'][:14]} {d['hi_name'][:14]} × {d['lo'][:14]} {d['lo_name'][:14]}  u{d['u']} v{d['v']} z{d['z']}")
    L.append('閉じていない物：' + '、'.join(f'{k} {v}' for k, v in R['open'].most_common()))
    txt = '\n'.join(L); print(txt)
    if OT: open(OT, 'w').write(txt + '\n')
