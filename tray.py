"""System tray icon (background residence)."""

from __future__ import annotations

from typing import Callable, Optional

from PIL import Image
import pystray

from assets import resource_path
from make_icon import build_icon


def _load_image() -> Image.Image:
    ico = resource_path("icon.ico")
    if not ico.exists():
        build_icon(ico)
    return Image.open(ico)


class TrayIcon:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_quit: Callable[[], None],
        on_toggle_startup: Callable[[], None],
        startup_checked: Callable[[], bool],
    ) -> None:
        self._icon: Optional[pystray.Icon] = None
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", lambda *_: on_show(), default=True),
            pystray.MenuItem(
                "开机启动",
                lambda *_: on_toggle_startup(),
                checked=lambda _: startup_checked(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", lambda *_: on_quit()),
        )
        self._icon = pystray.Icon("PasteHistory", _load_image(), "粘贴历史", menu)

    def start(self) -> None:
        assert self._icon is not None
        self._icon.run_detached()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
