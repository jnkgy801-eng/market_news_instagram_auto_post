"""
📈📸 市場ニュース → Instagram 自動投稿スクリプト
GitHub Actions で4時間ごとに自動実行されます。
"""

import os
import sys
import subprocess

# ================================================================
# ⚙️  設定（環境変数から読み込み）
# ================================================================

ACCESS_TOKEN  = os.environ.get('META_ACCESS_TOKEN', '')
IG_USER_ID    = os.environ.get('INSTAGRAM_ACCOUNT_ID', '')
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', '')

if not ACCESS_TOKEN or not IG_USER_ID:
    print('❌ 環境変数 META_ACCESS_TOKEN / INSTAGRAM_ACCOUNT_ID が設定されていません。')
    sys.exit(1)

print('✅ 認証情報を読み込みました。')

# ── RSSフィード設定 ─────────────────────────────────────────────
RSS_FEEDS = {
    'Yahoo!ファイナンス': 'https://finance.yahoo.co.jp/rss/category/stock',
    'NHK経済':           'https://www.nhk.or.jp/rss/news/cat6.xml',
    'ロイター JP':        'https://feeds.reuters.com/reuters/JPBusinessNews',
    '日経新聞':           'https://www.nikkei.com/rss/news.rdf',
}

# ── 投稿設定 ────────────────────────────────────────────────────
POST_INDEX    = 0      # 投稿するニュースの番号（0 = 最初に取得したもの）
POST_ALL      = False  # True にすると取得した全ニュースを順番に投稿
INTERVAL      = 15     # 複数投稿時の待機秒数
NEWS_PER_FEED = 3      # 各RSSフィードから取得するニュース件数

HASHTAGS = '#市場ニュース #株式 #経済 #投資 #マーケット #finance #investing'
MAX_SUMMARY_CHARS = 200

# ================================================================
# 🔧 関数定義
# ================================================================

import feedparser
import requests
import re
import json
import time
import io
import base64
import urllib.parse
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

BASE_URL = 'https://graph.facebook.com/v19.0'


def clean_html(raw):
    return BeautifulSoup(raw or '', 'html.parser').get_text(separator=' ').strip()

def truncate(text, max_chars=MAX_SUMMARY_CHARS):
    text = re.sub(r'\s+', ' ', text).strip()
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + '…'

def extract_image_from_entry(entry):
    for key in ('media_content', 'media_thumbnail'):
        for item in getattr(entry, key, []):
            if item.get('url'):
                return item['url']
    for enc in getattr(entry, 'enclosures', []):
        if enc.get('type', '').startswith('image'):
            return enc.get('href') or enc.get('url')
    html_blob = getattr(entry, 'summary', '')
    for c in getattr(entry, 'content', []):
        html_blob += c.get('value', '')
    img = BeautifulSoup(html_blob, 'html.parser').find('img')
    if img and img.get('src'):
        return img['src']
    return None

def fetch_og_image(url, timeout=5):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=timeout)
        og = BeautifulSoup(resp.text, 'html.parser').find('meta', property='og:image')
        if og and og.get('content'):
            return og['content']
    except Exception:
        pass
    return None

def is_valid_image_url(url):
    if not url or not url.startswith('http'):
        return False
    return any(ext in url.lower() for ext in ('.jpg', '.jpeg', '.png', 'image/jpeg', 'image/png'))

def build_news_related_prompt(title, source):
    title_lower = title.lower()

    if any(kw in title_lower or kw in title for kw in ['株', '株式', '株価', 'stock', '上場', '東証', 'ipo']):
        scene = 'stock market trading floor with busy traders, financial district skyscrapers at dusk, Wall Street atmosphere'
    elif any(kw in title_lower or kw in title for kw in ['円', '為替', 'ドル', 'yen', 'dollar', 'currency', '外貨']):
        scene = 'currency exchange concept, yen and dollar coins, global money flow on world map, international finance'
    elif any(kw in title_lower or kw in title for kw in ['金利', '利上げ', '利下げ', '日銀', '中央銀行', 'fed', '金融政策']):
        scene = 'central bank neoclassical building exterior, monetary policy meeting room, bank vault door, financial stability concept'
    elif any(kw in title_lower or kw in title for kw in ['物価', 'インフレ', 'cpi', '消費者物価', '値上げ']):
        scene = 'supermarket shopping cart with price tags, inflation concept, grocery store shelves, cost of living illustration'
    elif any(kw in title_lower or kw in title for kw in ['gdp', '経済成長', '景気', 'economy', '経済指標']):
        scene = 'modern city skyline prosperity, bustling urban economic activity, infrastructure and construction, economic progress'
    elif any(kw in title_lower or kw in title for kw in ['貿易', '輸出', '輸入', 'trade', '関税', 'tariff', '港']):
        scene = 'large cargo container ship at port, aerial view of shipping containers, global trade logistics, harbor at golden hour'
    elif any(kw in title_lower or kw in title for kw in ['半導体', 'ai', '人工知能', 'テック', 'tech', 'デジタル', 'チップ']):
        scene = 'semiconductor microchip close-up macro photography, AI data center server room, technology innovation concept'
    elif any(kw in title_lower or kw in title for kw in ['エネルギー', '原油', '石油', '電力', '再生可能', '太陽光', '風力']):
        scene = 'solar panels and wind turbines landscape, oil refinery at sunset, clean energy transition, power plant aerial view'
    elif any(kw in title_lower or kw in title for kw in ['不動産', '住宅', 'マンション', '土地', 'real estate', '建設']):
        scene = 'modern residential apartment buildings, real estate development construction crane, urban housing market concept'
    elif any(kw in title_lower or kw in title for kw in ['企業', '決算', '収益', '利益', '売上', 'earnings', '業績']):
        scene = 'corporate glass skyscraper headquarters exterior, executive boardroom meeting, business success concept'
    elif any(kw in title_lower or kw in title for kw in ['雇用', '失業', '求人', '労働', 'jobs', 'employment', '採用']):
        scene = 'diverse professionals in modern office, job interview handshake, employment agency busy atmosphere'
    elif any(kw in title_lower or kw in title for kw in ['政府', '政策', '予算', '財政', '税', '補助金', '首相']):
        scene = 'government parliament building with national flags, policy document signing, public finance budget planning'
    elif any(kw in title_lower or kw in title for kw in ['農業', '食料', '食品', '農産', '農家']):
        scene = 'agricultural fields aerial view at harvest time, farm machinery, food supply chain, sustainable farming'
    elif any(kw in title_lower or kw in title for kw in ['医療', '製薬', '病院', '健康', 'pharma', 'health']):
        scene = 'modern hospital building exterior, medical research laboratory, pharmaceutical production, healthcare concept'
    elif any(kw in title_lower or kw in title for kw in ['観光', '旅行', 'インバウンド', '訪日', '宿泊', 'tourism']):
        scene = 'tourists at iconic Japanese landmark, bustling travel destination, hotel skyline, vibrant tourism scene'
    else:
        scene = 'professional business news concept, modern office district aerial view, corporate world economic activity'

    prompt = (
        f'{scene}, '
        'photorealistic cinematic photography style, '
        'professional news journalism aesthetic, '
        'high quality, no text overlay, no letters, no watermark, 4k HDR'
    )
    seed = abs(hash(title)) % 99999
    return (
        f'https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}'
        f'?width=1080&height=1080&nologo=true&model=flux&seed={seed}'
    )

def generate_news_card_image(title, source, summary):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), color='#0a1628')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 8], fill='#2563eb')
    draw.rectangle([0, H-8, W, H], fill='#2563eb')
    draw.rectangle([0, 0, 6, H], fill='#2563eb')
    draw.rectangle([60, 80, 60 + len(source)*22 + 20, 130], fill='#2563eb')
    try:
        font_large  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 60)
        font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
        font_small  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
        font_source = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28)
    except Exception:
        font_large = font_medium = font_small = font_source = ImageFont.load_default()
    draw.text((70, 85), source, font=font_source, fill='white')
    lines, line, max_w = [], '', W - 120
    for ch in title:
        test = line + ch
        bbox = draw.textbbox((0, 0), test, font=font_large)
        if bbox[2] - bbox[0] > max_w:
            lines.append(line); line = ch
        else:
            line = test
    if line: lines.append(line)
    y = 200
    for ln in lines[:4]:
        draw.text((60, y), ln, font=font_large, fill='white'); y += 75
    draw.rectangle([60, y+20, W-60, y+24], fill='#2563eb')
    sum_lines, line = [], ''
    for ch in (summary or ''):
        test = line + ch
        bbox = draw.textbbox((0, 0), test, font=font_medium)
        if bbox[2] - bbox[0] > W - 120:
            sum_lines.append(line); line = ch
        else:
            line = test
    if line: sum_lines.append(line)
    y2 = y + 60
    for sl in sum_lines[:5]:
        draw.text((60, y2), sl, font=font_medium, fill='#94a3b8'); y2 += 48
    draw.text((60, H - 80), '📈 Market News Auto Post', font=font_small, fill='#475569')
    return img

def upload_to_imgbb(pil_img, api_key):
    if not api_key:
        return None
    buf = io.BytesIO()
    pil_img.save(buf, format='JPEG', quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode()
    try:
        resp = requests.post('https://api.imgbb.com/1/upload',
                             data={'key': api_key, 'image': b64}, timeout=30)
        data = resp.json()
        if data.get('success'):
            return data['data']['url']
    except Exception as e:
        print(f'    ⚠️ imgbbエラー: {e}')
    return None

def download_image_as_pil(url, timeout=90):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', ''):
            return Image.open(io.BytesIO(resp.content)).convert('RGB')
    except Exception as e:
        print(f'    ⚠️ ダウンロードエラー: {e}')
    return None

def get_image_url(news):
    title   = news.get('title', '')
    source  = news.get('source', '')
    summary = news.get('summary', '')

    def to_static(pil_img, label):
        if not IMGBB_API_KEY:
            return None
        print(f'    ☁️  [{label}] imgbbにアップロード中...')
        url = upload_to_imgbb(pil_img, IMGBB_API_KEY)
        if url:
            print(f'    ✅ アップロード成功: {url}')
        return url

    rss_url = news.get('image_url')
    if rss_url and rss_url.startswith('http'):
        if is_valid_image_url(rss_url):
            print(f'    🖼️  RSS/OG静的画像を使用')
            return rss_url
        pil = download_image_as_pil(rss_url, timeout=20)
        if pil:
            url = to_static(pil, 'RSS画像')
            if url: return url

    print(f'    🤖 ニュース関連画像を生成中: 「{title[:25]}...」')
    ai_url = build_news_related_prompt(title, source)
    pil = download_image_as_pil(ai_url)
    if pil:
        if IMGBB_API_KEY:
            url = to_static(pil, 'AI関連画像')
            if url: return url
        else:
            print('    ⚠️  imgbb未設定のため動的URLを使用')
            return ai_url

    if IMGBB_API_KEY:
        print('    🎨 Pillowでニュースカードを生成中...')
        try:
            url = to_static(generate_news_card_image(title, source, summary), 'Pillowカード')
            if url: return url
        except Exception as e:
            print(f'    ❌ カード生成エラー: {e}')

    print('    🆘 フォールバック: Pollinations.AI URLを使用')
    return ai_url

def fetch_latest_news(source_name, feed_url, n=3):
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f'    ❌ フィード取得エラー: {e}')
        return []
    if not feed.entries:
        print(f'    ⚠️  エントリが0件: {feed_url}')
        return []
    results = []
    for entry in feed.entries[:n]:
        title     = clean_html(entry.get('title', ''))
        summary   = clean_html(entry.get('summary', '') or entry.get('description', ''))
        link      = entry.get('link', '')
        image_url = extract_image_from_entry(entry) or (fetch_og_image(link) if link else None)
        results.append({
            'source': source_name, 'title': title,
            'summary': truncate(summary or title),
            'link': link, 'image_url': image_url,
        })
    return results

def build_caption(news):
    link = news.get('link', '')
    url_block = ''
    if link:
        try:
            domain = urllib.parse.urlparse(link).netloc.replace('www.', '')
        except Exception:
            domain = ''
        url_block = (
            f'📰 詳細記事: {domain}\n'
            f'👆 プロフィールのリンクから記事をご覧いただけます\n'
            f'🔗 {link}'
        )
    return (
        f"【{news['source']}】\n"
        f"{news['title']}\n\n"
        f"{news['summary']}\n\n"
        f"{url_block}\n\n"
        f"{HASHTAGS}"
    )

def create_media_container(image_url, caption):
    resp = requests.post(
        f'{BASE_URL}/{IG_USER_ID}/media',
        data={'image_url': image_url, 'caption': caption,
              'media_type': 'IMAGE', 'access_token': ACCESS_TOKEN}
    )
    data = resp.json()
    if resp.status_code == 200 and 'id' in data:
        print(f'  ✅ メディアコンテナ作成: ID={data["id"]}')
        print('  ⏳ 処理待機中（10秒）...')
        time.sleep(10)
        return data['id']
    print('  ❌ コンテナ作成失敗:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return None

def publish_media(container_id):
    resp = requests.post(
        f'{BASE_URL}/{IG_USER_ID}/media_publish',
        data={'creation_id': container_id, 'access_token': ACCESS_TOKEN}
    )
    data = resp.json()
    if resp.status_code == 200 and 'id' in data:
        print(f'  🎉 投稿成功！ 投稿ID={data["id"]}')
        return data['id']
    print('  ❌ 投稿失敗:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return None

def post_to_instagram(image_url, caption):
    print('=' * 55)
    print('📤 Instagram投稿開始...')
    print(f'  画像URL: {image_url[:70]}...')
    print(f'  キャプション: {caption[:50]}...')
    print('=' * 55)
    if not image_url or not image_url.startswith('http'):
        print('❌ 有効な画像URLがありません。')
        return None
    cid = create_media_container(image_url, caption)
    if not cid:
        return None
    pid = publish_media(cid)
    if pid:
        print('\n✨ 投稿完了！Instagramアプリで確認してください。')
    return pid


# ================================================================
# 🚀 メイン実行
# ================================================================

print('📡 RSSフィードからニュースを取得中...')
all_news = []
for source_name, feed_url in RSS_FEEDS.items():
    print(f'  [{source_name}] 取得中...')
    try:
        items = fetch_latest_news(source_name, feed_url, n=NEWS_PER_FEED)
        all_news.extend(items)
        print(f'    ✅ {len(items)} 件取得')
    except Exception as e:
        print(f'    ❌ エラー: {e}')

print(f'\n合計 {len(all_news)} 件取得完了\n')

if not all_news:
    print('❌ ニュースが1件も取得できませんでした。')
    sys.exit(1)

print('🖼️  画像を取得・生成中...')
for news in all_news:
    print(f"  [{news['source']}] {news['title'][:35]}...")
    news['resolved_image_url'] = get_image_url(news)

print('\n📤 Instagramへ投稿中...')

if POST_ALL:
    targets = [n for n in all_news if n.get('resolved_image_url')]
    print(f'  {len(targets)} 件を順番に投稿します。')
    for idx, news in enumerate(targets, 1):
        print(f'\n  [{idx}/{len(targets)}] {news["source"]} - {news["title"][:30]}...')
        post_to_instagram(news['resolved_image_url'], build_caption(news))
        if idx < len(targets):
            print(f'  ⏳ {INTERVAL}秒待機中...')
            time.sleep(INTERVAL)
    print('\n🏁 全投稿完了！')
else:
    if POST_INDEX >= len(all_news):
        print(f'❌ POST_INDEX={POST_INDEX} が範囲外です（0〜{len(all_news)-1}）')
        sys.exit(1)
    news = all_news[POST_INDEX]
    img_url = news.get('resolved_image_url')
    print(f'  選択: [{POST_INDEX}] {news["source"]} - {news["title"]}')
    if not img_url:
        print('  ❌ 有効な画像URLがありません。')
        sys.exit(1)
    post_to_instagram(img_url, build_caption(news))
