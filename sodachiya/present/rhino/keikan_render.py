# -*- coding: utf-8 -*-
"""育ち舎　沿川の景観立面（昼・夜）を Rhino のレイトレースで書き出す（プレゼンの準備、10-27）

使い方（Rhino 8、Mac）：
  1. atelier を pull して、sodachiya/sodachiya.3dm を開く。
  2. ツール → スクリプト → 実行…（または コマンド RunPythonScript）で、このファイルを選ぶ。
  3. いまのビューが一時的に景観立面の向きになり、レンダリング（Render）で昼・夜の2枚を書き出す（1枚に数分）。
     画質（回数）は レンダリングの設定 → 「レンダリング」の最大回数で決まる。
     書き出し先：このファイルの隣の out/keikan_hiru.png・out/keikan_yoru.png（と、写った範囲の keikan_view.json）。
  4. 走り終わると、足した物・変えた設定は元に戻る（3dm は保存しなくてよい）。
  5. out/ の3つを push する（git add sodachiya/present/rhino/out）。mock.py が素材03・04にこの絵を使う。
     絵が無いあいだは今までの影絵のまま。

見る向き：高野川の向こうから、敷地の川の辺（S→E）に直角に（mock.py の「沿川の景観立面」と同じ）。
平行投影、1/300 で 360×85 mm（横 108 m × 高さ 25.5 m）、背景は透明（空と川の色は mock.py が塗る）。
昼：11/5 10:00 の太陽（京都）。夜：太陽を消し、越屋根の LED（50b）だけを光らせる。
数字を変えたいときは下の「決める数」だけを直す。
"""
import os, json, datetime
import Rhino
import scriptcontext as sc
import System

# ---------------------------------------------------------------- 決める数
S_MM = (-14440.0, -83040.0)            # 敷地の南の角（3dm、mm）
T_DIR = (0.78264675, 0.62246611)       # 川から見て右（北東）へ
D_DIR = (-0.62246611, 0.78264675)      # 奥（北西）へ＝見る向き
T0, T1, Z0, Z1 = -22000.0, 86000.0, -6500.0, 19000.0   # 写す範囲（S から t、高さ z、mm）
PX_PER_MM = 300 / 25.4                  # 紙の 300 dpi
SCALE = 300
PASSES = 400                            # レイトレースの回数（多いほどざらつきが減る）
DAY = datetime.datetime(2026, 11, 5, 10, 0)
LAT, LON, TZ = 35.049106, 135.785095, 9.0
LED_LAYERS = ("50b_越屋根_LED", "29_西館_越屋根_LED")   # 本館・西館の越屋根
NIGHT = datetime.datetime(2026, 11, 5, 21, 0)   # 夜は太陽を地平の下にも置く（消すのが効かない Rhino があった）
FRONT_CUT = -8000.0                     # 川の辺より手前（川の向こう岸の建物など）は隠す（mm、mock.py と同じ）
LED_COLOR = System.Drawing.Color.FromArgb(255, 217, 138)

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
OUT = os.path.join(HERE, "out")
if not os.path.isdir(OUT):
    os.makedirs(OUT)

doc = sc.doc


def P(t, d, z):
    return Rhino.Geometry.Point3d(S_MM[0] + T_DIR[0] * t + D_DIR[0] * d, S_MM[1] + T_DIR[1] * t + D_DIR[1] * d, z)


def raytraced():
    for m in Rhino.Display.DisplayModeDescription.GetDisplayModes():
        if m.EnglishName.lower().startswith("raytrac"):
            return m
    return None


# ---------------------------------------------------------------- ビュー（いま開いているビューを一時的に使う。終わったら元に戻す）
# 浮いたビューは Mac で書き出しが通らなかった（10-27）ので使わない。前に作った「景観立面」の浮いたビューがあれば閉じる
_old = doc.Views.Find("景観立面", False)
if _old is not None and _old.Floating:
    try:
        _old.Close()
    except Exception:
        pass
view = doc.Views.ActiveView
vp = view.ActiveViewport
saved_vi = Rhino.DocObjects.ViewportInfo(vp)
saved_mode = vp.DisplayMode
cw, ch = vp.Size.Width, vp.Size.Height
tc, zc = (T0 + T1) / 2, (Z0 + Z1) / 2
# 写す範囲（t0〜t1 × z0〜z1）がビューの縦横の比で全部入るように広げる（広げた分は json に書き、mock.py が切る）
half_w, half_h = (T1 - T0) / 2, (Z1 - Z0) / 2
if half_w / half_h > cw / float(ch):
    half_h = half_w * ch / float(cw)
else:
    half_w = half_h * cw / float(ch)
vp.ChangeToParallelProjection(True)
target = P(tc, 0, zc)
camera = P(tc, -400000.0, zc)
vp.SetCameraLocations(target, camera)
vp.CameraUp = Rhino.Geometry.Vector3d.ZAxis
vi = Rhino.DocObjects.ViewportInfo(vp)
vi.SetFrustum(-half_w, half_w, -half_h, half_h, 1000.0, 800000.0)
vp.SetViewProjection(vi, True)
mode = raytraced()
if mode:
    vp.DisplayMode = mode
else:
    print("Raytraced display mode not found")
view.Redraw()
W = int(round(2 * half_w / SCALE * PX_PER_MM))
H = int(round(W * ch / float(cw)))
if max(W, H) > 8000:                     # 大きすぎる絵は Rhino が書けない
    f_ = 8000.0 / max(W, H)
    W, H = int(W * f_), int(H * f_)
json.dump(dict(t0=tc - half_w, t1=tc + half_w, z0=zc - half_h, z1=zc + half_h, scale=SCALE, px=[W, H],
               made=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), note="t・z は mm（S から）。mock.py が読む"),
          open(os.path.join(OUT, "keikan_view.json"), "w"), indent=1)
try:
    doc.NamedViews.Add("景観立面", vp.Id)
except Exception:
    pass

# ---------------------------------------------------------------- 光
rs = doc.RenderSettings
sun = None
try:
    sun = rs.Sun
except Exception:
    try:
        sun = doc.Lights.Sun
    except Exception:
        pass
saved = {}
if sun is not None:
    for k in ("Enabled", "ManualControl", "Latitude", "Longitude", "TimeZone", "DaylightSaving"):
        try:
            saved[k] = getattr(sun, k)
        except Exception:
            pass


def set_sun(on, when=DAY):
    if sun is None:
        say(u"太陽の設定が見つからない（Rhino の版の違い）。太陽パネルで手で：11/5 10:00、京都")
        return
    try:
        sun.ManualControl = False
        sun.Latitude, sun.Longitude, sun.TimeZone = LAT, LON, TZ
        sun.DaylightSaving = False
        sun.SetDateTime(when, System.DateTimeKind.Local)
    except Exception as e:
        say(u"太陽の時刻：", e)
    sun.Enabled = on
    try:
        rs.Sun = sun
    except Exception:
        pass
    try:
        doc.RenderSettings = rs     # RenderSettings は写しなので、戻して効かせる
    except Exception:
        pass


def say(*a):
    # IronPython 2 でも Python 3 でも一行で出す
    print(u" ".join([x if isinstance(x, type(u"")) else (x.decode("utf-8") if isinstance(x, bytes) else u"%s" % (x,)) for x in a]))


def _try_capture(w, h, transparent, passes):
    vc = Rhino.Display.ViewCapture()
    vc.Width, vc.Height = w, h
    vc.ScaleScreenItems = False
    vc.DrawAxes = False
    vc.DrawGrid = False
    vc.DrawGridAxes = False
    vc.TransparentBackground = transparent
    if passes:
        try:
            vc.RealtimeRenderPasses = passes
        except Exception:
            pass
    try:
        return vc.CaptureToBitmap(view)
    except Exception as e:
        say(u"  ViewCapture の誤り：", e)
        return None


def _render_to(path):
    """Rhino のレンダリング（Render コマンド、Cycles）で書き出す。線（曲線・辺）は写らない"""
    old = {}
    for k in ("UseViewportSize", "ImageSize", "TransparentBackground"):
        try:
            old[k] = getattr(rs, k)
        except Exception:
            pass
    try:
        rs.UseViewportSize = False
        rs.ImageSize = System.Drawing.Size(W, H)     # ビューと同じ縦横の比なので、写る範囲は json のとおり
        rs.TransparentBackground = True
        doc.RenderSettings = rs
    except Exception as e:
        say(u"  レンダリングの大きさの設定：", e)
    try:
        Rhino.RhinoApp.RunScript(u"_-Render", False)
        Rhino.RhinoApp.RunScript(u'_-SaveRenderWindowAs "%s"' % path, False)
        Rhino.RhinoApp.RunScript(u"_-CloseRenderWindow", False)
    finally:
        try:
            for k, v in old.items():
                setattr(rs, k, v)
            doc.RenderSettings = rs
        except Exception:
            pass
    return os.path.exists(path)


def capture(name):
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        os.remove(path)
    say(u"書き出し：", name, u"ビュー", cw, u"×", ch, u"→", W, u"×", H)
    # 1）レンダリング（Render）。表示モードの書き出し（ViewCapture）は Mac では線だけになった（10-27）
    if _render_to(path):
        say(u"  レンダリングで書いた：", path)
        return
    say(u"  レンダリングで書けなかった。表示モードの書き出し（不透明）で")
    for w, h, tr, ps in [(W, H, False, PASSES), (W // 2, H // 2, False, PASSES)]:
        bmp = _try_capture(w, h, tr, ps)
        if bmp is not None:
            bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png)
            say(u"  書いた：", path, w, u"×", h)
            return
        say(u"  通らなかった：", w, u"×", h)


# ---------------------------------------------------------------- 一時的な変更（終わったら戻す）
# 1）材料の無いレイヤーに、レイヤーの色の材料を当てる（3dm には材料がほとんど無く、レンダリングが白一色になった）
added_mats = []
layer_old = []
used = set(o.Attributes.LayerIndex for o in doc.Objects)
for lay in list(doc.Layers):
    if lay.Index not in used or lay.RenderMaterialIndex >= 0:
        continue
    col = lay.Color
    m_ = Rhino.DocObjects.Material()
    m_.Name = u"作業_景観_" + lay.Name
    if lay.Name.startswith("04_"):                       # 周りの建物（PLATEAU）：淡い灰
        col = System.Drawing.Color.FromArgb(215, 215, 212)
    elif lay.Name.startswith("02_"):                     # 護岸
        col = System.Drawing.Color.FromArgb(190, 188, 182)
    m_.DiffuseColor = col
    if u"ガラス" in lay.Name:
        m_.Transparency = 0.6
        m_.Reflectivity = 0.2
    k_ = doc.Materials.Add(m_)
    added_mats.append(k_)
    layer_old.append((lay.Index, lay.RenderMaterialIndex))
    lay.RenderMaterialIndex = k_
    doc.Layers.Modify(lay, lay.Index, True)

# 2）川の辺より手前の物（向こう岸の建物）を隠す：視点は高野川の対岸
hidden = []
for o in doc.Objects:
    try:
        bb = o.Geometry.GetBoundingBox(True)
    except Exception:
        continue
    if not bb.IsValid:
        continue
    dmax = max((c.X - S_MM[0]) * D_DIR[0] + (c.Y - S_MM[1]) * D_DIR[1] for c in bb.GetCorners())
    if dmax < FRONT_CUT and o.Visible:
        hidden.append(o.Id)
for oid in hidden:
    doc.Objects.Hide(oid, True)
say(u"手前の物を隠した：", len(hidden), u"／材料を当てたレイヤー：", len(layer_old))

# 3）夜の LED（光る材料）
led_objs = []
for lay in doc.Layers:
    if lay.Name in LED_LAYERS:
        led_objs += list(doc.Objects.FindByLayer(lay) or [])
say(u"LED：", len(led_objs))
mat = Rhino.DocObjects.Material()
mat.Name = "作業_景観_LED"
mat.DiffuseColor = LED_COLOR
mat.EmissionColor = LED_COLOR
try:
    mat.ToPhysicallyBased()
    mat.PhysicallyBased.Emission = Rhino.Display.Color4f(LED_COLOR)
    mat.PhysicallyBased.BaseColor = Rhino.Display.Color4f(LED_COLOR)
except Exception:
    pass
mi = doc.Materials.Add(mat)
old_attr = [(o.Id, o.Attributes.Duplicate()) for o in led_objs]
sky_on = None

try:
    set_sun(True, DAY)
    view.Redraw()
    capture("keikan_hiru.png")

    for o in led_objs:
        a = o.Attributes.Duplicate()
        a.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
        a.MaterialIndex = mi
        doc.Objects.ModifyAttributes(o.Id, a, True)
    try:
        sky_on = rs.Skylight.Enabled
        rs.Skylight.Enabled = False
        doc.RenderSettings = rs
    except Exception:
        pass
    set_sun(False, NIGHT)
    view.Redraw()
    capture("keikan_yoru.png")
finally:
    for oid, a in old_attr:
        doc.Objects.ModifyAttributes(oid, a, True)
    for oid in hidden:
        doc.Objects.Show(oid, True)
    for li_, old_ in layer_old:
        lay = doc.Layers[li_]
        lay.RenderMaterialIndex = old_
        doc.Layers.Modify(lay, li_, True)
    for k_ in [mi] + added_mats:
        try:
            doc.Materials.Delete(k_, True)
        except Exception:
            pass
    if sun is not None:
        for k, v in saved.items():
            try:
                setattr(sun, k, v)
            except Exception:
                pass
        try:
            rs.Sun = sun
        except Exception:
            pass
        try:
            doc.RenderSettings = rs
        except Exception:
            pass
    try:
        if sky_on is not None:
            rs.Skylight.Enabled = sky_on
            doc.RenderSettings = rs
    except Exception:
        pass
    try:
        vp.SetViewProjection(saved_vi, True)
        vp.DisplayMode = saved_mode
    except Exception:
        pass
    doc.Views.Redraw()
say(u"おわり。out/ の keikan_hiru.png・keikan_yoru.png・keikan_view.json を push してください")
