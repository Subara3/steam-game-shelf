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
CONTENT_EN_DIR = BASE_DIR / "content" / "en"
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
    "scala": {"name_ja": "Dr.スカラ", "name_en": "Dr. Scala", "img": "img/scala.png", "side": "left"},
    "kotori": {"name_ja": "ことり", "name_en": "Kotori", "img": "img/kotori.png", "side": "right"},
}


def inline_markdown(text: str) -> str:
    """インラインMarkdown変換"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def simple_markdown_to_html(md: str, lang: str = "ja", img_prefix: str = "../") -> str:
    """最低限のMarkdown→HTML変換（対話記法・プロフィール記法対応）

    対話記法: > キャラID: セリフ
    例: > scala: やあ、今日のセール情報だよ
        > kotori: わー、安くなってますね！

    プロフィール記法: >> キャラID 〜 <<
    例: >> scala
        プロフィール本文
        <<
    """
    lines = md.split("\n")
    html_lines = []
    in_paragraph = False
    in_profile = False
    in_pet_safety = False
    profile_char = None
    profile_lines = []

    def close_paragraph():
        nonlocal in_paragraph
        if in_paragraph:
            html_lines.append("</p>")
            in_paragraph = False

    def close_pet_safety():
        nonlocal in_pet_safety
        if in_pet_safety:
            html_lines.append("</div>")
            in_pet_safety = False

    for line in lines:
        stripped = line.strip()

        # プロフィール開始: >> scala / >> kotori
        profile_start = re.match(r'^>>\s*(scala|kotori)\s*$', stripped)
        if profile_start:
            close_paragraph()
            in_profile = True
            profile_char = profile_start.group(1)
            profile_lines = []
            continue

        # プロフィール終了: <<
        if stripped == "<<" and in_profile:
            char = DIALOGUE_CHARS[profile_char]
            name = char[f"name_{lang}"]
            full_img = char["img"].replace(".png", "-full.png")
            paras = []
            buf = []
            for pl in profile_lines:
                if pl.strip() == "":
                    if buf:
                        paras.append(" ".join(buf))
                        buf = []
                else:
                    buf.append(inline_markdown(pl.strip()))
            if buf:
                paras.append(" ".join(buf))
            body_html = "".join(f"<p>{p}</p>" for p in paras)
            html_lines.append(
                f'<div class="profile-card">'
                f'<img src="{img_prefix}{full_img}" alt="{name}" class="profile-img">'
                f'<div class="profile-info">'
                f'<div class="profile-name">{name}</div>'
                f'<div class="profile-text">{body_html}</div>'
                f'</div></div>'
            )
            in_profile = False
            profile_char = None
            profile_lines = []
            continue

        if in_profile:
            profile_lines.append(line)
            continue

        # 対話記法: > scala: セリフ  / > kotori: セリフ
        dialogue_match = re.match(r'^>\s*(scala|kotori)\s*:\s*(.+)', stripped)
        if dialogue_match:
            close_paragraph()
            char_id = dialogue_match.group(1)
            text = inline_markdown(dialogue_match.group(2).strip())
            char = DIALOGUE_CHARS[char_id]
            name = char[f"name_{lang}"]
            side = char["side"]
            html_lines.append(
                f'<div class="dialogue dialogue-{side}">'
                f'<img src="{img_prefix}{char["img"]}" alt="{name}" class="dialogue-avatar">'
                f'<div class="dialogue-bubble">'
                f'<span class="dialogue-name">{name}</span>'
                f'{text}'
                f'</div></div>'
            )
            continue

        # Steam OGP カード: !steam[appid](ゲーム名)
        steam_match = re.match(r'^!steam\[(\d+)\]\((.+?)\)\s*$', stripped)
        if steam_match:
            close_paragraph()
            s_appid = steam_match.group(1)
            s_name = steam_match.group(2)
            html_lines.append(
                f'<a href="https://store.steampowered.com/app/{s_appid}/" target="_blank" class="steam-ogp-card">'
                f'<img src="https://cdn.akamai.steamstatic.com/steam/apps/{s_appid}/header.jpg" alt="{s_name}" class="steam-ogp-img">'
                f'<span class="steam-ogp-name">{s_name}</span>'
                f'</a>'
            )
            continue

        # 画像: ![alt](src)
        img_match = re.match(r'^!\[(.+?)\]\((.+?)\)\s*$', stripped)
        if img_match:
            close_paragraph()
            alt = img_match.group(1)
            src = img_match.group(2)
            if src.startswith("img/"):
                src = img_prefix + src
            html_lines.append(
                f'<figure class="article-figure">'
                f'<img src="{src}" alt="{alt}" class="article-img">'
                f'<figcaption>{alt}</figcaption>'
                f'</figure>'
            )
            continue

        # 見出し
        if stripped.startswith("### "):
            close_paragraph()
            html_lines.append(f"<h3>{inline_markdown(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_paragraph()
            heading_text = stripped[3:]
            if "犬猫" in heading_text:
                close_pet_safety()
                pet_label = "Pet Safety" if lang == "en" else "犬猫の無事度"
                html_lines.append(
                    f'<div class="pet-safety-section">'
                    f'<div class="pet-safety-header">'
                    f'<span class="pet-safety-icon">🐾</span>'
                    f'<span class="pet-safety-label">{pet_label}</span>'
                    f'</div>'
                )
                in_pet_safety = True
            else:
                close_pet_safety()
                html_lines.append(f"<h2>{inline_markdown(heading_text)}</h2>")
        elif stripped.startswith("# "):
            close_paragraph()
            close_pet_safety()
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
    close_pet_safety()
    return "\n".join(html_lines)


def load_articles(content_dir: Path = CONTENT_DIR, lang: str = "ja", img_prefix: str = "../") -> dict:
    """指定ディレクトリの *.md を読み込み、slug → {meta, html} のマップを返す"""
    articles = {}
    if not content_dir.exists():
        return articles
    for md_file in sorted(content_dir.glob("*.md")):
        slug = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_markdown_frontmatter(text)
        html = simple_markdown_to_html(body, lang=lang, img_prefix=img_prefix)
        articles[slug] = {"meta": meta, "html": html, "slug": slug}
    return articles


def build_data_json(snapshot: dict, history: dict, articles: dict, articles_en: dict = None):
    """site/data/ にダッシュボード用JSONを出力"""
    data_dir = SITE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # games.json マスターからメタ情報を読み込み
    game_master = {}
    if GAMES_PATH.exists():
        with open(GAMES_PATH, encoding="utf-8") as f:
            for entry in json.load(f).get("games", []):
                game_master[entry["appid"]] = entry

    # ゲーム一覧（記事有無フラグ + recommend 付き）
    games = []
    for g in snapshot.get("games", []):
        slug = g.get("slug", "")
        g["has_article"] = slug in articles
        if slug in articles:
            g["article_title"] = articles[slug]["meta"].get("title", "")
        # recommend をマスターから補完
        if "recommend" not in g:
            master = game_master.get(g.get("appid"), {})
            g["recommend"] = master.get("recommend", "all")
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
            "lang": "ja",
        })
    if articles_en:
        for slug, art in articles_en.items():
            article_list.append({
                "slug": slug,
                "title": art["meta"].get("title", slug),
                "appid": art["meta"].get("appid", ""),
                "tags": art["meta"].get("tags", []),
                "lang": "en",
            })
    with open(data_dir / "articles.json", "w", encoding="utf-8") as f:
        json.dump(article_list, f, ensure_ascii=False, indent=2)


def build_article_pages(articles: dict, lang: str = "ja"):
    """Markdown記事をHTMLページとして出力"""
    if lang == "en":
        articles_dir = SITE_DIR / "articles" / "en"
        prefix = "../../"
        html_lang = "en"
        top_label = "Top"
        store_label = "Steam Store Page"
        site_name = "The Wonderful Steam Game Shelf"
        emotelab_credit = 'Characters in this article were created with <a href="https://store.steampowered.com/app/4301100/EmoteLab/" target="_blank">EmoteLab</a>.'
    else:
        articles_dir = SITE_DIR / "articles"
        prefix = "../"
        html_lang = "ja"
        top_label = "トップ"
        store_label = "Steam ストアページ"
        site_name = "すばらしきSteamゲームの本棚"
        emotelab_credit = 'この記事のキャラクターは <a href="https://store.steampowered.com/app/4301100/EmoteLab/" target="_blank">EmoteLab</a> で作成しました。'

    articles_dir.mkdir(parents=True, exist_ok=True)

    for slug, art in articles.items():
        meta = art["meta"]
        title = meta.get("title", slug)
        appid = meta.get("appid", "")

        if appid:
            ogp_card = (
                f'<a href="https://store.steampowered.com/app/{appid}/" target="_blank" class="steam-ogp-card">'
                f'<img src="https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg" alt="{title}" class="steam-ogp-img">'
                f'<span class="steam-ogp-name">{store_label}</span>'
                f'</a>'
            )
        else:
            ogp_card = ""

        html = f"""<!DOCTYPE html>
<html lang="{html_lang}" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | {site_name}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
<link rel="stylesheet" href="{prefix}style.css">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7086371722392050"
     crossorigin="anonymous"></script>
</head>
<body>
<main class="container">
  <nav class="breadcrumb">
    <a href="{prefix}">{top_label}</a> &gt; <span>{title}</span>
  </nav>
  <article class="article-content">
    <header>
      <h1>{title}</h1>
      {ogp_card}
    </header>
    {art["html"]}
  </article>

  <div style="text-align: center; margin: 20px auto; max-width: 800px;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-7086371722392050"
         data-ad-slot="4953305789" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
  </div>

  <div class="emotelab-credit">
    <p>{emotelab_credit}</p>
  </div>
</main>
<footer class="container">
  <p><a href="{prefix}">{site_name}</a> | Steam data &copy; <a href="https://store.steampowered.com/" target="_blank">Valve Corporation</a></p>
</footer>
</body>
</html>"""
        out_path = articles_dir / f"{slug}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  記事生成 ({lang}): {out_path.name}")


def main():
    print("サイトビルド開始...")

    snapshot = load_latest_snapshot()
    if not snapshot:
        print("スナップショットなし。先に fetch_steam.py を実行してください。")
        return

    history = load_price_history()
    articles = load_articles()
    articles_en = load_articles(CONTENT_EN_DIR, lang="en", img_prefix="../../")
    print(f"スナップショット: {snapshot['date']} ({len(snapshot['games'])}本)")
    print(f"記事: {len(articles)}本 (ja), {len(articles_en)}本 (en)")

    # data JSON 出力
    build_data_json(snapshot, history, articles, articles_en)
    print(f"データJSON出力完了")

    # 記事ページ生成
    if articles:
        build_article_pages(articles, lang="ja")
    if articles_en:
        build_article_pages(articles_en, lang="en")

    # i18n インライン JS 生成
    i18n_path = TEMPLATE_DIR / "i18n.json"
    if i18n_path.exists():
        with open(i18n_path, encoding="utf-8") as f:
            i18n_data = f.read().strip()
        with open(SITE_DIR / "i18n-data.js", "w", encoding="utf-8") as f:
            f.write(f"window.__i18n={i18n_data};")
        print("i18nインラインJS生成完了")

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
