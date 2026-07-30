#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sample_figures.py

ImageMagick を使って、教材用のサンプル画像と説明図を作るスクリプトです。

【このスクリプトは教材の保守用です】
読者が制作作業で使うものではありません。
教材（このリポジトリ）を編集した人が、図版を作り直すために使います。

【入力】
    assets/sample-images/generated/*.png
        Codex ImageGen で生成したキャラクター画像（背景 #EFEFEF の単色）

【出力】
    assets/sample-images/transparent/   背景を透過した画像
    assets/sample-images/stamps/        LINE仕様に合わせたスタンプ画像
    assets/sample-images/figures/       教材に貼る説明図

【処理の流れ】
    1. 背景の #EFEFEF を flood fill で透過にする
       （-transparent ではなく flood fill を使うのが重要。
         白いTシャツを消さないため）
    2. 余白をトリミングして、LINE仕様のサイズに収める
    3. セリフを入れて、白フチ＋濃色の2重フチを付ける
    4. 比較用の説明図を組み立てる

【必要なもの】
    ImageMagick 7 以上（magick コマンド）
        確認: magick -version

使い方:
    python  scripts/build_sample_figures.py      # Windows
    python3 scripts/build_sample_figures.py      # macOS

オプション:
    --skip-transparent  透過処理を飛ばす（すでに作ってある場合）
    --only <名前>       特定の図だけを作り直す

外部APIは使用しません。
"""

import os
import sys
import shutil
import argparse
import subprocess

# ============================================================
# 設定
# ============================================================

# LINE Creators Market の仕様（2026年7月30日時点の公式記載）
STAMP_SIZE = (370, 320)      # スタンプ画像の最大サイズ
MAIN_SIZE = (240, 240)       # メイン画像
TAB_SIZE = (96, 74)          # タブ画像
MARGIN_PX = 10               # 外枠とコンテンツの間に必要な余白

# フォント
# 【注意】Meiryo は Windows 同梱フォントです。
# 教材を商用配布する場合は、フォントのライセンスを必ず確認してください。
# オープンライセンスのフォント（Noto Sans JP など）に差し替える場合は、
# ここのパスだけを変更してください。
FONT_CANDIDATES = [
    "C:/Windows/Fonts/meiryob.ttc",          # Meiryo Bold
    "C:/Windows/Fonts/YuGothB.ttc",          # Yu Gothic Bold
    "C:/Windows/Fonts/biz-udgothicb.ttc",    # BIZ UDGothic Bold
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",  # macOS
]

# 色
COLOR_BG_GENERATED = "#EFEFEF"   # 生成画像の背景色
COLOR_TEXT = "#2B2B2B"           # 文字の色
COLOR_STROKE = "#FFFFFF"         # 文字のフチ（白）
COLOR_ACCENT = "#FF4FA3"         # アクセント（キャラクターの羽織りの色）
COLOR_DARK_TALK = "#1F2A33"      # 暗いトーク背景に見立てた色
COLOR_LIGHT_TALK = "#8CABD9"     # 明るいトーク背景に見立てた色

# flood fill の許容誤差
FUZZ = "20%"

# 作るスタンプ（出力名, 元画像, セリフ）
STAMPS = [
    ("stamp_001.png", "aina_base.png", "おはよ！"),
    ("stamp_002.png", "aina_ok.png", "了解っしょ！"),
    ("stamp_003.png", "aina_sorry.png", "ごめん！"),
    ("stamp_004.png", "aina_surprised.png", "びっくり"),
    ("stamp_005.png", "aina_happy.png", "やったー！"),
]

# ============================================================
# パス
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR_GEN = os.path.join(ROOT, "assets", "sample-images", "generated")
DIR_TRANS = os.path.join(ROOT, "assets", "sample-images", "transparent")
DIR_STAMPS = os.path.join(ROOT, "assets", "sample-images", "stamps")
DIR_FIG = os.path.join(ROOT, "assets", "sample-images", "figures")

LINE_WIDTH = 60


def setup_console():
    """Windowsのコンソールで日本語が文字化けしないようにします。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_font():
    """
    使える日本語フォントを探します。

    戻り値:
        フォントのパス / 見つからない場合は None
    """
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def run_magick(args, description=""):
    """
    magick コマンドを実行します。

    引数はリストで渡すため、パスに空白が含まれていても安全です。

    戻り値:
        True = 成功 / False = 失敗
    """
    cmd = ["magick"] + [str(a) for a in args]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    except FileNotFoundError:
        print("  エラー: magick コマンドが見つかりません。")
        print("          ImageMagick をインストールしてください。")
        return False
    except Exception as e:
        print("  エラー: magick の実行に失敗しました（{}）".format(e))
        return False

    if result.returncode != 0:
        print("  失敗: {}".format(description or " ".join(cmd[:4])))
        if result.stderr:
            for line in result.stderr.strip().split("\n")[:4]:
                print("        {}".format(line))
        return False
    return True


def identify(path):
    """
    画像のサイズを取得します。

    戻り値:
        (幅, 高さ) / 取得できない場合は None
    """
    try:
        result = subprocess.run(
            ["magick", "identify", "-format", "%w %h", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return None
        w, h = result.stdout.strip().split()
        return (int(w), int(h))
    except Exception:
        return None


# ============================================================
# 1. 背景の透過
# ============================================================

def make_transparent(src, dst):
    """
    背景の単色（#EFEFEF）を透過にします。

    【重要】-transparent ではなく flood fill を使います。

    -transparent は「画像全体の一致する色」を透明にするため、
    白いTシャツ（#FFFFFF）も一緒に消えてしまいます。

    flood fill は「四隅からつながっている領域」だけを透明にするため、
    キャラクターの内側にある白は残ります。

    先に1pxの枠を足すのは、背景が四隅まで確実に届くようにするためです。
    """
    return run_magick(
        [
            src,
            "-alpha", "set",
            "-bordercolor", COLOR_BG_GENERATED,
            "-border", "2",
            "-fuzz", FUZZ,
            "-fill", "none",
            "-draw", "alpha 0,0 floodfill",
            "-shave", "2x2",
            dst,
        ],
        "透過: " + os.path.basename(src),
    )


# ============================================================
# 2. LINE仕様のスタンプ画像を作る
# ============================================================

def pointsize_for(text):
    """
    セリフの文字数から、適切な文字サイズを決めます。

    文字数が多いほど小さくしないと、画像の幅に収まりません。
    """
    n = len(text)
    if n <= 4:
        return 66
    if n <= 6:
        return 54
    if n <= 8:
        return 44
    if n <= 11:
        return 34
    return 28


def make_stamp(src_transparent, dst, text, font, size=None, margin=None):
    """
    透過済み画像から、LINE仕様のスタンプ画像を作ります。

    手順:
        1. 透明部分をトリミングする
        2. 余白の分を引いたサイズに収まるよう縮小する
        3. 規定サイズのキャンバスの中央に配置する
        4. セリフを白フチ付きで入れる

    白フチを付けるのは、暗いトーク背景でも文字が読めるようにするためです。
    """
    size = size or STAMP_SIZE
    margin = MARGIN_PX if margin is None else margin

    inner_w = size[0] - margin * 2
    inner_h = size[1] - margin * 2

    ps = pointsize_for(text) if text else 0
    sw = max(4, int(ps * 0.20))  # フチの太さは文字サイズの2割程度

    args = [
        src_transparent,
        "-background", "none",
        "-trim", "+repage",
        "-resize", "{}x{}".format(inner_w, inner_h),
        "-gravity", "center",
        "-extent", "{}x{}".format(size[0], size[1]),
    ]

    if text:
        # 1回目: 白い太いフチを描く
        # 2回目: その上に濃い色の文字を重ねる
        # この順番でないと、フチが文字を覆ってしまいます
        args += [
            "-font", font,
            "-pointsize", str(ps),
            "-gravity", "south",
            "-stroke", COLOR_STROKE,
            "-strokewidth", str(sw),
            "-annotate", "+0+{}".format(margin + 2), text,
            "-stroke", "none",
            "-fill", COLOR_TEXT,
            "-annotate", "+0+{}".format(margin + 2), text,
        ]

    args.append(dst)
    return run_magick(args, "スタンプ: " + os.path.basename(dst))


def make_main_image(src_transparent, dst, font):
    """メイン画像（240×240）を作ります。顔が大きく見えるようにします。"""
    inner = MAIN_SIZE[0] - MARGIN_PX * 2
    return run_magick(
        [
            src_transparent,
            "-background", "none",
            "-trim", "+repage",
            "-resize", "{}x{}".format(inner, inner),
            "-gravity", "center",
            "-extent", "{}x{}".format(MAIN_SIZE[0], MAIN_SIZE[1]),
            dst,
        ],
        "メイン画像",
    )


def make_tab_image(src_transparent, dst):
    """
    タブ画像（96×74）を作ります。

    タブ画像はとても小さいため、顔だけを切り出します。
    全身を縮小すると、細部が潰れて何かわからなくなります。

    トリミング後の上から45%を顔の範囲として切り出しています。
    """
    trimmed = dst + ".tmp_trim.png"
    if not run_magick(
        [src_transparent, "-background", "none", "-trim", "+repage", trimmed],
        "タブ画像（トリミング）",
    ):
        return False

    dim = identify(trimmed)
    if dim is None:
        return False
    w, h = dim

    # 顔の範囲を切り出す
    # タブ画像はとても小さいため、全身を縮小すると何かわからなくなります。
    #
    # タブ画像は 96x74 の「横長」です。
    # 顔だけを縦長に切り出すと左右に余白ができるので、
    # 髪の横まで含めた横長の範囲を切り出します。
    #
    # 【重要】切り出したあとに -trim をかけないこと。
    # trim をかけると輪郭の外側が削られ、指定した構図に戻らなくなります。
    # 比率は実測で決めています（全身画像の場合、顔は上から約46%まで）。
    # 元画像の構図が変わったら、ここを調整してください。
    face_h = int(h * 0.46)
    face_w = int(w * 0.88)
    off_x = int((w - face_w) / 2)

    inner_w = TAB_SIZE[0] - 4
    inner_h = TAB_SIZE[1] - 4

    ok = run_magick(
        [
            trimmed,
            "-crop", "{}x{}+{}+0".format(face_w, face_h, off_x),
            "+repage",
            "-background", "none",
            "-resize", "{}x{}".format(inner_w, inner_h),
            "-gravity", "center",
            "-extent", "{}x{}".format(TAB_SIZE[0], TAB_SIZE[1]),
            dst,
        ],
        "タブ画像",
    )
    try:
        os.remove(trimmed)
    except OSError:
        pass
    return ok


# ============================================================
# 3. 説明図を組み立てる部品
# ============================================================

def make_label(text, width, dst, font, pointsize=21, bg="white", fg="#2B2B2B",
               height=66):
    """
    図版に付けるラベル（帯）を作ります。

    label: ではなく caption: を使います。
    label: は幅に収まらない文字を切り捨ててしまうため、
    自動で折り返してくれる caption: のほうが安全です。

    折り返しても収まるよう、高さは2行ぶん確保しています。
    """
    inner = max(40, width - 24)
    return run_magick(
        [
            "-background", bg,
            "-fill", fg,
            "-font", font,
            "-pointsize", str(pointsize),
            "-size", "{}x".format(inner),
            "caption:" + text,
            "-gravity", "center",
            "-extent", "{}x{}".format(width, height),
            dst,
        ],
        "ラベル: " + text[:20],
    )


def on_background(src, dst, bg_color, pad=24):
    """画像を指定色の背景に重ねます（透過の確認用）。"""
    dim = identify(src)
    if dim is None:
        return False
    w, h = dim
    return run_magick(
        [
            "-size", "{}x{}".format(w + pad * 2, h + pad * 2),
            "canvas:" + bg_color,
            src,
            "-gravity", "center",
            "-composite",
            dst,
        ],
        "背景合成",
    )


def stack_v(paths, dst):
    """画像を縦に並べます。"""
    return run_magick(list(paths) + ["-background", "white", "-append", dst], "縦連結")


def stack_h(paths, dst, bg="white"):
    """画像を横に並べます。"""
    return run_magick(
        list(paths) + ["-background", bg, "-gravity", "south", "+append", dst],
        "横連結",
    )


def titled_panel(image_path, title, dst, font, width=None, bg="white",
                 title_bg="#F2F2F2", fg="#2B2B2B"):
    """画像の上にタイトル帯を付けた1枚のパネルを作ります。"""
    dim = identify(image_path)
    if dim is None:
        return False
    w = width or dim[0]
    label = dst + ".tmp_label.png"
    if not make_label(title, w, label, font, pointsize=24, bg=title_bg, fg=fg):
        return False
    ok = stack_v([label, image_path], dst)
    try:
        os.remove(label)
    except OSError:
        pass
    return ok


# ============================================================
# 4. 各説明図
# ============================================================

def fig_transparency(font):
    """
    透過の成功例と失敗例を、暗い背景の上で比較する図。

    文章では絶対に伝わらない部分なので、教材で最も重要な図です。
    """
    dst = os.path.join(DIR_FIG, "fig_transparency.png")
    tmp = []

    # 失敗例: 背景を透過していない（生成したままの #EFEFEF 背景）
    ng_src = os.path.join(DIR_GEN, "aina_base.png")
    ng_stamp = os.path.join(DIR_FIG, "_tmp_ng_stamp.png")
    tmp.append(ng_stamp)
    if not run_magick(
        [
            ng_src, "-trim", "+repage",
            "-resize", "{}x{}".format(STAMP_SIZE[0] - 20, STAMP_SIZE[1] - 20),
            "-background", COLOR_BG_GENERATED, "-gravity", "center",
            "-extent", "{}x{}".format(STAMP_SIZE[0], STAMP_SIZE[1]),
            ng_stamp,
        ],
        "透過失敗例",
    ):
        return False

    # 成功例: 透過済みのスタンプ
    ok_stamp = os.path.join(DIR_STAMPS, "stamp_001.png")

    ng_on = os.path.join(DIR_FIG, "_tmp_ng_on.png")
    ok_on = os.path.join(DIR_FIG, "_tmp_ok_on.png")
    tmp += [ng_on, ok_on]
    if not on_background(ng_stamp, ng_on, COLOR_DARK_TALK):
        return False
    if not on_background(ok_stamp, ok_on, COLOR_DARK_TALK):
        return False

    ng_panel = os.path.join(DIR_FIG, "_tmp_ng_panel.png")
    ok_panel = os.path.join(DIR_FIG, "_tmp_ok_panel.png")
    tmp += [ng_panel, ok_panel]
    if not titled_panel(ng_on, "NG  透過なし（白い四角が出る）", ng_panel,
                        font, title_bg="#FFE3E3", fg="#B00020"):
        return False
    if not titled_panel(ok_on, "OK  透過済み（キャラだけが浮く）", ok_panel,
                        font, title_bg="#E3F4E7", fg="#1B6B33"):
        return False

    ok = stack_h([ng_panel, ok_panel], dst)
    cleanup(tmp)
    return ok


def fig_outline(font):
    """白フチのあり／なしを、暗い背景で比較する図。"""
    dst = os.path.join(DIR_FIG, "fig_outline.png")
    tmp = []

    src_t = os.path.join(DIR_TRANS, "aina_ok.png")
    text = "了解っしょ！"

    # フチなし版（文字を濃い色でそのまま置く）
    no_outline = os.path.join(DIR_FIG, "_tmp_no_outline.png")
    tmp.append(no_outline)
    inner_w = STAMP_SIZE[0] - MARGIN_PX * 2
    inner_h = STAMP_SIZE[1] - MARGIN_PX * 2
    if not run_magick(
        [
            src_t, "-background", "none", "-trim", "+repage",
            "-resize", "{}x{}".format(inner_w, inner_h),
            "-gravity", "center",
            "-extent", "{}x{}".format(STAMP_SIZE[0], STAMP_SIZE[1]),
            "-font", font, "-pointsize", str(pointsize_for(text)),
            "-gravity", "south",
            "-stroke", "none", "-fill", COLOR_TEXT,
            "-annotate", "+0+{}".format(MARGIN_PX + 2), text,
            no_outline,
        ],
        "フチなし",
    ):
        return False

    with_outline = os.path.join(DIR_STAMPS, "stamp_002.png")

    a = os.path.join(DIR_FIG, "_tmp_o_a.png")
    b = os.path.join(DIR_FIG, "_tmp_o_b.png")
    tmp += [a, b]
    if not on_background(no_outline, a, COLOR_DARK_TALK):
        return False
    if not on_background(with_outline, b, COLOR_DARK_TALK):
        return False

    pa = os.path.join(DIR_FIG, "_tmp_o_pa.png")
    pb = os.path.join(DIR_FIG, "_tmp_o_pb.png")
    tmp += [pa, pb]
    if not titled_panel(a, "NG  フチなし（暗い背景で沈む）", pa, font,
                        title_bg="#FFE3E3", fg="#B00020"):
        return False
    if not titled_panel(b, "OK  白フチあり（背景を問わず読める）", pb, font,
                        title_bg="#E3F4E7", fg="#1B6B33"):
        return False

    ok = stack_h([pa, pb], dst)
    cleanup(tmp)
    return ok


def fig_size_compare(font):
    """スタンプ画像・メイン画像・タブ画像の実寸サイズを並べた図。"""
    dst = os.path.join(DIR_FIG, "fig_size_compare.png")
    tmp = []

    items = [
        (os.path.join(DIR_STAMPS, "stamp_001.png"),
         "スタンプ画像  370 x 320 px", STAMP_SIZE),
        (os.path.join(DIR_STAMPS, "main.png"),
         "メイン画像  240 x 240 px", MAIN_SIZE),
        (os.path.join(DIR_STAMPS, "tab.png"),
         "タブ画像  96 x 74 px", TAB_SIZE),
    ]

    # ラベルが切れないよう、パネルには最低幅を設ける
    MIN_PANEL_W = 210

    panels = []
    for i, (path, title, size) in enumerate(items):
        panel_w = max(size[0] + 2, MIN_PANEL_W)

        # 実寸がわかるよう、市松模様の上に置いて枠線を付ける
        framed = os.path.join(DIR_FIG, "_tmp_sz_{}.png".format(i))
        tmp.append(framed)
        if not run_magick(
            [
                "-size", "{}x{}".format(size[0], size[1]),
                "pattern:checkerboard",
                "-alpha", "off",
                path, "-gravity", "center", "-composite",
                "-bordercolor", "#999999", "-border", "1",
                # 同じ高さにそろえ、最低幅まで白で広げる
                "-background", "white", "-gravity", "north",
                "-extent", "{}x{}".format(panel_w, STAMP_SIZE[1] + 2),
                framed,
            ],
            "サイズ比較 " + title,
        ):
            return False

        panel = os.path.join(DIR_FIG, "_tmp_szp_{}.png".format(i))
        tmp.append(panel)
        if not titled_panel(framed, title, panel, font, width=panel_w):
            return False
        panels.append(panel)

    # パネルの間に隙間を入れる
    spacer = os.path.join(DIR_FIG, "_tmp_sz_spacer.png")
    tmp.append(spacer)
    if not run_magick(["-size", "28x10", "canvas:white", spacer], "隙間"):
        return False

    seq = []
    for i, p in enumerate(panels):
        if i > 0:
            seq.append(spacer)
        seq.append(p)

    ok = stack_h(seq, dst)
    cleanup(tmp)
    return ok


def fig_margin(font):
    """余白なしと余白10pxを比較する図。"""
    dst = os.path.join(DIR_FIG, "fig_margin.png")
    tmp = []
    src_t = os.path.join(DIR_TRANS, "aina_base.png")

    # 余白0（端まで大きく描いた失敗例）
    no_margin = os.path.join(DIR_FIG, "_tmp_m_no.png")
    tmp.append(no_margin)
    if not make_stamp(src_t, no_margin, "", font, margin=0):
        return False

    # 余白10px
    with_margin = os.path.join(DIR_FIG, "_tmp_m_yes.png")
    tmp.append(with_margin)
    if not make_stamp(src_t, with_margin, "", font, margin=MARGIN_PX):
        return False

    # それぞれに、10pxのガイド枠を赤線で描く
    for path in (no_margin, with_margin):
        if not run_magick(
            [
                path,
                "-fill", "none", "-stroke", "#FF3B30", "-strokewidth", "2",
                "-draw", "rectangle {},{} {},{}".format(
                    MARGIN_PX, MARGIN_PX,
                    STAMP_SIZE[0] - MARGIN_PX, STAMP_SIZE[1] - MARGIN_PX
                ),
                path,
            ],
            "ガイド枠",
        ):
            return False

    a = os.path.join(DIR_FIG, "_tmp_m_a.png")
    b = os.path.join(DIR_FIG, "_tmp_m_b.png")
    tmp += [a, b]
    if not on_background(no_margin, a, "#FFFFFF", pad=16):
        return False
    if not on_background(with_margin, b, "#FFFFFF", pad=16):
        return False

    pa = os.path.join(DIR_FIG, "_tmp_m_pa.png")
    pb = os.path.join(DIR_FIG, "_tmp_m_pb.png")
    tmp += [pa, pb]
    if not titled_panel(a, "NG  余白なし（赤枠を越えている）", pa, font,
                        title_bg="#FFE3E3", fg="#B00020"):
        return False
    if not titled_panel(b, "OK  上下左右に10pxの余白", pb, font,
                        title_bg="#E3F4E7", fg="#1B6B33"):
        return False

    ok = stack_h([pa, pb], dst)
    cleanup(tmp)
    return ok


def fig_headcount(font):
    """3頭身と6頭身を比較する図（ボツ案の説明用）。"""
    dst = os.path.join(DIR_FIG, "fig_headcount.png")
    tmp = []

    for name, src_name, title, tbg, tfg in [
        ("ok", "aina_base.png", "採用  3頭身（顔が大きく表情が読める）\n右は実際のトーク表示に近いサイズ",
         "#E3F4E7", "#1B6B33"),
        ("ng", "aina_reject_tall.png", "ボツ  6頭身（縮小すると顔が潰れる）\n右は実際のトーク表示に近いサイズ",
         "#FFE3E3", "#B00020"),
    ]:
        src_t = os.path.join(DIR_TRANS, src_name)
        stamp = os.path.join(DIR_FIG, "_tmp_hc_{}.png".format(name))
        tmp.append(stamp)
        if not make_stamp(src_t, stamp, "", font):
            return False

        # 実際のトーク表示サイズに近い大きさへ縮小したものも並べる
        small = os.path.join(DIR_FIG, "_tmp_hcs_{}.png".format(name))
        tmp.append(small)
        if not run_magick(
            [
                stamp, "-resize", "35%",
                "-background", COLOR_LIGHT_TALK, "-gravity", "center",
                "-extent", "150x130",
                small,
            ],
            "縮小表示",
        ):
            return False

        big_on = os.path.join(DIR_FIG, "_tmp_hcb_{}.png".format(name))
        tmp.append(big_on)
        if not on_background(stamp, big_on, "#FFFFFF", pad=10):
            return False

        row = os.path.join(DIR_FIG, "_tmp_hcr_{}.png".format(name))
        tmp.append(row)
        if not stack_h([big_on, small], row):
            return False

        panel = os.path.join(DIR_FIG, "_tmp_hcp_{}.png".format(name))
        tmp.append(panel)
        if not titled_panel(row, title, panel, font, title_bg=tbg, fg=tfg):
            return False

    ok = stack_v(
        [
            os.path.join(DIR_FIG, "_tmp_hcp_ok.png"),
            os.path.join(DIR_FIG, "_tmp_hcp_ng.png"),
        ],
        dst,
    )
    cleanup(tmp)
    return ok


def fig_textlength(font):
    """短いセリフと長いセリフの可読性を比較する図。"""
    dst = os.path.join(DIR_FIG, "fig_textlength.png")
    tmp = []
    src_t = os.path.join(DIR_TRANS, "aina_base.png")

    cases = [
        ("short", "おはよ！", "OK  4文字\n大きく読める", "#E3F4E7", "#1B6B33"),
        ("long", "おはようございます！", "NG  10文字\n小さくなる",
         "#FFF4E0", "#8A5A00"),
        ("toolong", "おはようございます本日もよろしく",
         "NG  15文字\n読めない", "#FFE3E3", "#B00020"),
    ]

    panels = []
    for key, text, title, tbg, tfg in cases:
        stamp = os.path.join(DIR_FIG, "_tmp_tl_{}.png".format(key))
        tmp.append(stamp)
        if not make_stamp(src_t, stamp, text, font):
            return False

        # 実際のトーク表示サイズに近い大きさ
        small = os.path.join(DIR_FIG, "_tmp_tls_{}.png".format(key))
        tmp.append(small)
        if not run_magick(
            [
                stamp, "-resize", "40%",
                "-background", COLOR_LIGHT_TALK, "-gravity", "center",
                "-extent", "215x150",
                small,
            ],
            "縮小表示",
        ):
            return False

        panel = os.path.join(DIR_FIG, "_tmp_tlp_{}.png".format(key))
        tmp.append(panel)
        if not titled_panel(small, title, panel, font, width=215,
                            title_bg=tbg, fg=tfg):
            return False
        panels.append(panel)

    spacer = os.path.join(DIR_FIG, "_tmp_tl_spacer.png")
    tmp.append(spacer)
    if not run_magick(["-size", "20x10", "canvas:white", spacer], "隙間"):
        return False

    seq = []
    for i, p in enumerate(panels):
        if i > 0:
            seq.append(spacer)
        seq.append(p)

    ok = stack_h(seq, dst)
    cleanup(tmp)
    return ok


def fig_stamp_sheet(font):
    """作った5枚を並べた一覧図（顔がそろっているかの確認用）。"""
    dst = os.path.join(DIR_FIG, "fig_stamp_sheet.png")
    tmp = []
    cells = []

    for i, (name, _src, text) in enumerate(STAMPS):
        cell = os.path.join(DIR_FIG, "_tmp_sheet_{}.png".format(i))
        tmp.append(cell)
        if not run_magick(
            [
                "-size", "{}x{}".format(STAMP_SIZE[0], STAMP_SIZE[1]),
                "pattern:checkerboard", "-alpha", "off",
                os.path.join(DIR_STAMPS, name),
                "-gravity", "center", "-composite",
                "-bordercolor", "#CCCCCC", "-border", "2",
                "-resize", "50%",
                cell,
            ],
            "一覧セル " + name,
        ):
            return False
        cells.append(cell)

    row = os.path.join(DIR_FIG, "_tmp_sheet_row.png")
    tmp.append(row)
    if not stack_h(cells, row):
        return False

    ok = titled_panel(
        row,
        "サンプル5枚（髪型・服装・線の太さがそろっているか確認する）",
        dst, font,
    )
    cleanup(tmp)
    return ok


def fig_talk_preview(font):
    """
    トーク画面での見え方を再現した図（明るい背景・暗い背景）。

    【注意】これはLINEの画面そのものではなく、
    見え方を確認するために作った「再現図」です。
    図の中にもその旨を書いています。
    """
    dst = os.path.join(DIR_FIG, "fig_talk_preview.png")
    tmp = []

    for key, bg, title in [
        ("light", COLOR_LIGHT_TALK, "明るいトーク背景での見え方（再現図）"),
        ("dark", COLOR_DARK_TALK, "暗いトーク背景での見え方（再現図）"),
    ]:
        cells = []
        for i, (name, _src, _text) in enumerate(STAMPS[:4]):
            cell = os.path.join(DIR_FIG, "_tmp_tp_{}_{}.png".format(key, i))
            tmp.append(cell)
            # 実際のトーク表示に近いサイズ（およそ幅140px相当）へ縮小
            if not run_magick(
                [
                    os.path.join(DIR_STAMPS, name),
                    "-resize", "140x120",
                    "-background", bg, "-gravity", "center",
                    "-extent", "165x140",
                    cell,
                ],
                "トーク再現 " + name,
            ):
                return False
            cells.append(cell)

        row = os.path.join(DIR_FIG, "_tmp_tp_row_{}.png".format(key))
        tmp.append(row)
        if not stack_h(cells, row, bg=bg):
            return False

        panel = os.path.join(DIR_FIG, "_tmp_tp_panel_{}.png".format(key))
        tmp.append(panel)
        if not titled_panel(row, title, panel, font):
            return False

    ok = stack_v(
        [
            os.path.join(DIR_FIG, "_tmp_tp_panel_light.png"),
            os.path.join(DIR_FIG, "_tmp_tp_panel_dark.png"),
        ],
        dst,
    )
    cleanup(tmp)
    return ok


def cleanup(paths):
    """一時ファイルを削除します。"""
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


# ============================================================
# メイン
# ============================================================

FIGURES = {
    "transparency": fig_transparency,
    "outline": fig_outline,
    "size_compare": fig_size_compare,
    "margin": fig_margin,
    "headcount": fig_headcount,
    "textlength": fig_textlength,
    "stamp_sheet": fig_stamp_sheet,
    "talk_preview": fig_talk_preview,
}


def main():
    setup_console()

    parser = argparse.ArgumentParser(
        description="ImageMagickで教材用のサンプル画像と説明図を作ります。"
    )
    parser.add_argument("--skip-transparent", action="store_true",
                        help="透過処理を飛ばす")
    parser.add_argument("--only", default=None,
                        help="特定の図だけ作る（" + " / ".join(FIGURES) + "）")
    args = parser.parse_args()

    print("=" * LINE_WIDTH)
    print(" 教材用サンプル画像・説明図の生成")
    print("=" * LINE_WIDTH)

    # --- ImageMagickの確認 ---
    if shutil.which("magick") is None:
        print("エラー: magick コマンドが見つかりません。")
        print("ImageMagick 7 以上をインストールしてください。")
        return 1

    # --- フォントの確認 ---
    font = find_font()
    if font is None:
        print("エラー: 日本語フォントが見つかりません。")
        print("スクリプト冒頭の FONT_CANDIDATES にパスを追加してください。")
        return 1
    print("使用フォント: {}".format(font))

    # --- 入力の確認 ---
    if not os.path.isdir(DIR_GEN):
        print("エラー: 入力フォルダがありません: {}".format(DIR_GEN))
        return 1

    for d in (DIR_TRANS, DIR_STAMPS, DIR_FIG):
        os.makedirs(d, exist_ok=True)

    errors = 0

    # --- 1. 透過処理 ---
    if not args.skip_transparent:
        print()
        print("[1] 背景の透過（flood fill）")
        sources = sorted(
            f for f in os.listdir(DIR_GEN) if f.lower().endswith(".png")
        )
        if not sources:
            print("  エラー: 生成画像が見つかりません。")
            return 1
        for name in sources:
            src = os.path.join(DIR_GEN, name)
            dst = os.path.join(DIR_TRANS, name)
            if make_transparent(src, dst):
                print("  OK  {}".format(name))
            else:
                errors += 1
    else:
        print()
        print("[1] 背景の透過: 飛ばしました（--skip-transparent）")

    # --- 2. スタンプ画像 ---
    print()
    print("[2] LINE仕様のスタンプ画像")
    for name, src_name, text in STAMPS:
        src_t = os.path.join(DIR_TRANS, src_name)
        if not os.path.exists(src_t):
            print("  スキップ: {} がありません".format(src_name))
            errors += 1
            continue
        dst = os.path.join(DIR_STAMPS, name)
        if make_stamp(src_t, dst, text, font):
            dim = identify(dst)
            print("  OK  {}  {}  「{}」".format(
                name, "{}x{}".format(*dim) if dim else "?", text))
        else:
            errors += 1

    base_t = os.path.join(DIR_TRANS, "aina_base.png")
    if os.path.exists(base_t):
        if make_main_image(base_t, os.path.join(DIR_STAMPS, "main.png"), font):
            print("  OK  main.png  {}x{}".format(*MAIN_SIZE))
        else:
            errors += 1
        if make_tab_image(base_t, os.path.join(DIR_STAMPS, "tab.png")):
            print("  OK  tab.png   {}x{}".format(*TAB_SIZE))
        else:
            errors += 1

    # --- 3. 説明図 ---
    print()
    print("[3] 説明図")
    targets = FIGURES if args.only is None else {
        k: v for k, v in FIGURES.items() if k == args.only
    }
    if not targets:
        print("  エラー: --only の名前が不正です（{}）".format(
            " / ".join(FIGURES)))
        return 1

    for key, fn in targets.items():
        try:
            if fn(font):
                out = os.path.join(DIR_FIG, "fig_{}.png".format(key))
                dim = identify(out)
                print("  OK  fig_{}.png  {}".format(
                    key, "{}x{}".format(*dim) if dim else "?"))
            else:
                print("  NG  fig_{}.png".format(key))
                errors += 1
        except Exception as e:
            print("  NG  fig_{}.png（例外: {}）".format(key, e))
            errors += 1

    # --- 結果 ---
    print()
    print("=" * LINE_WIDTH)
    if errors == 0:
        print(" 完了: すべて生成しました")
    else:
        print(" 完了: {} 件のエラーがありました".format(errors))
    print("=" * LINE_WIDTH)
    print()
    print("出力先:")
    print("  {}".format(DIR_TRANS))
    print("  {}".format(DIR_STAMPS))
    print("  {}".format(DIR_FIG))
    print()
    print("【フォントのライセンスについて】")
    print("この図版は Windows 同梱フォント（Meiryo等）で作成しています。")
    print("教材を商用配布する場合は、フォントのライセンスを確認し、")
    print("必要ならオープンライセンスのフォントに差し替えてください。")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
