"""乳児室（0・1歳、スパン1）の南の妻の開口を比べる（本館係、10-26、監修の項 20261026-2043 の 1）。
案ごとに、南の妻の立面（南から北を見る、右が東）と、v6 で切った断面（西を見る、左が南）に夏至・春秋分・冬至の南中の日を描く。
南の軒（屋根の面の延長、東 1.8 → 西 4.2、屋根の厚み 420）はどの案も同じ。京都（北緯35.0°）、妻はほぼ真南（方位 約173°）を向く。
出力：out/sodachiya_south_gable_study.pdf / .png（A3横）
"""
import os, sys, math
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MP, Ellipse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import subprocess, matplotlib.font_manager as _fm
_TTF = os.path.expanduser('~/.cache/sodachiya_fonts')
if not os.path.exists(os.path.join(_TTF, 'NotoSansCJKjp-Bold.ttf')):
    subprocess.run([sys.executable, os.path.join(ROOT, 'present', 'tools', 'make_ttf.py'), _TTF], check=False)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
if os.path.exists(os.path.join(_TTF, 'NotoSansCJKjp-Bold.ttf')):
    for _f in ('Regular', 'Bold'): _fm.fontManager.addfont(os.path.join(_TTF, f'NotoSansCJKjp-{_f}.ttf'))
    plt.rcParams['font.family'] = _fm.FontProperties(fname=os.path.join(_TTF, 'NotoSansCJKjp-Regular.ttf')).get_name()
plt.rcParams['pdf.fonttype'] = 42
OUT = os.environ.get('OUT', os.path.join(ROOT, 'out'))

# ---- 本館の形（3dm と同じ数、m）
ROOF = lambda v: 4.150 - v / 12.0                 # 前の屋根の面
UNDER = lambda v: ROOF(v) - 0.15                  # 屋根の立体の下面＝梁の上端
TOP = lambda v: ROOF(v) + 0.27                    # 屋根の上面
_BB = [(-0.28, 3.40), (0.525, 3.356), (11.475, 2.444), (12.0, 2.235), (12.525, 2.417), (15.0, 2.50)]
BEAM_BOT = lambda v: float(np.interp(v, [p[0] for p in _BB], [p[1] for p in _BB]))
EAVE = lambda v: 1.8 + 2.4 * (15.0 - v) / 15.45   # 南の軒の出（東 1.8 → 西 4.2）
GL, KAMOI = -0.30, 2.385
V0, V1 = 1.75, 11.80                              # 乳児室の南の妻の開口の幅（柱と受け取り土間の戸のあいだ）
VS = 6.0                                          # 断面の位置
SUN = [('夏至', 78.4, '#c0392b'), ('春分・秋分', 55.0, '#2e8b57'), ('冬至', 31.6, '#1f5fa8')]
C_W, C_G, C_D = '#E6D2B0', '#D6E8F2', '#C9DDEA'

def bays(n):
    w = (V1 - V0) / n; return [(V0 + i * w, V0 + (i + 1) * w) for i in range(n)]

def opt1():
    out = [(a, b, 0, KAMOI, 'door') for a, b in bays(6)]
    out += [(V0, V1, KAMOI, None, 'glass')]
    return out
def opt2():
    d0, d1 = 6.9, 8.7
    out = [(V0, d0, 0, 1.6, 'glass'), (d1, V1, 0, 1.6, 'glass'), (d0, d1, 0, KAMOI, 'door')]
    out += [(V0, d0, 1.6, None, 'wall'), (d1, V1, 1.6, None, 'wall'), (d0, d1, KAMOI, None, 'wall')]
    return out
def opt3():
    out = []
    for i, (a, b) in enumerate(bays(6)):
        out.append((a, b, 0, KAMOI, 'door' if i % 2 == 0 else 'wall'))
    out += [(V0, V1, KAMOI, None, 'glass')]
    return out

CASES = [
    ('案1　今のまま（全面のガラス戸）＋室内の障子', opt1,
     ['深い南の軒（1.8〜4.2）が、すでに日を選んでいる：夏至・春秋分の南中は軒の影、冬至は下の約1.5 mだけに日が当たり、床に奥行き約2.5 mの日だまり。',
      '冬のまぶしさ・床の照り返しは、室内の障子（引き込み）で。窓に格子は付けない。',
      '弱み：ガラスが大きく（約{g:.0f} m²）、冬の夜と朝の熱の逃げがいちばん大きい。上の欄間は一年中直射が当たらず、空の光だけ。']),
    ('案2　日の当たる所だけガラス（低い連窓＋園庭への戸）', opt2,
     ['上の部分（約1.6より上）は一年中軒の影で直射が当たらないので、杉の壁にしても冬の日だまりは減らない。',
      '低い連窓（0〜1.6）ははう子・座った子・寝ている子の目の高さで、みなみのさんかくの草と空が見える。真ん中に園庭への戸。',
      '上の壁は掲示・棚に。まぶしい空が目に入らない。ガラス約{g:.0f} m²（案1の約6割）。弱み：南の妻の立面が重くなる、大人の立った目から空は見えにくい。']),
    ('案3　縁側と同じリズム（1.5 mごとに杉の壁とガラスの戸）', opt3,
     ['東の縁側（各スパンの半分が杉の壁）と同じ言葉を、角を回って南の妻にも。外から一つの建物に見える。',
      '日だまりは戸の所だけ（半分）。壁の間にベビーベッド・棚を置ける。欄間は東と同じく鴨居の上をガラスで通す。',
      'ガラス約{g:.0f} m²。弱み：日だまりが途切れ途切れ、はう子の目の高さの見通しも半分。']),
]

# ---- 第2版（10-26 21:34、ユーザー：南の開口は架構の水平に合わせる。案3（縦のリズム）はなし、案2で戸の所の変化が無いもの）
def b1():
    return [(V0, V1, 0, 1.6, 'glass'), (V0, V1, 1.6, None, 'wall')]
def b2():
    return [(V0, V1, 0, KAMOI, 'glass'), (V0, V1, KAMOI, None, 'wall')]
def b3():
    return [(V0, V1, 0, 1.6, 'glass'), (V0, V1, 1.6, KAMOI, 'wall'), (V0, V1, KAMOI, None, 'glass')]
CASES2 = [
    ('B1　低い連窓だけ（0〜1.6、戸なし）', b1,
     ['案2から園庭への戸を取り、0〜1.6 のガラスを妻の幅いっぱいに一本で通す。上端 1.6 は、冬至の南中に日が当たる高さ（約1.5）と大人の目の高さに近い。',
      '園庭（みなみのさんかく）へは東の縁側の戸から（どのスパンも開く、南の縁側・スロープへ続く）。連窓は全部引き違いで開け、風も通す。',
      'ガラス約{g:.0f} m²。上の杉の壁は、勾配の梁の下で台形になり、水平の窓と勾配の架構の対比がはっきりする。']),
    ('B2　鴨居の線で一本（0〜2.385 のガラス戸、上は杉の壁）', b2,
     ['ガラス戸の上端を東の縁側の鴨居（h2.385）にそろえ、角を回って一本の水平線で通す。戸は全部引き戸で、どこからでも出入りできる（戸の所の変化が無い）。',
      '鴨居より上（一年中軒の影）は杉の壁。東の端では梁の下端（約2.42）と鴨居がほぼ重なり、壁は西から東へ細くなる三角になる。',
      'ガラス約{g:.0f} m²（案1の約8割）。弱み：1.6〜2.4 のガラスは直射が当たらず熱の逃げが増える分、B1よりガラスが多い。']),
    ('B3　二本の帯（低い連窓＋鴨居の上の欄間）', b3,
     ['下の連窓（0〜1.6）で日だまりと子の目の高さの景色、鴨居の上の欄間（2.385〜梁の下端）で空の光を奥へ。あいだの杉の壁の帯（1.6〜2.385）が、東の縁側の鴨居の線を受ける。',
      '東の縁側の「戸＋鴨居の上の欄間」の二段の構成を、南の妻では「連窓＋欄間」に読みかえる。園庭へは東の縁側から。',
      'ガラス約{g:.0f} m²。弱み：欄間は西で高さ約0.9、東で0にすぼまる（梁の下端の勾配）。']),
]

# ---- 第3版（10-26 21:38、ユーザー：B1とB2の中間、B2寄り）
def band(zt): return lambda: [(V0, V1, 0, zt, 'glass'), (V0, V1, zt, None, 'wall')]
CASES3 = [
    ('B2-a　上端 1.95（受け取り土間の戸の上端にそろえる）', band(1.95),
     ['同じ南の妻にある受け取り土間の戸（h1.95）の上端と一本の線にそろえる。妻の面の中に水平線が一本だけ通る。',
      'ガラス戸は低め（1.95）。大人はくぐる感じは無いが、戸としては低い側。上の杉の壁が厚く、水平の帯がはっきりする。',
      'ガラス約{g:.0f} m²。']),
    ('B2-b　上端 2.15（中間、B2寄り）', band(2.15),
     ['戸として標準的な高さ。上の杉の壁は西で約1.1、東で約0.2の台形で、壁の帯が東の端まで消えずに残る（B2では東で三角に消える）。',
      '東の縁側の鴨居（2.385）とは角で約0.24ずれる。角は柱（v12）と内縁側の端のガラスで切れるので、ずれは目立ちにくい。',
      'ガラス約{g:.0f} m²。']),
    ('B2　上端 2.385（東の縁側の鴨居の線、前の案）', band(KAMOI),
     ['東の縁側の鴨居と角を回って一本の線。上の杉の壁は東へ細くなり、東の端では梁の下端（柱の際で約2.3）がガラスの上端より下がるので、そこだけガラスを梁に合わせて切る。',
      'ガラス約{g:.0f} m²。']),
]

def area(spec):
    s = 0.0
    for a, b, z0, z1, k in spec:
        if k == 'wall': continue
        vs = np.linspace(a, b, 40)
        s += np.trapezoid([(BEAM_BOT(v) if z1 is None else z1) - z0 for v in vs], vs)
    return s

W, H = 420, 297
fig = plt.figure(figsize=(W / 25.4, H / 25.4))
fig.text(14 / W, 1 - 13 / H, '乳児室（0・1歳）の南の開口を比べる' + {'1': '', '2': '（2）架構の水平に合わせる', '3': '（3）B1とB2の中間'}[os.environ.get('SG_SET', '1')], fontsize=14, weight='bold')
fig.text(14 / W, 1 - 19.5 / H, '本館係　2026-10-26　左：南の妻の立面（南から北を見る、右が東）1/125　右：v6 で切った断面（西を見る、左が南）1/125、南中の日。'
         '京都 北緯35.0°、妻の向き 約173°（ほぼ真南）。南の軒・屋根の厚みはどの案も同じ', fontsize=7.2, color='#555')
S = 1 / 125 * 1000
SET = os.environ.get('SG_SET', '1')
for i, (name, fn, notes) in enumerate({'1': CASES, '2': CASES2, '3': CASES3}[SET]):
    spec = fn(); g = area(spec)
    top = H - 30 - i * 88
    fig.text(14 / W, (top - 2) / H, name, fontsize=10.5, weight='bold')
    import textwrap
    yy = top - 12
    for t in notes:
        lines = textwrap.wrap(t.format(g=g), 44)
        fig.text(300 / W, yy / H, '\n'.join(lines), fontsize=6.6, va='top', linespacing=1.5)
        yy -= 4.2 * len(lines) + 3
    # --- 立面
    ax = fig.add_axes([14 / W, (top - 8 - 5.2 * S) / H, 16.2 * S / W, 5.2 * S / H])
    ax.set_xlim(-0.8, 15.4); ax.set_ylim(GL - 0.3, 4.9); ax.set_aspect('equal'); ax.axis('off')
    vs = np.linspace(-0.45, 15.0, 80)
    ax.fill_between(vs, [UNDER(v) for v in vs], [TOP(v) for v in vs], color='#9aa0a6', zorder=6)          # 軒先の見付け（屋根の厚み）
    ax.plot(vs, [TOP(v) + 0.04 for v in vs], color='#2d313a', lw=1.2, zorder=7)                           # 太陽光
    vb = np.linspace(-0.28, 15.0, 80)
    ax.fill_between(vb, [BEAM_BOT(v) for v in vb], [UNDER(v) for v in vb], color='#b58a5a', zorder=4)    # 架構1の梁
    ax.add_patch(Rectangle((-0.35, GL), 0.55, UNDER(0) - GL, fc=C_W, ec='none', zorder=3))                # 西の壁・柱の所
    ax.add_patch(Rectangle((1.4, 0), 0.35, BEAM_BOT(1.5), fc=C_W, ec='none', zorder=3))
    ax.add_patch(Rectangle((0.2, 0), 1.2, 1.95, fc='#d9c7a6', ec='#6b5a44', lw=0.4, zorder=5))             # 受け取り土間の戸
    ax.add_patch(Rectangle((0.2, 1.95), 1.2, BEAM_BOT(0.8) - 1.95, fc=C_W, ec='none', zorder=3))
    for vc in (0.0, 12.0): ax.add_patch(Rectangle((vc - 0.2, 0), 0.4, BEAM_BOT(vc), fc='#8b6b45', zorder=5))
    ax.add_patch(Rectangle((12.2, 0), 1.3, 3.0, fc=C_G, ec='#33475a', lw=0.4, zorder=3))                  # 内縁側の端のガラス
    for a, b, z0, z1, k in spec:
        vv = np.linspace(a, b, 20); zt = [BEAM_BOT(v) if z1 is None else z1 for v in vv]
        fc = {'wall': C_W, 'glass': C_G, 'door': C_D}[k]
        ax.fill_between(vv, [z0] * len(vv), zt, color=fc, zorder=3, lw=0)
        ax.plot(list(vv) + [b, a, a], zt + [z0, z0, zt[0]], color='#33475a' if k != 'wall' else '#8a7358', lw=0.45, zorder=4)
        if k == 'wall':
            for x in np.arange(a + 0.06, b, 0.12): ax.plot([x, x], [z0, BEAM_BOT(x) if z1 is None else z1], color='#b89a74', lw=0.12, zorder=3.5)
    ax.plot([-0.8, 15.4], [GL, GL], color='k', lw=0.8, zorder=8); ax.plot([0, 15], [0, 0], color='#999', lw=0.25, ls=':', zorder=8)
    ax.text(6.8, GL - 0.12, '乳児室', fontsize=5.5, ha='center', va='top'); ax.text(0.8, GL - 0.12, '受け取り土間', fontsize=5.5, ha='center', va='top')
    ax.text(13.6, GL - 0.12, '縁側', fontsize=5.5, ha='center', va='top')
    ax.plot([VS, VS], [GL - 0.05, 4.8], color='#c0392b', lw=0.4, ls=(0, (5, 2, 1, 2)), zorder=9); ax.text(VS + 0.1, 4.75, '断面', fontsize=5, color='#c0392b')
    # --- 断面（v6、西を見る：左が南）
    D = EAVE(VS); zu, zt_ = UNDER(VS), TOP(VS); zb = BEAM_BOT(VS)
    ax2 = fig.add_axes([(14 + 16.2 * S + 10) / W, (top - 8 - 5.2 * S) / H, 14.6 * S / W, 5.2 * S / H])
    ax2.set_xlim(-6.4, 8.2); ax2.set_ylim(GL - 0.3, 4.9); ax2.set_aspect('equal'); ax2.axis('off')
    ax2.add_patch(Rectangle((-D, zu), D + 8.2, zt_ - zu, fc='#9aa0a6', ec='#555', lw=0.4, zorder=5))
    ax2.plot([-D, 8.2], [zt_ + 0.04] * 2, color='#2d313a', lw=1.2, zorder=6)
    for uf in (0, 3, 6):
        ax2.add_patch(Rectangle((uf - 0.18, zb), 0.36, zu - zb, fc='#b58a5a', ec='#6b4a2a', lw=0.3, zorder=5))
    ax2.plot([-6.4, 0], [GL, GL], color='k', lw=0.8); ax2.plot([0, 8.2], [0, 0], color='k', lw=0.8)
    ax2.plot([0, 0], [GL, 0], color='k', lw=0.8)
    hit = [s for s in spec if s[0] <= VS <= s[1]]
    for a, b, z0, z1, k in hit:
        zz1 = zb if z1 is None else z1
        ax2.add_patch(Rectangle((-0.04 if k != 'wall' else -0.07, z0), 0.08 if k != 'wall' else 0.14, zz1 - z0,
                                fc={'wall': C_W, 'glass': C_G, 'door': C_D}[k], ec='#33475a' if k != 'wall' else '#8a7358', lw=0.5, zorder=6))
    hw = None
    for lab, alt, col in SUN:
        t = math.tan(math.radians(alt))
        x_end = -D + (zu - 0) / t if -D + (zu - 0) / t > 0 else -D + (zu - GL) / t
        z_end = 0 if x_end > 0 else GL
        x_st = -D - 1.3 / math.tan(math.radians(alt)) * 1.0; z_st = zu + 1.3
        ax2.plot([x_st, x_end], [z_st, z_end], color=col, lw=0.7, zorder=7)
        h_at = zu - D * t
        k_ = [x[0] for x in SUN].index(lab)
        ax2.plot([-6.3, -5.8], [4.55 - k_ * 0.32] * 2, color=col, lw=0.9)
        ax2.text(-5.7, 4.55 - k_ * 0.32, f'{lab}の南中 {alt:.0f}°', fontsize=5, color=col, va='center')
        if alt < 40: hw = h_at
    if hw is not None and hw > 0:                                     # 冬至の日だまり：ガラスで日が当たる高さ 0〜hw
        t = math.tan(math.radians(31.6)); segs = []
        for a, b, z0, z1, k in hit:
            if k == 'wall': continue
            lo, hi = z0, min(zb if z1 is None else z1, hw)
            if hi > lo: segs.append((lo / t, hi / t))
        for x0, x1 in segs:
            ax2.add_patch(Rectangle((x0, 0), x1 - x0, 0.06, fc='#f5c542', ec='none', zorder=8))
        if segs:
            ax2.text(sum(segs[0]) / 2, 0.12, f'冬至の日だまり 約{segs[0][1] - segs[0][0]:.1f} m', fontsize=5, ha='center', color='#8a6d00')
        elif not hit or hit[0][4] == 'wall':
            ax2.text(1.2, 0.12, '（壁の所：日は入らない）', fontsize=5, color='#8a6d00')
    ax2.add_patch(Ellipse((1.3, 0.09), 0.6, 0.18, fc='#e8c9a8', ec='#8a6a4a', lw=0.3, zorder=9))       # 寝ている子
    ax2.add_patch(Ellipse((3.2, 0.25), 0.5, 0.3, fc='#e8c9a8', ec='#8a6a4a', lw=0.3, zorder=9))        # はう子
    ax2.text(-D, zu + 0.08 + 0.42, f'南の軒 出 {D:.1f}', fontsize=5, ha='left')
    ax2.text(7.9, -0.15, '北 →', fontsize=5, ha='right', va='top'); ax2.text(-6.2, -0.45, '← 南（みなみのさんかく）', fontsize=5, va='top')
    fig.text((14 + 16.2 * S - 2) / W, (top - 10 - 5.2 * S) / H, f'ガラス 約{g:.0f} m²', fontsize=7, ha='right', va='top')
fig.text(14 / W, 8 / H, '日の角度は南中の高さ（夏至78°・春秋分55°・冬至32°）。朝夕は日が東西に回るので、南の妻には夏はほとんど当たらず、冬は南中に近い角度で当たる。'
         '日だまりは冬至の南中の床の上の日の範囲（ガラスで日が当たる高さから）。', fontsize=6.3, color='#555')
os.makedirs(OUT, exist_ok=True)
for ext in ('pdf', 'png'):
    fig.savefig(os.path.join(OUT, f'sodachiya_south_gable_study{"" if SET == "1" else "_" + SET}.{ext}'), dpi=200 if ext == 'png' else None)
print('written', SET)
