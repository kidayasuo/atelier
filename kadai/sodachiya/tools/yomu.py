#!/usr/bin/env python3
"""長い Markdown を丸ごと読まないための道具（効率化委員会、10-28）。

  python3 tools/yomu.py <file>               見出しの一覧（行の番号と節の字数）だけを出す
  python3 tools/yomu.py <file> 見出しの一部   その見出しの節だけを出す（下の階の見出しも含む）
  python3 tools/yomu.py <file> 見出し --grep 語   その節の中で語を含む行だけ
"""
import re, sys

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 2
    pat = None
    if '--grep' in a:
        i = a.index('--grep'); pat = a[i + 1]; del a[i:i + 2]
    lines = open(a[0], encoding='utf-8').read().split('\n')
    heads = [(i, len(m.group(1)), m.group(2)) for i, l in enumerate(lines)
             if (m := re.match(r'^(#{1,6})\s+(.*)', l))]
    if len(a) == 1:
        for k, (i, lv, t) in enumerate(heads):
            end = next((j for j, lv2, _ in heads[k + 1:] if lv2 <= lv), len(lines))
            n = sum(len(x) for x in lines[i:end])
            print(f"{i + 1:5d} {'  ' * (lv - 1)}{t}（{n}字）")
        print(f"全部で {len(lines)} 行・{sum(len(x) for x in lines)} 字")
        return 0
    hit = [(k, h) for k, h in enumerate(heads) if a[1] in h[2]]
    if not hit:
        print(f"見出しに「{a[1]}」が無い。一覧は: python3 tools/yomu.py {a[0]}"); return 1
    for k, (i, lv, t) in hit[:3]:
        end = next((j for j, lv2, _ in heads[k + 1:] if lv2 <= lv), len(lines))
        body = lines[i:end]
        if pat:
            body = [f"{i + 1 + n:5d}: {x}" for n, x in enumerate(body) if pat in x]
        print('\n'.join(body))
    return 0

if __name__ == '__main__':
    sys.exit(main())
