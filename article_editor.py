"""Steam記事エディタ - 対話形式の記事を編集するGUIツール

Usage: python article_editor.py
"""

import re
import sys
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content"
CONTENT_EN_DIR = CONTENT_DIR / "en"
TEMPLATE_DIR = BASE_DIR / "templates"
STYLE_PATH = TEMPLATE_DIR / "style.css"
IMG_DIR = TEMPLATE_DIR / "img"

sys.path.insert(0, str(BASE_DIR))
from build_site import (
    simple_markdown_to_html,
    parse_markdown_frontmatter,
    DIALOGUE_CHARS,
)


class ArticleEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Steam記事エディタ - 新規")
        self.geometry("1280x820")
        self.current_file = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#1b2838", foreground="#c7d5e0")
        style.configure("TLabelframe", background="#1b2838", foreground="#66c0f4")
        style.configure("TLabelframe.Label", background="#1b2838", foreground="#66c0f4")
        style.configure("TFrame", background="#1b2838")
        style.configure("TLabel", background="#1b2838", foreground="#c7d5e0")
        style.configure("TButton", background="#2a3f5f", foreground="#c7d5e0")
        style.map("TButton", background=[("active", "#66c0f4")])
        style.configure("Accent.TButton", background="#4c6b22", foreground="#a4d007")
        style.map("Accent.TButton", background=[("active", "#5c8b2a")])
        style.configure("TCombobox", fieldbackground="#16202d", foreground="#c7d5e0")
        style.configure("TEntry", fieldbackground="#16202d", foreground="#c7d5e0")
        self.configure(bg="#1b2838")

        self._build_menu()
        self._build_frontmatter_bar()
        self._build_toolbar()
        self._build_editor()
        self._build_status_bar()

    # ───── メニュー ─────
    def _build_menu(self):
        menubar = tk.Menu(self, bg="#16202d", fg="#c7d5e0",
                          activebackground="#66c0f4", activeforeground="#1b2838")

        file_menu = tk.Menu(menubar, tearoff=0, bg="#16202d", fg="#c7d5e0",
                            activebackground="#66c0f4", activeforeground="#1b2838")
        file_menu.add_command(label="新規  Ctrl+N", command=self.new_file)
        file_menu.add_command(label="開く  Ctrl+O", command=self.open_file)
        file_menu.add_command(label="保存  Ctrl+S", command=self.save_file)
        file_menu.add_command(label="名前を付けて保存", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="ブラウザプレビュー  Ctrl+P", command=self.preview_browser)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        self.config(menu=menubar)
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-p>", lambda e: self.preview_browser())

    # ───── フロントマター ─────
    def _build_frontmatter_bar(self):
        frame = ttk.LabelFrame(self, text="記事情報", padding=8)
        frame.pack(fill="x", padx=8, pady=(8, 2))

        ttk.Label(frame, text="タイトル:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.title_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.title_var, width=48).grid(row=0, column=1, padx=(0, 16))

        ttk.Label(frame, text="AppID:").grid(row=0, column=2, sticky="w", padx=(0, 4))
        self.appid_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.appid_var, width=10).grid(row=0, column=3, padx=(0, 16))

        ttk.Label(frame, text="タグ:").grid(row=0, column=4, sticky="w", padx=(0, 4))
        self.tags_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.tags_var, width=28).grid(row=0, column=5, padx=(0, 16))

        ttk.Label(frame, text="言語:").grid(row=0, column=6, sticky="w", padx=(0, 4))
        self.lang_var = tk.StringVar(value="ja")
        combo = ttk.Combobox(frame, textvariable=self.lang_var,
                             values=["ja", "en"], width=4, state="readonly")
        combo.grid(row=0, column=7)
        combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

    # ───── ツールバー ─────
    def _build_toolbar(self):
        frame = ttk.Frame(self, padding=(8, 4))
        frame.pack(fill="x")

        ttk.Button(frame, text="Dr.スカラ",
                   command=lambda: self._insert_dialogue("scala")).pack(side="left", padx=2)
        ttk.Button(frame, text="ことり",
                   command=lambda: self._insert_dialogue("kotori")).pack(side="left", padx=2)

        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=10, pady=2)

        ttk.Button(frame, text="## 見出し",
                   command=self._insert_heading).pack(side="left", padx=2)
        ttk.Button(frame, text="**太字**",
                   command=self._insert_bold).pack(side="left", padx=2)

        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=10, pady=2)

        ttk.Button(frame, text="ブラウザプレビュー", style="Accent.TButton",
                   command=self.preview_browser).pack(side="left", padx=2)

    # ───── エディタ + プレビュー ─────
    def _build_editor(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=(2, 4))

        # エディタ
        ef = ttk.LabelFrame(paned, text="Markdown")
        self.editor = scrolledtext.ScrolledText(
            ef, wrap="word", font=("Consolas", 11), undo=True,
            bg="#16202d", fg="#c7d5e0", insertbackground="#66c0f4",
            selectbackground="#2a3f5f", borderwidth=0, padx=8, pady=8,
        )
        self.editor.pack(fill="both", expand=True, padx=2, pady=2)
        paned.add(ef, weight=1)

        # プレビュー
        pf = ttk.LabelFrame(paned, text="プレビュー")
        self.preview = scrolledtext.ScrolledText(
            pf, wrap="word", font=("Yu Gothic UI", 11),
            bg="#1b2838", fg="#c7d5e0", state="disabled",
            borderwidth=0, padx=8, pady=8,
        )
        self.preview.pack(fill="both", expand=True, padx=2, pady=2)
        paned.add(pf, weight=1)

        # プレビュータグ
        self.preview.tag_configure("h1", font=("Yu Gothic UI", 18, "bold"), foreground="#ffffff",
                                   spacing3=8)
        self.preview.tag_configure("h2", font=("Yu Gothic UI", 15, "bold"), foreground="#ffffff",
                                   spacing1=12, spacing3=6)
        self.preview.tag_configure("h3", font=("Yu Gothic UI", 13, "bold"), foreground="#ffffff",
                                   spacing1=10, spacing3=4)
        self.preview.tag_configure("scala_name", font=("Yu Gothic UI", 9, "bold"),
                                   foreground="#4fc3f7")
        self.preview.tag_configure("kotori_name", font=("Yu Gothic UI", 9, "bold"),
                                   foreground="#81c784")
        self.preview.tag_configure("dialogue", font=("Yu Gothic UI", 11),
                                   foreground="#c7d5e0", lmargin1=16, lmargin2=16, spacing3=8)
        self.preview.tag_configure("body", font=("Yu Gothic UI", 11), foreground="#c7d5e0")
        self.preview.tag_configure("spacer", font=("Yu Gothic UI", 6))

        self.editor.bind("<KeyRelease>", self._update_preview)

    # ───── ステータスバー ─────
    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="新規ファイル")
        bar = tk.Label(self, textvariable=self.status_var, anchor="w",
                       bg="#171a21", fg="#8f98a0", padx=8, pady=3, font=("Yu Gothic UI", 9))
        bar.pack(fill="x", side="bottom")

    # ───── 挿入ヘルパー ─────
    def _insert_dialogue(self, char_id):
        pos = self.editor.index("insert")
        line_text = self.editor.get(f"{pos} linestart", pos)
        prefix = "\n" if line_text.strip() else ""
        self.editor.insert("insert", f"{prefix}> {char_id}: ")
        self.editor.focus_set()
        self._update_preview()

    def _insert_heading(self):
        pos = self.editor.index("insert")
        line_text = self.editor.get(f"{pos} linestart", pos)
        prefix = "\n" if line_text.strip() else ""
        self.editor.insert("insert", f"{prefix}## ")
        self.editor.focus_set()
        self._update_preview()

    def _insert_bold(self):
        try:
            sel = self.editor.get("sel.first", "sel.last")
            self.editor.delete("sel.first", "sel.last")
            self.editor.insert("insert", f"**{sel}**")
        except tk.TclError:
            self.editor.insert("insert", "****")
            pos = self.editor.index("insert")
            self.editor.mark_set("insert", f"{pos}-2c")
        self.editor.focus_set()
        self._update_preview()

    # ───── フロントマター入出力 ─────
    def _get_frontmatter_text(self):
        tags = self.tags_var.get().strip()
        if tags:
            tags_str = "[" + ", ".join(t.strip() for t in tags.split(",")) + "]"
        else:
            tags_str = "[]"
        return (
            f"---\n"
            f"title: {self.title_var.get()}\n"
            f"appid: {self.appid_var.get()}\n"
            f"tags: {tags_str}\n"
            f"---\n"
        )

    def _set_frontmatter_from_text(self, text: str) -> str:
        meta, body = parse_markdown_frontmatter(text)
        self.title_var.set(meta.get("title", ""))
        self.appid_var.set(meta.get("appid", ""))
        tags = meta.get("tags", [])
        self.tags_var.set(", ".join(tags) if isinstance(tags, list) else str(tags))
        return body

    def _get_full_content(self) -> str:
        return self._get_frontmatter_text() + "\n" + self.editor.get("1.0", "end-1c")

    # ───── ファイル操作 ─────
    def new_file(self):
        self.current_file = None
        self.title_var.set("")
        self.appid_var.set("")
        self.tags_var.set("")
        self.lang_var.set("ja")
        self.editor.delete("1.0", "end")
        self.title("Steam記事エディタ - 新規")
        self.status_var.set("新規ファイル")
        self._update_preview()

    def open_file(self):
        lang = self.lang_var.get()
        init_dir = CONTENT_EN_DIR if lang == "en" else CONTENT_DIR
        if not init_dir.exists():
            init_dir = CONTENT_DIR
        path = filedialog.askopenfilename(
            initialdir=str(init_dir),
            filetypes=[("Markdown", "*.md"), ("All", "*.*")],
        )
        if not path:
            return
        with open(path, encoding="utf-8") as f:
            text = f.read()
        body = self._set_frontmatter_from_text(text)

        # パスから言語を判定
        if "\\en\\" in path or "/en/" in path:
            self.lang_var.set("en")
        else:
            self.lang_var.set("ja")

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", body.lstrip("\n"))
        self.current_file = path
        self.title(f"Steam記事エディタ - {Path(path).name}")
        self.status_var.set(path)
        self._update_preview()

    def save_file(self):
        if self.current_file:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self._get_full_content())
            self.status_var.set(f"保存: {self.current_file}")
        else:
            self.save_as()

    def save_as(self):
        lang = self.lang_var.get()
        init_dir = CONTENT_EN_DIR if lang == "en" else CONTENT_DIR
        init_dir.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            initialdir=str(init_dir),
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._get_full_content())
        self.current_file = path
        self.title(f"Steam記事エディタ - {Path(path).name}")
        self.status_var.set(f"保存: {path}")

    # ───── ライブプレビュー ─────
    def _update_preview(self, event=None):
        text = self.editor.get("1.0", "end-1c")
        lang = self.lang_var.get()
        name_key = f"name_{lang}"

        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")

        for line in text.split("\n"):
            stripped = line.strip()

            # 対話
            m = re.match(r'^>\s*(scala|kotori)\s*:\s*(.+)', stripped)
            if m:
                char_id = m.group(1)
                content = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(2))
                name = DIALOGUE_CHARS[char_id].get(name_key, char_id)
                self.preview.insert("end", f"  {name}:\n", f"{char_id}_name")
                self.preview.insert("end", f"  {content}\n", "dialogue")
                continue

            if stripped.startswith("### "):
                self.preview.insert("end", f"{stripped[4:]}\n", "h3")
            elif stripped.startswith("## "):
                self.preview.insert("end", f"{stripped[3:]}\n", "h2")
            elif stripped.startswith("# "):
                self.preview.insert("end", f"{stripped[2:]}\n", "h1")
            elif stripped == "":
                self.preview.insert("end", "\n", "spacer")
            else:
                clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
                self.preview.insert("end", f"{clean}\n", "body")

        self.preview.config(state="disabled")

    # ───── ブラウザプレビュー ─────
    def preview_browser(self):
        md_text = self.editor.get("1.0", "end-1c")
        lang = self.lang_var.get()
        title = self.title_var.get() or "プレビュー"
        appid = self.appid_var.get()

        # 画像パスをローカルファイルに
        img_uri = IMG_DIR.as_uri() + "/"
        html_body = simple_markdown_to_html(md_text, lang=lang, img_prefix=img_uri)

        # CSS読み込み
        css = STYLE_PATH.read_text(encoding="utf-8") if STYLE_PATH.exists() else ""

        store_label = "Steam Store Page" if lang == "en" else "Steam ストアページ"
        store_link = (
            f'<a href="https://store.steampowered.com/app/{appid}/" '
            f'target="_blank" class="steam-link">{store_label}</a>'
        ) if appid else ""

        html = f"""<!DOCTYPE html>
<html lang="{lang}" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | プレビュー</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
<style>
{css}
</style>
</head>
<body>
<main class="container">
  <article class="article-content">
    <header>
      <h1>{title}</h1>
      {store_link}
    </header>
    {html_body}
  </article>
  <div class="emotelab-credit">
    <p>{'Characters created with' if lang == 'en' else 'キャラクターは'}
       <a href="https://store.steampowered.com/app/4301100/EmoteLab/" target="_blank">EmoteLab</a>
       {'.' if lang == 'en' else 'で作成しました。'}</p>
  </div>
</main>
</body>
</html>"""

        tmp = Path(tempfile.gettempdir()) / "steam_article_preview.html"
        tmp.write_text(html, encoding="utf-8")
        webbrowser.open(tmp.as_uri())
        self.status_var.set(f"プレビュー: {tmp}")


if __name__ == "__main__":
    app = ArticleEditor()
    app.mainloop()
