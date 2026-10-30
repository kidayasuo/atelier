// 育ち舎のプレゼン：layout.json から .ai を組む（Illustrator → ファイル → スクリプト → その他のスクリプト… でこのファイルを選ぶ）
// できたファイルは同じフォルダの sodachiya_present.ai（すでにあれば日時の付いた名前で、上書きしない）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    var L = SDY.readJSON(File(SDY.here.fsName + "/layout.json"));
    var K = SDY.K, n = L.pages.length;
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var doc = app.documents.add(DocumentColorSpace.RGB, L.artboard[0] * K, L.artboard[1] * K, n,
                                DocumentArtboardLayout.GridByRow, 30 * K, 3);
    // アートボードは壁に貼るときと同じ並び（先生のエスキス 10-30、ユーザー）：2段×3列、上の段1・3・5、下の段2・4・6（[列, 段]）
    var GAP = 30 * K, AW = L.artboard[0] * K, AH = L.artboard[1] * K;
    var PLACE = { 1: [0, 0], 2: [0, 1], 3: [1, 0], 4: [1, 1], 5: [2, 0], 6: [2, 1] };
    for (i = 0; i < n; i++) {
        var cr = PLACE[L.pages[i].no] || [i, 0];
        var x0 = cr[0] * (AW + GAP), y0 = -cr[1] * (AH + GAP);
        doc.artboards[i].artboardRect = [x0, y0, x0 + AW, y0 - AH];
    }
    var first = doc.layers[0];
    var names = ["枠", "図", "線", "説明", "注記"], i, j, p, made = 0, skipped = 0;
    for (i = 0; i < names.length; i++) { SDY.layer(doc, names[i]); }        // 下から 枠・図・線・説明・注記
    for (i = 0; i < n; i++) { doc.artboards[i].name = L.pages[i].no + "/" + n; }
    try { SDY.makeFrame(doc, L); } catch (e) { SDY.missing.push("枠（" + e.message + "）"); }
    for (i = 0; i < n; i++) {
        for (j = 0; j < L.pages[i].parts.length; j++) {
            p = L.pages[i].parts[j];
            if (p.hidden) { skipped++; continue; }
            try { if (SDY.make(doc, i, p)) { made++; } else { SDY.failed[p.id] = 1; } } catch (e) { SDY.failed[p.id] = 1; SDY.missing.push(p.id + "（" + e.message + "）"); }
        }
    }
    try { SDY.groupBoxes(doc); } catch (e) { SDY.missing.push("箱のまとめ（" + e.message + "）"); }
    var note = SDY.layer(doc, "注記");
    note.printable = false;                          // 割付の注記は見えるが印刷しない
    try { if (first.pageItems.length === 0 && first.name !== "枠") { first.remove(); } } catch (e) {}
    var out = File(SDY.here.fsName + "/sodachiya_present.ai");
    var carried = 0, drawnU = 0, U = null, known = {}, q;
    // 木田さんが足した物は layout_user.json の user_items から描き直す（正本、10-29：build で消えない）
    try { var uf = File(SDY.here.fsName + "/layout_user.json"); if (uf.exists) { U = SDY.readJSON(uf); } } catch (e) { SDY.missing.push("layout_user.json を読めなかった（" + e.message + "）"); }
    if (U) {
        for (q = 0; q < (U.user_items || []).length; q++) { if (U.user_items[q].key) { known[U.user_items[q].key] = true; } }
        for (q = 0; q < (U.deleted_user || []).length; q++) { if (U.deleted_user[q].key) { known[U.deleted_user[q].key] = true; } }
        try { drawnU = SDY.drawUserItems(doc, L, U); } catch (e) { SDY.missing.push("足した物（" + e.message + "）"); }
    }
    if (out.exists) {                                  // 前の .ai にある木田さんの物（印の無い物）を新しい .ai へ写す（ユーザー、10-26）
        try {
            var RM = SDY.oldNumbering(L);
            if (RM) {                                  // 前の .ai は前の番号のまま（10-28 の振り直し）：木田さんの物を新しい番号の枚へ
                SDY.abMap = function (a) { var nn = RM[String(a + 1)]; return nn ? nn - 1 : a; };
            }
            var oldDoc = app.open(out);
            // 配置図が紙の上で動いたか：前の .ai の配置図の原点（素材01aの左上＋素材の中の原点の位置）と、新しい layout.json の目印の原点（10-28：.ai で測る）。
            // 測れなければ、前に組んだときの目印（layout_built.json、無ければ layout.json の anchors_prev）
            var bf = File(SDY.here.fsName + "/layout_built.json"), OB = null, an = L.anchors ? L.anchors["p1.siteplan"] : null, ao = null, ab1 = -1;
            try { if (bf.exists) { OB = SDY.readJSON(bf); } } catch (e) {}
            ao = (OB && OB.anchors && OB.anchors["p1.siteplan"]) || (L.anchors_prev ? L.anchors_prev["p1.siteplan"] : null);
            for (i = 0; i < n; i++) { if (L.pages[i].no === 1) { ab1 = i; } }
            var po = SDY.planOrigin(oldDoc, ao, an);
            if (po) { ao = { origin: po.origin, window: po.window || (ao ? ao.window : null) }; }
            if (an && ao && ao.window && ab1 >= 0) {
                SDY.planShift = { ab: ab1, win: ao.window, dx: an.origin[0] - ao.origin[0], dy: an.origin[1] - ao.origin[1], n: 0 };
            }
            carried = SDY.copyUserItems(oldDoc, doc, known);   // まだ書き出していない物だけ（補助）
            oldDoc.close(SaveOptions.DONOTSAVECHANGES);
            app.activeDocument = doc;
        } catch (e) { SDY.missing.push("前の .ai を開けなかった（" + e.message + "）"); }
    }
    try { SDY.groupPlan(doc, L); } catch (e) { SDY.missing.push("配置図のまとめ（" + e.message + "）"); }
    try { SDY.groupDrawings(doc, L); } catch (e) { SDY.missing.push("図面のまとめ（" + e.message + "）"); }
    try { SDY.applyOrder(doc, L); SDY.applyStacking(doc, U); } catch (e) { SDY.missing.push("重ね順（" + e.message + "）"); }   // 重ね順：決め打ち → 書き出した並び（10-29）
    if (out.exists) {                                  // 前のファイルは old/ に日時を付けて退け、同じ名前で保存する（ユーザー、10-26：名前が増えていく）
        var d = new Date();
        var st = d.getFullYear() + ("0" + (d.getMonth() + 1)).slice(-2) + ("0" + d.getDate()).slice(-2) + "-" + ("0" + d.getHours()).slice(-2) + ("0" + d.getMinutes()).slice(-2);
        var od = Folder(SDY.here.fsName + "/old"); if (!od.exists) { od.create(); }
        if (confirm("sodachiya_present.ai を新しく組んだもので置き換えます。\n前のファイルは old/sodachiya_present_" + st + ".ai に移します。\n（いいえ：日時を付けた別の名前で保存）")) {
            if (!out.copy(od.fsName + "/sodachiya_present_" + st + ".ai")) { alert("前のファイルを old/ に移せませんでした。開いたままなら閉じてから、もう一度。"); return; }
            out.remove();
            out = File(SDY.here.fsName + "/sodachiya_present.ai");
        } else {
            out = File(SDY.here.fsName + "/sodachiya_present_" + st + ".ai");
        }
    }
    doc.saveAs(out, new IllustratorSaveOptions());
    try { File(SDY.here.fsName + "/layout.json").copy(SDY.here.fsName + "/layout_built.json"); } catch (e) {}   // 組んだときの位置（書き出しで、動かした部品だけを残すため）
    var msg = "組みました：" + made + " 個（隠した " + skipped + " 個）、前の .ai から写した木田さんの物 " + carried + " 個\n" + out.fsName;
    if (SDY.planShift && SDY.planShift.n && (Math.abs(SDY.planShift.dx) > 0.05 || Math.abs(SDY.planShift.dy) > 0.05)) { msg += "\n配置図の上の物 " + SDY.planShift.n + " 個を、配置図と一緒に " + Math.round(SDY.planShift.dx) + "・" + Math.round(SDY.planShift.dy) + " mm 動かしました"; }
    if (SDY.missing.length) { msg += "\n\n見つからない・作れなかったもの：\n" + SDY.missing.join("\n"); }
    if (!SDY.font("W3")) { msg += "\n\nヒラギノ角ゴシックが見つからないので、書体は既定のままです。"; }
    SDY.writeFailed();
    alert(msg);
})();
