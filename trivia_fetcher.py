"""
🔍 ホット雑学フェッチャー
無料・認証不要のAPIから「今日話題の雑学」を収集するモジュール。

利用ソース（すべて無料・APIキー不要）:
  1. Google Trends RSS  — 日本のトレンドキーワード
  2. Wikipedia API      — トレンドキーワードの記事概要 → 雑学ポイントを抽出
  3. Wikipedia 今日の出来事 — 今日の歴史的出来事
  4. フォールバック固定プール — 取得失敗時の保険
"""

import re
import json
import random
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

JST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(JST)

UA = 'Mozilla/5.0 (compatible; TriviaBot/1.0; +https://github.com)'

# ================================================================
# 🔧 共通ユーティリティ
# ================================================================

def _get(url, timeout=10):
    """GETリクエスト → テキスト。失敗時はNone。"""
    try:
        req = urllib.request.Request(
            url, headers={'User-Agent': UA, 'Accept-Language': 'ja,en;q=0.8'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  ⚠️  GET失敗 {url[:60]}: {e}')
        return None


def _get_json(url, timeout=10):
    text = _get(url, timeout)
    if text:
        try:
            return json.loads(text)
        except Exception:
            pass
    return None


def _clean(text):
    """Wikiマークアップ・HTMLタグ・余分な空白を除去。"""
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _shorten(text, max_chars=42):
    """句点・。で区切り、最初の1〜2文に収める。"""
    text = _clean(text)
    # 句点で区切り最初の文を取る
    sentences = re.split(r'[。．！？\!?]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return text[:max_chars]
    result = sentences[0]
    if len(result) <= 20 and len(sentences) > 1:
        result += '。' + sentences[1]
    if len(result) > max_chars:
        result = result[:max_chars - 1] + '…'
    return result


# ================================================================
# 📡 ソース1: Google Trends RSS（日本）
# ================================================================

def fetch_google_trends_jp(n=15):
    """Googleトレンド（日本）からトレンドキーワードを取得。"""
    url = 'https://trends.google.com/trends/trendingsearches/daily/rss?geo=JP'
    xml = _get(url)
    if not xml:
        return []
    keywords = []
    try:
        root = ET.fromstring(xml)
        for item in root.findall('.//item'):
            title_el = item.find('title')
            if title_el is not None and title_el.text:
                kw = title_el.text.strip()
                if kw and len(kw) >= 2:
                    keywords.append(kw)
            if len(keywords) >= n:
                break
    except Exception as e:
        print(f'  ⚠️  Trends XML解析失敗: {e}')
    print(f'  🌐 Google Trends: {len(keywords)}件 取得')
    return keywords


# ================================================================
# 📡 ソース2: Wikipedia API（日本語）
# ================================================================

def fetch_wikipedia_summary(title):
    """日本語Wikipedia の記事概要を取得。"""
    url = (
        'https://ja.wikipedia.org/w/api.php?'
        + urllib.parse.urlencode({
            'action': 'query',
            'titles': title,
            'prop': 'extracts',
            'exintro': True,
            'explaintext': True,
            'exsentences': 3,
            'format': 'json',
            'utf8': 1,
        })
    )
    data = _get_json(url)
    if not data:
        return None
    pages = data.get('query', {}).get('pages', {})
    for pid, page in pages.items():
        if pid == '-1':
            return None
        extract = page.get('extract', '')
        if extract and len(extract) > 30:
            return extract
    return None


def fetch_wikipedia_random_featured(n=10):
    """Wikipedia の注目記事タイトル一覧を取得。"""
    url = (
        'https://ja.wikipedia.org/w/api.php?'
        + urllib.parse.urlencode({
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': 'Category:秀逸な記事',
            'cmlimit': 50,
            'cmsort': 'timestamp',
            'cmdir': 'desc',
            'format': 'json',
            'utf8': 1,
        })
    )
    data = _get_json(url)
    titles = []
    if data:
        members = data.get('query', {}).get('categorymembers', [])
        titles = [m['title'] for m in members if ':' not in m['title']]
    # シャッフルしてn件
    random.shuffle(titles)
    return titles[:n]


def fetch_wikipedia_on_this_day():
    """今日の歴史的出来事（Wikipedia「今日は何の日」）を取得。"""
    month = NOW.month
    day   = NOW.day
    url = (
        'https://ja.wikipedia.org/w/api.php?'
        + urllib.parse.urlencode({
            'action': 'query',
            'titles': f'{month}月{day}日',
            'prop': 'extracts',
            'exintro': True,
            'explaintext': True,
            'format': 'json',
            'utf8': 1,
        })
    )
    data = _get_json(url)
    if not data:
        return []
    pages = data.get('query', {}).get('pages', {})
    facts = []
    for pid, page in pages.items():
        if pid == '-1':
            continue
        extract = page.get('extract', '')
        # 「できごと」セクションの年号付き行を抽出
        lines = extract.split('\n')
        for line in lines:
            line = line.strip()
            # 「YYYY年 - 〜」パターン
            m = re.match(r'^(\d{3,4})年\s*[–\-]\s*(.+)', line)
            if m:
                year, event = m.group(1), m.group(2).strip()
                event = _clean(event)
                if 10 < len(event) < 60:
                    facts.append((year, event))
    return facts[:8]


# ================================================================
# 🧠 雑学ポイントを Wikipedia 概要から抽出
# ================================================================

_TRIVIA_PATTERNS = [
    # 数値・記録系
    r'(\d+(?:\.\d+)?(?:万|億|兆|km|m|cm|kg|g|℃|度|年|個|人|羽|頭|匹|本|枚|冊|件|回|倍|%|％)[^。、]{0,30})',
    # 「〜は〜である」「〜は〜とされる」
    r'([^。]{5,40}(?:とされる|と言われる|といわれる|に分類される|が特徴|として知られる)[^。]{0,20})',
    # 「世界初」「世界一」「日本初」「唯一」
    r'([^。]{0,10}(?:世界初|世界一|日本初|日本最|唯一|最大|最小|最古|最長|最速)[^。]{5,40})',
    # 「〜の名前の由来」「語源」
    r'([^。]{0,10}(?:名前の由来|語源|名称は|由来は)[^。]{5,40})',
]


def extract_trivia_point(summary, keyword):
    """Wikipedia概要から雑学ポイントを抽出。"""
    if not summary:
        return None
    for pattern in _TRIVIA_PATTERNS:
        m = re.search(pattern, summary)
        if m:
            point = _clean(m.group(1))
            if 8 < len(point) < 55:
                return point
    # パターン未命中 → 最初の文を短縮
    first = re.split(r'[。]', _clean(summary))[0]
    if 10 < len(first) < 55:
        return first + '。'
    return None


# ================================================================
# 🏆 ランキング組み立て
# ================================================================

def build_hot_trivia_ranking(max_items=10):
    """
    今日のホット雑学ランキングを組み立てて返す。

    Returns:
        dict: {
            'title': str,
            'items': [(name, reason), ...],   # max_items件
            'hashtags': str,
            'footer_question': str,
            'sources': [str],
        }
    """
    items = []
    sources_used = []

    # ── A. 今日の出来事（Wikipedia） ─────────────────────────
    print('  📅 今日の出来事を取得中...')
    otd = fetch_wikipedia_on_this_day()
    if otd:
        sources_used.append('Wikipedia 今日の出来事')
        rng = random.Random(NOW.strftime('%Y-%m-%d-otd'))
        rng.shuffle(otd)
        for year, event in otd[:3]:
            name = f'{year}年の出来事'
            reason = event[:42]
            items.append((name, reason))
            if len(items) >= 3:
                break

    # ── B. Googleトレンドキーワード → Wikipedia概要から雑学抽出 ─
    print('  🌐 Googleトレンドを取得中...')
    trends = fetch_google_trends_jp(n=20)
    if trends:
        sources_used.append('Google Trends JP')
        tried = 0
        for kw in trends:
            if len(items) >= max_items:
                break
            if tried >= 12:   # タイムアウト防止
                break
            tried += 1
            # 既存と重複チェック
            if any(kw in name for name, _ in items):
                continue
            summary = fetch_wikipedia_summary(kw)
            if not summary:
                continue
            point = extract_trivia_point(summary, kw)
            if not point:
                continue
            # キーワードが短すぎる場合は記事名を補完
            name = kw if len(kw) <= 12 else kw[:12] + '…'
            items.append((name, point))
            print(f'    ✅ [{kw}] → {point[:30]}...')

    # ── C. Wikipedia 注目記事（件数が足りない場合の補完） ────────
    if len(items) < max_items:
        print(f'  📚 Wikipedia注目記事で補完中（残り{max_items - len(items)}件）...')
        featured = fetch_wikipedia_random_featured(n=15)
        sources_used.append('Wikipedia 注目記事')
        for title in featured:
            if len(items) >= max_items:
                break
            if any(title in name for name, _ in items):
                continue
            summary = fetch_wikipedia_summary(title)
            if not summary:
                continue
            point = extract_trivia_point(summary, title)
            if not point:
                continue
            name = title if len(title) <= 12 else title[:12] + '…'
            items.append((name, point))

    # ── D. フォールバック（それでも足りない場合） ──────────────
    if len(items) < max_items:
        print(f'  🔒 フォールバック補完...')
        fallback = _get_fallback_pool()
        rng = random.Random(NOW.strftime('%Y-%m-%d-fb'))
        rng.shuffle(fallback)
        for fb in fallback:
            if len(items) >= max_items:
                break
            items.append(fb)

    # ランキング確定（max_items件）
    items = items[:max_items]

    # タイトル・ハッシュタグ
    month = NOW.month
    day = NOW.day
    title = f'{month}月{day}日 今日のホット雑学'

    hashtags = (
        '#雑学 #今日の雑学 #豆知識 #トリビア #知ってた '
        '#雑学ランキング #面白い #Googleトレンド #話題 #今日の話題'
    )
    footer_question = 'どれが一番「へぇ」でしたか？コメントで！'

    return {
        'title': title,
        'items': items,
        'hashtags': hashtags,
        'footer_question': footer_question,
        'sources': list(dict.fromkeys(sources_used)),  # 重複除去
    }


# ================================================================
# 🔒 フォールバック固定プール
# ================================================================

def _get_fallback_pool():
    """ネット取得失敗時の保険用固定雑学プール。"""
    return [
        ('バナナの分類',     'バナナは植物学的には「ベリー」に分類される。'),
        ('蜂蜜の保存性',     '適切に保存すれば数千年経っても食べられる。'),
        ('タコの脳',         '脳が9つあり各足にも小さな脳がある。'),
        ('まばたき回数',     '人間は1日に約1万5000〜2万回まばたきする。'),
        ('月の後退',         '月は1年に約3.8cmずつ地球から遠ざかっている。'),
        ('骨の数の変化',     '赤ちゃん300個→成長で206個に自然に癒合する。'),
        ('ハチドリの飛行',   '唯一後ろ向きに飛べる鳥として知られる。'),
        ('りんごと水',       '果肉の約25%が空気で水に浮かぶ。'),
        ('雷の温度',         '雷の温度は太陽の表面より高くなることがある。'),
        ('カンガルー',       '構造上、後ろ向きに歩くことができない。'),
        ('富士山',           '現在も活火山に分類されている。'),
        ('ゾウの自己認識',   '鏡に映った自分を認識できる数少ない動物。'),
        ('コアラの指紋',     '人間とほぼ区別がつかないほど似ている。'),
        ('雪の結晶',         '同じ形の結晶は世界に二つと存在しない。'),
        ('心臓の拍動数',     '一生で約20億回拍動するといわれる。'),
    ]


# ================================================================
# 🚀 単体テスト用
# ================================================================

if __name__ == '__main__':
    print('=== ホット雑学ランキング取得テスト ===')
    result = build_hot_trivia_ranking()
    print(f'\n📌 タイトル: {result["title"]}')
    print(f'📡 ソース: {", ".join(result["sources"])}')
    print()
    for i, (name, reason) in enumerate(result['items'], 1):
        print(f'{i:2}位: {name}')
        print(f'      → {reason}')
