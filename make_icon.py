"""Create a simple clipboard icon for the tray and the exe."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def build_icon(path: Path) -> None:
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((36, 40, 220, 236), radius=32, fill=(31, 33, 39, 255))
    draw.rounded_rectangle((36, 40, 220, 236), radius=32, outline=(91, 141, 239, 255), width=10)
    draw.rounded_rectangle((86, 18, 170, 62), radius=14, fill=(91, 141, 239, 255))
    for y in (96, 132, 168):
        draw.rounded_rectangle((68, y, 188, y + 20), radius=8, fill=(91, 141, 239, 230))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(
        path,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    build_icon(Path(__file__).resolve().parent / "icon.ico")
