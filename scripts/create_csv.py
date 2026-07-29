#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_csv.py

LINEスタンプのセリフ40個を管理するCSVを作るスクリプトです。

【列】
    number       通し番号（1〜40）
    category     カテゴリー（あいさつ / 返事 / 感謝 ...）
    text         セリフ
    emotion      表情
    pose         ポーズ
    image_prompt 画像生成プロンプトのメモ
    status       進捗（todo / generated / edited / done）
    filename     対応するファイル名（stamp_001.png）
    notes        メモ

【文字コード】
    UTF-8 BOM付きで出力します。

    BOM（ボム）とは、ファイルの先頭に付ける短い印です。
    これがあると、Excelが「日本語のファイルだ」と判断してくれます。
    BOMがないと、Excelで開いたときに文字化けすることがあります。

使い方:
    python  create_csv.py                                  # Windows
    python3 create_csv.py                                  # macOS

    python  create_csv.py --output csv/stamp_list.csv       # 出力先を指定
    python  create_csv.py --empty                          # 空のテンプレート
    python  create_csv.py --rows 24                        # 行数を変える

オプション:
    --output  出力先のファイル（省略すると stamp_list.csv）
    --empty   セリフを空にして、枠だけを出力する
    --rows    行数（省略すると 40）
    --force   既存ファイルがあっても、バックアップを取って上書きする

必要なライブラリ:
    なし（Python標準機能のみで動きます）

外部APIは使用しません。
"""

import os
import sys
import csv
import shutil
import argparse

# ============================================================
# 設定（必要に応じて修正してください）
# ============================================================

# CSVの列（この順番で出力します）
COLUMNS = [
    "number",
    "category",
    "text",
    "emotion",
    "pose",
    "image_prompt",
    "status",
    "filename",
    "notes",
]

# 既定の出力ファイル名
DEFAULT_OUTPUT = "stamp_list.csv"

# 既定の行数
DEFAULT_ROWS = 40

# ファイル名の形式（stamp_001.png のような3桁連番）
FILENAME_PREFIX = "stamp"
FILENAME_DIGITS = 3
FILENAME_EXTENSION = ".png"

# 進捗の初期値
INITIAL_STATUS = "todo"

# 空テンプレートで使うカテゴリーの配分
# （合計40。第4章の配分表に対応しています）
CATEGORY_PLAN = [
    ("あいさつ", 4),
    ("返事", 5),
    ("感謝", 3),
    ("謝罪", 3),
    ("確認", 4),
    ("仕事", 5),
    ("感情", 5),
    ("応援", 4),
    ("締め", 4),
    ("ネタ", 3),
]

# ============================================================
# サンプルデータ
#
# 教材の実例キャラクター「アイナ」（架空のAI活用コンサルタント）の
# セリフ40個です。そのまま使っても構いません。
#
# 形式: (カテゴリー, セリフ, 表情, ポーズ, 画像プロンプトのメモ, 備考)
# ============================================================

SAMPLE_ROWS = [
    ("あいさつ", "おはよ！", "満面の笑み",
     "右手＝頭より高く大きく振る / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "笑顔で片手を大きく振る 上半身のみ", ""),
    ("あいさつ", "おつかれ！", "にっこり",
     "右手＝胸の前で軽く拍手 / 左手＝胸の前で軽く拍手 / 体＝正面 / 足＝描かない",
     "両手で小さく拍手する", ""),
    ("あいさつ", "こんばんは〜", "にっこり",
     "右手＝胸の高さで軽く開く / 左手＝自然に下ろす / 体＝正面からやや斜め / 足＝描かない",
     "軽く会釈しながら片手を上げる", ""),
    ("あいさつ", "ひさしぶり！", "驚き＋笑顔",
     "右手＝斜め上に開く / 左手＝斜め上に開く / 体＝正面 / 足＝描かない",
     "両手を広げて再会を喜ぶ", ""),
    ("返事", "了解っしょ！", "得意げ",
     "右手＝親指を立てて胸の高さで前に出す / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "ウインクしてサムズアップ", ""),
    ("返事", "まかせて！", "満面の笑み",
     "右手＝握りこぶしで胸を叩く / 左手＝腰に当てる / 体＝正面からやや前傾 / 足＝描かない",
     "胸を叩いて引き受ける", ""),
    ("返事", "OK！", "にっこり",
     "右手＝指で丸を作り顔の横に出す / 左手＝自然に下ろす / 体＝正面 / 足＝描かない",
     "指で丸を作る", ""),
    ("返事", "ちょっと待って", "困り顔",
     "右手＝手のひらを前に出す / 左手＝胸の前で軽く握る / 体＝正面 / 足＝描かない",
     "手のひらを前に出して制止", ""),
    ("返事", "むりかも…", "困り顔",
     "右手＝小さく上げて手のひらを見せる / 左手＝小さく上げて手のひらを見せる / 体＝正面 / 足＝描かない",
     "両手を小さく上げて困る", ""),
    ("感謝", "ありがと〜！", "満面の笑み",
     "右手＝顔の前で合わせる / 左手＝顔の前で合わせる / 体＝正面 / 足＝描かない",
     "両手を合わせて感謝", ""),
    ("感謝", "助かった！", "にっこり",
     "右手＝額の汗をぬぐう / 左手＝腰に当てる / 体＝正面からやや斜め / 足＝描かない",
     "額の汗をぬぐって安心", ""),
    ("感謝", "感謝しかない", "にっこり（目を閉じる）",
     "右手＝体の横に添える / 左手＝体の横に添える / 体＝正面から前傾（深いお辞儀） / 足＝描かない",
     "深くお辞儀する", ""),
    ("謝罪", "ごめん！", "困り顔",
     "右手＝顔の前で合わせる / 左手＝顔の前で合わせる / 体＝正面からやや前傾 / 足＝描かない",
     "手を合わせて頭を下げる", ""),
    ("謝罪", "遅くなって／ごめん！", "困り顔",
     "右手＝膝に手をつく / 左手＝顔の前で軽く上げる / 体＝前傾（肩で息） / 足＝走ってきた姿勢",
     "走ってきて息を切らして謝る 2行表示", "セリフは2行に分けて配置"),
    ("謝罪", "アタシのミス…", "泣き",
     "右手＝膝の上 / 左手＝膝の上 / 体＝しゃがんで小さくなる / 足＝しゃがみ姿勢",
     "しゃがみ込んで落ち込む", ""),
    ("確認", "どう？", "期待の目（にっこり）",
     "右手＝顎に添える / 左手＝腰に当てる / 体＝正面からやや斜め（首をかたむける） / 足＝描かない",
     "首をかたむけて反応を待つ", ""),
    ("確認", "これで／合ってる？", "真剣",
     "右手＝ノートパソコンを支える / 左手＝画面を指さす / 体＝正面からやや斜め / 足＝描かない",
     "無地のノートパソコンを見せる 画面には何も表示しない", "セリフは2行 / 小物の画面は無地"),
    ("確認", "いつまで？", "真剣",
     "右手＝人差し指を1本立てる / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "指を1本立てて期限を尋ねる", ""),
    ("確認", "見た？", "にっこり",
     "右手＝スマートフォンを顔の高さに掲げる / 左手＝腰に当てる / 体＝正面からやや斜め / 足＝描かない",
     "無地のスマートフォンを掲げる 画面は単色", "小物の画面は無地"),
    ("仕事", "今から会議", "真剣",
     "右手＝書類の束を抱える / 左手＝書類を支える / 体＝やや斜めで歩く姿勢 / 足＝歩いている",
     "書類を抱えて歩く 書類に文字は描かない", ""),
    ("仕事", "資料できた！", "得意げ",
     "右手＝書類を頭上に掲げる / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "書類を掲げて達成 書類に文字は描かない", ""),
    ("仕事", "送っといた", "にっこり",
     "右手＝ノートパソコンの蓋を閉じる / 左手＝パソコンを支える / 体＝正面からやや斜め / 足＝描かない",
     "ノートパソコンを閉じる", ""),
    ("仕事", "対応中！", "真剣",
     "右手＝キーボードに置く / 左手＝キーボードに置く / 体＝正面からやや斜め / 足＝描かない",
     "パソコンを打っている 画面には何も表示しない", "小物の画面は無地"),
    ("仕事", "明日でもいい？", "眠い",
     "右手＝目をこする / 左手＝小さく上げる / 体＝正面 / 足＝描かない",
     "目をこすりながら手を上げる", ""),
    ("感情", "うれしい！", "満面の笑み",
     "右手＝頭より高く突き上げる / 左手＝頭より高く突き上げる / 体＝正面（軽く飛び跳ねる） / 足＝地面から少し浮く",
     "両手を突き上げて飛び跳ねる 足元に短い動線", ""),
    ("感情", "びっくり", "驚き",
     "右手＝頬に当てる / 左手＝頬に当てる / 体＝正面 / 足＝描かない",
     "両手を頬に当てて驚く 頭上に驚きの線3本", ""),
    ("感情", "つらい…", "泣き",
     "右手＝机の上に伸ばす / 左手＝机の上に伸ばす / 体＝机に突っ伏す / 足＝描かない",
     "机に突っ伏す 机は無地", ""),
    ("感情", "ねむい", "眠い",
     "右手＝口元を覆う / 左手＝自然に下ろす / 体＝正面 / 足＝描かない",
     "大きくあくびをする", ""),
    ("感情", "やったー！", "満面の笑み",
     "右手＝握りこぶしを突き上げる / 左手＝握りこぶしを突き上げる / 体＝正面からやや後傾 / 足＝描かない",
     "両手を突き上げて喜ぶ", ""),
    ("応援", "がんばれ！", "応援",
     "右手＝握りこぶしを前方に押し出す / 左手＝握りこぶしを胸の前に構える / 体＝正面からやや前傾 / 足＝描かない",
     "こぶしを前に出して応援", ""),
    ("応援", "いけるいける", "得意げ",
     "右手＝相手の背を押すしぐさで前に出す / 左手＝腰に当てる / 体＝やや斜め / 足＝描かない",
     "背中を押すしぐさ", ""),
    ("応援", "ナイス！", "にっこり",
     "右手＝指を鳴らすしぐさ / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "指を鳴らして褒める", ""),
    ("応援", "無理しないで", "心配そう（困り顔寄り）",
     "右手＝相手の肩に置くしぐさで前に出す / 左手＝胸の前に添える / 体＝やや前傾 / 足＝描かない",
     "肩に手を置くしぐさ", ""),
    ("締め", "お先に失礼〜", "にっこり",
     "右手＝顔の横で手を振る / 左手＝かばんの持ち手を握る / 体＝やや斜め（歩き出す姿勢） / 足＝歩いている",
     "かばんを持って手を振る かばんは無地", ""),
    ("締め", "また明日", "にっこり",
     "右手＝胸の高さで小さく手を振る / 左手＝自然に下ろす / 体＝正面 / 足＝描かない",
     "小さく手を振る", ""),
    ("締め", "おやすみ", "眠い（目を閉じる）",
     "右手＝頬に添える / 左手＝自然に下ろす / 体＝正面（頭をかたむける） / 足＝描かない",
     "頬に手を添えて眠る仕草", ""),
    ("締め", "今日は／ここまで！", "得意げ",
     "右手＝ノートパソコンの蓋を閉じる / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "ノートパソコンを閉じて締める", "セリフは2行に分けて配置"),
    ("ネタ", "それAIで／いけるっしょ", "得意げ",
     "右手＝人差し指を立てて顔の横に出す / 左手＝腰に当てる / 体＝正面（片目を閉じる） / 足＝描かない",
     "指を立ててウインク キャラクターの看板セリフ", "セリフは2行に分けて配置"),
    ("ネタ", "はい、時短！", "満面の笑み",
     "右手＝ストップウォッチを止めるしぐさ / 左手＝腰に当てる / 体＝正面 / 足＝描かない",
     "ストップウォッチを止める 小物は無地で文字を描かない", ""),
    ("ネタ", "自動化しよ？", "にっこり",
     "右手＝足元の小型ロボットを指さす / 左手＝腰に当てる / 体＝やや斜め / 足＝描かない",
     "小型AIロボットを指さす ロボットは白と水色の丸い形 文字は描かない", "追加キャラクターあり"),
]

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


def make_filename(number):
    """
    番号から、対応するファイル名を作ります。

    例: 1 -> stamp_001.png
    """
    return "{}_{}{}".format(
        FILENAME_PREFIX, str(number).zfill(FILENAME_DIGITS), FILENAME_EXTENSION
    )


def build_category_list(rows):
    """
    行数に応じたカテゴリーの並びを作ります。

    40行なら、第4章の配分表どおりに並べます。
    40行以外なら、配分の比率を保ったまま調整します。
    """
    total_plan = sum(count for _name, count in CATEGORY_PLAN)

    if rows == total_plan:
        # 40行の場合は配分表どおり
        categories = []
        for name, count in CATEGORY_PLAN:
            categories.extend([name] * count)
        return categories

    # 40行以外の場合は、比率を保って割り当てる
    categories = []
    for name, count in CATEGORY_PLAN:
        allocated = max(1, round(count * rows / total_plan))
        categories.extend([name] * allocated)

    # 端数を調整する
    if len(categories) > rows:
        categories = categories[:rows]
    while len(categories) < rows:
        categories.append(CATEGORY_PLAN[-1][0])

    return categories


def build_sample_data(rows):
    """
    サンプルデータ（アイナのセリフ）を使って、行データを作ります。
    """
    data = []
    for i in range(rows):
        number = i + 1
        if i < len(SAMPLE_ROWS):
            category, text, emotion, pose, prompt, notes = SAMPLE_ROWS[i]
        else:
            # 40行を超える場合は空欄で埋める
            categories = build_category_list(rows)
            category = categories[i] if i < len(categories) else ""
            text = ""
            emotion = ""
            pose = ""
            prompt = ""
            notes = ""

        data.append(
            {
                "number": number,
                "category": category,
                "text": text,
                "emotion": emotion,
                "pose": pose,
                "image_prompt": prompt,
                "status": INITIAL_STATUS,
                "filename": make_filename(number),
                "notes": notes,
            }
        )
    return data


def build_empty_data(rows):
    """
    空のテンプレートとして、行データを作ります。

    カテゴリー、番号、ファイル名だけを埋めておきます。
    セリフは自分で入力してもらう形です。
    """
    categories = build_category_list(rows)
    data = []
    for i in range(rows):
        number = i + 1
        data.append(
            {
                "number": number,
                "category": categories[i] if i < len(categories) else "",
                "text": "",
                "emotion": "",
                "pose": "",
                "image_prompt": "",
                "status": INITIAL_STATUS,
                "filename": make_filename(number),
                "notes": "",
            }
        )
    return data


def backup_existing(path):
    """
    既存のファイルがある場合、バックアップを作ります。

    上書きで作業内容を失わないための処理です。

    戻り値:
        バックアップ先のパス（バックアップしなかった場合は None）
    """
    if not os.path.exists(path):
        return None

    base, ext = os.path.splitext(path)
    backup_path = base + "_backup" + ext

    # 既にバックアップがある場合は、番号を付けて重複を避ける
    counter = 2
    while os.path.exists(backup_path):
        backup_path = "{}_backup{}{}".format(base, counter, ext)
        counter += 1

    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except OSError as e:
        raise OSError("バックアップを作成できませんでした（{}）".format(e))


def write_csv(path, data):
    """
    CSVファイルを書き出します。

    encoding="utf-8-sig" を指定すると、UTF-8 BOM付きで保存されます。
    これでExcelで開いても文字化けしにくくなります。

    newline="" は、Windowsで空行が入るのを防ぐための指定です。
    """
    folder = os.path.dirname(os.path.abspath(path))
    try:
        if folder:
            os.makedirs(folder, exist_ok=True)
    except OSError as e:
        raise OSError("出力先のフォルダを作成できませんでした（{}）".format(e))

    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
    except PermissionError:
        raise PermissionError(
            "ファイルに書き込めませんでした。\n"
            "        Excelなどで {} を開いていませんか。\n"
            "        開いている場合は閉じてから、もう一度実行してください。".format(
                os.path.basename(path)
            )
        )
    except OSError as e:
        raise OSError("ファイルに書き込めませんでした（{}）".format(e))


def print_summary(data, path, backup_path, is_empty):
    """処理結果を表示します。"""
    print("=" * LINE_WIDTH)
    print(" CSV作成完了")
    print("=" * LINE_WIDTH)
    print("出力先　　: {}".format(os.path.abspath(path)))
    print("行数　　　: {} 行（ヘッダー行を除く）".format(len(data)))
    print("文字コード: UTF-8 BOM付き（Excelで開いても文字化けしにくい形式）")
    print("内容　　　: {}".format("空のテンプレート" if is_empty else "サンプル入り"))

    if backup_path:
        print()
        print("既存のファイルがあったため、バックアップを作成しました。")
        print("  {}".format(os.path.abspath(backup_path)))

    # カテゴリーごとの件数
    print()
    print("カテゴリーごとの件数:")
    counts = {}
    order = []
    for row in data:
        c = row["category"]
        if c not in counts:
            counts[c] = 0
            order.append(c)
        counts[c] += 1
    for c in order:
        print("  {:<10} {} 件".format(c, counts[c]))

    # 文字数の確認（サンプル入りの場合のみ）
    if not is_empty:
        long_texts = [
            (row["number"], row["text"])
            for row in data
            if row["text"] and len(row["text"]) >= 9
        ]
        if long_texts:
            print()
            print("9文字以上のセリフ（2行に分けることを検討してください）:")
            for number, text in long_texts:
                print("  No.{:<3} {} （{}文字）".format(number, text, len(text)))

    print()
    print("=" * LINE_WIDTH)
    print()
    print("次の手順:")
    print("  1. CSVをExcelまたはスプレッドシートで開く")
    print("  2. text（セリフ）を自分の内容に書き換える")
    print("  3. emotion（表情）と pose（ポーズ）を埋める")
    print("  4. 画像ができたら status を generated / edited / done に更新する")


def main():
    """メインの処理。"""
    setup_console()

    parser = argparse.ArgumentParser(
        description="LINEスタンプのセリフ管理用CSVを作成します（UTF-8 BOM付き）。"
    )
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT,
        help="出力先のファイル（既定: {}）".format(DEFAULT_OUTPUT),
    )
    parser.add_argument(
        "--rows", "-r", type=int, default=DEFAULT_ROWS,
        help="行数（既定: {}）".format(DEFAULT_ROWS),
    )
    parser.add_argument(
        "--empty", "-e", action="store_true",
        help="セリフを空にして、枠だけを出力する",
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="既存ファイルがあっても、バックアップを取って上書きする",
    )
    args = parser.parse_args()

    # --- 入力の検証 ---
    if args.rows < 1 or args.rows > 999:
        print("エラー: --rows は 1 〜 999 の範囲で指定してください。")
        return 1

    path = args.output

    # --- 既存ファイルの確認 ---
    backup_path = None
    if os.path.exists(path):
        if not args.force:
            print("注意: 既にファイルが存在します。")
            print("  {}".format(os.path.abspath(path)))
            print()
            print("作業中の内容を失わないため、そのままでは上書きしません。")
            print()
            print("上書きする場合は、--force を付けて実行してください。")
            print("バックアップ（_backup 付きのファイル）を自動で作成します。")
            print()
            print("  例: python create_csv.py --output {} --force".format(path))
            return 1

        try:
            backup_path = backup_existing(path)
        except OSError as e:
            print("エラー: {}".format(e))
            return 1

    # --- データを作る ---
    try:
        if args.empty:
            data = build_empty_data(args.rows)
        else:
            data = build_sample_data(args.rows)
    except Exception as e:
        print("エラー: データの作成に失敗しました（{}）".format(e))
        return 1

    # --- 書き出す ---
    try:
        write_csv(path, data)
    except PermissionError as e:
        print("エラー: {}".format(e))
        return 1
    except OSError as e:
        print("エラー: {}".format(e))
        return 1

    print_summary(data, path, backup_path, args.empty)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print("中断しました。")
        sys.exit(130)
