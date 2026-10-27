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
        for (src, pno, clip, (x, y, w, h)) in emb:
            if inside(x + w / 2, y + h / 2):
                continue
            if src in c["sitemap"]:
                fn = c["sitemap"][src]
                _uc = _USER_ALL.get("siteclip")                 # Illustratorで選んだ切り抜き（export_layout.jsx）
                if _uc:
                    x, w, h = _uc["x"], _uc["w"], _uc["h"]; y = H - _uc["y"] - h
                bx, by, bw, bh = c["sitebig"]                   # 素材は大きい窓、切り抜きの四角が見せる窓（一つのグループに四つ、ユーザー 10-26夕）
                add(dict(id=f"sozai.{fn.split('_')[0]}", name=f"素材 {fn[:-4]}", kind="link", layer="図", file=rel(os.path.join(HERE, "sozai", fn)),
                         x=round(bx, 2), y=round(by, 2), w=round(bw, 2), h=round(bh, 2), clip=None, scale=1,
                         clipgroup="配置図（切り抜き）", cliprect=[round(x, 2), round(H - y - h, 2), round(w, 2), round(h, 2)]))
            else:
                full = clip[0] == 0 and clip[1] == 0
                add(dict(id=f"link.{os.path.splitext(os.path.basename(src))[0]}", name=f"図 {os.path.basename(src)}", kind="link", layer="図",
                         file=rel(src), x=round(x, 2), y=round(H - y - h, 2), w=round(w, 2), h=round(h, 2),
                         clip=None if full else [round(v, 2) for v in clip], scale=round(w / (clip[2] - clip[0]), 4), page=pno + 1))
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
                         color=r["color"], align=r["ha"] if r["ha"] in ("left", "center", "right") else "left", mock_hash=djb2(r["s"])))
            elif k == "area":
                if inside(r["x"], r["y"]):
                    continue
                e = em(r["size"])
                top = r["y"] + 0.88 * e                     # 1行目の基準線から枠の上端へ
                add(dict(id=r["id"], name=r["name"], kind="area", layer=layer, x=round(r["x"], 2), y=round(H - top, 2),
                         w=round(r["w"], 2), h=round(max(r["h"], 2 * e) + e, 2), s=r["s"], size_pt=pt(r["size"]),
                         font="W6" if r["bold"] else "W3", color=r["color"], align="left", justify="full_last_left",   # 両端揃え（最終行は左）、ユーザー 10-25夕
                         leading=r.get("leading", 1.5), para_space=r.get("para_space", 1.0), mock_hash=djb2(r["s"])))
            elif k == "box":
                if inside(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2):
                    continue
                add(dict(id=r["id"], name=r["name"], kind="box", layer=layer, x=round(r["x"], 2), y=round(H - r["y"] - r["h"], 2),
                         w=round(r["w"], 2), h=round(r["h"], 2), fill=r["fill"], stroke=r["stroke"], lw=r["lw"], dash=r["dash"]))
        # 5) 引き出し線と重ねた文字
        for i, (pts, col, *kk) in enumerate(c["topl"].get(no, [])):
            lk = kk[0] if kk and kk[0] else str(i + 1)
            add(dict(id=f"leader.{lk}", name=f"引き出し線 {lk}", kind="line", layer="線", pts=[[round(p[0], 2), round(H - p[1], 2)] for p in pts],
                     color=col, lw=0.6, dot=0.9))
        for i, (tx, ty, ts, th, tb, *ex) in enumerate(c["topt"].get(no, [])):
            add(dict(id=f"top.{_slug(ts)}", name=ts[:24], kind="text", layer="説明", x=round(tx, 2), y=round(H - ty, 2), s=ts,
                     size_pt=pt(th), font=(ex[0] if ex and ex[0] else ("W6" if tb else "W3")), color=(ex[1] if len(ex) > 1 else "#1A1A1A"), align="left", mock_hash=djb2(ts)))
        # 6) 配置図の中の文字・注の線・突き出た木（1枚目、ユーザー 10-25夕：一つずつ動かして書き換える。注の文字と線は一つのグループ）
        if no == 1:
            for sp in c.get("siteparts", []):
                if sp["kind"] == "text":
                    e = em(sp["size"])
                    y = sp["y"] + {"center": -0.35 * e, "top": -0.88 * e, "bottom": 0.12 * e}.get(sp["va"], 0.0)
                    add(dict(id=f"site.t.{_slug(sp['s'], 16)}", name=f"配置図の文字　{sp['s'][:20]}", kind="text", layer="説明",
                             x=round(sp["x"], 2), y=round(H - y, 2), s=sp["s"], size_pt=pt(sp["size"]), font="W6" if sp["bold"] else "W3",
                             color=sp["color"], align=sp["ha"] if sp["ha"] in ("left", "center", "right") else "left",
                             group=sp.get("group"), mock_hash=djb2(sp["s"])))
                elif sp["kind"] == "line":
                    add(dict(id=sp.get("id") or f"site.l.{(sp.get('group') or 'x').split('.')[-1]}", name=sp.get("name", "配置図の注の線"), kind="line", layer="説明",
                             pts=[[round(q[0], 2), round(H - q[1], 2)] for q in sp["pts"]], color=sp["color"], lw=sp["lw"], dot=sp.get("dot"),
                             arrow=sp.get("arrow"), group=sp.get("group")))
                elif sp["kind"] == "circle":
                    add(dict(id=f"site.{sp['id']}", name=sp["name"], kind="circle", layer="説明",
                             x=round(sp["cx"] - sp["r"], 2), y=round(H - sp["cy"] - sp["r"], 2), w=round(2 * sp["r"], 2), h=round(2 * sp["r"], 2),
                             fill=sp["fill"], alpha=sp.get("alpha", 1.0), stroke=sp.get("stroke"), lw=sp.get("lw", 0), group=sp.get("group")))
        for p in parts:
            g_ = p.get("group")
            if g_:
                p["group_name"] = "突き出た木" if g_ == "site.g.tree" else ("縮尺" if g_ == "site.g.縮尺" else "配置図の注　" + g_.split(".")[-1])
        # ユーザーの割付を優先
        for p in parts:
            u = user.get(p["id"])
            if not u:
                continue
            if u.get("hidden"):
                p["hidden"] = True
            for key in ("x", "y", "w", "h", "pts"):
                if key in u:
                    p[key] = u[key]
            if p["kind"] == "link" and "w" in u and p.get("clip"):
                p["scale"] = round(u["w"] / (p["clip"][2] - p["clip"][0]), 4)
            if "s" in u and p["kind"] in ("text", "area"):
                p["s"] = u["s"]
        pages.append(dict(no=no, frame=has_frame, parts=parts))
    M = 15.0
    out = dict(note="mock.pyが書き出す。Illustratorで build_sodachiya.jsx が読む。手で書き換えない（ユーザーの割付は layout_user.json）",
               generated=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
               unit="mm", artboard=[W, H],
               frame=dict(margin=M, header=16, title=dict(s="こどもたちの育ち舎", x=M + 4, y=M + 11, size_pt=pt(6.5), font="W6"),
                          footer=dict(s="建築設計実習Ⅱ—Ⅰ　2026.11.05　木田", x=W - M - 4, y=H - M - 4, size_pt=pt(3.0), font="W3", align="right"),
                          lw_rect=0.6, lw_header=0.4, color="#222222"),
               anchors=c.get("anchors", {}), anchors_prev=c.get("anchors_prev", {}),
               pages=pages)
    json.dump(out, open(os.path.join(AI, "layout.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("Illustratorの割付：", ", ".join(f"{p['no']}枚目 {len(p['parts'])}部品" for p in pages))
