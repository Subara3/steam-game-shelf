"""
Steam Store API からゲーム情報を取得し、data/snapshots/ に保存する。
EN/JP 両方をフェッチして1レコードにまとめる。
外部依存: なし（stdlib のみ）
"""

import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GAMES_PATH = BASE_DIR / "games.json"
SNAPSHOTS_DIR = BASE_DIR / "data" / "snapshots"

STORE_API = "https://store.steampowered.com/api/appdetails"
REVIEW_API = "https://store.steampowered.com/appreviews"
TAG_LOOKUP_API = "https://store.steampowered.com/tagdata/populartags"


def load_games() -> list[dict]:
    with open(GAMES_PATH, encoding="utf-8") as f:
        return json.load(f)["games"]


def fetch_app_details(appid: int, lang: str = "japanese") -> dict | None:
    """Steam Store API から1本のゲーム情報を取得"""
    url = f"{STORE_API}?appids={appid}&l={lang}&cc=JP"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SteamGameShelf/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        entry = data.get(str(appid), {})
        if entry.get("success"):
            return entry["data"]
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"  API エラー (appid={appid}, lang={lang}): {e}")
    return None


def fetch_reviews(appid: int) -> dict:
    """レビュー統計を取得"""
    url = f"{REVIEW_API}/{appid}?json=1&language=all&purchase_type=all&num_per_page=0"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SteamGameShelf/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        summary = data.get("query_summary", {})
        return {
            "total_reviews": summary.get("total_reviews", 0),
            "total_positive": summary.get("total_positive", 0),
            "total_negative": summary.get("total_negative", 0),
            "review_score_desc": summary.get("review_score_desc", ""),
        }
    except Exception:
        return {}


def fetch_tag_lookup(lang: str = "japanese") -> dict[int, str]:
    """Steam タグID→名前のマッピングを取得"""
    url = f"{TAG_LOOKUP_API}/{lang}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SteamGameShelf/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return {t["tagid"]: t["name"] for t in data}
    except Exception as e:
        print(f"  タグ辞書取得エラー ({lang}): {e}")
        return {}


def fetch_user_tags(appid: int) -> list[dict]:
    """Steam ストアページからユーザータグ（人気タグ）を取得"""
    url = f"https://store.steampowered.com/app/{appid}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "birthtime=0; wants_mature_content=1; lastagecheckage=1-0-1990",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
        match = re.search(r'InitAppTagModal\(\s*\d+,\s*(\[.*?\])', html, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group(1))
    except Exception as e:
        print(f"  タグ取得エラー (appid={appid}): {e}")
        return []


def extract_game_info(raw_ja: dict, raw_en: dict | None, reviews: dict) -> dict:
    """JP/EN の API レスポンスから必要なフィールドを抽出・統合"""
    price = raw_ja.get("price_overview", {})
    metacritic = raw_ja.get("metacritic", {})
    release_ja = raw_ja.get("release_date", {})
    platforms = raw_ja.get("platforms", {})
    en = raw_en or {}

    # デモ
    demos = raw_ja.get("demos", [])
    demo_appid = demos[0]["appid"] if demos else None

    # トレーラー
    movies = []
    for m in raw_ja.get("movies", []):
        mp4 = m.get("mp4", {})
        movies.append({
            "name": m.get("name", ""),
            "thumbnail": m.get("thumbnail", ""),
            "url_480": mp4.get("480", ""),
            "url_max": mp4.get("max", ""),
        })

    # EN/JP 名前・説明文
    name_ja = raw_ja.get("name", "")
    name_en = en.get("name", name_ja)
    desc_ja = raw_ja.get("short_description", "")
    desc_en = en.get("short_description", desc_ja)
    release_en = en.get("release_date", {})

    return {
        "appid": raw_ja.get("steam_appid"),
        "required_age": int(raw_ja.get("required_age", 0) or 0),
        "name_ja": name_ja,
        "name_en": name_en,
        "name": name_en,  # 後方互換
        "short_description_ja": desc_ja,
        "short_description_en": desc_en,
        "short_description": desc_ja,  # 後方互換
        "header_image": raw_ja.get("header_image", ""),
        "capsule_image": raw_ja.get("capsule_image", ""),
        "developers": raw_ja.get("developers", []),
        "publishers": raw_ja.get("publishers", []),
        "genres_ja": [g["description"] for g in raw_ja.get("genres", [])],
        "genres_en": [g["description"] for g in en.get("genres", raw_ja.get("genres", []))],
        "genres": [g["description"] for g in raw_ja.get("genres", [])],  # 後方互換
        "categories": [c["description"] for c in raw_ja.get("categories", [])],
        "release_date_ja": release_ja.get("date", ""),
        "release_date_en": release_en.get("date", release_ja.get("date", "")),
        "release_date": release_ja.get("date", ""),  # 後方互換
        "is_free": raw_ja.get("is_free", False),
        "price_initial": price.get("initial", 0),
        "price_final": price.get("final", 0),
        "discount_percent": price.get("discount_percent", 0),
        "price_formatted": price.get("final_formatted", ""),
        "currency": price.get("currency", "JPY"),
        "metacritic_score": metacritic.get("score"),
        "platforms": {
            "windows": platforms.get("windows", False),
            "mac": platforms.get("mac", False),
            "linux": platforms.get("linux", False),
        },
        "supported_languages": raw_ja.get("supported_languages", ""),
        "website": raw_ja.get("website", ""),
        "screenshots": [s["path_full"] for s in raw_ja.get("screenshots", [])[:5]],
        "movies": movies,
        "demo_appid": demo_appid,
        "recommendations_total": raw_ja.get("recommendations", {}).get("total", 0),
        "total_reviews": reviews.get("total_reviews", 0),
        "total_positive": reviews.get("total_positive", 0),
        "total_negative": reviews.get("total_negative", 0),
        "review_score_desc": reviews.get("review_score_desc", ""),
    }


def main():
    games = load_games()
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.isoformat()

    results = []

    # タグ辞書を取得（JP/EN）
    print("タグ辞書を取得中...")
    tag_names_ja = fetch_tag_lookup("japanese")
    time.sleep(1)
    tag_names_en = fetch_tag_lookup("english")
    time.sleep(1)
    print(f"  タグ辞書: {len(tag_names_ja)}件 (ja), {len(tag_names_en)}件 (en)")

    print(f"Steam ゲーム情報取得 ({len(games)}本)")
    for i, game in enumerate(games, 1):
        appid = game["appid"]
        slug = game["slug"]
        print(f"  [{i}/{len(games)}] {slug} (appid={appid})")

        raw_ja = fetch_app_details(appid, "japanese")
        if not raw_ja:
            print(f"    スキップ: JP データ取得失敗")
            continue
        time.sleep(1)

        raw_en = fetch_app_details(appid, "english")
        time.sleep(1)

        reviews = fetch_reviews(appid)

        info = extract_game_info(raw_ja, raw_en, reviews)
        info["slug"] = slug
        info["recommend"] = game.get("recommend", "all")
        if game.get("coming_soon"):
            info["coming_soon"] = True
        if game.get("free_section"):
            info["free_section"] = True
        if game.get("multi"):
            info["multi"] = True
        if game.get("by"):
            info["by"] = game["by"]

        # ユーザータグ取得（上位8件）
        user_tags = fetch_user_tags(appid)
        top_tags = user_tags[:8]
        info["tags_ja"] = [tag_names_ja.get(t["tagid"], t["name"]) for t in top_tags]
        info["tags_en"] = [tag_names_en.get(t["tagid"], t["name"]) for t in top_tags]
        if top_tags:
            print(f"    タグ: {', '.join(info['tags_en'][:5])}")
        time.sleep(1)

        info["fetched_at"] = timestamp
        results.append(info)

        # 個別ファイル保存
        detail_path = SNAPSHOTS_DIR / f"{appid}.json"
        with open(detail_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        time.sleep(1)

    # 日次スナップショット
    snapshot = {
        "date": today,
        "timestamp": timestamp,
        "games": results,
    }
    snapshot_path = SNAPSHOTS_DIR / f"{today}.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"\n完了: {len(results)}本取得, スナップショット: {snapshot_path}")


if __name__ == "__main__":
    main()
