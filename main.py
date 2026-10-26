"""Clipboard history tool for Windows."""

from __future__ import annotations

import ctypes
import logging
import queue
import sys
import time
import tkinter as tk
import traceback

import clipboard_win
import startup
from hotkey_win import HotkeyListener
from store import HistoryStore, show_request_path
from tray import TrayIcon
from ui import HistoryWindow

MUTEX_NAME = "Local\\PasteHistoryToolSingleton"
POLL_MS = 180
IGNORE_COPY_WINDOW = 0.8

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
kernel32.CreateMutexW.restype = ctypes.c_void_p
ERROR_ALREADY_EXISTS = 183


def setup_logging() -> None:
    from store import data_dir

    log_file = data_dir() / "app.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def acquire_singleton() -> bool:
    handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if not handle:
        return True
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        try:
            show_request_path().write_text(str(time.time()), encoding="utf-8")
        except OSError:
            pass
        return False
    return True


class App:
    def __init__(self) -> None:
        self.store = HistoryStore()
        self.events: queue.Queue[str] = queue.Queue()
        self.hotkey = HotkeyListener(self.events)
        self.last_seq = clipboard_win.clipboard_sequence()
        self.ignore_until = 0.0
        self.hidden = True
        self.hotkey_label = "Ctrl+Shift+V"
        self._quitting = False

        self.root = tk.Tk()
        self.root.withdraw()
        self.window = HistoryWindow(
            self.root,
            on_copy=self.copy_item,
            on_delete=self.delete_item,
            on_pin=self.pin_item,
            on_clear=self.clear_unpinned,
            on_hide=self.hide,
            on_quit=self.quit,
            on_search=self.store.filtered,
            on_toggle_startup=self.toggle_startup,
            startup_enabled=startup.is_enabled,
            hotkey_label=self.hotkey_label,
        )
        self.tray = TrayIcon(
            on_show=lambda: self.root.after(0, self.show),
            on_quit=lambda: self.root.after(0, self.quit),
            on_toggle_startup=lambda: self.root.after(0, self.toggle_startup),
            startup_checked=startup.is_enabled,
        )
        self.hotkey.start()
        self.tray.start()
        self.root.after(POLL_MS, self._tick)

    def run(self) -> None:
        self.root.mainloop()

    def _tick(self) -> None:
        if self._quitting:
            return
        self._poll_clipboard()
        self._drain_events()
        self._poll_show_request()
        self.root.after(POLL_MS, self._tick)

    def _poll_clipboard(self) -> None:
        seq = clipboard_win.clipboard_sequence()
        if seq == self.last_seq:
            return
        self.last_seq = seq
        if time.time() < self.ignore_until:
            return
        text = clipboard_win.get_text()
        if not text:
            return
        added = self.store.add(text)
        if added and not self.hidden:
            self.window.refresh()

    def _drain_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "show":
                self.show()
            elif event.startswith("hotkey-ready:"):
                self.hotkey_label = event.split(":", 1)[1]
                self.window.set_hotkey_label(self.hotkey_label)
                logging.info("Hotkey ready: %s", self.hotkey_label)
            elif event == "hotkey-failed":
                logging.warning("Failed to register a global hotkey")

    def _poll_show_request(self) -> None:
        path = show_request_path()
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
            self.show()

    def copy_item(self, item) -> None:
        self.ignore_until = time.time() + IGNORE_COPY_WINDOW
        if clipboard_win.set_text(item.text):
            self.last_seq = clipboard_win.clipboard_sequence()
            self.store.add(item.text)
            self.window.refresh()

    def delete_item(self, item_id: str) -> None:
        self.store.remove(item_id)

    def pin_item(self, item_id: str) -> None:
        self.store.toggle_pin(item_id)

    def clear_unpinned(self) -> None:
        self.store.clear_unpinned()

    def toggle_startup(self) -> None:
        startup.set_enabled(not startup.is_enabled())
        self.window.sync_startup()

    def show(self) -> None:
        self.hidden = False
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(120, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        self.window.refresh()
        self.window.focus_search()

    def hide(self) -> None:
        self.hidden = True
        self.root.withdraw()

    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        try:
            self.tray.stop()
        except Exception:
            logging.exception("Failed to stop tray icon")
        try:
            self.hotkey.stop()
        except Exception:
            logging.exception("Failed to stop hotkey listener")
        self.root.destroy()


def main() -> int:
    if sys.platform != "win32":
        print("This tool currently supports Windows only.")
        return 1
    enable_dpi_awareness()
    setup_logging()
    if not acquire_singleton():
        return 0
    try:
        App().run()
    except Exception:
        logging.error(traceback.format_exc())
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
