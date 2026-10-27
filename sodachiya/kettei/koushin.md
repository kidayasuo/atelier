# 育ち舎　3dm と図の更新係の手順

**10-28 からこのファイルが本文**（設計監修、ユーザー 10-28）。書く前に `git pull`、直す所だけ Edit で（丸ごと書き直さない）、書いたらすぐ commit・push。プロジェクトの同じ名前の文書はこのファイルの写し（そちらは書き換えない）。

更新係のチャットが読む手順。最終更新：2026-10-27（作り直しは GitHub Actions で自動になった、監修の項 20261027-1144-kanshu）。

# 役目（10-27 から）
- **3dm・全体の図・面積表の作り直しは自動**（`.github/workflows/sodachiya_build.yml`）。`data/`・作り直しのスクリプト（`model/build/**`）・取り込み用ファイル（`model/*_layers.3dm`）などが main に push されると、約2分待って続けての push をまとめ、`run_all.sh … base --publish` を走らせ、通れば `[3dm] 自動の作り直し（<commit>まで）` で push する。止まれば push せず、前の作り直しから commit した係に連携の項を立てる。結果の一行は `renkei/log/auto.md`。
- **`--publish` は手で走らせない**（自動とぶつかる。10-27、手の作り直しと自動の作り直しが同じ図を書いて、pull でぶつかった）。確かめは `--publish` なしで（`/tmp/claude-0/out/preview/` に入る）。
- 更新係が持つもの：
  1. 作り直しの仕組み：`model/build/run_all.sh`・`setup.sh`・`vendor/`・`reads.py`・`check_build.py`（`check_build.py` は監修も直す）、ワークフローの作業場の用意（足りない Python の部品など。監修と相談）。
  2. 共通の段のスクリプト：`south/finish.py`（レイヤーの整理・外構の取り込み）・`add_play_import.py`・`add_site.py`（護岸・園庭の取り込み）・`add_context.py`（周辺）・`areas.py`（面積表）・`context/`。
  3. **全体の図の描き方 `south/draw100.py`**（配置図 1/200・1/100 の平面・断面・立面）。図の直しの依頼は更新係に来る。直して push すれば自動で図が入る。
  4. **止まったときの手当て**：自動の作り直しが止まって自分あての項が立ったら（作り直しの仕組みや共通の段・draw100 の誤り）、原因を見て直す。形の判断が要るものはその場所の担当へ。

# 毎回の手順（ユーザーが「お願い」など一言で来たら）
1. `cd atelier && git pull`。作業場が無ければ `cd sodachiya && bash model/build/setup.sh`。
2. `python3 renkei/inbox.py mine 更新係`（知らせは出たときに自動で「読んだ」になる）。
3. 依頼を片づける：図の直し（`draw100.py`）・共通の段のスクリプト・止まった作り直しの手当て。
   - 図だけ確かめる：`SODACHIYA_ROOT=$A DRAW_ONLY=<名前の一部> python3 model/build/south/draw100.py $A/model/sodachiya_exact_mesh.3dm /tmp/claude-0/el /tmp/claude-0/el`（出力は作業場へ。リポジトリの `drawings/` には書かない）。名前の一部は `siteplan`・`plan`・`sections`・`elevations_`（立面図1）・`elevations2`（立面図2）。立面は1枚5分前後で記憶を多く使うので、立面図1と2は別々に。
   - 3dm まで確かめたいときは `bash model/build/run_all.sh /tmp/claude-0/out s4`（`--publish` なし）。
4. スクリプトだけ commit して push（頭は `[3dm]`、いつもの署名）。約30分で自動の作り直しが入る。`renkei/log/auto.md` で終わったかを見て、図を縮めて見る（長辺 1600 px くらい）。
5. `inbox.py mark <項> 更新係 済 ひとこと（commit）`、`inbox.py log 更新係 "一行"`、`python3 renkei/inbox.py` で受け箱を作って commit・push、`claude/受け箱.md` を `renkei/inbox.md` で上書き（`project_write` の `local_path`）。
6. ユーザーへの報告は短く：何を直したか、自動の作り直しで入るか（入ったか）。

# 覚えておくこと（10-25〜10-27）
- **Rhino 版（段10、`clean_wire.py`）はソリッド係の受け持ち**（すべて閉じた立体）。新しいレイヤーが親（A〜L）の下に入っているかだけ見る：`sodachiya.3dm` の一番上のレイヤーに `10k_…` のような番号のレイヤーが出ていたら、`clean_wire.py` の `PARENTS` に番号を足して push。
- **配置図 1/200**（`make_siteplan`）：A1、向きは3枚目の平面図と同じ（−38.5°）、文字は PDF に入れない（DXF の60・80のレイヤーにだけ）。書き出すたびに `…_線.pdf`・`…_色.pdf`（地が透明）と `…_xform.json`（3dm の m → 紙の mm）を作る。プレゼンの準備がこの json で位置を合わせて読むので、紙の大きさを変えたら `paper_mm` を見る。
- **周辺と護岸**：`add_context.py`（PLATEAU：敷地にかかる建物は入れない、向かいの3軒の回転 `ROT_BLOCK`、北東の辺の中ほどに接する道の片は入れない）。`add_site.py`（高野川：水面 GL−5.5・幅 18 m、辺の両端から 45 m 延ばす。寸法は仮）。周辺の位置を動かすときは `data/context_plateau.json`・`data/georef.json` をいっしょに。
- **屋根の下面**（`clip_parts.py`、監修のスクリプト、10-26）：屋根が厚み 300 を超える立体の所は、その下面が屋根の下面（垂木の下）。厚みの無い所だけ 150 下げる。
- **立面図**：隠面・隠線は監修の z バッファ（10-26）。大和張りの縦の線 `yamato_lines`（120 おき、17・21・35）。手前の外構と樹木 `elev_exterior`（10-27：塀・柵・木戸・棚・柱は線だけ、レイヤーごとに足し合わせた外形。木は淡い緑の輪郭で手前 15 m まで）。細かく繰り返す物は `ELEV_OUTLINE_ONLY` で外形だけ。
- 前半の写しの指紋（`reads.py`）と前の版との比べ（`check_build.py`、止める ✗・知らせる !）は自動の作り直しでも同じに働く。段の表は `model/build/stages.md`。

# 残っていること（10-27 昼）
- 閉じていない物 27（10p 太陽光の板 20、83 遊戯室の網 4、62・78 みなみのさんかく 各1、20p 1）：監修の項 20261027-0724-kanshu。決まり「すべてソリッド」で 0 にする。形はそれぞれ本館係・西館係・アプローチ係のものなので、閉じ方は担当かソリッド係に頼むのがよい。
- ソリッド係：キャットウォークの縁のずれ 32〜43 mm（前からの残り）。

# 会話を軽く保つ
- 長い出力・ファイルを丸ごと貼らない。覚えておくことはこの手順とリポジトリ（`renkei/`）に書く。
- 会話が一度でも自動で要約されたら「そろそろ新しいスレッドにしましょう」と伝え、この手順と変更の記録を先に push しておく（役割分担の「チャットが溢れたとき」）。

## 最初の一文（新しい更新係のチャットに貼る）
> 育ち舎の「3dm と図の更新係」です。「役割分担」と「更新係の手順」を読み、atelier リポジトリ（kidayasuo/atelier）を接続して `sodachiya/model/build/setup.sh` を走らせて待機してください。作り直しは自動です。私が短い一言（「お願い」など）で来たら、`renkei/inbox.py mine 更新係` の依頼（図の描き方・共通の段・止まった作り直し）を片づけて push してください。
