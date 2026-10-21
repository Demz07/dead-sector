#!/usr/bin/env python3
"""Generate the tiny animated Overdrive reactor sprite and embed it in the game.

Run: python tools/generate_overdrive_core.py
Requires Pillow. The PNG is saved as assets/overdrive_core.png and the exact
same image is embedded into index.html so the game remains a single-file PWA.
"""
from __future__ import annotations

import base64
import io
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "overdrive_core.png"
CELL = 32
FRAMES = 4
SCALE = 3


def point(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius


def make_frame(frame: int) -> Image.Image:
    size = CELL * SCALE
    c = size / 2
    t = frame * math.tau / FRAMES
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # Soft, compact bloom behind a deliberately hard-edged pixel icon.
    gd.ellipse((c - 12 * SCALE, c - 12 * SCALE, c + 12 * SCALE, c + 12 * SCALE),
               fill=(255, 158, 47, 38))
    glow = glow.filter(ImageFilter.GaussianBlur(3.5 * SCALE))

    art = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    px = lambda v: int(round(v * SCALE))

    # Four rotating segmented arcs and their crisp luminous edge pixels.
    for j in range(4):
        start = t + j * math.pi / 2 + 0.18
        end = start + 0.76
        box = (px(4), px(4), px(28), px(28))
        d.arc(box, math.degrees(start), math.degrees(end), fill=(255, 157, 59, 230), width=px(1.2))
        ex, ey = point(c, c, 12, end)
        d.rectangle((px(ex - 0.65), px(ey - 0.65), px(ex + 0.65), px(ey + 0.65)),
                    fill=(255, 231, 137, 255))

    # Four orbiting charge nodes; every frame advances one quarter turn.
    for j in range(4):
        a = t + j * math.pi / 2
        x, y = point(c, c, 10.3, a)
        color = (116, 244, 255, 255) if j % 2 == 0 else (255, 221, 121, 255)
        d.rectangle((px(x - 1), px(y - 1), px(x + 1), px(y + 1)), fill=color)
        d.point((px(x), px(y)), fill=(255, 255, 223, 255))

    # Reactor housing: octagonal gold frame, dark well, cyan core and pulse.
    outer = [point(c, c, 7.4 * SCALE, math.pi / 8 + k * math.tau / 8) for k in range(8)]
    inner = [point(c, c, 6.2 * SCALE, math.pi / 8 + k * math.tau / 8) for k in range(8)]
    d.polygon(outer, fill=(255, 195, 81, 255))
    d.polygon(inner, fill=(78, 45, 30, 255))
    d.polygon([(px(16), px(9)), (px(21), px(12)), (px(21), px(20)),
               (px(16), px(23)), (px(11), px(20)), (px(11), px(12))],
              fill=(23, 31, 39, 255))
    pulse = (frame % 2) * 2
    d.polygon([(px(16), px(11 - pulse * 0.35)), (px(20), px(16)),
               (px(16), px(21 + pulse * 0.35)), (px(12), px(16))],
              fill=(96, 244, 255, 255))
    d.rectangle((px(15), px(14), px(17), px(18)), fill=(235, 255, 222, 255))
    # Tiny hash marks make the housing read as machined sci-fi hardware.
    for x in (13, 18):
        d.point((px(x), px(7)), fill=(255, 238, 171, 230))
        d.point((px(x), px(25)), fill=(255, 238, 171, 230))

    # Upscale-space bloom composites under the pixel art, then return native pixels.
    glow.alpha_composite(art)
    return glow.resize((CELL, CELL), Image.Resampling.LANCZOS)


def main() -> None:
    sheet = Image.new("RGBA", (CELL * FRAMES, CELL), (0, 0, 0, 0))
    for frame in range(FRAMES):
        sheet.alpha_composite(make_frame(frame), (frame * CELL, 0))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, optimize=True)

    raw = io.BytesIO()
    sheet.save(raw, format="PNG", optimize=True)
    encoded = base64.b64encode(raw.getvalue()).decode("ascii")
    html = ROOT / "index.html"
    source = html.read_text()
    marker = "  var ASSETS = window.__A__, SPR = window.__S__, DATA = window.__D__, FONT = window.__F__;"
    source = re.sub(r"\n  ASSETS\.overdrive_core = 'data:image/png;base64,[^']+';", "", source)
    injection = marker + "\n  ASSETS.overdrive_core = 'data:image/png;base64," + encoded + "';"
    if marker not in source:
        raise SystemExit("Could not find the runtime asset registry in index.html")
    source = source.replace(marker, injection, 1)
    html.write_text(source)
    print(f"Wrote {OUT.relative_to(ROOT)} ({sheet.width}x{sheet.height}) and embedded it in index.html")


if __name__ == "__main__":
    main()
