"""
サイトビルダー: data/snapshots/ + content/*.md → site/ に静的サイトを生成。
stdlib のみ使用。Markdown は簡易パーサーで変換。
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SNAPSHOTS_DIR = BASE_DIR / "data" / "snapshots"
CONTENT_DIR = BASE_DIR / "content"
SITE_DIR = BASE_DIR / "steam"
GAMES_PATH = BASE_DIR / "games.json"
TEMPLATE_DIR = BASE_DIR / "templates"


def load_game_list() -> list[dict]:
    with open(GAMES_PATH, encoding="utf-8") as f:
        return json.load(f)["games"]


def load_latest_snapshot() -> dict | None:
    """最新の日次スナップショットを読み込む"""
    files = sorted(SNAPSHOTS_DIR.glob("2*-*-*.json"), reverse=True)
    if not files:
        return None
    with open(files[0], encoding="utf-8") as f:
        return json.load(f)


def load_price_history() -> dict:
    """全日次スナップショットから価格履歴を構築"""
    history = {}  # appid -> [{date, price_final, discount_percent}, ...]
    for f in sorted(SNAPSHOTS_DIR.glob("2*-*-*.json")):
        with open(f, encoding="utf-8") as fh:
            snap = json.load(fh)
        date = snap.get("date", "")
        for game in snap.get("games", []):
            appid = str(game["appid"])
            if appid not in history:
                history[appid] = []
            history[appid].append({
                "date": date,
                "price_final": game.get("price_final", 0),
                "discount_percent": game.get("discount_percent", 0),
            })
    return history


def parse_markdown_frontmatter(text: str) -> tuple[dict, str]:
    """--- で囲まれたフロントマターとMarkdown本文を分離"""
    meta = {}
    body = text
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                # 簡易配列パース [a, b, c]
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
                meta[key] = val
        body = match.group(2)
    return meta, body


DIALOGUE_CHARS = {
    "scala": {"name": "Dr.スカラ", "img": "img/scala.png", "side": "left"},
    "kotori": {"name": "ことり", "img": "img/kotori.png", "side": "right"},
}


def inline_markdown(text: str) -> str:
    """インラインMarkdown変換"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def simple_markdown_to_html(md: str) -> str:
    """最低限のMarkdown→HTML変換（対話記法対応）

    対話記法: > キャラID: セリフ
    例: > scala: やあ、今日のセール情報だよ
        > kotori: わー、安くなってますね！
    """
    lines = md.split("\n")
    html_lines = []
    in_paragraph = False

    def close_paragraph():
        nonlocal in_paragraph
        if in_paragraph:
            html_lines.append("</p>")
            in_paragraph = False

    for line in lines:
        stripped = line.strip()

        # 対話記法: > scala: セリフ  / > kotori: セリフ
        dialogue_match = re.match(r'^>\s*(scala|kotori)\s*:\s*(.+)', stripped)
        if dialogue_match:
            close_paragraph()
            char_id = dialogue_match.group(1)
            text = inline_markdown(dialogue_match.group(2).strip())
            char = DIALOGUE_CHARS[char_id]
            side = char["side"]
            html_lines.append(
                f'<div class="dialogue dialogue-{side}">'
                f'<img src="../{char["img"]}" alt="{char["name"]}" class="dialogue-avatar">'
                f'<div class="dialogue-bubble">'
                f'<span class="dialogue-name">{char["name"]}</span>'
                f'{text}'
                f'</div></div>'
            )
            continue

        # 見出し
        if stripped.startswith("### "):
            close_paragraph()
            html_lines.append(f"<h3>{inline_markdown(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_paragraph()
            html_lines.append(f"<h2>{inline_markdown(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            close_paragraph()
            html_lines.append(f"<h1>{inline_markdown(stripped[2:])}</h1>")
        elif stripped == "":
            close_paragraph()
        else:
            processed = inline_markdown(stripped)
            if not in_paragraph:
                html_lines.append("<p>")
                in_paragraph = True
            html_lines.append(processed)

    close_paragraph()
    return "\n".join(html_lines)


def load_articles() -> dict:
    """content/*.md を読み込み、slug → {meta, html} のマップを返す"""
    articles = {}
    if not CONTENT_DIR.exists():
        return articles
    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        slug = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_markdown_frontmatter(text)
        html = simple_markdown_to_html(body)
        articles[slug] = {"meta": meta, "html": html, "slug": slug}
    return articles


def build_data_json(snapshot: dict, history: dict, articles: dict):
    """site/data/ にダッシュボード用JSONを出力"""
    data_dir = SITE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # ゲーム一覧（記事有無フラグ付き）
    games = []
    for g in snapshot.get("games", []):
        slug = g.get("slug", "")
        g["has_article"] = slug in articles
        if slug in articles:
            g["article_title"] = articles[slug]["meta"].get("title", "")
        games.append(g)

    games_data = {
        "date": snapshot.get("date", ""),
        "timestamp": snapshot.get("timestamp", ""),
        "games": games,
    }
    with open(data_dir / "games.json", "w", encoding="utf-8") as f:
        json.dump(games_data, f, ensure_ascii=False, indent=2)

    # 価格履歴
    with open(data_dir / "history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # 記事一覧
    article_list = []
    for slug, art in articles.items():
        article_list.append({
            "slug": slug,
            "title": art["meta"].get("title", slug),
            "appid": art["meta"].get("appid", ""),
            "tags": art["meta"].get("tags", []),
        })
    with open(data_dir / "articles.json", "w", encoding="utf-8") as f:
        json.dump(article_list, f, ensure_ascii=False, indent=2)


def build_article_pages(articles: dict):
    """Markdown記事をHTMLページとして出力"""
    articles_dir = SITE_DIR / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    for slug, art in articles.items():
        meta = art["meta"]
        title = meta.get("title", slug)
        appid = meta.get("appid", "")

        html = f"""<!DOCTYPE html>
<html lang="ja" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | すばらしきSteamゲームの本棚</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
<link rel="stylesheet" href="../style.css">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7086371722392050"
     crossorigin="anonymous"></script>
</head>
<body>
<main class="container">
  <nav class="breadcrumb">
    <a href="../">トップ</a> &gt; <span>{title}</span>
  </nav>
  <article class="article-content">
    <header>
      <h1>{title}</h1>
      {f'<a href="https://store.steampowered.com/app/{appid}/" target="_blank" class="steam-link">Steam ストアページ</a>' if appid else ''}
    </header>
    {art["html"]}
  </article>

  <!-- 記事下広告 -->
  <div style="text-align: center; margin: 20px auto; max-width: 800px;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-7086371722392050"
         data-ad-slot="4953305789" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
  </div>

  <div class="emotelab-credit">
    <p>この記事のキャラクターは <a href="https://store.steampowered.com/app/4301100/EmoteLab/" target="_blank">EmoteLab</a> で作成しました。</p>
  </div>
</main>
<footer class="container">
  <p><a href="../">すばらしきSteamゲームの本棚</a> | Steam data &copy; <a href="https://store.steampowered.com/" target="_blank">Valve Corporation</a></p>
</footer>
</body>
</html>"""
        out_path = articles_dir / f"{slug}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  記事生成: {out_path.name}")


def main():
    print("サイトビルド開始...")

    snapshot = load_latest_snapshot()
    if not snapshot:
        print("スナップショットなし。先に fetch_steam.py を実行してください。")
        return

    history = load_price_history()
    articles = load_articles()
    print(f"スナップショット: {snapshot['date']} ({len(snapshot['games'])}本)")
    print(f"記事: {len(articles)}本")

    # data JSON 出力
    build_data_json(snapshot, history, articles)
    print(f"データJSON出力完了")

    # 記事ページ生成
    if articles:
        build_article_pages(articles)

    # 静的ファイルコピー (templates/ → site/)
    for src in (TEMPLATE_DIR,):
        if src.exists():
            for f in src.iterdir():
                if f.is_file():
                    shutil.copy2(f, SITE_DIR / f.name)
                elif f.is_dir():
                    dest = SITE_DIR / f.name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(f, dest)

    print(f"\nビルド完了: {SITE_DIR}")


if __name__ == "__main__":
    main()
