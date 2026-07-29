#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_full_manuscript.py

manuscript/ フォルダの各章を結合して、full_manuscript.md を作ります。

【このスクリプトは教材の保守用です】
読者が制作作業で使うものではありません。
教材（このリポジトリ）を編集した人が、結合版を作り直すために使います。

【やっていること】

  1. manuscript/00_*.md 〜 13_*.md を番号順に読み込む
  2. 各章の見出しレベルを1段下げる
     （章タイトルの # を ## にする。書籍タイトルを # にするため）
  3. コードブロック（``` で囲まれた部分）の中は変換しない
     （プロンプト例やPythonのコメントの # を壊さないため）
  4. 先頭に書籍タイトルと目次を付ける
  5. 章ごとの文字数と合計文字数を表示する

使い方:
    python  scripts/build_full_manuscript.py      # Windows
    python3 scripts/build_full_manuscript.py      # macOS

オプション:
    --manuscript  原稿フォルダ（既定: manuscript）
    --output      出力先（既定: manuscript/full_manuscript.md）
    --count-only  ファイルを書き出さず、文字数だけを表示する

必要なライブラリ:
    なし（Python標準機能のみで動きます）

外部APIは使用しません。
"""

import os
import re
import sys
import argparse

# ============================================================
# 設定
# ============================================================

# 原稿フォルダ（既定）
DEFAULT_MANUSCRIPT_DIR = "manuscript"

# 出力ファイル名（既定）
DEFAULT_OUTPUT_NAME = "full_manuscript.md"

# 書籍タイトル
BOOK_TITLE = "【2026年最新版】生成AIでLINEスタンプを作って販売する完全ガイド"

# 書籍サブタイトル
BOOK_SUBTITLE = (
    "ChatGPT・Claude・ImageGenを使って、企画から審査・販売まで進める方法"
)

# 結合対象から除外するファイル名
EXCLUDED_FILES = ["full_manuscript.md"]

# 章ファイルの名前の形式（先頭が2桁の数字）
CHAPTER_PATTERN = re.compile(r"^(\d{2})_.+\.md$")

# 見出し行の形式
HEADING_PATTERN = re.compile(r"^(#{1,5})(\s+)(.*)$")

# コードブロックの開始・終了行
FENCE_PATTERN = re.compile(r"^\s*```")

# ============================================================
# ここから下は、通常は修正不要です
# ============================================================

LINE_WIDTH = 60


def setup_console():
    """Windowsのコンソールで日本語が文字化けしないようにします。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_chapter_files(manuscript_dir):
    """
    原稿フォルダから章ファイルを集めて、番号順に並べます。

    戻り値:
        [(番号, ファイル名), ...]
    """
    try:
        entries = os.listdir(manuscript_dir)
    except FileNotFoundError:
        raise FileNotFoundError(
            "原稿フォルダが見つかりません: {}".format(manuscript_dir)
        )
    except PermissionError:
        raise PermissionError(
            "原稿フォルダを読み取る権限がありません: {}".format(manuscript_dir)
        )

    chapters = []
    for name in entries:
        if name in EXCLUDED_FILES:
            continue
        match = CHAPTER_PATTERN.match(name)
        if match:
            chapters.append((int(match.group(1)), name))

    chapters.sort()
    return chapters


def read_text(path):
    """
    ファイルをUTF-8で読み込みます。

    BOM付きで保存されている場合にも対応するため utf-8-sig を使います。
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding, e.object, e.start, e.end,
            "ファイルの文字コードがUTF-8ではない可能性があります: {}".format(path),
        )
    except OSError as e:
        raise OSError("ファイルを読み込めませんでした: {} ({})".format(path, e))


def demote_headings(text):
    """
    見出しレベルを1段下げます。

    コードブロック（``` で囲まれた部分）の中は変換しません。
    プロンプト例やPythonのコメントに含まれる # を
    見出しと誤認しないためです。

    戻り値:
        変換後の文字列
    """
    lines = text.split("\n")
    result = []
    in_fence = False

    for line in lines:
        # コードブロックの開始・終了を検出する
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            result.append(line)
            continue

        # コードブロックの中は変換しない
        if in_fence:
            result.append(line)
            continue

        match = HEADING_PATTERN.match(line)
        if match:
            hashes, space, content = match.groups()
            # 6段（######）を超えないようにする
            if len(hashes) < 6:
                hashes = hashes + "#"
            result.append(hashes + space + content)
        else:
            result.append(line)

    return "\n".join(result)


def extract_chapter_title(text):
    """
    章ファイルの先頭にある H1 見出しから、章タイトルを取り出します。

    見つからない場合は None を返します。
    """
    lines = text.split("\n")
    in_fence = False
    for line in lines:
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("# "):
            return line[2:].strip()
    return None


def count_characters(text):
    """
    文字数を数えます。

    改行と空白を除いた実質的な文字数を返します。
    noteに貼ったときのボリュームの目安として使います。
    """
    cleaned = re.sub(r"\s", "", text)
    return len(cleaned)


def build_toc(chapter_titles):
    """目次を作ります。"""
    lines = ["## 目次", ""]
    for title in chapter_titles:
        lines.append("- {}".format(title))
    lines.append("")
    return "\n".join(lines)


def build_front_matter(chapter_titles):
    """書籍タイトルと目次、注意書きを作ります。"""
    parts = []
    parts.append("# {}".format(BOOK_TITLE))
    parts.append("")
    parts.append("**{}**".format(BOOK_SUBTITLE))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## この教材について")
    parts.append("")
    parts.append("絵が描けなくても、生成AIを使えばLINEスタンプは作れます。")
    parts.append("")
    parts.append(
        "この教材は、テーマ選びからキャラクター設計、セリフ40個の作成、"
        "画像生成、加工、LINE Creators Marketへの申請、審査対応、"
        "販売後の宣伝、シリーズ展開までを、実際に手を動かせる手順として書いたものです。"
    )
    parts.append("")
    parts.append("**重要な注意**")
    parts.append("")
    parts.append(
        "LINE Creators Marketの仕様（画像サイズ・枚数・価格帯・分配金・"
        "AI利用に関するルールなど）は変更される可能性があります。"
    )
    parts.append("")
    parts.append(
        "この教材に出てくる数値は参考値として扱い、"
        "**申請前に必ずLINE Creators Market公式の最新ガイドラインを"
        "確認してください。**"
    )
    parts.append("")
    parts.append(
        "また、画像生成AIとフォントの商用利用条件は、"
        "ご自身で各サービスの公式情報を確認してください。"
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(build_toc(chapter_titles))
    parts.append("---")
    parts.append("")
    return "\n".join(parts)


def main():
    """メインの処理。"""
    setup_console()

    parser = argparse.ArgumentParser(
        description="各章を結合して full_manuscript.md を作ります。"
    )
    parser.add_argument(
        "--manuscript", default=DEFAULT_MANUSCRIPT_DIR,
        help="原稿フォルダ（既定: {}）".format(DEFAULT_MANUSCRIPT_DIR),
    )
    parser.add_argument(
        "--output", default=None,
        help="出力先（既定: <原稿フォルダ>/{}）".format(DEFAULT_OUTPUT_NAME),
    )
    parser.add_argument(
        "--count-only", action="store_true",
        help="ファイルを書き出さず、文字数だけを表示する",
    )
    args = parser.parse_args()

    manuscript_dir = args.manuscript
    output_path = args.output or os.path.join(manuscript_dir, DEFAULT_OUTPUT_NAME)

    print("=" * LINE_WIDTH)
    print(" 原稿結合ツール")
    print("=" * LINE_WIDTH)
    print("原稿フォルダ: {}".format(os.path.abspath(manuscript_dir)))
    print()

    # --- 章ファイルを集める ---
    try:
        chapters = find_chapter_files(manuscript_dir)
    except (FileNotFoundError, PermissionError) as e:
        print("エラー: {}".format(e))
        print()
        print("確認してください。")
        print("  1. リポジトリのルートで実行しているか")
        print("  2. --manuscript でフォルダを指定しているか")
        return 1

    if not chapters:
        print("エラー: 章ファイルが見つかりませんでした。")
        print("ファイル名が 00_〜13_ で始まる .md ファイルを探しています。")
        return 1

    print("[1] 章ファイルの読み込み")
    print()

    body_parts = []
    chapter_titles = []
    counts = []
    total = 0

    for number, name in chapters:
        path = os.path.join(manuscript_dir, name)
        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError) as e:
            print("  エラー: {}".format(e))
            return 1

        title = extract_chapter_title(text) or name
        chapter_titles.append(title)

        count = count_characters(text)
        counts.append((name, title, count))
        total += count

        print("  {:<32} {:>7,} 文字  ({})".format(name, count, title))

        body_parts.append(demote_headings(text).rstrip())

    print()
    print("[2] 文字数の集計")
    print()
    print("  合計: {:,} 文字（空白・改行を除く）".format(total))
    print()

    if total < 30000:
        print("  注意: 目標の30,000文字に達していません。")
        print("        不足: 約 {:,} 文字".format(30000 - total))
    else:
        print("  OK: 目標の30,000文字を超えています。")
    print()

    if args.count_only:
        print("--count-only が指定されているため、ファイルは書き出しません。")
        return 0

    # --- 結合して書き出す ---
    print("[3] 結合版の書き出し")
    print()

    front = build_front_matter(chapter_titles)
    separator = "\n\n---\n\n"
    full_text = front + separator.join(body_parts) + "\n"

    try:
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(full_text)
    except PermissionError:
        print("  エラー: 書き込めませんでした。ファイルを開いていませんか。")
        print("          {}".format(os.path.abspath(output_path)))
        return 1
    except OSError as e:
        print("  エラー: 書き込めませんでした（{}）".format(e))
        return 1

    full_count = count_characters(full_text)

    print("  出力先: {}".format(os.path.abspath(output_path)))
    print("  文字数: {:,} 文字（目次・前書きを含む）".format(full_count))
    print()
    print("=" * LINE_WIDTH)
    print(" 完了")
    print("=" * LINE_WIDTH)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
