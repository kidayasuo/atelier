"""遊戯室の遊具（80〜88）を、遊戯室のチャットの取り込み用ファイルで置き換える
使い方: python3 add_play_import.py IN.3dm OUT.3dm model/sodachiya_play_layers.3dm
- IN の 80〜88 の物を消し、取り込み用ファイルの物を同じ番号のレイヤーへ（レイヤーの名前は取り込み用ファイルの名前にそろえる）。
- 89（搬入の大戸）と外壁の開口・床の板 31 の穴は add_west_south.py / add_play.py のまま。
"""
import sys, re, rhino3dm as r

IN, OUT, PF = sys.argv[1:4]
m = r.File3dm.Read(IN); p = r.File3dm.Read(PF)
code = lambda n: (re.match(r'^(\d+)', n) or [None, None])[1]
REPL = {str(c) for c in range(80, 89)}
have = {code(l.Name): i for i, l in enumerate(m.Layers) if code(l.Name) in REPL}

out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
mp = {}; LS = [m.Layers[i] for i in range(len(m.Layers))]
for i, l in enumerate(p.Layers):
    c = code(l.Name)
    if c in have: LS[have[c]].Name = l.Name; mp[i] = have[c]
for l in LS: out.Layers.Add(l)
for i, l in enumerate(p.Layers):
    if i not in mp:
        nl = r.Layer(); nl.Name = l.Name; nl.Color = l.Color; mp[i] = out.Layers.Add(nl)
for mt in m.Materials: out.Materials.Add(mt)
drop = set(have.values()); n0 = 0
for o in m.Objects:
    if o.Attributes.LayerIndex in drop: n0 += 1; continue
    out.Objects.Add(o.Geometry, o.Attributes)
n1 = 0
for o in p.Objects:
    a = o.Attributes; a.LayerIndex = mp[a.LayerIndex]; out.Objects.Add(o.Geometry, a); n1 += 1
out.Write(OUT, 8); print('play: removed', n0, 'imported', n1, '→', OUT, len(out.Objects))
