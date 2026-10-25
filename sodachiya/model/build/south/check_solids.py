"""Rhino 版の確かめ（ソリッド係、10-25）：python3 check_solids.py MESH.3dm RHINO.3dm
- すべての押し出し・ポリサーフェスが IsValid かつ IsSolid、メッシュが閉じているか。
- 形のずれ：ポリサーフェス・押し出しの辺の上の点が、もとのメッシュの面から何 mm 離れているか（物ごとの最大）。
  もとが閉じていない面（厚みをつけた物）は除く。
  曲面に戻した所は、細かく分けた面（弦）との差（数 mm 以下）が出る。
"""
import sys, collections, numpy as np, rhino3dm as r, trimesh

MESH, RH = sys.argv[1], sys.argv[2]
m0 = r.File3dm.Read(MESH); m1 = r.File3dm.Read(RH)
L1 = [l.Name for l in m1.Layers]
kinds = collections.Counter(); bad = []
src = collections.defaultdict(list)
for o in m1.Objects:
    g = o.Geometry; k = type(g).__name__; ln = L1[o.Attributes.LayerIndex]
    if isinstance(g, (r.Brep, r.Extrusion)):
        ok = g.IsValid and g.IsSolid; kinds[k, ok] += 1
        if not ok: bad.append((ln, k))
    elif isinstance(g, r.Mesh):
        kinds[k, g.IsClosed] += 1
        if not g.IsClosed: bad.append((ln, k))
    else: kinds[k] += 1
    s = o.Attributes.GetUserString('src')
    if s and isinstance(g, (r.Brep, r.Extrusion)): src[int(s)].append(g)
print('物の数:', dict(kinds))
print('閉じたソリッドでない物:', bad or 'なし')
dev = []
for i, gs in src.items():
    g0 = m0.Objects[i].Geometry
    if not isinstance(g0, r.Mesh): continue
    V = np.array([[v.X, v.Y, v.Z] for v in g0.Vertices]); F = []
    for j in range(g0.Faces.Count):
        f = g0.Faces[j]; F.append((f[0], f[1], f[2]))
        if f[3] != f[2]: F.append((f[0], f[2], f[3]))
    tm = trimesh.Trimesh(V, np.array(F), process=False)
    if not trimesh.Trimesh(V, np.array(F)).is_watertight: continue      # 厚みをつけた面（ずれは厚みの分）は除く
    pts = []
    for g in gs:
        b = g.ToBrep(False) if isinstance(g, r.Extrusion) else g
        for k in range(len(b.Edges)):
            e = b.Edges[k]; d = e.Domain
            for t in np.linspace(d.T0, d.T1, 7):
                p = e.PointAt(t); pts.append((p.X, p.Y, p.Z))
    if not pts: continue
    pts = np.array(pts)
    if len(pts) > 4000: pts = pts[np.random.default_rng(0).choice(len(pts), 4000, replace=False)]
    _, dist, _ = trimesh.proximity.closest_point(tm, pts)
    dev.append((float(dist.max()), m0.Layers[m0.Objects[i].Attributes.LayerIndex].Name, i))
dev.sort(reverse=True)
print('辺の点ともとのメッシュのずれ（物ごとの最大、mm）：上位', [(round(d, 2), ln[:16], i) for d, ln, i in dev[:15]])
print('ずれ 1 mm 超の物', sum(d > 1 for d, _, _ in dev), '/', len(dev), '　5 mm 超', sum(d > 5 for d, _, _ in dev))
