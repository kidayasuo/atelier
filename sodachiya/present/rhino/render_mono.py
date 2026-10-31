# -*- coding: utf-8 -*-
"""教室・居場所の切断を、表示モード「モノクロ」で書き出す（プレゼンの準備、10-31。ユーザー：モノクロが輪郭がはっきりして見やすい）

使い方（Rhino 8、Mac）：
  1. atelier を pull して sodachiya/sodachiya.3dm を開き、Perspective のビューをクリックしてアクティブにする。
  2. RunPythonScript でこのファイルを選ぶ。二つ聞かれる：
     ①部屋：一つ、または「教室と居場所の5部屋まとめて」（room_3to5・room_01・room_2・room_dokusho・room_hako）
     ②大きさ：2400×1800（ふつう、2枚目に横60〜80 mm で刷る）／1600×1200（試し）／3200×2400
  3. 部屋ごとに、room_view.py と同じ準備（クリッピング平面で切る・屋根などを隠す・南東の上から見る）→ モノクロで書き出す →
     元に戻す、を続けて行う。選んだ物は書き出す前に選択を外す。
     書き出し：out/<部屋>_mono.png と、カメラを書いた out/<部屋>_mono_view.json。
  4. 終わったら push：git add sodachiya/present/rhino/out && git commit -m "[プレゼン] 部屋のモノクロ" && git push
  ・線の太さ：SCALE_SCREEN_ITEMS（下、始めは True＝画面で見る太さの割合のまま絵の大きさに合わせて太らせる）。
    細すぎれば大きさを1600×1200に、太すぎれば False に。
  ・モノクロの表示モードが見つからないときは、コマンド行に今ある表示モードの名前が出る。MONO_NAMES に足す。
3dm は変えない（保存しなくてよい）。
"""
import os
import io
import sys
import json
import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import room_view
try:
    from importlib import reload as _reload
except ImportError:
    _reload = reload    # IronPython 2
room_view = _reload(room_view)          # 直したら読み直す

OUT = os.path.join(_HERE, "out")
ROOMS5 = [u"room_3to5", u"room_01", u"room_2", u"room_dokusho", u"room_hako"]
SIZES = [((2400, 1800), u"2400×1800（ふつう）"), ((1600, 1200), u"1600×1200（試し）"), ((3200, 2400), u"3200×2400")]
MONO_NAMES = (u"Monochrome", u"モノクロ")     # 表示モードの名前（英語名・日本語名）
SCALE_SCREEN_ITEMS = True                       # 線と点を絵の大きさに合わせて太らせる（画面で見る太さの割合のまま）
HOW = u"クリッピング平面で切る（ふつう）"


def say(*a):
    Rhino.RhinoApp.WriteLine(u" ".join(u"%s" % x for x in a))


def mono_mode():
    modes = Rhino.Display.DisplayModeDescription.GetDisplayModes()
    for d in modes:
        if d.EnglishName in MONO_NAMES or d.LocalName in MONO_NAMES:
            return d
    say(u"モノクロの表示モードが見つからない。ある表示モード：", u"、".join(d.LocalName for d in modes))
    return None


def write_view(vp, name, W, H):
    d = dict(name=name + u"_mono", made=System.DateTime.Now.ToString("yyyy-MM-dd HH:mm"),
             camera_mm=[round(vp.CameraLocation.X), round(vp.CameraLocation.Y), round(vp.CameraLocation.Z)],
             target_mm=[round(vp.CameraTarget.X), round(vp.CameraTarget.Y), round(vp.CameraTarget.Z)],
             lens_mm=round(vp.Camera35mmLensLength, 2), px=[W, H], mode=u"モノクロ（render_mono.py）")
    with io.open(os.path.join(OUT, name + u"_mono_view.json"), "w", encoding="utf-8") as f_:
        f_.write(u"%s" % json.dumps(d, indent=1, ensure_ascii=False))


def capture(view, path, W, H):
    vc = Rhino.Display.ViewCapture()
    vc.Width, vc.Height = W, H
    vc.ScaleScreenItems = SCALE_SCREEN_ITEMS
    vc.DrawAxes = vc.DrawGrid = vc.DrawGridAxes = False
    vc.TransparentBackground = False
    bmp = vc.CaptureToBitmap(view)
    if bmp is None:
        return False
    bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png)
    return True


def main():
    doc = sc.doc
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    labels = [u"教室と居場所の5部屋まとめて"] + [l for n, l, _, _, _ in room_view.ROOMS]
    got = rs.ListBox(labels, u"部屋（モノクロで書き出す）", u"モノクロ")
    if got is None:
        return
    names = ROOMS5 if got == labels[0] else [n for n, l, _, _, _ in room_view.ROOMS if l == got]
    sl = [l for _, l in SIZES]
    gs = rs.ListBox(sl, u"大きさ（画素）", u"モノクロ", sl[0])
    if gs is None:
        return
    W, H = [s for s, l in SIZES if l == gs][0]
    mode = mono_mode()
    if mode is None:
        return
    view = doc.Views.ActiveView
    vp = view.ActiveViewport
    old_mode = vp.DisplayMode
    done = []
    try:
        rs.UnselectAllObjects()
        vp.DisplayMode = mode
        for n in names:
            say(u"—", n, u"：準備")
            room_view.setup(doc, n, HOW)
            rs.UnselectAllObjects()
            view.Redraw()
            path = os.path.join(OUT, n + u"_mono.png")
            if os.path.exists(path):
                os.remove(path)
            if capture(view, path, W, H):
                write_view(vp, n, W, H)
                done.append(n)
                say(u"  書いた：", path, W, u"×", H)
            else:
                say(u"  書けなかった：", n)
            room_view.save_state(room_view.restore(doc, room_view.load_state()))
    finally:
        try:
            room_view.save_state(room_view.restore(doc, room_view.load_state()))
        except Exception as e:
            say(u"  元に戻せなかった（room_view.py の「元に戻す」で）：", e)
        try:
            vp.DisplayMode = old_mode
        except Exception:
            pass
        doc.Views.Redraw()
    say(u"おわり：", len(done), u"枚（", u"、".join(done), u"）。out/ の *_mono.png を push してください")


main()
