"""作り直した面積表と干渉の一覧を、リポジトリの前の版（git の HEAD）と比べる（設計監修、10-24。本館係の依頼）。
10-27から、push のたびの自動の作り直し（GitHub Actions、.github/workflows/sodachiya_build.yml）でも走る。止めるが出たら push せず、連携の項を立てる。

使い方: python3 check_build.py REPO NEWDIR [REPORT.txt]
  REPO    sodachiya/ の場所
  NEWDIR  作り直した sodachiya_areas.json・sodachiya_clash.json のある所（model/drawings か preview の model/drawings）
止める（終わりの値 1）：
  - 課題の判定が○だった部屋が○でなくなった、または判定が○でも空でもない部屋がある
  - 延床が上限（2,000）を超えた
  - 干渉の一覧の「屋根から出る・屋根の外へ出る構造・埋まったガラス」が前より増えた
知らせる（止めない）：
  - 面積が0.5 m²より大きく変わった部屋（触っていない部屋が変わっていたら、古い写しや取り違えを疑う）
  - 種類をまたぐ食い込みが増えた
  - 力の道（10-29、段14 load_path.py の sodachiya_loadpath.json・.txt があれば）：check の行に数、下に節
  - 形が素直でない物（10-31）：Rhino版（NEWDIR/../../sodachiya.3dm）のレイヤーごとの数が前の版より増えた。数は NEWDIR/sodachiya_katachi.txt
"""
import sys, os, json, subprocess

REPO, NEW = sys.argv[1], sys.argv[2]
REPORT = sys.argv[3] if len(sys.argv) > 3 else None
REL = 'sodachiya/model/drawings/'


def old(name):
    top = subprocess.run(['git', '-C', REPO, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
    rel = os.path.relpath(os.path.join(REPO, 'model/drawings', name), top)
    r = subprocess.run(['git', '-C', top, 'show', 'HEAD:' + rel], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def rooms(a):
    d = {}
    for r in a.get('rooms', []):
        d[r['room']] = (r.get('planned'), r.get('judge', ''))
    for r in a.get('other', []):
        d[r['room']] = (r.get('planned'), '')
    return d


stop, warn, info = [], [], []
na = json.load(open(os.path.join(NEW, 'sodachiya_areas.json')))
oa = old('sodachiya_areas.json')
nr = rooms(na)
orr = rooms(oa) if oa else {}
for k, (p, j) in nr.items():
    pj = orr.get(k, (None, ''))[1]
    if j not in ('○', ''):
        stop.append(f'課題の判定：{k} {p} が「{j}」')
    elif pj == '○' and j != '○':
        stop.append(f'課題の判定：{k} が○でなくなった（{orr[k][0]} → {p}）')
    op = orr.get(k, (None, ''))[0]
    if op is not None and p is not None and abs(p - op) > 0.5:
        warn.append(f'面積が変わった：{k} {op} → {p}（{p - op:+.1f}）')
    elif k not in orr and oa:
        warn.append(f'新しい部屋：{k} {p}')
for k in orr:
    if k not in nr:
        warn.append(f'無くなった部屋：{k}')
fl = na['floor']
if fl['total'] > fl.get('limit', 2000):
    stop.append(f'延床 {fl["total"]} が上限 {fl.get("limit", 2000)} を超えた')
if oa:
    info.append(f'延床 {oa["floor"]["total"]} → {fl["total"]}')
else:
    info.append(f'延床 {fl["total"]}（前の版が無い）')

nc = json.load(open(os.path.join(NEW, 'sodachiya_clash.json')))
oc = old('sodachiya_clash.json') or {}
for key, name in (('poke', '屋根から出る'), ('out_s', '屋根の外へ出る構造'), ('buried', '埋まったガラス')):
    n, o = len(nc.get(key, [])), len(oc.get(key, [])) if oc else 0
    if n > o:
        stop.append(f'干渉：{name} {o} → {n}')
    info.append(f'{name} {n}')
n, o = len(nc.get('cross', [])), len(oc.get('cross', [])) if oc else 0
if n > o:
    warn.append(f'干渉：種類をまたぐ食い込み {o} → {n}')
info.append(f'種類をまたぐ食い込み {n}')

# 力の道の点検（10-29、load_path.py の段 14）：知らせだけ（止めない）。数は check の行に、中身は下の節に
lp_txt, lp_json = os.path.join(NEW, 'sodachiya_loadpath.txt'), os.path.join(NEW, 'sodachiya_loadpath.json')
lp_sec = []
if os.path.exists(lp_json) and os.path.exists(lp_txt):
    try:
        lp = json.load(open(lp_json))
        info.append(f'力が地面に届かない{len(lp["floating"])}・金物頼みだけ{len(lp["hardware_only"])}')
        lp_sec = [''] + open(lp_txt).read().rstrip('\n').split('\n')
    except Exception as e:
        warn.append(f'力の道の点検が読めない（{e}）')

# 形が素直でない物（10-31 効率化委員会、ユーザー：新しい部材が毎回三角形の網や妙な片になる。kettei/kanshu.md の点検の7）：
# Rhino版の、自由な形のレイヤー（KATACHI_FREE）でない所のメッシュ・面が KATACHI_FACES より多いポリサーフェス・閉じていない物を
# レイヤーごとに数え、sodachiya_katachi.txt に書く。前の版（HEAD）より増えたレイヤーを知らせる（止めない）。前の版が無ければ書くだけ
KATACHI_FREE = ('85', '90', '92', '92s', '99', '78')     # クスノキ・地形・水・雨庭の玉石の層（くぼみに沿う、ユーザー 10-31）・雨の川・みなみのさんかくの丘（clean_wire.py の FREEFORM と 85・78）
KATACHI_FACES = 30
k3dm = os.path.join(NEW, '..', '..', 'sodachiya.3dm')
if os.path.exists(k3dm):
    try:
        import rhino3dm as r3
        km = r3.File3dm.Read(k3dm); kn = {}
        kl = [km.Layers[i].Name for i in range(len(km.Layers))]
        for o in km.Objects:
            g = o.Geometry; ln = kl[o.Attributes.LayerIndex]
            if ln.split('_')[0] in KATACHI_FREE or ln.startswith('床の絵') or o.Attributes.GetUserString('etch_of'): continue      # 床の絵の板は絵を貼るためのメッシュ（materials.py）
            # 例外（10-31 監修、西館係の項 1620）：西館の外壁21（一つの閉じた立体＝外壁の輪の押し出し−開口＋水切り、角の丸み）と
            # 2階床23（丸い壁に沿う輪郭の押し出し）は面が多くてよい。平らな面だけでも面が多い物は例外にしない（曲線を細かい平面で近似した物を見逃すため、ユーザー）
            many = isinstance(g, r3.Brep) and len(g.Faces) > KATACHI_FACES and ln.split('_')[0] not in ('21', '23')
            bad = isinstance(g, r3.Mesh) or (isinstance(g, r3.Brep) and (many or not g.IsSolid)) \
                or (isinstance(g, r3.Extrusion) and not g.IsSolid)
            if bad: kn[ln] = kn.get(ln, 0) + 1
        ktxt = ''.join(f'{v}\t{k}\n' for k, v in sorted(kn.items()))
        open(os.path.join(NEW, 'sodachiya_katachi.txt'), 'w').write(
            f'# 形が素直でない物（メッシュ・{KATACHI_FACES}面より多いポリサーフェス・閉じていない物）のレイヤーごとの数。check_build.py が書く\n' + ktxt)
        top = subprocess.run(['git', '-C', REPO, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
        rel = os.path.relpath(os.path.join(REPO, 'model/drawings', 'sodachiya_katachi.txt'), top)
        ro = subprocess.run(['git', '-C', top, 'show', 'HEAD:' + rel], capture_output=True, text=True)
        info.append(f'形が素直でない物 {sum(kn.values())}')
        if ro.returncode == 0:
            ko = {}
            for l in ro.stdout.splitlines():
                if l and not l.startswith('#') and '\t' in l:
                    v, k = l.split('\t', 1); ko[k] = int(v)
            up = [f'{k.split("（")[0]} {ko.get(k, 0)}→{v}' for k, v in sorted(kn.items()) if v > ko.get(k, 0)]
            if up: warn.append('形が素直でない物が増えた（直方体・押し出しで作る、katachi.py）：' + '、'.join(up))
    except Exception as e:
        warn.append(f'形の数えができない（{e}）')

L = ['check: ' +('止める（直してから作り直す）' if stop else '通った') + '　' + '・'.join(info)]
L += ['  ✗ ' + s for s in stop] + ['  ! ' + s for s in warn] + lp_sec
txt = '\n'.join(L)
print(txt)
if REPORT:
    open(REPORT, 'w').write(txt + '\n')
sys.exit(1 if stop else 0)
