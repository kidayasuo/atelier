#!/usr/bin/env python3
"""育ち舎の連携（チャット間の依頼）と受け箱（設計監修、10-24）。

連携は 1項1ファイル（open/）。あて先ごとに一行の状態を持ち、あて先のチャットが自分の行だけを書き換える。
書く人が分かれているので、二つのチャットがほぼ同時に書いても項が消えない（ぶつかれば git が知らせる）。
受け箱はこのスクリプトが open/ から作る（手で書かない。いつ誰が作っても同じものになる）。

使い方（sodachiya/ の中で）:
  python3 renkei/inbox.py                      受け箱を作る：済んだ項を done/ へ移し、renkei/inbox.md を書いて画面に出す
  python3 renkei/inbox.py new 監修 "題" 更新係=未:ひとこと 本館係=知らせ:ひとこと
                                               新しい項の下書き（open/ に作り、パスを出す。本文は後から書く）
  python3 renkei/inbox.py mark <項のファイル> 更新係 済 [ひとこと]
                                               自分の行の状態を変える（未→済、知らせ→読んだ）
  python3 renkei/inbox.py mine 更新係           自分あての未と知らせの項の本文だけを出す（連携を全部読まない）。
                                               出した知らせは「読んだ」にする（10-27：知らせは取りに行くもの。--keep で残す）
  python3 renkei/inbox.py log 監修 "一行"        変更の記録に一行（log/<チャット>.md、チャットごとのファイル）
  python3 renkei/inbox.py log --since 1023      変更の記録を日付で並べて出す（10-23 から）

状態：未（依頼、やってほしい）／知らせ（読んでほしい）／済（依頼を片づけた）／読んだ（知らせを読んだ）。
知らせ（10-27）：受け箱には出さない（ユーザーが知らせのために回らなくてよい）。各チャットは作業の始めに mine で読む。
自動の作り直し（GitHub Actions、.github/workflows/sodachiya_build.yml）も「自動の作り直し」の名前で項と記録を書く。
あて先「ユーザー」の未は、受け箱の「ユーザーへの問い」に出る（答えを聞いたチャットが済にする）。
すべての行が 済 か 読んだ になった項は、次に受け箱を作ったとき done/ へ移る（だれが作ってもよい）。
"""
import os, re, sys, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
OPEN, DONE, LOG = (os.path.join(HERE, d) for d in ('open', 'done', 'log'))
JST = dt.timezone(dt.timedelta(hours=9))

# チャットの名前（受け箱の行の順）と、ファイル名に使う英字
CHATS = [('本館係', 'honkan'), ('西館係', 'nishikan'), ('アプローチ係', 'approach'), ('園庭', 'garden'),
         ('更新係', 'koushin'), ('ソリッド係', 'solid'), ('設計監修', 'kanshu'), ('模型作成', 'mokei'), ('プレゼンの準備', 'present'),
         ('ユーザー', 'user'), ('自動の作り直し', 'auto')]
ALIAS = {'自動': '自動の作り直し', '監修': '設計監修', '3dmと図の更新係': '更新係', '模型': '模型作成', 'プレゼン': 'プレゼンの準備',
         'アプローチ': 'アプローチ係', '本館': '本館係', '西館': '西館係', 'ソリッド': 'ソリッド係', 'ソリッドがかり': 'ソリッド係'}
SLUG = dict(CHATS)
STATES = ('未', '知らせ', '済', '読んだ')
LINE = re.compile(r'^- (\S+?)：(未|知らせ|済|読んだ)(?:　(.*))?$')


def name(n):
    n = ALIAS.get(n, n)
    if n not in SLUG:
        sys.exit(f'知らないチャットの名前：{n}（{"・".join(SLUG)}）')
    return n


def parse(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    title = next((l[2:].strip() for l in lines if l.startswith('# ')), os.path.basename(path))
    to = []
    for i, l in enumerate(lines):
        if l.strip() == '---':
            break
        m = LINE.match(l)
        if m:
            to.append((i, name(m.group(1)), m.group(2), m.group(3) or ''))
    return title, to, lines


def items():
    os.makedirs(OPEN, exist_ok=True)
    return sorted(os.path.join(OPEN, f) for f in os.listdir(OPEN) if f.endswith('.md'))


def git_mv(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run(['git', 'mv', src, dst], cwd=HERE, capture_output=True)
    if r.returncode:
        os.replace(src, dst)


def inbox():
    rows = {n: {'未': [], '知らせ': []} for n, _ in CHATS}
    moved = []
    for p in items():
        title, to, _ = parse(p)
        if to and all(s in ('済', '読んだ') for _, _, s, _ in to):
            git_mv(p, os.path.join(DONE, os.path.basename(p)))
            moved.append(os.path.basename(p))
            continue
        for _, n, s, note in to:
            if s in rows[n]:
                rows[n][s].append((title, note))
    now = dt.datetime.now(JST).strftime('%m-%d %H:%M')
    out = ['# 育ち舎　受け箱（自動。手で書かない）', '',
           f'{now}に`sodachiya/renkei/inbox.py`が`renkei/open/`から作った。中身は各項のファイル（`renkei/open/<項>.md`）。',
           '使い方：ユーザーは行に「未」があるチャットに行き「お願い」など何か一言だけ言う（言葉は何でもよい。言われたチャットは受け箱の自分の行を片づける）。'
           '知らせはここに出さない：各チャットが作業の始めに`inbox.py mine`で読む（ユーザーは知らせのために回らなくてよい、10-27）。'
           '3dm・全体の図・面積表の作り直しは自動（push の後 約30分、GitHub Actions）。決まりは「役割分担」の「連携と受け箱」。', '',
           '| チャット | 未の依頼 | （知らせ） |', '|---|---|---|']
    cell = lambda xs: f'{len(xs)}件：' + '／'.join(t for t, _ in xs) if xs else 'なし'
    for n, _ in CHATS:
        if n in ('ユーザー', '自動の作り直し'):
            continue
        k = len(rows[n]["知らせ"])
        out.append(f'| {n} | {cell(rows[n]["未"])} | {f"{k}件" if k else ""} |')
    q = rows['ユーザー']['未'] + rows['ユーザー']['知らせ']
    out += ['', '**ユーザーへの問い（返事待ち）**：' + ('／'.join(note or t for t, note in q) if q else 'なし'),
            '', '（各チャットは`python3 renkei/inbox.py mine <係>`で自分あての項の中身を読む）']
    if moved:
        out += ['', f'（今回 done/ へ移した項：{"・".join(moved)}）']
    text = '\n'.join(out) + '\n'
    open(os.path.join(HERE, 'inbox.md'), 'w', encoding='utf-8').write(text)
    print(text)


def new(frm, title, *dests):
    frm = name(frm)
    now = dt.datetime.now(JST)
    os.makedirs(OPEN, exist_ok=True)
    base = f'{now:%Y%m%d-%H%M}-{SLUG[frm]}'
    p, k = os.path.join(OPEN, base + '.md'), 2
    while os.path.exists(p):
        p, k = os.path.join(OPEN, f'{base}-{k}.md'), k + 1
    body = [f'# {title}', '', f'{now:%m-%d %H:%M}　{frm}から。', '']
    for d in dests:
        n, _, rest = d.partition('=')
        s, _, note = rest.partition(':')
        if s not in STATES[:2]:
            sys.exit(f'状態は 未 か 知らせ：{d}')
        body += [f'- {name(n)}：{s}' + (f'　{note}' if note else ''), '']
    body += ['---', '', '（本文：だれに・何を・どこに（ファイル・commit）だけ。理由と数は担当の決定事項_〇〇に書き、ここからは名前で指す。1,500字以内）', '',
             '## 返事', '']
    open(p, 'w', encoding='utf-8').write('\n'.join(body))
    print(os.path.relpath(p, os.path.dirname(HERE)))


def mark(path, who, state, *note):
    who = name(who)
    if state not in STATES:
        sys.exit(f'状態は {"・".join(STATES)}')
    if not os.path.exists(path):
        path = os.path.join(OPEN, os.path.basename(path) if path.endswith('.md') else path + '.md')
    title, to, lines = parse(path)
    hit = [t for t in to if t[1] == who]
    if not hit:
        sys.exit(f'{who}の行が無い：{path}')
    for i, _, _, old in hit:
        lines[i] = f'- {who}：{state}' + (f'　{" ".join(note)}' if note else (f'　{old}' if old else ''))
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'{os.path.basename(path)}：{who}＝{state}')


def mine(who, *opt):
    who = name(who)
    read = []
    for p in items():
        title, to, lines = parse(p)
        if any(n == who and s in ('未', '知らせ') for _, n, s, _ in to):
            print(f'=== {os.path.basename(p)}\n' + '\n'.join(lines).rstrip() + '\n')
            if '--keep' not in opt and any(n == who and s == '知らせ' for _, n, s, _ in to):
                for i, n, s, note in to:
                    if n == who and s == '知らせ':
                        lines[i] = f'- {who}：読んだ' + (f'　{note}' if note else '')
                open(p, 'w', encoding='utf-8').write('\n'.join(lines))
                read.append(os.path.basename(p))
    if read:
        print(f'（知らせ {len(read)}件を「読んだ」にした。commit・push して受け箱を作り直す）')


def log(*args):
    os.makedirs(LOG, exist_ok=True)
    if args and args[0] == '--since':
        since = args[1].replace('-', '') if len(args) > 1 else '0000'
        rows = []
        for f in sorted(os.listdir(LOG)):
            for l in open(os.path.join(LOG, f), encoding='utf-8'):
                m = re.match(r'^- (\d\d)-(\d\d) (\d\d:\d\d)', l)
                if m and m.group(1) + m.group(2) >= since:
                    rows.append((m.group(1) + m.group(2) + m.group(3), l.rstrip()))
        print('\n'.join(r for _, r in sorted(rows)))
        return
    who, text = name(args[0]), ' '.join(args[1:])
    p = os.path.join(LOG, SLUG[who] + '.md')
    if not os.path.exists(p):
        open(p, 'w', encoding='utf-8').write(f'# 変更の記録（{who}）\n\n1件1〜2行（約150字以内）：何を変えたか・ユーザーの一言・commit・連携の項。中身は決定事項にある。\n\n')
    with open(p, 'a', encoding='utf-8') as f:
        f.write(f'- {dt.datetime.now(JST):%m-%d %H:%M}（{who}）{text}\n')
    print(os.path.relpath(p, os.path.dirname(HERE)))


if __name__ == '__main__':
    a = sys.argv[1:]
    {'new': new, 'mark': mark, 'mine': mine, 'log': log}.get(a[0], None)(*a[1:]) if a else inbox()
