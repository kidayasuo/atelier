<!-- eyebrow: 建築設計実習Ⅱ—Ⅰ -->
# 育ち舎（こども園）

設計課題「こどもたちの育ち舎」の図・3dm・スクリプト。提出 2026-11-05。

## フォルダ

| フォルダ | 中身 | 担当 |
|---|---|---|
| `model/` | 3dm。`sodachiya_exact.3dm`（本体の架構・部屋）、`sodachiya_exact_mesh.3dm`（スクリプトが読むメッシュの版）、`sodachiya_approachA_layers.3dm`（外構、取り込み用、70〜79）、`drawings/`（3dm から自動の 1/100 の図）、`build/`（3dm を作るスクリプト） | 本体＝3dm のチャット、外構＝図のチャット |
| `scripts/` | 図をつくるスクリプト（matplotlib＋shapely） | 図のチャット |
| `data/` | 図と 3dm が共有する寸法とデータ。`approachA.json`（アプローチ A 案の寸法）、`forest.json`（ホールの北山杉の林）、`minami.json`（みなみのさんかく＝乳児の園庭）、`wnew.pkl`（西館の輪郭） | 書いたチャットが責任をもつ |
| `out/` | 出力した PDF・PNG | 図のチャット |
| `mokei/` | 1/100 模型の作り方とレーザーカッター用のデータ（寸法は `data/mokei.json`） | 模型作成のチャット |
| `archive/` | 10-18 の引き継ぎ一式（古いスクリプト、/tmp の絶対パスのまま） | 参照のみ |

決定事項・役割分担・チャット間の依頼は、claude.ai のプロジェクト「建築設計課題：こども園」の文書（`決定事項`・`役割分担`・`連携`・`変更の記録`）にある。ここ（リポジトリ）はファイルの置き場。

## 3dm のレイヤー番号

- 00〜69：本体（3dm のチャット）
- 70〜79：外構（図のチャット、`scripts/export3dm.py` で書き出す）
- 80〜89：あき（新しい担当ができたら、ここから割り当てる）

座標は mm、敷地は `00_敷地` と同じ。図のスクリプトは m（3dm の座標 ÷ 1000）。

## 動かし方

```
pip install shapely rhino3dm matplotlib --break-system-packages
python sodachiya/scripts/approachA.py      # → sodachiya/out/sodachiya_site_A_1-200.pdf / .png
python sodachiya/scripts/export3dm.py      # → sodachiya/model/sodachiya_approachA_layers.3dm（78・79 はみなみのさんかく）
python sodachiya/scripts/minami01.py       # → sodachiya/out/sodachiya_minami_01.pdf / .png（みなみのさんかく 1/50、形は minami_common.py）
python sodachiya/scripts/forest_gen.py     # ホールの北山杉の林の配列 → data/forest.json の TREES
python sodachiya/scripts/forest01.py       # → sodachiya/out/sodachiya_forest_01.pdf / .png（平面・断面・模型の表）
python sodachiya/scripts/forest02.py       # → sodachiya/out/sodachiya_forest_02.pdf / .png（目の高さの景色・透け方のばら）
python sodachiya/scripts/forest03.py       # → sodachiya/out/sodachiya_forest_03.pdf / .png（幹の頭と足もと 1/5）
```

フォントは Noto Sans CJK JP。出力先は環境変数 `OUT` で変えられる。

## 決まり

- 作業の前に `git pull`、終わったら commit して push。commit のメッセージにチャットの名前を入れる（例：`[図] 配置図に0〜2歳を追加`、`[3dm] 西館の輪郭を更新`）。
- 他の担当のファイルは書き換えない。直してほしいことはプロジェクトの `連携` に書く。
- 寸法を変えたら `data/` の JSON を直し、そこから図と 3dm をつくり直す（数字をスクリプトに直接書かない）。
