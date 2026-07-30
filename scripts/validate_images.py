#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_images.py

LINEスタンプ用の画像フォルダを検証するスクリプトです。

次の8項目を自動でチェックします。

  1. 中身が本当にPNG形式か（拡張子だけPNGの偽装を検出）
  2. 画像サイズが規定内か
  3. 縦横のピクセル数が偶数か
  4. スタンプ画像の枚数が申請可能な数か
  5. 透過情報（RGBA など）があるか
  6. 実際に透明な部分があるか（白で塗りつぶしただけの状態を検出）
  7. ファイル名が stamp_001.png 形式か
  8. 画像が壊れていないか

さらに、メイン画像（main.png）とタブ画像（tab.png）の
存在とサイズも確認します。

使い方:
    python validate_images.py <フォルダ>       # Windows
    python3 validate_images.py <フォルダ>      # macOS

    フォルダを省略すると、現在のフォルダを検証します。

必要なライブラリ:
    Pillow
        Windows : python -m pip install Pillow
        macOS   : python3 -m pip install Pillow

外部APIは使用しません。ファイルの読み取りのみを行い、
画像を書き換えることはありません。
"""

import os
import re
import sys
import argparse

# ============================================================
# 設定（LINE側の仕様が変わったら、ここだけ修正してください）
#
# 【出典】
# 下の数値は 2026年7月30日時点で
# LINE Creators Market 公式の「スタンプ制作ガイドライン」
#   https://creator.line.me/ja/guideline/sticker/
# に記載されていた内容です。
#
# 【重要】
# 仕様は変更される可能性があります。
# 申請前に上記ページで最新の仕様を確認し、
# 数値が違っていればここを書き換えてください。
# ============================================================

# スタンプ画像の最大サイズ（幅, 高さ）単位はピクセル
STAMP_MAX_SIZE = (370, 320)

# メイン画像のサイズ（幅, 高さ）単位はピクセル
MAIN_IMAGE_SIZE = (240, 240)

# タブ画像のサイズ（幅, 高さ）単位はピクセル
TAB_IMAGE_SIZE = (96, 74)

# 申請可能なスタンプの枚数
VALID_STAMP_COUNTS = [8, 16, 24, 32, 40]

# 1ファイルあたりのファイルサイズ上限（キロバイト）
# 公式記載: 1個あたり 1MB 以下
MAX_FILE_SIZE_KB = 1024

# ZIPにまとめる場合の合計サイズ上限（メガバイト）
# 公式記載: ZIPファイルを 60MB 以下
MAX_ZIP_SIZE_MB = 60

# 縦横のピクセル数を偶数に限定するか
# 公式記載: 自動的に縮小されるため偶数にしてください
REQUIRE_EVEN_SIZE = True

# 画像の外枠とコンテンツの間に必要な余白（ピクセル）
# 公式記載: 10pxぐらいの余白が必要です
# 0 にするとこのチェックを行いません
MIN_MARGIN_PX = 10

# 解像度の下限（dpi）
# 公式記載: 画像の解像度は72dpi以上
# PNGに解像度情報が入っていない場合はチェックを飛ばします
MIN_DPI = 72

# 許可するカラーモード
# 公式記載: カラーモードはRGB
# RGBA は RGB にアルファチャンネルが付いたものなので許可します
ALLOWED_COLOR_MODES = ["RGB", "RGBA", "P", "LA", "PA"]

# メイン画像のファイル名
MAIN_IMAGE_NAME = "main.png"

# タブ画像のファイル名
TAB_IMAGE_NAME = "tab.png"

# スタンプ画像のファイル名の形式（stamp_001.png のような3桁連番）
STAMP_NAME_PATTERN = re.compile(r"^stamp_\d{3}\.png$")

# PNGファイルの先頭にある固定の8バイト（PNGシグネチャ）
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# ============================================================
# ここから下は、通常は修正不要です
# ============================================================

LINE_WIDTH = 60


def setup_console():
    """
    Windowsのコンソールで日本語が文字化けしないように、
    標準出力の文字コードをUTF-8に設定します。

    古いPython（3.6以前）では reconfigure が使えないため、
    失敗しても処理は続行します。
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # 設定できない環境でも動作させる（文字化けする可能性はある）
        pass


def print_header(title):
    """見出しを枠付きで表示します。"""
    print("=" * LINE_WIDTH)
    print(" " + title)
    print("=" * LINE_WIDTH)


def is_real_png(path):
    """
    ファイルの先頭8バイトを読んで、本当にPNG形式かを判定します。

    拡張子を .png に変えただけのJPEGファイルを検出するために使います。

    戻り値:
        True  : PNG形式
        False : PNG形式ではない
    """
    try:
        with open(path, "rb") as f:
            head = f.read(8)
        return head == PNG_SIGNATURE
    except OSError as e:
        # 読み取りに失敗した場合は「PNGではない」として扱う
        print("  警告: ファイルを読み取れませんでした: {} ({})".format(path, e))
        return False


def detect_actual_format(path):
    """
    ファイルの先頭バイトから、実際の画像形式を推測します。

    エラーメッセージで「本当は何の形式だったのか」を
    利用者に伝えるために使います。

    戻り値:
        形式名の文字列（判定できない場合は "不明"）
    """
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return "不明"

    if head.startswith(PNG_SIGNATURE):
        return "PNG"
    if head.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "GIF"
    if head.startswith(b"BM"):
        return "BMP"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "WebP"
    return "不明"


def load_image(path):
    """
    画像を開いて、壊れていないかを確認します。

    Pillowの verify() は一度呼ぶと画像データを読めなくなるため、
    確認後にもう一度開き直しています。

    戻り値:
        (画像オブジェクト, エラーメッセージ)
        正常なら (Image, None)
        異常なら (None, "エラーの説明")
    """
    try:
        from PIL import Image
    except ImportError:
        # 呼び出し側で対処するため、そのまま投げ直す
        raise

    try:
        # 1回目: 壊れていないかの確認
        with Image.open(path) as img:
            img.verify()
        # 2回目: 実際に情報を読むために開き直す
        img = Image.open(path)
        img.load()
        return img, None
    except FileNotFoundError:
        return None, "ファイルが見つかりません"
    except OSError as e:
        return None, "画像が壊れている可能性があります（{}）".format(e)
    except Exception as e:
        return None, "画像を読み込めませんでした（{}）".format(e)


def has_alpha_channel(img):
    """
    画像に透過情報があるかを判定します。

    RGBA / LA / PA は透過情報を持つカラーモードです。
    P（パレット）モードでも、info に transparency があれば透過を持ちます。
    """
    if img.mode in ("RGBA", "LA", "PA"):
        return True
    if img.mode == "P" and "transparency" in img.info:
        return True
    return False


def has_transparent_pixels(img):
    """
    実際に透明なピクセルが存在するかを判定します。

    「背景を白で塗りつぶしただけ」の画像を検出するために使います。
    透過情報（アルファチャンネル）はあるのに、
    すべてのピクセルが不透明という状態を見つけます。

    戻り値:
        True  : 透明な部分がある
        False : 透明な部分がない
        None  : 判定できなかった
    """
    try:
        # どのカラーモードでも同じ方法で判定できるようRGBAに変換する
        rgba = img.convert("RGBA")
        alpha = rgba.getchannel("A")
        # getextrema() は (最小値, 最大値) を返す
        # 最小値が255なら、すべてのピクセルが不透明
        min_alpha, _max_alpha = alpha.getextrema()
        return min_alpha < 255
    except Exception:
        return None


def get_file_size_kb(path):
    """ファイルサイズをキロバイト単位で返します。"""
    try:
        return os.path.getsize(path) / 1024.0
    except OSError:
        return None


def check_margin(img):
    """
    画像の外枠とコンテンツの間の余白を測ります。

    透明でないピクセルの範囲（バウンディングボックス）を求め、
    各辺からの距離を計算します。

    公式ガイドラインでは「10pxぐらいの余白が必要」とされています。

    戻り値:
        (上, 右, 下, 左) の余白ピクセル数
        判定できない場合は None
    """
    try:
        rgba = img.convert("RGBA")
        alpha = rgba.getchannel("A")
        # getbbox() は「値が0でない領域」の範囲を返す
        # アルファチャンネルに対して使うと、不透明部分の範囲がわかる
        bbox = alpha.getbbox()
        if bbox is None:
            # 全体が透明（中身がない画像）
            return None
        left, top, right, bottom = bbox
        width, height = rgba.size
        return (top, width - right, height - bottom, left)
    except Exception:
        return None


def check_dpi(img):
    """
    画像の解像度（dpi）を確認します。

    PNGに解像度情報が入っていないことは珍しくありません。
    その場合は判定を飛ばします（None を返す）。

    戻り値:
        (横dpi, 縦dpi) / 情報がない場合は None
    """
    try:
        dpi = img.info.get("dpi")
        if not dpi:
            return None
        # dpi は (x, y) のタプル
        return (float(dpi[0]), float(dpi[1]))
    except Exception:
        return None


def check_stamp_image(path, filename):
    """
    スタンプ画像1枚を検証します。

    戻り値:
        問題点のリスト（問題がなければ空のリスト）
    """
    problems = []

    # --- 1. ファイル名の形式 ---
    if not STAMP_NAME_PATTERN.match(filename):
        problems.append(
            "ファイル名が {} 形式ではありません".format("stamp_001.png")
        )

    # --- 2. 中身が本当にPNGか ---
    if not is_real_png(path):
        actual = detect_actual_format(path)
        problems.append(
            "中身がPNG形式ではありません（実際の形式: {}）".format(actual)
        )
        # PNGでない場合、以降のチェックは意味が薄いのでここで返す
        return problems

    # --- 3. 画像が壊れていないか ---
    img, error = load_image(path)
    if img is None:
        problems.append(error)
        return problems

    try:
        width, height = img.size
        max_w, max_h = STAMP_MAX_SIZE

        # --- 4. 画像サイズ ---
        if width > max_w or height > max_h:
            problems.append(
                "画像サイズが規定を超えています"
                "（{} x {} / 上限 {} x {}）".format(width, height, max_w, max_h)
            )

        # --- 5. 縦横が偶数か ---
        if REQUIRE_EVEN_SIZE:
            if width % 2 != 0:
                problems.append("横の長さが奇数です（{} x {}）".format(width, height))
            if height % 2 != 0:
                problems.append("縦の長さが奇数です（{} x {}）".format(width, height))

        # --- 6. カラーモード ---
        if img.mode not in ALLOWED_COLOR_MODES:
            problems.append(
                "カラーモードが規定外です（{} / 公式はRGB指定）".format(img.mode)
            )

        # --- 7. 透過情報があるか ---
        if not has_alpha_channel(img):
            problems.append(
                "透過情報がありません（カラーモード: {}）".format(img.mode)
            )
        else:
            # --- 8. 実際に透明な部分があるか ---
            transparent = has_transparent_pixels(img)
            if transparent is False:
                problems.append(
                    "透過情報はありますが、透明な部分が見つかりません"
                    "（背景が白などで塗りつぶされている可能性があります）"
                )
            elif transparent is None:
                problems.append("透明部分の判定に失敗しました（手動で確認してください）")

        # --- 9. 余白（公式記載: 10pxぐらい必要） ---
        if MIN_MARGIN_PX > 0:
            margins = check_margin(img)
            if margins is None:
                problems.append("余白の判定ができませんでした（中身が空の可能性があります）")
            else:
                top, right, bottom, left = margins
                short = []
                if top < MIN_MARGIN_PX:
                    short.append("上{}px".format(top))
                if right < MIN_MARGIN_PX:
                    short.append("右{}px".format(right))
                if bottom < MIN_MARGIN_PX:
                    short.append("下{}px".format(bottom))
                if left < MIN_MARGIN_PX:
                    short.append("左{}px".format(left))
                if short:
                    problems.append(
                        "余白が不足しています（{} / 必要 {}px以上）".format(
                            " ".join(short), MIN_MARGIN_PX
                        )
                    )

        # --- 10. 解像度（情報がある場合だけ判定） ---
        dpi = check_dpi(img)
        if dpi is not None:
            if dpi[0] < MIN_DPI or dpi[1] < MIN_DPI:
                problems.append(
                    "解像度が低すぎます（{:.0f} x {:.0f} dpi / 下限 {} dpi）".format(
                        dpi[0], dpi[1], MIN_DPI
                    )
                )

        # --- 11. ファイルサイズ ---
        size_kb = get_file_size_kb(path)
        if size_kb is not None and size_kb > MAX_FILE_SIZE_KB:
            problems.append(
                "ファイルサイズが大きすぎます"
                "（{:.0f} KB / 上限 {} KB = 1MB）".format(size_kb, MAX_FILE_SIZE_KB)
            )
    finally:
        # 開いた画像は必ず閉じる
        try:
            img.close()
        except Exception:
            pass

    return problems


def check_fixed_size_image(path, filename, expected_size):
    """
    メイン画像・タブ画像を検証します。

    スタンプ画像と違い、サイズが「以内」ではなく「ぴったり」である
    必要があるため、専用の関数にしています。

    戻り値:
        (問題点のリスト, サイズの文字列)
    """
    problems = []
    size_text = "-"

    if not is_real_png(path):
        actual = detect_actual_format(path)
        problems.append("中身がPNG形式ではありません（実際の形式: {}）".format(actual))
        return problems, size_text

    img, error = load_image(path)
    if img is None:
        problems.append(error)
        return problems, size_text

    try:
        width, height = img.size
        size_text = "{} x {}".format(width, height)
        exp_w, exp_h = expected_size

        if (width, height) != (exp_w, exp_h):
            problems.append(
                "サイズが規定と異なります"
                "（{} x {} / 規定 {} x {}）".format(width, height, exp_w, exp_h)
            )

        if not has_alpha_channel(img):
            problems.append("透過情報がありません（カラーモード: {}）".format(img.mode))
        else:
            transparent = has_transparent_pixels(img)
            if transparent is False:
                problems.append(
                    "透過情報はありますが、透明な部分が見つかりません"
                )

        size_kb = get_file_size_kb(path)
        if size_kb is not None and size_kb > MAX_FILE_SIZE_KB:
            problems.append(
                "ファイルサイズが大きすぎます"
                "（{:.0f} KB / 上限 {} KB）".format(size_kb, MAX_FILE_SIZE_KB)
            )
    finally:
        try:
            img.close()
        except Exception:
            pass

    return problems, size_text


def collect_png_files(folder):
    """
    フォルダ内のPNGファイルを集めて、種類ごとに分けます。

    戻り値:
        (スタンプ画像のファイル名リスト, メイン画像の有無, タブ画像の有無)
    """
    try:
        entries = sorted(os.listdir(folder))
    except FileNotFoundError:
        raise
    except PermissionError:
        raise

    stamps = []
    has_main = False
    has_tab = False

    for name in entries:
        full = os.path.join(folder, name)
        if not os.path.isfile(full):
            continue
        # 拡張子の大文字・小文字を区別しない
        if not name.lower().endswith(".png"):
            continue

        lower = name.lower()
        if lower == MAIN_IMAGE_NAME:
            has_main = True
        elif lower == TAB_IMAGE_NAME:
            has_tab = True
        else:
            stamps.append(name)

    return stamps, has_main, has_tab


def sort_key(filename):
    """
    ファイル名に含まれる数字を数値として扱い、並び順を安定させます。

    これがないと stamp_1 の次に stamp_10 が来てしまいます。
    """
    numbers = re.findall(r"\d+", filename)
    if numbers:
        return (0, int(numbers[0]), filename)
    return (1, 0, filename)


def print_footer_notice():
    """仕様確認の注意書きを表示します。"""
    print()
    print("【重要】")
    print("画像サイズ・枚数・ファイル形式などの仕様は変更される可能性があります。")
    print("申請前に LINE Creators Market 公式ガイドラインで")
    print("最新の仕様を確認してください。")
    print()
    print("このスクリプトの判定基準は、ファイル冒頭の「設定」部分に")
    print("まとめてあります。仕様が変わったら、そこだけ書き換えてください。")


def main():
    """メインの処理。"""
    setup_console()

    parser = argparse.ArgumentParser(
        description="LINEスタンプ用のPNG画像を検証します。"
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="検証するフォルダ（省略すると現在のフォルダ）",
    )
    args = parser.parse_args()
    folder = args.folder

    print_header("LINEスタンプ画像 検証ツール")
    print("対象フォルダ: {}".format(os.path.abspath(folder)))
    print()

    # --- Pillowが入っているか確認 ---
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("エラー: Pillow（画像を扱うライブラリ）がインストールされていません。")
        print()
        print("次のコマンドでインストールしてください。")
        print("  Windows : python -m pip install Pillow")
        print("  macOS   : python3 -m pip install Pillow")
        return 1

    # --- フォルダの存在確認 ---
    if not os.path.isdir(folder):
        print("エラー: フォルダが見つかりません: {}".format(folder))
        print()
        print("確認してください。")
        print("  1. フォルダ名のつづりが正しいか")
        print("  2. 今いる場所が正しいか（pwd コマンドで確認できます）")
        return 1

    # --- [1] ファイルの読み込み ---
    print("[1] ファイルの読み込み")
    try:
        stamps, has_main, has_tab = collect_png_files(folder)
    except PermissionError:
        print("  エラー: フォルダを読み取る権限がありません: {}".format(folder))
        return 1
    except OSError as e:
        print("  エラー: フォルダを読み取れませんでした（{}）".format(e))
        return 1

    stamps.sort(key=sort_key)

    print("  PNGファイル: {} 件".format(len(stamps)))
    print(
        "  メイン画像 ({}): {}".format(
            MAIN_IMAGE_NAME, "見つかりました" if has_main else "見つかりません"
        )
    )
    print(
        "  タブ画像   ({}): {}".format(
            TAB_IMAGE_NAME, "見つかりました" if has_tab else "見つかりません"
        )
    )
    print()

    if not stamps and not has_main and not has_tab:
        print("エラー: PNGファイルが1件も見つかりませんでした。")
        print()
        print("確認してください。")
        print("  1. 画像がこのフォルダに入っているか")
        print("  2. 拡張子が .png になっているか")
        print("  3. 別のフォルダを指定していないか")
        return 1

    problem_count = 0

    # --- [2] 枚数チェック ---
    print("[2] 枚数チェック")
    if len(stamps) in VALID_STAMP_COUNTS:
        print("  OK: スタンプ画像は {} 枚です（申請可能な枚数）".format(len(stamps)))
    else:
        print("  NG: スタンプ画像が {} 枚です".format(len(stamps)))
        print(
            "      申請できる枚数は {} のいずれかです".format(
                " / ".join(str(n) for n in VALID_STAMP_COUNTS)
            )
        )
        problem_count += 1
    print()

    # --- [3] 各画像のチェック ---
    print("[3] 各画像のチェック")
    ng_files = []
    for name in stamps:
        path = os.path.join(folder, name)
        try:
            problems = check_stamp_image(path, name)
        except Exception as e:
            problems = ["検証中に予期しないエラーが発生しました（{}）".format(e)]

        if problems:
            ng_files.append((name, problems))

    if not ng_files:
        print("  OK: {} 件すべて問題ありません".format(len(stamps)))
    else:
        print()
        for name, problems in ng_files:
            print("  NG: {}".format(name))
            for p in problems:
                print("      - {}".format(p))
            print()
            problem_count += len(problems)
    print()

    # --- [4] メイン画像・タブ画像のチェック ---
    print("[4] メイン画像・タブ画像のチェック")

    if not has_main:
        print("  NG: {} が見つかりません".format(MAIN_IMAGE_NAME))
        print(
            "      メイン画像（{} x {}）を作成してください".format(
                MAIN_IMAGE_SIZE[0], MAIN_IMAGE_SIZE[1]
            )
        )
        problem_count += 1
    else:
        main_path = os.path.join(folder, MAIN_IMAGE_NAME)
        # 実際のファイル名が大文字の場合にも対応する
        if not os.path.exists(main_path):
            for n in os.listdir(folder):
                if n.lower() == MAIN_IMAGE_NAME:
                    main_path = os.path.join(folder, n)
                    break
        problems, size_text = check_fixed_size_image(
            main_path, MAIN_IMAGE_NAME, MAIN_IMAGE_SIZE
        )
        if problems:
            print("  NG: {} ({})".format(MAIN_IMAGE_NAME, size_text))
            for p in problems:
                print("      - {}".format(p))
            problem_count += len(problems)
        else:
            print("  OK: {} ({})".format(MAIN_IMAGE_NAME, size_text))

    if not has_tab:
        print("  NG: {} が見つかりません".format(TAB_IMAGE_NAME))
        print(
            "      タブ画像（{} x {}／横長）を作成してください".format(
                TAB_IMAGE_SIZE[0], TAB_IMAGE_SIZE[1]
            )
        )
        problem_count += 1
    else:
        tab_path = os.path.join(folder, TAB_IMAGE_NAME)
        if not os.path.exists(tab_path):
            for n in os.listdir(folder):
                if n.lower() == TAB_IMAGE_NAME:
                    tab_path = os.path.join(folder, n)
                    break
        problems, size_text = check_fixed_size_image(
            tab_path, TAB_IMAGE_NAME, TAB_IMAGE_SIZE
        )
        if problems:
            print("  NG: {} ({})".format(TAB_IMAGE_NAME, size_text))
            for p in problems:
                print("      - {}".format(p))
            problem_count += len(problems)
        else:
            print("  OK: {} ({})".format(TAB_IMAGE_NAME, size_text))

    print()

    # --- [5] ZIPにまとめた場合の合計サイズ ---
    print("[5] 合計サイズのチェック（ZIP一括アップロード用）")
    total_kb = 0.0
    all_names = list(stamps)
    if has_main:
        all_names.append(MAIN_IMAGE_NAME)
    if has_tab:
        all_names.append(TAB_IMAGE_NAME)

    for name in all_names:
        p = os.path.join(folder, name)
        kb = get_file_size_kb(p)
        if kb is not None:
            total_kb += kb

    total_mb = total_kb / 1024.0
    if total_mb > MAX_ZIP_SIZE_MB:
        print(
            "  NG: 合計 {:.1f} MB（ZIPの上限 {} MB を超えています）".format(
                total_mb, MAX_ZIP_SIZE_MB
            )
        )
        print("      1枚ずつのアップロードに切り替えるか、画像を軽くしてください")
        problem_count += 1
    else:
        print(
            "  OK: 合計 {:.1f} MB（ZIPの上限 {} MB 以内）".format(
                total_mb, MAX_ZIP_SIZE_MB
            )
        )
    print()

    # --- 結果 ---
    print("=" * LINE_WIDTH)
    if problem_count == 0:
        print(" 結果: 問題は見つかりませんでした")
    else:
        print(" 結果: {} 件の問題が見つかりました".format(problem_count))
    print("=" * LINE_WIDTH)

    print_footer_notice()

    # 問題があれば終了コード1を返す（他のツールと連携しやすくするため）
    return 0 if problem_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
