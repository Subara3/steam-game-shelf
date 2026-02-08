"""
Steam Store API からゲーム情報を取得し、data/snapshots/ に保存する。
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
        print(f"  API エラー (appid={appid}): {e}")
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


def extract_game_info(raw: dict, reviews: dict) -> dict:
    """API レスポンスから必要なフィールドを抽出"""
    price = raw.get("price_overview", {})
    metacritic = raw.get("metacritic", {})
    release = raw.get("release_date", {})
    platforms = raw.get("platforms", {})

    return {
        "appid": raw.get("steam_appid"),
        "name": raw.get("name", ""),
        "short_description": raw.get("short_description", ""),
        "header_image": raw.get("header_image", ""),
        "developers": raw.get("developers", []),
        "publishers": raw.get("publishers", []),
        "genres": [g["description"] for g in raw.get("genres", [])],
        "categories": [c["description"] for c in raw.get("categories", [])],
        "release_date": release.get("date", ""),
        "is_free": raw.get("is_free", False),
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
        "screenshots": [s["path_full"] for s in raw.get("screenshots", [])[:5]],
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

        raw = fetch_app_details(appid)
        if not raw:
            print(f"    スキップ: データ取得失敗")
            continue

        reviews = fetch_reviews(appid)
        info = extract_game_info(raw, reviews)
        info["slug"] = slug
        info["fetched_at"] = timestamp
        results.append(info)

        # 個別ファイル保存
        detail_path = SNAPSHOTS_DIR / f"{appid}.json"
        with open(detail_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        time.sleep(1.5)  # レートリミット対策

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
