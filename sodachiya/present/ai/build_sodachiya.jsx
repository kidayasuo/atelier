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
    // アートボードは壁に貼るときと同じ並び（ユーザー、10-26）：1の下に2、1の右に3、3の下に4、3の右に5
    var GAP = 30 * K, AW = L.artboard[0] * K, AH = L.artboard[1] * K;
    var PLACE = { 1: [0, 0], 2: [0, 1], 3: [1, 0], 4: [1, 1], 5: [2, 0] };
    for (i = 0; i < n; i++) {
        var cr = PLACE[L.pages[i].no] || [i, 0];
        var x0 = cr[0] * (AW + GAP), y0 = -cr[1] * (AH + GAP);
        doc.artboards[i].artboardRect = [x0, y0, x0 + AW, y0 - AH];
    }
    var first = doc.layers[0];
    var names = ["枠", "図", "線", "説明", "注記"], i, j, p, made = 0, skipped = 0;
    for (i = 0; i < names.length; i++) { SDY.layer(doc, names[i]); }        // 下から 枠・図・線・説明・注記
    for (i = 0; i < n; i++) { doc.artboards[i].name = L.pages[i].no + "/5"; }
    try { SDY.makeFrame(doc, L); } catch (e) { SDY.missing.push("枠（" + e.message + "）"); }
    for (i = 0; i < n; i++) {
        for (j = 0; j < L.pages[i].parts.length; j++) {
            p = L.pages[i].parts[j];
            if (p.hidden) { skipped++; continue; }
            try { if (SDY.make(doc, i, p)) { made++; } } catch (e) { SDY.missing.push(p.id + "（" + e.message + "）"); }
        }
    }
    try { SDY.groupBoxes(doc); } catch (e) { SDY.missing.push("箱のまとめ（" + e.message + "）"); }
    var note = SDY.layer(doc, "注記");
    note.printable = false;                          // 割付の注記は見えるが印刷しない
    try { if (first.pageItems.length === 0 && first.name !== "枠") { first.remove(); } } catch (e) {}
    var out = File(SDY.here.fsName + "/sodachiya_present.ai");
    var carried = 0;
    if (out.exists) {                                  // 前の .ai にある木田さんの物（印の無い物）を新しい .ai へ写す（ユーザー、10-26）
        try {
            // 配置図が紙の上で動いたか（前に組んだときの目印 layout_built.json、無ければ layout.json の anchors_prev）
            var bf = File(SDY.here.fsName + "/layout_built.json"), OB = null, an = L.anchors ? L.anchors["p1.siteplan"] : null, ao = null, ab1 = -1;
            try { if (bf.exists) { OB = SDY.readJSON(bf); } } catch (e) {}
            ao = (OB && OB.anchors && OB.anchors["p1.siteplan"]) || (L.anchors_prev ? L.anchors_prev["p1.siteplan"] : null);
            for (i = 0; i < n; i++) { if (L.pages[i].no === 1) { ab1 = i; } }
            if (an && ao && ab1 >= 0) {
                var ddx = an.origin[0] - ao.origin[0], ddy = an.origin[1] - ao.origin[1];
                if (Math.abs(ddx) > 0.05 || Math.abs(ddy) > 0.05) { SDY.planShift = { ab: ab1, win: ao.window, dx: ddx, dy: ddy, n: 0 }; }
            }
            var oldDoc = app.open(out);
            carried = SDY.copyUserItems(oldDoc, doc);
            oldDoc.close(SaveOptions.DONOTSAVECHANGES);
            app.activeDocument = doc;
        } catch (e) { SDY.missing.push("前の .ai を開けなかった（" + e.message + "）"); }
    }
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
    if (SDY.planShift && SDY.planShift.n) { msg += "\n配置図の上の物 " + SDY.planShift.n + " 個を、配置図と一緒に " + Math.round(SDY.planShift.dx) + "・" + Math.round(SDY.planShift.dy) + " mm 動かしました"; }
    if (SDY.missing.length) { msg += "\n\n見つからない・作れなかったもの：\n" + SDY.missing.join("\n"); }
    if (!SDY.font("W3")) { msg += "\n\nヒラギノ角ゴシックが見つからないので、書体は既定のままです。"; }
    alert(msg);
})();
