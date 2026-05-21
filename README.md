# 📈📸 市場ニュース → Instagram 自動投稿

Google ColabのノートブックをGitHub Actionsに移行し、**4時間ごとに自動投稿**します。

---

## ⏰ 実行スケジュール（JST）

| UTC | JST |
|-----|-----|
| 00:00 | 09:00 |
| 04:00 | 13:00 |
| 08:00 | 17:00 |
| 12:00 | 21:00 |
| 16:00 | 01:00 |
| 20:00 | 05:00 |

---

## 🚀 セットアップ手順

### 1. このファイルをGitHubリポジトリに配置

```
your-repo/
├── main.py
├── README.md
└── .github/
    └── workflows/
        └── auto_post.yml
```

### 2. GitHub Secrets に認証情報を登録

GitHubリポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下を登録：

| Secret名 | 内容 |
|----------|------|
| `META_ACCESS_TOKEN` | Instagramのアクセストークン |
| `INSTAGRAM_ACCOUNT_ID` | InstagramビジネスアカウントID |
| `IMGBB_API_KEY` | imgbb APIキー（任意・推奨） |

### 3. GitHub Actions を有効化

リポジトリの **Actions タブ** を開き、「I understand my workflows, go ahead and enable them」をクリック。

### 4. 動作確認（手動テスト）

Actions タブ → **Instagram 自動投稿（4時間ごと）** → **Run workflow** で手動実行できます。

---

## ⚙️ 設定変更

`main.py` の上部にある設定を変更できます：

```python
POST_INDEX    = 0      # 投稿するニュースの番号
POST_ALL      = False  # True にすると全ニュースを投稿
NEWS_PER_FEED = 3      # 各フィードから取得する件数
HASHTAGS      = '...'  # ハッシュタグ
```

スケジュールを変更する場合は `.github/workflows/auto_post.yml` の `cron` 行を編集してください。

---

## ❗ トラブルシューティング

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `190` | トークン期限切れ | Meta DevelopersでSecretを更新 |
| `9004` | 画像URL非対応 | `IMGBB_API_KEY` Secretを設定 |
| `24` | 投稿上限超過（25投稿/日） | スケジュールを減らす |
