#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_note_version.py

原稿を「note に貼り付けたときに読みやすい形」へ整形します。

【このスクリプトは教材の保守用です】

【なぜ必要か】

原稿はGitHubで読む前提のMarkdownです。
そのままnoteへ貼ると、次の3点が崩れます。

  1. チェックボックス（- [ ]）
     noteにはチェックボックスがないため「[ ]」が文字として残る
     → 「□」に置き換える

  2. 表
     noteの編集画面には表を作る機能がありません。
     貼り付けた表は平文に潰れ、項目の対応関係が読めなくなります。
     （実機で確認済み）
     → すべての表を箇条書きに開く

  3. 長いコードブロック
     noteでは折りたためないため、本文が分断されて読み進めにくい
     → 何行あるかを先に書いて、読み飛ばす判断をできるようにする

そのほか、noteの見出しは3段階（大・中・小）しかないため、
4段目以降（####）は太字の段落にします。

また、noteは1記事5,000〜8,000字くらいが読み切りやすいサイズです。
9,000字を超える章は、意味の切れ目で前後編に分けます（SPLITS の設定）。
14章 → 19記事になります。

【出力】
    site/note/ch00.html 〜 ch13.html   記事ごとの貼り付け用ページ
      （分割した章は ch05a / ch05b のように a・b が付きます）
    site/note/index.html              使い方と記事一覧

使い方:
    python  scripts/build_note_version.py      # Windows
    python3 scripts/build_note_version.py      # macOS

外部APIは使用しません。
"""

import os
import re
import sys
import html
import argparse

# ============================================================
# 設定
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR_MS = os.path.join(ROOT, "manuscript")
DIR_OUT = os.path.join(ROOT, "site", "note")

# 画像はnoteから参照できるよう、公開URLの絶対パスにする
IMAGE_BASE = "https://line-stamp-note.pages.dev/read/"

# 表を箇条書きに開く列数のしきい値
#
# noteには表を作る機能がありません。
# 表を貼り付けると平文に潰れ、項目の対応関係が読めなくなります。
# そのため、2列の表も含めてすべて開きます（= 2）。
TABLE_OPEN_COLS = 2

# 「長い」と判断するコードブロックの行数
LONG_BLOCK_LINES = 20

# ============================================================
# 章の分割
#
# noteは1記事5,000〜8,000字くらいが読み切りやすいサイズです。
# 9,000字を超える章を、意味の切れ目で前後編に分けます。
#
# 形式:
#   章番号: (分割する見出し, 前編の副題, 後編の副題)
#
# 分割する見出しは、その章の「##」の行と完全に一致させてください。
# 見つからない場合は分割せず、そのまま1記事にします。
# ============================================================

SPLITS = {
    5: ("## そのまま使えるプロンプト（10種）",
        "プロンプトの型とキャラクターの固定",
        "生成プロンプト10種と修正プロンプト"),
    6: ("## ⑤ 文字入れ",
        "切り抜き・余白・リサイズ",
        "文字入れ・白フチ・メイン画像とタブ画像"),
    7: ("## そのまま使えるタイトル案10個",
        "登録から審査申請までの手順",
        "タイトル案10個と日英の説明文"),
    9: ("## そのまま使える投稿文",
        "何を見せるかと媒体の使い分け",
        "媒体別の投稿文12案"),
    11: ("## 自動化4　画像の検証（最重要）",
         "環境の準備とファイル整理",
         "画像の検証と原稿の自動生成"),
}

BOOK_TITLE = "【2026年最新版】生成AIでLINEスタンプを作って販売する完全ガイド"

LINE_WIDTH = 60


def setup_console():
    """Windowsのコンソールで日本語が文字化けしないようにします。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def read_text(path):
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
    return sorted(out)


def split_fences(md):
    """
    本文をコードブロックとそれ以外に分けます。

    コードブロックの中身は加工してはいけないため、
    処理の対象から外すのに使います。

    戻り値:
        [(種別, テキスト), ...]   種別は "text" か "code"
    """
    parts = []
    buf = []
    in_code = False
    fence = ""

    for line in md.split("\n"):
        if not in_code and line.strip().startswith("```"):
            if buf:
                parts.append(("text", "\n".join(buf)))
                buf = []
            in_code = True
            fence = line
            buf.append(line)
            continue
        if in_code and line.strip().startswith("```"):
            buf.append(line)
            parts.append(("code", "\n".join(buf)))
            buf = []
            in_code = False
            continue
        buf.append(line)

    if buf:
        parts.append(("code" if in_code else "text", "\n".join(buf)))
    return parts


# ============================================================
# 1. チェックボックス
# ============================================================

def convert_checkboxes(text):
    """
    「- [ ]」を「- □」に置き換えます。

    noteにはチェックボックスの機能がないため、
    そのままだと「[ ]」という文字がそのまま出てしまいます。
    """
    text = re.sub(r"^(\s*)- \[ \] ", r"\1- □ ", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)- \[[xX]\] ", r"\1- ■ ", text, flags=re.MULTILINE)
    return text


# ============================================================
# 2. 表を開く
# ============================================================

def parse_table(lines):
    """
    Markdownの表を、ヘッダーと行に分解します。

    戻り値:
        (ヘッダーのリスト, 行のリスト) / 表でなければ None
    """
    if len(lines) < 2:
        return None
    if not re.match(r"^\s*\|", lines[0]):
        return None
    if not re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[1]):
        return None

    def cells(l):
        l = l.strip()
        if l.startswith("|"):
            l = l[1:]
        if l.endswith("|"):
            l = l[:-1]
        return [c.strip() for c in l.split("|")]

    header = cells(lines[0])
    rows = [cells(l) for l in lines[2:] if l.strip().startswith("|")]
    return header, rows


def open_table(header, rows):
    """
    表を「箇条書き」に開きます。

    noteには表を作る機能がなく、貼り付けた表は平文に潰れます。
    潰れると項目の対応関係が読み取れなくなるため、
    こちらで先に箇条書きへ開いておきます。

    2列の場合（定義リストとして開く）:
        | 項目 | 内容 |
        | 頭身 | 2〜3頭身 |
        ↓
        - **頭身**：2〜3頭身

    3列以上の場合（見出し＋箇条書きとして開く）:
        | No | 作品名 | 種類 | 使う人 |
        | 1  | アイナ | スタンプ | 社会人 |
        ↓
        **1　アイナ**
        - 種類：スタンプ
        - 使う人：社会人
    """
    out = []
    skip = ("", "ー", "-", "—", "－")

    # --- 2列の表は、そのまま定義リストにする ---
    if len(header) <= 2:
        for row in rows:
            if not any(c for c in row):
                continue
            left = row[0] if len(row) > 0 else ""
            right = row[1] if len(row) > 1 else ""
            if left in skip and right in skip:
                continue
            if right in skip:
                out.append("- **{}**".format(left))
            elif left in skip:
                out.append("- {}".format(right))
            else:
                out.append("- **{}**：{}".format(left, right))
        out.append("")
        return "\n".join(out)

    # --- 3列以上は、1列目を見出しにして開く ---
    for row in rows:
        if not any(c for c in row):
            continue
        title_parts = [c for c in row[:2] if c not in skip]
        title = "　".join(title_parts) if title_parts else "（項目）"
        out.append("**{}**".format(title))
        out.append("")
        for i in range(2, len(row)):
            key = header[i] if i < len(header) else ""
            val = row[i]
            if val in skip:
                continue
            if key and key not in skip:
                out.append("- {}：{}".format(key, val))
            else:
                out.append("- {}".format(val))
        out.append("")
    return "\n".join(out)


def convert_tables(text, stats):
    """列数の多い表を開きます。3列以下はそのまま残します。"""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if re.match(r"^\s*\|", lines[i]):
            # 表の範囲を取る
            j = i
            while j < len(lines) and re.match(r"^\s*\|", lines[j]):
                j += 1
            block = lines[i:j]
            parsed = parse_table(block)
            if parsed:
                header, rows = parsed
                stats["tables"] += 1
                if len(header) >= TABLE_OPEN_COLS:
                    stats["tables_opened"] += 1
                    out.append(open_table(header, rows))
                    i = j
                    continue
            out.extend(block)
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


# ============================================================
# 3. 長いコードブロックに目印を付ける
# ============================================================

def label_code_blocks(parts, stats):
    """
    長いコードブロックの前に、行数と用途の見出しを入れます。

    noteでは折りたためないため、
    「ここから何行あるか」が先にわかると読み進めやすくなります。
    """
    out = []
    for kind, text in parts:
        if kind != "code":
            out.append((kind, text))
            continue

        body = text.split("\n")
        inner = len(body) - 2  # 前後のフェンス行を除く
        stats["blocks"] += 1

        if inner >= LONG_BLOCK_LINES:
            stats["blocks_labeled"] += 1
            # 中身からプロンプトかどうかを推測する
            if "【" in text and "】" in text:
                label = "▼ ここからコピーして使えます（{}行）".format(inner)
            else:
                label = "▼ 以下 {}行".format(inner)
            out.append(("text", "\n**{}**\n".format(label)))
            out.append((kind, text))
            # 終わりにも目印を置く。
            # noteでは折りたためないため、
            # 「どこまで読み飛ばせばよいか」がわかるようにする。
            out.append(("text", "\n**▲ ここまで**\n"))
            continue

        out.append((kind, text))
    return out


# ============================================================
# 4. 見出しの調整
# ============================================================

def adjust_headings(text):
    """
    noteの見出しは3段階しかありません。

    4段目以降（####）は、太字の段落に変えます。
    """
    def repl(m):
        return "**{}**".format(m.group(1).strip())

    return re.sub(r"^#{4,}\s+(.+)$", repl, text, flags=re.MULTILINE)


# ============================================================
# 5. 挿絵
# ============================================================

# build_reading_site.py と同じ対応表を使う
try:
    sys.path.insert(0, HERE)
    from build_reading_site import IMAGE_MAP, parse_shot_block  # noqa
    HAS_MAP = True
except Exception:
    HAS_MAP = False
    IMAGE_MAP = []


def convert_shots(text, stats):
    """
    【スクリーンショット挿入】ブロックを、画像またはメモに変えます。

    画像がある場合   → 公開URLの画像として挿入
    画像がない場合   → その位置を1行のメモにする（撮影指示は載せない）
                       読者に見せる原稿なので、指示書は残しません。
    """
    pattern = re.compile(
        r"```text\s*\n(【スクリーンショット挿入】.*?)\n```", re.DOTALL
    )

    def repl(m):
        stats["shots"] += 1
        if not HAS_MAP:
            return ""
        info = parse_shot_block(m.group(1))
        screen = info.get("画面", "")
        for pat, (folder, fname), caption in IMAGE_MAP:
            if re.search(pat, screen):
                parent = os.path.basename(folder)
                url = "{}img/{}_{}".format(IMAGE_BASE, parent, fname)
                stats["shots_with_image"] += 1
                return "\n![{cap}]({url})\n\n*{cap}*\n".format(
                    cap=caption.replace("*", ""), url=url
                )
        # 画像がない位置は、空にする（貼り付け原稿に指示書を残さない）
        stats["shots_removed"] += 1
        return ""

    return pattern.sub(repl, text)


# ============================================================
# 変換の本体
# ============================================================

def convert_chapter(md, stats):
    """1章ぶんを、note向けのMarkdownに整形します。"""
    # 画像ブロックの処理は、コードブロック分割より前に行う
    md = convert_shots(md, stats)

    parts = split_fences(md)
    parts = label_code_blocks(parts, stats)

    out = []
    for kind, text in parts:
        if kind == "code":
            out.append(text)
            continue
        text = convert_checkboxes(text)
        text = convert_tables(text, stats)
        text = adjust_headings(text)
        out.append(text)

    return "\n".join(out)


def split_chapter(md, num, title):
    """
    章を前後編に分けます。

    分割の対象でない章、または分割位置の見出しが見つからない場合は、
    1本のまま返します。

    戻り値:
        [(記事タイトル, 本文), ...]
    """
    if num not in SPLITS:
        return [(title, md)]

    heading, sub_a, sub_b = SPLITS[num]
    lines = md.split("\n")

    # 分割位置を探す（コードブロックの中は見ない）
    idx, in_code = None, False
    for i, l in enumerate(lines):
        if l.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code and l.strip() == heading:
            idx = i
            break

    if idx is None:
        print("    警告: 分割位置が見つかりません（{}）".format(heading))
        return [(title, md)]

    head = "\n".join(lines[:idx]).rstrip()
    tail = "\n".join(lines[idx:]).rstrip()

    # 章タイトル（先頭の # 行）を、後編にも付け直す
    m = re.match(r"^#\s+.+$", lines[0]) if lines else None
    h1 = lines[0] if m else "# " + title

    # 前編の末尾に、続きがあることを書く
    head += (
        "\n\n---\n\n"
        "**この章は前後編に分かれています。**\n\n"
        "続きは「{}（後編）{}」です。\n".format(title, sub_b)
    )

    # 後編の冒頭に、前編の続きであることを書く
    tail_body = (
        "{h1}（後編）\n\n"
        "**前編の続きです。**\n\n"
        "前編では「{a}」を扱いました。\n\n"
        "この後編では「{b}」を扱います。\n\n"
        "---\n\n"
        "{rest}"
    ).format(h1=h1, a=sub_a, b=sub_b, rest=tail)

    return [
        ("{}（前編）{}".format(title, sub_a), head),
        ("{}（後編）{}".format(title, sub_b), tail_body),
    ]


def md_to_html(md):
    import markdown

    return markdown.markdown(
        md,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )


# ============================================================
# ページのひな型
# ============================================================

CSS = """
:root{--bg:#fff;--fg:#1b1f24;--sub:#5b6672;--line:#e4e8ec;--card:#f7f9fb;
--accent:#FF4FA3;--accent-d:#c2266f;--code:#f4f6f8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:17px/1.95 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN",
"Yu Gothic","Meiryo",sans-serif}
.bar{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid var(--line);
padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.bar .t{font-size:14px;font-weight:700;flex:1;min-width:140px}
.btn{font:600 13px/1 inherit;padding:9px 14px;border-radius:8px;cursor:pointer;
border:1px solid var(--line);background:#fff;color:var(--fg);text-decoration:none;
display:inline-flex;align-items:center;gap:6px}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn:hover{border-color:var(--accent);color:var(--accent-d)}
.btn.primary:hover{color:#fff;opacity:.9}
.howto{max-width:760px;margin:20px auto;padding:0 16px;color:var(--sub);font-size:14px;
background:var(--card);border-radius:12px;padding:16px 18px}
.howto b{color:var(--fg)}
main{max-width:760px;margin:0 auto;padding:24px 16px 80px}
h1{font-size:26px;line-height:1.45;margin:28px 0 10px}
h2{font-size:21px;margin:40px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line)}
h3{font-size:18px;margin:30px 0 10px;color:var(--accent-d)}
p{margin:0 0 1.15em}
ul,ol{padding-left:1.45em;margin:0 0 1.15em}
li{margin:.32em 0}
hr{border:0;border-top:1px solid var(--line);margin:34px 0}
strong{font-weight:700}
blockquote{margin:20px 0;padding:12px 18px;border-left:4px solid var(--accent);
background:var(--card);border-radius:0 10px 10px 0;color:var(--sub)}
blockquote p:last-child{margin:0}
code{background:var(--code);padding:2px 6px;border-radius:5px;
font:.88em/1.6 "Consolas","Menlo","MS Gothic",monospace}
pre{background:var(--code);padding:15px 17px;border-radius:10px;overflow-x:auto;
margin:18px 0;font:13px/1.7 "Consolas","Menlo","MS Gothic",monospace}
pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;font-size:14.5px;margin:18px 0}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left}
th{background:var(--card);font-weight:700}
img{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--line);
display:block;margin:22px auto 6px}
em{display:block;text-align:center;font-size:13px;color:var(--sub);font-style:normal;
margin-bottom:20px}
.toast{position:fixed;left:50%;bottom:24px;transform:translate(-50%,20px);
background:var(--fg);color:#fff;padding:11px 20px;border-radius:999px;font-size:14px;
font-weight:600;opacity:0;pointer-events:none;transition:.2s;z-index:20}
.toast.show{opacity:1;transform:translate(-50%,0)}
"""

JS = """
(function(){
  var t=document.getElementById('toast'),tm=null;
  function toast(m){t.textContent=m;t.classList.add('show');clearTimeout(tm);
    tm=setTimeout(function(){t.classList.remove('show')},2600);}
  var b=document.getElementById('sel');
  if(b) b.addEventListener('click',function(){
    var body=document.getElementById('body');
    var r=document.createRange();r.selectNodeContents(body);
    var s=window.getSelection();s.removeAllRanges();s.addRange(r);
    try{document.execCommand('copy');
      toast('コピーしました。noteの編集画面に貼り付けてください');}
    catch(e){toast('選択しました。Ctrl+C（Macは Cmd+C）でコピーしてください');}
  });
})();
"""


def page(title, bar, body, howto=""):
    return """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title><meta name="robots" content="noindex">
<style>{css}</style></head><body>
{bar}
{howto}
<main id="body" data-title="{t}">{body}</main>
<div class="toast" id="toast"></div>
<script>{js}</script>
</body></html>""".format(t=html.escape(title), css=CSS, js=JS, bar=bar,
                         howto=howto, body=body)


def main():
    setup_console()
    parser = argparse.ArgumentParser(
        description="原稿をnote貼り付け用に整形します。"
    )
    parser.add_argument("--out", default=DIR_OUT)
    args = parser.parse_args()
    out_dir = args.out

    print("=" * LINE_WIDTH)
    print(" note貼り付け用ページの生成")
    print("=" * LINE_WIDTH)

    try:
        import markdown  # noqa
    except ImportError:
        print("エラー: markdown ライブラリが必要です。")
        print("  python -m pip install markdown")
        return 1

    os.makedirs(out_dir, exist_ok=True)
    chapters = find_chapters()
    if not chapters:
        print("エラー: 章ファイルが見つかりません。")
        return 1

    total = {"tables": 0, "tables_opened": 0, "blocks": 0, "blocks_labeled": 0,
             "shots": 0, "shots_with_image": 0, "shots_removed": 0,
             "split_chapters": 0}
    items = []

    print()
    for num, name in chapters:
        md = read_text(os.path.join(DIR_MS, name))
        m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
        title = m.group(1).strip() if m else name

        st = {k: 0 for k in total}
        conv = convert_chapter(md, st)
        for k in total:
            total[k] += st[k]

        # 長い章は前後編に分ける
        parts = split_chapter(conv, num, title)
        if len(parts) > 1:
            total["split_chapters"] += 1

        suffixes = ["a", "b", "c"]
        for pi, (part_title, part_md) in enumerate(parts):
            cid = "ch{:02d}".format(num)
            if len(parts) > 1:
                cid += suffixes[pi]

            body_html = md_to_html(part_md)
            chars = len(re.sub(r"\s", "", part_md))
            items.append((cid, part_title, chars))

            bar = """<div class="bar">
  <span class="t">{t}（約{c:,}文字）</span>
  <button class="btn primary" id="sel">本文をコピー</button>
  <a class="btn" href="index.html">記事一覧</a>
</div>""".format(t=html.escape(part_title), c=chars)

            howto = """<div class="howto">
  <b>使い方</b>　「本文をコピー」を押す → noteの編集画面を開く → 貼り付け（Ctrl+V）<br>
  見出し・太字・箇条書き・引用・画像は書式が保たれます。<br>
  表はnoteで保持されないため、あらかじめ箇条書きに開いてあります。
</div>"""

            with open(os.path.join(out_dir, cid + ".html"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(page(part_title, bar, body_html, howto))

            mark = "  ←分割" if len(parts) > 1 else ""
            print("  {:<11}{:<42}{:>7,}字{}".format(
                cid + ".html", part_title[:40], chars, mark))

    # 章一覧
    rows = []
    for cid, title, chars in items:
        rows.append(
            '<li><a href="{cid}.html">{t}</a>　<span style="color:#5b6672;'
            'font-size:14px">約{c:,}文字</span></li>'.format(
                cid=cid, t=html.escape(title), c=chars)
        )

    idx_bar = """<div class="bar">
  <span class="t">note貼り付け用　章一覧</span>
  <a class="btn" href="../read/">通読版</a>
  <a class="btn" href="../">素材ページ</a>
</div>"""

    idx_body = """
<h1>noteへ貼り付ける</h1>
<p>1記事あたり5,000〜8,000字になるよう、長い章は前後編に分けています。</p>
<h2>手順</h2>
<ol>
<li>下の章を開く</li>
<li>「本文をコピー」を押す</li>
<li>noteで新規記事を作り、本文に貼り付ける（Ctrl+V）</li>
<li>下書き保存する</li>
</ol>
<h2>note向けに調整してある点</h2>
<ul>
<li>チェックボックス（- [ ]）を「□」に置き換え（noteにチェックボックス機能がないため）</li>
<li>4列以上の表を「見出し＋箇条書き」に変換（スマートフォンで読めるようにするため）</li>
<li>20行以上のコードブロックに行数の見出しを追加（折りたためないため）</li>
<li>4段目以降の見出しを太字の段落に変更（noteの見出しは3段階のため）</li>
<li>撮影前のスクリーンショット指示は削除（読者に見せる原稿のため）</li>
</ul>
<h2>記事一覧</h2>
<ul>{rows}</ul>
""".format(rows="\n".join(rows))

    with open(os.path.join(out_dir, "index.html"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(page("note貼り付け用", idx_bar, idx_body))

    print()
    print("=" * LINE_WIDTH)
    print(" 変換した内容")
    print("=" * LINE_WIDTH)
    print("  表　　　　　: {} 個中 {} 個を箇条書きに開いた".format(
        total["tables"], total["tables_opened"]))
    print("  コードブロック: {} 個中 {} 個に行数の見出しを追加".format(
        total["blocks"], total["blocks_labeled"]))
    print("  図の位置　　: {} 箇所中 {} 箇所に画像、{} 箇所は削除".format(
        total["shots"], total["shots_with_image"], total["shots_removed"]))
    print()
    print("出力先: {}".format(out_dir))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
