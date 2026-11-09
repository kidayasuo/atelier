// 育ち舎のプレゼン：箱を動かした後に、引き出し線を箱に付け直す（線の終わりの点は動かさない。始まりを箱の縁の、点に近い側へ）
#target illustrator
#include "sdy_lib.jsxinc"
(function () {
    if (app.documents.length === 0) { alert("育ち舎の .ai を開いてから実行してください。"); return; }
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var L = SDY.readJSON(File(SDY.here.fsName + "/layout.json"));
    var n = SDY.reconnect(app.activeDocument, L);
    alert("引き出し線を " + n + " 本付け直しました。");
})();
