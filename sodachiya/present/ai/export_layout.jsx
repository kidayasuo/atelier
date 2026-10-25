// 育ち舎のプレゼン：今開いている .ai から、部品の位置・大きさと、書き換えた文字を layout_user.json に書き出す
// （書き出したら、atelier のフォルダで git add・commit・push。次の更新で mock.py がこの割付をもとにする）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    if (app.documents.length === 0) { alert("育ち舎の .ai を開いてから実行してください。"); return; }
    var doc = app.activeDocument, K = SDY.K;
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var L = null;
    try { L = SDY.readJSON(File(SDY.here.fsName + "/layout.json")); } catch (e) { L = null; }
    var out = { note: "Illustratorから export_layout.jsx が書き出した。ユーザーの割付（位置・大きさ・書き換えた文字・消した部品）。", parts: {} };
    var found = {}, i, it, t, b, ai, r, rec, k, n = 0, edited = 0;
    var bad = [];
    for (i = 0; i < doc.pageItems.length; i++) {
      try {
        it = doc.pageItems[i];
        t = SDY.parseTag(it);
        if (!t || found[t.id]) { continue; }
        found[t.id] = true;
        rec = {};
        if (t.kind === "text" && it.typename === "TextFrame" && it.kind === TextType.POINTTEXT) {
            b = it.geometricBounds; ai = SDY.abOf(doc, b);
            if (ai < 0) { continue; }
            r = SDY.ab(doc, ai);
            rec.x = (it.anchor[0] - r[0]) / K; rec.y = (r[1] - it.anchor[1]) / K;
        } else if (t.kind === "area" && it.typename === "TextFrame") {
            b = null; try { b = it.textPath.geometricBounds; } catch (e) {} if (!b) { b = it.geometricBounds; } ai = SDY.abOf(doc, b);
            if (ai < 0) { continue; }
            r = SDY.ab(doc, ai);
            rec.x = (b[0] - r[0]) / K; rec.y = (r[1] - b[1]) / K; rec.w = (b[2] - b[0]) / K; rec.h = (b[1] - b[3]) / K;
        } else if (t.kind === "line") {
            b = it.geometricBounds; ai = SDY.abOf(doc, b);
            if (ai < 0) { continue; }
            r = SDY.ab(doc, ai);
            var pi = (it.typename === "GroupItem") ? it.pathItems[it.pathItems.length - 1] : it;   // 線（点の丸ではない方）
            for (k = 0; k < it.pathItems.length; k++) { if (it.pathItems[k].pathPoints.length > 2 || !it.pathItems[k].closed) { pi = it.pathItems[k]; } }
            rec.pts = [];
            for (k = 0; k < pi.pathPoints.length; k++) {
                var a = pi.pathPoints[k].anchor;
                rec.pts.push([(a[0] - r[0]) / K, (r[1] - a[1]) / K]);
            }
        } else {                                       // link（切り抜きのグループは切り抜きの四角）・box
            b = it.geometricBounds;
            if (it.typename === "GroupItem" && it.clipped) {
                for (k = 0; k < it.pathItems.length; k++) { if (it.pathItems[k].clipping) { b = it.pathItems[k].geometricBounds; } }
            }
            ai = SDY.abOf(doc, b);
            if (ai < 0) { continue; }
            r = SDY.ab(doc, ai);
            rec.x = (b[0] - r[0]) / K; rec.y = (r[1] - b[1]) / K; rec.w = (b[2] - b[0]) / K; rec.h = (b[1] - b[3]) / K;
        }
        rec.artboard = ai + 1;
        if ((t.kind === "text" || t.kind === "area") && it.typename === "TextFrame") {
            if (SDY.hash(it.contents) !== t.mock_hash) { rec.s = SDY.norm(it.contents); edited++; }   // 書き換えた文字だけ
        }
        out.parts[t.id] = rec; n++;
      } catch (e) { bad.push((t ? t.id : ("物 " + i)) + "（" + e.message + "）"); }
    }
    var gone = 0, j, p;                                // layout.json にあって .ai に無い部品＝消したもの
    if (L) {
        for (i = 0; i < L.pages.length; i++) {
            for (j = 0; j < L.pages[i].parts.length; j++) {
                p = L.pages[i].parts[j];
                if (!found[p.id]) { out.parts[p.id] = { hidden: true }; gone++; }
            }
        }
    }
    var ui = SDY.userItems(doc), q;                    // 木田さんが足した物も台帳に（プレゼンの準備が読む）
    out.user_items = [];
    for (q = 0; q < ui.length; q++) { try { out.user_items.push(SDY.describe(doc, ui[q])); } catch (e2) {} }
    SDY.writeText(File(SDY.here.fsName + "/layout_user.json"), SDY.stringify(out));
    alert("書き出しました：部品 " + n + " 個、木田さんが足した物 " + out.user_items.length + " 個（書き換えた文字 " + edited + "、消した部品 " + gone + "）\n" + SDY.here.fsName + "/layout_user.json\n\natelier で git add・commit・push してください。" + (bad.length ? "\n\n書き出せなかった部品（位置は前のまま）：\n" + bad.slice(0, 15).join("\n") : ""));
})();
