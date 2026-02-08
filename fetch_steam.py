"""
Steam Store API からゲーム情報を取得し、data/snapshots/ に保存する。
EN/JP 両方をフェッチして1レコードにまとめる。
外部依存: なし（stdlib のみ）
"""

import json
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
        "genres": [g["description"] for g in raw_ja.get("genres", [])],
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
