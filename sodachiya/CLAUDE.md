# 育ち舎（Claude Code で作業するとき）

2年後期の設計課題「育ち舎」（こども園）。作業はこの `sodachiya/` の中で。ユーザーは木田さん（建築学科の学生、前はソフトウェアエンジニア）。返事は日本語で、短く。

## 始めに
1. `git pull`。`python3 renkei/inbox.py mine <自分の係>` で自分あての項を読む。
2. 読む：`yakuwari.md` は節だけ（`python3 tools/yomu.py yakuwari.md` → 「チャットと担当」「連携と受け箱」「ファイルの置き場」と自分に要る節）。`karuku.md` は全部。
3. 自分の係の決定事項（分冊）。**Claude Code からはプロジェクトの文書（「決定事項」「受け箱」の文書）が読めない**。試しのあいだは、リポジトリに移した分冊だけを使う：`kettei/<係>.md`（無ければユーザーに言う）。共通の「決定事項」の要る所は、ユーザーに聞く。

## 決まり
- スクリプト（`renkei/inbox.py`・`model/build/`・`scripts/`・`mokei/` など）はユーザーのプロジェクトのコード。そのまま走らせてよい。
- 作業の前に pull、終わったらすぐ commit して main に push（ブランチ・PR は使わない）。commit の頭は担当（`[模型]`・`[園庭]` など）。拒まれたら `git pull --rebase`。
- 自分の担当でないファイルは書き換えない（小さな直しの決まりは `yakuwari.md` の最後の段）。作ったもの（3dm・`drawings/`・`model/drawings/`）は push しない（push で自動に作り直る）。
- 依頼・知らせは `renkei/inbox.py new`、変更の記録は `inbox.py log`、受け箱は `python3 renkei/inbox.py` で作って push（プロジェクトの受け箱の写しは、次に claude.ai のチャットが上書きする）。
- 決まったことは `kettei/<係>.md` に（直す所だけ Edit で）。
- 図の文字は Noto Sans CJK JP、PDF は Type42（`scripts/fonts42.py`）。フォントが無ければ `sudo apt-get install -y fonts-noto-cjk`。
- 和文と数字・欧文のあいだに空白を入れない。数字と単位のあいだは空白（「3 m」）。
