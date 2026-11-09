"""仕上げ（2026-10-21）：同じ材のものを同じレイヤにまとめ、ガラスを透明にする。最後に実行。
python3 -I finish.py IN OUT"""
import sys, rhino3dm as r
IN, OUT = sys.argv[1], sys.argv[2]
m = r.File3dm.Read(IN)
MERGE = {
    '50d_本館_すき間の蓋（西館まで）': '50a_本館_越屋根_ガラスの蓋',
    '50_本館_越屋根_立ち上がり': '97_本館_外壁（西・南北の妻）',
    '50e_本館_越屋根_妻（壁と同じ材で閉じる）': '97_本館_外壁（西・南北の妻）',
    '70_西館_越屋根_立ち上がり': '21_西館_外壁',
    '70e_西館_越屋根_妻（壁と同じ材で閉じる）': '21_西館_外壁',
    '61_外構_南の縁側': '82_本館_外縁側（土足 −150）',
    '65_縁側の端のスロープ': '82_本館_外縁側（土足 −150）',
    '51_本館_南の軒': '10_本館_屋根',
}
LATTICE = '96b_しつらえ_格子・手すり（木）'
# 10-21：リポジトリの決まり（本体は 00〜69）に合わせて番号を付け直す
RENUM = {
    '70a_西館_越屋根_ガラスの蓋': '28_西館_越屋根_ガラスの蓋', '70b_西館_越屋根_LED': '29_西館_越屋根_LED',
    '70c_西館_越屋根_木のルーバー（白の艶消し）': '30_西館_越屋根_木のルーバー（白の艶消し）',
    '80_本館_床（はだし ±0）': '12_本館_床（はだし ±0）', '81_本館_内縁側（はだし ±0）': '13_本館_内縁側（はだし ±0）',
    '82_本館_外縁側（土足 −150）': '14_本館_外縁側（土足 −150）', '83_本館_海峡（土足 −150）': '15_本館_あまのがわ（土足 −150）', '83_本館_あまのがわ（土足 −150）': '15_本館_あまのがわ（土足 −150）',   # 海峡 → あまのがわ（ユーザー 10-28、本館係の add_floor.py が直す前も後も）
    '85_本館_断熱ガラス戸（縁側の中ほど）': '16_本館_断熱ガラス戸（縁側の中ほど）', '97_本館_外壁（西・南北の妻）': '17_本館_外壁（西・南北の妻）',
    '90_しつらえ_家具（スギ）': '37_しつらえ_家具（スギ）', '91_しつらえ_間仕切り・框・腰壁': '38_しつらえ_間仕切り・框・腰壁',
    '92_しつらえ_水まわり（便器・手洗い・沐浴）': '39_しつらえ_水まわり（便器・手洗い・沐浴）', '93_しつらえ_布・ござ・畳・クッション': '40_しつらえ_布・ござ・畳・クッション',
    '94_しつらえ_遊び（山・丘・ロフト・段々）': '46_しつらえ_遊び（山・丘・ロフト・段々）', '95_午睡時のコット（ふだんは片付け、非表示）': '47_午睡時のコット（ふだんは片付け、非表示）',
    '96_しつらえ_ガラス・窓': '48_しつらえ_ガラス・窓', '96b_しつらえ_格子・手すり（木）': '49_しつらえ_格子・手すり（木）',
    '98_外構_読書の庭（モミジ）': '67_外構_読書の庭（モミジ）', '98c_外構_読書の庭（モミジ）_樹冠（葉）': '67c_外構_読書の庭（モミジ）_樹冠（葉）', '99_しつらえ_頭上（天蓋・物干し・天袋）': '51_しつらえ_頭上（天蓋・物干し・天袋）',
}
GLASS = {'16_本館_断熱ガラス戸（縁側の中ほど）': 'clear', '48_しつらえ_ガラス・窓': 'clear', '27_西館_室内窓': 'clear',
         '50a_本館_越屋根_ガラスの蓋': 'clear', '28_西館_越屋根_ガラスの蓋': 'clear'}  # 10-24 透明（本館係・西館係）
old = {i: l for i, l in enumerate(m.Layers)}
n = r.File3dm(); n.Settings.ModelUnitSystem = r.UnitSystem.Millimeters
def mat(name, rgb, tr):
    a = r.Material(); a.Name = name; a.DiffuseColor = (*rgb, 255); a.Transparency = tr
    return n.Materials.Add(a)
MAT = {'clear': mat('ガラス（透明）', (205, 228, 238), 0.8), 'frost': mat('乳白ガラス', (238, 242, 245), 0.4)}
# 使われているレイヤだけを作り直す
used = {}
for o in m.Objects:
    name = old[o.Attributes.LayerIndex].FullPath
    name = MERGE.get(name, name)
    if name == '96_しつらえ_ガラス・窓・格子':
        name = '96_しつらえ_ガラス・窓'
        a = o.Attributes
        if a.ColorSource == r.ObjectColorSource.ColorFromObject and tuple(a.ObjectColor[:3]) in ((216, 191, 153), (217, 191, 153)):
            name = LATTICE
    if name == '96_しつらえ_ガラス・窓' and False: pass
    used.setdefault(RENUM.get(name, name), []).append(o)
byname = {l.FullPath: l for l in old.values()}
NEWIDX = {}
for name in sorted(used):
    if name not in used or name in NEWIDX: continue
    INV = {v: k for k, v in RENUM.items()}; oname = INV.get(name, name)
    src = byname.get(oname) or byname.get('96_しつらえ_ガラス・窓・格子' if oname=='96_しつらえ_ガラス・窓' else oname)
    L = r.Layer(); L.Name = name
    L.Color = src.Color if src is not None else (138, 106, 58, 255)
    if src is not None: L.Visible = src.Visible
    if name in GLASS: L.RenderMaterialIndex = MAT[GLASS[name]]
    NEWIDX[name] = n.Layers.Add(L)
for name, objs in used.items():
    for o in objs:
        a = o.Attributes.Duplicate() if hasattr(o.Attributes, 'Duplicate') else o.Attributes
        a.LayerIndex = NEWIDX[name]
        if name in GLASS:
            a.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; a.MaterialIndex = MAT[GLASS[name]]
            a.ColorSource = r.ObjectColorSource.ColorFromLayer
        if name in ('10_本館_屋根', '14_本館_外縁側（土足 −150）', '17_本館_外壁（西・南北の妻）', '21_西館_外壁'):
            a.ColorSource = r.ObjectColorSource.ColorFromLayer
        n.Objects.Add(o.Geometry, a)
APP = sys.argv[3] if len(sys.argv) > 3 else None
if APP:
    a3 = r.File3dm.Read(APP); AL = {i: l for i, l in enumerate(a3.Layers)}; amap = {}
    for o in a3.Objects:
        src = AL[o.Attributes.LayerIndex]
        if src.FullPath not in amap:
            L = r.Layer(); L.Name = src.FullPath; L.Color = src.Color; amap[src.FullPath] = n.Layers.Add(L)
        g = o.Geometry.Duplicate() if hasattr(o.Geometry, 'Duplicate') else o.Geometry
        g.Translate(r.Vector3d(0, 0, -300.0))
        at = o.Attributes; at.LayerIndex = amap[src.FullPath]
        n.Objects.Add(g, at)
    print('imported approach objects', len(a3.Objects))
n.Write(OUT, 8)
print('layers', len(NEWIDX), 'objects', sum(len(v) for v in used.values()))
