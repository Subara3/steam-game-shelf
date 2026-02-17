#!/usr/bin/env python3
"""
Steam Game Shelf ビルド出力のテスト
デプロイ前に実行して問題を検出する
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows cp932対策
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
SITE_DIR = ROOT / "steam"


def test_json_syntax():
    """JSONファイルの構文チェック"""
    print("\n[JSON構文チェック]")
    errors = []

    json_files = list(ROOT.glob("data/**/*.json")) + list(SITE_DIR.glob("data/*.json"))
    root_json = ROOT / "games.json"
    if root_json.exists():
        json_files.append(root_json)

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"{jf.relative_to(ROOT)}: {e}")

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print(f"  [OK] {len(json_files)}個のJSONファイル OK")
    return errors


def test_python_syntax():
    """Pythonファイルの構文チェック"""
    print("\n[Python構文チェック]")
    errors = []

    py_files = list(ROOT.glob("*.py")) + list(ROOT.glob("tests/*.py"))

    for pf in py_files:
        try:
            with open(pf, "r", encoding="utf-8") as f:
                compile(f.read(), str(pf), "exec")
        except SyntaxError as e:
            errors.append(f"{pf.name}: line {e.lineno}: {e.msg}")

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print(f"  [OK] {len(py_files)}個のPythonファイル OK")
    return errors


def test_html_syntax():
    """HTMLの基本的な構文チェック"""
    print("\n[HTML構文チェック]")
    errors = []

    for html_file in SITE_DIR.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")

        for tag in ["div", "span", "a", "article", "section", "header", "footer"]:
            opens = len(re.findall(f"<{tag}[^>]*>", content, re.IGNORECASE))
            closes = len(re.findall(f"</{tag}>", content, re.IGNORECASE))
            if abs(opens - closes) > 5:
                errors.append(f"{html_file.name}: <{tag}> タグの開閉不一致 (開:{opens}, 閉:{closes})")

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [OK]")
    return errors


def test_css_mobile():
    """モバイルCSSの基本チェック"""
    print("\n[モバイルCSSチェック]")
    errors = []
    css_file = SITE_DIR / "style.css"

    if not css_file.exists():
        errors.append("style.css が存在しない")
    else:
        content = css_file.read_text(encoding="utf-8")
        if "@media" not in content:
            errors.append("メディアクエリがない")

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [OK]")
    return errors


def test_required_files():
    """必須ファイルの存在チェック"""
    print("\n[必須ファイルチェック]")

    required = [
        "steam/index.html",
        "steam/style.css",
        "steam/app.js",
        "steam/i18n-data.js",
        "steam/data/games.json",
        "templates/index.html",
        "templates/style.css",
        "templates/app.js",
        "templates/i18n.json",
        "games.json",
        "build_site.py",
    ]

    missing = [f for f in required if not (ROOT / f).exists()]

    if missing:
        for f in missing:
            print(f"  [FAIL] {f} が不足")
    else:
        print("  [OK]")
    return missing


def test_cache_busting():
    """キャッシュバスティングパラメータのチェック"""
    print("\n[キャッシュバスティングチェック]")
    errors = []
    index_file = SITE_DIR / "index.html"

    if not index_file.exists():
        errors.append("index.html が存在しない")
    else:
        content = index_file.read_text(encoding="utf-8")
        css_links = re.findall(r'href="[^"]*\.css(\?[^"]*)"', content)
        for link in css_links:
            if link.count("?") > 1:
                errors.append(f"CSS に二重のパラメータ: {link}")

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [OK]")
    return errors


def run_tests():
    print("=" * 60)
    print("Steam Game Shelf ビルドテスト")
    print("=" * 60)

    all_errors = []
    tests = [
        test_json_syntax,
        test_python_syntax,
        test_html_syntax,
        test_css_mobile,
        test_required_files,
        test_cache_busting,
    ]

    for test_func in tests:
        try:
            errors = test_func()
            all_errors.extend(errors)
        except Exception as ex:
            print(f"  [FAIL] テスト実行エラー: {ex}")
            all_errors.append(str(ex))

    print("\n" + "=" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} 件のエラー")
        return 1
    else:
        print("PASSED: すべてのテストに合格")
        return 0


if __name__ == "__main__":
    sys.exit(run_tests())
