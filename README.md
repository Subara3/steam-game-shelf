# すばらしきSteamゲームの本棚

Steam ゲームのセール情報・価格推移を追跡するダッシュボードサイト。

**URL**: http://steam.subara3.com

## 構成

```
fetch_steam.py      # Steam Store API からゲーム情報を取得
build_site.py       # 静的サイト生成 (JSON + HTML)
games.json          # 追跡ゲームリスト
content/*.md        # 手書き記事 (Markdown)
templates/          # HTML/CSS/JS テンプレート
site/               # ビルド出力 → FTPでデプロイ
```

## ゲームを追加する

`games.json` にAppIDとslugを追加:

```json
{"appid": 12345, "slug": "game-name", "comment": "ゲームの説明"}
```

AppID は Steam ストアURLの `app/数字` の部分。

## 記事を書く

`content/game-slug.md` にMarkdownファイルを作成:

```markdown
---
title: ゲーム名 レビュー
appid: 12345
tags: [RPG, インディー]
---

記事の本文をここに書く...
```

## デプロイ

GitHub Actions で毎日自動実行 → ロリポップにFTPデプロイ。

### 必要なシークレット

| 名前 | 用途 |
|------|------|
| `FTP_HOST` | ロリポップ FTPサーバー |
| `FTP_USER` | FTPユーザー名 |
| `FTP_PASS` | FTPパスワード |

## 技術スタック

- Python 3.12 (stdlib のみ、外部依存なし)
- Alpine.js + Pico CSS (フロントエンド)
- GitHub Actions (定期実行)
- ロリポップ (ホスティング)
