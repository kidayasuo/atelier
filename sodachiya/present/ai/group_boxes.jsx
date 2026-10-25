// 育ち舎のプレゼン：開いている .ai の説明の箱を、箱・見出し・本文の一つのグループにまとめる（一度だけ。新しく組んだ .ai はもうまとまっている）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    if (app.documents.length === 0) { alert("育ち舎の .ai を開いてから実行してください。"); return; }
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var n = SDY.groupBoxes(app.activeDocument);
    alert("箱を " + n + " 個まとめました。箱をドラッグすると見出しと本文もいっしょに動きます。\n引き出し線は、箱を動かした後に reconnect_leaders.jsx で付け直します。");
})();
