"""Clipboard history window."""

from __future__ import annotations

import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Callable, List, Optional

from store import ClipItem

BG = "#16171b"
SURFACE = "#1f2127"
SURFACE_2 = "#272a31"
ACCENT = "#5b8def"
TEXT = "#eceef2"
MUTED = "#8d919c"
PIN = "#e2b340"
DANGER = "#d36b6b"
SELECT = "#2c3f63"


def relative_time(ts: float) -> str:
    delta = max(0, time.time() - ts)
    if delta < 45:
        return "刚刚"
    if delta < 3600:
        return f"{int(delta // 60) or 1} 分钟前"
    if delta < 86400:
        return f"{int(delta // 3600)} 小时前"
    if delta < 86400 * 7:
        return f"{int(delta // 86400)} 天前"
    return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")


class HistoryWindow:
    def __init__(
        self,
        root: tk.Tk,
        on_copy: Callable[[ClipItem], None],
        on_delete: Callable[[str], None],
        on_pin: Callable[[str], None],
        on_clear: Callable[[], None],
        on_hide: Callable[[], None],
        on_quit: Callable[[], None],
        on_search: Callable[[str], List[ClipItem]],
        on_toggle_startup: Callable[[], None],
        startup_enabled: Callable[[], bool],
        hotkey_label: str,
    ) -> None:
        self.root = root
        self.on_copy = on_copy
        self.on_delete = on_delete
        self.on_pin = on_pin
        self.on_clear = on_clear
        self.on_hide = on_hide
        self.on_quit = on_quit
        self.on_search = on_search
        self.on_toggle_startup = on_toggle_startup
        self.startup_enabled = startup_enabled
        self.hotkey_label = hotkey_label
        self.visible_items: List[ClipItem] = []
        self._selected_id: Optional[str] = None

        self._build()
        self.refresh("")

    def _build(self) -> None:
        self.root.title("粘贴历史")
        self.root.configure(bg=BG)
        self.root.geometry("780x540")
        self.root.minsize(560, 400)
        self.root.protocol("WM_DELETE_WINDOW", self.on_hide)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 14))
        style.configure("TButton", font=("Segoe UI", 9), padding=(10, 5))

        outer = ttk.Frame(self.root, style="TFrame")
        outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        header = ttk.Frame(outer, style="TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="粘贴历史", style="Title.TLabel").pack(side=tk.LEFT)
        self.startup_var = tk.BooleanVar(value=self.startup_enabled())
        startup = tk.Checkbutton(
            header,
            text="开机启动",
            variable=self.startup_var,
            command=self.on_toggle_startup,
            bg=BG,
            fg=TEXT,
            activebackground=BG,
            activeforeground=TEXT,
            selectcolor=SURFACE,
            font=("Segoe UI", 9),
            highlightthickness=0,
        )
        startup.pack(side=tk.RIGHT)
        self.status = ttk.Label(header, text="", style="Muted.TLabel")
        self.status.pack(side=tk.RIGHT, padx=(0, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh(self.search_var.get()))
        search = tk.Entry(
            outer,
            textvariable=self.search_var,
            font=("Segoe UI", 11),
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#3a3d46",
            highlightcolor=ACCENT,
        )
        search.pack(fill=tk.X, pady=(12, 10), ipady=7)
        self.search = search
        self.search.bind("<Down>", lambda e: self._move(1) or "break")
        self.search.bind("<Up>", lambda e: self._move(-1) or "break")
        self.search.bind("<Return>", lambda e: self._copy_selected(hide=True) or "break")
        self.search.bind("<Escape>", lambda e: self.on_hide() or "break")
        self.search.bind("<Delete>", lambda e: self._delete_selected() or "break")
        self.search.bind("<Control-p>", lambda e: self._pin_selected() or "break")
        self.search.bind("<Control-P>", lambda e: self._pin_selected() or "break")

        body = ttk.Frame(outer, style="TFrame")
        body.pack(fill=tk.BOTH, expand=True)

        list_wrap = tk.Frame(body, bg=SURFACE, highlightthickness=1, highlightbackground="#32353d")
        list_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(
            list_wrap,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            bg=SURFACE,
            fg=TEXT,
            selectbackground=SELECT,
            selectforeground=TEXT,
            exportselection=False,
        )
        scroll = tk.Scrollbar(list_wrap, command=self.listbox.yview, bg=SURFACE)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=6, padx=(0, 4))
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._on_select())
        self.listbox.bind("<Double-Button-1>", lambda e: self._copy_selected(hide=True))
        self.listbox.bind("<Return>", lambda e: self._copy_selected(hide=True) or "break")
        self.listbox.bind("<Escape>", lambda e: self.on_hide() or "break")
        self.listbox.bind("<Delete>", lambda e: self._delete_selected() or "break")
        self.listbox.bind("<Control-c>", lambda e: self._copy_selected(hide=False) or "break")
        self.listbox.bind("<Control-p>", lambda e: self._pin_selected() or "break")

        preview_wrap = tk.Frame(body, bg=SURFACE_2, highlightthickness=1, highlightbackground="#32353d")
        preview_wrap.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        preview_wrap.configure(width=280)
        preview_wrap.pack_propagate(False)
        ttk.Label(preview_wrap, text="预览", style="Muted.TLabel").pack(anchor="w", padx=10, pady=(8, 4))
        self.preview = tk.Text(
            preview_wrap,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg=SURFACE_2,
            fg=TEXT,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=6,
            state=tk.DISABLED,
        )
        self.preview.pack(fill=tk.BOTH, expand=True)
        self.meta = ttk.Label(preview_wrap, text="", style="Muted.TLabel")
        self.meta.pack(anchor="w", padx=10, pady=(0, 8))

        footer = ttk.Frame(outer, style="TFrame")
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(footer, text="复制", command=lambda: self._copy_selected(hide=True)).pack(side=tk.LEFT)
        ttk.Button(footer, text="固定 / 取消", command=self._pin_selected).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(footer, text="删除", command=self._delete_selected).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(footer, text="清空未固定", command=self._confirm_clear).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(footer, text="退出", command=self.on_quit).pack(side=tk.RIGHT)
        hint = f"{self.hotkey_label or 'Ctrl+Shift+V'} 呼出  ·  关闭窗口后继续在托盘运行"
        ttk.Label(footer, text=hint, style="Muted.TLabel").pack(side=tk.RIGHT, padx=(0, 12))

        self.root.bind("<Escape>", lambda e: self.on_hide())
        self.root.bind("<Control-q>", lambda e: self.on_quit())
        self.root.bind("<Control-f>", lambda e: (self.search.focus_set(), self.search.select_range(0, tk.END)))

    def set_hotkey_label(self, label: str) -> None:
        self.hotkey_label = label

    def sync_startup(self) -> None:
        self.startup_var.set(self.startup_enabled())

    def refresh(self, query: Optional[str] = None) -> None:
        if query is None:
            query = self.search_var.get()
        keep_id = self._selected_id
        self.visible_items = self.on_search(query)
        self.listbox.delete(0, tk.END)
        for item in self.visible_items:
            pin = "★ " if item.pinned else "   "
            self.listbox.insert(tk.END, f"{pin}{item.preview(64)}    {relative_time(item.created_at)}")
        self.status.configure(text=f"{len(self.visible_items)} 条")
        index = next((i for i, item in enumerate(self.visible_items) if item.id == keep_id), 0)
        if self.visible_items:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            self.listbox.see(index)
            self._selected_id = self.visible_items[index].id
            self._render_preview(self.visible_items[index])
        else:
            self._selected_id = None
            self._render_preview(None)

    def focus_search(self) -> None:
        self.search.focus_set()
        self.search.select_range(0, tk.END)

    def _current(self) -> Optional[ClipItem]:
        selection = self.listbox.curselection()
        if not selection:
            return None
        index = int(selection[0])
        if 0 <= index < len(self.visible_items):
            return self.visible_items[index]
        return None

    def _on_select(self) -> None:
        item = self._current()
        self._selected_id = item.id if item else None
        self._render_preview(item)

    def _render_preview(self, item: Optional[ClipItem]) -> None:
        self.preview.configure(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        if item:
            self.preview.insert("1.0", item.text)
            self.meta.configure(
                text=f"{len(item.text)} 字符  ·  {relative_time(item.created_at)}"
                + ("  ·  已固定" if item.pinned else "")
            )
        else:
            self.preview.insert("1.0", "没有匹配的记录。复制任意文本后会出现在这里。")
            self.meta.configure(text="")
        self.preview.configure(state=tk.DISABLED)

    def _move(self, delta: int) -> None:
        if not self.visible_items:
            return
        selection = self.listbox.curselection()
        index = int(selection[0]) if selection else 0
        index = max(0, min(len(self.visible_items) - 1, index + delta))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
        self._on_select()

    def _copy_selected(self, hide: bool) -> None:
        item = self._current()
        if not item:
            return
        self.on_copy(item)
        if hide:
            self.on_hide()

    def _delete_selected(self) -> None:
        item = self._current()
        if not item:
            return
        self.on_delete(item.id)
        self.refresh()

    def _pin_selected(self) -> None:
        item = self._current()
        if not item:
            return
        self.on_pin(item.id)
        self.refresh()

    def _confirm_clear(self) -> None:
        if messagebox.askyesno("清空", "删除所有未固定的记录？"):
            self.on_clear()
            self.refresh()
