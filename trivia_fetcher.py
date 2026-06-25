"""
🔍 ホット雑学フェッチャー
無料・認証不要のAPIから「今日話題の雑学」を収集するモジュール。

利用ソース（すべて無料・APIキー不要）:
  1. Google Trends RSS  — 日本のトレンドキーワード
  2. Wikipedia API      — トレンドキーワードの記事概要 → 雑学ポイントを抽出
  3. Wikipedia 今日の出来事 — 今日の歴史的出来事
  4. フォールバック固定プール — 取得失敗時の保険

【設計方針】
- 「名前」列と「説明」列がセットで意味が通じることを最優先
- Wikipediaから取った説明は必ず「〇〇は〜」の形に整形して単体で読める文にする
- 件数が少なくてもフォールバックプールで必ず補完するので投稿は途切れない
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


def _first_sentence(text, max_chars=50):
    """
    テキストから最初の1文を取り出す。
    句点で終わる完全な文として返す。max_charsを超える場合は切る。
    """
    text = _clean(text)
    # 句点・感嘆符・疑問符で区切る
    m = re.search(r'(.{8,}?[。！？])', text)
    if m:
        s = m.group(1).strip()
        if len(s) <= max_chars:
            return s
        # 長すぎる場合は別の区切りを試みる
    # 読点で区切って短くする
    parts = re.split(r'[。！？]', text)
    parts = [p.strip() for p in parts if p.strip()]
    if parts and len(parts[0]) >= 8:
        s = parts[0]
        return (s[:max_chars - 1] + '…') if len(s) > max_chars else s + '。'
    return None


def _make_readable(keyword, summary, max_chars=50):
    """
    Wikipedia概要とキーワードから「○○は〜。」形式の読める説明文を作る。

    優先順位:
      1. 「キーワードは〜」「キーワードとは〜」で始まる文を探す
      2. 数値・記録・特徴を含む文を探す
      3. 最初の1文をそのまま使う
      4. 失敗時はNone
    """
    if not summary or not keyword:
        return None

    text = _clean(summary)
    sentences = [s.strip() for s in re.split(r'[。！？]', text) if s.strip()]

    # ── 優先1: 「キーワードは/とは」で始まる文 ──────────────────
    for s in sentences[:5]:
        if s.startswith(keyword) or re.match(rf'^{re.escape(keyword[:4])}', s):
            # 「〜は〜」「〜とは〜」の形か確認
            if re.search(r'(は|とは|とも呼|として)', s[:len(keyword)+8]):
                clean_s = s[:max_chars]
                if len(s) > max_chars:
                    clean_s += '…'
                else:
                    clean_s += '。'
                if len(clean_s) >= 12:
                    return clean_s

    # ── 優先2: 特徴的な数値・記録を含む文 ───────────────────────
    NUM_PATTERN = re.compile(
        r'(\d[\d,\.]+(?:万|億|兆|km|m|cm|kg|g|℃|度|年|個|人|羽|頭|匹|本|枚|冊|件|回|倍|%|％))')
    FEAT_PATTERN = re.compile(
        r'(世界初|世界一|世界最|日本初|日本最|唯一|最大|最小|最古|最長|最速|最多|最少)')

    for s in sentences[:8]:
        if NUM_PATTERN.search(s) or FEAT_PATTERN.search(s):
            # キーワードが含まれているか、短くてもOK
            snippet = s[:max_chars]
            if len(s) > max_chars:
                snippet += '…'
            else:
                snippet += '。'
            if len(snippet) >= 12:
                # 主語が欠けている場合はキーワードを先頭に補う
                if not s.startswith(keyword[:2]):
                    snippet = f'{keyword}は' + snippet
                    snippet = snippet[:max_chars + len(keyword) + 1]
                    if not snippet.endswith('。') and not snippet.endswith('…'):
                        snippet += '…'
                return snippet

    # ── 優先3: 最初の文をそのまま ────────────────────────────────
    if sentences:
        s = sentences[0]
        if len(s) >= 10:
            snippet = s[:max_chars]
            if len(s) > max_chars:
                snippet += '…'
            else:
                snippet += '。'
            return snippet

    return None


# ================================================================
# 📡 ソース1: Google Trends RSS（日本）
# ================================================================

def fetch_google_trends_jp(n=20):
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
                # 人名っぽいもの（姓名2語）や記号を含むものを除外
                if kw and 2 <= len(kw) <= 15 and not re.search(r'[・＆&/\-]', kw):
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
            'exsentences': 5,
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


def fetch_wikipedia_random_featured(n=15):
    """Wikipedia の秀逸な記事タイトルをランダムに取得。"""
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
    rng = random.Random(NOW.strftime('%Y-%m-%d'))
    rng.shuffle(titles)
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
        lines = extract.split('\n')
        for line in lines:
            line = line.strip()
            m = re.match(r'^(\d{3,4})年\s*[–\-]\s*(.+)', line)
            if m:
                year, event = m.group(1), _clean(m.group(2).strip())
                # 意味が通じる長さのみ採用
                if 15 <= len(event) <= 45:
                    # 「○○年に〜した。」形式に整形
                    if not event.endswith('。'):
                        event += '。'
                    facts.append((f'{year}年の今日', event))
    return facts[:5]


# ================================================================
# 🏆 ランキング組み立て
# ================================================================

def build_hot_trivia_ranking(max_items=10):
    """
    今日のホット雑学ランキングを組み立てて返す。
    名前列と説明列が必ずセットで意味の通る文になるよう整形する。
    件数はmax_items以下になることがあるが、最低5件はフォールバックで保証。
    """
    items = []
    seen_names = set()

    def add(name, reason):
        """重複・空・短すぎ をガードしてから追加。"""
        name = name.strip()
        reason = reason.strip()
        if not name or not reason:
            return False
        if len(reason) < 10:
            return False
        # 「。」で終わっていなければ補う
        if not reason[-1] in '。！？…':
            reason += '。'
        # 名前がすでにある場合はスキップ
        if name in seen_names:
            return False
        seen_names.add(name)
        items.append((name, reason))
        return True

    # ── A. 今日の出来事（Wikipedia） ─────────────────────────
    print('  📅 今日の出来事を取得中...')
    otd = fetch_wikipedia_on_this_day()
    for name, event in otd[:3]:
        add(name, event)

    # ── B. Googleトレンド → Wikipedia で雑学抽出 ──────────────
    print('  🌐 Googleトレンドを取得中...')
    trends = fetch_google_trends_jp(n=20)
    tried = 0
    for kw in trends:
        if len(items) >= max_items:
            break
        if tried >= 15:
            break
        tried += 1
        summary = fetch_wikipedia_summary(kw)
        desc = _make_readable(kw, summary)
        if desc:
            # 名前はキーワードそのまま（12文字上限）
            name = kw if len(kw) <= 12 else kw[:12] + '…'
            if add(name, desc):
                print(f'    ✅ [{name}] {desc[:30]}')

    # ── C. Wikipedia 秀逸記事で補完 ───────────────────────────
    if len(items) < max_items:
        print(f'  📚 Wikipedia秀逸記事で補完中...')
        for title in fetch_wikipedia_random_featured(n=20):
            if len(items) >= max_items:
                break
            summary = fetch_wikipedia_summary(title)
            desc = _make_readable(title, summary)
            if desc:
                name = title if len(title) <= 12 else title[:12] + '…'
                add(name, desc)

    # ── D. フォールバック固定プール ───────────────────────────
    if len(items) < max_items:
        print(f'  🔒 フォールバック補完（現在{len(items)}件）...')
        rng = random.Random(NOW.strftime('%Y-%m-%d-fb'))
        pool = _get_fallback_pool()
        rng.shuffle(pool)
        for name, reason in pool:
            if len(items) >= max_items:
                break
            add(name, reason)

    return {
        'title': f'{NOW.month}月{NOW.day}日 今日のホット雑学',
        'items': items[:max_items],
        'hashtags': (
            '#雑学 #今日の雑学 #豆知識 #トリビア #知ってた '
            '#雑学ランキング #面白い #Googleトレンド #話題 #今日の話題'
        ),
        'footer_question': 'どれが一番「へぇ」でしたか？コメントで！',
        'sources': [],
    }


# ================================================================
# 🔒 フォールバック固定プール（すべて主語付きの完全な1文）
# ================================================================

def _get_fallback_pool():
    """ネット取得失敗時の保険用固定雑学プール。すべて単体で意味が通じる文。"""
    return [
        ('バナナの分類',   'バナナは植物学的には「ベリー」に分類される。'),
        ('蜂蜜の保存性',   '蜂蜜は適切に保存すれば数千年経っても腐らない。'),
        ('タコの脳',       'タコには脳が9つあり、各足にも神経節がある。'),
        ('まばたきの回数', '人間は1日に約1万5千〜2万回まばたきする。'),
        ('月の後退速度',   '月は毎年約3.8cmずつ地球から遠ざかっている。'),
        ('人間の骨の数',   '赤ちゃんの骨は約300本あるが、成長で206本に減る。'),
        ('ハチドリの飛行', 'ハチドリは鳥類で唯一、後ろ向きに飛べる。'),
        ('りんごの浮力',   'りんごは果肉の約25%が空気のため水に浮かぶ。'),
        ('雷の温度',       '雷の温度は太陽の表面温度の約5倍に達する。'),
        ('カンガルーの歩行','カンガルーは体の構造上、後ろに歩けない。'),
        ('富士山の状態',   '富士山は現在も活火山に分類されている。'),
        ('ゾウの自己認識', 'ゾウは鏡で自分を認識できる数少ない動物の一つ。'),
        ('コアラの指紋',   'コアラの指紋は人間のものとほぼ区別がつかない。'),
        ('雪の結晶',       '雪の結晶は同じ形のものが二つと存在しない。'),
        ('心臓の拍動数',   '人間の心臓は一生で約20億回拍動するといわれる。'),
        ('脳の消費量',     '脳は体重の約2%だが全エネルギーの約20%を消費する。'),
        ('南極の分類',     '南極大陸は降水量が極めて少なく砂漠に分類される。'),
        ('イルカの睡眠',   'イルカは脳の左右を交互に休ませながら泳ぎ続ける。'),
        ('ラクダのこぶ',   'ラクダのこぶの中身は水ではなく脂肪が蓄積している。'),
        ('チーターの加速', 'チーターは約3秒で時速100kmに達する地上最速の動物。'),
    ]


if __name__ == '__main__':
    print('=== ホット雑学ランキング取得テスト ===')
    result = build_hot_trivia_ranking()
    print(f'\n📌 タイトル: {result["title"]}')
    print(f'📊 取得件数: {len(result["items"])}件\n')
    for i, (name, reason) in enumerate(result['items'], 1):
        print(f'{i:2}位: {name}')
        print(f'      → {reason}')
