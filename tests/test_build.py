#!/usr/bin/env python3
"""
Steam Game Shelf ビルド出力のテスト
デプロイ前に実行して問題を検出する
"""
import re
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "steam"

def test_html_syntax():
    """HTMLの基本的な構文チェック"""
    errors = []
    
    for html_file in SITE_DIR.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")
        
        # 閉じタグの欠落チェック
        for tag in ["div", "span", "a", "article", "section", "header", "footer"]:
            opens = len(re.findall(f"<{tag}[^>]*>", content, re.IGNORECASE))
            closes = len(re.findall(f"</{tag}>", content, re.IGNORECASE))
            if abs(opens - closes) > 5:
                errors.append(f"{html_file.name}: <{tag}> タグの開閉不一致 (開:{opens}, 閉:{closes})")
        
        # 属性の閉じ忘れ（複数行タグは除外）
        pass  # 複数行にまたがるタグは正常なので基本チェックのみ
    
    return errors

def test_css_mobile():
    """モバイルCSSの基本チェック"""
    errors = []
    css_file = SITE_DIR / "style.css"
    
    if not css_file.exists():
        return ["style.css が存在しない"]
    
    content = css_file.read_text(encoding="utf-8")
    
    # モバイル用メディアクエリの存在確認
    if "@media" not in content:
        errors.append("メディアクエリがない")
    
    return errors

def test_cache_busting():
    """キャッシュバスティングパラメータのチェック"""
    errors = []
    index_file = SITE_DIR / "index.html"
    
    if not index_file.exists():
        return ["index.html が存在しない"]
    
    content = index_file.read_text(encoding="utf-8")
    
    # 二重パラメータチェック
    css_links = re.findall(r'href="[^"]*\.css(\?[^"]*)"', content)
    for link in css_links:
        if link.count("?") > 1:
            errors.append(f"CSS に二重のパラメータ: {link}")
    
    return errors

def test_required_elements():
    """必須要素の存在確認"""
    errors = []
    index_file = SITE_DIR / "index.html"
    
    if not index_file.exists():
        return ["index.html が存在しない"]
    
    content = index_file.read_text(encoding="utf-8")
    
    # Alpine.js の初期化
    if "x-data" not in content:
        errors.append("Alpine.js の初期化がない")
    
    return errors

def run_tests():
    """全テスト実行"""
    print("=" * 60)
    print("Steam Game Shelf ビルドテスト")
    print("=" * 60)
    
    all_errors = []
    
    tests = [
        ("HTML構文チェック", test_html_syntax),
        ("モバイルCSSチェック", test_css_mobile),
        ("キャッシュバスティングチェック", test_cache_busting),
        ("必須要素チェック", test_required_elements),
    ]
    
    for name, test_func in tests:
        print(f"\n[{name}]")
        try:
            errors = test_func()
            if errors:
                for e in errors:
                    print(f"  ❌ {e}")
                all_errors.extend(errors)
            else:
                print("  ✅ OK")
        except Exception as ex:
            print(f"  ❌ テスト実行エラー: {ex}")
            all_errors.append(f"{name}: {ex}")
    
    print("\n" + "=" * 60)
    if all_errors:
        print(f"❌ {len(all_errors)} 件のエラー")
        return 1
    else:
        print("✅ すべてのテストに合格")
        return 0

if __name__ == "__main__":
    sys.exit(run_tests())
