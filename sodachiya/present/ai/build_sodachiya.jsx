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
    if (out.exists) {
        var d = new Date();
        var st = d.getFullYear() + ("0" + (d.getMonth() + 1)).slice(-2) + ("0" + d.getDate()).slice(-2) + "-" + ("0" + d.getHours()).slice(-2) + ("0" + d.getMinutes()).slice(-2);
        out = File(SDY.here.fsName + "/sodachiya_present_" + st + ".ai");
    }
    doc.saveAs(out, new IllustratorSaveOptions());
    var msg = "組みました：" + made + " 個（隠した " + skipped + " 個）\n" + out.fsName;
    if (SDY.missing.length) { msg += "\n\n見つからない・作れなかったもの：\n" + SDY.missing.join("\n"); }
    if (!SDY.font("W3")) { msg += "\n\nヒラギノ角ゴシックが見つからないので、書体は既定のままです。"; }
    alert(msg);
})();
