// 育ち舎のプレゼン：開いている .ai の図を、図ごとに一つのグループにまとめる（一度だけ。ユーザー 11-01 08:49：配置図・ゾーン図がバラバラで位置の調整ができない）
// 図を作る部品（素材のリンク・図の中の文字と注・線・記号・凡例・色の層・文字の層・図の題）を、layout.json の fig（図の名前）で探して一つのグループに入れる。
// 位置・大きさ・色・文字は変えない（グループに入れるだけ）。印の無い物（木田さんの物）は入れない。もうまとまっている図は触らない。
// 先に数えて見せ、「はい」で入れる。走らせる前に .ai を保存しておく（戻すときは保存せずに閉じる）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    if (app.documents.length === 0) { alert("育ち舎の .ai を開いてから実行してください。"); return; }
    try { app.executeMenuCommand("exitisolation"); } catch (eIso) {}   // 編集モード（グループの中に入った状態）だとレイヤーを足せないので、先に抜ける（11-01）
    var doc = app.activeDocument;
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var L = SDY.readJSON(File(SDY.here.fsName + "/layout.json"));
    if (SDY.oldNumbering(L)) { alert("この .ai は前の枚の番号のままです。先に build_sodachiya.jsx の「組み替え」で組み直してください。"); return; }
    if (!SDY.hasFigs(L)) { alert("layout.json に図の名前（fig）がありません。git pull してから、もう一度。"); return; }
    var P = SDY.groupFigures(doc, L, null, true);
    var cut = function (a) { return a.length > 20 ? a.slice(0, 20).join("\n") + "\n…ほか " + (a.length - 20) : a.join("\n"); };
    var OUTS = [], STR = [];
    try { OUTS = SDY.figsOutside(doc, L); STR = SDY.figStrays(doc, L); } catch (e0) {}
    var chk = "\n\n図のグループの外にある図の部品：" + (OUTS.length ? OUTS.length + "\n" + cut(OUTS) : "なし") +
              (STR.length ? "\n\n図の上にあるが図の部品でない物（図とは別に動く。「更新（新しい線）」「（前の線）」は見比べて要らない方を消す。一から作り直すのが早い：README）：" + STR.length + "\n" + cut(STR) : "");
    if (P.figs === 0) { alert("まとめる図はありません（" + P.done + "）。" + SDY.figReport(P) + chk); return; }
    var ask = "図を " + P.figs + " つ、それぞれ一つのグループにまとめます（グループに入れる物 " + P.moved + "、もうまとまっている図 " + P.done + "）。\n" +
              "位置・大きさ・色・文字は変えません。グループはその図のいちばん下の物のレイヤー（ふつう「図」）に作ります。" + SDY.figReport(P) + "\n\n続けますか。";
    if (!confirm(ask)) { return; }
    var R = SDY.groupFigures(doc, L, null, false);
    alert("図を " + R.figs + " つまとめました（新しいグループ " + R.made + "、入れた物 " + R.moved + "、もうまとまっていた図 " + R.done + "）。\n" +
          "図をドラッグすると中の物も一緒に動きます。中の一つだけ動かすときはダブルクリックで中に入る（終わったら Esc）。\n" +
          "動かしたら export_layout.jsx で書き出して push。" + SDY.figReport(R));
})();
