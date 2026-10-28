"""図面の文字と寸法を Illustrator の部品に（ユーザー 10-29 0:16：「全ての図面で数字やテキストや寸法線は動かしたり消したりできるように。
個々のテキストや寸法線と図をグルーピングしてください」）。ai_layout.py が使う。

- 文字と寸法は更新係の drawings/<紙の名前>_文字.pdf（draw100.py、同じ紙・同じ位置に文字と注記だけ）から読む：
  文字（行ごと：文・基準線の点・向き・大きさ・色）と、線と塗り（寸法線・端の印・高さの記号・通り芯の丸・字の白い地など）。
- 寸法は一つずつ（寸法線の一区間＋両端の補助線と斜線＋数字、続き寸法は区間ごとに切る）。ほかは近い物どうしをまとめる
  （高さの記号と値、通り芯の丸と番号、部屋名と面積、図名と縮尺、縮尺の棒と目盛り、注）。長い線（20 mm を超える）は、
  同じ色の短い物に端が触れるときだけまとめる（地盤の線・通り芯の線が全部をつながないように）。
- 自動の図（線と文字が一つの PDF）は、文字の層と同じ線と文字を中身から抜いた「線だけ」の写しを作る（lines_only）。
  Rhino の図（drawings_rhino/）はもともと線だけ。
"""
import os, re, math
import fitz
import numpy as np
from shapely.geometry import LineString, Point, box as sbox
from shapely.ops import substring

MM = 72 / 25.4
GREEN = "#2e7d32"
RED = "#b03030"


def _hex(c):
    if c is None:
        return None
    if isinstance(c, int):
        return "#%06x" % c
    return "#" + "".join("%02x" % int(round(v * 255)) for v in c[:3])


def _bez(p0, p1, p2, p3, n=8):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3


def _dash(d):
    if not d:
        return None
    m = re.match(r"\[\s*([^\]]*)\]", d)
    v = [float(x) for x in (m.group(1).split() if m else [])]
    return v or None


def read_moji(path, page=0):
    """文字の層を読む。座標は紙の mm（左上から、下へ y）"""
    pg = fitz.open(path)[page]
    D = []
    for k, d in enumerate(pg.get_drawings()):
        subs, cur = [], None
        for it in d["items"]:
            op = it[0]
            if op == "l":
                a, b = np.array([it[1].x, it[1].y]) / MM, np.array([it[2].x, it[2].y]) / MM
                if cur is None or np.linalg.norm(cur[-1] - a) > 1e-3:
                    cur = [a]; subs.append(cur)
                cur.append(b)
            elif op == "c":
                P = [np.array([q.x, q.y]) / MM for q in it[1:5]]
                if cur is None or np.linalg.norm(cur[-1] - P[0]) > 1e-3:
                    cur = [P[0]]; subs.append(cur)
                cur.extend(list(_bez(*P)))
            elif op == "re":
                r = it[1]
                subs.append([np.array([r.x0, r.y0]) / MM, np.array([r.x1, r.y0]) / MM, np.array([r.x1, r.y1]) / MM, np.array([r.x0, r.y1]) / MM, np.array([r.x0, r.y0]) / MM])
                cur = None
            elif op == "qu":
                q = it[1]
                subs.append([np.array([p.x, p.y]) / MM for p in (q.ul, q.ur, q.lr, q.ll, q.ul)])
                cur = None
        if not subs:
            continue
        typ = d.get("type") or "s"
        paths = []
        for s in subs:
            closed = bool(d.get("closePath")) or (len(s) > 2 and np.linalg.norm(s[0] - s[-1]) < 1e-3) or ("f" in typ)
            pts = [list(map(float, p)) for p in s]
            if closed and len(pts) > 2 and np.linalg.norm(np.array(pts[0]) - np.array(pts[-1])) < 1e-3:
                pts = pts[:-1]
            paths.append(dict(pts=pts, closed=bool(closed)))
        allp = np.array([p for s in paths for p in s["pts"]])
        D.append(dict(i=k, paths=paths, stroke=_hex(d.get("color")) if "s" in typ else None, fill=_hex(d.get("fill")) if "f" in typ else None,
                      lw=float(d.get("width") or 0), dash=_dash(d.get("dashes")), sop=float(d.get("stroke_opacity") or 1.0), fop=float(d.get("fill_opacity") or 1.0),
                      even_odd=bool(d.get("even_odd")), bb=(allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max())))
    T = []
    for b in pg.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            sp = [s for s in l["spans"] if s["text"].strip()]
            if not sp:
                continue
            s0 = sp[0]
            txt = "".join(s["text"] for s in l["spans"]).rstrip()
            u = np.array(l["dir"], float)
            o = np.array(s0["origin"], float) / MM
            bb = np.array(l["bbox"], float) / MM
            # 行の長さ（向きに沿って）：文字の箱の角を向きに射影
            cs = np.array([[bb[0], bb[1]], [bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]]])
            L = float(((cs - o) @ u).max())
            T.append(dict(s=txt, o=o, u=u, size=float(s0["size"]), color=_hex(s0["color"]),
                          bold=("Bold" in s0["font"]) or bool(s0["flags"] & 16), L=max(L, 0.1), bb=tuple(bb),
                          c=((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)))
    return T, D


def _seg(d):
    """一本のまっすぐな線（2点）なら (a, b)"""
    if len(d["paths"]) == 1 and len(d["paths"][0]["pts"]) == 2 and not d["fill"]:
        return np.array(d["paths"][0]["pts"][0]), np.array(d["paths"][0]["pts"][1])
    return None


def _line_of(d):
    if d["fill"] or len(d["paths"]) != 1 or d["paths"][0]["closed"]:
        return None
    pts = d["paths"][0]["pts"]
    return LineString(pts) if len(pts) >= 2 else None


def _inter(a, b, e=0.0):
    return not (a[2] + e < b[0] or b[2] + e < a[0] or a[3] + e < b[1] or b[3] + e < a[1])


def cluster(T, D):
    """部品のまとまり：[dict(kind, name, texts=[T], draws=[(D, 切り出した線 or None)])]"""
    used_d, used_t = set(), set()
    # 字の白い地（塗りだけの白）を、その字に付ける
    box_of = {}
    for d in D:
        if d["fill"] == "#ffffff" and not d["stroke"]:
            for j, t in enumerate(T):
                if d["bb"][0] - 0.2 <= t["c"][0] <= d["bb"][2] + 0.2 and d["bb"][1] - 0.2 <= t["c"][1] <= d["bb"][3] + 0.2 and \
                        (d["bb"][2] - d["bb"][0]) * (d["bb"][3] - d["bb"][1]) < 4 * max(1.0, (t["bb"][2] - t["bb"][0]) * (t["bb"][3] - t["bb"][1])):
                    box_of.setdefault(j, []).append(d["i"]); break
    DI = {d["i"]: d for d in D}
    # 1) 寸法：緑の線で、端の印（短い線）が2つ以上かかるもの
    green = [d for d in D if d["stroke"] == GREEN and not d["fill"]]
    marks = []
    for d in green:
        sg = _seg(d)
        if sg is not None and np.linalg.norm(sg[1] - sg[0]) <= 6.0:
            marks.append((d, sg))
    dimlines = []
    for d in green:
        ls = _line_of(d)
        if ls is None or ls.length <= 3.0:
            continue
        ends = []
        for m, (a, b) in marks:
            if m is d:
                continue
            mid = Point((a + b) / 2)
            if ls.distance(mid) > 0.35:
                continue
            s_ = ls.project(mid)
            p0, p1 = np.array(ls.interpolate(max(s_ - 0.2, 0)).coords[0]), np.array(ls.interpolate(min(s_ + 0.2, ls.length)).coords[0])
            tv = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-9); mv = (b - a) / max(np.linalg.norm(b - a), 1e-9)
            if abs(float(tv @ mv)) > 0.9:
                continue
            ends.append((s_, m))
        pos = sorted(set(round(s_, 1) for s_, _ in ends))
        if len(pos) >= 2:
            dimlines.append(dict(d=d, ls=ls, ends=ends, pos=pos))
    dims = {}
    for j, t in enumerate(T):
        if t["color"] != GREEN:
            continue
        best = None
        c = Point(t["c"])
        for k, dl in enumerate(dimlines):
            ls = dl["ls"]
            dist = ls.distance(c)
            if dist > 7.0:
                continue
            s_ = ls.project(c)
            if s_ <= 0.05 or s_ >= ls.length - 0.05:
                continue
            p0, p1 = np.array(ls.interpolate(max(s_ - 0.5, 0)).coords[0]), np.array(ls.interpolate(min(s_ + 0.5, ls.length)).coords[0])
            tv = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-9)
            if abs(float(tv @ t["u"])) < 0.97:
                continue
            if best is None or dist < best[0]:
                best = (dist, k, s_)
        if best is None:
            continue
        _, k, s_ = best
        pos = dimlines[k]["pos"]
        a = max([p for p in pos if p <= s_ + 1e-6], default=0.0)
        b = min([p for p in pos if p >= s_ - 1e-6], default=dimlines[k]["ls"].length)
        dims.setdefault((k, a, b), []).append(j)
    # 区間に字の無い所（続き寸法の短い区間）は、となりの寸法に入れる
    covered = {}
    for (k, a, b) in dims:
        covered.setdefault(k, []).append((a, b))
    extra = {}
    for k, iv in covered.items():
        pos = dimlines[k]["pos"]
        full = [0.0] + pos + [dimlines[k]["ls"].length]
        for a, b in zip(full, full[1:]):
            if b - a < 1e-3 or any(abs(a - x) < 1e-3 and abs(b - y) < 1e-3 for x, y in iv):
                continue
            near = min(iv, key=lambda q: min(abs(q[0] - b), abs(q[1] - a)))
            extra.setdefault((k,) + near, []).append((a, b))
    out = []
    for (k, a, b), js in dims.items():
        dl = dimlines[k]
        spans = [(a, b)] + extra.get((k, a, b), [])
        draws = []
        for (x, y) in spans:
            sub = substring(dl["ls"], x, y)
            if sub.length > 1e-3:
                draws.append((dl["d"], [list(map(float, q)) for q in sub.coords]))
        endpos = set()
        for (x, y) in spans:
            endpos |= {x, y}
        for s_, m in dl["ends"]:
            if any(abs(s_ - e) < 0.3 for e in endpos):
                draws.append((m, None)); used_d.add(m["i"])
        for j in js:
            for bi in box_of.get(j, []):
                draws.append((DI[bi], None)); used_d.add(bi)
        used_d.add(dl["d"]["i"])
        used_t |= set(js)
        out.append(dict(kind="dim", texts=[T[j] for j in sorted(js, key=lambda j: (T[j]["o"] @ np.array([-T[j]["u"][1], T[j]["u"][0]])))], draws=draws))
    # 2) 残りは近い物どうし
    items = [("t", j) for j in range(len(T)) if j not in used_t] + [("d", d["i"]) for d in D if d["i"] not in used_d and not any(d["i"] in v for v in box_of.values())]
    par = list(range(len(items)))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x

    def bbx(it):
        return T[it[1]]["bb"] if it[0] == "t" else DI[it[1]]["bb"]

    def is_long(it):
        b = bbx(it)
        return it[0] == "d" and max(b[2] - b[0], b[3] - b[1]) > 20.0

    def color(it):
        return T[it[1]]["color"] if it[0] == "t" else (DI[it[1]]["stroke"] or DI[it[1]]["fill"])

    for x in range(len(items)):
        for y in range(x + 1, len(items)):
            A, B = items[x], items[y]
            la, lb = is_long(A), is_long(B)
            if not la and not lb:
                e_ = 1.2 if (A[0] != B[0] and color(A) == color(B)) else 0.6     # 字と同じ色の印（高さの記号と値）は少し離れていても
                if _inter(bbx(A), bbx(B), e_):
                    par[f(x)] = f(y)
            elif la and lb:
                continue
            else:
                L_, S_ = (A, B) if la else (B, A)
                if S_[0] != "d" or color(L_) != color(S_):
                    continue
                sb = bbx(S_)
                sc = np.array([(sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2])
                for p_ in DI[L_[1]]["paths"]:
                    for e, e2 in ((p_["pts"][0], p_["pts"][1]), (p_["pts"][-1], p_["pts"][-2])):
                        if sb[0] - 1.5 <= e[0] <= sb[2] + 1.5 and sb[1] - 1.5 <= e[1] <= sb[3] + 1.5:
                            par[f(x)] = f(y)
                        else:                           # 線の延長の先 15 mm までに丸の中心（通り芯の線と丸のあいだがあいている）
                            e, e2 = np.array(e), np.array(e2)
                            v = (e - e2) / max(np.linalg.norm(e - e2), 1e-9)
                            al, pe = float((sc - e) @ v), abs(float(v[0] * (sc - e)[1] - v[1] * (sc - e)[0]))
                            if 0 < al <= 15.0 and pe < 0.6:
                                par[f(x)] = f(y)
    groups = {}
    for x in range(len(items)):
        groups.setdefault(f(x), []).append(items[x])
    for g in groups.values():
        ts = [T[j] for k_, j in g if k_ == "t"]
        js = [j for k_, j in g if k_ == "t"]
        ds = [(DI[i], None) for k_, i in g if k_ == "d"]
        for j in js:
            ds += [(DI[bi], None) for bi in box_of.get(j, [])]
        ts.sort(key=lambda t: (round(t["o"][1], 1), t["o"][0]))
        out.append(dict(kind=_kind(ts, [d for d, _ in ds]), texts=ts, draws=ds))
    for g in out:
        g["draws"].sort(key=lambda q: q[0]["i"])          # もとの重なりの順（白い地は字の下、線の上）
    return out


def _kind(ts, ds):
    s = " ".join(t["s"] for t in ts)
    if ts and all(re.fullmatch(r"[A-Z]", t["s"].strip()) for t in ts) and ds:
        return "cut"
    if any(t["size"] >= 10 for t in ts):
        return "title"
    if ts and all(t["color"] == RED for t in ts):
        return "grid"
    if ts and any(t["color"] == GREEN and re.search(r"[+±−]\s*[\d,]+$|[+±−][\d,]+", t["s"]) for t in ts):
        return "level"
    if "m²" in s:
        return "room"
    if ts and any(re.fullmatch(r"\d+\s*m", t["s"].strip()) for t in ts) and any(d["fill"] for d in ds):
        return "scale"
    if not ts:
        return "line"
    return "note"


KIND_NAME = dict(dim="寸法", title="図名", cut="断面の位置", grid="通り芯", level="高さ", room="部屋名", scale="縮尺", line="線", note="注")


def _slug(s, n=16):
    s = re.sub(r"[\s　/\\|:.~]+", "", s)
    return s[:n] or "x"


def parts_for(path, clip, dest_tl, scale, key, page=0):
    """文字の層の、切り抜く範囲（clip：紙の mm（左・上・右・下）、None は紙全体）の中の物を部品に。
    dest_tl：.ai の紙の上の置き場所（切り抜きの左上、mm）。戻り値は ai_layout の部品（id は p番号を付ける前）"""
    T, D = read_moji(path, page)
    pr = fitz.open(path)[page].rect
    cl = clip or (0, 0, pr.width / MM, pr.height / MM)
    X = lambda q: [round(dest_tl[0] + (q[0] - cl[0]) * scale, 3), round(dest_tl[1] + (q[1] - cl[1]) * scale, 3)]
    groups = cluster(T, D)
    # 切り抜く範囲の中（まとまりの外形の中心が中、かつ外形が 3 mm より外へ出ない）
    keep = []
    for g in groups:
        bbs = [t["bb"] for t in g["texts"]] + [d["bb"] if sub is None else (min(p[0] for p in sub), min(p[1] for p in sub), max(p[0] for p in sub), max(p[1] for p in sub)) for d, sub in g["draws"]]
        b = (min(q[0] for q in bbs), min(q[1] for q in bbs), max(q[2] for q in bbs), max(q[3] for q in bbs))
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if not (cl[0] <= cx <= cl[2] and cl[1] <= cy <= cl[3]):
            continue
        if b[0] < cl[0] - 3 or b[1] < cl[1] - 3 or b[2] > cl[2] + 3 or b[3] > cl[3] + 3:
            continue
        g["bb"] = b
        keep.append(g)
    keep.sort(key=lambda g: (round(g["bb"][1] / 2), g["bb"][0]))
    seen, parts = {}, []
    for g in keep:
        label = "　".join(t["s"] for t in g["texts"])[:28] if g["texts"] else ""
        kn = KIND_NAME[g["kind"]]
        # 鍵は文字から（同じ文字が多いときは位置の順に ~2, ~3）。文字の無い線は、もとの図の上の位置（5 mm 刻み）から
        base = f"dwg.{key}.{g['kind']}." + (_slug(label) if label else f"{int(round((g['bb'][0] + g['bb'][2]) / 10) * 5)}_{int(round((g['bb'][1] + g['bb'][3]) / 10) * 5)}")
        n = seen.get(base, 0) + 1; seen[base] = n
        gid = base + (f"~{n}" if n > 1 else "")
        gname = f"{kn}　{label}" if label else kn
        multi = (1 if g["draws"] else 0) + len(g["texts"]) > 1
        grp = dict(group=gid, group_name=gname) if multi else {}
        if g["draws"]:
            paths = []
            for d, sub in g["draws"]:
                src = [dict(pts=sub, closed=False)] if sub is not None else d["paths"]
                for p_ in src:
                    paths.append(dict(pts=[X(q) for q in p_["pts"]], closed=bool(p_["closed"]), stroke=d["stroke"], fill=d["fill"],
                                      lw=round(d["lw"] * scale, 3), dash=[round(v * scale, 3) for v in d["dash"]] if d["dash"] else None,
                                      op=round(min(d["sop"] if d["stroke"] else 1.0, d["fop"] if d["fill"] else 1.0), 3), eo=bool(d["even_odd"])))
            allp = np.array([q for p_ in paths for q in p_["pts"]])
            x0, y0 = allp.min(0); x1, y1 = allp.max(0)
            geo = "|".join(",".join(f"{q[0] - x0:.2f}:{q[1] - y0:.2f}" for q in p_["pts"]) + f";{p_['stroke']};{p_['fill']};{p_['lw']}" for p_ in paths)
            parts.append(dict(id=gid + ".l", name=("線　" + label if label else gname) if multi else gname, kind="lines", layer="図",
                              x=round(float(x0), 2), y=round(float(y0), 2), w=round(float(x1 - x0), 2), h=round(float(y1 - y0), 2),
                              paths=paths, geo=geo, **grp))
        for k, t in enumerate(g["texts"]):
            ctr = t["o"] + t["u"] * (t["L"] / 2)              # 基準線の真ん中（書体が変わっても字の真ん中がそろう）
            P = X(ctr)
            ang = math.degrees(math.atan2(-t["u"][1], t["u"][0]))
            parts.append(dict(id=gid + (".t" if k == 0 else f".t{k + 1}"), name=t["s"][:24], kind="text", layer="図", x=round(P[0], 2), y=round(P[1], 2),
                              s=t["s"], size_pt=round(t["size"] * scale, 2), font="W6" if t["bold"] else "W3", color=t["color"] or "#000000",
                              align="center", **({"rot": round(ang, 2)} if abs(ang) > 0.05 else {}), **grp))
    return parts


# ---------------------------------------------------------------- 線だけの写し（自動の図から、文字の層と同じ線と文字を抜く）
def lines_only(full, moji, out):
    """full（線と文字）から、moji（同じ紙の文字の層）にある線と文字を抜いた PDF を out に。変わらなければ書かない。戻り値：抜いた数"""
    import pikepdf
    from collections import Counter

    PAINT = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"}
    BUILD = {"m", "l", "c", "v", "y", "h", "re"}

    def segs(ops):
        """[(始まり, 終わり, 印)]：パスを作る演算の並びと塗る演算までを一つに（切り抜き W n は除く）"""
        res, st, sig = [], None, []
        for i, o in enumerate(ops):
            op = str(o.operator)
            if op in BUILD:
                if st is None:
                    st, sig = i, []
                sig.append(op + ":" + ",".join(f"{float(v):.2f}" for v in o.operands))
            elif op in ("W", "W*"):
                st = None
            elif op in PAINT:
                if st is not None and op != "n":
                    res.append((st, i, op + "|" + ";".join(sig)))
                st = None
        return res

    def texts(ops):
        res, st = [], None
        for i, o in enumerate(ops):
            op = str(o.operator)
            if op == "BT":
                st = i
            elif op == "ET" and st is not None:
                res.append((st, i)); st = None
        return res

    pf = pikepdf.open(full)
    pm = pikepdf.open(moji)
    of, om = pikepdf.parse_content_stream(pf.pages[0]), pikepdf.parse_content_stream(pm.pages[0])
    want = Counter(s for _, _, s in segs(om))
    drop = set()
    n = 0
    for a, b, s in segs(of):
        if want.get(s, 0) > 0:
            want[s] -= 1
            drop.update(range(a, b + 1)); n += 1
    for a, b in texts(of):
        drop.update(range(a, b + 1)); n += 1
    keep = [o for i, o in enumerate(of) if i not in drop]
    pf.pages[0].Contents = pf.make_stream(pikepdf.unparse_content_stream(keep))
    tmp = out + ".tmp"
    pf.save(tmp, static_id=True, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    if os.path.exists(out) and open(out, "rb").read() == open(tmp, "rb").read():
        os.remove(tmp)
    else:
        os.replace(tmp, out)
    return n, sum(want.values())
