# -*- coding: utf-8 -*-
"""育ち舎　沿川の景観立面（昼・夜）を Rhino のレイトレースで書き出す（プレゼンの準備、10-27）

使い方（Rhino 8、Mac）：
  1. atelier を pull して、sodachiya/sodachiya.3dm を開く。
  2. ツール → スクリプト → 実行…（または コマンド RunPythonScript）で、このファイルを選ぶ。
  3. 浮いたビュー「景観立面」ができ、レイトレースで昼・夜の2枚を書き出す（1枚に数分）。
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
LED_LAYER = "50b_越屋根_LED"
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


# ---------------------------------------------------------------- ビュー（紙と同じ縦横の比の浮いたビュー）
paper_w = (T1 - T0) / SCALE
paper_h = (Z1 - Z0) / SCALE
view = doc.Views.Find("景観立面", False)
if view is None:
    rect = System.Drawing.Rectangle(60, 60, 1440, int(1440 * paper_h / paper_w) + 40)
    view = doc.Views.Add("景観立面", Rhino.Display.DefinedViewportProjection.Front, rect, True)
vp = view.ActiveViewport
cw, ch = vp.Size.Width, vp.Size.Height
tc, zc = (T0 + T1) / 2, (Z0 + Z1) / 2
half_w = (T1 - T0) / 2
half_h = half_w * ch / float(cw)          # ビューの比に合わせる（高さが紙より少し違えば、その分を json に書く）
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
view.Redraw()
W = int(round(paper_w * PX_PER_MM))
H = int(round(W * ch / float(cw)))
json.dump(dict(t0=T0, t1=T1, z0=zc - half_h, z1=zc + half_h, scale=SCALE, px=[W, H],
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


def set_sun(on):
    if sun is None:
        print("太陽の設定が見つからない（Rhino の版の違い）。太陽パネルで手で：11/5 10:00、京都")
        return
    try:
        sun.ManualControl = False
        sun.Latitude, sun.Longitude, sun.TimeZone = LAT, LON, TZ
        sun.DaylightSaving = False
        sun.SetDateTime(DAY, System.DateTimeKind.Local)
    except Exception as e:
        print("太陽の時刻：", e)
    sun.Enabled = on
    try:
        rs.Sun = sun
    except Exception:
        pass


def capture(name):
    vc = Rhino.Display.ViewCapture()
    vc.Width, vc.Height = W, H
    vc.ScaleScreenItems = False
    vc.DrawAxes = False
    vc.DrawGrid = False
    vc.DrawGridAxes = False
    vc.TransparentBackground = True
    try:
        vc.RealtimeRenderPasses = PASSES
    except Exception:
        pass
    bmp = vc.CaptureToBitmap(view)
    if bmp is None:
        print("書き出せなかった：", name)
        return
    path = os.path.join(OUT, name)
    bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png)
    print("書いた：", path, W, "×", H)


# ---------------------------------------------------------------- 夜の LED（一時的に光る材料を当てる）
led_objs = []
for lay in doc.Layers:
    if lay.Name == LED_LAYER:
        led_objs += list(doc.Objects.FindByLayer(lay) or [])
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
    set_sun(True)
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
    except Exception:
        pass
    set_sun(False)
    view.Redraw()
    capture("keikan_yoru.png")
finally:
    for oid, a in old_attr:
        doc.Objects.ModifyAttributes(oid, a, True)
    try:
        doc.Materials.Delete(mi, True)
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
        if sky_on is not None:
            rs.Skylight.Enabled = sky_on
    except Exception:
        pass
    doc.Views.Redraw()
print("おわり。out/ の keikan_hiru.png・keikan_yoru.png・keikan_view.json を push してください")
