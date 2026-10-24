"""作り直しの各段が読んだファイルを記録する（設計監修、10-24。本館係の依頼：古い写しで面積が狂った件）。

run_all.sh が各段を strace で包み、開いたファイルを $OUT/reads_<段>.raw に書く。このスクリプトはそれを
  - 段ごとの「読んだもの」（リポジトリの場所に直した一覧）$OUT/reads_<段>.txt
  - 前半（しつらえまで）の指紋 $OUT/s4.sha（読んだファイルの sha256）
  - 段ごとの表 model/build/stages.md（データを変えたチャットが「どの段から作り直しが要るか」を見る表）
にまとめる。作業場 /tmp/claude-0/t の写しは、リポジトリの元の場所に読み替える。

使い方:
  python3 reads.py collect OUT REPO            … reads_*.raw → reads_*.txt
  python3 reads.py fingerprint OUT S0 S1 ...   … 指定の段の読んだファイルの sha256 を OUT/s4.sha へ
  python3 reads.py verify OUT                  … s4.sha が今のファイルと合えば 0、違えば 1（違うファイルを出す）
  python3 reads.py table OUT REPO OUT.md       … 段ごとの表
"""
import sys, os, re, hashlib, glob, json

T = '/tmp/claude-0/t'
# 作業場の写し → リポジトリの元（sodachiya/ からの相対）
MAP = [
    (T + '/south/', 'model/build/south/'),
    (T + '/shitsu/', 'model/build/shitsu/'),
    (T + '/ideas/roof_geo.py', 'model/build/ideas/roof_geo.py'),
    (T + '/exact/wnew.pkl', 'data/wnew.pkl'),
    ('/home/claude/plans/rhino/', 'model/build/vendor/plans_rhino/'),
    ('/tmp/claude-0/mock2/', 'model/build/vendor/mock2/'),
    (T + '/', 'archive/handoff_1018/t/'),
]
SKIP = ('/usr/', '/proc/', '/sys/', '/dev/', '/etc/', '/lib', '/root/.', '/opt/', '/var/', '/bin', '/sbin', '/run/')
LINE = re.compile(r'openat\([^,]+, "([^"]+)", ([A-Z_|]+)')


def repo_rel(path, repo):
    p = os.path.realpath(path)
    for a, b in MAP:
        if p.startswith(a) or p == a.rstrip('/'):
            return b + p[len(a):] if a.endswith('/') else b
    r = os.path.realpath(repo)
    if p.startswith(r + '/'):
        return p[len(r) + 1:]
    return None


def collect(out, repo):
    outr = os.path.realpath(out)
    for raw in sorted(glob.glob(os.path.join(out, 'reads_*.raw'))):
        keep = {}
        for ln in open(raw, errors='replace'):
            m = LINE.search(ln)
            if not m or 'O_RDONLY' not in m.group(2) or 'O_DIRECTORY' in m.group(2):
                continue
            p = m.group(1)
            if p.startswith(SKIP) or '/site-packages/' in p or '/dist-packages/' in p or '__pycache__' in p:
                continue
            if not os.path.isfile(p):
                continue
            rp = os.path.realpath(p)
            if rp.startswith(outr + '/'):
                keep[rp] = '（作り直しの途中の写し）' + os.path.basename(rp)
                continue
            rel = repo_rel(rp, repo)
            if rel is None or rel.startswith('model/build/vendor/mock2/') and rel.endswith('.pyc'):
                continue
            keep[rp] = rel
        with open(raw[:-4] + '.txt', 'w') as f:
            for rp, rel in sorted(keep.items(), key=lambda kv: kv[1]):
                f.write(f'{rp}\t{rel}\n')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fingerprint(out, stages):
    files = {}
    for s in stages:
        for ln in open(os.path.join(out, f'reads_{s}.txt')):
            rp, rel = ln.rstrip('\n').split('\t')
            if not rel.startswith('（'):
                files[rp] = rel
    with open(os.path.join(out, 's4.sha'), 'w') as f:
        for rp, rel in sorted(files.items(), key=lambda kv: kv[1]):
            f.write(f'{sha(rp)}\t{rp}\t{rel}\n')
    print(f'reads: 前半の指紋 {len(files)} ファイル → {out}/s4.sha')


def verify(out):
    fn = os.path.join(out, 's4.sha')
    if not os.path.isfile(fn):
        print('reads: 前半の指紋が無い')
        return 1
    bad = []
    for ln in open(fn):
        h, rp, rel = ln.rstrip('\n').split('\t')
        if not os.path.isfile(rp) or sha(rp) != h:
            bad.append(rel)
    if bad:
        print('reads: 前半の写しを作った後に変わったファイル：' + '、'.join(bad[:12]) + ('…' if len(bad) > 12 else ''))
        return 1
    return 0


def table(out, repo, md):
    order = []
    for ln in open(os.path.join(repo, 'model/build/run_all.sh')):
        m = re.search(r'stage (\S+) (\S+)', ln)
        if m and not ln.lstrip().startswith('#') and 'stage()' not in ln:
            order.append((m.group(1), m.group(2)))
    L = ['# 作り直しの段と、それぞれが読むもの（自動、`run_all.sh` が作り直しのたびに書く）', '',
         'データ・スクリプト・取り込み用ファイルを変えたら、それを読む**いちばん上の段から下**が作り直しになる。',
         '前半（0〜4、しつらえまで）は写し`s4.3dm`を使い回せるが、`run_all.sh … s4`は前半の読むものが1つでも変わっていれば自動ではじめから流す。', '',
         '| 段 | 名前 | 読むもの（リポジトリの場所、`sodachiya/`から） |', '|---|---|---|']
    for key, name in order:
        fn = os.path.join(out, f'reads_{key}.txt')
        if not os.path.isfile(fn):
            continue
        rels = []
        for ln in open(fn):
            rel = ln.rstrip('\n').split('\t')[1]
            if rel.startswith('（'):
                continue
            rels.append(rel)
        # 細かいものはまとめる
        groups, rest = {}, []
        for r in rels:
            m = re.match(r'(archive/handoff_1018/t/|model/build/vendor/mock2/)', r)
            if m:
                groups[m.group(1)] = groups.get(m.group(1), 0) + 1
            else:
                rest.append(r)
        cells = [f'`{r}`' for r in rest] + [f'`{g}`の{n}ファイル' for g, n in groups.items()]
        L.append(f'| {key} | {name} | ' + '・'.join(cells) + ' |')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('reads: 段の表 →', md)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'collect':
        collect(sys.argv[2], sys.argv[3])
    elif cmd == 'fingerprint':
        fingerprint(sys.argv[2], sys.argv[3:])
    elif cmd == 'verify':
        sys.exit(verify(sys.argv[2]))
    elif cmd == 'table':
        table(sys.argv[2], sys.argv[3], sys.argv[4])
