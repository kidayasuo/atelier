# -*- coding: utf-8 -*-
"""育ち舎　2枚目「景観」の透視図（A4）：公園の角から西の道を北へ見る目の高さの透視を Rhino のレンダリングで書き出す（プレゼンの準備、10-29）
（今のビューのまま描くなら render_hiru.py・render_yoru.py を使う。名前と大きさを聞かれる）

左に道の向かいの家（お向かいさん）、真ん中に狭い西の道、右に西館の低い軒（向かいへは平屋の高さに抑えた側）。
課題の「透視図1枚以上、A4以上」に当てる（鳥瞰の代わり）。

使い方（Rhino 8、Mac）：
  1. atelier を pull して、sodachiya/sodachiya.3dm を開く。
  2. ツール→スクリプト→実行…（またはコマンド RunPythonScript）で、このファイルを選ぶ。
  3. いまのビューが一時的に目の高さの透視（二点透視：縦の線は縦）になり、レンダリング（Render、Cycles）で1枚書き出す。
     A4・300 dpi（3508×2480）で約5〜15分（レンダリングの設定の最大回数しだい。試しは下の SIZE を (1754, 1240) に）。
     書き出し先：このファイルの隣の out/me.png と、カメラを書いた out/me_view.json。
  4. 走り終わると、足した物・変えた設定は元に戻る（3dm は保存しなくてよい）。
     周りの建物（04_周辺_建物と親）は一時的に表示して淡い暖かい灰（keikan_render.py と同じ）。公園の木などはそのまま。
     空は淡い色の不透明。太陽は 11/5 10:00（京都）。
     コマンド行に「〜：効かなかった」と出たら、その設定はレンダリングのパネルで手で直す。
  5. 視点を直すとき：
     ・数で：下の CAM（立つ所、z は目の高さ）・TGT（見る点、z を CAM と同じにすると縦の線が縦）・LENS を直す。
       道の向きは北から少し西（敷地の西の辺の向き (-0.074, 0.997)）。TGT を右（東）へ動かすと道は絵の左へ寄り、西館が大きく入る。
       仮の図で確かめる：python3 sodachiya/present/tools/me_kari.py → present/out/me_kari.png（同じ CAM・TGT・LENS を読む）。
     ・Rhino で：好きな透視のビューにしてから USE_CURRENT_VIEW を True にして走らせる
       （今のビューのまま描く。カメラは me_view.json に書かれる）。
  6. できたら out/ の2つを push する：
       git add sodachiya/present/rhino/out/me.png sodachiya/present/rhino/out/me_view.json
       git commit -m "[プレゼン] 2枚目の透視図のレンダリング" && git push

座標は 3dm（mm、+y が北、z=0 が敷地の GL、道の面は約−0.3 m）。
敷地の角（m）：北 (0, 0)・東 (34.86, -43.83)・南 (-14.44, -83.04)・南西 (-21.91, -73.65)・北西 (-25.83, -20.54)。
小竹薮公園は南西の角（南・南西・(-12.52, -66.18)・(-5.05, -75.57) の四角）。西の道（幅 6 m）は南西の角で折れて馬橋へ。
西館は y −44〜−13.5、道の側の軒は高さ約 4.5 m。
"""
import os, io, json, datetime
import Rhino
import scriptcontext as sc
import System

# ---------------------------------------------------------------- 決める数
USE_CURRENT_VIEW = False               # True：今のビューのまま描く（その場で視点を直したとき）
CAM = (-26600.0, -71500.0, 1500.0)     # カメラ：公園の角（道の折れ目）の道の上、目の高さ GL+1.5 m
TGT = (-23700.0, -36400.0, 1500.0)     # 見る点：西の道を約35 m 北、道の軸から右へ約2.5 m（同じ高さ＝二点透視）
LENS = 28.0                            # レンズ（35 mm 換算）
SIZE = (3508, 2480)                    # A4 横・300 dpi（297:210）。試しは (1754, 1240)
DAY = datetime.datetime(2026, 11, 5, 10, 0)
LAT, LON, TZ = 35.049106, 135.785095, 9.0
SKY_TOP = System.Drawing.Color.FromArgb(0xC9, 0xDC, 0xEC)      # 空：淡い青（上）
SKY_BOTTOM = System.Drawing.Color.FromArgb(0xEE, 0xF2, 0xF4)   # 地平の近く：ほぼ白
CONTEXT_COLOR = System.Drawing.Color.FromArgb(0xD9, 0xD6, 0xCF)  # 周りの建物（PLATEAU）：淡い暖かい灰
CONTEXT_LAYER = u"04_周辺_建物"

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
OUT = os.path.join(HERE, "out")
if not os.path.isdir(OUT):
    os.makedirs(OUT)

doc = sc.doc


def say(*a):
    print(u" ".join([x if isinstance(x, type(u"")) else (x.decode("utf-8") if isinstance(x, bytes) else u"%s" % (x,)) for x in a]))


def P3(t):
    return Rhino.Geometry.Point3d(t[0], t[1], t[2])


# ---------------------------------------------------------------- ビュー（いま開いているビューを一時的に使う。終わったら元に戻す）
view = doc.Views.ActiveView
vp = view.ActiveViewport
saved_vi = Rhino.DocObjects.ViewportInfo(vp)
saved_mode = vp.DisplayMode
if not USE_CURRENT_VIEW:
    try:
        vp.ChangeToTwoPointPerspectiveProjection(LENS)       # 二点透視（縦の線は縦）
    except Exception as e:
        say(u"二点透視：効かなかった（ふつうの透視で。見る点が目と同じ高さなので縦はほぼ縦）", e)
        try:
            vp.ChangeToPerspectiveProjection(True, LENS)
        except Exception as e2:
            say(u"透視への切り替え：効かなかった", e2)
    vp.SetCameraLocations(P3(TGT), P3(CAM))
    vp.CameraUp = Rhino.Geometry.Vector3d.ZAxis
    try:
        vp.Camera35mmLensLength = LENS
    except Exception as e:
        say(u"レンズ：効かなかった", e)
elif not vp.IsPerspectiveProjection:
    say(u"今のビューは透視ではない（平行投影のまま描く）")
for m in Rhino.Display.DisplayModeDescription.GetDisplayModes():
    if m.EnglishName.lower().startswith("raytrac") or m.EnglishName.lower().startswith("render"):
        try:
            vp.DisplayMode = m
        except Exception:
            pass
        break
view.Redraw()
_c, _t = vp.CameraLocation, vp.CameraTarget
with io.open(os.path.join(OUT, "me_view.json"), "w", encoding="utf-8") as _f:   # IronPython では閉じないと書かれない（10-30）
    _f.write(u"%s" % json.dumps(dict(camera_mm=[round(_c.X), round(_c.Y), round(_c.Z)], target_mm=[round(_t.X), round(_t.Y), round(_t.Z)],
               lens_mm=round(vp.Camera35mmLensLength, 1), px=list(SIZE), current_view=USE_CURRENT_VIEW,
               made=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               note=u"3dm の mm。公園の角から西の道を北へ見る目の高さの透視。2枚目「景観」の A4 の透視図の箱（297×210 mm）に縦横の比を保って入れる"), indent=1, ensure_ascii=True))
try:
    doc.NamedViews.Add(u"目の高さ_公園の角から北", vp.Id)
except Exception:
    pass

# ---------------------------------------------------------------- 光と背景
rs = doc.RenderSettings
sun = None
try:
    sun = rs.Sun
except Exception:
    try:
        sun = doc.Lights.Sun
    except Exception:
        pass
saved_sun = {}
if sun is not None:
    for k in ("Enabled", "ManualControl", "Latitude", "Longitude", "TimeZone", "DaylightSaving"):
        try:
            saved_sun[k] = getattr(sun, k)
        except Exception:
            pass


def set_sun():
    if sun is None:
        say(u"太陽の設定が見つからない（Rhino の版の違い）。太陽パネルで手で：11/5 10:00、京都")
        return
    try:
        sun.ManualControl = False
        sun.Latitude, sun.Longitude, sun.TimeZone = LAT, LON, TZ
        sun.DaylightSaving = False
        sun.SetDateTime(DAY, System.DateTimeKind.Local)
    except Exception as e:
        say(u"太陽の時刻：", e)
    sun.Enabled = True
    try:
        rs.Sun = sun
    except Exception:
        pass
    try:
        doc.RenderSettings = rs
    except Exception:
        pass


BG_KEYS = ("BackgroundStyle", "BackgroundColorTop", "BackgroundColorBottom")
bg_old = {}
for k in BG_KEYS:
    try:
        bg_old[k] = getattr(doc.RenderSettings, k)
    except Exception:
        pass


def bg_set(vals):
    for k, v in vals.items():
        try:
            setattr(rs, k, v)
        except Exception as e:
            say(u"  背景の", k, u"：効かなかった", e)
    try:
        doc.RenderSettings = rs
    except Exception as e:
        say(u"  背景：効かなかった", e)


def day_sky():
    vals = dict(BackgroundColorTop=SKY_TOP, BackgroundColorBottom=SKY_BOTTOM)
    try:
        vals["BackgroundStyle"] = Rhino.Display.BackgroundStyle.Gradient
    except Exception:
        pass
    bg_set(vals)


def render_to(path):
    """Rhino のレンダリング（Render コマンド、Cycles）で書き出す。線（曲線・辺）は写らない"""
    old = {}
    for k in ("UseViewportSize", "ImageSize", "TransparentBackground"):
        try:
            old[k] = getattr(rs, k)
        except Exception:
            pass
    try:
        rs.UseViewportSize = False
        rs.ImageSize = System.Drawing.Size(SIZE[0], SIZE[1])
        rs.TransparentBackground = False
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
    say(u"書き出し：", name, SIZE[0], u"×", SIZE[1])
    if render_to(path):
        say(u"  レンダリングで書いた：", path)
        return
    say(u"  レンダリングで書けなかった。表示モードの書き出し（ViewCapture）で")
    for w, h in (SIZE, (SIZE[0] // 2, SIZE[1] // 2)):
        try:
            vc = Rhino.Display.ViewCapture()
            vc.Width, vc.Height = w, h
            vc.ScaleScreenItems = False
            vc.DrawAxes = vc.DrawGrid = vc.DrawGridAxes = False
            vc.TransparentBackground = False
            bmp = vc.CaptureToBitmap(view)
        except Exception as e:
            say(u"  ViewCapture の誤り：", e)
            bmp = None
        if bmp is not None:
            bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png)
            say(u"  書いた：", path, w, u"×", h)
            return
        say(u"  通らなかった：", w, u"×", h)


# ---------------------------------------------------------------- 一時的な変更（終わったら戻す）
# 0）周りの建物（PLATEAU）のレイヤーと親を表示する（ふだん隠してある、隠れたレイヤーは Render に写らない）
ctx_idx = set()
ctx_old = []
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
    for l_ in reversed(chain):
        l_ = doc.Layers[l_.Index]
        try:
            l_.SetPersistentVisibility(True)
        except Exception:
            pass
        l_.IsVisible = True
        if l_.Index == lay.Index:
            l_.Color = CONTEXT_COLOR
        doc.Layers.Modify(l_, l_.Index, True)
say(u"周りの建物のレイヤー：", len(ctx_idx))

# 1）材料の無いレイヤーに、レイヤーの色の材料を当てる（周りの建物は淡い灰）
added_mats, layer_old = [], []
used = set(o.Attributes.LayerIndex for o in doc.Objects)
for lay in list(doc.Layers):
    if lay.Index not in ctx_idx and (lay.Index not in used or lay.RenderMaterialIndex >= 0):
        continue
    col = lay.Color
    m_ = Rhino.DocObjects.Material()
    m_.Name = u"作業_目の高さ_" + lay.Name
    if lay.Index in ctx_idx:
        col = CONTEXT_COLOR
        m_.Shine = 0.0
        m_.Reflectivity = 0.0
    elif lay.Name.startswith("02_"):
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
say(u"材料を当てたレイヤー：", len(layer_old))

try:
    set_sun()
    day_sky()
    view.Redraw()
    capture("me.png")
finally:
    for li_, old_ in layer_old:
        lay = doc.Layers[li_]
        lay.RenderMaterialIndex = old_
        doc.Layers.Modify(lay, li_, True)
    for li_, vis_, col_, pv_ in ctx_old:
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
    for k_ in added_mats:
        try:
            doc.Materials.Delete(k_, True)
        except Exception:
            pass
    if sun is not None:
        for k, v in saved_sun.items():
            try:
                setattr(sun, k, v)
            except Exception:
                pass
        try:
            rs.Sun = sun
        except Exception:
            pass
    if bg_old:
        bg_set(bg_old)
    try:
        doc.RenderSettings = rs
    except Exception:
        pass
    try:
        vp.SetViewProjection(saved_vi, True)
        vp.DisplayMode = saved_mode
    except Exception:
        pass
    doc.Views.Redraw()
say(u"おわり。out/ の me.png・me_view.json を push してください")
