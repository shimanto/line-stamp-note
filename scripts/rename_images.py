#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_images.py

画像ファイルを stamp_001.png 形式の連番にリネームするスクリプトです。

【安全のための設計】

  1. 元ファイルを上書きしません
     入力フォルダには一切書き込まず、出力フォルダへコピーします。

  2. 処理前に対象ファイルの一覧を表示します
     確認して y を入力するまで、何も起きません。

  3. 連番順が崩れないようにします
     ファイル名に含まれる数字を「数値」として比較するため、
     img1 / img2 / img10 が正しい順に並びます。

  4. メイン画像とタブ画像は連番から除外します
     main.png と tab.png は、名前を変えずに出力フォルダへコピーします。

使い方:
    python  rename_images.py --input edited --output output      # Windows
    python3 rename_images.py --input edited --output output      # macOS

オプション:
    --input   入力フォルダ（元画像。書き込みません）
    --output  出力フォルダ（なければ自動で作成します）
    --start   開始番号（省略すると 1）
    --prefix  ファイル名の先頭（省略すると stamp）
    --digits  番号の桁数（省略すると 3）
    --yes     確認を省略して実行する
    --dry-run 一覧だけ表示して、コピーはしない

必要なライブラリ:
    なし（Python標準機能のみで動きます）

外部APIは使用しません。
"""

import os
import re
import sys
import shutil
import argparse

# ============================================================
# 設定（必要に応じて修正してください）
# ============================================================

# 出力するファイル名の先頭
DEFAULT_PREFIX = "stamp"

# 番号の桁数（3なら stamp_001.png）
DEFAULT_DIGITS = 3

# 開始番号
DEFAULT_START = 1

# 連番の対象にしないファイル名（そのままコピーします）
EXCLUDED_NAMES = ["main.png", "tab.png"]

# 対象にする拡張子
TARGET_EXTENSIONS = [".png"]

# ============================================================
# ここから下は、通常は修正不要です
# ============================================================

LINE_WIDTH = 60


def setup_console():
    """
    Windowsのコンソールで日本語が文字化けしないように、
    標準出力の文字コードをUTF-8に設定します。
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def sort_key(filename):
    """
    ファイル名を並べるための「並び順のキー」を作ります。

    ファイル名に含まれる最初の数字を、数値として比較します。
    これがないと、次のような並びになってしまいます。

        img1.png
        img10.png    <- ここに来てしまう
        img2.png

    数字が含まれないファイルは、後ろにまとめます。
    """
    numbers = re.findall(r"\d+", filename)
    if numbers:
        # (0, 数値, 元の名前) の順で比較する
        return (0, int(numbers[0]), filename.lower())
    # 数字がないファイルは後ろへ
    return (1, 0, filename.lower())


def collect_target_files(input_folder):
    """
    入力フォルダから、リネーム対象のファイルを集めます。

    戻り値:
        (リネーム対象のリスト, 除外ファイルのリスト)
    """
    try:
        entries = os.listdir(input_folder)
    except FileNotFoundError:
        raise
    except PermissionError:
        raise

    targets = []
    excluded = []

    for name in entries:
        full = os.path.join(input_folder, name)

        # フォルダは対象外
        if not os.path.isfile(full):
            continue

        # 拡張子で絞り込む（大文字・小文字は区別しない）
        ext = os.path.splitext(name)[1].lower()
        if ext not in TARGET_EXTENSIONS:
            continue

        # main.png / tab.png は連番から除外する
        if name.lower() in EXCLUDED_NAMES:
            excluded.append(name)
            continue

        targets.append(name)

    targets.sort(key=sort_key)
    excluded.sort(key=sort_key)

    return targets, excluded


def build_rename_plan(targets, prefix, digits, start):
    """
    「どのファイルを、どんな名前にコピーするか」の計画を作ります。

    戻り値:
        [(元のファイル名, 新しいファイル名), ...]
    """
    plan = []
    number = start

    for name in targets:
        # 拡張子は元のものを引き継ぐ（小文字に統一）
        ext = os.path.splitext(name)[1].lower()
        new_name = "{}_{}{}".format(prefix, str(number).zfill(digits), ext)
        plan.append((name, new_name))
        number += 1

    return plan


def print_plan(plan, excluded, input_folder, output_folder):
    """処理前に、対象ファイルの一覧を表示します。"""
    print("=" * LINE_WIDTH)
    print("リネーム対象ファイル一覧")
    print("=" * LINE_WIDTH)
    print("入力フォルダ: {}".format(os.path.abspath(input_folder)))
    print("出力フォルダ: {}".format(os.path.abspath(output_folder)))
    print()

    if not plan:
        print("  リネーム対象のファイルがありません。")
    else:
        for i, (old, new) in enumerate(plan, start=1):
            print("  {:>3}. {:<28} ->  {}".format(i, old, new))

    print()
    print("対象ファイル数: {} 件".format(len(plan)))

    if excluded:
        print()
        print("次のファイルは連番から除外し、名前を変えずにコピーします。")
        for name in excluded:
            print("  - {}".format(name))

    print("=" * LINE_WIDTH)
    print()


def check_conflicts(plan, excluded, output_folder):
    """
    出力フォルダに、同じ名前のファイルが既にあるかを確認します。

    戻り値:
        既に存在するファイル名のリスト
    """
    if not os.path.isdir(output_folder):
        return []

    conflicts = []
    existing = set(n.lower() for n in os.listdir(output_folder))

    for _old, new in plan:
        if new.lower() in existing:
            conflicts.append(new)

    for name in excluded:
        if name.lower() in existing:
            conflicts.append(name)

    return conflicts


def confirm(message):
    """
    利用者に確認を求めます。

    y または yes が入力されたときだけ True を返します。
    それ以外（Enterのみ、n、Ctrl+C）は False を返します。
    """
    try:
        answer = input(message).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")


def copy_files(plan, excluded, input_folder, output_folder):
    """
    計画どおりにファイルをコピーします。

    元ファイルは変更しません（shutil.copy2 はコピーのみを行います）。

    戻り値:
        (成功件数, 失敗のリスト)
    """
    success = 0
    failures = []

    # 出力フォルダを作る（既にあれば何もしない）
    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        raise OSError("出力フォルダを作成できませんでした（{}）".format(e))

    # 連番でコピー
    for old, new in plan:
        src = os.path.join(input_folder, old)
        dst = os.path.join(output_folder, new)
        try:
            # copy2 は中身とタイムスタンプをコピーします（移動ではありません）
            shutil.copy2(src, dst)
            print("  コピー: {} -> {}".format(old, new))
            success += 1
        except OSError as e:
            failures.append((old, str(e)))
            print("  失敗　: {} （{}）".format(old, e))

    # main.png / tab.png はそのままコピー
    for name in excluded:
        src = os.path.join(input_folder, name)
        dst = os.path.join(output_folder, name)
        try:
            shutil.copy2(src, dst)
            print("  コピー: {} -> {}（名前はそのまま）".format(name, name))
            success += 1
        except OSError as e:
            failures.append((name, str(e)))
            print("  失敗　: {} （{}）".format(name, e))

    return success, failures


def main():
    """メインの処理。"""
    setup_console()

    parser = argparse.ArgumentParser(
        description="画像を stamp_001.png 形式の連番にコピーします（元ファイルは変更しません）。"
    )
    parser.add_argument(
        "--input", "-i", default="edited", help="入力フォルダ（既定: edited）"
    )
    parser.add_argument(
        "--output", "-o", default="output", help="出力フォルダ（既定: output）"
    )
    parser.add_argument(
        "--start", type=int, default=DEFAULT_START, help="開始番号（既定: 1）"
    )
    parser.add_argument(
        "--prefix", default=DEFAULT_PREFIX, help="ファイル名の先頭（既定: stamp）"
    )
    parser.add_argument(
        "--digits", type=int, default=DEFAULT_DIGITS, help="番号の桁数（既定: 3）"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="確認を省略して実行する"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="一覧だけ表示して、コピーはしない"
    )
    args = parser.parse_args()

    input_folder = args.input
    output_folder = args.output

    # --- 入力の検証 ---
    if args.digits < 1 or args.digits > 6:
        print("エラー: --digits は 1 〜 6 の範囲で指定してください。")
        return 1

    if args.start < 0:
        print("エラー: --start は 0 以上で指定してください。")
        return 1

    if not os.path.isdir(input_folder):
        print("エラー: 入力フォルダが見つかりません: {}".format(input_folder))
        print()
        print("確認してください。")
        print("  1. フォルダ名のつづりが正しいか")
        print("  2. 今いる場所が正しいか（pwd コマンドで確認できます）")
        print("  3. --input でフォルダを指定しているか")
        return 1

    # 入力と出力が同じだと、元ファイルを壊す危険があるため止める
    if os.path.abspath(input_folder) == os.path.abspath(output_folder):
        print("エラー: 入力フォルダと出力フォルダが同じです。")
        print("元ファイルを守るため、別のフォルダを指定してください。")
        return 1

    # --- 対象ファイルを集める ---
    try:
        targets, excluded = collect_target_files(input_folder)
    except PermissionError:
        print("エラー: フォルダを読み取る権限がありません: {}".format(input_folder))
        return 1
    except OSError as e:
        print("エラー: フォルダを読み取れませんでした（{}）".format(e))
        return 1

    if not targets and not excluded:
        print("対象のファイルが見つかりませんでした。")
        print()
        print("確認してください。")
        print("  1. 画像が {} フォルダに入っているか".format(input_folder))
        print("  2. 拡張子が {} になっているか".format(" / ".join(TARGET_EXTENSIONS)))
        return 1

    # --- 計画を作って表示 ---
    plan = build_rename_plan(targets, args.prefix, args.digits, args.start)
    print_plan(plan, excluded, input_folder, output_folder)

    # --- 名前の重複を確認 ---
    conflicts = check_conflicts(plan, excluded, output_folder)
    if conflicts:
        print("注意: 出力フォルダに、同じ名前のファイルが既にあります。")
        for name in conflicts[:10]:
            print("  - {}".format(name))
        if len(conflicts) > 10:
            print("  ... 他 {} 件".format(len(conflicts) - 10))
        print()
        print("このまま進めると、出力フォルダのファイルが上書きされます。")
        print("（入力フォルダの元ファイルは変更されません）")
        print()

    # --- 実行するか確認 ---
    if args.dry_run:
        print("--dry-run が指定されているため、コピーは行いません。")
        return 0

    if not args.yes:
        if not confirm("この内容でコピーを実行しますか? (y/N): "):
            print("中止しました。何も変更していません。")
            return 0

    # --- コピー実行 ---
    print()
    print("コピーを開始します。")
    print()

    try:
        success, failures = copy_files(plan, excluded, input_folder, output_folder)
    except OSError as e:
        print("エラー: {}".format(e))
        return 1

    print()
    print("=" * LINE_WIDTH)
    print("完了: {} 件をコピーしました".format(success))
    if failures:
        print("失敗: {} 件".format(len(failures)))
        for name, reason in failures:
            print("  - {}: {}".format(name, reason))
    print("=" * LINE_WIDTH)
    print()
    print("元ファイルは変更していません（{}）。".format(os.path.abspath(input_folder)))
    print()
    print("次の手順:")
    print("  1. 出力フォルダに main.png と tab.png があるか確認する")
    print("  2. 検証スクリプトを実行する")
    print("     Windows : python  validate_images.py {}".format(output_folder))
    print("     macOS   : python3 validate_images.py {}".format(output_folder))

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。何も変更していません。")
        sys.exit(130)
