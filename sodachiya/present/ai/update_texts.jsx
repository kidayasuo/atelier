// 育ち舎のプレゼン：今開いている .ai の部品を、新しい layout.json で更新する（位置は動かさない）
// ・文字：中身を新しい文に（ユーザーが書き換えた文字は layout_user.json を通してそのまま残る）
// ・素材のリンク：同じファイルを読み直す（ファイルの場所が変わっていれば付け替える）
// ・.ai にまだ無い新しい部品：layout.json の位置に足す（消した部品は足さない）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    if (app.documents.length === 0) { alert("育ち舎の .ai を開いてから実行してください。"); return; }
    var doc = app.activeDocument;
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var L = SDY.readJSON(File(SDY.here.fsName + "/layout.json"));
    if (SDY.oldNumbering(L)) { alert("5枚の番号を振り直しました（10-28）。この .ai は前の番号のままなので、update_texts ではなく build_sodachiya.jsx で組み直してください（木田さんの物は新しい番号の枚へ写ります）。"); return; }
    var map = SDY.findByTag(doc), i, j, p, it, nt = 0, nl = 0, na = 0;
    for (i = 0; i < L.pages.length; i++) {
        for (j = 0; j < L.pages[i].parts.length; j++) {
            p = L.pages[i].parts[j];
            if (p.hidden) { continue; }
            it = map[p.id];
            if (!it) {
                try { if (SDY.make(doc, i, p)) { na++; } } catch (e) { SDY.missing.push(p.id + "（" + e.message + "）"); }
                continue;
            }
            if ((p.kind === "text" || p.kind === "area") && it.typename === "TextFrame") {
                var want = String(p.s).replace(/\n/g, "\r");
                if (SDY.norm(it.contents) !== SDY.norm(p.s)) { it.contents = want; nt++; }
                SDY.tag(it, p);                          // 新しい元の文の印に
            } else if (p.kind === "link") {
                var f = File(SDY.root.fsName + "/" + p.file), pl = it;
                if (it.typename === "GroupItem") { pl = it.placedItems.length ? it.placedItems[0] : null; }
                if (pl && f.exists) {
                    try { if (pl.file.fsName !== f.fsName) { pl.relink(f); } else { pl.relink(f); } nl++; } catch (e2) { SDY.missing.push(p.file); }
                } else if (!f.exists) { SDY.missing.push(p.file); }
            }
        }
    }
    var msg = "更新しました：文字 " + nt + "、リンク " + nl + "、新しい部品 " + na;
    if (SDY.missing.length) { msg += "\n\n見つからない・作れなかったもの：\n" + SDY.missing.join("\n"); }
    alert(msg);
})();
