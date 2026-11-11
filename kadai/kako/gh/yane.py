# -*- coding: utf-8 -*-
#! python 3
VERSION = 'yane 2026-11-11 14:48'     # 版（直すたびに、そのときの時刻に）。log の1行目にも出る
"""
屋根（Rhino 8 Mac、Grasshopper の Python 3 スクリプト部品）。

屋根の面（梁の上端の面）を、案の名前と高さから作る。出力 roof を「架構」部品の roof につなぐ。
架構は本館の背骨の円の中心からの放射の線（kakou.py と同じ：架構kは u＝3(k−1) m、u は v＝0 の円弧の上で測る）。

架構の線ごとに、東の縁（v−0.9 の円弧）から軒先の線（eave）までの直線を引き、その両端の高さを案で決め、
直線を順に「直線でつなぐ」Loft で面にする。南北の端の架構の外へも gable だけ延ばす（端の梁の外の1本を覆う）。

案（kettei.md「A案・B案・C案」）：
  A：東の縁と軒をどれも水平（東 zE、軒 zW）。勾配は架構ごとに違い、架構のあいだは双一次（ねじれた）面。
  B：南西の辺（西の直線の軒）にかかる架構は A と同じく軒の高さ zW。それより北は、その境の架構の勾配のまま一定。
     境の架構 kB は入力で決めるか、無ければ軒の線の向きが k の最小の架構から3°以上変わる手前の架構。
  C：どこも勾配一定（円錐の面）。架構のあいだは平らな面（合板がねじれない）。勾配は入力 slope（°）、
     無ければ kRef の架構で A と同じ勾配。

入力  k（架構の番号、List）・eave（軒先の線＝屋根の面の縁、平面の曲線、Item）
      plan（'A'・'B'・'C'、Item、既定 'A'）
      zE（東の縁の梁の上端、8150）・zW（軒の梁の上端、4650）・vE（東の縁の v、m、0.9）
      kB（B案の境の架構）・slope（C案の勾配、°）・kRef（C案の勾配を取る架構、15）・gable（南北の端の外へ、mm、1000）
出力  roof（屋根の面、Brep）・lines（架構ごとの直線）・table（架構ごとの数、CSV の文字）・log
"""
import math

PITCH = 3000.0
CX, CY, RW = 194662.93237, -41348.26335, 205017.7
TH_S = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)
DEF = dict(zE=8150.0, zW=4650.0, vE=0.9, kRef=15.0, gable=1000.0)
TURN_DEG = 3.0        # B案の境：軒の線の向きが、最初の架構からこれ以上変わったら南西の辺の外


# ================================================================== 核（Rhino を使わない）
def theta(k):
    """架構kの向き（本館の背骨の円の中心から、u は v＝0 の円弧の上で測る）"""
    return TH_S - PITCH * (k - 1.0) / RW


def plan_heights(plan, fr, zE, zW, kRef=15.0, kB=None, slope=None):
    """架構ごとの両端の高さ。fr：k の小さい順の [dict(k, L, turn)]（L：東の縁から軒までの長さ mm、turn：軒の線の向きの
    最初の架構からの変化 °）。返す：[(zE_k, zW_k)] と、決めたこと（文字）"""
    note = ''
    if plan == 'A':
        return [(zE, zW) for _ in fr], 'A：東%.0f・軒%.0f（どれも水平）' % (zE, zW)
    if plan == 'C':
        if slope is not None:
            i = math.tan(math.radians(slope))
            note = '勾配%.2f°（入力）' % slope
        else:
            ref = min(fr, key=lambda f: abs(f['k'] - kRef))
            i = (zE - zW) / ref['L']
            note = '勾配%.2f°（k%g で A と同じ）' % (math.degrees(math.atan(i)), ref['k'])
        return [(zE, zE - i * f['L']) for f in fr], 'C：東%.0f・' % zE + note
    if plan == 'B':
        if kB is None:
            kB = fr[0]['k']
            for f in fr:                   # 南から、軒の線の向きが変わる手前まで
                if abs(f['turn']) < TURN_DEG:
                    kB = f['k']
                else:
                    break
            note = '（軒の線の向きから）'
        else:
            note = '（入力）'
        fb = min(fr, key=lambda f: abs(f['k'] - kB))
        i = (zE - zW) / fb['L']
        out = [(zE, zW) if f['k'] <= fb['k'] + 1e-9 else (zE, zE - i * f['L']) for f in fr]
        return out, 'B：k%g までは軒%.0f、その北は勾配%.2f°一定%s' % (fb['k'], zW, math.degrees(math.atan(i)), note)
    raise ValueError('plan は A・B・C のどれか：%r' % plan)


# ================================================================== Rhino
try:
    import Rhino.Geometry as rg
    from Rhino.Geometry.Intersect import Intersection as _X
    _RHINO = True
except ImportError:
    _RHINO = False


def _in(name, default=None):
    v = globals().get(name)
    if v is None:
        return default
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return default
    return v


def _raw(x):
    for _ in range(3):
        if hasattr(x, 'Value') and not isinstance(x, (str, int, float)):
            try:
                x = x.Value
                continue
            except Exception:
                pass
        break
    return x


def _f(x):
    x = _raw(x)
    try:
        return float(x)
    except Exception:
        return float(str(x).strip())


def _nums(v):
    if v is None:
        return []
    if isinstance(_raw(v), str):
        v = [_raw(v)]
    try:
        items = [_raw(x) for x in v]
    except TypeError:
        items = [_raw(v)]
    out = []
    for x in items:
        if isinstance(x, str):
            out += [float(q) for q in x.replace(',', ' ').replace(';', ' ').split()]
        else:
            out.append(_f(x))
    return out


def _num(name):
    v = _in(name)
    return _f(v) if v is not None else DEF[name]


def _eave_hit(eave, th, rE):
    """架構の向き th の線（東の縁 rE から外へ）と軒の線の交わる所：(長さ L、点、交わる所の軒の線の向き)"""
    c, s = math.cos(th), math.sin(th)
    E = rg.Point3d(CX + rE * c, CY + rE * s, 0)
    F = rg.Point3d(CX + (rE + 40000) * c, CY + (rE + 40000) * s, 0)
    ev = _X.CurveCurve(rg.LineCurve(E, F), eave, 0.1, 0.1)
    best = None
    for x in ev or []:
        L = E.DistanceTo(x.PointA)
        if L > 1000 and (best is None or L < best[0]):
            tg = eave.TangentAt(x.ParameterB)
            best = (L, x.PointA, math.degrees(math.atan2(tg.Y, tg.X)))
    return E, best


def run():
    ks = sorted(_nums(_in('k')))
    eave = _in('eave')
    if not ks or eave is None:
        return None, '入力 k（架構の番号）と eave（軒先の線）が要る'
    plan = str(_raw(_in('plan', 'A'))).strip().upper()
    zE, zW, vE, kRef, gable = (_num(n) for n in ('zE', 'zW', 'vE', 'kRef', 'gable'))
    kB = _in('kB')
    kB = _f(kB) if kB is not None else None
    slope = _in('slope')
    slope = _f(slope) if slope is not None else None
    rE = RW + vE * 1000.0
    flat = rg.Curve.ProjectToPlane(_raw(eave), rg.Plane.WorldXY)
    ext = flat.Extend(rg.CurveEnd.Both, 20000.0, rg.CurveExtensionStyle.Line)
    if ext is not None:
        flat = ext
    log = []
    # 架構の線（南北の端の外に、gable だけ離れた線を1本ずつ足す）
    dk = gable / PITCH * (RW / rE)          # 東の縁で gable 離れる k の差
    kk = [ks[0] - dk] + ks + [ks[-1] + dk]
    fr = []
    turn0 = None
    for k_ in kk:
        E, hit = _eave_hit(flat, theta(k_), rE)
        if hit is None:
            return None, 'k%.2f：架構の線が軒先の線と交わらない' % k_
        L, W, ang = hit
        if turn0 is None and k_ >= ks[0]:
            turn0 = ang
        fr.append(dict(k=k_, L=L, E=E, W=W, ang=ang))
    for f in fr:
        d = (f['ang'] - (turn0 if turn0 is not None else f['ang']) + 90) % 180 - 90
        f['turn'] = d
    hs, note = plan_heights(plan, fr, zE, zW, kRef, kB, slope)
    log.append(note)
    lines = []
    rows = ['k,L,zE,zW,slope_deg,eave_turn_deg']
    for f, (a, b) in zip(fr, hs):
        lines.append(rg.LineCurve(rg.Point3d(f['E'].X, f['E'].Y, a), rg.Point3d(f['W'].X, f['W'].Y, b)))
        rows.append('%.3f,%.0f,%.0f,%.0f,%.3f,%.2f' % (f['k'], f['L'], a, b, math.degrees(math.atan((a - b) / f['L'])), f['turn']))
    lofts = rg.Brep.CreateFromLoft(lines, rg.Point3d.Unset, rg.Point3d.Unset, rg.LoftType.Straight, False)
    if not lofts or len(lofts) != 1:
        return None, 'Loft ができない（%d）' % (len(lofts) if lofts else 0)
    roof = lofts[0]
    zs = [b for a, b in hs[1:-1]]
    log.append('軒の梁の上端：%.0f〜%.0f（架構 k%g〜k%g）。南北の端の外へ %.0f' % (min(zs), max(zs), ks[0], ks[-1], gable))
    return dict(roof=roof, lines=lines, table='\n'.join(rows)), '\n'.join(log)


globals().update(locals())
log = VERSION + '\n部品は動いたが、入力 k が見えない'
if _RHINO and 'k' in globals():
    _res, _log = run()
    log = VERSION + '\n' + _log
    if _res:
        roof, lines, table = _res['roof'], _res['lines'], _res['table']
