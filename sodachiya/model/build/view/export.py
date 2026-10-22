"""3dm（メッシュ版）→ glb（レイヤーごとのノード、色はレイヤー色）"""
import sys, numpy as np, rhino3dm as r, trimesh, re
sys.path.insert(0, '/tmp/claude-0/t/view'); import tri
IN, OUT = sys.argv[1:3]
SKIP = tuple(sys.argv[3].split(',')) if len(sys.argv) > 3 and sys.argv[3] else ()
m = r.File3dm.Read(IN)
scene = trimesh.Scene(); groups = {}
for o in m.Objects:
    L = m.Layers[o.Attributes.LayerIndex]; ln = L.Name
    if ln.startswith(SKIP) or not L.Visible: continue
    g = o.Geometry
    if isinstance(g, r.Mesh):
        V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))]) / 1000.0
        F = []
        for i in range(g.Faces.Count):
            f = g.Faces[i]; F.append(f[:3])
            if f[2] != f[3]: F.append((f[0], f[2], f[3]))
    elif isinstance(g, (r.Extrusion, r.Brep)):
        T = tri.tri_extrusion(g) if isinstance(g, r.Extrusion) else tri.tri_brep(g)
        if len(T) == 0: continue
        V = T.reshape(-1, 3) / 1000.0; F = np.arange(len(V)).reshape(-1, 3).tolist()
    else: continue
    if not len(F): continue
    c = o.Attributes.ObjectColor if o.Attributes.ColorSource == r.ObjectColorSource.ColorFromObject else L.Color
    groups.setdefault(ln, []).append((V, np.array(F), c))
for ln, items in groups.items():
    Vs, Fs, Cs, off = [], [], [], 0
    for V, F, c in items:
        Vs.append(V); Fs.append(F + off); off += len(V)
        Cs.append(np.tile([c[0], c[1], c[2], 255], (len(V), 1)))
    tm = trimesh.Trimesh(np.vstack(Vs)[:, [0, 2, 1]] * [1, 1, -1], np.vstack(Fs)[:, ::-1], vertex_colors=np.vstack(Cs), process=False)
    scene.add_geometry(tm, node_name=re.sub(r'[^0-9A-Za-z_]', '', ln.split('_')[0]) + '|' + ln, geom_name=ln)
scene.export(OUT); print('glb', OUT, len(groups), 'layers')
