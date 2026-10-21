#!/usr/bin/env python3
"""Generate and embed tiny, stick-like animated bird sprites.

Run: python tools/generate_ambient_birds.py
Requires Pillow. Writes assets/ambient_birds.png and embeds the PNG in index.html
so the game still runs offline as a single-file PWA.
"""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "ambient_birds.png"
CELL_W, CELL_H, FRAMES = 10, 7, 4


def bird_frame(frame: int) -> Image.Image:
    image = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # A single-pixel M/V silhouette cycles through four wing positions.
    # Keep the design deliberately close to the game's original stick birds.
    poses = (
        [(0, 4), (2, 2), (4, 3), (5, 3), (7, 2), (9, 4)],
        [(0, 3), (2, 3), (4, 4), (5, 4), (7, 3), (9, 3)],
        [(0, 2), (2, 4), (4, 3), (5, 3), (7, 4), (9, 2)],
        [(0, 3), (2, 1), (4, 2), (5, 2), (7, 1), (9, 3)],
    )
    pose = poses[frame]
    ink = (57, 55, 63, 255)
    draw.line(pose[:3], fill=ink, width=1)
    draw.line(pose[3:], fill=ink, width=1)
    # Tiny center pixel gives the chevron a bird-like body without extra detail.
    draw.point((4, pose[2][1]), fill=(75, 73, 81, 255))
    draw.point((5, pose[3][1]), fill=(75, 73, 81, 255))
    return image


def main() -> None:
    sheet = Image.new("RGBA", (CELL_W * FRAMES, CELL_H), (0, 0, 0, 0))
    for frame in range(FRAMES):
        sheet.alpha_composite(bird_frame(frame), (frame * CELL_W, 0))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, optimize=True)

    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    html = ROOT / "index.html"
    source = html.read_text()
    marker = "  var ASSETS = window.__A__, SPR = window.__S__, DATA = window.__D__, FONT = window.__F__;"
    source = re.sub(r"\n  ASSETS\.ambient_birds = 'data:image/png;base64,[^']+';", "", source)
    if marker not in source:
        raise SystemExit("Could not find the runtime asset registry in index.html")
    source = source.replace(marker, marker + "\n  ASSETS.ambient_birds = 'data:image/png;base64," + encoded + "';", 1)
    html.write_text(source)
    print(f"Wrote {OUT.relative_to(ROOT)} ({sheet.width}x{sheet.height}) and embedded it in index.html")


if __name__ == "__main__":
    main()
