# -*- coding: utf-8 -*-
"""前に描いた絵の視点に、今のビューを戻す（プレゼンの準備、10-30）

git pull で sodachiya.3dm が作り直されると、名前付きビューは消える。render_hiru.py・render_yoru.py は描くたびに
カメラの記録を out/<名前>_view.json に書いているので、それを読んで今のビューを同じ視点にする。

使い方（Rhino 8、Mac）：
  1. sodachiya/sodachiya.3dm を開き、戻したいビュー（Perspective など）をクリックしてアクティブにする。
  2. ツール→スクリプト→実行…（またはコマンド RunPythonScript）で、このファイルを選ぶ。
  3. out/ にある記録（keikan・me・choukan・ほか）から一つ選ぶ。カメラ・ターゲット・上の向き・レンズの長さ・
     投影（透視／2点透視／平行）が戻り、同じ名前の名前付きビューも作り直す。
  4. そのまま render_hiru.py か render_yoru.py を走らせ、同じ名前を選ぶ。
  画面の縦横比は記録と違うことがある（絵の大きさはレンダリングの側で決まるので、写る範囲は同じになる）。
"""
import os
import json
import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Users/kida/Developer/atelier/sodachiya/present/rhino"
OUT = os.path.join(HERE, "out")


def say(*a):
    Rhino.RhinoApp.WriteLine(u" ".join(u"%s" % x for x in a))


def main():
    doc = sc.doc
    if not os.path.isdir(OUT):
        say(u"out/ が無い：", OUT)
        return
    names = sorted(f[:-len("_view.json")] for f in os.listdir(OUT) if f.endswith("_view.json"))
    if not names:
        say(u"out/ に *_view.json が無い（まだ render_hiru/yoru で描いていない）")
        return
    name = rs.ListBox(names, u"どの視点に戻しますか", u"視点を戻す") if len(names) > 1 else names[0]
    if not name:
        return
    info = json.load(open(os.path.join(OUT, name + "_view.json")))
    if "camera_mm" not in info or "target_mm" not in info:
        say(u"この記録にはカメラが無い（前の平行投影の書式）：", name)
        return
    view = doc.Views.ActiveView
    vp = view.ActiveViewport
    cam = Rhino.Geometry.Point3d(*info["camera_mm"])
    tgt = Rhino.Geometry.Point3d(*info["target_mm"])
    if info.get("projection") == "parallel":
        vp.ChangeToParallelProjection(True)
    else:
        vp.ChangeToPerspectiveProjection(True, info.get("lens_mm") or 50.0)
        if info.get("two_point"):
            try:
                vp.ChangeToTwoPointPerspectiveProjection(info.get("lens_mm") or 50.0)
            except Exception as e:
                say(u"  2点透視にできなかった：", e)
    vp.SetCameraLocations(tgt, cam)
    up = info.get("up")
    if up:
        try:
            vp.CameraUp = Rhino.Geometry.Vector3d(*up)
        except Exception:
            pass
    if info.get("lens_mm") and info.get("projection") != "parallel":
        try:
            vp.Camera35mmLensLength = info["lens_mm"]
        except Exception as e:
            say(u"  レンズの長さを戻せなかった：", e)
    view.Redraw()
    # 名前付きビューも作り直す（同じ名前があれば置き換え）
    try:
        k = doc.NamedViews.FindByName(name)
        if k >= 0:
            doc.NamedViews.Delete(k)
        doc.NamedViews.Add(name, vp.Id)
    except Exception as e:
        say(u"  名前付きビューを作れなかった：", e)
    say(u"視点を戻した：", name, u"／カメラ", info["camera_mm"], u"ターゲット", info["target_mm"],
        u"レンズ", info.get("lens_mm"), u"mm", u"（2点透視）" if info.get("two_point") else u"")


main()
