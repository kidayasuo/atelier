"""Tamediaの留めの点検（設計監修、11-01。ユーザー 10-31：本館と西館の架構は、梁の板も柱も一枚残らず Tamedia 風に留める）
使い方: python3 tamedia.py RHINO.3dm OUT.json [OUT.txt]

決まり：桁（ピン、11c・22d）が、2枚の梁の板と、そのあいだの柱の頭の、同じ丸・長円の穴を通る。ピンで留まらない梁の板・柱は無い。
模型では桁は一本の竹ひごなので、一本の桁が通る穴はみな一直線の上（芯のずれ 10 mm 以内）。桁の線が折れる所
（西館の斜めの間 u42→45→48、u21→24、本館の弧の架構ごと）は、架構の線の柱の頭の穴の中で折れる（二本の桁の端が 10 以内で会う）。

数える部材（11-01 ユーザー）：架構だけ。柱（階段の箱の柱・床梁の下の骨格の柱を除く）と梁（板二枚で一本）。西館＝柱22・梁17（22b の屋根の梁 12＝枠 u21.33…u50.57 の 11 組＋u43.5 の一枚、22c の2階の床梁 5 組）、本館＝柱40・梁20。

読むもの：Rhino版（押し出しのまま。メッシュの版は本館の桁 11c がメッシュ）。穴＝押し出しの輪郭の内側の輪。
部材：
  桁：11c、22d（窓台・まぐさを除く）。芯＝輪郭の外の輪の重心から押し出しの向きへ
  柱：11a、22a（柱の受け材を除く）。頭の穴（柱の高さの上の 1/3 にある穴）に桁が通れば留まる
  梁の板：11b、22b、22c（受け材・楔・スペーサー・腕木を除く）。両端（長さの 1/3 ずつ）の穴に桁が通れば留まる。
  出し梁・片持ちは片端（元）だけでよい
除く（釘・金物で留める小さな材、この点検に入れない）：梁・腕木・柱の受け材（22a・22b）、楔、スペーサー、合わせ梁の受け、
  腕木（22b、柱の頭から外へ、鼻母屋を受ける）、母屋・鼻母屋（10v・20v、層ごと読まない）、窓台・まぐさ（22d）。
見るもの（板・柱の厚みの中央の面で、桁の芯が穴の重心からどれだけずれるか）：
  ok：穴を桁が通り、ずれ 10 以内
  ずれ：穴を桁が通るが、ずれが 10 より大きい
  穴だけ：穴があるが、どの桁も通らない
  穴なし：留まるべき端（梁の両端・柱の頭）に穴が無い
  止まる：桁の端が板・柱の厚みの中で止まる（折れの所＝柱の穴の中で、ほかの桁の端と 10 以内で会うものは別）
  折れが外：二本の桁の端が会うが、柱の穴の中でない
  材を貫く：桁の芯が、穴の無い所で板・柱を通る
知らせだけ（作り直しを止めない）。check_build.py が OUT.json・OUT.txt を読み、check の行と sodachiya_check.txt の節に書く。数秒。
"""
import sys, os, re, json, time, numpy as np
import rhino3dm as r
from shapely.geometry import Polygon, Point
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solids import curve_pts
from uv import uv

T0 = time.time()
TOL = 10.0                       # 芯のずれ（mm、本当の寸法）。0.1 mm に丸めて比べる
FLUSH = 2.0                      # 桁の端が板・柱の面から 2 mm 以内なら面一（通った）と見る
GIRDER = ('11c', '22d'); POST = ('11a', '22a'); PLY = ('11b', '22b', '22c')
SKIP = re.compile(r'受け材|楔|スペーサー|腕木|合わせ梁の受け|窓台|まぐさ|母屋')
CANT = re.compile(r'出し梁|片持ち')
BLD = lambda ln: '本館' if ln[0] == '1' else '西館'
A = lambda p: np.array([p.X, p.Y, p.Z])


def centroid(q):
    x, y = q[:, 0], q[:, 1]; x1, y1 = np.roll(x, -1), np.roll(y, -1); cr = x * y1 - x1 * y; a = cr.sum() / 2
    if abs(a) < 1e-9: return q.mean(0)
    return np.array([((x + x1) * cr).sum() / (6 * a), ((y + y1) * cr).sum() / (6 * a)])


def load(path):
    m = r.File3dm.Read(path)
    LN = {i: l.FullPath.split('::')[-1] for i, l in enumerate(m.Layers)}
    G, M, other = [], [], []
    for o in m.Objects:
        ln = LN[o.Attributes.LayerIndex]; pre = ln.split('_')[0]
        if pre not in GIRDER + POST + PLY: continue
        name = o.Attributes.Name or ''
        if SKIP.search(name): continue
        g = o.Geometry; bb = g.GetBoundingBox()
        c = np.array([(bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2, (bb.Min.Z + bb.Max.Z) / 2])
        u, v = uv(c[0], c[1])
        d = dict(layer=pre, ln=ln, name=name, id=str(o.Attributes.Id)[:8], u=round(u, 2), v=round(v, 2), z=round(c[2]), bld=BLD(pre))
        if not isinstance(g, r.Extrusion):
            d['kind'] = 'girder' if pre in GIRDER else 'post' if pre in POST else 'ply'; other.append(d); continue
        # 輪郭の面は押し出しの向きに直角な面として自分で作る（GetProfilePlane の X・Y は輪郭の面に載らないことがある、本館の桁 11c）
        P = A(g.PathEnd) - A(g.PathStart); O = A(g.PathStart); nz = P / np.linalg.norm(P)
        X = np.cross(nz, [0, 0, 1.0]) if abs(nz[2]) < 0.9 else np.cross(nz, [0, 1.0, 0]); X /= np.linalg.norm(X); Y = np.cross(nz, X)
        rings = []
        for k in range(g.ProfileCount):
            Q = np.array([A(p) for p in curve_pts(g.Profile3d(k, 0.0))])
            rings.append(Q)
        O = O + nz * float(np.mean((rings[0] - O) @ nz))          # 輪郭が始まりの面に無いとき（念のため）
        if pre in GIRDER:
            q = np.c_[(rings[0] - O) @ X, (rings[0] - O) @ Y]; c2 = centroid(q)
            a = O + c2[0] * X + c2[1] * Y
            d.update(kind='girder', a=a, b=a + P, L=float(np.linalg.norm(P)))
            G.append(d)
        else:
            t = float(np.linalg.norm(P)); n = P / t
            q2 = [np.c_[(R - O) @ X, (R - O) @ Y] for R in rings]
            d.update(kind='post' if pre in POST else 'ply', O=O, X=X, Y=Y, n=n, t=t, P=P,
                     outer=Polygon(q2[0]).buffer(0), holes=[(Polygon(h).buffer(0), centroid(h)) for h in q2[1:]],
                     q=q2[0])
            M.append(d)
    return G, M, other


def run(path):
    G, M, other = load(path)
    hits = {id(m): {} for m in M}          # 部材→穴の番号→[(ずれ, 桁)]
    solid, stops, ends = [], [], []
    for g in G:
        a, b = g['a'], g['b']; t = b - a; g['through'] = 0
        for m in M:
            den = t @ m['n']
            if abs(den) < 1e-6 * g['L']: continue
            s0 = ((m['O'] - a) @ m['n']) / den; s1 = ((m['O'] + m['P'] - a) @ m['n']) / den
            lo, hi = min(s0, s1), max(s0, s1)
            if (min(hi, 1) - max(lo, 0)) * g['L'] <= FLUSH: continue      # 桁が板・柱に入らない（面に触れるだけを含む）
            sm = (s0 + s1) / 2; X = a + sm * t
            q = np.array([(X - m['O']) @ m['X'], (X - m['O']) @ m['Y']])
            if not m['outer'].buffer(1.0).contains(Point(q)): continue
            hole = None
            for k, (hp, hc) in enumerate(m['holes']):
                if hp.buffer(1.0).contains(Point(q)): hole = (k, float(np.hypot(*(q - hc))))
            ee = FLUSH / g['L']
            part = lo < -ee or hi > 1 + ee               # 桁の端が厚みの中（向こうの面で止まる＝面一は通ったと見る）
            if hole is None:
                solid.append((g, m)); continue
            k, off = hole
            hits[id(m)].setdefault(k, []).append((off, g, part))
            if not part: g['through'] += 1
            for e, s in ((0, 0.0), (1, 1.0)):
                # short：桁の端から、板・柱の向こうの面までの長さ（mm）
                if lo + ee < s < hi - ee: ends.append(dict(g=g, e=e, m=m, hole=k, short=(hi - 1 if e else -lo) * g['L']))
    # 桁の端：厚みの中で止まる→ほかの桁の端と 10 以内で会い、柱の穴の中なら折れ
    P_end = [(g, e, g['a'] if e == 0 else g['b']) for g in G for e in (0, 1)]
    inside = {(id(x['g']), x['e']): x for x in ends}
    bend_out = []
    for g, e, p in P_end:
        mates = [(h, f) for h, f, q in P_end if h is not g and np.linalg.norm(q - p) <= TOL]
        x = inside.get((id(g), e))
        if x is not None:
            if not (mates and x['m']['kind'] == 'post'):
                stops.append((g, e, x['m'], x['short']))
        elif mates and id(g) < min(id(h) for h, f in mates):
            bend_out.append((g, e))
    # 部材ごと
    rows = []
    for m in M:
        H = hits[id(m)]
        hs = []
        for k, (hp, hc) in enumerate(m['holes']):
            L = H.get(k, [])
            st = 'ok' if L and round(min(o for o, _, _ in L), 1) <= TOL else 'ずれ' if L else '穴だけ'
            hs.append(dict(k=k, c=hc, st=st, off=round(min(o for o, _, _ in L), 1) if L else None))
        q = m['q']
        if m['kind'] == 'post':
            zax = np.array([m['X'][2], m['Y'][2]])      # 輪郭の面の中の上向き
            if np.linalg.norm(zax) < 0.5:
                ends_need = {'頭': []}                   # 輪郭が平面（鉛直の押し出し）：横の穴は作れない
            else:
                zax /= np.linalg.norm(zax); h = q @ zax; lo, hi = h.min(), h.max()
                ends_need = {'頭': [x for x in hs if x['c'] @ zax >= hi - (hi - lo) / 3]}
        else:
            hax = np.array([m['X'] @ np.array([1, 0, 0]), 0.0])
            # 輪郭の面の中の水平の向き：X・Y のうち水平に近い方を、面の中で鉛直を除いて作る
            up = np.array([m['X'][2], m['Y'][2]])
            hax = np.array([-up[1], up[0]]) if np.linalg.norm(up) > 0.5 else np.array([1.0, 0])
            hax /= np.linalg.norm(hax); h = q @ hax; lo, hi = h.min(), h.max(); L3 = (hi - lo) / 3
            ends_need = {'端A': [x for x in hs if x['c'] @ hax <= lo + L3], '端B': [x for x in hs if x['c'] @ hax >= hi - L3]}
            if CANT.search(m['name']):
                ends_need = {'元': [x for x in hs if x['c'] @ hax <= lo + L3 or x['c'] @ hax >= hi - L3]}
        res = {}
        for en, L in ends_need.items():
            if not L: res[en] = '穴なし'
            elif any(x['st'] == 'ok' for x in L): res[en] = 'ok'
            elif any(x['st'] == 'ずれ' for x in L): res[en] = 'ずれ%.1f' % min(x['off'] for x in L if x['off'] is not None)
            else: res[en] = '穴だけ'
        rows.append(dict(bld=m['bld'], kind=m['kind'], layer=m['layer'], name=m['name'], id=m['id'], u=m['u'], v=m['v'], z=m['z'],
                         ends=res, holes=len(hs)))
    for d in other:
        rows.append(dict(bld=d['bld'], kind=d['kind'], layer=d['layer'], name=d['name'], id=d['id'], u=d['u'], v=d['v'], z=d['z'],
                         ends={'形': '押し出しでない'}, holes=0))
    # 架構（ユーザー 11-01）：Tamedia は構造の架構だけ＝柱（11a・22a）と梁（11b・22b・22c、板二枚で一本）。
    # 階段の箱の柱・骨格の柱（床梁の下の 180×400）は架構でない。西館：柱 22・梁 17（屋根の梁 12＝22b の枠ごと＋43.5、2 階の床梁 5＝22c の枠ごと）
    FR_SKIP = re.compile(r'階段の箱|骨格の柱')
    frows = [x for x in rows if not (x['kind'] == 'post' and FR_SKIP.search(x['name'])) and x['kind'] in ('post', 'ply')]
    fid = {x['id'] for x in frows}
    units = [dict(bld=x['bld'], kind='post', ms=[x]) for x in frows if x['kind'] == 'post']
    for lay in sorted({x['layer'] for x in frows if x['kind'] == 'ply'}):
        P = [x for x in frows if x['kind'] == 'ply' and x['layer'] == lay]
        pr = sorted(((np.hypot(a['u'] - b['u'], a['v'] - b['v']), i, j) for i, a in enumerate(P) for j, b in enumerate(P)
                     if i < j and abs(a['z'] - b['z']) < 300 and np.hypot(a['u'] - b['u'], a['v'] - b['v']) < 0.6), key=lambda t: t[0])
        used = set()
        for dd, i, j in pr:
            if i in used or j in used: continue
            used |= {i, j}; units.append(dict(bld=P[i]['bld'], kind='beam', ms=[P[i], P[j]]))
        units += [dict(bld=P[i]['bld'], kind='beam', ms=[P[i]]) for i in range(len(P)) if i not in used]
    for un in units:
        un['ok'] = all(v == 'ok' for m in un['ms'] for v in m['ends'].values())
        un['nohole'] = any(v in ('穴なし', '穴だけ') for m in un['ms'] for v in m['ends'].values())
        un['off'] = any(v.startswith('ずれ') for m in un['ms'] for v in m['ends'].values())
        un['x'] = un['ms'][0]
    for k in ('stops', 'solid'):
        pass
    loc = lambda d: f"u{d['u']:.2f} v{d['v']:.2f} z{d['z']:.0f}"
    gloc = lambda g, e: (lambda p: f"u{uv(p[0], p[1])[0]:.2f} v{uv(p[0], p[1])[1]:.2f} z{p[2]:.0f}")(g['a'] if e == 0 else g['b'])
    out = dict(members=rows,
               stops=[dict(bld=g['bld'], mid=m['id'], at=gloc(g, e), text=f"桁{g['layer']}（{g['id']}）の端が{m['layer']}（{m['id']}{('、' + m['name'][:20]) if m['name'] else ''}）の中で止まる（向こうの面まで{sh:.0f} mm）") for g, e, m, sh in stops],
               bend_out=[dict(bld=g['bld'], at=gloc(g, e), text=f"桁{g['layer']}（{g['id']}）の端がほかの桁と会うが、柱の穴の中でない") for g, e in bend_out],
               solid=[dict(bld=m['bld'], mid=m['id'], at=loc(m), text=f"桁{g['layer']}（{g['id']}、{loc(g)}）の芯が{m['layer']}（{m['id']}{('、' + m['name'][:20]) if m['name'] else ''}）を穴の無い所で通る") for g, m in solid],
               idle=[dict(bld=g['bld'], at=loc(g), text=f"桁{g['layer']}（{g['id']}{('、' + g['name'][:20]) if g['name'] else ''}）") for g in G if g['through'] == 0])
    # 数（架構の部材＝柱・梁一本ごと。梁は板二枚で一本）
    S = {}
    fs = lambda key, b: sum(1 for x in out[key] if x['bld'] == b and (key not in ('stops', 'solid') or x['mid'] in fid))
    out['stops'] = [x for x in out['stops'] if x['mid'] in fid]; out['solid'] = [x for x in out['solid'] if x['mid'] in fid]
    for b in ('本館', '西館'):
        R = [u for u in units if u['bld'] == b]
        S[b] = dict(members=len(R), posts=sum(u['kind'] == 'post' for u in R), beams=sum(u['kind'] == 'beam' for u in R),
                    ok=sum(u['ok'] for u in R), nohole=sum(u['nohole'] for u in R), off=sum(u['off'] and not u['nohole'] for u in R),
                    stops=fs('stops', b), bend_out=fs('bend_out', b), solid=fs('solid', b), idle=fs('idle', b),
                    girders=sum(1 for g in G if g['bld'] == b))
    rows = frows; out['members'] = frows
    out['summary'] = S
    out['n_none'] = sum(S[b]['nohole'] for b in S); out['n_off'] = sum(S[b]['off'] for b in S)
    out['n_stop'] = sum(S[b]['stops'] + S[b]['bend_out'] + S[b]['solid'] for b in S)
    # 文
    sm = lambda b: (f"{b}：柱{S[b]['posts']}梁{S[b]['beams']}で留まる{S[b]['ok']}・無い{S[b]['nohole']}・ずれ{S[b]['off']}・止まる{S[b]['stops']}"
                    f"・折れが外{S[b]['bend_out']}・材を貫く{S[b]['solid']}・何も通らない桁{S[b]['idle']}（桁{S[b]['girders']}）")
    T = [f"Tamediaの留め：{sm('本館')}、{sm('西館')}　（{time.time() - T0:.1f}秒。知らせだけ、止めない）"]
    KN = {'post': '柱', 'ply': '梁の板', 'girder': '桁'}
    bad = [x for x in rows if not all(v == 'ok' for v in x['ends'].values())]
    if bad:
        T.append('  留まらない柱・梁の板（u, v, z・層・名前・端ごと）：')
        for x in sorted(bad, key=lambda x: (x['bld'], x['layer'], x['u'], x['v'], x['z'])):
            T.append(f"    {x['bld']}の{KN[x['kind']]} u{x['u']:.2f} v{x['v']:.2f} z{x['z']:.0f}\t{x['layer']}\t{x['name'][:30] or '-'}\t"
                     + '・'.join(f'{k}：{v}' for k, v in x['ends'].items()) + f"（穴{x['holes']}、{x['id']}）")
    for key, title in (('stops', '桁が板・柱の厚みの中で止まる'), ('bend_out', '桁の折れが柱の穴の外'), ('solid', '桁の芯が穴の無い所で板・柱を通る'),
                       ('idle', 'どの穴も通らない桁')):
        if out[key]:
            T.append(f'  {title}：')
            for x in out[key]:
                T.append(f"    {x['bld']} {x['at']}\t{x['text']}")
    out['text'] = '\n'.join(T)
    return out


if __name__ == '__main__':
    res = run(sys.argv[1])
    txt = res.pop('text')
    json.dump(res, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    print(txt.split('\n')[0])
    if len(sys.argv) > 3: open(sys.argv[3], 'w').write(txt + '\n')
