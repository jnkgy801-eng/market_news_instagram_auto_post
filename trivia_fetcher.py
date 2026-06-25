"""
🔍 ホット雑学フェッチャー
無料・認証不要のAPIから「今日話題の雑学」を収集するモジュール。

利用ソース（すべて無料・APIキー不要）:
  1. Google Trends RSS  — 日本のトレンドキーワード
  2. Wikipedia API      — トレンドキーワードの記事概要 → 雑学ポイントを抽出
  3. Wikipedia 今日の出来事 — 今日の歴史的出来事
  4. フォールバック固定プール — 取得失敗時の保険（身近な日常トリビア）

【設計方針】
- 説明文は「シンプルに事実をわかりやすく」、40字以内・2行まで
- 必ず主語を含む完全な文にする（単体で意味が通じる）
- フォールバックは誰でもピンとくる身近な日常トリビア
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

MAX_DESC = 40  # 説明文の最大文字数

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
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _trim(text, max_chars=MAX_DESC):
    """指定文字数以内に収め、句点で終わらせる。"""
    text = text.strip()
    if len(text) <= max_chars:
        if not text[-1] in '。！？':
            text += '。'
        return text
    # 句点で切れる最長の位置を探す
    cut = text[:max_chars]
    last_kuten = max(cut.rfind('。'), cut.rfind('！'), cut.rfind('？'))
    if last_kuten > max_chars // 2:
        return text[:last_kuten + 1]
    return cut.rstrip('、') + '…'


def _make_readable(keyword, summary, max_chars=MAX_DESC):
    """
    Wikipedia概要とキーワードから読める説明文を作る。
    優先順位:
      1. 「キーワードは〜」で始まる定義文
      2. 数値・記録・特徴を含む文
      3. 最初の文
    """
    if not summary:
        return None
    text = _clean(summary)
    sentences = [s.strip() for s in re.split(r'[。！？]', text) if s.strip() and len(s.strip()) >= 8]

    # 優先1: キーワードで始まる定義文
    for s in sentences[:5]:
        if s.startswith(keyword[:3]) and re.search(r'(は|とは|であり|である)', s[:len(keyword)+6]):
            return _trim(s, max_chars)

    # 優先2: 数値・記録・特徴を含む文
    NUM = re.compile(r'\d[\d,\.]+(?:万|億|兆|km|m|cm|kg|g|℃|年|個|人|回|倍|%|％)')
    FEAT = re.compile(r'世界初|世界一|日本初|日本最|唯一|最大|最古|最長|最速|最多')
    for s in sentences[:8]:
        if NUM.search(s) or FEAT.search(s):
            # 主語がなければキーワードを補う
            if not s.startswith(keyword[:2]):
                s = f'{keyword}は{s}'
            return _trim(s, max_chars)

    # 優先3: 最初の文
    if sentences:
        s = sentences[0]
        if not s.startswith(keyword[:2]):
            s = f'{keyword}は{s}'
        return _trim(s, max_chars)

    return None


# ================================================================
# 📡 ソース1: Google Trends RSS（日本）
# ================================================================

def fetch_google_trends_jp(n=20):
    url = 'https://trends.google.com/trends/trendingsearches/daily/rss?geo=JP'
    xml = _get(url)
    if not xml:
        return []
    keywords = []
    try:
        root = ET.fromstring(xml)
        for item in root.findall('.//item'):
            el = item.find('title')
            if el is not None and el.text:
                kw = el.text.strip()
                if 2 <= len(kw) <= 15 and not re.search(r'[・＆&/\-]', kw):
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
    url = (
        'https://ja.wikipedia.org/w/api.php?'
        + urllib.parse.urlencode({
            'action': 'query', 'titles': title,
            'prop': 'extracts', 'exintro': True,
            'explaintext': True, 'exsentences': 5,
            'format': 'json', 'utf8': 1,
        })
    )
    data = _get_json(url)
    if not data:
        return None
    for pid, page in data.get('query', {}).get('pages', {}).items():
        if pid != '-1':
            extract = page.get('extract', '')
            if len(extract) > 30:
                return extract
    return None


def fetch_wikipedia_random_featured(n=15):
    url = (
        'https://ja.wikipedia.org/w/api.php?'
        + urllib.parse.urlencode({
            'action': 'query', 'list': 'categorymembers',
            'cmtitle': 'Category:秀逸な記事', 'cmlimit': 50,
            'cmsort': 'timestamp', 'cmdir': 'desc',
            'format': 'json', 'utf8': 1,
        })
    )
    data = _get_json(url)
    titles = []
    if data:
        titles = [m['title'] for m in data.get('query', {}).get('categorymembers', [])
                  if ':' not in m['title']]
    rng = random.Random(NOW.strftime('%Y-%m-%d'))
    rng.shuffle(titles)
    return titles[:n]


def fetch_wikipedia_on_this_day():
    month, day = NOW.month, NOW.day
    url = (
        'https://ja.wikipedia.org/w/api.php?'
        + urllib.parse.urlencode({
            'action': 'query', 'titles': f'{month}月{day}日',
            'prop': 'extracts', 'exintro': True,
            'explaintext': True, 'format': 'json', 'utf8': 1,
        })
    )
    data = _get_json(url)
    if not data:
        return []
    facts = []
    for pid, page in data.get('query', {}).get('pages', {}).items():
        if pid == '-1':
            continue
        for line in page.get('extract', '').split('\n'):
            m = re.match(r'^(\d{3,4})年\s*[–\-]\s*(.+)', line.strip())
            if m:
                year, event = m.group(1), _clean(m.group(2).strip())
                if 12 <= len(event) <= 38:
                    if not event.endswith('。'):
                        event += '。'
                    facts.append((f'{year}年の今日', event))
    return facts[:4]


# ================================================================
# 🏆 ランキング組み立て
# ================================================================

def build_hot_trivia_ranking(max_items=10):
    items = []
    seen = set()

    def add(name, reason):
        name, reason = name.strip(), reason.strip()
        if not name or not reason or len(reason) < 10 or name in seen:
            return False
        if not reason[-1] in '。！？…':
            reason += '。'
        seen.add(name)
        items.append((name, reason))
        return True

    # A. 今日の出来事
    print('  📅 今日の出来事を取得中...')
    for name, event in fetch_wikipedia_on_this_day()[:3]:
        add(name, event)

    # B. Googleトレンド → Wikipedia
    print('  🌐 Googleトレンドを取得中...')
    tried = 0
    for kw in fetch_google_trends_jp(n=20):
        if len(items) >= max_items or tried >= 15:
            break
        tried += 1
        desc = _make_readable(kw, fetch_wikipedia_summary(kw))
        if desc:
            name = kw if len(kw) <= 12 else kw[:12] + '…'
            if add(name, desc):
                print(f'    ✅ [{name}] {desc[:30]}')

    # C. Wikipedia 秀逸記事で補完
    if len(items) < max_items:
        print(f'  📚 Wikipedia秀逸記事で補完中...')
        for title in fetch_wikipedia_random_featured(n=20):
            if len(items) >= max_items:
                break
            desc = _make_readable(title, fetch_wikipedia_summary(title))
            if desc:
                name = title if len(title) <= 12 else title[:12] + '…'
                add(name, desc)

    # D. フォールバック
    if len(items) < max_items:
        print(f'  🔒 フォールバック補完（現在{len(items)}件）...')
        pool = _get_fallback_pool()
        random.Random(NOW.strftime('%Y-%m-%d-fb')).shuffle(pool)
        for name, reason in pool:
            if len(items) >= max_items:
                break
            add(name, reason)

    return {
        'title': f'{NOW.month}月{NOW.day}日 今日のびっくり雑学',
        'items': items[:max_items],
        'hashtags': (
            '#雑学 #豆知識 #トリビア #知ってた #びっくり '
            '#日常の不思議 #へぇ #面白い #今日の雑学 #雑学好きと繋がりたい'
        ),
        'footer_question': 'どれが一番「へぇ！」でしたか？コメントで！',
        'sources': [],
    }


# ================================================================
# 🔒 フォールバック — 誰でもピンとくる身近な日常トリビア
# ================================================================

def _get_fallback_pool():
    """
    日常生活に密着した「え、そうなの！？」系トリビア。
    すべて40字以内・主語あり・句点で終わる完全な1文。
    """
    return [
        # 食べ物・飲み物
        ('カップ麺の秘密',      'カップ麺は3分待たなくても2分で食べごろになる。'),
        ('コーラの炭酸',        'コーラを冷やすと炭酸が長持ちするのは気体が冷えると水に溶けやすいから。'),
        ('バナナの保存',        'バナナは冷蔵庫より常温保存のほうが長持ちする。'),
        ('卵の鮮度チェック',    '卵を水に入れると新鮮なものは沈み、古いものは浮く。'),
        ('蜂蜜の保存性',        '蜂蜜は正しく保存すれば何年経っても腐らない。'),
        ('チョコと体温',        'チョコレートの融点は体温に近いため口の中でとろける。'),
        ('緑茶とカフェイン',    '緑茶のカフェイン量はコーヒーの約半分程度。'),
        ('納豆のかき混ぜ',      '納豆は混ぜるほどうまみ成分グルタミン酸が増える。'),

        # 体・健康
        ('くしゃみの速度',      'くしゃみの速度は時速約160kmにもなる。'),
        ('笑いと筋肉',          '思いっきり笑うと腹筋を100回したのと同じ運動量になる。'),
        ('人間の体温',          '人の体温は昔37度が基準だったが今は36度台が標準とされる。'),
        ('爪の成長速度',        '手の爪は足の爪より約3倍速く伸びる。'),
        ('欠伸うつり',          'あくびがうつるのは共感能力が高い人ほど起きやすいとされる。'),
        ('利き手と利き足',      '利き手と利き足は多くの場合同じ側になることが多い。'),
        ('睡眠と記憶',          '睡眠中に脳は昼間の記憶を整理して定着させている。'),
        ('水を飲む量',          '成人が1日に必要な水分量は約2〜2.5リットルとされる。'),

        # 日常・生活
        ('エレベーターの鏡',    'エレベーターの鏡は後方確認のために設置されている。'),
        ('赤信号の色',          '赤信号に赤が使われているのは波長が長く遠くからでも見えるから。'),
        ('電子レンジの仕組み',  '電子レンジは食品内の水分子を振動させて熱を発生させる。'),
        ('シャンプーと指の本数','シャンプーのボトルにあるギザギザはコンディショナーと区別するためにある。'),
        ('お札の向き',          'お財布にお札を入れるとき頭を下に向けると出ていきにくいといわれる。'),
        ('蛍光灯の点滅',        '蛍光灯が寿命になると点滅するのは電極が劣化して放電が不安定になるから。'),

        # 動物・自然
        ('犬の汗',              '犬は主に肉球から汗をかき、口を開けて体温を調節する。'),
        ('猫の鳴き声',          '猫の「ニャー」はほぼ人間にだけ向けた鳴き声。'),
        ('金魚の記憶',          '金魚の記憶は3秒という説は誤りで実際は数ヶ月以上記憶できる。'),
        ('カラスの知能',        'カラスは信号が赤のときに車の前に木の実を置き、青になると車に轢かせて割る。'),
        ('蚊に刺されやすい人',  '蚊はO型の血液型の人を最も好むとされている。'),
        ('雨上がりの匂い',      '雨の独特な匂いは土の細菌が原因でペトリコールと呼ぶ。'),
        ('カタツムリの歯',      'カタツムリは歯を約1万2千本持っており食べ物をすりおろして食べる。'),
        ('てんとう虫の点',      'てんとう虫の点の数は種類を示し、年齢や雌雄とは無関係。'),
    ]


if __name__ == '__main__':
    print('=== ホット雑学ランキング取得テスト ===')
    result = build_hot_trivia_ranking()
    print(f'\n📌 タイトル: {result["title"]}')
    print(f'📊 取得件数: {len(result["items"])}件\n')
    for i, (name, reason) in enumerate(result['items'], 1):
        print(f'{i:2}位: {name}')
        print(f'      → {reason}')
