"""
🧠📸 今日のホット雑学ランキング → Instagram 自動投稿スクリプト
GitHub Actions で1日数回、自動実行されます。

【情報収集の流れ】
  1. Google Trends RSS  → 日本の今日のトレンドキーワード取得
  2. Wikipedia API      → 各キーワードの記事概要から雑学ポイント抽出
  3. Wikipedia 今日の出来事 → 今日の歴史的出来事を補完
  4. フォールバック固定プール → 取得失敗時の保険

すべて無料・APIキー不要。
"""

import os
import re
import sys
import random
import datetime

from PIL import Image, ImageDraw, ImageFont

import ig_utils
from ig_utils import check_credentials, upload_to_imgbb, post_to_instagram
from trivia_fetcher import build_hot_trivia_ranking


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
# 🖼️  画像生成 — 表スタイル
# ================================================================

RANK_ROW_BG = [
    '#FFF3CD',  # 1位
    '#E8E8E8',  # 2位
    '#FFDCB8',  # 3位
    '#DFFFF7',  # 4位
    '#DFFFF7',  # 5位
    '#F0F8FF',  # 6位
    '#F0F8FF',  # 7位
    '#F0F0F0',  # 8位
    '#F0F0F0',  # 9位
    '#EAEAEA',  # 10位
]

RANK_NUM_COLOR = [
    '#B8860B',  # 1位
    '#888888',  # 2位
    '#A0522D',  # 3位
    '#2E8B57',  # 4位
    '#2E8B57',  # 5位
    '#4169E1',  # 6位
    '#4169E1',  # 7位
    '#555555',  # 8位
    '#555555',  # 9位
    '#333333',  # 10位
]


def generate_trivia_table_image(theme: dict, date_label: str) -> Image.Image:
    """添付画像のような表形式ランキング画像を生成する。"""

    img = Image.new('RGB', (W, H), '#FFFFFF')
    draw = ImageDraw.Draw(img)

    title_font   = get_font(FONT_BLACK,  56)
    date_font    = get_font(FONT_MEDIUM, 28)
    header_font  = get_font(FONT_BOLD,   32)
    rank_font    = get_font(FONT_BLACK,  46)
    name_font    = get_font(FONT_BOLD,   30)
    reason_font  = get_font(FONT_REGULAR,27)
    footer_font  = get_font(FONT_BOLD,   32)

    # ── タイトル帯（赤） ──
    title_area_h = 148
    draw.rectangle([0, 0, W, title_area_h], fill='#E83030')

    title_text = for_image(theme['title'])
    tw = text_width(draw, title_text, title_font)
    tx = (W - tw) / 2
    ty = 18
    for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
        draw.text((tx + dx, ty + dy), title_text, font=title_font, fill='#8B0000')
    draw.text((tx, ty), title_text, font=title_font, fill='#FFFFFF')
    draw_centered_text(draw, date_label, date_font, W / 2, title_area_h - 32, '#FFE0E0')


    # ── テーブルヘッダー ──
    header_y = title_area_h + 2
    header_h = 52
    draw.rectangle([0, header_y, W, header_y + header_h], fill='#C8E6C9')

    col_rank_w  = 90
    col_name_w  = 250
    col_reason_x = col_rank_w + col_name_w + 12

    draw.text((18, header_y + 10), '順位', font=header_font, fill='#1B5E20')
    draw.text((col_rank_w + 10, header_y + 10), '項目', font=header_font, fill='#1B5E20')
    draw.text((col_reason_x, header_y + 10), '主な内容（簡潔に）', font=header_font, fill='#1B5E20')

    # ── 各行 ──
    row_start_y = header_y + header_h + 4
    items = theme['items'][:10]
    n_rows = len(items)
    footer_area_h = 110
    avail_h = H - row_start_y - footer_area_h
    row_h = avail_h // n_rows

    for i, (name, reason) in enumerate(items):
        ry = row_start_y + i * row_h
        bg = RANK_ROW_BG[i] if i < len(RANK_ROW_BG) else '#F5F5F5'
        draw.rectangle([0, ry, W, ry + row_h - 3], fill=bg)
        draw.line([(0, ry + row_h - 3), (W, ry + row_h - 3)], fill='#BDBDBD', width=1)

        rank_num = i + 1
        num_color = RANK_NUM_COLOR[i] if i < len(RANK_NUM_COLOR) else '#333333'

        rnum_str = f'{rank_num}位'
        rnum_font = get_font(FONT_BLACK, 38) if rank_num >= 10 else rank_font
        rnum_w = text_width(draw, rnum_str, rnum_font)
        draw.text((col_rank_w / 2 - rnum_w / 2, ry + (row_h - 46) / 2),
                  rnum_str, font=rnum_font, fill=num_color)

        draw.line([(col_rank_w, ry), (col_rank_w, ry + row_h - 3)], fill='#BDBDBD', width=1)
        draw.line([(col_rank_w + col_name_w, ry), (col_rank_w + col_name_w, ry + row_h - 3)],
                  fill='#BDBDBD', width=1)

        name_lines = wrap_text(draw, for_image(name), name_font, col_name_w - 10, max_lines=2)
        name_total_h = len(name_lines) * 34
        name_sy = ry + (row_h - name_total_h) / 2
        for li, ln in enumerate(name_lines):
            draw.text((col_rank_w + 6, name_sy + li * 34), ln, font=name_font, fill='#212121')

        reason_max_w = W - col_reason_x - 14
        reason_lines = wrap_text(draw, for_image(reason), reason_font, reason_max_w, max_lines=3)
        reason_total_h = len(reason_lines) * 32
        reason_sy = ry + (row_h - reason_total_h) / 2
        for li, ln in enumerate(reason_lines):
            draw.text((col_reason_x, reason_sy + li * 32), ln, font=reason_font, fill='#424242')

    # ── フッター ──
    footer_y = H - footer_area_h
    draw.rectangle([0, footer_y, W, H], fill='#FFF8E1')
    draw.line([(0, footer_y), (W, footer_y)], fill='#F9A825', width=3)

    footer_text = for_image(theme.get('footer_question', 'コメントで教えてください！'))
    draw_centered_text(draw, footer_text, footer_font, W / 2, footer_y + 20, '#E65100')

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
# 🚀 メイン実行
# ================================================================

def main():
    if not check_credentials():
        sys.exit(1)

    date_label = f"{NOW.year}年{NOW.month}月{NOW.day}日（{WEEKDAY_JP[NOW.weekday()]}）"

    print('🔍 今日のホット雑学を収集中...')
    theme = build_hot_trivia_ranking(max_items=10)
    theme['title'] = f'{NOW.month}月{NOW.day}日 今日のホット雑学'

    print(f'\n📌 テーマ: {theme["title"]}')
    print(f'📊 取得件数: {len(theme["items"])}件\n')
    for i, (name, reason) in enumerate(theme['items'], 1):
        print(f'  {i:2}位: {name} → {reason[:30]}')

    img = generate_trivia_table_image(theme, date_label)
    caption = build_trivia_caption(theme, date_label)

    print('\n☁️  画像をimgbbにアップロード中...')
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
