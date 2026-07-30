# sample-images

教材に載せるサンプル画像を置くフォルダです。

**すべて作成済みです。**

実例キャラクターは「アイナ」（架空のAI活用コンサルタント）です。

---

## 作り方（再現手順）

```text
1. Codex ImageGen でキャラクター画像を6枚生成
   → generated/
2. ImageMagick で背景を flood fill で透過
   → transparent/
3. ImageMagick で LINE仕様のスタンプに加工（余白・サイズ・文字入れ）
   → stamps/
4. ImageMagick で比較用の説明図を組み立て
   → figures/
```

2〜4は次のコマンドで再実行できます。

```powershell
# Windows
python scripts\build_sample_figures.py
```

```bash
# macOS
python3 scripts/build_sample_figures.py
```

`--skip-transparent` を付けると、透過処理を飛ばして図版だけ作り直せます。

---

## generated/ — 生成したままの画像（6枚）

Codex ImageGen で生成しました。背景は均一な薄いグレー（#EFEFEF）です。

| ファイル | 内容 |
| --- | --- |
| `aina_base.png` | 基準画像（正面・にっこり）。以降の生成で参照用に使う |
| `aina_happy.png` | 喜ぶ（両手を突き上げる） |
| `aina_sorry.png` | 困り顔（手を合わせて謝る） |
| `aina_ok.png` | 了解ポーズ（サムズアップ＋ウインク） |
| `aina_surprised.png` | 驚く（両手を頬に当てる） |
| `aina_reject_tall.png` | **ボツ案**：頭身だけ6頭身に変えたもの（失敗例として使う） |

### 背景を薄いグレーにした理由

キャラクターが**白いTシャツ**を着ています。

白背景で生成すると、背景を透過するときにTシャツも消えます。

薄いグレーにすると境界が残るので、切り抜けます。

これは第5章で説明している実務上のコツです。

---

## transparent/ — 背景を透過した画像（6枚）

`generated/` の背景だけを透明にしたものです。

### flood fill を使う理由

```text
× magick in.png -fuzz 20% -transparent "#EFEFEF" out.png
   → 画像全体の一致する色を消すため、白いTシャツも消える

○ magick in.png -alpha set -bordercolor "#EFEFEF" -border 2 \
     -fuzz 20% -fill none -draw "alpha 0,0 floodfill" -shave 2x2 out.png
   → 四隅からつながった領域だけを消すため、内側の白は残る
```

先に2pxの枠を足すのは、背景が四隅まで確実につながるようにするためです。

---

## stamps/ — LINE仕様のスタンプ画像（7枚）

**検証ツールの全項目を通過しています**（枚数チェックのみ、サンプル5枚のためNG）。

| ファイル | サイズ | セリフ |
| --- | --- | --- |
| `stamp_001.png` | 370×320 | おはよ！ |
| `stamp_002.png` | 370×320 | 了解っしょ！ |
| `stamp_003.png` | 370×320 | ごめん！ |
| `stamp_004.png` | 370×320 | びっくり |
| `stamp_005.png` | 370×320 | やったー！ |
| `main.png` | 240×240 | （メイン画像） |
| `tab.png` | 96×74 | （タブ画像・顔だけ） |

### 満たしている条件

- 370×320px 以内（公式の最大サイズ）
- 縦横ともに偶数ピクセル
- 透過PNG（実際に透明部分がある）
- **上下左右に10px以上の余白**（公式の推奨値）
- 1個あたり1MB以下
- 文字は白フチ＋濃色の2重フチ（暗いトーク背景でも読める）

### 検証コマンド

```powershell
python scripts\validate_images.py assets\sample-images\stamps
```

枚数（5枚）以外はすべてOKになります。

---

## figures/ — 説明図（8枚）

原稿に貼る比較図です。

| ファイル | 使う章 | 内容 |
| --- | --- | --- |
| `fig_transparency.png` | 第1・6・8・12章 | **透過の成功例と失敗例**（暗い背景に重ねて比較） |
| `fig_outline.png` | 第6・12章 | **白フチのあり・なし**（暗い背景で比較） |
| `fig_size_compare.png` | 第1・6章 | 3種類の画像サイズを実寸で並べる |
| `fig_talk_preview.png` | 第6章 | トーク表示サイズでの見え方（明・暗の再現図） |
| `fig_margin.png` | 第6・8・12章 | 余白10pxのあり・なし（赤枠がガイド） |
| `fig_textlength.png` | 第4・6・12章 | 文字数と可読性（4／10／15文字） |
| `fig_headcount.png` | 第3・5・12章 | 頭身の比較（3頭身と6頭身） |
| `fig_stamp_sheet.png` | 第6・13章 | 5枚を並べて統一感を確認 |

### 「再現図」と明記している図

`fig_talk_preview.png` は、LINEの画面そのものではありません。

**見え方を確認するために作った再現図**です。

図の中にもその旨を書いています。

実際のLINEの画面が必要な場合は、`assets/screenshots/` の手動撮影リストを参照してください。

---

## ライセンスと権利の確認事項

### 画像生成AI

Codex ImageGen で生成しています。

**教材（有料販売）に掲載する前に、生成物の商用利用条件を規約でご確認ください。**

### フォント

図版の文字は **Windows 同梱フォント（Meiryo Bold）** で描画しています。

商用配布する場合は、フォントのライセンスを確認してください。

オープンライセンスのフォント（Noto Sans JP など）に差し替える場合は、
`scripts/build_sample_figures.py` の `FONT_CANDIDATES` のパスだけを変更すれば済みます。

### キャラクターの設計上の配慮

- 実在の人物・芸能人・インフルエンサーに似せていない
- 既存のアニメ・漫画・ゲームのキャラクターに似せていない
- 企業ロゴ・商標・ブランド名を描いていない
- 画像内に文字を一切描いていない（IDカードもノートパソコンの画面も無地）
- 肌の色は「日焼け」として色コード（#A9714B）で指定し、
  特定の人種・国籍・属性を戯画化していない

---

## 公開ページ

これらの画像は、次のページからダウンロードできます。

https://line-stamp-note.pages.dev/

コピー用のSNS投稿文・タイトル・説明文も同じページにまとめています。
