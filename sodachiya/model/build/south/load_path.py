"""力の道の点検（設計監修、10-29。ユーザー：どの構造の部材の力も、ほかの部材を通って地面まで届くか）
使い方: python3 load_path.py IN.3dm OUT.json [OUT.txt]

部材：構造の層（本館 11a 柱・11b 梁の板・11c 桁・10v 母屋・10s 南の軒の鋼、西館 22a 柱・22b 梁の板と出し梁・
22c 2階床梁・22d 桁・まぐさ・窓台・20v 母屋・鼻母屋・23 2階床、外壁 17・21、24 のうち階段の箱の壁）。
地面：下の面が z ≤ 5 の部材（柱の足・外壁の足。基礎は 3dm に無いので GL を地面とする）。

支え（A が B に支えられる）は、平らな面どうしの向かい合い（向きの差 15°以内、木口は 50°以内）と重なりで見る。
離れは重なりの中で一次の式として測り、5 以内（食い込み 15 まで）の所の面積を数える：
  載る        A の下向きの面が B の上向きの面に 5 以内（面の重なり 1,000 mm² 以上）
  柱の穴      同じで、離れが 5〜15 の柱の穴の下の縁（本館の桁、模型の穴は 10 ほどのあそび）→ 載ると同じ
  穴の縁      離れ 5〜15 の、柱でない材（梁の板）の穴の縁 → 金物頼み
  挟む・重ね  横向きの面どうしが 5 以内、両方とも材の長い側の面（柱の頭を 2 枚の梁で挟む、ボルトの重ね）
  金物（決まった納まり）：母屋の木口が梁の側面に（両端は梁の側面の金物）、木口が柱の側面に（桁・窓台・まぐさは柱の面で止めて金物）、
              南の軒の鋼、梁の木口に出し梁（梁が出し梁を受ける向きだけ）→ 載ると同じ
  突き当たり  木口がそれ以外の面（梁の板・外壁など）に当たる、木口どうし（継手）→ 金物頼み
  木口の角だけ 斜め（10°より）に当たる木口で、5 以内に当たる所が木口の 2 割に満たない（楔のすき間）→ 金物頼み
  食い込み    閉じた立体どうしが 0.2 L 以上重なり、B が重なりより下へ続く（壁に差し込んだ端など）
地面から上へ、支えをたどる（幅優先）。出すもの：
  浮いている     どの道でも地面に届かない
  金物頼みだけ   届くが、途中に「穴の縁」「突き当たり」「木口の角だけ」が要る
  片持ち         長い材で、支えが片方の半分にしかない（出し梁・鋼の片持ち・鼻母屋の先などの設計どおりのものは別に数だけ）
  端が届かない   長い材の木口が、向かいの部材の面まで 5〜100 離れている（向かい合う面の重なりがある所）
作り直しを止めない（知らせだけ）。check_build.py が OUT.json・OUT.txt を読んで sodachiya_check.txt に節を書く。
約1.5分、約0.5 GB。試すとき：LP_CACHE=<pickle> で読んだ部材を使い回す、LP_SHOW=<id,…> でその部材の支えを出す。
"""
import sys, os, json, re, collections, time, numpy as np
import rhino3dm as r, trimesh
from rtree import index
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solids import geom_vf, to_trimesh, to_manifold
from uv import uv

T0 = time.time()
DBG = set(filter(None, os.environ.get('LP_DBG', '').split(',')))
LAYERS = ('11a', '11b', '11c', '10v', '10s', '22a', '22b', '22c', '22d', '20v', '23', '17', '21', '24')
WALL24 = '階段の箱'                 # 24 は階段の箱の壁だけ（骨格）。間仕切りは床に載る板で、力の道に入れない
TOL, HOLE, NEAR, PEN = 5.0, 15.0, 100.0, 15.0     # PEN：面どうしの食い込み（接すると見る）
AMIN = 1000.0                        # 支えと見る面の重なり（mm²）
PAR = np.cos(np.radians(15))           # 向かい合う面の向きの差
PAR_END = np.cos(np.radians(50))       # 木口が斜めに当たるとき
PAR10 = np.cos(np.radians(10))
DESIGNED = re.compile(r'出し梁|片持ち|軒先|鼻母屋|縁の材')
BLD = lambda pre: '本館' if pre[0] == '1' else '西館'


def regions(t, org):
    """平らな面のまとまり → [(n, d, e1, e2, poly2d, area, bottom/top/side)]"""
    V = np.asarray(t.vertices) - org; F = np.asarray(t.faces); N = t.face_normals; A = t.area_faces
    groups = [list(f) for f in t.facets]
    used = np.zeros(len(F), bool)
    for g in groups: used[g] = True
    groups += [[i] for i in np.where(~used)[0]]
    out = []
    for g in groups:
        ar = float(A[g].sum())
        if ar < 200: continue
        n = (N[g] * A[g][:, None]).sum(0); n /= np.linalg.norm(n) + 1e-12
        e1 = np.cross(n, [0, 0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0, 0]); e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        P = V[F[g]]                                     # (k, 3, 3)
        d = float(np.mean(P.reshape(-1, 3) @ n))
        Q = np.stack([P @ e1, P @ e2], -1)              # (k, 3, 2)
        tris = shapely.polygons(np.concatenate([Q, Q[:, :1]], 1))
        pg = tris[0] if len(g) == 1 else shapely.union_all(tris, grid_size=0.05)
        if pg.is_empty or pg.area < 100: continue
        lo = P.reshape(-1, 3).min(0); hi = P.reshape(-1, 3).max(0)
        out.append(dict(n=n, d=d, e1=e1, e2=e2, pg=pg, area=ar, lo=lo, hi=hi, P=np.unique(P.reshape(-1, 3), axis=0)))
    return out


def load(path):
    m = r.File3dm.Read(path)
    LN = {i: l.FullPath for i, l in enumerate(m.Layers)}
    org = None; mem = []
    for o in m.Objects:
        ln = LN[o.Attributes.LayerIndex]; pre = ln.split('_')[0]
        if pre not in LAYERS: continue
        nm = o.Attributes.Name or ''
        if pre == '24' and WALL24 not in nm: continue
        if '縁の材' in nm: continue      # 光の筋の端の縁の材は屋根の合板の上の小さな材（力の道に入れない）
        vf = geom_vf(o.Geometry)
        if vf is None or len(vf[1]) == 0: continue
        try: t = to_trimesh(*vf)
        except Exception: continue
        if len(t.faces) == 0: continue
        if org is None: org = np.round(t.vertices.mean(0), -3)
        V = np.asarray(t.vertices) - org
        c = V.mean(0); _, s, Vt = np.linalg.svd(V - c, full_matrices=False)
        ax = Vt[0]; pr = (V - c) @ Vt.T
        ext = pr.max(0) - pr.min(0)
        elong = ext[0] / max(ext[1], 1.0)
        mem.append(dict(id=str(o.Attributes.Id)[:8], layer=pre, name=nm, t=t, bb=np.array([V.min(0), V.max(0)]), ax=ax, c=c,
                        L=float(ext[0]), long=elong > 3.0 and pre not in ('17', '21', '23'), M=None))
    for q in mem: q['R'] = regions(q['t'], org)
    return mem, org


def where(p, org):
    x, y, z = p + org; u, v = uv(x, y)
    return round(u, 2), round(v, 2), int(round(z))


def run(path):
    cache = os.environ.get('LP_CACHE')              # 試すとき：読んだ部材を pickle に置いて使い回す
    if cache and os.path.exists(cache):
        import pickle; mem, org = pickle.load(open(cache, 'rb'))
    else:
        mem, org = load(path)
        if cache:
            import pickle; pickle.dump((mem, org), open(cache, 'wb'))
    print(f'読んだ {len(mem)} 部材 {time.time() - T0:.0f} 秒', file=sys.stderr)
    idx = index.Index(properties=index.Property(dimension=3))
    for k, q in enumerate(mem): idx.insert(k, (*(q['bb'][0] - NEAR), *(q['bb'][1] + NEAR)))
    edges = collections.defaultdict(list)          # B → [(A, kind)]：B が A を支える
    sup = collections.defaultdict(list)            # A → [(B, kind, pts2d along axis (s0, s1))]
    endgap = collections.defaultdict(list)          # A → [(gap, B, point)]
    kinds = collections.Counter()

    for q in mem:
        if 'srange' not in q:
            s = (np.asarray(q['t'].vertices) - org - q['c']) @ q['ax']; q['srange'] = (float(s.min()), float(s.max()))
    def is_end(q, ra):
        """木口：材の軸の向きの面で、軸の端から 300 以内（梁の板の穴の内側の面などは木口でない）"""
        if not q['long'] or abs(float(ra['n'] @ q['ax'])) <= 0.35: return False      # 斜めに切った木口も（長い側の面は 0）
        s = (ra['P'] - q['c']) @ q['ax']; s0, s1 = q['srange']
        return s.min() <= s0 + 300 or s.max() >= s1 - 300

    def proj(q, ra, poly2):
        if poly2.is_empty: return None
        cs = np.asarray(poly2.convex_hull.exterior.coords) if poly2.geom_type != 'Point' else None
        if cs is None or len(cs) == 0: return None
        P = np.outer(cs[:, 0], ra['e1']) + np.outer(cs[:, 1], ra['e2']) + ra['d'] * ra['n']
        s = (P - q['c']) @ q['ax']
        return float(s.min()), float(s.max()), P.mean(0)

    def add(B, A, kind, area, iv):
        edges[B].append((A, kind)); kinds[kind] += 1
        sup[A].append((B, kind, iv[0], iv[1], iv[2]))

    def hanger(qe, qo):
        """木口 qe が qo の側面に当たる所が、決まった金物の納まりか（母屋の両端は梁の側面の金物、南の軒の鋼の骨は架構にボルト、柱の側面）"""
        return ((qe['layer'] in ('10v', '20v') and qo['layer'] in ('11b', '22b')) or qe['layer'] == '10s' or qo['layer'] == '10s'
                or qo['layer'] in ('11a', '22a'))       # 桁・窓台・まぐさは柱の面で止めて柱に金物で留める（決定事項_西館の「架構の仕上げ」）

    for a, qa in enumerate(mem):
        for b in idx.intersection((*qa['bb'][0], *qa['bb'][1])):
            if b <= a: continue
            qb = mem[b]
            lo = np.maximum(qa['bb'][0], qb['bb'][0]); hi = np.minimum(qa['bb'][1], qb['bb'][1])
            near_only = (hi - lo).min() < -HOLE           # 箱どうしが 15 より離れる → 木口の近さだけ見る
            acc = {}                                      # (支える, 支えられる, 種類) → [面積, s0, s1, 点]
            def put(key, area, ra, inter, q=None):
                if inter.is_empty: return
                cs = np.asarray(inter.convex_hull.exterior.coords) if inter.convex_hull.geom_type == 'Polygon' else np.asarray(inter.convex_hull.coords)
                P = np.outer(cs[:, 0], ra['e1']) + np.outer(cs[:, 1], ra['e2']) + ra['d'] * ra['n']
                v = acc.get(key)
                if v is None: acc[key] = [area, [P]]
                else: v[0] += area; v[1].append(P)
            for ra in qa['R']:
                if (ra['hi'] < qb['bb'][0] - NEAR).any() or (ra['lo'] > qb['bb'][1] + NEAR).any(): continue
                for rb in qb['R']:
                    c = float(ra['n'] @ rb['n'])
                    if c > -PAR_END: continue
                    if (rb['hi'] < ra['lo'] - NEAR).any() or (rb['lo'] > ra['hi'] + NEAR).any(): continue
                    endA, endB = is_end(qa, ra), is_end(qb, rb)
                    if c > -PAR and not (endA or endB): continue      # 木口は斜めに当たってもよい（斜めのスパンの母屋・桁）
                    sd = rb['P'] @ ra['n'] - ra['d']             # B の面の点の、A の面からの外向きの離れ
                    if sd.max() < -PEN or sd.min() > NEAR: continue
                    if near_only and sd.min() <= HOLE: continue
                    if sd.min() > HOLE and not (endA or endB): continue
                    pb = shapely.transform(rb['pg'], lambda X, rb=rb, ra=ra: (np.outer(X[:, 0], rb['e1']) + np.outer(X[:, 1], rb['e2']) + rb['d'] * rb['n']) @ np.c_[ra['e1'], ra['e2']])
                    try: inter = ra['pg'].intersection(pb)
                    except Exception: inter = ra['pg'].buffer(0).intersection(pb.buffer(0))
                    if inter.area < 50: continue
                    # A の面の外向きに B の面までの離れ（面がわずかに傾いていても、重なりの中で測る）
                    # A の面の外向きに B の面までの離れ g は、A の面の上で一次の式（面がわずかに傾いていても、斜めに当たっても測れる）
                    g0 = float((rb['d'] - ra['d'] * (rb['n'] @ ra['n'])) / c)
                    gg = -np.array([rb['n'] @ ra['e1'], rb['n'] @ ra['e2']]) / c
                    hull = inter.convex_hull
                    x0 = np.asarray(hull.exterior.coords if hull.geom_type == 'Polygon' else hull.coords)
                    gv = g0 + x0 @ gg
                    if gv.min() > NEAR or gv.max() < -PEN: continue
                    def clip(lo_, hi_):
                        out = inter
                        nrm = float(np.hypot(*gg))
                        bx = inter.bounds; diam = float(np.hypot(bx[2] - bx[0], bx[3] - bx[1]))
                        gc = float(g0 + np.asarray(inter.centroid.coords[0]) @ gg)
                        if nrm * diam < 0.5:                       # 重なりの中で離れがほぼ一定
                            return out if lo_ <= gc <= hi_ else None
                        if gc - nrm * diam > hi_ or gc + nrm * diam < lo_: return None
                        u_ = gg / nrm; p_ = np.array([-u_[1], u_[0]]); cc = np.asarray(inter.centroid.coords[0]); B9 = 4 * diam + 10
                        for lim, sgn in ((hi_, -1), (lo_, 1)):
                            if abs(lim - gc) > nrm * diam: continue        # その側は重なりの外
                            xl = cc + (lim - (g0 + cc @ gg)) / nrm * u_
                            hp = Polygon([xl + p_ * B9, xl - p_ * B9, xl - p_ * B9 + sgn * u_ * B9, xl + p_ * B9 + sgn * u_ * B9])
                            out = out.intersection(hp)
                            if out.is_empty: return None
                        return out
                    th = max(AMIN, 0.2 * min(ra['area'], rb['area'])) if (endA or endB) and c > -PAR10 else AMIN     # 10°より斜めに当たる木口は、面の 2 割以上が 5 以内で当たる
                    if DBG and {qa['id'], qb['id']} <= DBG: print('DBG', qa['id'], qb['id'], endA, endB, round(c, 3), round(g0, 1), gg, round(inter.area), th, file=sys.stderr)
                    nz = ra['n'][2]
                    c5 = clip(-PEN, TOL)
                    corner = False
                    if c5 is not None and c5.area >= (th if (endA or endB) else 50):
                        inter, g = c5, 0.0
                    elif c5 is not None and c5.area >= 50 and abs(nz) <= 0.5:      # 木口が斜めで、角だけが当たる（楔のすき間）
                        inter, g, corner = c5, 0.0, True
                    else:
                        c15 = clip(-PEN, HOLE) if abs(nz) > 0.5 else None
                        if c15 is not None and c15.area >= 50:
                            inter, g = c15, HOLE
                        else:
                            if (endA or endB) and inter.area >= 300:
                                gm = float(g0 + np.asarray(inter.representative_point().coords[0]) @ gg)      # 木口と向かいの面の離れ（重なりの中ほど）
                                if TOL < gm <= NEAR:
                                    if endA: endgap[a].append((round(gm), b, proj(qa, ra, inter)[2]))
                                    if endB: endgap[b].append((round(gm), a, proj(qa, ra, inter)[2]))
                            continue
                    if nz < -0.5:   put((b, a, 'bear' if g <= TOL else 'hole'), inter.area, ra, inter, qa)
                    elif nz > 0.5:  put((a, b, 'bear' if g <= TOL else 'hole'), inter.area, ra, inter)
                    else:
                        if endA and endB:                      # 木口どうし（継手）。出し梁と梁は一つの梁の続き
                            if qa['layer'] == qb['layer'] == '22b' and ('出し梁' in qa['name']) != ('出し梁' in qb['name']):
                                if '出し梁' in qa['name']: put((b, a, 'hanger'), inter.area, ra, inter)       # 梁が出し梁を受ける（逆は無い）
                                else: put((a, b, 'hanger'), inter.area, ra, inter)
                            else: put((b, a, 'butt'), inter.area, ra, inter); put((a, b, 'butt'), inter.area, ra, inter)
                        elif corner:
                            if endA: put((b, a, 'corner'), inter.area, ra, inter)
                            if endB: put((a, b, 'corner'), inter.area, ra, inter)
                        elif endA: put((b, a, 'hanger' if hanger(qa, qb) else 'butt'), inter.area, ra, inter)     # A の木口が B の側面に当たる：B が A を受ける
                        elif endB: put((a, b, 'hanger' if hanger(qb, qa) else 'butt'), inter.area, ra, inter)
                        else: put((b, a, 'lap'), inter.area, ra, inter); put((a, b, 'lap'), inter.area, ra, inter)
            found = False
            for (B_, A_, k), (area, Ps) in acc.items():
                if area < (50 if k == 'corner' else AMIN): continue
                if k == 'hole' and mem[B_]['layer'] in ('11a', '22a'): k = 'hole_post'     # 柱の穴に通して載る（設計どおりの仕口、模型の穴は 10 ほどのあそび）
                found = True
                P = np.vstack(Ps); s = (P - mem[A_]['c']) @ mem[A_]['ax']      # 支えられる側の軸に
                add(B_, A_, k, area, (float(s.min()), float(s.max()), P.mean(0)))
            # 食い込み
            if not found and (hi - lo).min() > 10.0:
                for q in (qa, qb):
                    if q['M'] is None: q['M'] = to_manifold(q['t']) or False
                if qa['M'] and qb['M']:
                    I = qa['M'] ^ qb['M']
                    if I.volume() > 2e5:
                        bl = np.asarray(I.bounding_box()[:3]) - org; bh = np.asarray(I.bounding_box()[3:]) - org
                        mid = (bl + bh) / 2
                        for (x, y, qx, qy) in ((a, b, qa, qb), (b, a, qb, qa)):
                            if qy['bb'][0][2] < bl[2] - 20:           # y が重なりより下へ続く → y が x を支える
                                edges[y].append((x, 'embed')); kinds['embed'] += 1
                                s = (np.array([bl, bh]) - qx['c']) @ qx['ax']
                                sup[x].append((y, 'embed', float(s.min()), float(s.max()), mid))
    # 地面から
    roots = [k for k, q in enumerate(mem) if q['bb'][0][2] + org[2] <= 5.0]
    def bfs(ok):
        seen = set(roots); Q = collections.deque(roots); via = {}
        while Q:
            b = Q.popleft()
            for a, k in edges[b]:
                if a in seen or k not in ok: continue
                seen.add(a); via[a] = (b, k); Q.append(a)
        return seen
    R1 = bfs({'bear', 'lap', 'embed', 'hanger', 'hole_post'})
    R2 = bfs({'bear', 'lap', 'embed', 'hanger', 'hole_post', 'hole', 'butt', 'corner'})

    def info(k, extra=None):
        q = mem[k]
        u, v, z = where(q['c'], org)
        d = dict(id=q['id'], layer=q['layer'], bld=BLD(q['layer']), name=q['name'][:40], u=u, v=v, z=z,
                 u0=round(min(uv(*(q['bb'][0][:2] + org[:2]))[0], uv(*(q['bb'][1][:2] + org[:2]))[0]), 2),
                 u1=round(max(uv(*(q['bb'][0][:2] + org[:2]))[0], uv(*(q['bb'][1][:2] + org[:2]))[0]), 2))
        if extra: d.update(extra)
        return d
    floating = [info(k) for k in range(len(mem)) if k not in R2]
    hwonly = []
    for k in range(len(mem)):
        if k in R2 and k not in R1:
            ks = sorted({kk for _, kk, *_ in sup[k] if kk in ('hole', 'butt', 'corner')})
            hwonly.append(info(k, dict(how='・'.join({'hole': '穴の縁', 'butt': '突き当たり', 'corner': '木口の角だけ'}[x] for x in ks))))
    cant, cant_ok, gaps = [], 0, []
    for k, q in enumerate(mem):
        if not q['long'] or k not in R2: continue
        if q['layer'] in ('11a', '22a'): continue           # 柱は足で地面に立つ
        V = np.asarray(q['t'].vertices) - org; s = (V - q['c']) @ q['ax']; s0, s1 = s.min(), s.max(); L = s1 - s0
        S = [(x0, x1) for (_, kk, x0, x1, _) in sup[k]]
        if not S: continue
        lo = min(x0 for x0, _ in S); hi = max(x1 for _, x1 in S)
        if (hi - s0) < 0.5 * L or (s1 - lo) < 0.5 * L:
            if DESIGNED.search(q['name']) or q['layer'] == '10s': cant_ok += 1
            else:
                over = max(lo - s0, s1 - hi)
                cant.append(info(k, dict(over=int(round(over)), L=int(round(L)))))
    for k, G in endgap.items():
        q = mem[k]
        # その木口に支え（5 以内）があれば数えない
        best = {}
        for g, b, P in G:
            s = float((P - q['c']) @ q['ax']); side = 1 if s > 0 else -1
            if side not in best or g < best[side][0]: best[side] = (g, b, P, s)
        V = np.asarray(q['t'].vertices) - org; ss = (V - q['c']) @ q['ax']
        for side, (g, b, P, s) in best.items():
            # その端の 300 以内に支えがあるか
            e = ss.max() if side > 0 else ss.min()
            has = any((side > 0 and x1 >= e - 300) or (side < 0 and x0 <= e + 300) for (_, kk, x0, x1, _) in sup[k])
            u, v, z = where(P, org)
            gaps.append(dict(info(k), gap=g, to=mem[b]['id'], to_layer=mem[b]['layer'], at=dict(u=u, v=v, z=z), held=has))
    gaps.sort(key=lambda d: (d['held'], -d['gap']))
    show = os.environ.get('LP_SHOW', '').split(',')
    for k, q in enumerate(mem):
        if q['id'] in show:
            print(q['id'], q['layer'], q['name'][:20], 'R1' if k in R1 else ('R2' if k in R2 else '-'), file=sys.stderr)
            for (B_, kk, x0, x1, P) in sup[k]:
                print('   ←', mem[B_]['layer'], mem[B_]['id'], mem[B_]['name'][:16], kk, round(x0), round(x1), where(P, org), file=sys.stderr)
    res = dict(members=len(mem), roots=len(roots), kinds=dict(kinds),
               count={b: sum(1 for q in mem if BLD(q['layer']) == b) for b in ('本館', '西館')},
               floating=floating, hardware_only=hwonly, cantilever=cant, cantilever_designed=cant_ok,
               end_gap=[g for g in gaps if not g['held']], end_gap_held=[g for g in gaps if g['held']],
               sec=round(time.time() - T0, 1))
    return res


def text(res):
    """sodachiya_check.txt の節（check_build.py が足す）。母屋は架構のあいだごとにまとめる"""
    def line(d, extra=''):
        nm = f'「{d["name"]}」' if d['name'] else ''
        return f'    {d["bld"]} {d["layer"]} {d["id"]}{nm} u{d["u0"]}〜{d["u1"]} v{d["v"]} z{d["z"]}{extra}'
    def cnt(lst): c = collections.Counter(d['bld'] for d in lst); return f'本館{c["本館"]}・西館{c["西館"]}'
    def rows(lst, f):
        out, grp = [], {}
        for d in lst:
            if d['layer'] in ('10v', '20v') and d['name'].startswith('母屋'):
                k = (d['bld'], d['layer'], re.sub(r'、高さ [\d.]+', '', d['name']), '' if 'over' in d else f(d))
                grp.setdefault(k, []).append(d)
            else: out.append(line(d, f(d)))
        for (bl, ly, nm, ex), ds in grp.items():
            vs = [d['v'] for d in ds]; zs = [d['z'] for d in ds]
            if 'over' in ds[0]: ex = f'　張り出し{min(d["over"] for d in ds)}〜{max(d["over"] for d in ds)}'
            out.append(f'    {bl} {ly} 母屋{len(ds)}本「{nm[:30]}」 u{min(d["u0"] for d in ds)}〜{max(d["u1"] for d in ds)} v{min(vs)}〜{max(vs)} z{min(zs)}〜{max(zs)}{ex}')
        return out
    L = [f'力の道：地面に届かない{len(res["floating"])}（{cnt(res["floating"])}）・金物頼みだけ{len(res["hardware_only"])}（{cnt(res["hardware_only"])}）・'
         f'片持ち{len(res["cantilever"])}・端が届かない{len(res["end_gap"])}　（部材{res["members"]}、地面に立つ{res["roots"]}、設計どおりの片持ち{res["cantilever_designed"]}、{res["sec"]}秒。知らせだけ、止めない）']
    for key, title, f in (('floating', '地面に届かない（どの道でも）', lambda d: ''),
                          ('hardware_only', '金物頼みだけ（梁の板の穴の縁に5〜15のすき間で載る・木口が柱でない面に突き当たる・斜めの木口の角だけが当たる、を通らないと届かない）', lambda d: f'　{d["how"]}'),
                          ('cantilever', '片持ち（支えが片方の半分だけ。設計どおりの出し梁・鋼の片持ち・鼻母屋は除く）', lambda d: f'　張り出し{d["over"]}／長さ{d["L"]}'),
                          ('end_gap', '端が届かない（木口と向かいの面の離れ5〜100、その端の300以内に支え無し）', lambda d: f'　離れ{d["gap"]}（→{d["to_layer"]} {d["to"]}、u{d["at"]["u"]} v{d["at"]["v"]} z{d["at"]["z"]}）')):
        if res[key]:
            L.append(f'  {title}：{len(res[key])}')
            R = rows(res[key], f)
            L += R[:40]
            if len(R) > 40: L.append(f'    ほか{len(R) - 40}行')
    return '\n'.join(L)


if __name__ == '__main__':
    res = run(sys.argv[1])
    json.dump(res, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
    txt = text(res)
    if len(sys.argv) > 3: open(sys.argv[3], 'w').write(txt + '\n')
    print(txt.split('\n')[0])
