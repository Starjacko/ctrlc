"""Global hotkey via RegisterHotKey, delivered through a queue."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import queue
import threading
from typing import Optional, Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_V = 0x56
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

HOTKEY_CANDIDATES: Tuple[Tuple[int, int, str], ...] = (
    (MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_V, "Ctrl+Shift+V"),
    (MOD_CONTROL | MOD_SHIFT, VK_V, "Ctrl+Shift+V"),
    (MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_V, "Ctrl+Alt+V"),
    (MOD_CONTROL | MOD_ALT, VK_V, "Ctrl+Alt+V"),
)


class HotkeyListener:
    def __init__(self, events: queue.Queue[str]) -> None:
        self.events = events
        self.label = ""
        self._thread_id: Optional[int] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        self._thread = threading.Thread(target=self._run, name="hotkey", daemon=True)
        self._thread.start()
        return self.label

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        registered = False
        for mods, vk, label in HOTKEY_CANDIDATES:
            if user32.RegisterHotKey(None, 1, mods, vk):
                self.label = label
                registered = True
                break
            err = ctypes.get_last_error()
            if err not in (0, ERROR_HOTKEY_ALREADY_REGISTERED):
                continue
        if not registered:
            self.events.put("hotkey-failed")
            return
        self.events.put(f"hotkey-ready:{self.label}")
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                self.events.put("show")
        user32.UnregisterHotKey(None, 1)
