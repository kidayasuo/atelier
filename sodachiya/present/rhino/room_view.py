# -*- coding: utf-8 -*-
"""教室・居場所の切断のレンダリングの準備：ビューを合わせ、屋根などを隠し、クリッピング平面で切る（プレゼンの準備、10-30）

2枚目「ゾーニングと動線・環境」の教室3つと居場所2つを Rhino でレンダリングするため（present/tools/rooms3d.py の軸測図と同じ見え方）。
使い方（Rhino 8、Mac）：
  1. atelier を pull して sodachiya/sodachiya.3dm を開き、Perspective のビューをクリックしてアクティブにする。
  2. RunPythonScript でこのファイルを選び、部屋を一つ選ぶ（room_3to5＝4歳／room_01＝0・1歳／room_2＝2歳／
     room_dokusho＝絵本の通りと本の奥／room_hako＝遊戯室の西の壁のひだ）。切り方も聞かれる：
     ・クリッピング平面（ふつう）：部屋の四方を垂直の面で、上を水平の面（床から2.4 m）で切る。手前（南、読書は東も）の面は
       壁より内側に置き、手前の壁を取り去って中を見せる。本館の柱・梁・桁は、水平の面では切らない（Rhino 8 のクリッピングの
       参加の設定。効かなければ梁も2.4 mで切れる、コマンド行に出る）。
     ・壁のレイヤーを隠す（クリッピング平面がレンダリングに出ないとき）：壁・間仕切り・建具・ガラスのレイヤーを隠す。隣の部屋は残る。
     どちらでも、屋根・越屋根・母屋・垂木・光の筋のガラスと鏡・2階の床と部屋・午睡のコット・天井扇のレイヤーを隠す。
     ビューは南東の上から覗き込む透視（レンズ50 mm、配置図と同じ向き＝紙の下の高野川の側から、見下ろす角40°）になり、
     同じ名前の名前付きビューもできる。
  3. render_hiru.py（夜なら render_yoru.py）を走らせ、同じ名前（room_…）と大きさ「1600×1200」を選ぶ → out/<名前>_hiru.png。
  4. 終わったら、もう一度このファイルを走らせて「元に戻す」を選ぶ（隠したレイヤーを表示に戻し、sdy_clip_ のクリッピング平面を消す）。
     3dm は保存しなくてよい。絵ができたら push：git add sodachiya/present/rhino/out && git commit -m "[プレゼン] 部屋のレンダリング" && git push
  ・全部消えた／切る側が逆のとき：「クリッピング平面の向きを逆に」を選んでから、もう一度部屋を選ぶ。
"""
import os
import io
import json
import math
import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

G = Rhino.Geometry
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
OUT = os.path.join(HERE, "out")
STATE = os.path.join(OUT, "room_view_state.json")     # 隠したレイヤー・参加を変えた物・向きの記録（元に戻すため）

# ---------------------------------------------------------------- 本館の (u, v)（model/build/south/uv.py と同じ定数、mm）
CX, CY, RW = 194662.93237, -41348.26335, 205017.7
TH_S = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)


def xy(u, v):
    th = TH_S - u * 1000.0 / RW
    r = RW - v * 1000.0
    return (CX + r * math.cos(th), CY + r * math.sin(th))


# ---------------------------------------------------------------- 部屋（u, v は m。near：手前で壁ごと切り取る辺 S＝南 u0、E＝東 v1）
ROOMS = [
    (u"room_3to5", u"room_3to5＝4歳の保育室（巣A・巣B・共有・腰の壁・ロフト・天蓋）", (42.0, 48.0), (1.6, 12.0), u"S"),
    (u"room_01", u"room_01＝0・1歳の保育室", (0.0, 12.0), (1.6, 12.0), u"S"),
    (u"room_2", u"room_2＝2歳の保育室", (11.6, 18.0), (1.6, 12.0), u"S"),
    (u"room_dokusho", u"room_dokusho＝絵本の通りと本の奥", (45.0, 57.34), (-0.4, 1.6), u"SE"),
    (u"room_hako", u"room_hako＝遊戯室の西の壁のひだ（箱）", (33.3, 44.6), (-15.4, -11.0), u""),
]
CUT = 2400.0            # 水平の切断（床から mm）
OUT_PAD = 300.0         # 奥の辺は壁の外まで含める（mm）
IN_PAD = 120.0          # 手前の辺は壁より内側に置いて壁を取り去る（mm）
LENS = 50.0
EL = 40.0               # 見下ろす角（度）
VIEW_ROT = -38.5        # 配置図の向き（data/garden.json の VIEW_ROT）
CLIP_PREFIX = u"sdy_clip_"

# 隠すレイヤー（レイヤーの名前の頭。親レイヤーを除いた名前で見る）
HIDE = (u"10_", u"10b_", u"10k_", u"10m_", u"10p_", u"10r_", u"10s_", u"10t_", u"10v_",          # 本館の屋根・母屋・垂木・光の筋のガラスと鏡
        u"20_", u"20b_", u"20m_", u"20p_", u"20r_", u"20t_", u"20v_", u"22t_",                  # 西館の屋根
        u"50", u"26_", u"28_", u"29_", u"30_",                                                   # 越屋根・室外機
        u"23_", u"41_", u"42_", u"43_", u"43b_", u"44_", u"45_",                                 # 2階の床と部屋
        u"47_", u"58_", u"58b_", u"88_")                                                         # 午睡のコット・天井扇
HIDE_WALLS = (u"16", u"17", u"18_", u"19", u"21_", u"24_", u"27", u"38_", u"48_")               # 「壁のレイヤーを隠す」で足す
KEEP_UNCUT = (u"11a_", u"11b_", u"11c_")                                                        # 水平の面で切らない（本館の架構）


def say(*a):
    Rhino.RhinoApp.WriteLine(u" ".join(u"%s" % x for x in a))


def load_state():
    try:
        with io.open(STATE, "r", encoding="utf-8-sig") as f_:
            t_ = f_.read().strip()
        return json.loads(t_) if t_ else {}
    except Exception:
        return {}


def save_state(st):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with io.open(STATE, "w", encoding="utf-8") as f_:
        f_.write(u"%s" % json.dumps(st, indent=1, ensure_ascii=True))


def short(name):
    return name.split(u"::")[-1]


def restore(doc, st):
    """隠したレイヤーを戻し、クリッピングの参加を戻し、sdy_clip_ の平面を消す"""
    n = 0
    for lid in st.get("hidden_layers", []):
        try:
            k = doc.Layers.FindId(System.Guid(lid))
            if k is not None and not k.IsVisible:
                k.IsVisible = True
                k.CommitChanges()
                n += 1
        except Exception as e:
            say(u"  レイヤーを戻せなかった：", lid, e)
    m = 0
    for oid in st.get("clip_objects", []):
        try:
            o = doc.Objects.FindId(System.Guid(oid))
            if o is None:
                continue
            a = o.Attributes.Duplicate()
            a.SetClipParticipationForAll()
            doc.Objects.ModifyAttributes(o, a, True)
            m += 1
        except Exception:
            pass
    c = 0
    for o in list(doc.Objects.GetObjectList(Rhino.DocObjects.ObjectType.ClipPlane)):
        if (o.Attributes.Name or u"").startswith(CLIP_PREFIX):
            doc.Objects.Delete(o, True)
            c += 1
    st["hidden_layers"], st["clip_objects"] = [], []
    say(u"元に戻した：レイヤー", n, u"／参加を戻した物", m, u"／消したクリッピング平面", c)
    return st


def hide_layers(doc, prefixes, st):
    cur = doc.Layers.CurrentLayer
    hid = list(st.get("hidden_layers", []))
    names = []
    for l in doc.Layers:
        if l.IsDeleted or not l.IsVisible:
            continue
        if not short(l.Name).startswith(prefixes):
            continue
        if cur is not None and l.Id == cur.Id:
            say(u"  今のレイヤーなので隠せない：", l.FullPath)
            continue
        l.IsVisible = False
        l.CommitChanges()
        hid.append(str(l.Id))
        names.append(short(l.Name))
    st["hidden_layers"] = hid
    say(u"隠したレイヤー：", len(names), u"（" + u"・".join(names[:12]) + (u"…" if len(names) > 12 else u"") + u"）")
    return st


def set_view(vp, U, V):
    """南東の上から覗き込む透視。部屋が絵（4:3）に入る距離に"""
    c = [xy(u, v) for u in U for v in V]
    tx = sum(p[0] for p in c) / 4.0
    ty = sum(p[1] for p in c) / 4.0
    tgt = G.Point3d(tx, ty, 800.0)
    r_ = math.radians(VIEW_ROT)
    dx, dy = math.sin(-r_), -math.cos(r_)              # 紙の下（高野川の側）の向き
    e_ = math.radians(EL)
    d_ = G.Vector3d(dx * math.cos(e_), dy * math.cos(e_), math.sin(e_))
    d_.Unitize()
    right = G.Vector3d.CrossProduct(-d_, G.Vector3d(0, 0, 1))
    right.Unitize()
    up = G.Vector3d.CrossProduct(right, -d_)
    up.Unitize()
    th = 18.0 / LENS * 0.9                              # 横の半分の画角の tan（35 mm 換算、少し余白）
    tv = th * 0.75                                      # 4:3
    need = 0.0
    for (px, py) in c:
        for z in (0.0, 3500.0):
            p = G.Vector3d(px - tgt.X, py - tgt.Y, z - tgt.Z)
            x, y, w = p * right, p * up, p * d_
            need = max(need, w + abs(x) / th, w + abs(y) / tv)
    cam = tgt + d_ * need
    vp.ChangeToPerspectiveProjection(True, LENS)
    vp.SetCameraLocations(tgt, cam)
    try:
        vp.CameraUp = up
    except Exception:
        pass
    try:
        vp.Camera35mmLensLength = LENS
    except Exception:
        pass
    return tgt, cam


def add_clips(doc, vp, name, U, V, near, flip):
    """四方の垂直の面（内向き）と上の水平の面。法線の側が見える（と見込む。逆なら flip）"""
    s = -1.0 if flip else 1.0
    u0, u1 = U
    v0, v1 = V
    um, vm = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    ids = List_of_guid()
    ids.Add(vp.Id)
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.Name = CLIP_PREFIX + name
    made = []

    def vplane(ua, va, ub, vb, inward_u, inward_v):
        pa, pb = xy(ua, va), xy(ub, vb)
        o_ = G.Point3d((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, 1500.0)
        t_ = G.Vector3d(pb[0] - pa[0], pb[1] - pa[1], 0)
        L_ = t_.Length
        t_.Unitize()
        pi_ = xy(inward_u, inward_v)
        n_ = G.Vector3d(pi_[0] - o_.X, pi_[1] - o_.Y, 0)
        n_ = n_ - t_ * (n_ * t_)
        n_.Unitize()
        pl = G.Plane(o_, n_ * s)
        made.append(doc.Objects.AddClippingPlane(pl, L_ / 2.0 + 2000.0, 6000.0, ids, attr))

    pad_o, pad_i = OUT_PAD / 1000.0, IN_PAD / 1000.0
    us = u0 + pad_i if u"S" in near else u0 - pad_o
    un = u1 + pad_o
    ve = v1 - pad_i if u"E" in near else v1 + pad_o
    vw = v0 - pad_o
    vplane(us, vw, us, ve, um, vm)        # 南
    vplane(un, vw, un, ve, um, vm)        # 北
    vplane(us, vw, un, vw, um, vm)        # 西
    vplane(us, ve, un, ve, um, vm)        # 東
    c = xy(um, vm)
    pl = G.Plane(G.Point3d(c[0], c[1], CUT), G.Vector3d(0, 0, -1.0 * s))
    top = doc.Objects.AddClippingPlane(pl, 20000.0, 20000.0, ids, attr)
    made.append(top)
    return [m for m in made if m != System.Guid.Empty], top


def List_of_guid():
    from System.Collections.Generic import List
    return List[System.Guid]()


def keep_frames(doc, clips, top, st):
    """本館の柱・梁・桁は水平の面に参加させない（四方の面には参加）。Rhino 8 の参加の設定"""
    side = List_of_guid()
    for g in clips:
        if g != top:
            side.Add(g)
    done = list(st.get("clip_objects", []))
    n = 0
    try:
        for l in doc.Layers:
            if l.IsDeleted or not short(l.Name).startswith(KEEP_UNCUT):
                continue
            for o in doc.Objects.FindByLayer(l) or []:
                a = o.Attributes.Duplicate()
                a.SetClipParticipationList(side, True)
                doc.Objects.ModifyAttributes(o, a, True)
                done.append(str(o.Id))
                n += 1
        say(u"本館の架構（柱・梁・桁）", n, u"本を、上の水平の面では切らないようにした")
    except Exception as e:
        say(u"  架構を切らない設定が効かなかった（梁も2.4 mで切れる）：", e)
    st["clip_objects"] = done
    return st


def main():
    doc = sc.doc
    st = load_state()
    labels = [l for _, l, _, _, _ in ROOMS] + [u"元に戻す（隠したレイヤーを戻し、クリッピング平面を消す）",
                                                u"クリッピング平面の向きを逆に（今：%s）" % (u"逆" if st.get("flip") else u"ふつう")]
    got = rs.ListBox(labels, u"部屋を選ぶ", u"部屋の切断")
    if got is None:
        return
    if got.startswith(u"元に戻す"):
        save_state(restore(doc, st))
        doc.Views.Redraw()
        return
    if got.startswith(u"クリッピング平面の向き"):
        st["flip"] = not st.get("flip", False)
        save_state(st)
        say(u"クリッピング平面の向き：", u"逆" if st["flip"] else u"ふつう", u"（もう一度部屋を選ぶ）")
        return
    name, _, U, V, near = [r_ for r_ in ROOMS if r_[1] == got][0]
    how = rs.ListBox([u"クリッピング平面で切る（ふつう）", u"壁のレイヤーを隠す（クリッピング平面がレンダリングに出ないとき）"],
                     u"切り方", u"部屋の切断", u"クリッピング平面で切る（ふつう）")
    if how is None:
        return
    st = restore(doc, st)                               # 前の部屋の分は戻してから
    view = doc.Views.ActiveView
    vp = view.ActiveViewport
    tgt, cam = set_view(vp, U, V)
    prefixes = HIDE + (HIDE_WALLS if how.startswith(u"壁") else ())
    st = hide_layers(doc, prefixes, st)
    if how.startswith(u"クリッピング"):
        clips, top = add_clips(doc, vp, name, U, V, near, st.get("flip", False))
        say(u"クリッピング平面：", len(clips), u"枚（", CLIP_PREFIX + name, u"、上は床から", int(CUT), u"mm）")
        st = keep_frames(doc, clips, top, st)
    st["room"] = name
    save_state(st)
    view.Redraw()
    try:
        k = doc.NamedViews.FindByName(name)
        if k >= 0:
            doc.NamedViews.Delete(k)
        doc.NamedViews.Add(name, vp.Id)
    except Exception as e:
        say(u"  名前付きビューを作れなかった：", e)
    say(u"ビュー：", name, u"／透視 レンズ", int(LENS), u"mm、南東の上から", int(EL), u"°／カメラ",
        [int(cam.X), int(cam.Y), int(cam.Z)], u"ターゲット", [int(tgt.X), int(tgt.Y), int(tgt.Z)])
    say(u"次に render_hiru.py を走らせ、名前", name, u"・大きさ 1600×1200 を選ぶ。終わったらこのファイルで「元に戻す」")


main()
