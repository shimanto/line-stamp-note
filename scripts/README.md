# scripts フォルダの使い方

LINEスタンプ制作を助けるPythonスクリプトです。

**プログラミング経験は不要です。**

コマンドをコピーして実行するだけで動きます。

対応する章：**第11章　Claude Codeによる自動化**

---

## この5つのスクリプトができること

| ファイル | できること | 手作業なら |
| --- | --- | --- |
| `validate_images.py` | 画像40枚の仕様を一括チェック（11項目） | 30分以上（一部は目視不可能） |
| `rename_images.py` | 画像を `stamp_001.png` 形式に一括リネーム | 20〜30分 |
| `create_csv.py` | セリフ管理用のCSVを作成 | 15分 |
| `build_full_manuscript.py` | 教材の章を結合（**教材の保守用**） | ー |
| `build_sample_figures.py` | サンプル画像と説明図を生成（**教材の保守用**） | ー |

**最後の2つは、教材を編集する人向けです。**

スタンプ制作では使いません。

必要なものが違います。

| スクリプト | 必要なもの |
| --- | --- |
| `validate_images.py` | Python + **Pillow** |
| `rename_images.py` / `create_csv.py` / `build_full_manuscript.py` | Python のみ |
| `build_sample_figures.py` | Python + **ImageMagick 7** |

### とくに重要なのは validate_images.py です

理由は、**目視では不可能な確認ができるから**です。

- 拡張子はPNGだが、中身がJPEGになっている
- 透過情報はあるが、実際には全部不透明（白で塗りつぶしただけ）

この2つは、画面を見ても判別できません。

そして、どちらもリジェクトの原因になります。

---

## 1. Pythonの導入

### インストールされているか確認する

ターミナル（後述）を開いて、次を実行します。

**Windows（PowerShell）**

```powershell
python --version
```

**macOS（ターミナル）**

```bash
python3 --version
```

`Python 3.12.0` のようなバージョン番号が出れば、インストール済みです。

### `python` と `python3` の違い

**ここでつまずく人が多いので、はっきり書きます。**

| OS | 使うコマンド |
| --- | --- |
| Windows | `python` |
| macOS | `python3` |

macOSで `python` と打つと、古いバージョンが動くかエラーになります。

**macOSでは必ず `python3` と打ってください。**

以降は両方を併記します。

### インストールされていない場合

**Windows**

方法1：Microsoft Store

1. Microsoft Store を開く
2. 「Python」で検索する
3. 最新版をインストールする

方法2：公式サイト

1. Python公式サイトからインストーラーをダウンロードする
2. インストーラーを実行する
3. **「Add Python to PATH」に必ずチェックを入れる**
4. インストールする
5. **PowerShellを閉じて、開き直す**

「Add Python to PATH」のチェックを忘れると、PowerShellから起動できません。

そして、PowerShellを開き直さないと設定が反映されません。

**macOS**

多くの場合、`python3` が最初から入っています。

入っていない場合は、Python公式サイトからインストーラーをダウンロードしてください。

---

## 2. Pillowのインストール

画像を扱うために、Pillow（ピロー）というライブラリが必要です。

**`validate_images.py` だけが必要とします。**

他の3つは、Python標準機能のみで動きます。

### インストール

**Windows（PowerShell）**

```powershell
python -m pip install Pillow
```

**macOS（ターミナル）**

```bash
python3 -m pip install Pillow
```

インストールが終わると `Successfully installed Pillow-...` と表示されます。

### 確認

**Windows**

```powershell
python -c "import PIL; print(PIL.__version__)"
```

**macOS**

```bash
python3 -c "import PIL; print(PIL.__version__)"
```

バージョン番号が出ればOKです。

---

## 3. ターミナルの開き方

「ターミナル」とは、文字でコマンドを入力する画面です。

### Windows（PowerShell）

**方法1**

1. キーボードの `Windows` キーを押す
2. `powershell` と入力する
3. 「Windows PowerShell」をクリックする

**方法2（おすすめ）**

1. 作業したいフォルダをエクスプローラーで開く
2. アドレスバーをクリックして、`powershell` と入力してEnter
3. そのフォルダの場所でPowerShellが開く

**方法2だとフォルダ移動が不要になります。**

### macOS（ターミナル）

**方法1**

1. `Command` + `Space` キーを押す
2. `ターミナル` または `Terminal` と入力する
3. Enterを押す

**方法2（おすすめ）**

1. Finderで作業したいフォルダを開く
2. フォルダを右クリック
3. 「フォルダに新しいターミナル」を選ぶ

---

## 4. 覚えるコマンドは4つだけ

| やりたいこと | Windows | macOS |
| --- | --- | --- |
| 今いる場所を確認 | `pwd` | `pwd` |
| フォルダの中身を見る | `ls` | `ls` |
| フォルダを移動 | `cd フォルダ名` | `cd フォルダ名` |
| 1つ上に戻る | `cd ..` | `cd ..` |

### パスの書き方の違い

| 項目 | Windows | macOS |
| --- | --- | --- |
| 区切り文字 | `\`（円記号） | `/`（スラッシュ） |
| 先頭 | `C:\Users\...` | `/Users/...` |

### 入力を楽にする方法

`cd ` と打ったあと（半角スペースを入れる）、フォルダをターミナルの画面にドラッグ＆ドロップします。

パスが自動で入力されます。

---

## 5. フォルダ構成

このスクリプトは、次の構成を前提にしています。

```text
line-stamp/
├── raw/           生成したままの画像
├── edited/        加工済みの画像（透過・文字入れ済み）
├── output/        リネーム後の申請用画像（main.png と tab.png もここ）
├── csv/           stamp_list.csv
├── prompts/       使ったプロンプト
├── boneyard/      ボツ案（SNS投稿用に保存）
└── scripts/       このフォルダ
    ├── validate_images.py
    ├── rename_images.py
    ├── create_csv.py
    └── build_full_manuscript.py
```

### フォルダを作るコマンド

**Windows（PowerShell）**

```powershell
New-Item -ItemType Directory -Force -Path raw, edited, output, csv, prompts, boneyard
```

**macOS（ターミナル）**

```bash
mkdir -p raw edited output csv prompts boneyard
```

### `boneyard`（ボツ案）を分ける理由

ボツ案は、SNSでいちばん反応がある素材です（第9章）。

捨てずに残します。

ただし、申請用フォルダに混ざると枚数が合わなくなります。

だからフォルダを分けます。

---

## 6. create_csv.py の使い方

セリフ40個を管理するCSVを作ります。

### 基本

**Windows**

```powershell
python scripts\create_csv.py --output csv\stamp_list.csv
```

**macOS**

```bash
python3 scripts/create_csv.py --output csv/stamp_list.csv
```

### 空のテンプレートとして作る

セリフを自分で入れたい場合は `--empty` を付けます。

```powershell
python scripts\create_csv.py --output csv\stamp_list.csv --empty
```

```bash
python3 scripts/create_csv.py --output csv/stamp_list.csv --empty
```

40行の枠だけが作られます。

カテゴリー・番号・ファイル名は埋まっています。

### 行数を変える

```powershell
python scripts\create_csv.py --rows 24
```

### 既存ファイルを上書きする

既にファイルがある場合、そのままでは上書きしません。

上書きする場合は `--force` を付けます。

```powershell
python scripts\create_csv.py --output csv\stamp_list.csv --force
```

**バックアップ（`_backup` 付きのファイル）が自動で作られます。**

### 出力される列

```text
number,category,text,emotion,pose,image_prompt,status,filename,notes
```

| 列名 | 内容 |
| --- | --- |
| number | 通し番号（1〜40） |
| category | カテゴリー |
| text | セリフ |
| emotion | 表情 |
| pose | ポーズ |
| image_prompt | 画像生成プロンプトのメモ |
| status | 進捗（todo / generated / edited / done） |
| filename | 対応するファイル名 |
| notes | メモ |

### 文字化けについて

このスクリプトは**UTF-8 BOM付き**で出力します。

BOM（ボム）とは、ファイルの先頭に付ける短い印です。

これがあると、Excelが「日本語のファイルだ」と判断してくれます。

BOMがないと、Excelで開いたときに文字化けすることがあります。

---

## 7. rename_images.py の使い方

画像を `stamp_001.png` 形式の連番にします。

### 基本

**Windows**

```powershell
python scripts\rename_images.py --input edited --output output
```

**macOS**

```bash
python3 scripts/rename_images.py --input edited --output output
```

### 実行すると出る画面

```text
============================================================
リネーム対象ファイル一覧
============================================================
入力フォルダ: C:\Users\...\edited
出力フォルダ: C:\Users\...\output

    1. IMG_2034.png                 ->  stamp_001.png
    2. IMG_2035.png                 ->  stamp_002.png
    3. IMG_2036.png                 ->  stamp_003.png
  ...
   40. IMG_2073.png                 ->  stamp_040.png

対象ファイル数: 40 件

次のファイルは連番から除外し、名前を変えずにコピーします。
  - main.png
  - tab.png
============================================================

この内容でコピーを実行しますか? (y/N):
```

`y` を入力するまで、何も起きません。

### 3つの安全設計

**1. 元ファイルを上書きしません**

入力フォルダには一切書き込みません。

出力フォルダへコピーします。

失敗してもやり直せます。

**2. 処理前に一覧を表示します**

確認してから実行できます。

**3. 並び順が崩れません**

ファイル名の数字を「数値」として比較します。

```text
× img1.png, img10.png, img2.png
○ img1.png, img2.png, img10.png
```

### よく使うオプション

| オプション | 内容 |
| --- | --- |
| `--yes` | 確認を省略して実行する |
| `--dry-run` | 一覧だけ表示して、コピーはしない |
| `--start 11` | 番号を11から始める |
| `--prefix line` | `line_001.png` の形式にする |
| `--digits 4` | `stamp_0001.png` の形式にする |

### 例：まず確認だけしたい

```powershell
python scripts\rename_images.py --input edited --output output --dry-run
```

---

## 8. validate_images.py の使い方

**申請前に必ず実行してください。**

### 基本

**Windows**

```powershell
python scripts\validate_images.py output
```

**macOS**

```bash
python3 scripts/validate_images.py output
```

フォルダ名を省略すると、現在のフォルダを対象にします。

### チェックする8項目

| No | チェック内容 | なぜ必要か |
| --- | --- | --- |
| 1 | 中身が本当にPNGか | 拡張子だけPNGの偽装を検出 |
| 2 | 画像サイズが規定内か | サイズ超過はリジェクト原因 |
| 3 | 縦横が偶数ピクセルか | 奇数はリジェクト原因になりうる |
| 4 | 枚数が 8/16/24/32/40 か | 中途半端な枚数では申請できない |
| 5 | 透過情報（RGBA）があるか | 透過なしはリジェクト原因 |
| 6 | 実際に透明な部分があるか | 「白塗り」を検出 |
| 7 | ファイル名が正しい形式か | 順番崩れを防ぐ |
| 8 | 画像が壊れていないか | アップロード失敗を防ぐ |

さらに、`main.png` と `tab.png` の存在とサイズも確認します。

### 出力例（問題がない場合）

```text
============================================================
 LINEスタンプ画像 検証ツール
============================================================
対象フォルダ: C:\Users\...\output

[1] ファイルの読み込み
  PNGファイル: 40 件
  メイン画像 (main.png): 見つかりました
  タブ画像   (tab.png): 見つかりました

[2] 枚数チェック
  OK: スタンプ画像は 40 枚です（申請可能な枚数）

[3] 各画像のチェック
  OK: 40 件すべて問題ありません

[4] メイン画像・タブ画像のチェック
  OK: main.png (240 x 240)
  OK: tab.png (96 x 74)

============================================================
 結果: 問題は見つかりませんでした
============================================================
```

### 出力例（問題がある場合）

```text
[3] 各画像のチェック

  NG: stamp_007.png
      - 中身がPNG形式ではありません（実際の形式: JPEG）
      - 透過情報がありません（カラーモード: RGB）

  NG: stamp_012.png
      - 画像サイズが規定を超えています（412 x 340 / 上限 370 x 320）

  NG: stamp_019.png
      - 透過情報はありますが、透明な部分が見つかりません
        （背景が白などで塗りつぶされている可能性があります）
```

**どのファイルに、何の問題があるかが日本語で表示されます。**

### 仕様が変わったときの修正方法

スクリプトの冒頭に、設定をまとめてあります。

```python
# ============================================================
# 設定（LINE側の仕様が変わったら、ここだけ修正してください）
# ============================================================

STAMP_MAX_SIZE = (370, 320)      # スタンプ画像の最大サイズ
MAIN_IMAGE_SIZE = (240, 240)     # メイン画像のサイズ
TAB_IMAGE_SIZE = (96, 74)        # タブ画像のサイズ
VALID_STAMP_COUNTS = [8, 16, 24, 32, 40]   # 申請可能な枚数
MAX_FILE_SIZE_KB = 1024          # ファイルサイズ上限
```

**この数値だけを書き換えてください。**

他の場所を触る必要はありません。

> **上記の数値は参考値です。申請前にLINE Creators Market公式の最新ガイドラインで確認し、違っていればここを書き換えてください。**

---

## 9. build_full_manuscript.py の使い方

**このスクリプトは教材の保守用です。**

スタンプ制作では使いません。

`manuscript/` の各章を結合して `full_manuscript.md` を作ります。

### 基本

リポジトリのルートで実行します。

**Windows**

```powershell
python scripts\build_full_manuscript.py
```

**macOS**

```bash
python3 scripts/build_full_manuscript.py
```

### 文字数だけを数える

```powershell
python scripts\build_full_manuscript.py --count-only
```

章ごとの文字数と合計が表示されます。

### やっていること

1. `manuscript/00_*.md` 〜 `13_*.md` を番号順に読む
2. 各章の見出しレベルを1段下げる（`#` → `##`）
3. コードブロック（``` で囲まれた部分）の中は変換しない
4. 先頭に書籍タイトルと目次を付ける
5. 章ごとの文字数を表示する

**章を編集したら、必ず再実行してください。**

---

## 9-2. build_sample_figures.py の使い方

**このスクリプトも教材の保守用です。**

スタンプ制作では使いません。

ImageMagick で、サンプル画像と説明図を作り直します。

### 必要なもの

ImageMagick 7 以上が必要です。

```powershell
magick -version
```

`ImageMagick 7.x.x` と表示されればOKです。

### 基本

リポジトリのルートで実行します。

```powershell
# Windows
python scripts\build_sample_figures.py
```

```bash
# macOS
python3 scripts/build_sample_figures.py
```

### オプション

| オプション | 内容 |
| --- | --- |
| `--skip-transparent` | 透過処理を飛ばす（図版だけ作り直すとき） |
| `--only transparency` | 特定の図だけ作り直す |

`--only` に指定できる名前です。

```text
transparency / outline / size_compare / margin /
headcount / textlength / stamp_sheet / talk_preview
```

### 入力と出力

```text
入力: assets/sample-images/generated/*.png
       （Codex ImageGen で生成した画像。背景は単色 #EFEFEF）

出力: assets/sample-images/transparent/   背景を透過した画像
      assets/sample-images/stamps/        LINE仕様のスタンプ
      assets/sample-images/figures/       説明図
```

### 処理のポイント

**1. 背景の透過は flood fill を使う**

```text
× magick in.png -fuzz 20% -transparent "#EFEFEF" out.png
   → 白いTシャツも消える

○ magick in.png -alpha set -bordercolor "#EFEFEF" -border 2 \
     -fuzz 20% -fill none -draw "alpha 0,0 floodfill" -shave 2x2 out.png
   → 四隅からつながった領域だけを消すので、内側の白は残る
```

**2. 余白は10px確保する**

公式の推奨値です。

`370 - 10×2 = 350`、`320 - 10×2 = 300` に収まるよう縮小してから、
370×320のキャンバス中央に配置しています。

**3. 文字は2回描く**

```text
1回目: 白い太いフチ（-stroke white -strokewidth N）
2回目: その上に濃い色の文字（-stroke none -fill "#2B2B2B"）
```

この順番でないと、フチが文字を覆います。

**4. タブ画像は顔だけ切り出す**

96×74は横長です。

全身を縮小すると何かわからなくなるので、顔の範囲（上から約46%）を切り出しています。

切り出したあとに `-trim` をかけると構図が戻ってしまうので、かけていません。

### フォントについて

Windows 同梱フォント（Meiryo Bold など）を使っています。

**商用配布する場合は、フォントのライセンスを確認してください。**

オープンライセンスのフォントに差し替える場合は、
スクリプト冒頭の `FONT_CANDIDATES` にパスを追加するだけです。

```python
FONT_CANDIDATES = [
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/biz-udgothicb.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
]
```

---

## 10. 作業の全体フロー

実際の作業順に並べます。

### Windows（PowerShell）

```powershell
# 1. 作業フォルダへ移動
cd C:\Users\あなたのユーザー名\line-stamp

# 2. Pythonとライブラリの確認
python --version
python -c "import PIL; print(PIL.__version__)"

# 3. CSVを作る（セリフ管理用）
python scripts\create_csv.py --output csv\stamp_list.csv

# 4. 画像を生成して edited フォルダに加工済みを置く（手作業）

# 5. 連番にリネームして output へコピー
python scripts\rename_images.py --input edited --output output

# 6. main.png と tab.png を output に置く（手作業）

# 7. 検証する
python scripts\validate_images.py output

# 8. 問題がなければ申請へ
```

### macOS（ターミナル）

```bash
# 1. 作業フォルダへ移動
cd /Users/あなたのユーザー名/line-stamp

# 2. Pythonとライブラリの確認
python3 --version
python3 -c "import PIL; print(PIL.__version__)"

# 3. CSVを作る（セリフ管理用）
python3 scripts/create_csv.py --output csv/stamp_list.csv

# 4. 画像を生成して edited フォルダに加工済みを置く（手作業）

# 5. 連番にリネームして output へコピー
python3 scripts/rename_images.py --input edited --output output

# 6. main.png と tab.png を output に置く（手作業）

# 7. 検証する
python3 scripts/validate_images.py output

# 8. 問題がなければ申請へ
```

---

## 11. エラー時の確認方法

### エラー1　`python` が見つからない

**表示例（Windows）**

```text
'python' は、内部コマンドまたは外部コマンド、
操作可能なプログラムまたはバッチ ファイルとして認識されていません。
```

**原因**

- Pythonがインストールされていない
- インストール時に「Add Python to PATH」をチェックしなかった

**対処**

1. Pythonを再インストールする
2. インストール時に「Add Python to PATH」にチェックを入れる
3. **PowerShellを閉じて、開き直す**

### エラー2　`python3` が見つからない（macOS）

**対処**

`python` で試してください。

```bash
python --version
```

バージョンが3以上なら、`python` で動きます。

### エラー3　`ModuleNotFoundError: No module named 'PIL'`

**原因**

Pillowがインストールされていません。

**対処**

```powershell
python -m pip install Pillow
```

```bash
python3 -m pip install Pillow
```

### エラー4　`No such file or directory` / フォルダが見つかりません

**対処**

1. 今いる場所を確認する

```bash
pwd
```

2. 中身を確認する

```bash
ls
```

3. `scripts` フォルダが見えていますか

見えていなければ、フォルダを移動します。

### エラー5　日本語が文字化けする（Windows）

**症状**

`????` や記号になる。

**対処**

PowerShellで次を実行してから、スクリプトを実行します。

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### エラー6　`Permission denied` / 書き込めませんでした

**原因**

ファイルが他のソフトで開かれています。

**対処**

ExcelやプレビューでCSVや画像を開いていたら、閉じてください。

### エラー7　`UnicodeDecodeError`

**原因**

CSVやMarkdownの文字コードが違います。

**対処**

テキストエディタで開き、UTF-8で保存し直します。

または `create_csv.py` で作り直します。

### エラー8　画像が1件も見つからない

**対処**

1. 画像がそのフォルダに入っているか確認する
2. 拡張子が `.png` になっているか確認する
3. `--input` で正しいフォルダを指定しているか確認する

---

## 12. スクリプトの方針

このフォルダのスクリプトは、次の方針で書いています。

- **外部APIを使わない**（ネットワーク通信なし）
- **依存ライブラリはPillowのみ**（`validate_images.py` だけ）
- **元ファイルを上書きしない**（出力は別フォルダ）
- **LINE側の仕様値はファイル冒頭にまとめる**（仕様変更時に1か所だけ直す）
- **各関数に日本語コメントを付ける**
- **例外処理を入れて、エラー時に対処方法を表示する**
- **すべての表示を日本語にする**

---

## 13. 困ったときは

第11章に、Claude Codeを使った自動化の手順が書いてあります。

エラーが出た場合は、次のように頼めます。

```text
scripts/validate_images.py を output フォルダに対して実行してください。

エラーが出た場合は、次のことをしてください。

1. 問題のあるファイルを一覧にする
2. 問題の種類ごとに分類する
3. それぞれの直し方を、画像編集ソフトでの操作として説明する
4. 自動で直せるものがあれば、修正方法を提案する
   （ただし、元ファイルは上書きしないこと）
```
