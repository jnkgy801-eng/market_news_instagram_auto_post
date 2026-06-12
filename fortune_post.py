"""
🔮📸 今日のラッキー星座ランキング / 雑学ランキング → Instagram 自動投稿スクリプト
GitHub Actions で1日数回、自動実行されます。

市場ニュース（main.py）とは別に、閲覧者の「気を引く・保存したくなる」
エンタメ系コンテンツ（星座ラッキーランキング・今日の雑学ランキング）を
画像化してInstagramに投稿します。
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

# 'zodiac'（星座ラッキーランキング） / 'trivia'（今日の雑学ランキング） / 'random'
CONTENT_TYPE = os.environ.get('FORTUNE_CONTENT_TYPE', 'random')

JST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(JST)
TODAY_STR = NOW.strftime('%Y-%m-%d')

W, H = 1080, 1080

FONT_DIR = '/usr/share/fonts/opentype/noto'
FONT_BLACK   = f'{FONT_DIR}/NotoSansCJK-Black.ttc'
FONT_BOLD    = f'{FONT_DIR}/NotoSansCJK-Bold.ttc'
FONT_MEDIUM  = f'{FONT_DIR}/NotoSansCJK-Medium.ttc'
FONT_REGULAR = f'{FONT_DIR}/NotoSansCJK-Regular.ttc'

WEEKDAY_JP = ['月', '火', '水', '木', '金', '土', '日']


# ================================================================
# 🗂️  コンテンツデータ
# ================================================================

ZODIAC_SIGNS = [
    '牡羊座', '牡牛座', '双子座', '蟹座', '獅子座', '乙女座',
    '天秤座', '蠍座', '射手座', '山羊座', '水瓶座', '魚座',
]

LUCKY_COLORS = [
    'レッド', 'ブルー', 'イエロー', 'グリーン', 'ピンク', 'パープル',
    'ホワイト', 'ゴールド', 'オレンジ', 'ターコイズ', 'シルバー',
    'ラベンダー', 'ベージュ', 'ネイビー', 'ミント', 'ワインレッド',
]

LUCKY_ITEMS = [
    'お気に入りのマグカップ', '手帳', '腕時計', 'ハンドクリーム',
    '観葉植物', '香水', 'お守り', 'スマホケース', 'アロマキャンドル',
    'ヘアアクセサリー', '読みかけの本', '推しグッズ', '新しい文房具',
    'お財布', 'イヤホン', '折り紙鶴', 'キーホルダー', 'コインケース',
]

LUCKY_ACTIONS = [
    '朝日を浴びながら深呼吸する', '部屋の掃除をしてスッキリさせる',
    '気になっていた人に連絡してみる', 'いつもと違う道で帰る',
    'お気に入りの音楽を聴く', '少し早起きしてみる',
    '感謝の気持ちを言葉にする', '新しいことに挑戦してみる',
    'カフェでひと息つく', '自然の多い場所を歩く',
    '誰かの話をじっくり聞く', '部屋に花を飾る',
]

# 1位〜12位ごとの運勢コメント
RANK_COMMENTS = [
    '絶好調！何をやってもうまくいく、まさに無双の一日✨',
    '好調の波に乗れる日。チャンスを逃さずキャッチして🍀',
    '行動すればするだけ良いことが返ってくる予感',
    '周囲との縁が深まり、嬉しい知らせが届きそう',
    'コツコツ努力してきたことが少しずつ形になる日',
    '安定した一日。いつも通りのペースで大丈夫',
    '小さなラッキーが見つかる、ほっこり過ごせる日',
    '気分の波があるかも。深呼吸してリラックスを',
    '焦らずゆっくりがキーワード。無理は禁物',
    '今日は守りの日。慎重な行動が吉と出る',
    '少しお疲れモード？早めの休息でリセットしよう',
    '充電期間。明日への準備をする一日に',
]

# ── 今日の雑学（豆知識）プール ───────────────────────────────────
TRIVIA_FACTS = [
    'バナナは植物学的には「ベリー」の一種に分類される',
    '蜂蜜は正しく保存すれば数千年経っても食べられる',
    'タコには脳が9つあり、各足にも小さな脳がある',
    'フラミンゴの羽が赤いのはエビなど食べ物の色素が原因',
    'ペンギンの多くは南極周辺に生息し、北極にはいない',
    '人間の鼻は1兆種類近いにおいを区別できるとされる',
    'カタツムリは環境が悪いと数年間眠ることがある',
    '雷の温度は太陽の表面温度より高くなることがある',
    'シロナガスクジラの心臓は小型車ほどの大きさになる',
    '人は1日に約1万5000〜2万回まばたきしている',
    '「ありがとう」は「有り難い」、つまり"めったにない"が語源',
    'イルカは脳を半分ずつ休ませながら眠る',
    'ラクダのこぶに入っているのは水ではなく脂肪',
    '富士山は今も活火山に分類されている',
    '1万円札の肖像は2024年から渋沢栄一になった',
    '世界初の切手はイギリスで発行された「ペニー・ブラック」',
    'ゾウは鏡に映った自分を認識できる数少ない動物のひとつ',
    'カエルの多くは皮膚から直接呼吸することができる',
    'ハチドリは唯一、後ろ向きに飛べる鳥として知られる',
    '寿司の起源は東南アジア生まれの保存食「なれずし」とされる',
    '江戸時代の握り寿司は、今で言うファストフードだった',
    '牛は前足の構造上、階段をうまく下りられない',
    'りんごは果肉の約25%が空気でできており水に浮く',
    'スズメバチの女王は冬を越し、春に新しい巣をひとりで作り始める',
    'ピーナッツはナッツではなくマメ科の植物の種子',
    'イチゴはレモンよりビタミンCが多く含まれている',
    '心臓は一生のうちに約20億回拍動するといわれる',
    '月は1年に約3.8cmずつ地球から遠ざかっている',
    '雪の結晶は同じ形のものが存在しないといわれる',
    'コアラの指紋は人間のものと非常によく似ている',
    'カンガルーは構造上、後ろ向きに歩くことができない',
    'タツノオトシゴは雄がお腹の袋で卵を育てて出産する',
    '蚊は人が出す二酸化炭素のにおいを感知して近づいてくる',
    '世界で最も消費されている飲み物は水に次いでお茶といわれる',
    '満月の夜は地球から見て月の同じ面しか見えない',
    'チーターは加速力が非常に高く、わずか3秒で時速100km近くに達する',
    '人間の骨は生まれたときは約300個あるが成長とともに減って206個になる',
    '北極星（ポラリス）は実は1つではなく連星系である',
    'キリンの鳴き声は非常に低周波で人にはほとんど聞こえない',
    'コーヒーの木に実る果実は赤く、見た目はチェリーに似ている',
    '南極大陸は世界最大の「砂漠」に分類されることがある',
    '人間の体内では1日に数百万個の細胞が新しく作られている',
    '虹は厳密には円形をしているが、地面に隠れて半円にしか見えない',
    'タコの墨はイカの墨に比べて粘り気が少なく、逃げるための煙幕に近い',
    '世界一硬い天然物質はダイヤモンドだが、加工品にはさらに硬いものもある',
    '猫の鼻紋（鼻のしわ模様）は人間の指紋のように一匹ごとに異なる',
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
    '\U0001F000-\U0001FFFF'  # 絵文字全般
    '\U00002600-\U000027BF'  # その他記号・絵文字
    '\U00002190-\U000021FF'  # 矢印
    '\U00002B00-\U00002BFF'  # 記号・矢印
    '\U0000FE00-\U0000FE0F'  # 異字体セレクタ
    ']+', flags=re.UNICODE)


def for_image(text):
    """Noto Sans CJKに存在しない絵文字等を画像描画用に取り除く。"""
    return _EMOJI_PATTERN.sub('', text).strip()


def vertical_gradient(w, h, top_rgb, bottom_rgb):
    img = Image.new('RGB', (w, h), top_rgb)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * ratio)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * ratio)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img, draw


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


def draw_rank_badge(draw, cx, cy, radius, rank, fill, text_fill='#1a1a2e', font=None):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)
    label = str(rank)
    if font is None:
        font = get_font(FONT_BLACK, int(radius * 1.2))
    bbox = draw.textbbox((0, 0), label, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), label, font=font, fill=text_fill)


def scatter_stars(draw, w, h, rng, count=70, top_area=720):
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, top_area)
        size = rng.choice([1, 1, 1, 2, 2, 3])
        alpha = rng.choice(['#ffffff', '#cfd8ff', '#9aa6e8'])
        draw.ellipse([x, y, x + size, y + size], fill=alpha)


# ================================================================
# 🔮 星座ラッキーランキング
# ================================================================

def build_zodiac_data(seed):
    rng = random.Random(seed)
    order = ZODIAC_SIGNS[:]
    rng.shuffle(order)

    details = []
    for i, sign in enumerate(order):
        rank = i + 1
        item = {
            'rank': rank,
            'sign': sign,
            'comment': RANK_COMMENTS[i],
        }
        if rank <= 3:
            item['color'] = rng.choice(LUCKY_COLORS)
            item['lucky_item'] = rng.choice(LUCKY_ITEMS)
            item['action'] = rng.choice(LUCKY_ACTIONS)
        details.append(item)
    return details


RANK_MEDAL_COLORS = {1: '#FFD45E', 2: '#D9DEE8', 3: '#E3A06A'}


def generate_zodiac_image(data, date_label):
    img, draw = vertical_gradient(W, H, (26, 16, 64), (61, 31, 110))
    rng = random.Random(TODAY_STR + '-stars')
    scatter_stars(draw, W, H, rng)

    title_font = get_font(FONT_BLACK, 56)
    date_font  = get_font(FONT_MEDIUM, 30)
    name_font  = get_font(FONT_BOLD, 46)
    sub_font   = get_font(FONT_REGULAR, 28)
    list_font  = get_font(FONT_MEDIUM, 32)
    rank_font  = get_font(FONT_BOLD, 28)

    draw_centered_text(draw, '今日の星座ラッキーランキング', title_font, W / 2, 48, '#ffffff')
    draw_centered_text(draw, date_label, date_font, W / 2, 118, '#c9b8ff')

    # ── TOP3 カード ─────────────────────────────────────────────
    card_x0, card_x1 = 50, W - 50
    card_h = 150
    card_gap = 14
    y = 175
    for item in data[:3]:
        rank = item['rank']
        draw.rounded_rectangle([card_x0, y, card_x1, y + card_h], radius=24,
                                fill=(255, 255, 255, 255), outline=None)
        # 半透明感を出すため少し暗めの白
        overlay = Image.new('RGB', (card_x1 - card_x0, card_h), (255, 255, 255))
        img.paste(overlay, (card_x0, y))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([card_x0, y, card_x1, y + card_h], radius=24, fill='#ffffff')

        badge_cx, badge_cy, radius = card_x0 + 80, y + card_h / 2, 44
        draw_rank_badge(draw, badge_cx, badge_cy, radius, rank,
                         fill=RANK_MEDAL_COLORS[rank], text_fill='#2a1a52',
                         font=get_font(FONT_BLACK, 50))

        text_x = card_x0 + 150
        draw.text((text_x, y + 18), item['sign'], font=name_font, fill='#2a1a52')
        info = f"ラッキーカラー: {item['color']} ／ ラッキーアイテム: {item['lucky_item']}"
        draw.text((text_x, y + 72), info, font=sub_font, fill='#5b4a8a')
        comment_lines = wrap_text(draw, for_image(item['comment']), sub_font, card_x1 - text_x - 20, max_lines=1)
        draw.text((text_x, y + 108), comment_lines[0], font=sub_font, fill='#9b8bd0')

        y += card_h + card_gap

    # ── 4〜12位 リスト ───────────────────────────────────────────
    list_top = y + 10
    list_bottom = H - 90

    draw_centered_text(draw, '― 4位 〜 12位 ―', sub_font, W / 2, list_top - 8, '#c9b8ff')
    list_top += 36
    row_h = (list_bottom - list_top) / 9
    rank_label_font = get_font(FONT_BOLD, 28)

    for idx, item in enumerate(data[3:]):
        ry = list_top + idx * row_h
        cy = ry + row_h / 2
        draw.text((60, cy - 18), f"{item['rank']}位", font=rank_label_font, fill='#c9b8ff')
        draw.text((150, cy - 18), item['sign'], font=list_font, fill='#ffffff')
        comment_lines = wrap_text(draw, for_image(item['comment']), get_font(FONT_REGULAR, 24), W - 380 - 60, max_lines=1)
        draw.text((380, cy - 14), comment_lines[0], font=get_font(FONT_REGULAR, 24), fill='#a99adf')

    # ── フッター ────────────────────────────────────────────────
    footer_font = get_font(FONT_MEDIUM, 30)
    draw.line([(60, H - 70), (W - 60, H - 70)], fill='#5b4a8a', width=2)
    draw_centered_text(draw, for_image('保存して毎日チェックしてね🌙'), footer_font, W / 2, H - 56, '#e6defb')

    return img


def build_zodiac_caption(data, date_label):
    lines = [f'🔮 今日（{date_label}）の星座ラッキーランキング！\n']
    for item in data:
        rank = item['rank']
        if rank <= 3:
            lines.append(
                f"{rank}位：{item['sign']}\n"
                f"　 ラッキーカラー → {item['color']}\n"
                f"　 ラッキーアイテム → {item['lucky_item']}\n"
                f"　 ラッキーアクション → {item['action']}\n"
                f"　 {item['comment']}\n"
            )
        else:
            lines.append(f"{rank}位：{item['sign']}　{item['comment']}")

    body = '\n'.join(lines)
    hashtags = (
        '\n\n#星座占い #今日の運勢 #星座ランキング #ラッキー星座 '
        '#占い好き #ホロスコープ #運勢ランキング #今日のラッキーアイテム'
    )
    note = '\n\n⚠️ 占いはエンタメ目的です。一日を楽しく過ごすヒントにしてくださいね😊'
    return body + note + hashtags


# ================================================================
# 🧠 今日の雑学ランキング
# ================================================================

def build_trivia_data(seed):
    rng = random.Random(seed)
    facts = TRIVIA_FACTS[:]
    rng.shuffle(facts)
    chosen = facts[:5]
    return [{'rank': i + 1, 'fact': fact} for i, fact in enumerate(chosen)]


RANK_BADGE_COLORS = {1: '#FFD45E', 2: '#D9DEE8', 3: '#E3A06A', 4: '#7FD8C8', 5: '#7FD8C8'}


def generate_trivia_image(data, date_label):
    img, draw = vertical_gradient(W, H, (12, 30, 38), (38, 78, 96))

    title_font = get_font(FONT_BLACK, 54)
    date_font  = get_font(FONT_MEDIUM, 30)
    fact_font  = get_font(FONT_BOLD, 34)

    draw_centered_text(draw, '今日の雑学ランキング TOP5', title_font, W / 2, 40, '#ffffff')
    draw_centered_text(draw, date_label, date_font, W / 2, 104, '#a9eee0')

    card_x0, card_x1 = 50, W - 50
    card_h = 167
    card_gap = 8
    y = 150

    for item in data:
        draw.rounded_rectangle([card_x0, y, card_x1, y + card_h], radius=22, fill='#ffffff')
        badge_cx, badge_cy, radius = card_x0 + 80, y + card_h / 2, 46
        draw_rank_badge(draw, badge_cx, badge_cy, radius, item['rank'],
                        fill=RANK_BADGE_COLORS.get(item['rank'], '#7FD8C8'),
                        text_fill='#0c1e26', font=get_font(FONT_BLACK, 52))

        text_x = card_x0 + 150
        lines = wrap_text(draw, for_image(item['fact']), fact_font, card_x1 - text_x - 30, max_lines=3)
        line_h = 44
        total_h = line_h * len(lines)
        start_y = y + (card_h - total_h) / 2
        for li, ln in enumerate(lines):
            draw.text((text_x, start_y + li * line_h), ln, font=fact_font, fill='#123238')

        y += card_h + card_gap

    footer_font = get_font(FONT_MEDIUM, 30)
    draw.line([(60, H - 56), (W - 60, H - 56)], fill='#a9eee0', width=2)
    draw_centered_text(draw, for_image('保存して友達にも教えてあげよう📚'), footer_font, W / 2, H - 44, '#e6fbf6')

    return img


def build_trivia_caption(data, date_label):
    lines = [f'🧠 今日（{date_label}）の雑学ランキング TOP5！\n']
    for item in data:
        lines.append(f"{item['rank']}位：{item['fact']}")
    body = '\n'.join(lines)
    hashtags = (
        '\n\n#雑学 #今日の雑学 #トリビア #面白い知識 #知ってた '
        '#雑学ランキング #暇つぶし #へぇボタン'
    )
    note = '\n\nどれが一番「へぇ」でしたか？コメントで教えてください👇'
    return body + note + hashtags


# ================================================================
# 🚀 メイン実行
# ================================================================

def main():
    if not check_credentials():
        sys.exit(1)

    date_label = f"{NOW.year}年{NOW.month}月{NOW.day}日（{WEEKDAY_JP[NOW.weekday()]}）"

    content_type = CONTENT_TYPE
    if content_type == 'random':
        rng = random.Random(NOW.strftime('%Y-%m-%d-%H'))
        content_type = rng.choice(['zodiac', 'trivia'])

    print(f'📌 コンテンツタイプ: {content_type}')

    if content_type == 'trivia':
        data = build_trivia_data(TODAY_STR + '-trivia')
        img = generate_trivia_image(data, date_label)
        caption = build_trivia_caption(data, date_label)
    else:
        data = build_zodiac_data(TODAY_STR + '-zodiac')
        img = generate_zodiac_image(data, date_label)
        caption = build_zodiac_caption(data, date_label)

    print('☁️  画像をimgbbにアップロード中...')
    if not ig_utils.IMGBB_API_KEY:
        print('❌ IMGBB_API_KEY が設定されていません。画像投稿には imgbb の設定が必要です。')
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
