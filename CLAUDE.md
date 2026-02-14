# Steam Game Shelf ビルドガイド

Steamゲーム情報ダッシュボード。割引情報やレビューを一覧表示する静的サイト。

## サイト概要

- **URL**: https://steam.subara3.com/
- **リポジトリ**: Subara3/steam-game-shelf (public)
- **ホスティング**: Lolipop（FTP経由）
- **デプロイ**: GitHub Actions（masterブランチpushで自動: fetch → build → FTP）
- **技術**: Alpine.js 3 + vanilla CSS。サーバサイドなし（完全静的）

## ★最重要ルール: テンプレートとビルド出力

**`steam/` を直接編集するな。必ず `templates/` を編集しろ。**

### なぜか
GitHub Actionsの `build_site.py` が `templates/` → `steam/` にコピーする。
`steam/` を直接編集しても、次のActionsビルドで `templates/` の内容に上書きされる。

### ビルドフロー
```
templates/app.js        → steam/app.js        (そのままコピー)
templates/index.html    → steam/index.html    (そのままコピー)
templates/style.css     → steam/style.css     (そのままコピー)
templates/i18n.json     → steam/i18n-data.js  (window.__i18n=...;でラップ)
templates/favicon.svg   → steam/favicon.svg   (そのままコピー)
templates/img/          → steam/img/          (ディレクトリコピー)
```

### build_site.py が自動生成するファイル（手動編集不要）
```
steam/data/games.json     ← data/snapshots/ + games.json から生成
steam/data/articles.json  ← content/*.md のメタデータ
steam/data/history.json   ← 全スナップショットの価格履歴
steam/i18n-data.js        ← templates/i18n.json のJSラップ
steam/i18n.json           ← templates/i18n.json のコピー
steam/sitemap.xml         ← 自動生成
steam/robots.txt          ← 自動生成
steam/articles/*.html     ← content/*.md からHTML生成
steam/articles/en/*.html  ← content/en/*.md からHTML生成
```

## 変更の手順

### UI・ロジック・スタイルの変更
1. `templates/` 内のファイルを編集
2. `python build_site.py` でローカルビルド
3. `steam/` の出力を確認
4. `templates/` と `steam/` の両方をコミット＆プッシュ

### ゲームの追加・削除
`games.json` を編集（appid, name, featured フラグ等）。

### 記事の追加
`content/` にMarkdownファイルを追加。フロントマター形式。

### 翻訳の追加
`templates/i18n.json` を編集（`steam/i18n-data.js` を直接触るな）。

## ファイル構造

```
steam-game-shelf/
├── CLAUDE.md               ← このファイル
├── games.json              ← ゲームマスタ（appid, name, featured等）★編集対象
├── fetch_steam.py          ← Steam API → data/snapshots/ に日次データ取得
├── build_site.py           ← templates/ + data/ → steam/ にサイト生成
├── article_editor.py       ← 記事エディタ
├── content/                ← 記事Markdown（日本語）★編集対象
│   └── en/                 ← 記事Markdown（英語）
├── data/
│   └── snapshots/          ← 日次Steam APIスナップショット（自動）
├── templates/              ← ★ソースの真実（UI変更はここ）
│   ├── app.js              ← Alpine.jsダッシュボードロジック
│   ├── index.html          ← メインHTML（Alpine.jsテンプレート）
│   ├── style.css           ← 全スタイル
│   ├── i18n.json           ← 日英翻訳データ
│   ├── favicon.svg
│   └── img/
├── steam/                  ← ビルド出力（build_site.pyが生成）
│   ├── app.js              ← templates/からコピー
│   ├── index.html          ← templates/からコピー
│   ├── style.css           ← templates/からコピー
│   ├── i18n-data.js        ← i18n.jsonからJS変換
│   ├── data/               ← 自動生成JSON
│   ├── articles/           ← 自動生成HTML記事
│   └── ads.txt
└── .github/
    └── workflows/
        └── update.yml      ← 毎日JST 7:00 + push時に実行
```

## GitHub Actionsワークフロー (update.yml)

1. `python fetch_steam.py` — Steam APIからデータ取得
2. `python build_site.py` — テンプレートからサイトビルド
3. `data/` の変更があればコミット＆プッシュ
4. `steam/` をFTPでLolipopにデプロイ

**注意**: ステップ2で `templates/` → `steam/` が上書きされる。

## やってはいけないこと

- `steam/app.js`, `steam/index.html`, `steam/style.css` を直接編集する
- `steam/i18n-data.js` を直接編集する（`templates/i18n.json` を使え）
- `steam/data/` 内のJSONを手動編集する（自動生成される）
- `sed` で日本語を含むファイルを編集する（文字化けの恐れ）
