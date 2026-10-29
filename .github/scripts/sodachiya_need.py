#!/usr/bin/env python3
"""育ち舎の自動の作り直し：前の作り直しから、作り直しが読むものが変わったか（設計監修、10-27）。

前の作り直し＝sodachiya/model/drawings/sodachiya_check.txt を最後に変えた commit（--publish はいつもこれを書く）。
出力（GITHUB_OUTPUT の形）：build=yes|no、since=<前の作り直しの commit>
"""
import fnmatch, subprocess, sys

# ワークフローの paths と同じ（作り直しが読むもの）
PATS = ['sodachiya/data/*', 'sodachiya/scripts/plan01.py', 'sodachiya/scripts/plan02.py', 'sodachiya/scripts/plan04.py',
        'sodachiya/model/build/*', 'sodachiya/model/*_layers.3dm', 'sodachiya/archive/handoff_1018/*',
        'sodachiya/logo/sodachiya_logo.svg', 'sodachiya/present/kadai_map.json',
        '.github/workflows/sodachiya_build.yml', '.github/scripts/sodachiya_*.py']


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True).stdout.strip()


def reads(p):
    if p.startswith('sodachiya/model/build/') and p.endswith('.md'):
        return False
    return any(fnmatch.fnmatch(p, q) for q in PATS)


force = len(sys.argv) > 1 and sys.argv[1] == 'true'
since = git('log', '-1', '--format=%H', '--', 'sodachiya/model/drawings/sodachiya_check.txt')
# 10-30 監修：作り直しの commit は、作り直しのあいだにほかのチャットが push した commit の上に載せ直される。
# その commit から比べると、あいだの commit（作り直しに入っていない）を見落とす（10-30 1:39 の西館 64ab09c）。
# 題の「（<hash>まで）」が作り直しが読んだ HEAD なので、そこから比べる
import re
m_ = re.search(r'（([0-9a-f]{7,40})まで）', git('log', '-1', '--format=%s', since)) if since else None
if m_ and git('rev-parse', '--verify', '-q', m_.group(1) + '^{commit}'):
    since = git('rev-parse', m_.group(1))
if not since:
    print('build=yes\nsince=')
    sys.exit()
changed = [p for p in git('diff', '--name-only', since, 'HEAD').splitlines() if reads(p)]
print(f'build={"yes" if changed or force else "no"}\nsince={since}')
for p in changed[:30]:
    print(f'# changed: {p}', file=sys.stderr)
