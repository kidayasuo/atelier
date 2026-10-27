<!-- eyebrow: 建築設計実習Ⅱ—Ⅰ -->
# 育ち舎（こども園）

設計課題「こどもたちの育ち舎」の図・3dm・スクリプト。提出 2026-11-05。

## 直下（ユーザーが開く・書くもの）

| ファイル | 中身 |
|---|---|
| `sodachiya.3dm` | Rhinoで開く版（更新係の作り直し`run_all.sh --publish`が書く。0番は空の作業用レイヤー） |
| `drawings/` | 3dmから自動の1/100の図のPDF（平面・断面・立面1・2・面積表）。DXF・PNG・面積表のjsonは`model/drawings/` |
| `presentation.pdf` | 提出のA1 5枚（`present/mock.py`が書く） |
| `concept.txt` | 設計趣旨（ユーザーが書く。`present/mock.py`が読む、「#」の行は読まない） |
| `logo/` | 園のロゴ（`sodachiya_logo.svg`が元：黒＝エッチング、透明＝ガラス。`.png`（透明）・`.pdf`は書き出し。ユーザーが書き換えてよい） |

## フォルダ

| フォルダ | 中身 | 担当 |
|---|---|---|
| `model/` | 作業用の3dm。`sodachiya_exact_mesh.3dm`（スクリプトが読むメッシュの版、Rhino版は直下の`sodachiya.3dm`）、`sodachiya_approachA_layers.3dm`（外構、取り込み用、70〜79）、`sodachiya_play_layers.3dm`・`sodachiya_garden_layers.3dm`（遊戯室・園庭、取り込み用）、`drawings/`（3dm から自動の図のDXF・PNG・面積表のjson・干渉の一覧）、`build/`（3dm を作るスクリプト） | 本体＝3dm のチャット、外構＝図のチャット |
| `scripts/` | 図をつくるスクリプト（matplotlib＋shapely）。`garden*.py`（園庭）と `play*.py`（遊戯室）はそれぞれのチャット | 図のチャット（garden・play はそれぞれ） |
| `data/` | 図と 3dm が共有する寸法とデータ。`approachA.json`（アプローチ A 案の寸法、`NORTH` は西館の周りと北）、`forest.json`（ホールの北山杉の林）、`minami.json`（みなみのさんかく＝乳児の園庭）、`garden.json`（園庭＝だいさんかく・しずかのもり、園庭のチャット）、`play.json`（遊戯室、遊戯室のチャット）、`wnew.pkl`（西館の輪郭） | 書いたチャットが責任をもつ |
| `out/` | 出力した PDF・PNG | 図のチャット |
| `mokei/` | 1/100 模型の作り方とレーザーカッター用のデータ（寸法は `data/mokei.json`） | 模型作成のチャット |
| `archive/` | 10-18 の引き継ぎ一式（古いスクリプト、/tmp の絶対パスのまま） | 参照のみ |
| `renkei/` | チャット間の連携（1項1ファイルの`open/`・済んだ`done/`）、受け箱を作る`inbox.py`（→`inbox.md`）、変更の記録（チャットごとの`log/`）、古い連携と変更の記録（`archive/`）。使い方は`inbox.py`の頭 | 項はそれぞれ出した係、状態の行はあて先の係、決まりは設計監修 |

役割分担は10-27から`yakuwari.md`（このフォルダ）。決定事項は、claude.ai のプロジェクト「建築設計課題：こども園」の文書（`決定事項`とその分冊）にある。チャット間の依頼（連携）と変更の記録は、10-24夕から`renkei/`（上の表）。受け箱の文書（`受け箱`）は`renkei/inbox.py`が作ったものを写す。

## 3dm のレイヤー番号

- 00〜69：本体（3dm のチャット）
- 70〜79：外構（図のチャット、`scripts/export3dm.py` で書き出す）
- 80〜89：遊戯室（`scripts/play3d.py` → `model/sodachiya_play_layers.3dm`）
- 90〜99：園庭（`scripts/garden_export.py` → `model/sodachiya_garden_layers.3dm`）

座標は mm、敷地は `00_敷地` と同じ。図のスクリプトは m（3dm の座標 ÷ 1000）。

## 動かし方

```
pip install shapely rhino3dm matplotlib --break-system-packages
python sodachiya/scripts/approachA.py      # → sodachiya/out/sodachiya_site_A_1-200.pdf / .png
python sodachiya/scripts/approachN.py      # → sodachiya/out/sodachiya_site_N_1-200.pdf / .png（北半分：西館の周り・読書の庭・機械室、形は north_common.py）
python sodachiya/scripts/export3dm.py      # → sodachiya/model/sodachiya_approachA_layers.3dm（78・79 はみなみのさんかく）
python sodachiya/scripts/minami01.py       # → sodachiya/out/sodachiya_minami_01.pdf / .png（みなみのさんかく 1/50、形は minami_common.py）
python sodachiya/scripts/garden01.py       # 園庭 → sodachiya/out/sodachiya_garden_01（共通 garden_common.py、木の下書き garden_trees.py）
python sodachiya/scripts/forest_gen.py     # ホールの北山杉の林の配列 → data/forest.json の TREES
python sodachiya/scripts/forest01.py       # → sodachiya/out/sodachiya_forest_01.pdf / .png（平面・断面・模型の表）
python sodachiya/scripts/forest02.py       # → sodachiya/out/sodachiya_forest_02.pdf / .png（目の高さの景色・透け方のばら）
python sodachiya/scripts/forest03.py       # → sodachiya/out/sodachiya_forest_03.pdf / .png（幹の頭と足もと 1/5）
```

フォントは Noto Sans CJK JP。出力先は環境変数 `OUT` で変えられる。

### 3dm と 1/100 の図の作り直し（10-24）

```
bash sodachiya/model/build/setup.sh                 # 作業場を用意（新しいセッションで一度）
bash sodachiya/model/build/run_all.sh               # 確かめるだけ：/tmp/claude-0/out/preview/ に作る（リポジトリは変わらない）
bash sodachiya/model/build/run_all.sh OUT s4        # 前半（しつらえまで）の写しを使い回す。前半の読むものが変わっていれば自動ではじめから
bash sodachiya/model/build/run_all.sh OUT base --publish   # 更新係だけ：リポジトリに書く
```

- **作ったもの（`sodachiya.3dm`・`drawings/`・`model/sodachiya_exact_mesh.3dm`・`model/drawings/`）を push するのは更新係だけ**（ユーザー、10-24）。ほかのチャットはスクリプト・データ・取り込み用ファイルだけを push し、受け箱の更新係の行に「作り直しが要る」と一行書く。
- 最後に `check_build.py` が面積表と干渉の一覧を前の版と比べる（`model/drawings/sodachiya_check.txt`、preview では preview の中）。課題の判定が○でなくなる・延床が2,000を超える・屋根から出る／屋根の外へ出る構造／埋まったガラスが増える、のどれかで「止める」。面積が0.5 m²より変わった部屋は知らせる。
- 段ごとに読むものは `model/build/stages.md`（作り直しのたびに自動で書く）。データを変えたら、それを読むいちばん上の段から下が作り直しになる。

## 決まり

- 作業の前に `git pull`、終わったら commit して push。commit のメッセージにチャットの名前を入れる（例：`[図] 配置図に0〜2歳を追加`、`[3dm] 西館の輪郭を更新`）。
- 他の担当のファイルは書き換えない。直してほしいことはプロジェクトの `連携` に書く。
- 寸法を変えたら `data/` の JSON を直し、そこから図と 3dm をつくり直す（数字をスクリプトに直接書かない）。
