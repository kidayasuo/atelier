# -*- coding: utf-8 -*-
"""育ち舎　沿川の景観（昼・夜）を、高野川の向こう岸から見る目の高さの透視図として Rhino のレンダリングで書き出す（プレゼンの準備、10-27、10-29 透視に）

使い方（Rhino 8、Mac）：
  1. atelier を pull して、sodachiya/sodachiya.3dm を開く。
  2. ツール→スクリプト→実行…（またはコマンド RunPythonScript）で、このファイルを選ぶ。
  3. いまのビューが一時的に景観の透視（二点透視：縦の線は縦）になり、レンダリング（Render）で昼・夜の2枚を書き出す。
     4252×1701（2.5:1）で1枚に約5〜15分。画質（回数）はレンダリングの設定→「レンダリング」の最大回数で決まる。試しは PX を半分に。
     書き出し先：このファイルの隣の out/keikan_hiru.png・out/keikan_yoru.png（と、カメラを書いた keikan_view.json）。
  4. 走り終わると、足した物・変えた設定は元に戻る（3dm は保存しなくてよい）。
     昼・夜とも、ふだん隠している周りの建物（04_周辺_建物（PLATEAU LOD1）と親の「L 周辺の道路・建物…」）を
     一時的に表示し、淡い暖かい灰（CONTEXT_COLOR）を当てる。夜は、スカイライトを切り、空を群青（NIGHT_SKY）の一色に、
     背景は不透明にし、越屋根の LED の帯に沿って線の光源（LED_LIGHT_POWER）を一時的に置く。
     3dm に無い向こう岸（川の水際から川沿いの道まで：河原と石積み）を、一時的に面で足す（足元が抜けないように）。
     コマンド行に「〜：効かなかった」と出たら、その設定はレンダリングのパネルで手で直す。
     曲線（等高線・駐車の線・屋根の円など）は Render の絵には写らない。ビューのレンダリング表示で光って見えるのを消すには、
     Rhino 設定＞表示モード＞レンダリング（またはレイトレース）＞オブジェクト＞曲線→「曲線を表示」を外す。
  5. 視点を直すとき：下の CAM_T（川に沿う位置、S から北東へ mm）・CAM_D（川に直角、S−E の辺から手前へ負）・EYE・LENS を直す。
     見る向きは川に直角（D_DIR）、見る点は目と同じ高さ（縦は縦）。仮の図で確かめる：
       python3 sodachiya/present/tools/keikan_kari.py → present/out/keikan_kari_hiru.png（同じ数を読む）。
     Rhino で好きな透視にしたときは USE_CURRENT_VIEW を True に（今のビューのまま描き、カメラは json に書かれる）。
  6. out/ の3つを push する（git add sodachiya/present/rhino/out）。mock.py が素材03・04にこの絵を使う。

見る向き：高野川の向こう岸（南東、川沿いの道の川の側の歩道）から、敷地の川の辺（S→E）に直角に、目の高さ 1.5 m。
昼の背景は透明（空は mock.py が塗る）、夜は群青の空ごと不透明。
昼：11/5 10:00 の太陽（京都）。夜：ナイトモード。太陽とスカイライトを消し、空は群青、越屋根の LED（50b・29）だけを光らせる。
数字を変えたいときは下の「決める数」だけを直す。
"""
import os, json, datetime, math
import Rhino
import scriptcontext as sc
import System

# ---------------------------------------------------------------- 決める数
S_MM = (-14440.0, -83040.0)            # 敷地の南の角（3dm、mm）
T_DIR = (0.78264675, 0.62246611)       # 川から見て右（北東）へ
D_DIR = (-0.62246611, 0.78264675)      # 奥（北西）へ＝見る向き
USE_CURRENT_VIEW = False               # True：今のビューのまま描く（その場で視点を直したとき）
CAM_T = 38000.0                         # カメラの川に沿う位置（S から北東へ、mm）：建物（t 約13〜64 m）の中ほど
CAM_D = -45000.0                        # 川に直角（S−E の辺＝敷地の側の崖の上の縁から手前へ、mm）：向こう岸の川沿いの道（3dm では d −44〜−54 m、高さ−0.42 m）の川の側の歩道
GROUND_Z = -420.0                       # 向こう岸の道の高さ（PLATEAU の道、mm）
EYE = 1500.0                            # 目の高さ（地面から、mm）
LENS = 24.0                             # レンズ（35 mm 換算、横 36 mm に当てる）。横の画角約74°
PX = (4252, 1701)                       # 横長 2.5:1（横 360 mm・300 dpi）
CAM = (S_MM[0] + T_DIR[0] * CAM_T + D_DIR[0] * CAM_D, S_MM[1] + T_DIR[1] * CAM_T + D_DIR[1] * CAM_D, GROUND_Z + EYE)
TGT = (CAM[0] + D_DIR[0] * 75000.0, CAM[1] + D_DIR[1] * 75000.0, GROUND_Z + EYE)   # 川に直角に、同じ高さ
# 向こう岸（3dm に無い）：川の水際（d −29 m、水面−6.1 m）→河原（−4.6 m）→石積み→道（d −44 m）。一時的に足す
BANK = [(-29000.0, -6100.0), (-30500.0, -4600.0), (-38500.0, -4600.0), (-44000.0, GROUND_Z), (-60000.0, GROUND_Z)]
BANK_COLOR = System.Drawing.Color.FromArgb(0xB4, 0xB4, 0x9C)
PASSES = 400                            # レイトレースの回数（多いほどざらつきが減る）
DAY = datetime.datetime(2026, 11, 5, 10, 0)
LAT, LON, TZ = 35.049106, 135.785095, 9.0
LED_LAYERS = ("50b_越屋根_LED", "29_西館_越屋根_LED")   # 本館・西館の越屋根
NIGHT = datetime.datetime(2026, 11, 5, 21, 0)   # 夜は太陽を地平の下にも置く（消すのが効かない Rhino があった）
FRONT_CUT = CAM_D - 300.0              # カメラより手前（後ろ）の物だけ隠す（川・橋・向こう岸の道は写す）
LED_COLOR = System.Drawing.Color.FromArgb(255, 217, 138)
LED_LIGHT_POWER = 1.0                   # LED の線の光源の強さ（Light.Intensity）。軒が暗ければ 2〜5、白く飛べば 0.3〜0.5
LED_LIGHT_DROP = 60.0                   # 線の光源を LED の帯の下端からどれだけ下に置くか（mm）
NIGHT_SKY = System.Drawing.Color.FromArgb(0x4C, 0x6C, 0xB3)   # 夜の空：群青色 #4C6CB3。もっと夜らしくは #1E2A5A など
CONTEXT_COLOR = System.Drawing.Color.FromArgb(0xD9, 0xD6, 0xCF)  # 周りの建物（PLATEAU）：淡い暖かい灰。育ち舎を主役に
CONTEXT_LAYER = u"04_周辺_建物"          # この名で始まるレイヤーと、その親を一時的に表示する

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
OUT = os.path.join(HERE, "out")
if not os.path.isdir(OUT):
    os.makedirs(OUT)

doc = sc.doc


def say(*a):
    print(u" ".join([x if isinstance(x, type(u"")) else (x.decode("utf-8") if isinstance(x, bytes) else u"%s" % (x,)) for x in a]))


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
W, H = PX
if not USE_CURRENT_VIEW:
    try:
        vp.ChangeToTwoPointPerspectiveProjection(LENS)       # 二点透視（縦の線は縦）
    except Exception as e:
        say(u"二点透視：効かなかった（ふつうの透視で。見る点が目と同じ高さなので縦はほぼ縦）", e)
        try:
            vp.ChangeToPerspectiveProjection(True, LENS)
        except Exception as e2:
            say(u"透視への切り替え：効かなかった", e2)
    vp.SetCameraLocations(Rhino.Geometry.Point3d(*TGT), Rhino.Geometry.Point3d(*CAM))
    vp.CameraUp = Rhino.Geometry.Vector3d.ZAxis
    try:
        vp.Camera35mmLensLength = LENS
    except Exception as e:
        say(u"レンズ：効かなかった", e)
elif not vp.IsPerspectiveProjection:
    say(u"今のビューは透視ではない（平行投影のまま描く）")
mode = raytraced()
if mode:
    vp.DisplayMode = mode
else:
    print("Raytraced display mode not found")
view.Redraw()
_c, _t = vp.CameraLocation, vp.CameraTarget
json.dump(dict(projection="perspective", camera_mm=[round(_c.X), round(_c.Y), round(_c.Z)],
               target_mm=[round(_t.X), round(_t.Y), round(_t.Z)], direction=[round(D_DIR[0], 6), round(D_DIR[1], 6), 0.0],
               lens_mm=round(vp.Camera35mmLensLength, 1), hfov_deg=round(2 * math.degrees(math.atan(18.0 / vp.Camera35mmLensLength)), 1),
               two_point=True, px=[W, H], current_view=USE_CURRENT_VIEW,
               made=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               note=u"3dm の mm。高野川の向こう岸から川に直角に見る目の高さ（1.5 m）の透視。昼は背景が透明"),
          open(os.path.join(OUT, "keikan_view.json"), "w"), indent=1, ensure_ascii=False)
try:
    doc.NamedViews.Add(u"景観_向こう岸から", vp.Id)
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


def _sky_get():
    """スカイライトが点いているか（読めなければ None）"""
    for f in (lambda: doc.RenderSettings.Skylight.Enabled,
              lambda: doc.RenderSettings.SkylightEnabled,
              lambda: doc.Lights.Skylight.Enabled):
        try:
            v = f()
            if v is not None:
                return bool(v)
        except Exception:
            pass
    return None


def set_skylight(on):
    """スカイライトを点ける・消す。Rhino の版で書き方が違うので、いくつか試し、読み直して確かめる"""
    tried = []
    # 1）Rhino 8：RenderSettings.Skylight（Rhino.Render.Skylight）。写しなので戻す
    try:
        r_ = rs     # 太陽と同じ写しに書く（別の写しを戻すと太陽の変更が消える）
        sk = r_.Skylight
        try:
            sk.BeginChange(Rhino.Render.RenderContent.ChangeContexts.Program)
        except Exception:
            pass
        sk.Enabled = on
        try:
            sk.EndChange()
        except Exception:
            pass
        try:
            r_.Skylight = sk
        except Exception:
            pass
        doc.RenderSettings = r_
        tried.append(u"RenderSettings.Skylight")
    except Exception as e:
        say(u"  スカイライト（RenderSettings.Skylight）：", e)
    # 2）古い書き方：RenderSettings.SkylightEnabled
    if _sky_get() != on:
        try:
            r_ = rs
            r_.SkylightEnabled = on
            doc.RenderSettings = r_
            tried.append(u"SkylightEnabled")
        except Exception as e:
            say(u"  スカイライト（SkylightEnabled）：", e)
    # 3）光源の表：doc.Lights.Skylight
    if _sky_get() != on:
        try:
            doc.Lights.Skylight.Enabled = on
            tried.append(u"Lights.Skylight")
        except Exception as e:
            say(u"  スカイライト（Lights.Skylight）：", e)
    now = _sky_get()
    if now == on:
        say(u"スカイライト：", u"点けた" if on else u"消した", u"（", u"・".join(tried), u"）")
    else:
        say(u"スカイライト：効かなかった（いま", now, u"）。レンダリングのパネルの「スカイライト」を手で",
            u"オンに" if on else u"オフに")


BG_KEYS = ("BackgroundStyle", "BackgroundColorTop", "BackgroundColorBottom")


def bg_save():
    out = {}
    for k in BG_KEYS:
        try:
            out[k] = getattr(doc.RenderSettings, k)
        except Exception:
            pass
    return out


def bg_set(vals):
    """背景（様式・色）を当てる。vals は {名前: 値}"""
    r_ = rs
    for k, v in vals.items():
        try:
            setattr(r_, k, v)
        except Exception as e:
            say(u"  背景の", k, u"：効かなかった", e)
    try:
        doc.RenderSettings = r_
    except Exception as e:
        say(u"  背景：効かなかった", e)


def night_sky():
    try:
        style = Rhino.Display.BackgroundStyle.SolidColor
    except Exception:
        style = None
    vals = dict(BackgroundColorTop=NIGHT_SKY, BackgroundColorBottom=NIGHT_SKY)
    if style is not None:
        vals["BackgroundStyle"] = style
    bg_set(vals)
    try:
        c_ = doc.RenderSettings.BackgroundColorTop
        say(u"夜の空：", u"#%02X%02X%02X" % (c_.R, c_.G, c_.B), doc.RenderSettings.BackgroundStyle)
    except Exception:
        say(u"夜の空：読み直せなかった。レンダリングのパネルの「背景」を単色・群青に")


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


def _render_to(path, transparent=True):
    """Rhino のレンダリング（Render コマンド、Cycles）で書き出す。線（曲線・辺）は写らない"""
    old = {}
    for k in ("UseViewportSize", "ImageSize", "TransparentBackground"):
        try:
            old[k] = getattr(rs, k)
        except Exception:
            pass
    try:
        rs.UseViewportSize = False
        rs.ImageSize = System.Drawing.Size(W, H)
        rs.TransparentBackground = transparent     # 昼は透明（空は mock.py）、夜は群青の空ごと
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


def capture(name, transparent=True):
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        os.remove(path)
    say(u"書き出し：", name, u"ビュー", cw, u"×", ch, u"→", W, u"×", H)
    # 1）レンダリング（Render）。表示モードの書き出し（ViewCapture）は Mac では線だけになった（10-27）
    if _render_to(path, transparent):
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
# 0）周りの建物（PLATEAU）のレイヤーと親を表示する。sodachiya.3dm ではふだん隠してあり（clean_wire.py の HIDE_DEFAULT）、
#    隠れたレイヤーは Render に写らない（10-29、昼に周りの建物が出なかった）
ctx_idx = set()
ctx_old = []                                             # (index, IsVisible, Color, 永続の表示)：子が先、親が後
for lay in list(doc.Layers):
    if not lay.Name.startswith(CONTEXT_LAYER):
        continue
    chain = [lay]
    pid = lay.ParentLayerId
    while pid != System.Guid.Empty:
        pl = doc.Layers.FindId(pid)
        if pl is None:
            break
        chain.append(pl)
        pid = pl.ParentLayerId
    ctx_idx.add(lay.Index)
    for l_ in chain:
        if any(i_ == l_.Index for i_, _, _, _ in ctx_old):
            continue
        try:
            pv = l_.GetPersistentVisibility()
        except Exception:
            pv = None
        ctx_old.append((l_.Index, l_.IsVisible, l_.Color, pv))
    for l_ in reversed(chain):                           # 親から順に点ける
        l_ = doc.Layers[l_.Index]
        try:
            l_.SetPersistentVisibility(True)
        except Exception:
            pass
        l_.IsVisible = True
        if l_.Index == lay.Index:
            l_.Color = CONTEXT_COLOR
        doc.Layers.Modify(l_, l_.Index, True)
if ctx_idx:
    say(u"周りの建物のレイヤーを表示した：", u"・".join(doc.Layers[i_].Name for i_, _, _, _ in ctx_old))
else:
    say(u"周りの建物のレイヤー（", CONTEXT_LAYER, u"…）が見つからない")

# 1）材料の無いレイヤーに、レイヤーの色の材料を当てる（3dm には材料がほとんど無く、レンダリングが白一色になった）
#    周りの建物は材料があっても淡い暖かい灰（CONTEXT_COLOR）に替える
added_mats = []
layer_old = []
used = set(o.Attributes.LayerIndex for o in doc.Objects)
for lay in list(doc.Layers):
    if lay.Index not in ctx_idx and (lay.Index not in used or lay.RenderMaterialIndex >= 0):
        continue
    col = lay.Color
    m_ = Rhino.DocObjects.Material()
    m_.Name = u"作業_景観_" + lay.Name
    if lay.Index in ctx_idx:                             # 周りの建物（PLATEAU）：淡い暖かい灰、つやなし
        col = CONTEXT_COLOR
        m_.Shine = 0.0
        m_.Reflectivity = 0.0
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

# 2b）向こう岸（3dm に無い、川の水際から川沿いの道まで）を一時的に面で足す。足元が抜けないように
bank_ids, bank_mat = [], -1
try:
    bm_ = Rhino.DocObjects.Material()
    bm_.Name = u"作業_景観_向こう岸"
    bm_.DiffuseColor = BANK_COLOR
    bank_mat = doc.Materials.Add(bm_)
    t_a, t_b = CAM_T - 150000.0, CAM_T + 150000.0
    for (d0, z0), (d1, z1) in zip(BANK[:-1], BANK[1:]):
        mesh = Rhino.Geometry.Mesh()
        for t_, d_, z_ in ((t_a, d0, z0), (t_b, d0, z0), (t_b, d1, z1), (t_a, d1, z1)):
            mesh.Vertices.Add(P(t_, d_, z_))
        mesh.Faces.AddFace(0, 1, 2, 3)
        mesh.Normals.ComputeNormals()
        at_ = Rhino.DocObjects.ObjectAttributes()
        at_.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
        at_.MaterialIndex = bank_mat
        bank_ids.append(doc.Objects.AddMesh(mesh, at_))
    say(u"向こう岸の面を足した：", len(bank_ids))
except Exception as e:
    say(u"向こう岸の面：効かなかった", e)

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
bg_old = bg_save()
sky_old = _sky_get()
led_lights = []                                          # 足した線の光源の Id（終わったら消す）


def add_led_lights():
    """LED の帯ごとに、長い向きに沿った線の光源（WorldLinear）を帯の少し下に置く。
    光る材料だけでは光源に数えられず、光源が無いと Rhino が既定の照明を足して昼のように明るくなった（10-29）"""
    n_ = 0
    for o in led_objs:
        try:
            bb = o.Geometry.GetBoundingBox(True)
        except Exception:
            continue
        if not bb.IsValid:
            continue
        dx, dy = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
        cx, cy = (bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2
        z = bb.Min.Z - LED_LIGHT_DROP
        if dx >= dy:
            a_ = Rhino.Geometry.Point3d(bb.Min.X, cy, z)
            b_ = Rhino.Geometry.Point3d(bb.Max.X, cy, z)
        else:
            a_ = Rhino.Geometry.Point3d(cx, bb.Min.Y, z)
            b_ = Rhino.Geometry.Point3d(cx, bb.Max.Y, z)
        if a_.DistanceTo(b_) < 1.0:
            continue
        try:
            lt = Rhino.Geometry.Light()
            lt.LightStyle = Rhino.Geometry.LightStyle.WorldLinear
            lt.Location = a_
            lt.Length = b_ - a_                          # 線の光源の長さと向き
            lt.Direction = Rhino.Geometry.Vector3d(0, 0, -1)
            lt.Diffuse = LED_COLOR
            lt.Intensity = LED_LIGHT_POWER
            try:
                lt.IsEnabled = True
            except Exception:
                pass
            try:
                lt.Name = u"作業_景観_LED光源"
            except Exception:
                pass
            k_ = doc.Lights.Add(lt)
            if k_ >= 0:
                led_lights.append(doc.Lights[k_].Id)
                n_ += 1
        except Exception as e:
            say(u"  LED の線の光源：効かなかった", e)
            break
    say(u"LED の線の光源を置いた：", n_, u"／", len(led_objs), u"（強さ", LED_LIGHT_POWER, u"）")


def remove_led_lights():
    for lid in led_lights:
        try:
            lt = doc.Lights.FindId(lid)
            if lt is not None:
                doc.Lights.Delete(lt.Index, True)
        except Exception as e:
            say(u"  LED の光源を消せなかった：", e)
    del led_lights[:]


try:
    # 昼：太陽、スカイライトと背景はファイルのまま、背景は透明（空は mock.py）
    set_sun(True, DAY)
    view.Redraw()
    capture("keikan_hiru.png", transparent=True)

    # 夜：ナイトモード。太陽なし・スカイライトなし・空は群青（不透明）、LED は光る材料と線の光源
    for o in led_objs:
        a = o.Attributes.Duplicate()
        a.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
        a.MaterialIndex = mi
        doc.Objects.ModifyAttributes(o.Id, a, True)
    set_sun(False, NIGHT)
    set_skylight(False)
    night_sky()
    add_led_lights()
    say(u"夜を描く前：スカイライト", _sky_get(), u"／光源", doc.Lights.Count)
    view.Redraw()
    capture("keikan_yoru.png", transparent=False)
finally:
    remove_led_lights()
    for oid in bank_ids:
        try:
            doc.Objects.Delete(oid, True)
        except Exception:
            pass
    if bank_mat >= 0:
        try:
            doc.Materials.Delete(bank_mat, True)
        except Exception:
            pass
    for oid, a in old_attr:
        doc.Objects.ModifyAttributes(oid, a, True)
    for oid in hidden:
        doc.Objects.Show(oid, True)
    for li_, old_ in layer_old:
        lay = doc.Layers[li_]
        lay.RenderMaterialIndex = old_
        doc.Layers.Modify(lay, li_, True)
    for li_, vis_, col_, pv_ in ctx_old:                 # 子から順に、表示と色を戻す
        try:
            lay = doc.Layers[li_]
            if pv_ is not None:
                try:
                    lay.SetPersistentVisibility(pv_)
                except Exception:
                    pass
            lay.IsVisible = vis_
            lay.Color = col_
            doc.Layers.Modify(lay, li_, True)
        except Exception as e:
            say(u"  レイヤーを戻せなかった：", e)
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
    if bg_old:
        bg_set(bg_old)
    if sky_old is not None and _sky_get() != sky_old:
        set_skylight(sky_old)
    try:
        vp.SetViewProjection(saved_vi, True)
        vp.DisplayMode = saved_mode
    except Exception:
        pass
    doc.Views.Redraw()
say(u"おわり。out/ の keikan_hiru.png・keikan_yoru.png・keikan_view.json を push してください")
