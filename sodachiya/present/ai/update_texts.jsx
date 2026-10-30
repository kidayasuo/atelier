// 育ち舎のプレゼン：今開いている .ai を、新しい layout.json で更新する（ふだんはこれ。.ai は木田さんの .ai が正本、ユーザー 10-31 0:22）
// 木田さんが手を入れた物（位置・大きさ・書式・塗り・レイヤー・グループ・重ね順）には触れない。前からある物で変えるのは次だけ：
// ・文字：文の元（mock）が変わり、木田さんが文を書き換えていなければ、文だけ差し替える（書式はそのまま）。書き換えていれば差し替えずに一覧で知らせる
// ・図のPDF（リンク）：ファイルを差し替えるだけ（位置・大きさ・切り抜きは今のまま）
// ・形の変わった線の部品（ゾーニングの区分・図面の寸法など）：前の線は残し、新しい版をレイヤー「更新（新しい線）」に足して一覧で知らせる（見比べて要らない方を消す）
// ・layout.json から無くなった部品：消さずにレイヤー「外した物」へ移して隠す
// ・新しい部品：layout.json の位置・元のレイヤーに足す（消した部品は足さない）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    if (app.documents.length === 0) { alert("育ち舎の .ai を開いてから実行してください。"); return; }
    var doc = app.activeDocument;
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var L = SDY.readJSON(File(SDY.here.fsName + "/layout.json"));
    if (SDY.oldNumbering(L)) { alert("枚の番号を振り直しました（10-28、10-30 の6枚）。この .ai は前の番号のままなので、update_texts ではなく build_sodachiya.jsx の「組み替え」で組み直してください（.ai の物はそのまま新しい番号の枚へ移ります）。"); return; }
    var U = null;
    try { var uf = File(SDY.here.fsName + "/layout_user.json"); if (uf.exists) { U = SDY.readJSON(uf); } } catch (e0) { SDY.missing.push("layout_user.json を読めなかった（" + e0.message + "）"); }
    var made = [], st = SDY.refresh(doc, L, U, made), sn = SDY.settleNew(doc, L, U, made);
    SDY.hideOut(doc);
    var msg = "更新しました：文字 " + st.nt + "、リンク " + st.nl + "、新しい部品 " + st.na +
              (st.nr ? "、形の変わった線（新しい版を「更新（新しい線）」に） " + st.nr : "") + (st.nx ? "、無くなった部品（「外した物」へ） " + st.nx : "") +
              (sn.ng ? "、配置図のまとめに入れた新しい物 " + sn.ng : "") + (sn.nd ? "、図面のまとめに入れた新しい物 " + sn.nd : "") + (st.nu ? "、足した物（layout_user.json から） " + st.nu : "");
    var cut = function (a) { return a.length > 15 ? a.slice(0, 15).join("\n") + "\n…ほか " + (a.length - 15) : a.join("\n"); };
    if (st.kept.length) { msg += "\n\n文の元が変わったが、書き換えてあるので差し替えなかった（見比べて直す）：\n" + cut(st.kept); }
    if (st.newl.length) { msg += "\n\n形の変わった線（前の線は名前の頭が「（前の線）」。見比べて要らない方を消す）：\n" + cut(st.newl); }
    if (SDY.notes.length) { msg += "\n\n知らせ：\n" + cut(SDY.notes); }
    if (SDY.missing.length) { msg += "\n\n見つからない・作れなかったもの：\n" + cut(SDY.missing); }
    SDY.writeFailed();
    alert(msg);
})();
