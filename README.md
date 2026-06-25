# 📈🧠 市場ニュース & 今日のびっくり雑学 Instagram 自動投稿

GitHub Actions を使って Instagram への自動投稿を行うリポジトリです。

| スクリプト | 内容 | ワークフロー |
|---|---|---|
| `main.py` | 経済・市場ニュースの自動投稿 | `auto_post.yml`（1日6回） |
| `fortune_post.py` | 今日のびっくり雑学ランキングの自動投稿 | `fortune_post.yml`（1日3回） |
| `trivia_fetcher.py` | 雑学コンテンツの収集モジュール（`fortune_post.py` から呼ばれる） | — |
| `ig_utils.py` | Instagram投稿の共通ユーティリティ | — |

---

## ⏰ 実行スケジュール（JST）

### 市場ニュース（`auto_post.yml`）

| UTC | JST |
|-----|-----|
| 00:00 | 09:00 |
| 04:00 | 13:00 |
| 08:00 | 17:00 |
| 12:00 | 21:00 |
| 16:00 | 01:00 |
| 20:00 | 05:00 |

### 今日のびっくり雑学（`fortune_post.yml`）

| UTC | JST | 備考 |
|-----|-----|------|
| 22:00（前日） | 07:00 | 朝の投稿 |
| 03:00 | 12:00 | お昼の投稿 |
| 10:00 | 19:00 | 夜の投稿 |

---

## 🧠 雑学ランキング投稿の内容

### 情報収集の仕組み（`trivia_fetcher.py`）

以下の順で情報を収集し、取得できた分だけ投稿します。
ネット取得に失敗した場合はフォールバックで補完するため、投稿が途切れることはありません。

| 優先順位 | ソース | 内容 |
|---|---|---|
| 1 | Wikipedia「今日の出来事」 | 当日の歴史的な出来事を最大3件取得 |
| 2 | Google Trends RSS（日本） | 今日の急上昇キーワードをWikipediaで調べて雑学化 |
| 3 | Wikipedia 秀逸な記事 | 件数が足りない場合に注目記事から補完 |
| 4 | フォールバック固定プール | ネット取得が全滅した場合の保険（身近な日常トリビア32件） |

すべて **無料・APIキー不要** です。

### 画像フォーマット

- サイズ: 1080 × 1350px（Instagram 縦型 4:5）
- Pillow（Python）で毎回生成
- 表形式ランキング（順位・項目名・説明文）
- フッターに「どれが一番『へぇ！』でしたか？」のコメント誘導

### 説明文のルール

- 主語を含む完全な1文（単体で意味が通じる）
- 26字以内で1行に収まる長さ
- 「〜する。」「〜になる。」とシンプルに事実を伝えるトーン

---

## 🚀 セットアップ手順

### 1. ファイル構成

```
your-repo/
├── main.py               # 市場ニュース投稿
├── fortune_post.py       # 雑学ランキング投稿（メイン）
├── trivia_fetcher.py     # 雑学コンテンツ収集モジュール
├── ig_utils.py           # Instagram投稿の共通ユーティリティ
├── README.md
└── .github/
    └── workflows/
        ├── auto_post.yml       # 市場ニュース用
        └── fortune_post.yml    # 雑学ランキング用
```

### 2. GitHub Secrets に認証情報を登録

**Settings → Secrets and variables → Actions → New repository secret** で以下を登録：

| Secret名 | 内容 | 必須 |
|----------|------|------|
| `META_ACCESS_TOKEN` | Instagram Graph API のアクセストークン | ✅ |
| `INSTAGRAM_ACCOUNT_ID` | Instagram ビジネスアカウント ID | ✅ |
| `IMGBB_API_KEY` | imgbb の API キー（画像のアップロード先） | ✅ |

> ⚠️ `fortune_post.py` はPillowで生成した画像をimgbbにアップロードして公開URLを取得してからInstagramに投稿します。`IMGBB_API_KEY` が未設定の場合は投稿に失敗します。

### 3. GitHub Actions を有効化

リポジトリの **Actions タブ** を開き、ワークフローを有効化してください。

### 4. 動作確認（手動実行）

- Actions タブ → **市場ニュース 自動投稿** → **Run workflow**
- Actions タブ → **雑学ランキング 自動投稿（1日3回）** → **Run workflow**

---

## ⚙️ カスタマイズ

### 市場ニュース（`main.py`）

```python
RSS_FEEDS     = { ... }  # ニュースソースの追加・変更
POST_INDEX    = 0        # 投稿するニュースの番号（0 = 最初の1件）
POST_ALL      = False    # True にすると取得した全ニュースを順番に投稿
NEWS_PER_FEED = 3        # 各フィードから取得する件数
HASHTAGS      = '...'   # ハッシュタグの変更
```

### 雑学ランキング（`trivia_fetcher.py`）

フォールバック用の固定雑学プールは `_get_fallback_pool()` 関数内のリストを編集することで追加・変更できます。

```python
def _get_fallback_pool():
    return [
        ('項目名',  '説明文（26字以内・主語あり・句点で終わる）'),
        ...
    ]
```

スケジュールを変更する場合は `.github/workflows/*.yml` の `cron` 行を編集してください。

---

## ❗ トラブルシューティング

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `190` | アクセストークンの期限切れ | Meta Developers でトークンを再発行し Secret を更新する |
| `9004` | 画像 URL が無効 | `IMGBB_API_KEY` Secret が正しく設定されているか確認する |
| `24` | 投稿上限超過（25投稿/日） | スケジュールの頻度を減らす |
| `❌ IMGBB_API_KEY が設定されていません` | Secret 未設定 | `IMGBB_API_KEY` を Secrets に追加する |
| 雑学の内容がフォールバックのみになる | GitHub Actions からのネット接続が制限されている | `trivia_fetcher.py` の `_get_fallback_pool()` を充実させる |
