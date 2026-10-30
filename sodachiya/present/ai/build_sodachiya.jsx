// 育ち舎のプレゼン：layout.json から .ai を組む（Illustrator → ファイル → スクリプト → その他のスクリプト… でこのファイルを選ぶ）
// できたファイルは同じフォルダの sodachiya_present.ai（前のファイルは old/ に日時を付けて退ける）
// 大きな配置換え（枚の構成・番号が変わったとき）だけ使う。ふだんは update_texts.jsx（.ai は木田さんの .ai が正本、ユーザー 10-31 0:22）。
// 組み替え（既定）：前の .ai から、各レイヤーのすぐ下の物をグループごと複製して持ってきて、新しい割付の位置へ平行に動かすだけ（SDY.carry）。
//   前の .ai に無い部品だけ新しく描き、要らなくなった物は「外した物」のレイヤーに隠して残す。
// 予備：layout.json と記録（layout_user.json）から描き直す（前の .ai が無いとき、壊れたとき）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    var L = SDY.readJSON(File(SDY.here.fsName + "/layout.json"));
    var K = SDY.K, n = L.pages.length, i, k;
    var out = File(SDY.here.fsName + "/sodachiya_present.ai");
    var carry = false;
    if (out.exists) {
        for (k = 0; k < app.documents.length; k++) {
            try { if (app.documents[k].fullName.fsName === out.fsName && !app.documents[k].saved) { alert("sodachiya_present.ai が開いていて、保存していない変更があります。保存してから、もう一度。"); return; } } catch (e0) {}
        }
        carry = confirm("どちらで組みますか。\n\nはい：組み替え（前の sodachiya_present.ai から、レイヤーのすぐ下の物をグループごと持ってきて、新しい割付の位置へ平行に動かす。ふつうはこちら）\n\nいいえ：予備（layout_user.json の記録から描き直す。前の .ai が壊れたときなど）");
    }
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
    for (i = 0; i < n; i++) { doc.artboards[i].name = L.pages[i].no + "/" + n; }
    var U = null;
    try { var uf0 = File(SDY.here.fsName + "/layout_user.json"); if (uf0.exists) { U = SDY.readJSON(uf0); } } catch (e1) { SDY.missing.push("layout_user.json を読めなかった（" + e1.message + "）"); }
    var std = ["枠", "図", "ゾーニング　境界", "ゾーニング　上の線", "線", "説明", "注記"];   // 下から（ゾーニングの白地図、10-31）
    var msg = "";
    if (carry) {
        var first0 = doc.layers[0], src = null, res = null, st = null, sn = null, nf = 0, made = [];
        try {
            src = app.open(out);
            res = SDY.carry(doc, L, U, src);
        } catch (e2) {
            try { if (src) { src.close(SaveOptions.DONOTSAVECHANGES); } } catch (e3) {}
            alert("組み替えの途中で止まりました（" + e2.message + "）。新しいドキュメントは保存していません。前の .ai はそのまま。\n閉じてから、予備の組み方（いいえ）でもう一度。");
            return;
        }
        try { src.close(SaveOptions.DONOTSAVECHANGES); } catch (e4) {}   // 前の .ai は読んだだけ（old/ へ退けるために閉じる）
        app.activeDocument = doc;
        SDY.dwgCont = null;
        var above = null, lay;                         // 前の .ai に無い決まったレイヤーを、決まった並びの所へ（上から）
        for (k = std.length - 1; k >= 0; k--) {
            try { lay = doc.layers.getByName(std[k]); } catch (e5) { lay = doc.layers.add(); lay.name = std[k]; if (above) { try { lay.move(above, ElementPlacement.PLACEAFTER); } catch (e6) {} } }
            above = lay;
        }
        try { nf = SDY.carryFrames(doc, L, res.proto); } catch (e7) { SDY.missing.push("枠（" + e7.message + "）"); }
        st = SDY.refresh(doc, L, U, made);             // 前の .ai に無い部品を描く・文とリンクを新しく・形の変わった線は新しい版を足す（update_texts と同じ）
        sn = SDY.settleNew(doc, L, U, made);
        for (k = 0; k < res.props.length; k++) {      // レイヤーの表示・ロック・印刷は前のまま
            try { res.props[k].l.visible = res.props[k].visible; res.props[k].l.printable = res.props[k].printable; res.props[k].l.locked = res.props[k].locked; } catch (e8) {}
        }
        SDY.hideOut(doc);
        try { if (first0.pageItems.length === 0 && first0.layers.length === 0 && !SDY.inArr(std, first0.name) && !res.names[first0.name]) { first0.remove(); } } catch (e9) {}
        var cut = function (a) { return a.length > 15 ? a.slice(0, 15).join("\n") + "\n…ほか " + (a.length - 15) : a.join("\n"); };
        msg = "組み替えました：前の .ai から持ってきた物 " + res.n + " 個（紙の中の位置のまま " + (res.kept + res.ab) + "、新しい割付の位置へ " + res.def + "）" +
              "、新しく描いた部品 " + st.na + (res.out + st.nx ? "、要らなくなった部品（「外した物」へ） " + (res.out + st.nx) : "") + (nf > 0 ? "、枠を足した枚 " + nf : "") +
              "\n文字 " + st.nt + "、リンク " + st.nl + (st.nr ? "、形の変わった線（新しい版を「更新（新しい線）」に） " + st.nr : "") + (st.nu ? "、足した物（layout_user.json から） " + st.nu : "");
        if (res.split.length) { msg += "\n\nグループの中の部品が別々の紙に分かれる（グループのまま多い方の紙へ。.ai で分ける）：\n" + cut(res.split); }
        if (st.kept.length) { msg += "\n\n文の元が変わったが、書き換えてあるので差し替えなかった：\n" + cut(st.kept); }
        if (st.newl.length) { msg += "\n\n形の変わった線（前の線は名前の頭が「（前の線）」。見比べて要らない方を消す）：\n" + cut(st.newl); }
        if (res.fail.length) { msg += "\n\n持ってこられなかった物（前の .ai には残っている）：\n" + cut(res.fail); }
        if (SDY.notes.length) { msg += "\n\n知らせ：\n" + cut(SDY.notes); }
    } else {
    // ── 予備：記録から当て直す（前の作り方）──
    var first = doc.layers[0];
    var names = std, j, p, nmade = 0, skipped = 0;
    for (i = 0; i < names.length; i++) { SDY.layer(doc, names[i]); }        // 下から 枠・図・ゾーニング・線・説明・注記
    try { SDY.makeFrame(doc, L); } catch (e) { SDY.missing.push("枠（" + e.message + "）"); }
    for (i = 0; i < n; i++) {
        for (j = 0; j < L.pages[i].parts.length; j++) {
            p = L.pages[i].parts[j];
            if (p.hidden) { skipped++; continue; }
            try { if (SDY.make(doc, i, p)) { nmade++; } else { SDY.failed[p.id] = 1; } } catch (e) { SDY.failed[p.id] = 1; SDY.missing.push(p.id + "（" + e.message + "）"); }
        }
    }
    try { SDY.groupBoxes(doc); } catch (e) { SDY.missing.push("箱のまとめ（" + e.message + "）"); }
    var note = SDY.layer(doc, "注記");
    note.printable = false;                          // 割付の注記は見えるが印刷しない
    try { if (first.pageItems.length === 0 && first.name !== "枠") { first.remove(); } } catch (e) {}
    var carried = 0, drawnU = 0, known = {}, q;
    // 木田さんが足した物は layout_user.json の user_items から描き直す（正本、10-29：build で消えない）
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
            try { carried += SDY.carryOutLayer(oldDoc, doc); } catch (e10) {}   // 前の「外した物」も（10-31）
            oldDoc.close(SaveOptions.DONOTSAVECHANGES);
            app.activeDocument = doc;
        } catch (e) { SDY.missing.push("前の .ai を開けなかった（" + e.message + "）"); }
    }
    try { SDY.groupPlan(doc, L); } catch (e) { SDY.missing.push("配置図のまとめ（" + e.message + "）"); }
    try { SDY.groupDrawings(doc, L); } catch (e) { SDY.missing.push("図面のまとめ（" + e.message + "）"); }
    try { SDY.applyOrder(doc, L); SDY.applyStacking(doc, U); } catch (e) { SDY.missing.push("重ね順（" + e.message + "）"); }   // 重ね順：決め打ち → 書き出した並び（10-29）
    SDY.hideOut(doc);
    msg = "組みました（予備：記録から当て直し）：" + nmade + " 個（隠した " + skipped + " 個）、前の .ai から写した木田さんの物 " + carried + " 個";
    if (SDY.planShift && SDY.planShift.n && (Math.abs(SDY.planShift.dx) > 0.05 || Math.abs(SDY.planShift.dy) > 0.05)) { msg += "\n配置図の上の物 " + SDY.planShift.n + " 個を、配置図と一緒に " + Math.round(SDY.planShift.dx) + "・" + Math.round(SDY.planShift.dy) + " mm 動かしました"; }
    }
    if (out.exists) {                                  // 前のファイルは old/ に日時を付けて退け、同じ名前で保存する（ユーザー、10-26：名前が増えていく）
        var d = new Date();
        var stamp = d.getFullYear() + ("0" + (d.getMonth() + 1)).slice(-2) + ("0" + d.getDate()).slice(-2) + "-" + ("0" + d.getHours()).slice(-2) + ("0" + d.getMinutes()).slice(-2);
        var od = Folder(SDY.here.fsName + "/old"); if (!od.exists) { od.create(); }
        if (confirm("sodachiya_present.ai を新しく組んだもので置き換えます。\n前のファイルは old/sodachiya_present_" + stamp + ".ai に移します。\n（いいえ：日時を付けた別の名前で保存）")) {
            if (!out.copy(od.fsName + "/sodachiya_present_" + stamp + ".ai")) { alert("前のファイルを old/ に移せませんでした。開いたままなら閉じてから、もう一度。"); return; }
            out.remove();
            out = File(SDY.here.fsName + "/sodachiya_present.ai");
        } else {
            out = File(SDY.here.fsName + "/sodachiya_present_" + stamp + ".ai");
        }
    }
    doc.saveAs(out, new IllustratorSaveOptions());
    try { File(SDY.here.fsName + "/layout.json").copy(SDY.here.fsName + "/layout_built.json"); } catch (e) {}   // 組んだときの位置（書き出しで、動かした部品だけを残すため）
    msg += "\n" + out.fsName;
    if (SDY.missing.length) { msg += "\n\n見つからない・作れなかったもの：\n" + SDY.missing.join("\n"); }
    if (!SDY.font("W3")) { msg += "\n\nヒラギノ角ゴシックが見つからないので、書体は既定のままです。"; }
    SDY.writeFailed();
    alert(msg);
})();
