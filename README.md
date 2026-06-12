# 📈📸 市場ニュース & 🔮 ラッキーランキング Instagram 自動投稿

Google ColabのノートブックをGitHub Actionsに移行し、**自動投稿**します。

このリポジトリには2つの自動投稿ワークフローがあります。

| スクリプト | 内容 | ワークフロー |
|---|---|---|
| `main.py` | 経済・市場ニュースの自動投稿 | `.github/workflows/auto_post.yml`（4時間ごと） |
| `fortune_post.py` | 👀 閲覧者の気を引く「今日の星座ラッキーランキング」「今日の雑学ランキング」の自動投稿 | `.github/workflows/fortune_post.yml`（1日3回） |

共通のInstagram投稿処理（メディアコンテナ作成・公開・imgbbアップロードなど）は
`ig_utils.py` にまとめられており、両スクリプトから利用されます。

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

### ラッキー星座・雑学ランキング（`fortune_post.yml`）

| UTC | JST | 備考 |
|-----|-----|------|
| 22:00（前日） | 07:00 | 朝の投稿 |
| 03:00 | 12:00 | お昼の投稿 |
| 10:00 | 19:00 | 夜の投稿 |

毎回 `FORTUNE_CONTENT_TYPE=random` で実行され、実行時刻に応じて
「🔮 今日の星座ラッキーランキング」と「🧠 今日の雑学ランキング TOP5」を
ランダムに切り替えて投稿します。

---

## 🔮 ラッキーランキング投稿の内容

### 1. 今日の星座ラッキーランキング
- 12星座を「その日」の運勢順にランキング化（日付をシードにしているため、
  同じ日なら何度実行しても同じランキングになります）
- 1〜3位はラッキーカラー・ラッキーアイテム・ラッキーアクション付きのカードで強調
- 「保存して毎日チェックしてね」のCTAでリピート訪問を促進

### 2. 今日の雑学ランキング TOP5
- 約45種類の「思わず誰かに話したくなる」雑学プールから、その日のTOP5をランダムに選出
- 「どれが一番『へぇ』でしたか？」とコメントを促すキャプション

どちらも 1080×1080 の正方形画像をPillowで生成し、Instagramの投稿に適した
コントラストの高いデザインにしています。

---

## 🚀 セットアップ手順

### 1. このリポジトリをそのままGitHubに配置

```
your-repo/
├── main.py              # 市場ニュース投稿
├── fortune_post.py      # ラッキー星座・雑学ランキング投稿
├── ig_utils.py          # 共通のInstagram投稿ユーティリティ
├── README.md
└── .github/
    └── workflows/
        ├── auto_post.yml
        └── fortune_post.yml
```

### 2. GitHub Secrets に認証情報を登録

GitHubリポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下を登録：

| Secret名 | 内容 |
|----------|------|
| `META_ACCESS_TOKEN` | Instagramのアクセストークン |
| `INSTAGRAM_ACCOUNT_ID` | InstagramビジネスアカウントID |
| `IMGBB_API_KEY` | imgbb APIキー（**ラッキーランキング投稿には必須**。市場ニュース投稿では任意・推奨） |

> ⚠️ `fortune_post.py` はPillowで生成した画像を必ずimgbbにアップロードして
> 公開URLを作成するため、`IMGBB_API_KEY` が未設定の場合は投稿に失敗します。

### 3. GitHub Actions を有効化

リポジトリの **Actions タブ** を開き、「I understand my workflows, go ahead and enable them」をクリック。

### 4. 動作確認（手動テスト）

- Actions タブ → **市場ニュース 自動投稿** → **Run workflow**
- Actions タブ → **ラッキー星座・雑学ランキング 自動投稿** → **Run workflow**
  - `content_type` を `zodiac` / `trivia` / `random` から選んでテスト投稿できます

---

## ⚙️ 設定変更

### 市場ニュース（`main.py`）

```python
POST_INDEX    = 0      # 投稿するニュースの番号
POST_ALL      = False  # True にすると全ニュースを投稿
NEWS_PER_FEED = 3      # 各フィードから取得する件数
HASHTAGS      = '...'  # ハッシュタグ
```

### ラッキーランキング（`fortune_post.py`）

```python
CONTENT_TYPE = os.environ.get('FORTUNE_CONTENT_TYPE', 'random')
# 'zodiac'  → 今日の星座ラッキーランキング
# 'trivia'  → 今日の雑学ランキング TOP5
# 'random'  → 実行時刻に応じて自動で切り替え
```

- `TRIVIA_FACTS` リストに雑学を追加・編集することで内容を増やせます。
- `LUCKY_COLORS` / `LUCKY_ITEMS` / `LUCKY_ACTIONS` / `RANK_COMMENTS` を編集すると
  星座ランキングの文言バリエーションを増やせます。

スケジュールを変更する場合は `.github/workflows/*.yml` の `cron` 行を編集してください。

---

## ❗ トラブルシューティング

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `190` | トークン期限切れ | Meta DevelopersでSecretを更新 |
| `9004` | 画像URL非対応 | `IMGBB_API_KEY` Secretを設定 |
| `24` | 投稿上限超過（25投稿/日） | スケジュールを減らす |
| `❌ IMGBB_API_KEY が設定されていません` | `fortune_post.py` 実行時に `IMGBB_API_KEY` Secretが未設定 | Secretを追加 |
