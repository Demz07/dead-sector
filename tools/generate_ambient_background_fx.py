#!/usr/bin/env python3
"""Generate and embed animated background smoke and atmospheric sprite strips.

Run: python tools/generate_ambient_background_fx.py
Requires Pillow. Writes assets/ambient_smoke.png and assets/ambient_motes.png,
then embeds them in index.html so the game still runs offline as a single-file PWA.
"""
from __future__ import annotations

import base64
import io
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SMOKE_OUT = ROOT / "assets" / "ambient_smoke.png"
MOTE_OUT = ROOT / "assets" / "ambient_motes.png"
SMOKE_W, SMOKE_H = 28, 32
SMOKE_FRAMES = 8
MOTE_CELL = 10
MOTE_FRAMES = 8
UPSCALE = 3


def smoke_frame(frame: int) -> Image.Image:
    """A curling chimney wisp: scalloped billows, a rising tip and warm rim."""
    width, height = SMOKE_W * UPSCALE, SMOKE_H * UPSCALE
    phase = frame * math.tau / SMOKE_FRAMES
    pulse = 1.0 + 0.05 * math.sin(phase)
    mask = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(mask)
    px = lambda n: int(round(n * UPSCALE))

    # The plume bends along a rising S-curve. Side lobes keep its silhouette
    # smoky and irregular instead of looking like a row of round bubbles.
    bend = math.sin(phase) * 1.55
    lobes = [
        (14.0, 27.5, 3.1, 2.5, 118),
        (14.0 + bend * 0.25, 23.5, 3.8, 3.4, 143),
        (10.9 + bend * 0.20, 22.0, 2.8, 2.8, 126),
        (17.7 + bend * 0.30, 22.1, 2.8, 2.9, 131),
        (13.0 + bend * 0.60, 17.7, 5.1, 4.3, 163),
        (8.5 + bend * 0.48, 15.7, 3.6, 3.8, 143),
        (18.9 + bend * 0.75, 15.4, 4.1, 3.9, 154),
        (13.0 + bend, 11.7, 4.7, 4.1, 162),
        (18.5 + bend * 1.1, 9.8 + math.cos(phase) * 0.8, 3.4, 3.7, 137),
        (11.1 + bend * 0.75, 10.4, 3.0, 3.4, 128),
    ]
    for x, y, rx, ry, opacity in lobes:
        rx *= pulse
        ry *= pulse
        d.ellipse((px(x - rx), px(y - ry), px(x + rx), px(y + ry)), fill=opacity)

    # A little detached curl changes sides over the loop, like wind peeling the tip.
    curl_x = 20.0 + math.sin(phase + 0.8) * 1.6
    curl_y = 4.5 + math.cos(phase + 0.8) * 1.0
    d.ellipse((px(curl_x - 2.0), px(curl_y - 2.5),
               px(curl_x + 2.0), px(curl_y + 2.5)), fill=82)

    mask = mask.filter(ImageFilter.GaussianBlur(0.82 * UPSCALE))
    glow = mask.filter(ImageFilter.GaussianBlur(2.2 * UPSCALE))
    rgba = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mpx, gpx = mask.load(), glow.load()
    out = rgba.load()
    for y in range(height):
        ny = y / height
        for x in range(width):
            a, ga = mpx[x, y], gpx[x, y]
            if not a and not ga:
                continue
            warm = max(0.0, 1.0 - abs(x / width - 0.72) * 2.6)
            r = int(74 + ny * 67 + warm * 34)
            g = int(94 + ny * 69 + warm * 13)
            b = int(118 + ny * 64 - warm * 18)
            core_alpha = int(a * (0.66 + ny * 0.08))
            glow_alpha = int(ga * 0.09)
            out[x, y] = (r, g, b, min(216, core_alpha + glow_alpha))

    # A few drifting copper glints tuck into the lit edges of the smoke.
    art = ImageDraw.Draw(rgba)
    for k in range(4):
        hx = 9.0 + k * 3.0 + math.sin(phase + k * 0.8) * 0.9
        hy = 13.0 + (k % 2) * 4.0 + math.cos(phase + k) * 0.65
        art.ellipse((px(hx - 0.5), px(hy - 0.45), px(hx + 0.5), px(hy + 0.45)),
                   fill=(222, 195, 157, 108))
    return rgba.resize((SMOKE_W, SMOKE_H), Image.Resampling.LANCZOS)


def mote_frame(frame: int) -> Image.Image:
    """A tiny neon ember/firefly that pulses and changes hue through its loop."""
    size = MOTE_CELL * UPSCALE
    scale = UPSCALE
    colors = [
        (255, 177, 91), (255, 221, 132), (115, 231, 255), (255, 192, 105),
        (255, 126, 91), (129, 220, 255), (205, 151, 255), (255, 219, 133),
    ]
    color = colors[frame]
    pulse = (0.56, 0.76, 1.0, 0.82, 0.60, 0.84, 1.0, 0.75)[frame]
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    c = size / 2
    gd.ellipse((c - 2.1 * scale, c - 2.1 * scale,
                c + 2.1 * scale, c + 2.1 * scale),
               fill=(*color, int(100 * pulse)))
    glow = glow.filter(ImageFilter.GaussianBlur(1.25 * scale))

    art = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    cx = 5 * scale + int(round(math.sin(frame * math.tau / MOTE_FRAMES) * 0.45 * scale))
    cy = 5 * scale + int(round(math.cos(frame * math.tau / MOTE_FRAMES) * 0.35 * scale))
    bright = tuple(min(255, int(ch + (255 - ch) * 0.55)) for ch in color)
    d.rectangle((cx - scale, cy - scale, cx + scale, cy + scale), fill=(*color, int(220 * pulse)))
    d.point((cx, cy), fill=(*bright, int(255 * pulse)))
    # A short pixel tail rotates, so a moving mote feels like an ember in air.
    tails = [(-2, 1), (-2, 0), (-1, -2), (0, -2), (2, -1), (2, 0), (1, 2), (0, 2)]
    tx, ty = tails[frame]
    d.point((cx + tx * scale // 2, cy + ty * scale // 2), fill=(*color, int(160 * pulse)))
    glow.alpha_composite(art)
    return glow.resize((MOTE_CELL, MOTE_CELL), Image.Resampling.LANCZOS)


def make_strip(cell_w: int, cell_h: int, frames: int, draw_frame) -> Image.Image:
    strip = Image.new("RGBA", (cell_w * frames, cell_h), (0, 0, 0, 0))
    for frame in range(frames):
        strip.alpha_composite(draw_frame(frame), (frame * cell_w, 0))
    return strip


def embed_asset(source: str, key: str, image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    source = re.sub(rf"\n  ASSETS\.{re.escape(key)} = 'data:image/png;base64,[^']+';", "", source)
    marker = "  var ASSETS = window.__A__, SPR = window.__S__, DATA = window.__D__, FONT = window.__F__;"
    if marker not in source:
        raise SystemExit("Could not find the runtime asset registry in index.html")
    declaration = f"  ASSETS.{key} = 'data:image/png;base64,{encoded}';"
    return source.replace(marker, marker + "\n" + declaration, 1)


def main() -> None:
    smoke = make_strip(SMOKE_W, SMOKE_H, SMOKE_FRAMES, smoke_frame)
    motes = make_strip(MOTE_CELL, MOTE_CELL, MOTE_FRAMES, mote_frame)
    SMOKE_OUT.parent.mkdir(parents=True, exist_ok=True)
    smoke.save(SMOKE_OUT, optimize=True)
    motes.save(MOTE_OUT, optimize=True)

    html = ROOT / "index.html"
    source = html.read_text()
    source = embed_asset(source, "ambient_smoke", smoke)
    source = embed_asset(source, "ambient_motes", motes)
    source = re.sub(r"\n  SPR\.ambient_smoke = \{[^\n]*\};", "", source)
    source = re.sub(r"\n  SPR\.ambient_motes = \{[^\n]*\};", "", source)
    marker = "  ASSETS.ambient_motes = 'data:image/png;base64,"
    pos = source.find(marker)
    if pos < 0:
        raise SystemExit("Could not find embedded ambient mote sprite")
    end = source.find("';", pos) + 2
    metadata = (
        "\n  SPR.ambient_smoke = { img: 'ambient_smoke', kind: 'fx', cw: 28, ch: 32, frames: 8, fps: 7, loop: true, ax: 14, ay: 30 };"
        "\n  SPR.ambient_motes = { img: 'ambient_motes', kind: 'fx', cw: 10, ch: 10, frames: 8, fps: 9, loop: true, ax: 5, ay: 5 };"
    )
    source = source[:end] + metadata + source[end:]
    html.write_text(source)
    print(f"Wrote {SMOKE_OUT.relative_to(ROOT)} ({smoke.width}x{smoke.height})")
    print(f"Wrote {MOTE_OUT.relative_to(ROOT)} ({motes.width}x{motes.height})")
    print("Embedded both animated sprite strips in index.html")


if __name__ == "__main__":
    main()
