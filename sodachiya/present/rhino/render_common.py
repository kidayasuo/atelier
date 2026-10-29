# -*- coding: utf-8 -*-
"""今のビューのまま描く昼・夜のレンダリングの共通（render_hiru.py・render_yoru.py から使う。プレゼンの準備、10-29）

使い方は render_hiru.py の頭を見る。ここは直接走らせない。
設定と後始末は keikan_render.py の昼・夜と同じ（昼：11/5 10:00 の太陽、周りの建物（04）を淡い暖かい灰で一時表示。
夜：太陽とスカイライトを消し、空は群青、越屋根の LED に光る材料と線の光源）。ビューは動かさない、手前の物も隠さない
（隠したい物は Rhino で Hide してから走らせる）。終わったら全部戻す。
"""
import os, json, datetime, math
import Rhino
import scriptcontext as sc
import System

# ---------------------------------------------------------------- 決める数（keikan_render.py と同じ）
DAY = datetime.datetime(2026, 11, 5, 10, 0)
NIGHT = datetime.datetime(2026, 11, 5, 21, 0)   # 夜は太陽を地平の下にも置く（消すのが効かない Rhino があった）
LAT, LON, TZ = 35.049106, 135.785095, 9.0
PASSES = 400                                    # 表示モードの書き出し（予備）の回数
LED_LAYERS = ("50b_越屋根_LED", "29_西館_越屋根_LED")   # 本館・西館の越屋根
LED_COLOR = System.Drawing.Color.FromArgb(255, 217, 138)
LED_LIGHT_POWER = 1.0                           # LED の線の光源の強さ。軒が暗ければ 2〜5、白く飛べば 0.3〜0.5
LED_LIGHT_DROP = 60.0                           # 線の光源を LED の帯の下端からどれだけ下に置くか（mm）
LED_LEN_MIN, LED_LEN_MAX = 500.0, 200000.0      # 線の光源の長さがこの外なら置かない（mm）
# 夜の切り替え（Rhino が落ちるときは一つずつ False にして、どれが原因かを見る。10-29 夜）
USE_LED_LIGHTS = False                          # LED のレイヤーごとに線の光源を1本（本館・西館の2本）。Mac の Cycles で落ちた 10-29、使わない
USE_LED_MATERIAL = False                        # LED の帯に光る材料（RenderMaterial）。10-29 から 3dm の中で発光の材料が当たる（materials.json「越屋根の LED（発光）」、監修 5b61cfc）ので差し替えない
USE_SKYLIGHT_DIM = True                         # スカイライトを消さずにごく弱く（SKYLIGHT_NIGHT）。強さを変えられなければ消す
SKYLIGHT_NIGHT = 0.05                           # 夜のスカイライトの強さ（建物の陰が真っ黒なら 0.1〜0.2、明るすぎれば 0.02）
USE_MOON = True                                 # 月明かり：ごく弱い青白い平行光を1本。光源が一つも無いと Rhino が既定の照明を点け、昼のように明るくなる
MOON_POWER = 0.15                               # 月明かりの強さ（建物が明るすぎれば 0.05〜0.1、暗すぎれば 0.3）
MOON_COLOR = System.Drawing.Color.FromArgb(0xAF, 0xC3, 0xE6)    # 青白い
MOON_AZ, MOON_ALT = 135.0, 40.0                 # 月の向き（北から時計回りの方位、南東）と高さ角（度）
USE_SKY_BG = True                               # 背景を群青の一色に
NIGHT_SKY = System.Drawing.Color.FromArgb(0x1E, 0x2A, 0x5A)     # 夜の空：暗い群青（前は #4C6CB3）
SKY_TOP = System.Drawing.Color.FromArgb(0xC9, 0xDC, 0xEC)       # 昼の空：淡い青（上）
SKY_BOTTOM = System.Drawing.Color.FromArgb(0xEE, 0xF2, 0xF4)    # 地平の近く：ほぼ白
CONTEXT_COLOR = System.Drawing.Color.FromArgb(0xD9, 0xD6, 0xCF)  # 周りの建物（PLATEAU）：淡い暖かい灰
CONTEXT_LAYER = u"04_周辺_建物"
TRANSPARENT_DAY = ("keikan",)                   # 昼の背景を透明にする名前（mock.py が空を塗る）。ほかは淡い空で不透明

NAMES = [(u"keikan", u"keikan＝沿川の景観"), (u"me", u"me＝透視図（公園の角）"), (u"choukan", u"choukan＝鳥瞰"),
         (u"*", u"その他（名前を文字で入れる。例 naibu_4sai）")]
SIZES = [((3508, 2480), u"A4横 3508×2480"), ((4252, 1701), u"横長 2.5:1 4252×1701"),
         (None, u"今のビューの縦横比で長辺4252")]
# mock.py が読む名前：沿川の景観は keikan_hiru.png・keikan_yoru.png、透視図は me.png、鳥瞰は choukan.png
DAY_PLAIN = ("me", "choukan")                   # 昼は <名前>.png（_hiru を付けない）

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
OUT = os.path.join(HERE, "out")


def say(*a):
    print(u" ".join([x if isinstance(x, type(u"")) else (x.decode("utf-8") if isinstance(x, bytes) else u"%s" % (x,)) for x in a]))


def stage(*a):
    """段の名をコマンド行に出し、画面に出してから進む（落ちたとき、どこまで来たかが残る）"""
    say(u"段：", *a)
    try:
        Rhino.RhinoApp.Wait()
    except Exception:
        pass


def ask():
    """名前と大きさを聞く。やめたら None"""
    import rhinoscriptsyntax as rss
    labels = [l for _, l in NAMES]
    got = rss.ListBox(labels, u"名前（書き出すファイルの頭）", u"レンダリング")
    if got is None:
        return None
    name = [n for n, l in NAMES if l == got][0]
    if name == "*":
        name = rss.StringBox(u"名前（英数字と _、例 naibu_4sai）", u"", u"レンダリング")
        if not name:
            return None
        name = name.strip().replace(" ", "_")
    labels = [l for _, l in SIZES]
    got = rss.ListBox(labels, u"大きさ（画素）", u"レンダリング", labels[0])
    if got is None:
        return None
    size = [s for s, l in SIZES if l == got][0]
    return name, size


def out_name(name, mode):
    if mode == "hiru" and name in DAY_PLAIN:
        return name + ".png"
    return u"%s_%s.png" % (name, mode)


def run(mode):
    """mode："hiru"（昼）か "yoru"（夜）"""
    doc = sc.doc
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    a_ = ask()
    if a_ is None:
        say(u"やめた")
        return
    name, size = a_
    view = doc.Views.ActiveView
    vp = view.ActiveViewport
    cw, ch = vp.Size.Width, vp.Size.Height
    if size is None:
        if cw >= ch:
            size = (4252, int(round(4252.0 * ch / cw)))
        else:
            size = (int(round(4252.0 * cw / ch)), 4252)
    W, H = size

    # ---------------------------------------------------------------- ビュー（動かさない。カメラを書き、名前付きビューに残す）
    saved_mode = vp.DisplayMode
    _c, _t = vp.CameraLocation, vp.CameraTarget
    two = False
    try:
        two = bool(vp.IsTwoPointPerspectiveProjection)
    except Exception:
        pass
    persp = vp.IsPerspectiveProjection or two
    lens = None
    try:
        lens = round(vp.Camera35mmLensLength, 2)
    except Exception:
        pass
    info = dict(name=name, projection="perspective" if persp else "parallel", two_point=two,
                camera_mm=[round(_c.X), round(_c.Y), round(_c.Z)], target_mm=[round(_t.X), round(_t.Y), round(_t.Z)],
                up=[round(vp.CameraUp.X, 4), round(vp.CameraUp.Y, 4), round(vp.CameraUp.Z, 4)],
                lens_mm=lens, px=[W, H], viewport_px=[cw, ch], named_view=name,
                made=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                note=u"3dm の mm。今のビューのまま描いた（render_%s.py）" % mode)
    if lens:
        info["hfov_deg"] = round(2 * math.degrees(math.atan(18.0 / lens)), 1)
    if not persp:
        say(u"今のビューは平行投影（透視ではない）。そのまま描く")
    try:
        k_ = doc.NamedViews.FindByName(name)
        if k_ >= 0:
            doc.NamedViews.Delete(k_)
        doc.NamedViews.Add(name, vp.Id)
        say(u"名前付きビューに残した：", name)
    except Exception as e:
        say(u"名前付きビュー：効かなかった", e)
    json.dump(info, open(os.path.join(OUT, u"%s_view.json" % name), "w"), indent=1, ensure_ascii=False)
    # 昼はレイトレースの表示で（前のとおり）。夜は、光源・材料・スカイライト・背景を変えるあいだと描くあいだ、
    # シェーディング（無ければワイヤーフレーム）にしておく（レイトレースの表示のまま変えると落ちることがあった、10-29 夜）
    want = ("raytrac",) if mode == "hiru" else ("shaded", "wireframe")
    stage(u"表示を切り替える：", want[0])
    for w_ in want:
        m_hit = [m for m in Rhino.Display.DisplayModeDescription.GetDisplayModes() if m.EnglishName.lower().startswith(w_)]
        if m_hit:
            try:
                vp.DisplayMode = m_hit[0]
                view.Redraw()
            except Exception as e:
                say(u"  表示の切り替え：効かなかった", e)
            break

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

    def set_sun(on, when):
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
            doc.RenderSettings = rs
        except Exception:
            pass

    def sky_get():
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
        tried = []
        try:
            sk = rs.Skylight
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
                rs.Skylight = sk
            except Exception:
                pass
            doc.RenderSettings = rs
            tried.append(u"RenderSettings.Skylight")
        except Exception as e:
            say(u"  スカイライト（RenderSettings.Skylight）：", e)
        if sky_get() != on:
            try:
                rs.SkylightEnabled = on
                doc.RenderSettings = rs
                tried.append(u"SkylightEnabled")
            except Exception as e:
                say(u"  スカイライト（SkylightEnabled）：", e)
        if sky_get() != on:
            try:
                doc.Lights.Skylight.Enabled = on
                tried.append(u"Lights.Skylight")
            except Exception as e:
                say(u"  スカイライト（Lights.Skylight）：", e)
        now = sky_get()
        if now == on:
            say(u"スカイライト：", u"点けた" if on else u"消した", u"（", u"・".join(tried), u"）")
        else:
            say(u"スカイライト：効かなかった（いま", now, u"）。レンダリングのパネルの「スカイライト」を手で",
                u"オンに" if on else u"オフに")

    sky_int_old = []                                     # (物, 名前, 前の値)：終わったら戻す

    def dim_skylight(val):
        """スカイライトの強さを val に。版で名前が違うので試す。効かなければ消す"""
        for get_obj, key in ((lambda: rs.Skylight, "Intensity"), (lambda: rs, "SkylightIntensity"),
                             (lambda: doc.Lights.Skylight, "Intensity")):
            try:
                obj = get_obj()
                old = getattr(obj, key)
                setattr(obj, key, val)
                try:
                    rs.Skylight = obj if key == "Intensity" and obj is not rs else rs.Skylight
                except Exception:
                    pass
                doc.RenderSettings = rs
                sky_int_old.append((get_obj, key, old))
                set_skylight(True)
                say(u"スカイライトを弱くした：", key, old, u"→", val)
                return
            except Exception:
                continue
        say(u"スカイライトの強さを変えられなかった。消す")
        set_skylight(False)

    def restore_skylight_int():
        for get_obj, key, old in reversed(sky_int_old):
            try:
                obj = get_obj()
                setattr(obj, key, old)
                try:
                    if obj is not rs:
                        rs.Skylight = obj
                except Exception:
                    pass
                doc.RenderSettings = rs
            except Exception as e:
                say(u"  スカイライトの強さを戻せなかった：", e)

    def add_moon():
        """月明かり：青白い平行光を1本（led_lights に入れ、終わったら一緒に消す）"""
        az, al = math.radians(MOON_AZ), math.radians(MOON_ALT)
        toward = Rhino.Geometry.Vector3d(math.sin(az) * math.cos(al), math.cos(az) * math.cos(al), math.sin(al))  # 月の方へ
        try:
            lt = Rhino.Geometry.Light()
            lt.LightStyle = Rhino.Geometry.LightStyle.WorldDirectional
            lt.Location = Rhino.Geometry.Point3d(toward.X * 100000.0, toward.Y * 100000.0, toward.Z * 100000.0)
            lt.Direction = -toward
            lt.Diffuse = MOON_COLOR
            lt.Intensity = MOON_POWER
            try:
                lt.IsEnabled = True
            except Exception:
                pass
            try:
                lt.Name = u"作業_レンダ_月明かり"
            except Exception:
                pass
            k_ = doc.Lights.Add(lt)
            if k_ >= 0:
                led_lights.append(doc.Lights[k_].Id)
                say(u"月明かりを置いた（強さ", MOON_POWER, u"）")
            else:
                say(u"月明かり：足せなかった")
        except Exception as e:
            say(u"月明かり：効かなかった", e)

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

    def sky(top, bottom, style_name):
        vals = dict(BackgroundColorTop=top, BackgroundColorBottom=bottom)
        try:
            vals["BackgroundStyle"] = getattr(Rhino.Display.BackgroundStyle, style_name)
        except Exception:
            pass
        bg_set(vals)

    def render_to(path, transparent):
        old = {}
        for k in ("UseViewportSize", "ImageSize", "TransparentBackground"):
            try:
                old[k] = getattr(rs, k)
            except Exception:
                pass
        try:
            rs.UseViewportSize = False
            rs.ImageSize = System.Drawing.Size(W, H)
            rs.TransparentBackground = transparent
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

    def capture(fname, transparent):
        path = os.path.join(OUT, fname)
        if os.path.exists(path):
            os.remove(path)
        say(u"書き出し：", fname, u"ビュー", cw, u"×", ch, u"→", W, u"×", H)
        if render_to(path, transparent):
            say(u"  レンダリングで書いた：", path)
            return
        say(u"  レンダリングで書けなかった。表示モードの書き出し（不透明）で")
        for w, h in ((W, H), (W // 2, H // 2)):
            bmp = None
            try:
                vc = Rhino.Display.ViewCapture()
                vc.Width, vc.Height = w, h
                vc.ScaleScreenItems = False
                vc.DrawAxes = vc.DrawGrid = vc.DrawGridAxes = False
                vc.TransparentBackground = False
                try:
                    vc.RealtimeRenderPasses = PASSES
                except Exception:
                    pass
                bmp = vc.CaptureToBitmap(view)
            except Exception as e:
                say(u"  ViewCapture の誤り：", e)
            if bmp is not None:
                bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png)
                say(u"  書いた：", path, w, u"×", h)
                return
            say(u"  通らなかった：", w, u"×", h)

    # ---------------------------------------------------------------- 一時的な変更（終わったら戻す）
    # 0）周りの建物（PLATEAU）のレイヤーと親を表示し、淡い暖かい灰に
    ctx_idx, ctx_old = set(), []
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
        m_.Name = u"作業_レンダ_" + lay.Name
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

    # 2）夜の LED：光る材料（RenderMaterial）と、レイヤーごとに1本の線の光源
    led_objs, old_attr, led_lights, led_rm, led_layers = [], [], [], None, []
    sky_old = sky_get()
    if mode == "yoru":
        led_layers = [lay for lay in doc.Layers if lay.Name in LED_LAYERS]
        for lay in led_layers:
            led_objs += list(doc.Objects.FindByLayer(lay) or [])
        say(u"LED のレイヤー：", len(led_layers), u"／物：", len(led_objs))

    def make_led_material():
        """発光の色を持つ RenderMaterial を作って文書に足す。作れなければ None"""
        m_ = Rhino.DocObjects.Material()
        m_.Name = u"作業_レンダ_LED"
        m_.DiffuseColor = LED_COLOR
        m_.EmissionColor = LED_COLOR
        rm = None
        for f in (lambda: Rhino.Render.RenderMaterial.CreateBasicMaterial(m_, doc),
                  lambda: Rhino.Render.RenderMaterial.CreateBasicMaterial(m_)):
            try:
                rm = f()
                if rm is not None:
                    break
            except Exception as e:
                say(u"  CreateBasicMaterial：", e)
        if rm is None:
            return None
        try:
            rm.Name = u"作業_レンダ_LED"
        except Exception:
            pass
        try:
            if not doc.RenderMaterials.Add(rm):
                say(u"  RenderMaterials.Add：足せなかった")
                return None
        except Exception as e:
            say(u"  RenderMaterials.Add：", e)
            return None
        return rm

    def add_led_lights():
        """LED のレイヤーごとに、全部の物を合わせた範囲の長い向きに沿って線の光源を1本、帯の少し下に置く"""
        n_ = 0
        for lay in led_layers:
            bb = Rhino.Geometry.BoundingBox.Empty
            for o in (doc.Objects.FindByLayer(lay) or []):
                try:
                    b_ = o.Geometry.GetBoundingBox(True)
                    if b_.IsValid:
                        bb.Union(b_)
                except Exception:
                    pass
            if not bb.IsValid:
                say(u"  ", lay.Name, u"：範囲が無い")
                continue
            dx, dy = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
            cx, cy = (bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2
            z = bb.Min.Z - LED_LIGHT_DROP
            if dx >= dy:
                a_, b_ = Rhino.Geometry.Point3d(bb.Min.X, cy, z), Rhino.Geometry.Point3d(bb.Max.X, cy, z)
            else:
                a_, b_ = Rhino.Geometry.Point3d(cx, bb.Min.Y, z), Rhino.Geometry.Point3d(cx, bb.Max.Y, z)
            L_ = a_.DistanceTo(b_)
            if L_ < LED_LEN_MIN or L_ > LED_LEN_MAX:
                say(u"  ", lay.Name, u"：長さ", round(L_), u"mm は外れるので置かない")
                continue
            try:
                lt = Rhino.Geometry.Light()
                lt.LightStyle = Rhino.Geometry.LightStyle.WorldLinear
                lt.Location = a_
                lt.Length = b_ - a_
                lt.Direction = Rhino.Geometry.Vector3d(0, 0, -1)
                lt.Diffuse = LED_COLOR
                lt.Intensity = LED_LIGHT_POWER
                try:
                    lt.IsEnabled = True
                except Exception:
                    pass
                try:
                    lt.Name = u"作業_レンダ_LED光源"
                except Exception:
                    pass
                k_ = doc.Lights.Add(lt)
                if k_ >= 0:
                    led_lights.append(doc.Lights[k_].Id)
                    n_ += 1
                    say(u"  ", lay.Name, u"：長さ", round(L_), u"mm")
            except Exception as e:
                say(u"  LED の線の光源：効かなかった", e)
        say(u"LED の線の光源を置いた：", n_, u"本（強さ", LED_LIGHT_POWER, u"）")

    fname = out_name(name, mode)
    try:
        if mode == "hiru":
            set_sun(True, DAY)
            transparent = name in TRANSPARENT_DAY
            if not transparent:
                sky(SKY_TOP, SKY_BOTTOM, "Gradient")
            view.Redraw()
            capture(fname, transparent)
        else:
            if USE_LED_MATERIAL and led_objs:
                stage(u"LED の光る材料")
                led_rm = make_led_material()
                if led_rm is None:
                    say(u"光る材料を作れなかった。材料は当てずに、線の光源だけで描く")
                else:
                    for o in led_objs:
                        try:
                            at_ = o.Attributes.Duplicate()
                            old_attr.append((o.Id, o.Attributes.Duplicate()))
                            at_.RenderMaterial = led_rm
                            at_.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
                            doc.Objects.ModifyAttributes(o.Id, at_, True)
                        except Exception as e:
                            say(u"  光る材料を当てられなかった：", e)
                            break
                    say(u"光る材料を当てた：", len(old_attr))
            stage(u"太陽を消す")
            set_sun(False, NIGHT)
            if USE_SKYLIGHT_DIM:
                stage(u"スカイライトをごく弱く：", SKYLIGHT_NIGHT)
                dim_skylight(SKYLIGHT_NIGHT)
            if USE_SKY_BG:
                stage(u"背景を群青に")
                sky(NIGHT_SKY, NIGHT_SKY, "SolidColor")
            if USE_LED_LIGHTS:
                stage(u"LED の線の光源")
                add_led_lights()
            if USE_MOON:
                stage(u"月明かりを足す")
                add_moon()
                stage(u"月明かりを足した")
            say(u"夜を描く前：スカイライト", sky_get(), u"／光源", doc.Lights.Count)
            view.Redraw()
            stage(u"描く（Render）")
            capture(fname, False)
            stage(u"描き終わった。戻す")
    finally:
        for lid in led_lights:
            try:
                lt = doc.Lights.FindId(lid)
                if lt is not None:
                    doc.Lights.Delete(lt.Index, True)
            except Exception as e:
                say(u"  LED の光源を消せなかった：", e)
        for oid, at_ in old_attr:
            doc.Objects.ModifyAttributes(oid, at_, True)
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
        if led_rm is not None:
            try:
                doc.RenderMaterials.Remove(led_rm)
            except Exception as e:
                say(u"  光る材料を消せなかった：", e)
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
            try:
                doc.RenderSettings = rs
            except Exception:
                pass
        if bg_old:
            bg_set(bg_old)
        restore_skylight_int()
        if sky_old is not None and sky_get() != sky_old:
            set_skylight(sky_old)
        try:
            vp.DisplayMode = saved_mode
        except Exception:
            pass
        doc.Views.Redraw()
    say(u"おわり。out/ の", fname, u"・", u"%s_view.json" % name, u"を push してください")
