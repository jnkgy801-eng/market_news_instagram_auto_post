"""
🧠📸 今日の雑学ランキング → Instagram 自動投稿スクリプト
GitHub Actions で1日数回、自動実行されます。

市場ニュース（main.py）とは別に、閲覧者の「気を引く・保存したくなる」
エンタメ系コンテンツ（今日の雑学ランキング）を画像化してInstagramに投稿します。
"""

import os
import re
import sys
import random
import datetime
import textwrap

from PIL import Image, ImageDraw, ImageFont

import ig_utils
from ig_utils import check_credentials, upload_to_imgbb, post_to_instagram


# ================================================================
# ⚙️  設定
# ================================================================

JST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(JST)
TODAY_STR = NOW.strftime('%Y-%m-%d')

W, H = 1080, 1350   # Instagram縦型（4:5比率）

FONT_DIR = '/usr/share/fonts/opentype/noto'
FONT_BLACK   = f'{FONT_DIR}/NotoSansCJK-Black.ttc'
FONT_BOLD    = f'{FONT_DIR}/NotoSansCJK-Bold.ttc'
FONT_MEDIUM  = f'{FONT_DIR}/NotoSansCJK-Medium.ttc'
FONT_REGULAR = f'{FONT_DIR}/NotoSansCJK-Regular.ttc'

WEEKDAY_JP = ['月', '火', '水', '木', '金', '土', '日']


# ================================================================
# 🗂️  コンテンツデータ — 雑学ランキング用テーマ一覧
# ================================================================

TRIVIA_THEMES = [
    {
        "title": "迷う駅ランキング",
        "unit": "駅",
        "items": [
            ("渋谷駅",   "再開発で構造が複雑&通路が頻繁に変わる。"),
            ("新宿駅",   "路線・出口が多すぎて迷宮レベル。"),
            ("大手町駅", "地下が広く出口も多く、距離が長い。"),
            ("東京駅",   "路線間が遠く、特に京葉線が別棟レベル。"),
            ("横浜駅",   "路線・地下道・ビル連絡が入り組みすぎ。"),
            ("池袋駅",   "路線が密集し、出口の方角も混乱しやすい。"),
            ("名古屋駅", "路線ごとの距離が遠く、地下街も迷路。"),
            ("梅田駅",   "「梅田」が複数あり、JR大阪駅との連携も複雑。"),
            ("天神駅",   "路線間で地上移動が多く、分かりづらい。"),
            ("北千住駅", "路線間の乗り換え距離が長く、構造も複雑。"),
        ],
        "hashtags": "#迷う駅 #駅ランキング #電車 #乗り換え #鉄道 #雑学 #豆知識 #ランキング",
        "footer_question": "あなたはどこで迷った？コメントで教えて！",
    },
    {
        "title": "日本の長寿企業ランキング",
        "unit": "位",
        "items": [
            ("金剛組（大阪）",     "578年創業。世界最古の建設会社。"),
            ("池坊華道会（京都）", "587年創業。生け花の元祖。"),
            ("西山温泉 慶雲館",   "705年創業。世界最古のホテル。"),
            ("古まん（兵庫）",     "717年創業。有馬温泉の旅館。"),
            ("善吾楼（石川）",     "718年創業。粟津温泉の旅館。"),
            ("源泉亭 湧駒荘",     "1674年創業。北海道の老舗旅館。"),
            ("虎屋（東京）",       "室町時代後期創業の和菓子の老舗。"),
            ("住友グループ",       "1590年代に銅精錬業として創業。"),
            ("三井グループ",       "1673年創業、日本最大財閥のルーツ。"),
            ("松坂屋（名古屋）",   "1611年創業。日本最古のデパート。"),
        ],
        "hashtags": "#長寿企業 #老舗 #日本史 #雑学 #豆知識 #ランキング #歴史",
        "footer_question": "知ってた？コメントで教えてね！",
    },
    {
        "title": "体に関するびっくり雑学",
        "unit": "位",
        "items": [
            ("まばたき回数",    "1日に約1万5000〜2万回もしている。"),
            ("骨の数の変化",    "赤ちゃん300個→大人になると206個に減る。"),
            ("心臓の拍動数",    "一生で約20億回拍動するといわれる。"),
            ("嗅覚の識別力",    "人間は1兆種類近いにおいを区別できる。"),
            ("細胞の新陳代謝",  "1日に数百万個の細胞が新しく生まれる。"),
            ("体の水分量",      "体重の約60%が水分で構成されている。"),
            ("脳の消費エネルギー", "脳は体全体のエネルギーの約20%を消費。"),
            ("指紋の唯一性",    "同一の指紋を持つ人間は存在しない。"),
            ("胃酸の強さ",      "胃酸のpHは1〜2。金属も溶かせる酸性度。"),
            ("爪の成長速度",    "足の爪より手の爪の方が約3倍早く伸びる。"),
        ],
        "hashtags": "#体の雑学 #人体 #豆知識 #びっくり #雑学 #ランキング #知識",
        "footer_question": "どれが一番びっくりした？コメントで！",
    },
    {
        "title": "動物のびっくり雑学",
        "unit": "位",
        "items": [
            ("タコの脳",       "脳が9つあり、各足にも小さな脳がある。"),
            ("ハチドリの飛行", "唯一、後ろ向きに飛べる鳥として知られる。"),
            ("ゾウの自己認識", "鏡に映った自分を認識できる数少ない動物。"),
            ("イルカの睡眠",   "脳を半分ずつ休ませながら眠る。"),
            ("カンガルー",      "構造上、後ろ向きに歩くことができない。"),
            ("タツノオトシゴ", "雄がお腹の袋で卵を育てて出産する。"),
            ("フラミンゴの羽", "食べ物の色素（エビ等）が原因で赤くなる。"),
            ("コアラの指紋",   "人間のものと非常によく似ている。"),
            ("ラクダのこぶ",   "中に入っているのは水ではなく脂肪。"),
            ("チーターの加速", "わずか3秒で時速100km近くに達する。"),
        ],
        "hashtags": "#動物雑学 #豆知識 #動物 #びっくり #雑学 #ランキング #自然",
        "footer_question": "どの動物が一番好き？コメントで！",
    },
    {
        "title": "食べ物のびっくり雑学",
        "unit": "位",
        "items": [
            ("バナナの分類",   "植物学的には「ベリー」の一種に分類される。"),
            ("蜂蜜の保存性",  "正しく保存すれば数千年経っても食べられる。"),
            ("りんごの成分",  "果肉の約25%が空気でできており水に浮く。"),
            ("寿司の起源",    "東南アジア生まれの保存食「なれずし」が起源。"),
            ("イチゴのビタミンC", "レモンよりビタミンCが多く含まれる。"),
            ("ピーナッツの分類", "ナッツではなくマメ科植物の種子。"),
            ("お茶の消費量",  "水に次いで世界で最も消費される飲み物。"),
            ("コーヒーの実",  "赤い果実がなり、見た目はチェリーに似る。"),
            ("江戸の握り寿司", "今で言うファストフードとして庶民に親しまれた。"),
            ("1万円札の肖像", "2024年から渋沢栄一にデザイン変更された。"),
        ],
        "hashtags": "#食べ物雑学 #食の豆知識 #グルメ #トリビア #雑学 #ランキング",
        "footer_question": "どれが一番「へぇ」でした？コメントで！",
    },
    {
        "title": "宇宙・自然のびっくり雑学",
        "unit": "位",
        "items": [
            ("月の移動",        "月は1年に約3.8cmずつ地球から遠ざかっている。"),
            ("雷の温度",        "雷の温度は太陽の表面温度より高くなることがある。"),
            ("雪の結晶",        "同じ形の結晶は存在しないといわれる。"),
            ("北極星の正体",    "北極星（ポラリス）は実は連星系である。"),
            ("虹の形",          "厳密には円形だが地面に隠れて半円にしか見えない。"),
            ("南極の分類",      "南極大陸は世界最大の「砂漠」に分類されることがある。"),
            ("富士山の現状",    "富士山は今も活火山に分類されている。"),
            ("シロナガスクジラ", "心臓は小型車ほどの大きさになる。"),
            ("ダイヤモンドの硬さ", "天然物質で最も硬いが、加工品にはさらに硬いものもある。"),
            ("カタツムリの睡眠", "環境が悪いと数年間眠ることがある。"),
        ],
        "hashtags": "#宇宙雑学 #自然の不思議 #豆知識 #サイエンス #雑学 #ランキング",
        "footer_question": "一番びっくりしたのはどれ？コメントで！",
    },
]


# ================================================================
# 🔧 共通: 描画ヘルパー
# ================================================================

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


_EMOJI_PATTERN = re.compile(
    '['
    '\U0001F000-\U0001FFFF'
    '\U00002600-\U000027BF'
    '\U00002190-\U000021FF'
    '\U00002B00-\U00002BFF'
    '\U0000FE00-\U0000FE0F'
    ']+', flags=re.UNICODE)


def for_image(text):
    """Noto Sans CJKに存在しない絵文字等を画像描画用に取り除く。"""
    return _EMOJI_PATTERN.sub('', text).strip()


def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_text(draw, text, font, max_width, max_lines=None):
    """ピクセル幅に基づいて1文字単位で折り返す。"""
    lines, line = [], ''
    for ch in text:
        test = line + ch
        if text_width(draw, test, font) > max_width and line:
            lines.append(line)
            line = ch
        else:
            line = test
    if line:
        lines.append(line)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while text_width(draw, last + '…', font) > max_width and len(last) > 1:
            last = last[:-1]
        lines[-1] = last + '…'
    return lines


def draw_centered_text(draw, text, font, center_x, y, fill):
    w = text_width(draw, text, font)
    draw.text((center_x - w / 2, y), text, font=font, fill=fill)


# ================================================================
# 🖼️  画像生成 — 表スタイル（添付画像のようなレイアウト）
# ================================================================

# 順位ごとの色（1〜10位）
RANK_ROW_BG = [
    '#FFF3CD',   # 1位: 金系
    '#E8E8E8',   # 2位: 銀系
    '#FFDCB8',   # 3位: 銅系
    '#DFFFF7',   # 4位
    '#DFFFF7',   # 5位
    '#F0F8FF',   # 6位
    '#F0F8FF',   # 7位
    '#F0F0F0',   # 8位
    '#F0F0F0',   # 9位
    '#EAEAEA',   # 10位
]

RANK_NUM_COLOR = [
    '#B8860B',   # 1位
    '#888888',   # 2位
    '#A0522D',   # 3位
    '#2E8B57',   # 4位
    '#2E8B57',   # 5位
    '#4169E1',   # 6位
    '#4169E1',   # 7位
    '#555555',   # 8位
    '#555555',   # 9位
    '#333333',   # 10位
]


def generate_trivia_table_image(theme: dict, date_label: str) -> Image.Image:
    """
    添付画像のような表形式ランキング画像を生成する。

    レイアウト:
      ┌─────────────────────────────┐
      │  タイトル（赤ベタ・太字）         │
      │  日付ラベル（小）                │
      ├──┬──────┬────────────────────┤  ← ヘッダー行
      │順位│ 名称  │  主な理由（簡潔に）  │
      ├──┼──────┼────────────────────┤
      │  1│ xxx  │ yyy                  │
      │ …│  …   │  …                   │
      └──┴──────┴────────────────────┘
      │ フッター質問文                    │
    """

    img = Image.new('RGB', (W, H), '#FFFFFF')
    draw = ImageDraw.Draw(img)

    # ── フォント ──
    title_font   = get_font(FONT_BLACK,  60)
    date_font    = get_font(FONT_MEDIUM, 28)
    header_font  = get_font(FONT_BOLD,   32)
    rank_font    = get_font(FONT_BLACK,  46)
    name_font    = get_font(FONT_BOLD,   32)
    reason_font  = get_font(FONT_REGULAR,28)
    footer_font  = get_font(FONT_BOLD,   32)

    # ── タイトル領域（赤い帯） ──
    title_area_h = 160
    draw.rectangle([0, 0, W, title_area_h], fill='#E83030')

    # タイトルテキスト（白ふち + 白文字）
    title_text = for_image(theme['title'])
    tw = text_width(draw, title_text, title_font)
    tx = (W - tw) / 2
    ty = 28
    # 影
    for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (4, 0)]:
        draw.text((tx + dx, ty + dy), title_text, font=title_font, fill='#8B0000')
    draw.text((tx, ty), title_text, font=title_font, fill='#FFFFFF')

    # 日付（タイトル帯内）
    draw_centered_text(draw, date_label, date_font, W / 2, title_area_h - 36, '#FFE0E0')

    # ── テーブルヘッダー ──
    header_y = title_area_h + 2
    header_h = 52

    # ヘッダー背景（薄緑）
    draw.rectangle([0, header_y, W, header_y + header_h], fill='#C8E6C9')

    col_rank_w  = 90
    col_name_w  = 250
    col_reason_x = col_rank_w + col_name_w + 12

    # ヘッダーテキスト
    draw.text((18, header_y + 10), '順位', font=header_font, fill='#1B5E20')
    draw.text((col_rank_w + 10, header_y + 10), '名称' if theme['unit'] == '駅' else '項目',
              font=header_font, fill='#1B5E20')
    draw.text((col_reason_x, header_y + 10), '主な理由（簡潔に）', font=header_font, fill='#1B5E20')

    # ── 各行 ──
    row_start_y = header_y + header_h + 4
    items = theme['items'][:10]
    n_rows = len(items)
    # 残り高さを均等分割（フッター分を確保）
    footer_area_h = 110
    avail_h = H - row_start_y - footer_area_h
    row_h = avail_h // n_rows

    for i, (name, reason) in enumerate(items):
        ry = row_start_y + i * row_h
        bg = RANK_ROW_BG[i] if i < len(RANK_ROW_BG) else '#F5F5F5'
        draw.rectangle([0, ry, W, ry + row_h - 3], fill=bg)

        # 区切り線
        draw.line([(0, ry + row_h - 3), (W, ry + row_h - 3)], fill='#BDBDBD', width=1)

        rank_num = i + 1
        num_color = RANK_NUM_COLOR[i] if i < len(RANK_NUM_COLOR) else '#333333'

        # 順位数字
        rnum_str = f'{rank_num}位'
        rnum_font = get_font(FONT_BLACK, 40) if rank_num >= 10 else rank_font
        rnum_w = text_width(draw, rnum_str, rnum_font)
        draw.text((col_rank_w / 2 - rnum_w / 2, ry + (row_h - 48) / 2),
                  rnum_str, font=rnum_font, fill=num_color)

        # 縦線
        draw.line([(col_rank_w, ry), (col_rank_w, ry + row_h - 3)], fill='#BDBDBD', width=1)
        draw.line([(col_rank_w + col_name_w, ry), (col_rank_w + col_name_w, ry + row_h - 3)],
                  fill='#BDBDBD', width=1)

        # 駅名 / 項目名
        name_lines = wrap_text(draw, for_image(name), name_font, col_name_w - 10, max_lines=2)
        name_total_h = len(name_lines) * 36
        name_sy = ry + (row_h - name_total_h) / 2
        for li, ln in enumerate(name_lines):
            draw.text((col_rank_w + 6, name_sy + li * 36), ln, font=name_font, fill='#212121')

        # 理由
        reason_max_w = W - col_reason_x - 14
        reason_lines = wrap_text(draw, for_image(reason), reason_font, reason_max_w, max_lines=3)
        reason_total_h = len(reason_lines) * 34
        reason_sy = ry + (row_h - reason_total_h) / 2
        for li, ln in enumerate(reason_lines):
            draw.text((col_reason_x, reason_sy + li * 34), ln, font=reason_font, fill='#424242')

    # ── フッター（質問文＋吹き出し風） ──
    footer_y = H - footer_area_h
    draw.rectangle([0, footer_y, W, H], fill='#FFF8E1')
    draw.line([(0, footer_y), (W, footer_y)], fill='#F9A825', width=3)

    footer_text = for_image(theme.get('footer_question', 'コメントで教えてね！'))
    draw_centered_text(draw, footer_text, footer_font, W / 2, footer_y + 20, '#E65100')

    # サブテキスト
    sub_font2 = get_font(FONT_MEDIUM, 26)
    draw_centered_text(draw, 'コメントで教えてください！', sub_font2, W / 2, footer_y + 66, '#BF360C')

    return img


# ================================================================
# 📝 キャプション生成
# ================================================================

def build_trivia_caption(theme: dict, date_label: str) -> str:
    lines = [f'🧠 {date_label} の雑学ランキング\n']
    lines.append(f'【{theme["title"]}】\n')
    for i, (name, reason) in enumerate(theme['items'][:10]):
        lines.append(f'{i+1}位：{name}')
        lines.append(f'　→ {reason}')
    body = '\n'.join(lines)
    note = f'\n\n{theme.get("footer_question", "コメントで教えてください！")}'
    hashtags = f'\n\n{theme.get("hashtags", "#雑学 #豆知識 #ランキング")}'
    return body + note + hashtags


# ================================================================
# 🗓️  テーマ選択（日付ベースで毎日違うテーマを選ぶ）
# ================================================================

def pick_theme(seed: str) -> dict:
    rng = random.Random(seed)
    return rng.choice(TRIVIA_THEMES)


# ================================================================
# 🚀 メイン実行
# ================================================================

def main():
    if not check_credentials():
        sys.exit(1)

    date_label = f"{NOW.year}年{NOW.month}月{NOW.day}日（{WEEKDAY_JP[NOW.weekday()]}）"

    # 1日3回実行されるが、テーマは時間帯ごとに変える
    seed = NOW.strftime('%Y-%m-%d-%H')
    theme = pick_theme(seed)

    print(f'📌 テーマ: {theme["title"]}')

    img = generate_trivia_table_image(theme, date_label)
    caption = build_trivia_caption(theme, date_label)

    print('☁️  画像をimgbbにアップロード中...')
    if not ig_utils.IMGBB_API_KEY:
        print('❌ IMGBB_API_KEY が設定されていません。')
        sys.exit(1)

    image_url = upload_to_imgbb(img)
    if not image_url:
        print('❌ 画像のアップロードに失敗しました。')
        sys.exit(1)

    print(f'✅ アップロード成功: {image_url}')
    print('\n📤 Instagramへ投稿中...')
    post_to_instagram(image_url, caption)


if __name__ == '__main__':
    main()
