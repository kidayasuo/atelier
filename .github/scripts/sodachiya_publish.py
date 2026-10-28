#!/usr/bin/env python3
"""育ち舎の自動の作り直しの後始末（設計監修、10-27）。push はワークフローがする。

環境変数：CODE（run_all.sh の終わりの値）、SINCE（前の作り直しの commit）、RUN_URL（この実行のページ）。
- 通った（CODE=0）：できたものを commit。更新係あての「作り直し：…」の未の項を済にする。変更の記録に一行。
- 止まった：できたものを捨てる。前の作り直しから commit した係（commit の頭）あてに連携の項を立てる（設計監修には知らせ）。
受け箱（renkei/inbox.md）は書かない（ほかのチャットの受け箱とぶつかるため、10-27）。
"""
import os, re, subprocess, sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
S = os.path.join(ROOT, 'sodachiya')
INBOX = [sys.executable, os.path.join(S, 'renkei/inbox.py')]
OUTS = ['sodachiya/sodachiya.3dm', 'sodachiya/drawings', 'sodachiya/model/sodachiya_exact_mesh.3dm',
        'sodachiya/model/drawings', 'sodachiya/model/build/stages.md',
        'sodachiya/logo/sodachiya_logo_etch.png', 'sodachiya/logo/sodachiya_logo_etch_mask.png']   # ガラスのロゴの絵（materials.py が SVG から作る、10-28）
HEADS = {'本館': '本館係', '西館': '西館係', 'アプローチ': 'アプローチ係', '園庭': '園庭', '3dm': '更新係',
         '監修': '設計監修', 'ソリッド': 'ソリッド係', '遊戯室': '西館係'}
ME = '自動の作り直し'


def run(*a, **k):
    return subprocess.run(a, cwd=S, capture_output=True, text=True, **k)


code = os.environ.get('CODE', '1')
since = os.environ.get('SINCE', '')
url = os.environ.get('RUN_URL', '')
head = run('git', 'rev-parse', '--short', 'HEAD').stdout.strip()
txt = open('/tmp/claude-0/run.txt', encoding='utf-8', errors='replace').read() if os.path.exists('/tmp/claude-0/run.txt') else ''
check = next((l for l in reversed(txt.splitlines()) if l.startswith('check:')), '')

if code == '0':
    run('git', 'add', '-A', '--', *[os.path.join(ROOT, o) for o in OUTS])
    # 更新係あての「作り直し」の未の項を済に（この作り直しに入った）
    for f in sorted(os.listdir(os.path.join(S, 'renkei/open'))):
        p = os.path.join(S, 'renkei/open', f)
        t = open(p, encoding='utf-8').read()
        if re.search(r'^# 作り直し', t, re.M) and re.search(r'^- 更新係：未', t, re.M):
            run(*INBOX, 'mark', p, '更新係', '済', f'自動の作り直し（{head}まで）')
    run(*INBOX, 'log', ME, f'{head}まで作り直した。{check}')
    msg = f'[3dm] 自動の作り直し（{head}まで）\n\n{check}\n{url}'
else:
    # できたものを捨てる
    run('git', 'checkout', '--', *[os.path.join(ROOT, o) for o in OUTS])
    run('git', 'clean', '-fdq', '--', *[os.path.join(ROOT, o) for o in OUTS])
    who = []
    if since:
        for s in run('git', 'log', '--format=%s', f'{since}..HEAD').stdout.splitlines():
            m = re.match(r'^\[([^\]]+)\]', s)
            n = HEADS.get(m.group(1)) if m else None
            if n and n not in who and n != '設計監修':
                who.append(n)
    who = who or ['更新係']
    tail = '\n'.join(txt.splitlines()[-25:])
    if re.search(r'ModuleNotFoundError|ImportError|No such file or directory: .?/(tmp|home)/', txt):
        # 作業場の誤り（部品が足りない・作業場の場所）：係の直しではないので、自動の作り直しを持つ監修だけに
        dests = ['設計監修=未:作業場の誤り（setup.sh か .github/）']
    else:
        dests = [f'{n}=未:自分の直しで止まっていないか見る' for n in who] + ['設計監修=知らせ:止まった']
    p = run(*INBOX, 'new', ME, f'自動の作り直しが止まった（{head}）', *dests).stdout.strip().splitlines()[0].strip()   # 2行目からはユーザーへの一行（inbox.py new、10-27）
    body = open(os.path.join(S, p), encoding='utf-8').read()
    note = (f'自動の作り直し（{head}まで）が止まったので、できたものは push していない。'
            f'前の作り直しから commit した係に送った。自分の直しが原因なら直して push すれば、自動でもう一度作り直す。\n\n'
            f'実行のページ：{url}\n\n```\n{tail}\n```')
    body = re.sub(r'（本文：[^\n]*）', lambda _: note, body, count=1)
    open(os.path.join(S, p), 'w', encoding='utf-8').write(body)
    run(*INBOX, 'log', ME, f'{head}で止まった（項 {os.path.basename(p)}）。{check}')
    msg = f'[3dm] 自動の作り直しが止まった（{head}）\n\n{check}\n{url}'

# 受け箱（renkei/inbox.md）は書かない：作り直しの約30分のあいだにほかのチャットが受け箱を push するとぶつかる（10-27）。
# 受け箱は次にどこかのチャットが inbox.py を走らせたときに作り直される。
run('git', 'add', '-A', 'renkei/open', 'renkei/done', 'renkei/log')
r = run('git', 'commit', '-q', '-m', msg)
print(r.stdout, r.stderr)
print(msg)
