#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_readability.py

原稿の「読みやすさ」を実測します。

【このスクリプトは教材の保守用です】

推敲は感覚でやると迷います。
数字にすると、どこを直せばよいかが決まります。

【測るもの】

  1. 一文の長さ        40字以下が軽快。60字を超えると読み返しが増える
  2. 表の列数          noteは表を保持しない。列が多いほど平文化したとき壊滅的
  3. コードブロックの行数  noteは折りたためない。長いと本文が分断される
  4. チェックボックスの数  noteに機能がないため要変換
  5. 見出しの間隔        見出しが少ないと読み進めにくい。100〜300字に1つが目安
  6. 語尾の偏り         同じ語尾が続くと単調になる
  7. 漢字比率          30%前後が読みやすい。40%を超えると硬い

使い方:
    python  scripts/analyze_readability.py            # Windows
    python3 scripts/analyze_readability.py            # macOS

    python scripts/analyze_readability.py --detail    # 長い文も一覧表示

外部APIは使用しません。
"""

import os
import re
import sys
import argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR_MS = os.path.join(ROOT, "manuscript")

# ============================================================
# 目安の値（推敲の基準。プロジェクトに合わせて変えてください）
# ============================================================

SENT_GOOD = 40        # 一文の長さ（これ以下が軽快）
SENT_WARN = 60        # これを超えると読み返しが増える
HEADING_SPAN = 300    # 見出しの間隔の上限（字）
KANJI_GOOD = 32.0     # 漢字比率の目安（%）
LONG_BLOCK = 20       # 長いと判断するコードブロックの行数
CHAP_MAX = 9000       # note 1記事としての目安の上限（字）

LINE_WIDTH = 104


def setup_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_chapters():
    pat = re.compile(r"^(\d{2})_.+\.md$")
    out = []
    for n in os.listdir(DIR_MS):
        if n == "full_manuscript.md":
            continue
        m = pat.match(n)
        if m:
            out.append((int(m.group(1)), n))
    return sorted(out)


def split_code(md):
    """
    コードブロックを本文から分離します。

    プロンプト例などは推敲の対象外なので、
    文の長さや漢字比率の計算から外します。
    """
    blocks, body, cur = [], [], []
    inb = False
    for l in md.split("\n"):
        if l.strip().startswith("```"):
            if inb:
                blocks.append(cur)
                cur = []
            inb = not inb
            continue
        (cur if inb else body).append(l)
    return "\n".join(body), blocks


def sentences(body):
    """
    本文を文に分けます。

    見出し・箇条書き・表の記号は落としてから分割します。
    表と箇条書きは句点で終わらないため、
    文としては数えず、別の指標（表・リスト）で見ます。
    """
    out = []
    for line in body.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("|") or s.startswith("#") or s.startswith(">"):
            continue
        if re.match(r"^\s*[-*]\s", s) or re.match(r"^\s*\d+\.\s", s):
            continue
        s = re.sub(r"\*\*|`|\[|\]\([^)]*\)", "", s)
        for part in re.split(r"(?<=[。！？])", s):
            part = part.strip()
            if len(part) >= 4:
                out.append(part)
    return out


def analyze(md):
    body, blocks = split_code(md)
    sents = sentences(body)
    lens = [len(s) for s in sents]

    # 表
    tables, max_cols = 0, 0
    lines = body.split("\n")
    for i, l in enumerate(lines):
        if re.match(r"^\s*\|", l) and i + 1 < len(lines) \
                and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i + 1]):
            tables += 1
            max_cols = max(max_cols, l.count("|") - 1)

    # 見出し
    heads = len(re.findall(r"^#{2,3}\s", body, re.MULTILINE))
    chars = len(re.sub(r"\s", "", md))
    body_chars = len(re.sub(r"\s", "", body))

    # 漢字比率
    plain = "".join(sents)
    kanji = len(re.findall(r"[一-鿿]", plain))
    kana = len(re.findall(r"[぀-ヿ]", plain))

    # 語尾
    tails = Counter()
    for s in sents:
        m = re.search(r"(.{2,5})[。！？]$", s)
        if m:
            tails[m.group(1)] += 1

    blk = [len(b) for b in blocks]

    return dict(
        chars=chars,
        sents=len(sents),
        avg=sum(lens) / len(lens) if lens else 0,
        over_good=sum(1 for x in lens if x > SENT_GOOD),
        over_warn=sum(1 for x in lens if x > SENT_WARN),
        longest=max(lens) if lens else 0,
        long_sents=[s for s in sents if len(s) > SENT_WARN],
        tables=tables, max_cols=max_cols,
        blocks=len(blk), long_blocks=sum(1 for x in blk if x >= LONG_BLOCK),
        max_block=max(blk) if blk else 0,
        cbs=len(re.findall(r"^\s*-\s\[[ xX]\]", body, re.MULTILINE)),
        heads=heads,
        span=body_chars / max(1, heads),
        kanji=kanji / max(1, kanji + kana) * 100,
        tails=tails,
    )


def flag(cond):
    return "★" if cond else "  "


def main():
    setup_console()
    ap = argparse.ArgumentParser(description="原稿の読みやすさを実測します。")
    ap.add_argument("--detail", action="store_true", help="長い文を一覧表示")
    args = ap.parse_args()

    chapters = find_chapters()
    if not chapters:
        print("エラー: 章ファイルが見つかりません。")
        return 1

    rows, total_tails = [], Counter()

    print("=" * LINE_WIDTH)
    print(" 読みやすさの実測　（★ = 目安を外れている項目）")
    print("=" * LINE_WIDTH)
    print("{:<24}{:>7}{:>6}{:>7}{:>7}{:>6}{:>7}{:>7}{:>7}{:>8}".format(
        "章", "文字", "文数", "平均字", ">60字", "表", "最大列", "長ｺｰﾄﾞ", "☑", "漢字%"))
    print("-" * LINE_WIDTH)

    for num, name in chapters:
        with open(os.path.join(DIR_MS, name), encoding="utf-8-sig") as f:
            md = f.read()
        a = analyze(md)
        rows.append((name, a))
        total_tails += a["tails"]

        print("{:<24}{:>7,}{:>6}{:>6.1f}{}{:>5}{}{:>5}{}{:>6}{}{:>5}{}{:>6}{}{:>6.1f}{}".format(
            name[:22], a["chars"], a["sents"], a["avg"], flag(a["avg"] > SENT_GOOD),
            a["over_warn"], flag(a["over_warn"] > 15),
            a["tables"], flag(a["tables"] > 0),
            a["max_cols"], flag(a["max_cols"] >= 4),
            a["long_blocks"], flag(a["long_blocks"] > 3),
            a["cbs"], flag(a["cbs"] > 25),
            a["kanji"], flag(a["kanji"] > KANJI_GOOD)))

    print("-" * LINE_WIDTH)
    t = lambda k: sum(a[k] for _n, a in rows)
    print("{:<24}{:>7,}{:>6}{:>6.1f} {:>5} {:>5} {:>6} {:>5} {:>6}".format(
        "合計", t("chars"), t("sents"),
        sum(a["avg"] * a["sents"] for _n, a in rows) / max(1, t("sents")),
        t("over_warn"), t("tables"),
        max(a["max_cols"] for _n, a in rows), t("long_blocks"), t("cbs")))

    # --- 1記事として重い章 ---
    heavy = [(n, a) for n, a in rows if a["chars"] > CHAP_MAX]
    if heavy:
        print()
        print("=" * LINE_WIDTH)
        print(" note 1記事としては重い章（目安 {:,}字）".format(CHAP_MAX))
        print("=" * LINE_WIDTH)
        for n, a in sorted(heavy, key=lambda x: -x[1]["chars"]):
            print("  {:<30} {:>7,} 字   前後編に分けると読みやすくなります".format(
                n[:28], a["chars"]))

    # --- 長いコードブロック ---
    print()
    print("=" * LINE_WIDTH)
    print(" 長いコードブロック（noteでは折りたためません）")
    print("=" * LINE_WIDTH)
    for n, a in sorted(rows, key=lambda x: -x[1]["max_block"])[:5]:
        if a["max_block"] >= LONG_BLOCK:
            print("  {:<30} 最長 {:>3} 行 / {}行以上が {} 個".format(
                n[:28], a["max_block"], LONG_BLOCK, a["long_blocks"]))

    # --- 語尾 ---
    print()
    print("=" * LINE_WIDTH)
    print(" 語尾の偏り（同じ語尾が続くと単調になります）")
    print("=" * LINE_WIDTH)
    tot = sum(total_tails.values())
    for w, c in total_tails.most_common(8):
        bar = "#" * int(c / max(1, total_tails.most_common(1)[0][1]) * 34)
        print("  {:<8}{:>5} 回 {:>5.1f}%  {}".format(w, c, c / tot * 100, bar))

    # --- 長い文の実例 ---
    if args.detail:
        print()
        print("=" * LINE_WIDTH)
        print(" {}字を超える文（章ごとに上位3件）".format(SENT_WARN))
        print("=" * LINE_WIDTH)
        for n, a in rows:
            ls = sorted(a["long_sents"], key=len, reverse=True)[:3]
            if not ls:
                continue
            print("\n  【{}】".format(n))
            for s in ls:
                print("    {:>3}字: {}".format(len(s), s[:74] + ("…" if len(s) > 74 else "")))

    print()
    print("=" * LINE_WIDTH)
    print(" 目安")
    print("=" * LINE_WIDTH)
    print("  一文        {}字以下が軽快 / {}字を超えると読み返しが増える".format(
        SENT_GOOD, SENT_WARN))
    print("  漢字比率     {:.0f}%前後が読みやすい / 40%を超えると硬い".format(KANJI_GOOD))
    print("  見出し間隔   100〜{}字に1つ".format(HEADING_SPAN))
    print("  1記事        {:,}字程度まで".format(CHAP_MAX))
    print("  表           noteでは保持されないため、箇条書きに開く")
    print("               （scripts/build_note_version.py が自動で行います）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
