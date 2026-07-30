#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_reading_site.py

原稿14章を挿絵つきのHTMLに変換して、通読用サイトを作ります。

【このスクリプトは教材の保守用です】

【作るもの】
    site/read/index.html    全14章を1ページに収めた通読版
    site/read/ch00.html 〜 ch13.html
                            章ごとのページ（noteへ貼り付ける用）
    site/read/img/          挿絵として使う画像

【挿絵の扱い】
    原稿の【スクリーンショット挿入】ブロックを、次のように置き換えます。

      対応する画像がある場合   → 実際の画像を表示（キャプション付き）
      対応する画像がない場合   → 撮影指示を書いた枠を表示

    「撮影指示の枠」を残すのは、読みながら
    「ここに何の画像が入る予定か」がわかるようにするためです。

【必要なもの】
    Python の markdown ライブラリ
        Windows : python -m pip install markdown
        macOS   : python3 -m pip install markdown

使い方:
    python  scripts/build_reading_site.py      # Windows
    python3 scripts/build_reading_site.py      # macOS

外部APIは使用しません。
"""

import os
import re
import sys
import html
import shutil
import argparse

# ============================================================
# パス
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR_MS = os.path.join(ROOT, "manuscript")
DIR_OUT = os.path.join(ROOT, "site", "read")
DIR_IMG = os.path.join(DIR_OUT, "img")

DIR_SHOT_PUB = os.path.join(ROOT, "assets", "screenshots", "public")
DIR_SHOT_TERM = os.path.join(ROOT, "assets", "screenshots", "terminal")
DIR_FIG = os.path.join(ROOT, "assets", "sample-images", "figures")
DIR_STAMPS = os.path.join(ROOT, "assets", "sample-images", "stamps")
DIR_TRANS = os.path.join(ROOT, "assets", "sample-images", "transparent")

BOOK_TITLE = "【2026年最新版】生成AIでLINEスタンプを作って販売する完全ガイド"
BOOK_SUB = "ChatGPT・Claude・ImageGenを使って、企画から審査・販売まで進める方法"

LINE_WIDTH = 60

# ============================================================
# 挿絵の対応表
#
# 原稿の【スクリーンショット挿入】ブロックの「画面：」の行に
# 下のキーワード（正規表現）が含まれていたら、その画像を割り当てます。
#
# 上から順に評価し、最初に一致したものを使います。
# ============================================================

IMAGE_MAP = [
    # ------------------------------------------------------------
    # 【重要】上から順に評価します。
    # 具体的な指示を先に、あいまいな指示を後に置いてください。
    # 順番を間違えると、別の画像が割り当てられます。
    # ------------------------------------------------------------

    # --- 具体的な図（先に判定する） ---
    (r"市松模様",
     (DIR_FIG, "fig_transparency.png"),
     "透過できているかは、暗い背景に重ねて確認する"),
    (r"240×240のキャンバス",
     (DIR_STAMPS, "main.png"),
     "メイン画像（240×240）の作例。顔が大きく見えるようにする"),
    (r"96×74のタブ画像",
     (DIR_STAMPS, "tab.png"),
     "タブ画像（96×74）の作例。横長なので顔だけを切り出す"),

    # --- 公開ページのスクリーンショット（Chromiumで取得済み） ---
    (r"LINE Creators Market のトップページ",
     (DIR_SHOT_PUB, "ch01_01_creators-market-top.png"),
     "LINE Creators Market トップページ（creator.line.me/ja/）"),
    (r"ガイドライン.*ヘルプページ|ガイドライン／ヘルプ",
     (DIR_SHOT_PUB, "ch01_03_guideline-sticker.png"),
     "スタンプ制作ガイドライン（creator.line.me/ja/guideline/sticker/）"),
    (r"スタンプ制作ガイドライン",
     (DIR_SHOT_PUB, "ch01_03_guideline-sticker.png"),
     "スタンプ制作ガイドライン（creator.line.me/ja/guideline/sticker/）"),
    (r"アニメーションスタンプ制作ガイドライン",
     (DIR_SHOT_PUB, "ch10_01_guideline-animationsticker.png"),
     "アニメーションスタンプ制作ガイドライン（creator.line.me/ja/guideline/animationsticker/）"),
    (r"絵文字 制作ガイドライン|絵文字制作ガイドライン",
     (DIR_SHOT_PUB, "ch10_02_guideline-emoji.png"),
     "絵文字 制作ガイドライン（creator.line.me/ja/guideline/emoji/）"),
    (r"LINEストアのスタンプ詳細ページ|LINE STORE",
     (DIR_SHOT_PUB, "ch01_04_line-store-stickershop.png"),
     "LINE STORE スタンプトップ（store.line.me）"),
    (r"Photopeaの編集画面|Photopea の編集画面",
     (DIR_SHOT_PUB, "ch06_01_photopea-editor.png"),
     "Photopea（ブラウザで動く画像編集ツール）"),

    # --- 検証スクリプトの実行結果（実出力を描画） ---
    (r"validate_images\.py.*すべてOK|validate_images\.py の実行結果",
     (DIR_SHOT_TERM, "ch11_01_validate_ok.png"),
     "validate_images.py の実行結果（問題なし）"),
    (r"validate_images\.py でエラー",
     (DIR_SHOT_TERM, "ch11_02_validate_ng.png"),
     "validate_images.py の実行結果（4ファイル・6件の問題を検出）"),
    (r"validate_images\.py の設定セクション",
     (DIR_SHOT_TERM, "ch11_02_validate_ng.png"),
     "検出された問題の一覧（設定セクションの数値で判定している）"),

    # --- 説明図（ImageMagickで作成） ---
    (r"黒背景レイヤーを下に置いて|透過PNGを暗い背景",
     (DIR_FIG, "fig_transparency.png"),
     "透過の成功例と失敗例（暗い背景に重ねて比較）"),
    (r"白フチあり・なしの比較|白フチあり／なし",
     (DIR_FIG, "fig_outline.png"),
     "白フチのあり・なし（暗い背景で比較）"),
    (r"完成した3種類の画像を並べた|3種類の画像のサイズ差",
     (DIR_FIG, "fig_size_compare.png"),
     "スタンプ画像・メイン画像・タブ画像を実寸で並べた比較"),
    (r"トーク背景を暗い色に変更|自分専用グループに画像を送った|LINEの自分専用グループ",
     (DIR_FIG, "fig_talk_preview.png"),
     "トーク表示サイズでの見え方（明るい背景・暗い背景／再現図）"),
    (r"LINEのトーク画面でスタンプを送っている|自作スタンプを実際のトークで",
     (DIR_FIG, "fig_talk_preview.png"),
     "トーク表示サイズでの見え方（再現図）"),
    (r"失敗例と成功例を並べた比較画像",
     (DIR_FIG, "fig_outline.png"),
     "白フチのあり・なし（暗い背景で比較）"),
    (r"キャラクターがブレてしまった失敗例|髪の長さと肌の色が変わっている",
     (DIR_FIG, "fig_headcount.png"),
     "頭身を変えた比較（3頭身と6頭身。右は実際のトーク表示に近いサイズ）"),
    (r"生成した4枚を並べた比較画像|同じ設定で生成した画像を並べた",
     (DIR_FIG, "fig_stamp_sheet.png"),
     "並べて統一感を確認する（髪型・服装・線の太さがそろっているか）"),
    (r"完成した40枚を一覧|40枚を1画面に並べた|40枚をフォルダで一覧",
     (DIR_FIG, "fig_stamp_sheet.png"),
     "並べて確認する（サンプルは5枚）"),
    (r"加工前と加工後の比較",
     (DIR_FIG, "fig_transparency.png"),
     "加工前（背景あり）と加工後（透過・文字入り）"),
    (r"薄いグレー背景で生成した画像",
     (DIR_TRANS, "aina_base.png"),
     "薄いグレー背景で生成し、背景だけを透過した画像（白いTシャツが残っている）"),
    (r"生成した基準画像|基準画像（キャラクターの正面",
     (DIR_TRANS, "aina_base.png"),
     "基準画像（正面・上半身・にっこり）。以降の生成で参照用に使う"),
    (r"ノートパソコンの画面に読めない文字",
     (DIR_STAMPS, "stamp_002.png"),
     "小物は無地にし、画面には何も表示しないよう指定する（作例）"),
    (r"小物（ノートパソコン・スマートフォン）を拡大",
     (DIR_STAMPS, "stamp_002.png"),
     "小物を拡大して、文字やロゴが入っていないことを確認する（作例）"),
    (r"9分割グリッド",
     (DIR_FIG, "fig_stamp_sheet.png"),
     "複数ポーズを並べて、顔がそろっているか確認する"),
    (r"文字が小さい|文字数",
     (DIR_FIG, "fig_textlength.png"),
     "文字数と可読性（4文字／10文字／15文字）"),
    (r"余白",
     (DIR_FIG, "fig_margin.png"),
     "余白10pxのあり・なし（赤枠が公式の推奨余白の位置）"),
]

# ============================================================


def setup_console():
    """Windowsのコンソールで日本語が文字化けしないようにします。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def read_text(path):
    """ファイルをUTF-8で読み込みます。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def find_chapters():
    """章ファイルを番号順に集めます。"""
    pat = re.compile(r"^(\d{2})_.+\.md$")
    out = []
    for name in os.listdir(DIR_MS):
        if name == "full_manuscript.md":
            continue
        m = pat.match(name)
        if m:
            out.append((int(m.group(1)), name))
    out.sort()
    return out


def parse_shot_block(body):
    """
    【スクリーンショット挿入】ブロックの中身を、項目ごとに分解します。

    戻り値:
        {"画面": "...", "撮影内容": "...", "注意": "...", "取得済み": "..."}
    """
    info = {}
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(画面|撮影内容|注意)[：:]\s*(.*)$", line)
        if m:
            info[m.group(1)] = m.group(2).strip()
        elif "【スクリーンショット挿入】" in line:
            # 「※ 取得済み → パス」の注記が同じ行にある場合を拾う
            m2 = re.search(r"取得済み\s*→\s*(\S+)", line)
            if m2:
                info["取得済み"] = m2.group(1)
    return info


def pick_image(info):
    """
    撮影指示から、割り当てる画像を決めます。

    戻り値:
        (画像の絶対パス, キャプション) / 見つからない場合は (None, None)
    """
    screen = info.get("画面", "")
    for pattern, (folder, fname), caption in IMAGE_MAP:
        if re.search(pattern, screen):
            path = os.path.join(folder, fname)
            if os.path.exists(path):
                return path, caption
    return None, None


def copy_image(src):
    """
    画像を site/read/img/ へコピーし、HTMLから参照するパスを返します。

    同名ファイルが別フォルダにある場合に衝突しないよう、
    親フォルダ名を接頭辞に付けます。
    """
    parent = os.path.basename(os.path.dirname(src))
    name = "{}_{}".format(parent, os.path.basename(src))
    dst = os.path.join(DIR_IMG, name)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
    return "img/" + name


def build_figure_html(info, fig_no):
    """
    撮影指示から、挿絵のHTMLを組み立てます。

    画像がある場合は <figure>、ない場合は撮影指示の枠を返します。

    引数の fig_no は「画像を配置した図」だけの連番です。
    （未撮影の枠は番号を持ちません）
    """
    src, caption = pick_image(info)

    if src:
        rel = copy_image(src)
        return (
            '<figure class="shot">\n'
            '  <img src="{src}" alt="{alt}" loading="lazy">\n'
            '  <figcaption><span class="fig-no">図{no}</span>{cap}</figcaption>\n'
            "</figure>".format(
                src=rel,
                alt=html.escape(info.get("画面", "スクリーンショット")),
                no=fig_no,
                cap=html.escape(caption),
            )
        ), True

    # 画像がまだない場合は、撮影指示を枠で表示する
    rows = []
    for key in ("画面", "撮影内容", "注意"):
        if info.get(key):
            rows.append(
                '    <div class="ph-row"><span class="ph-key">{}</span>'
                '<span class="ph-val">{}</span></div>'.format(
                    key, html.escape(info[key])
                )
            )
    return (
        '<div class="placeholder">\n'
        '  <div class="ph-head">画像を入れる位置（未撮影）</div>\n'
        + "\n".join(rows)
        + "\n</div>"
    ), False


def replace_shot_blocks(md, stats):
    """
    原稿の【スクリーンショット挿入】ブロックを、挿絵のHTMLに置き換えます。

    Markdownに変換する前に処理し、目印を埋めておきます。
    （Markdown変換でHTMLが壊れないようにするため）
    """
    pattern = re.compile(
        r"```text\s*\n(【スクリーンショット挿入】.*?)\n```", re.DOTALL
    )

    holders = []

    def repl(m):
        info = parse_shot_block(m.group(1))
        stats["total"] += 1
        # 図番号は「画像を配置したもの」だけで数える
        next_no = stats["with_image"] + 1
        block, has_img = build_figure_html(info, next_no)
        if has_img:
            stats["with_image"] += 1
        key = "@@FIGURE{}@@".format(len(holders))
        holders.append(block)
        # 前後に空行を入れて、段落として扱われるようにする
        return "\n\n" + key + "\n\n"

    md = pattern.sub(repl, md)
    return md, holders


def md_to_html(md):
    """MarkdownをHTMLに変換します。"""
    import markdown

    return markdown.markdown(
        md,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )


def restore_figures(html_text, holders):
    """目印を、挿絵のHTMLに戻します。"""
    for i, block in enumerate(holders):
        key = "@@FIGURE{}@@".format(i)
        # <p>@@FIGURE0@@</p> の形になっているので、pタグごと置き換える
        html_text = html_text.replace("<p>{}</p>".format(key), block)
        html_text = html_text.replace(key, block)
    return html_text


def fix_checkboxes(html_text):
    """
    「- [ ]」のリストを、チェックボックス風の見た目にします。

    markdownライブラリは [ ] をそのまま文字として出力するため、
    ここで置き換えます。
    """
    html_text = html_text.replace("<li>[ ] ", '<li class="cb">')
    html_text = html_text.replace("<li>[x] ", '<li class="cb done">')
    html_text = html_text.replace("<li>[X] ", '<li class="cb done">')
    return html_text


def count_chars(md):
    """空白・改行を除いた文字数を数えます。"""
    return len(re.sub(r"\s", "", md))


# ============================================================
# HTMLのひな型
# ============================================================

CSS = """
:root{
  --bg:#fff; --fg:#1b1f24; --sub:#5b6672; --line:#e4e8ec; --card:#f7f9fb;
  --accent:#FF4FA3; --accent-d:#c2266f; --code:#f2f4f7; --codefg:#243447;
  --ok:#1B6B33; --ok-bg:#E7F5EB; --ng:#B00020; --ng-bg:#FDEBEC;
  --ph:#8a94a0; --ph-bg:#f4f6f8;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0f1419; --fg:#e3e7ea; --sub:#98a3ae; --line:#242c35; --card:#161c23;
    --accent:#FF6FB5; --accent-d:#ff9ccd; --code:#141a21; --codefg:#cdd7e2;
    --ok:#7ee2a0; --ok-bg:#12291c; --ng:#ff9a9a; --ng-bg:#2d1418;
    --ph:#7d8794; --ph-bg:#151b22;
  }
}
:root[data-theme="dark"]{
  --bg:#0f1419; --fg:#e3e7ea; --sub:#98a3ae; --line:#242c35; --card:#161c23;
  --accent:#FF6FB5; --accent-d:#ff9ccd; --code:#141a21; --codefg:#cdd7e2;
  --ok:#7ee2a0; --ok-bg:#12291c; --ng:#ff9a9a; --ng-bg:#2d1418;
  --ph:#7d8794; --ph-bg:#151b22;
}
:root[data-theme="light"]{
  --bg:#fff; --fg:#1b1f24; --sub:#5b6672; --line:#e4e8ec; --card:#f7f9fb;
  --accent:#FF4FA3; --accent-d:#c2266f; --code:#f2f4f7; --codefg:#243447;
  --ok:#1B6B33; --ok-bg:#E7F5EB; --ng:#B00020; --ng-bg:#FDEBEC;
  --ph:#8a94a0; --ph-bg:#f4f6f8;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth; scroll-padding-top:70px}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font:17px/1.9 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN",
    "Yu Gothic","Meiryo",sans-serif;
  -webkit-text-size-adjust:100%; word-break:break-word;
}
.progress{position:fixed; top:0; left:0; height:3px; background:var(--accent);
  width:0; z-index:60; transition:width .1s}
.topbar{
  position:sticky; top:0; z-index:50; background:var(--bg);
  border-bottom:1px solid var(--line); backdrop-filter:blur(8px);
}
.topbar .inner{
  max-width:1180px; margin:0 auto; padding:10px 20px;
  display:flex; align-items:center; gap:14px;
}
.topbar .bt{font-size:14px; font-weight:700; flex:1; min-width:0;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.topbar a{color:var(--accent-d); text-decoration:none; font-size:13px; font-weight:600}
.btn{
  font:600 13px/1 inherit; padding:8px 13px; border-radius:8px; cursor:pointer;
  border:1px solid var(--line); background:var(--bg); color:var(--fg);
  text-decoration:none; display:inline-flex; align-items:center; gap:6px;
}
.btn:hover{border-color:var(--accent); color:var(--accent-d)}
.btn.primary{background:var(--accent); border-color:var(--accent); color:#fff}

.hero{
  background:linear-gradient(135deg,#FF4FA3 0%,#E8C468 100%);
  color:#fff; padding:52px 20px 46px; text-align:center;
}
.hero h1{margin:0 0 12px; font-size:clamp(21px,4.2vw,32px); line-height:1.45}
.hero p{margin:0; opacity:.95; font-size:14px}
.hero .meta{
  display:inline-flex; gap:10px; flex-wrap:wrap; justify-content:center;
  margin-top:18px; font-size:13px;
}
.hero .meta span{
  background:rgba(255,255,255,.22); padding:5px 12px; border-radius:999px;
}

.layout{max-width:1180px; margin:0 auto; padding:0 20px; display:flex; gap:36px}
.toc{
  width:250px; flex:none; position:sticky; top:62px; align-self:flex-start;
  max-height:calc(100vh - 80px); overflow-y:auto; padding:24px 0 40px;
  font-size:14px;
}
.toc h2{font-size:13px; color:var(--sub); margin:0 0 10px; letter-spacing:.04em}
.toc ol{list-style:none; margin:0; padding:0; counter-reset:c}
.toc li{margin:0}
.toc a{
  display:block; padding:7px 10px; border-radius:7px; text-decoration:none;
  color:var(--sub); line-height:1.5;
}
.toc a:hover{background:var(--card); color:var(--fg)}
.toc a.on{background:var(--card); color:var(--accent-d); font-weight:700}
.toc .cc{font-size:11px; opacity:.7; margin-left:6px}
main{flex:1; min-width:0; padding:24px 0 80px; max-width:820px}
@media (max-width:1000px){
  .layout{display:block}
  .toc{width:auto; position:static; max-height:none; padding:20px 0;
    border-bottom:1px solid var(--line)}
  main{padding-top:20px}
}

.warnbox{
  background:var(--ng-bg); color:var(--ng); border-radius:12px;
  padding:16px 18px; margin:24px 0; font-size:14px; line-height:1.75;
}
.warnbox b{display:block; margin-bottom:4px}

article{border-top:1px solid var(--line); padding-top:8px; margin-top:56px}
article:first-of-type{border-top:0; margin-top:0}
h1{font-size:clamp(22px,3.6vw,29px); line-height:1.4; margin:32px 0 6px}
h2{font-size:clamp(18px,2.8vw,22px); margin:44px 0 12px; padding-bottom:8px;
  border-bottom:2px solid var(--line)}
h3{font-size:17px; margin:32px 0 10px; color:var(--accent-d)}
h4{font-size:16px; margin:24px 0 8px}
p{margin:0 0 1.1em}
hr{border:0; border-top:1px solid var(--line); margin:36px 0}
ul,ol{padding-left:1.5em; margin:0 0 1.1em}
li{margin:.3em 0}
li.cb{list-style:none; margin-left:-1.5em; padding-left:1.9em; position:relative}
li.cb::before{
  content:""; position:absolute; left:0; top:.42em; width:15px; height:15px;
  border:2px solid var(--sub); border-radius:4px;
}
li.cb.done::before{background:var(--ok); border-color:var(--ok)}
strong{font-weight:700}
blockquote{
  margin:20px 0; padding:12px 18px; border-left:4px solid var(--accent);
  background:var(--card); border-radius:0 10px 10px 0; color:var(--sub);
}
blockquote p:last-child{margin:0}
code{
  background:var(--code); padding:2px 6px; border-radius:5px;
  font:.88em/1.6 "Consolas","Menlo","MS Gothic",monospace;
}
pre{
  background:var(--code); color:var(--codefg); padding:16px 18px;
  border-radius:10px; overflow-x:auto; margin:20px 0;
  font:13px/1.7 "Consolas","Menlo","MS Gothic",monospace;
}
pre code{background:none; padding:0; font-size:inherit}
.tablewrap{overflow-x:auto; margin:22px 0}
table{border-collapse:collapse; width:100%; font-size:14.5px}
th,td{border:1px solid var(--line); padding:9px 12px; text-align:left;
  vertical-align:top}
th{background:var(--card); font-weight:700}

figure.shot{margin:28px 0; text-align:center}
figure.shot img{
  max-width:100%; height:auto; border:1px solid var(--line);
  border-radius:10px; background:var(--card);
}
figure.shot figcaption{
  margin-top:10px; font-size:13px; color:var(--sub); line-height:1.7;
  text-align:left;
}
.fig-no{
  display:inline-block; background:var(--accent); color:#fff; font-weight:700;
  padding:2px 8px; border-radius:5px; margin-right:8px; font-size:12px;
}
.placeholder{
  border:2px dashed var(--line); border-radius:12px; background:var(--ph-bg);
  padding:16px 18px; margin:26px 0; font-size:13.5px; color:var(--ph);
}
.ph-head{font-weight:700; margin-bottom:8px; color:var(--sub)}
.ph-row{display:flex; gap:10px; margin:4px 0}
.ph-key{
  flex:none; width:70px; font-weight:700; color:var(--sub);
}
.ph-val{flex:1}
.chapmeta{
  display:inline-block; background:var(--card); color:var(--sub);
  padding:4px 12px; border-radius:999px; font-size:13px; margin-bottom:6px;
}
.theme-btn{
  position:fixed; right:16px; bottom:16px; z-index:55; width:44px; height:44px;
  border-radius:50%; display:grid; place-items:center; font-size:19px; padding:0;
  background:var(--bg); border:1px solid var(--line); cursor:pointer;
  box-shadow:0 2px 12px rgba(0,0,0,.14);
}
.totop{
  position:fixed; right:16px; bottom:70px; z-index:55; width:44px; height:44px;
  border-radius:50%; display:grid; place-items:center; font-size:17px; padding:0;
  background:var(--bg); border:1px solid var(--line); cursor:pointer;
  box-shadow:0 2px 12px rgba(0,0,0,.14); opacity:0; pointer-events:none;
  transition:opacity .2s;
}
.totop.show{opacity:1; pointer-events:auto}
footer{
  border-top:1px solid var(--line); padding:34px 20px 70px;
  text-align:center; color:var(--sub); font-size:14px;
}
footer a{color:var(--accent-d)}
.toast{
  position:fixed; left:50%; bottom:26px; transform:translate(-50%,20px);
  background:var(--fg); color:var(--bg); padding:11px 20px; border-radius:999px;
  font-size:14px; font-weight:600; opacity:0; pointer-events:none;
  transition:opacity .2s, transform .2s; z-index:70;
}
.toast.show{opacity:1; transform:translate(-50%,0)}
@media print{
  .topbar,.toc,.theme-btn,.totop,.progress,.hero .meta{display:none}
  body{font-size:11pt}
  article{page-break-before:always}
  article:first-of-type{page-break-before:avoid}
}
"""

JS = """
(function(){
  // 読み進み具合のバー
  var bar = document.querySelector('.progress');
  var top = document.querySelector('.totop');
  function onScroll(){
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var p = max > 0 ? (h.scrollTop / max) * 100 : 0;
    if(bar) bar.style.width = p + '%';
    if(top) top.classList.toggle('show', h.scrollTop > 700);
  }
  document.addEventListener('scroll', onScroll, {passive:true});
  onScroll();

  if(top) top.addEventListener('click', function(){
    window.scrollTo({top:0, behavior:'smooth'});
  });

  // 目次の現在位置を光らせる
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  var targets = links.map(function(a){
    return document.getElementById(a.getAttribute('href').slice(1));
  });
  if('IntersectionObserver' in window){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(!e.isIntersecting) return;
        var i = targets.indexOf(e.target);
        if(i < 0) return;
        links.forEach(function(a){ a.classList.remove('on'); });
        links[i].classList.add('on');
      });
    }, {rootMargin:'-70px 0px -70% 0px'});
    targets.forEach(function(t){ if(t) io.observe(t); });
  }

  // テーマ切り替え
  var root = document.documentElement;
  var tb = document.querySelector('.theme-btn');
  if(tb) tb.addEventListener('click', function(){
    var cur = root.getAttribute('data-theme');
    if(!cur){
      cur = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light';
    }
    root.setAttribute('data-theme', cur === 'dark' ? 'light':'dark');
  });

  // 本文だけを選択する（noteへ貼り付ける用）
  var toast = document.getElementById('toast');
  var tt = null;
  function showToast(msg){
    if(!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(tt);
    tt = setTimeout(function(){ toast.classList.remove('show'); }, 2400);
  }
  var sel = document.getElementById('selectBody');
  if(sel) sel.addEventListener('click', function(){
    var body = document.getElementById('body');
    if(!body) return;
    var r = document.createRange();
    r.selectNodeContents(body);
    var s = window.getSelection();
    s.removeAllRanges();
    s.addRange(r);
    showToast('本文を選択しました。Ctrl+C（Macは Cmd+C）でコピーできます');
  });
})();
"""


def page_shell(title, body, is_index, chapters_nav=""):
    """HTMLページ全体を組み立てます。"""
    return """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="robots" content="noindex">
<style>{css}</style>
</head>
<body>
<div class="progress"></div>
{body}
<button class="theme-btn" title="表示テーマを切り替え" aria-label="表示テーマを切り替え">◐</button>
<button class="totop" title="先頭へ戻る" aria-label="先頭へ戻る">↑</button>
<div class="toast" id="toast"></div>
<script>{js}</script>
</body>
</html>
""".format(title=html.escape(title), css=CSS, js=JS, body=body)


def wrap_tables(html_text):
    """表を横スクロールできる箱に入れます（スマートフォン対策）。"""
    return html_text.replace("<table>", '<div class="tablewrap"><table>').replace(
        "</table>", "</table></div>"
    )


def main():
    setup_console()

    parser = argparse.ArgumentParser(
        description="原稿を挿絵つきHTMLに変換して通読用サイトを作ります。"
    )
    parser.add_argument("--out", default=DIR_OUT, help="出力先")
    args = parser.parse_args()

    out_dir = args.out
    img_dir = os.path.join(out_dir, "img")

    print("=" * LINE_WIDTH)
    print(" 通読用サイトの生成")
    print("=" * LINE_WIDTH)

    try:
        import markdown  # noqa: F401
    except ImportError:
        print("エラー: markdown ライブラリがインストールされていません。")
        print("  Windows : python -m pip install markdown")
        print("  macOS   : python3 -m pip install markdown")
        return 1

    if not os.path.isdir(DIR_MS):
        print("エラー: 原稿フォルダがありません: {}".format(DIR_MS))
        return 1

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    # グローバル変数を差し替える（copy_image が参照するため）
    global DIR_IMG
    DIR_IMG = img_dir

    chapters = find_chapters()
    if not chapters:
        print("エラー: 章ファイルが見つかりません。")
        return 1

    print()
    print("[1] 章の変換")
    print()

    stats = {"total": 0, "with_image": 0}
    parts = []
    toc_items = []
    total_chars = 0

    for num, name in chapters:
        md = read_text(os.path.join(DIR_MS, name))
        chars = count_chars(md)
        total_chars += chars

        # 章タイトルを取り出す
        m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
        title = m.group(1).strip() if m else name

        before = stats["total"]
        md2, holders = replace_shot_blocks(md, stats)
        body = md_to_html(md2)
        body = restore_figures(body, holders)
        body = fix_checkboxes(body)
        body = wrap_tables(body)

        figs = stats["total"] - before
        cid = "ch{:02d}".format(num)
        toc_items.append((cid, title, chars))

        parts.append(
            '<article id="{cid}">\n'
            '<div class="chapmeta">{chars:,} 文字 ／ 図 {figs} 箇所</div>\n'
            "{body}\n</article>".format(cid=cid, chars=chars, figs=figs, body=body)
        )

        print("  {:<34} {:>7,} 文字  図{:>3}箇所".format(name, chars, figs))

    print()
    print("[2] 挿絵の割り当て")
    print()
    print("  挿入位置        : {} 箇所".format(stats["total"]))
    print("  画像を配置      : {} 箇所".format(stats["with_image"]))
    print(
        "  撮影指示の枠    : {} 箇所（未撮影）".format(
            stats["total"] - stats["with_image"]
        )
    )
    print("  使用した画像    : {} 枚".format(len(os.listdir(img_dir))))

    # ---- 通読版（1ページ） ----
    toc_html = ['<nav class="toc"><h2>目次</h2><ol>']
    for cid, title, chars in toc_items:
        toc_html.append(
            '<li><a href="#{cid}">{t}<span class="cc">{c:,}字</span></a></li>'.format(
                cid=cid, t=html.escape(title), c=chars
            )
        )
    toc_html.append("</ol></nav>")

    hero = """
<header class="hero">
  <h1>{title}</h1>
  <p>{sub}</p>
  <div class="meta">
    <span>全14章</span><span>{chars:,} 文字</span>
    <span>図 {shots} 箇所（{withimg} 箇所は画像あり）</span>
  </div>
</header>
""".format(
        title=html.escape(BOOK_TITLE),
        sub=html.escape(BOOK_SUB),
        chars=total_chars,
        shots=stats["total"],
        withimg=stats["with_image"],
    )

    warn = """
<div class="warnbox">
  <b>先に読んでください</b>
  LINE Creators Marketの仕様（画像サイズ・枚数・文字数・価格・分配金・AI利用ルール）は
  変更される可能性があります。本文中の数値は<strong>2026年7月30日時点で公式ガイドラインに
  記載されていた内容</strong>です。申請前に必ず
  <a href="https://creator.line.me/ja/guideline/sticker/" target="_blank"
     rel="noopener">公式ガイドライン</a>で最新の仕様を確認してください。
</div>
"""

    topbar = """
<div class="topbar"><div class="inner">
  <span class="bt">通読版 ／ 全14章 {chars:,}文字</span>
  <a href="chapters.html">章ごとに読む</a>
  <a href="../note/">note貼り付け用</a>
  <a href="../">素材ページ</a>
</div></div>
""".format(chars=total_chars)

    footer = """
<footer>
  <p>{title}</p>
  <p style="margin-top:14px">
    原稿・プロンプト集・テンプレート・スクリプト：
    <a href="https://github.com/shimanto/line-stamp-note" target="_blank"
       rel="noopener">github.com/shimanto/line-stamp-note</a>
  </p>
  <p style="margin-top:14px; font-size:13px">
    キャラクター「アイナ」は実在の人物・既存キャラクターに似せていない架空キャラクターです。<br>
    画像は Codex ImageGen で生成し、ImageMagick で加工しています。<br>
    公開ページのスクリーンショットは出典URLをキャプションに併記しています。
  </p>
</footer>
""".format(title=html.escape(BOOK_TITLE))

    index_body = (
        topbar
        + hero
        + '<div class="layout">'
        + "".join(toc_html)
        + '<main id="body">'
        + warn
        + "\n".join(parts)
        + "</main></div>"
        + footer
    )

    index_path = os.path.join(out_dir, "index.html")
    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page_shell(BOOK_TITLE + "｜通読版", index_body, True))

    # ---- 章ごとのページ（noteへ貼り付ける用） ----
    print()
    print("[3] 章ごとのページ")
    print()

    for i, ((num, name), (cid, title, chars)) in enumerate(zip(chapters, toc_items)):
        md = read_text(os.path.join(DIR_MS, name))
        s2 = {"total": 0, "with_image": 0}
        md2, holders = replace_shot_blocks(md, s2)
        body = md_to_html(md2)
        body = restore_figures(body, holders)
        body = fix_checkboxes(body)
        body = wrap_tables(body)

        prev_link = (
            '<a href="{}.html">← 前の章</a>'.format(toc_items[i - 1][0])
            if i > 0
            else ""
        )
        next_link = (
            '<a href="{}.html">次の章 →</a>'.format(toc_items[i + 1][0])
            if i < len(toc_items) - 1
            else ""
        )

        bar = """
<div class="topbar"><div class="inner">
  <span class="bt">{title}（{chars:,}文字）</span>
  <button class="btn primary" id="selectBody">本文を選択</button>
  <a href="chapters.html">章一覧</a>
  {prev}{next}
</div></div>
""".format(
            title=html.escape(title), chars=chars, prev=prev_link, next=next_link
        )

        note = """
<div class="warnbox" style="background:var(--card); color:var(--sub)">
  <b>noteへ貼り付ける場合</b>
  上の「本文を選択」を押してから Ctrl+C（Macは Cmd+C）でコピーし、
  noteの編集画面に貼り付けてください。見出し・太字・箇条書き・表は書式が保たれます。
  <strong>画像はnote側で個別にアップロードが必要になる可能性があります</strong>ので、
  まず1章だけで試してから残りを進めてください。
</div>
"""

        page_body = (
            bar
            + '<div class="layout"><main id="body" style="max-width:820px;margin:0 auto">'
            + note
            + '<article id="{}">'.format(cid)
            + body
            + "</article>"
            + '<p style="margin-top:40px">{} {}</p>'.format(prev_link, next_link)
            + "</main></div>"
        )

        with open(
            os.path.join(out_dir, cid + ".html"), "w", encoding="utf-8", newline="\n"
        ) as f:
            f.write(page_shell(title, page_body, False))

        print("  {}.html  {:<28} {:>7,} 文字".format(cid, title[:26], chars))

    # ---- 章一覧ページ ----
    rows = []
    for cid, title, chars in toc_items:
        rows.append(
            "<tr><td><a href=\"{cid}.html\">{t}</a></td>"
            '<td style="white-space:nowrap">{c:,} 文字</td></tr>'.format(
                cid=cid, t=html.escape(title), c=chars
            )
        )
    chapters_body = """
<div class="topbar"><div class="inner">
  <span class="bt">章一覧</span>
  <a href="index.html">通読版（1ページ）</a>
  <a href="../">素材ページ</a>
</div></div>
<div class="layout"><main style="max-width:820px;margin:0 auto">
<h1>章ごとに読む</h1>
<p>noteへ貼り付ける場合は、章ごとのページを使ってください。<br>
1記事にまとめる場合は<a href="index.html">通読版</a>から選択してコピーします。</p>
<div class="tablewrap"><table>
<tr><th>章</th><th>文字数</th></tr>
{rows}
<tr><th>合計</th><th>{total:,} 文字</th></tr>
</table></div>
</main></div>
""".format(rows="\n".join(rows), total=total_chars)

    with open(
        os.path.join(out_dir, "chapters.html"), "w", encoding="utf-8", newline="\n"
    ) as f:
        f.write(page_shell("章一覧", chapters_body, False))

    print()
    print("=" * LINE_WIDTH)
    print(" 完了")
    print("=" * LINE_WIDTH)
    print()
    print("出力先: {}".format(out_dir))
    print("  index.html      通読版（全14章・{:,}文字）".format(total_chars))
    print("  chapters.html   章一覧")
    print("  ch00〜ch13.html 章ごとのページ")
    print("  img/            挿絵 {} 枚".format(len(os.listdir(img_dir))))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
