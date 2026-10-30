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
    // 番号の振り直し（10-28・10-30 の6枚）：この .ai が前の番号のままなら、部品の名前（p2.… など）とアートボードを新しい番号に直して書き出す。
    // 枚が分かれた部品（renumber.split：前の3枚目の季節ごとの空気環境・配慮 → 2枚目など）は、前の紙の位置なので位置を書き出さない（文字・書式・レイヤー・消したは書き出す）
    var RN = SDY.oldNumbering(L), SP = SDY.oldSplit(L), SPLIT = {};
    var rab = function (n) { return (RN && RN[String(n)]) ? RN[String(n)] : n; };
    var rid = function (id) { var r2 = SDY.renameOld(id, RN, SP); if (r2[1]) { SPLIT[r2[0]] = true; } return r2[0]; };
    var rui = function (d) { var k3; if (d && d.artboard > 0) { d.artboard = rab(d.artboard); } if (d && d.children) { for (k3 = 0; k3 < d.children.length; k3++) { rui(d.children[k3]); } } return d; };
    var FAILED = SDY.readFailed();                    // build・update_texts が作れなかった部品（10-30）
    var LB = null;                                     // 組んだときの位置（layout_built.json、無ければ layout.json）
    try { LB = SDY.readJSON(File(SDY.here.fsName + "/layout_built.json")); } catch (e) { LB = L; }
    var BUILT = {}, bi, bj;
    if (LB) { for (bi = 0; bi < LB.pages.length; bi++) { for (bj = 0; bj < LB.pages[bi].parts.length; bj++) { BUILT[LB.pages[bi].parts[bj].id] = LB.pages[bi].parts[bj]; } } }
    var RB = {}, rb;                                   // 前の番号の .ai：組んだときにあった部品の今の名前（ここに無い新しい部品は「消した」にしない、10-30）
    if (RN) { for (rb in BUILT) { if (BUILT.hasOwnProperty(rb)) { RB[rid(rb)] = true; } } }
    // update_texts で後から足した部品（組んだときに無かった物）は、layout.json の位置と比べる（動かしていなければ書き出さない、10-29）
    if (L && LB !== L) { for (bi = 0; bi < L.pages.length; bi++) { for (bj = 0; bj < L.pages[bi].parts.length; bj++) { if (!BUILT[L.pages[bi].parts[bj].id]) { BUILT[L.pages[bi].parts[bj].id] = L.pages[bi].parts[bj]; } } } }
    var same = function (rec, o) {                     // 組んだときから動いていないか（0.3 mm）
        if (!o || rec.s !== undefined || rec.style !== undefined || rec.layer !== undefined) { return false; }
        var a = ["x", "y", "w", "h"], k2;
        for (k2 = 0; k2 < a.length; k2++) { if (rec[a[k2]] !== undefined && o[a[k2]] !== undefined && o[a[k2]] !== null && Math.abs(rec[a[k2]] - o[a[k2]]) > 0.3) { return false; } }
        if (rec.pts && o.pts) {
            if (rec.pts.length !== o.pts.length) { return false; }
            for (k2 = 0; k2 < rec.pts.length; k2++) { if (Math.abs(rec.pts[k2][0] - o.pts[k2][0]) > 0.3 || Math.abs(rec.pts[k2][1] - o.pts[k2][1]) > 0.3) { return false; } }
        }
        return true;
    };
    var out = { note: "Illustratorから export_layout.jsx が書き出した。ユーザーの割付（位置・大きさ・書き換えた文字・消した部品）。", parts: {} };
    var found = {}, i, it, t, b, ai, r, rec, k, n = 0, edited = 0;
    var bad = [];
    for (i = 0; i < doc.pageItems.length; i++) {
      try {
        it = doc.pageItems[i];
        t = SDY.parseTag(it);
        if (!t) { continue; }
        var oid = t.id; t.id = rid(t.id);                 // oid：組んだときの名前（layout_built.json）
        if (found[t.id]) { continue; }
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
        rec.artboard = rab(ai + 1);
        if (SPLIT[t.id]) {                             // 枚が分かれた部品：位置は前の紙のものなので書き出さない（10-30）
            delete rec.x; delete rec.y; delete rec.w; delete rec.h; delete rec.pts;
            var mp = /^p(\d+)\./.exec(t.id); if (mp) { rec.artboard = parseInt(mp[1], 10); }
        }
        try { var lyn = it.layer.name, bp = BUILT[oid]; if (bp && bp.layer && lyn !== bp.layer && lyn !== "編集モード" && lyn !== "Isolation Mode") { rec.layer = lyn; } } catch (e7) {}   // レイヤーを移した部品（10-29）
        if ((t.kind === "text" || t.kind === "area") && it.typename === "TextFrame") {
            // 書き換えた文字だけ。そのときの mock の文の印（s_base）も：mock の文が後で変わったら、記録の文は使わない（10-29）。
            // 設計趣旨（p1.concept）は concept.txt が正本なので文は記録しない（位置・大きさだけ、10-29）
            if (SDY.hash(it.contents) !== t.mock_hash && !/\.concept$/.test(t.id)) { rec.s = SDY.norm(it.contents); rec.s_base = t.mock_hash; edited++; }
            var LP = null, pj, pk;                          // 書式（書体・大きさ・色・行送り）：layout.json の部品と違う区間だけ（10-29）
            if (L) { for (pj = 0; pj < L.pages.length && !LP; pj++) { for (pk = 0; pk < L.pages[pj].parts.length; pk++) { if (L.pages[pj].parts[pk].id === t.id) { LP = L.pages[pj].parts[pk]; break; } } } }
            if (LP) { try { var sd = SDY.styleDiff(it, LP); if (sd.length) { rec.style = sd; } } catch (e6) {} }
        }
        if (!same(rec, BUILT[oid]) || (BUILT[oid] && BUILT[oid].u)) { out.parts[t.id] = rec; }   // 動かした・書き換えた部品だけ残す（動かしていない物はプレゼンの準備の既定のまま）
        n++;
      } catch (e) { bad.push((t ? t.id : ("物 " + i)) + "（" + e.message + "）"); }
    }
    var gone = 0, j, p;                                // layout.json にあって .ai に無い部品＝消したもの
    if (L) {
        for (i = 0; i < L.pages.length; i++) {
            for (j = 0; j < L.pages[i].parts.length; j++) {
                p = L.pages[i].parts[j];
                if (!found[p.id] && !FAILED[p.id] && (!RN || RB[p.id])) { out.parts[p.id] = { hidden: true }; gone++; }   // 作れなかった部品は「消した」にしない（10-30）
            }
        }
    }
    for (i = 0; i < doc.groupItems.length; i++) {      // 配置図の切り抜きの四角（使う大きさ、ユーザー 10-26夕）
        try {
            var cg = doc.groupItems[i];
            if (cg.name !== "配置図（切り抜き）" || !cg.clipped) { continue; }
            for (k = 0; k < cg.pathItems.length; k++) {
                if (!cg.pathItems[k].clipping) { continue; }
                b = cg.pathItems[k].geometricBounds; ai = SDY.abOf(doc, b); if (ai < 0) { break; }
                r = SDY.ab(doc, ai);
                out.siteclip = { artboard: rab(ai + 1), x: (b[0] - r[0]) / K, y: (r[1] - b[1]) / K, w: (b[2] - b[0]) / K, h: (b[1] - b[3]) / K };
                break;
            }
        } catch (e3) { bad.push("配置図の切り抜き（" + e3.message + "）"); }
    }
    try { out.stacking = SDY.stackingOf(doc, rid); } catch (e8) { bad.push("重ね順（" + e8.message + "）"); }   // レイヤーごとの重ね順（10-29）
    if (LB && LB.anchors) { out.anchors = LB.anchors; }   // 組んだときの配置図の目印（木田さんの物がどの配置図の上に描かれたか）
    // 木田さんが足した物（印の無い物、どの深さのグループの中でも）を台帳に。layout_user.json が正本で、build・update_texts はここから描き直す（10-29）。
    // 一つずつ印 sdyu:<鍵> を付けて次から同じ物と分かるように。前の書き出しにあって今回見つからない物は deleted_user へ（消した物は build で描かない）
    var ui = SDY.userItems(doc), q, PU = null, seen = {}, d, gp, uk;
    try { var uf = File(SDY.here.fsName + "/layout_user.json"); if (uf.exists) { PU = SDY.readJSON(uf); } } catch (e4) { PU = null; }
    out.user_items = [];
    var stamp = (function () { var t = new Date(); return t.getFullYear() + ("0" + (t.getMonth() + 1)).slice(-2) + ("0" + t.getDate()).slice(-2) + ("0" + t.getHours()).slice(-2) + ("0" + t.getMinutes()).slice(-2) + ("0" + t.getSeconds()).slice(-2); })();
    for (q = 0; q < ui.length; q++) {
        try {
            uk = SDY.userKey(ui[q]);
            if (!uk || seen[uk]) { uk = "u" + stamp + "_" + q; ui[q].note = SDY.UKEY + uk; }
            seen[uk] = true;
            d = rui(SDY.describe(doc, ui[q]));
            d.key = uk;
            gp = null; try { if (ui[q].parent.typename === "GroupItem") { gp = ui[q].parent.name || null; } } catch (e5) {}
            if (gp) { d.group = gp; }
            if (gp === SDY.PLAN_GROUP) { d.plan = true; }
            out.user_items.push(d);
        } catch (e2) { bad.push("足した物 " + q + "（" + e2.message + "）"); }
    }
    out.deleted_user = [];
    if (PU) {
        var prev = (PU.user_items || []).concat(PU.deleted_user || []);
        for (q = 0; q < prev.length; q++) { if (!prev[q].key || !seen[prev[q].key]) { out.deleted_user.push(prev[q]); } }
        if (out.deleted_user.length > 200) { out.deleted_user = out.deleted_user.slice(out.deleted_user.length - 200); }
    }
    SDY.writeText(File(SDY.here.fsName + "/layout_user.json"), SDY.stringify(out));
    alert("書き出しました：部品 " + n + " 個、木田さんが足した物 " + out.user_items.length + " 個（書き換えた文字 " + edited + "、消した部品 " + gone + "）\n" + SDY.here.fsName + "/layout_user.json\n\natelier で git add・commit・push してください。" + (bad.length ? "\n\n書き出せなかった部品（位置は前のまま）：\n" + bad.slice(0, 15).join("\n") : ""));
})();
