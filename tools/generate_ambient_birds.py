#!/usr/bin/env python3
"""Generate and embed a four-frame pixel-art bird flock sprite sheet.

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
CELL_W, CELL_H, FRAMES = 24, 18, 4


def bird_frame(frame: int) -> Image.Image:
    image = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Paired wings flap through a clear high / glide / low / glide cycle.
    tip_y = (1, 4, 9, 4)[frame]
    shoulder_y = (8, 8, 9, 8)[frame]
    left_wing = [
        (11, shoulder_y), (9, tip_y + 3), (6, tip_y), (7, tip_y + 6),
        (2, tip_y + 3), (5, 11), (9, 14)
    ]
    right_wing = [
        (12, shoulder_y), (15, tip_y + 3), (18, tip_y), (17, tip_y + 6),
        (22, tip_y + 3), (19, 11), (15, 14)
    ]
    wing = (34, 43, 54, 255)
    inner = (71, 91, 103, 255)
    glint = (137, 176, 183, 230)
    draw.polygon(left_wing, fill=wing)
    draw.polygon(right_wing, fill=wing)
    # Feather streaks and a couple of cool rim pixels keep the silhouette legible.
    if frame in (0, 1, 3):
        draw.line([(5, tip_y + 3), (9, shoulder_y + 1)], fill=inner, width=1)
        draw.line([(14, shoulder_y + 1), (19, tip_y + 3)], fill=inner, width=1)
        draw.point((5, tip_y + 2), fill=glint)
        draw.point((18, tip_y + 2), fill=glint)
    else:
        draw.line([(5, 12), (9, 10)], fill=inner, width=1)
        draw.line([(14, 10), (19, 12)], fill=inner, width=1)

    # Body, lifted head, eye glint, tail feathers and bright beak read clearly at game scale.
    draw.polygon([(8, 9), (10, 7), (14, 7), (17, 9), (15, 12), (12, 14), (9, 12)],
                 fill=(25, 31, 40, 255))
    draw.ellipse((13, 5, 17, 9), fill=(39, 49, 60, 255))
    draw.point((16, 6), fill=(173, 208, 202, 255))
    draw.polygon([(17, 7), (21, 8), (17, 9)], fill=(255, 185, 88, 255))
    draw.polygon([(9, 9), (5, 6), (7, 10), (4, 13), (10, 12)], fill=(30, 39, 49, 255))
    draw.line([(10, 9), (13, 9)], fill=(111, 145, 154, 255), width=1)
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
