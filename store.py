"""Persistent clipboard history stored under %APPDATA%."""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

MAX_ITEMS = 300
MAX_CHARS = 200_000


def data_dir() -> Path:
    root = Path(os.environ.get("APPDATA") or Path.home()) / "PasteHistory"
    root.mkdir(parents=True, exist_ok=True)
    return root


def history_path() -> Path:
    return data_dir() / "history.json"


def show_request_path() -> Path:
    return data_dir() / "show.request"


@dataclass
class ClipItem:
    id: str
    text: str
    created_at: float
    pinned: bool = False

    def preview(self, width: int = 72) -> str:
        line = " ".join(self.text.split())
        if len(line) > width:
            return line[: width - 1] + "…"
        return line or "(空文本)"


class HistoryStore:
    def __init__(self) -> None:
        self.items: List[ClipItem] = []
        self.load()

    def load(self) -> None:
        path = history_path()
        if not path.exists():
            self.items = []
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entries = raw.get("items", raw if isinstance(raw, list) else [])
            self.items = [
                ClipItem(
                    id=str(e.get("id") or uuid.uuid4()),
                    text=str(e.get("text") or ""),
                    created_at=float(e.get("created_at") or time.time()),
                    pinned=bool(e.get("pinned")),
                )
                for e in entries
                if str(e.get("text") or "")
            ]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self.items = []

    def save(self) -> None:
        path = history_path()
        payload = {"items": [asdict(item) for item in self.items]}
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=0)
            os.replace(tmp, path)
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass

    def add(self, text: str) -> Optional[ClipItem]:
        text = text.replace("\x00", "")
        if not text or text.isspace():
            return None
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]
        existing = next((item for item in self.items if item.text == text), None)
        if existing:
            existing.created_at = time.time()
            self.items.remove(existing)
            self.items.insert(0, existing)
            self._trim()
            self.save()
            return existing
        item = ClipItem(id=uuid.uuid4().hex, text=text, created_at=time.time())
        self.items.insert(0, item)
        self._trim()
        self.save()
        return item

    def get(self, item_id: str) -> Optional[ClipItem]:
        return next((item for item in self.items if item.id == item_id), None)

    def remove(self, item_id: str) -> None:
        self.items = [item for item in self.items if item.id != item_id]
        self.save()

    def toggle_pin(self, item_id: str) -> Optional[ClipItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.pinned = not item.pinned
        self.save()
        return item

    def clear_unpinned(self) -> None:
        self.items = [item for item in self.items if item.pinned]
        self.save()

    def filtered(self, query: str) -> List[ClipItem]:
        q = query.strip().lower()
        pinned = [item for item in self.items if item.pinned]
        others = [item for item in self.items if not item.pinned]
        ordered = pinned + others
        if not q:
            return ordered
        return [item for item in ordered if q in item.text.lower()]

    def _trim(self) -> None:
        pinned = [item for item in self.items if item.pinned]
        others = [item for item in self.items if not item.pinned]
        keep = max(0, MAX_ITEMS - len(pinned))
        self.items = pinned + others[:keep]
