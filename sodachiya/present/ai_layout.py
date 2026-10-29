"""Illustratorの割付（present/ai/）：mock.pyが記録した部品を layout.json に書き出す（ユーザー、10-25夕）。

- 座標は紙のmm、アートボードの左上が原点（Illustratorと同じ向き、yは下へ）。
- 部品：link（素材やほかの係のPDFをリンクで配置、切り抜きと倍率）、text（ポイント文字、x,yは文字の基準線の点）、
  area（エリア内文字、x,yは枠の左上）、box（四角）、line（引き出し線）。枠（frame）はシンボルとしてスクリプトが作る。
- present/ai/layout_user.json（Illustratorから export_layout.jsx で書き出したもの）があれば、位置・大きさ・
  ユーザーが書き換えた文字はそれを優先する（ユーザーの割付が次の更新のもとになる）。
"""
import os, re, json, struct, datetime
import fitz
import numpy as np


def djb2(s):
    s = (s or "").replace("\r", "\n").rstrip("\n")
    b = s.encode("utf-16-le")
    h = 5381
    for (u,) in struct.iter_unpack("<H", b):
        h = (h * 33 + u) % 4294967296
    return format(h, "x")


def _slug(s, n=14):
    s = re.sub(r"[\s　/\\|:]+", "", s)
    return s[:n] or "x"


def _grp(r):
    """箱の部品をまとめるグループ（案Hの箱：見出し・本文・印を「箱　…」のグループに、ユーザー 10-28）"""
    if r.get("group"):                            # 記録に書いたグループ（3枚目の表と囲み、10-29）
        return dict(group=r["group"], group_name=r.get("group_name") or r["group"])
    k = r.get("id") or ""
    m = re.match(r"^ibox\.(nat|com)\.([^.]+)\.(title|text)$", k)
    return dict(group=f"ibox.{m.group(1)}.{m.group(2)}", group_name="箱　" + (r.get("name") or "").split("：", 1)[-1]) if m else {}


def _dwg_ok(dw, PARTS):
    """図面の線だけのリンク：Rhino の図はそのまま、自動の図は文字の層の線と文字を抜いた写し（ai/parts/<名前>_線だけ.pdf）"""
    if dw.get("lines"):
        return True
    if dw.get("rhino"):
        dw["lines"] = dw["src"]
        return True
    out = os.path.join(PARTS, os.path.splitext(os.path.basename(dw["auto"]))[0] + "_線だけ.pdf")
    if dw.get("_tried") is None:
        try:
            from zumen_parts import lines_only
            n, left = lines_only(dw["auto"], dw["moji"], out)
            if left:
                print("図面の線だけの写し：", os.path.basename(dw["auto"]), "文字の層の線のうち", left, "本を自動の図に見つけられない")
            dw["_tried"] = True
        except Exception as e:
            print("図面の線だけの写しを作れない（pikepdf？）：", os.path.basename(dw["auto"]), e, "→文字と寸法は部品にせず、今までどおり")
            dw["_tried"] = False
    if dw["_tried"]:
        dw["lines"] = out
        return True
    return False


def write(c):
    figs, rec, W, H, MM = c["figs"], c["rec"], c["W"], c["H"], c["MM"]
    NOTE, ROOT, HERE = c["NOTE"], c["ROOT"], c["HERE"]
    AI = os.path.join(HERE, "ai")
    PARTS = os.path.join(AI, "parts")
    os.makedirs(PARTS, exist_ok=True)
    pt = lambda size_mm: round(size_mm / 0.3528 / 0.72, 2)          # T()と同じ：文字の高さ（mm）→ em（pt）
    em = lambda size_mm: size_mm / 0.72                                # em（mm）
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
    try:
        _USER_ALL = json.load(open(os.path.join(AI, "layout_user.json"), encoding="utf-8"))
    except Exception:
        _USER_ALL = {}
    user = _USER_ALL.get("parts", {})
    pages = []
    for pi, fig in enumerate(figs):
        no = pi + 1
        regions = [(k, x, y, w, h) for (k, nm, sh, (x, y, w, h), note) in c["sozai"] if sh == no]
        emb = c["embeds"].get(no, [])
        def inside(px, py, slack=0.0):
            return any(x - slack <= px <= x + w + slack and y - slack <= py <= y + h + slack for _, x, y, w, h in regions)
        parts, seen = [], {}

        def add(p):
            base = p["id"]
            n = seen.get(base, 0) + 1
            seen[base] = n
            p["id"] = f"p{no}.{base}" + (f"~{n}" if n > 1 else "")
            parts.append(p)

        # 1) その他：ページの絵から文字・箱・枠と、素材・貼った図の範囲を除いたもの（地は透明）
        hidden = []
        for ax in fig.axes:
            for t in ax.texts:
                if t.get_text() and t.get_visible():
                    t.set_visible(False); hidden.append(t)
            for a in list(ax.patches) + list(ax.lines):
                if a.get_gid() == "aipart" and a.get_visible():
                    a.set_visible(False); hidden.append(a)
        tmp = os.path.join(PARTS, f"_p{no}.pdf")
        fig.savefig(tmp, transparent=True)
        for a in hidden:
            a.set_visible(True)
        d = fitz.open(tmp)
        pg = d[0]
        rects = [(x, y, w, h) for _, x, y, w, h in regions] + [dest for (_, _, _, dest) in emb]
        for (x, y, w, h) in rects:                  # 範囲に触れる絵は除く（切り抜きの図は範囲の外まで形がある）。1 mm 外まで
            pg.add_redact_annot(fitz.Rect((x - 1) * MM, (H - y - h - 1) * MM, (x + w + 1) * MM, (H - y + 1) * MM), fill=False)
        pg.apply_redactions(images=0, graphics=2, text=1)
        other = os.path.join(PARTS, f"p{no}_その他.pdf")
        if len(pg.get_drawings()) > 0:
            d.save(other, garbage=3, deflate=True)
            add(dict(id="other", name=f"{no}枚目　その他の絵（縮尺・方位・矢印など）", kind="link", layer="図",
                     file=rel(other), x=0, y=0, w=W, h=H, clip=None, scale=1))
        elif os.path.exists(other):
            os.remove(other)
        d.close(); os.remove(tmp)

        # 2) 素材（mock.pyが描いた図の範囲）
        for k, x, y, w, h in regions:
            fn = c["sozfn"].get(k)
            if fn:
                add(dict(id=f"sozai.{k}", name=f"素材 {fn[:-4]}", kind="link", layer="図", file=rel(os.path.join(HERE, "sozai", fn)),
                         x=round(x, 2), y=round(H - y - h, 2), w=round(w, 2), h=round(h, 2), clip=None, scale=1))
        # 3) 貼った図（ほかの係のPDF、配置図の三つ）
        for k_e, (src, pno, clip, (x, y, w, h)) in enumerate(emb):
            if inside(x + w / 2, y + h / 2):
                continue
            if src in c["sitemap"]:
                fn = c["sitemap"][src]
                # 切り抜きの四角（.ai の座標、左上から）：既定は見本の窓（左右）を木田さんが動かした分ずらし、上下は内枠いっぱい（ユーザー 10-28 18:01）。
                # 木田さんの四角（siteclip）があれば左右はそれ。上下も、上下いっぱいの版（anchors の clipv）で組んだ .ai から書き出したものならそれ
                ssx, ssy = c.get("site_shift", (0.0, 0.0))
                cx_, cw_ = x + ssx, w
                cy_, ch_ = (c["siteclip_full"] if c.get("siteclip_full") else (H - y - h + ssy, h))
                _uc = _USER_ALL.get("siteclip")                 # Illustratorで選んだ切り抜き（export_layout.jsx）
                if _uc:
                    cx_, cw_ = _uc["x"], _uc["w"]
                    if (_USER_ALL.get("anchors", {}).get("p1.siteplan") or {}).get("clipv") == (c["anchors"].get("p1.siteplan") or {}).get("clipv"):
                        cy_, ch_ = _uc["y"], _uc["h"]
                bx, by, bw, bh = c["sitebig"]                   # 素材は大きい窓、切り抜きの四角が見せる窓（一つのグループに四つ、ユーザー 10-26夕）
                add(dict(id=f"sozai.{fn.split('_')[0]}", name=f"素材 {fn[:-4]}", kind="link", layer="図", file=rel(os.path.join(HERE, "sozai", fn)),
                         x=round(bx, 2), y=round(by, 2), w=round(bw, 2), h=round(bh, 2), clip=None, scale=1, plan=True,
                         clipgroup="配置図（切り抜き）", cliprect=[round(cx_, 2), round(cy_, 2), round(cw_, 2), round(ch_, 2)]))
            elif (no, k_e) in c.get("dwg", {}) and _dwg_ok(c["dwg"][(no, k_e)], PARTS):
                # 課題の要求の図面（立面・断面・平面、ユーザー 10-29 0:16）：線だけのリンク（自動の図から文字と寸法を抜いた写し、Rhino の図はそのまま）と、
                # 文字の層から作った文字と寸法の部品を、図ごとに一つのグループ（dwg）に。部品は一つずつ動かす・消す・書き換えられる
                dw = c["dwg"][(no, k_e)]
                full = clip is None or (clip[0] == 0 and clip[1] == 0)
                add(dict(id=f"link.{os.path.splitext(os.path.basename(src))[0]}", name=f"図 {dw['name']}（線）", kind="link", layer="図",
                         file=rel(dw["lines"]), x=round(x, 2), y=round(H - y - h, 2), w=round(w, 2), h=round(h, 2),
                         clip=None if full else [round(v, 2) for v in clip], scale=round(w / (clip[2] - clip[0]), 4) if clip else 1, page=pno + 1, dwg=dw["name"]))
                from zumen_parts import parts_for
                for q in parts_for(dw["moji"], None if full else clip, (x, H - y - h), w / (clip[2] - clip[0]) if clip else 1.0, dw["key"], pno):
                    q["dwg"] = dw["name"]
                    q["mock_hash"] = djb2(q["s"]) if q["kind"] == "text" else djb2(q.pop("geo"))
                    add(q)
            elif (no, k_e) in c.get("emb_dwg", {}):
                # 図面に重ねる物（採光の図を断面図Dに、10-29）：部品の一覧があれば文字と線を一つずつ（図面のグループの中のグループ）、無ければ PDF のリンク
                ed = c["emb_dwg"][(no, k_e)]
                if ed.get("parts") and os.path.exists(ed["parts"]):
                    T_ = lambda q: [round(ed["tl"][0] + (q[0] - ed["origin"][0]), 3), round(ed["tl"][1] + (q[1] - ed["origin"][1]), 3)]
                    for q in json.load(open(ed["parts"], encoding="utf-8"))["parts"]:
                        q = json.loads(json.dumps(q))
                        if "x" in q and "y" in q:
                            q["x"], q["y"] = T_((q["x"], q["y"]))
                        for pp in q.get("paths", []):
                            pp["pts"] = [T_(v) for v in pp["pts"]]
                        if q.get("group_name"):
                            q["name"] = q.get("name") or q["group_name"]
                        q["group"], q["group_name"] = ed["group"]
                        q["dwg"] = ed["dwg"]
                        q.setdefault("mock_hash", djb2(json.dumps(q, ensure_ascii=False, sort_keys=True)))
                        add(q)
                else:
                    add(dict(id=f"link.{os.path.splitext(os.path.basename(src))[0]}", name=f"図 {os.path.basename(src)}", kind="link", layer="図",
                             file=rel(src), x=round(x, 2), y=round(H - y - h, 2), w=round(w, 2), h=round(h, 2), clip=None, scale=1, page=pno + 1, dwg=ed["dwg"]))
            else:
                full = clip[0] == 0 and clip[1] == 0
                add(dict(id=f"link.{os.path.splitext(os.path.basename(src))[0]}", name=f"図 {os.path.basename(src)}", kind="link", layer="図",
                         file=rel(src), x=round(x, 2), y=round(H - y - h, 2), w=round(w, 2), h=round(h, 2),
                         clip=None if full else [round(v, 2) for v in clip], scale=round(w / (clip[2] - clip[0]), 4), page=pno + 1,
                         **({"plan": True} if src in c.get("plan_links", []) else {}),
                         # Rhino の線の図には、文字と寸法の図を同じ切り抜き・同じ位置で重ねる（一つの切り抜きのグループに二つのリンク、10-28）
                         **({"overlay": rel(c["rhino_txt"][(no, k_e)]), "base_name": "線（Rhino）", "overlay_name": "文字と寸法"} if (no, k_e) in c.get("rhino_txt", {}) else {})))
        # 4) 文字・箱
        has_frame = False
        for r in rec:
            if r["fig"] is not fig:
                continue
            k = r["kind"]
            if k == "frame":
                has_frame = True
                continue
            note = r.get("color") == NOTE or r.get("stroke") == NOTE
            layer = "注記" if note else "説明"
            if k == "text":
                e = em(r["size"])
                y = r["y"]
                y += {"center": -0.35 * e, "top": -0.88 * e, "bottom": 0.12 * e}.get(r["va"], 0.0)
                if inside(r["x"], r["y"]):
                    continue
                add(dict(id=r.get("id") or f"t.{_slug(r['s'])}", name=r.get("name") or r["s"][:24], kind="text", layer=layer,
                         x=round(r["x"], 2), y=round(H - y, 2), s=r["s"], size_pt=pt(r["size"]), font=r.get("font") or ("W6" if r["bold"] else "W3"),
                         color=r["color"], align=r["ha"] if r["ha"] in ("left", "center", "right") else "left", mock_hash=djb2(r["s"]),
                         **({"para_styles": r["para_styles"]} if r.get("para_styles") else {}), **_grp(r)))
            elif k == "area":
                if inside(r["x"], r["y"]):
                    continue
                e = em(r["size"])
                top = r["y"] + 0.88 * e                     # 1行目の基準線から枠の上端へ
                add(dict(id=r["id"], name=r["name"], kind="area", layer=layer, x=round(r["x"], 2), y=round(H - top, 2),
                         w=round(r["w"], 2), h=round(max(r["h"], 2 * e) + e, 2), s=r["s"], size_pt=pt(r["size"]),
                         font="W6" if r["bold"] else "W3", color=r["color"], align="left", justify="full_last_left",   # 両端揃え（最終行は左）、ユーザー 10-25夕
                         leading=r.get("leading", 1.5), para_space=r.get("para_space", 1.0), mock_hash=djb2(r["s"]), **_grp(r)))
            elif k == "box":
                if inside(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2):
                    continue
                add(dict(id=r["id"], name=r["name"], kind="box", layer=layer, x=round(r["x"], 2), y=round(H - r["y"] - r["h"], 2),
                         w=round(r["w"], 2), h=round(r["h"], 2), fill=r["fill"], stroke=r["stroke"], lw=r["lw"], dash=r["dash"], **_grp(r)))
            elif k == "line":                           # 罫線の部品（3枚目の表、10-29）
                add(dict(id=r["id"], name=r.get("name") or "罫線", kind="line", layer=layer, pts=[[round(q[0], 2), round(H - q[1], 2)] for q in r["pts"]],
                         color=r["color"], lw=r["lw"], **_grp(r)))
        # 5) 引き出し線と重ねた文字
        for i, (pts, col, *kk) in enumerate(c["topl"].get(no, [])):
            lk = kk[0] if kk and kk[0] else str(i + 1)
            add(dict(id=f"leader.{lk}", name=f"引き出し線 {lk}", kind="line", layer="線", pts=[[round(p[0], 2), round(H - p[1], 2)] for p in pts],
                     color=col, lw=0.6, dot=0.9))
        for i, (tx, ty, ts, th, tb, *ex) in enumerate(c["topt"].get(no, [])):
            o_ = ex[2] if len(ex) > 2 else {}            # id（固定の鍵）・name・align・follow（一緒に動く部品、ユーザー 10-28）
            add(dict(id=o_.get("id") or f"top.{_slug(ts)}", name=o_.get("name") or ts[:24], kind="text", layer="説明", x=round(tx, 2), y=round(H - ty, 2), s=ts,
                     size_pt=pt(th), font=(ex[0] if ex and ex[0] else ("W6" if tb else "W3")), color=(ex[1] if len(ex) > 1 else "#1A1A1A"),
                     align=o_.get("align", "left"), mock_hash=djb2(ts), **({"follow": f"p{no}." + o_["follow"]} if o_.get("follow") else {}),
                     **({"plan": True} if o_.get("plan") else {})))
        # 5b) 番号の印（案H、1枚目、ユーザー 10-28）：○（自然）か□（地域）と白抜きの数字を一つのグループに。
        #     配置図の上の印は素材01a（配置図）について行く（.ai で配置図ごと動かしたら一緒に）。数字は mock.py が決めた番号（.ai の書き換えは mock.py が拾う）
        if no == 1:
            for mk in c.get("marks", []):
                r_, col = mk["r"], (c["cnat"] if mk["cat"] == "nat" else c["ccom"])
                gk = dict(group=mk["group"], group_name=mk["group_name"]) if not mk["id"].startswith("ibox.") else \
                    dict(group=mk["group"].rsplit(".", 1)[0], group_name=mk["group_name"].replace("印（箱）　", "箱　"))
                fo = dict(plan=True) if mk.get("follow") == "sozai.01a" else (dict(follow=f"p{no}." + mk["follow"]) if mk.get("follow") else {})   # 配置図の上の印は配置図のまとめに
                s_ = r_ if mk["cat"] == "nat" else r_ * 0.9
                shp = dict(id=f"{mk['id']}.shape", name=("○" if mk["cat"] == "nat" else "□") + f"　{mk['group_name']}", layer="説明",
                           x=round(mk["cx"] - s_, 2), y=round(H - mk["cy"] - s_, 2), w=round(2 * s_, 2), h=round(2 * s_, 2), fill=col,
                           stroke="#FFFFFF" if mk["ring"] else None, lw=0.8 if mk["ring"] else 0, **gk, **fo)
                if mk["cat"] == "nat":
                    shp.update(kind="circle", alpha=1.0)
                else:
                    shp.update(kind="box", dash=None)
                add(shp)
                e = em(c["mark_num"])
                add(dict(id=f"{mk['id']}.num", name=f"番号　{mk['group_name']}", kind="text", layer="説明", x=round(mk["cx"], 2), y=round(H - (mk["cy"] - 0.35 * e), 2),
                         s=str(mk["num"]), size_pt=pt(c["mark_num"]), font="W6", color="#FFFFFF", align="center", mock_hash=djb2(str(mk["num"])),
                         no_user_s=True, **gk, **fo))
        # 6) 配置図の中の文字・注の線・突き出た木（1枚目、ユーザー 10-25夕：一つずつ動かして書き換える。注の文字と線は一つのグループ）
        if no == 1:
            for sp in c.get("siteparts", []):
                if sp["kind"] == "text":
                    e = em(sp["size"])
                    y = sp["y"] + {"center": -0.35 * e, "top": -0.88 * e, "bottom": 0.12 * e}.get(sp["va"], 0.0)
                    add(dict(id=f"site.t.{_slug(sp['s'], 16)}", name=f"配置図の文字　{sp['s'][:20]}", kind="text", layer="説明",
                             x=round(sp["x"], 2), y=round(H - y, 2), s=sp["s"], size_pt=pt(sp["size"]), font="W6" if sp["bold"] else "W3",
                             color=sp["color"], align=sp["ha"] if sp["ha"] in ("left", "center", "right") else "left",
                             group=sp.get("group"), mock_hash=djb2(sp["s"]), plan=True))
                elif sp["kind"] == "line":
                    add(dict(id=sp.get("id") or f"site.l.{(sp.get('group') or 'x').split('.')[-1]}", name=sp.get("name", "配置図の注の線"), kind="line", layer="説明",
                             pts=[[round(q[0], 2), round(H - q[1], 2)] for q in sp["pts"]], color=sp["color"], lw=sp["lw"], dot=sp.get("dot"),
                             arrow=sp.get("arrow"), group=sp.get("group"), plan=True))
                elif sp["kind"] == "circle":
                    add(dict(id=f"site.{sp['id']}", name=sp["name"], kind="circle", layer="説明",
                             x=round(sp["cx"] - sp["r"], 2), y=round(H - sp["cy"] - sp["r"], 2), w=round(2 * sp["r"], 2), h=round(2 * sp["r"], 2),
                             fill=sp["fill"], alpha=sp.get("alpha", 1.0), stroke=sp.get("stroke"), lw=sp.get("lw", 0), group=sp.get("group"), plan=True))
        for p in parts:
            g_ = p.get("group")
            if g_ and not p.get("group_name"):
                p["group_name"] = "突き出た木" if g_ == "site.g.tree" else ("縮尺" if g_ == "site.g.縮尺" else "配置図の注　" + g_.split(".")[-1])
        # ユーザーの割付を優先。follow の付いた部品は、自分の割付が無ければ、ついて行く部品（素材など）がユーザーに動かされた分だけ一緒に動く
        for p in parts:                             # 前の部品の .ai の位置へ一度だけ移す（mock.py の AI_SHIFT、例：前の箱 → 案Hの見出し・本文・印）
            for pre, (dx, dy) in c.get("ai_shift", {}).items():
                if p["id"].startswith(f"p{no}." + pre) and p.get("x") is not None:
                    p["x"], p["y"], p["u"] = round(p["x"] + dx, 2), round(p["y"] + dy, 2), 1
        _base = {p["id"]: (p.get("x"), p.get("y")) for p in parts}
        for p in parts:
            f_ = p.pop("follow", None)
            if f_ and p["id"] not in user and f_ in user and "x" in user[f_] and _base.get(f_, (None,))[0] is not None:
                p["x"] = round(p["x"] + user[f_]["x"] - _base[f_][0], 2)
                p["y"] = round(p["y"] + user[f_].get("y", _base[f_][1]) - _base[f_][1], 2)
        for p in parts:
            u = user.get(p["id"])
            if not u:
                continue
            if u.get("hidden"):
                p["hidden"] = True
            if p["kind"] == "lines":                    # 図面の線の部品（寸法線など）：動かした分だけ線をずらす（大きさは変えない）
                if "x" in u and "y" in u:
                    dx, dy = u["x"] - p["x"], u["y"] - p["y"]
                    for q in p["paths"]:
                        q["pts"] = [[round(a + dx, 3), round(b + dy, 3)] for a, b in q["pts"]]
                    p["x"], p["y"], p["u"] = round(u["x"], 2), round(u["y"], 2), 1
                continue
            h0 = p.get("h")
            for key in ("x", "y", "w", "h", "pts"):
                if key in u:
                    p[key] = u[key]
            if p["kind"] == "area" and h0 and "h" in u and h0 > u["h"]:   # 字を大きくして中身が伸びたら、ユーザーの上端・左端はそのままで高さだけ伸ばす（10-29）
                p["h"] = h0
            if any(k_ in u for k_ in ("x", "y", "w", "h", "pts")):
                p["u"] = 1                          # ユーザーの割付で置いた（export は動かしていなくても書き出す：次の更新で既定に戻らないように）
            if p["kind"] == "link" and "w" in u and p.get("clip"):
                p["scale"] = round(u["w"] / (p["clip"][2] - p["clip"][0]), 4)
            if "s" in u and p["kind"] in ("text", "area") and not p.get("no_user_s"):
                p["s"] = u["s"]
        # 配置図のまとめ（1枚目、ユーザー 10-28 18:03：配置図の位置に依存する物は全てグループに）：plan の付いた部品。
        # 木田さんが .ai で配置図ごと動かした分（site_shift）だけ、割付の無い部品も一緒に動かす。素材01a〜dは大きさが変わっても原点が同じ所に来るように
        ssx, ssy = c.get("site_shift", (0.0, 0.0)) if no == 1 else (0.0, 0.0)
        for p in parts:
            if not p.get("plan"):
                continue
            if p["id"].startswith("p1.sozai.01"):
                bx, by, bw, bh = c["sitebig"]
                p.update(x=round(bx + ssx, 2), y=round(by + ssy, 2), w=round(bw, 2), h=round(bh, 2), u=1)
                continue
            u = user.get(p["id"]) or {}
            if any(k_ in u for k_ in ("x", "y", "pts")) or (abs(ssx) + abs(ssy) < 0.01):
                continue
            if p.get("x") is not None:
                p["x"], p["y"] = round(p["x"] + ssx, 2), round(p["y"] + ssy, 2)
            if p.get("pts"):
                p["pts"] = [[round(q[0] + ssx, 2), round(q[1] + ssy, 2)] for q in p["pts"]]
        for p in parts:
            p.pop("no_user_s", None)
        pages.append(dict(no=no, frame=has_frame, parts=parts))
    M = 15.0
    out = dict(note="mock.pyが書き出す。Illustratorで build_sodachiya.jsx が読む。手で書き換えない（ユーザーの割付は layout_user.json）",
               generated=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
               unit="mm", artboard=[W, H],
               frame=dict(margin=M, header=c.get("frame_hdr", (16, 11, 6.5))[0], title=dict(s="こどもたちの育ち舎", x=M + 4, y=M + c.get("frame_hdr", (16, 11, 6.5))[1],
                          size_pt=pt(c.get("frame_hdr", (16, 11, 6.5))[2]), font="W6"),
                          footer=dict(s="建築設計実習Ⅱ—Ⅰ　2026.11.05　木田", x=W - M - 4, y=H - M - 4, size_pt=pt(3.0), font="W3", align="right"),
                          lw_rect=0.6, lw_header=0.4, color="#222222"),
               anchors=c.get("anchors", {}), anchors_prev=c.get("anchors_prev", {}),
               pages=pages)
    if c.get("renumber"):                       # 5枚の番号の振り直し（前の番号 → 新しい番号）。build・export が前の番号の .ai を読むときに使う
        out["renumber"] = c["renumber"]
    json.dump(out, open(os.path.join(AI, "layout.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("Illustratorの割付：", ", ".join(f"{p['no']}枚目 {len(p['parts'])}部品" for p in pages))
