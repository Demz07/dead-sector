#!/usr/bin/env python3
"""Generate and embed animated background smoke and atmospheric sprite strips.

Run: python tools/generate_ambient_background_fx.py
Requires Pillow. Writes assets/ambient_smoke.png and assets/ambient_embers.png,
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
EMBER_OUT = ROOT / "assets" / "ambient_embers.png"
SMOKE_W, SMOKE_H = 28, 32
SMOKE_FRAMES = 8
EMBER_CELL = 12
EMBER_FRAMES = 8
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


def ember_frame(frame: int) -> Image.Image:
    """A flying fire fragment with a jagged tail and an all-warm flicker loop."""
    size = EMBER_CELL * UPSCALE
    scale = UPSCALE
    phase = frame * math.tau / EMBER_FRAMES
    palette = [
        (255, 101, 32), (255, 148, 43), (255, 211, 91), (244, 84, 27),
        (255, 183, 55), (255, 231, 133), (235, 91, 30), (255, 137, 37),
    ]
    color = palette[frame]
    pulse = (0.62, 0.78, 1.0, 0.72, 0.56, 0.92, 0.68, 0.86)[frame]
    cx = 6 * scale + int(round(math.sin(phase) * 0.38 * scale))
    cy = 6 * scale + int(round(math.cos(phase) * 0.32 * scale))

    # Amber/red bloom remains small so the flying debris reads as hot pixels,
    # not neon orbs. The sharper core is composited above the soft halo.
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    radius = (2.5 + 0.25 * math.sin(phase)) * scale
    gd.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
               fill=(255, 99, 26, int(104 * pulse)))
    glow = glow.filter(ImageFilter.GaussianBlur(1.15 * scale))

    art = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    # Rotate a crooked shard and its broken tail through a restrained arc.
    angle = -0.7 + 0.25 * math.sin(phase)
    def rotate_point(x: float, y: float) -> tuple[int, int]:
        dx, dy = x * scale, y * scale
        return (int(round(cx + dx * math.cos(angle) - dy * math.sin(angle))),
                int(round(cy + dx * math.sin(angle) + dy * math.cos(angle))))

    shard = [(-2.0, 1.0), (-0.4, -2.0), (2.0, -0.7), (1.0, 0.8),
             (2.1, 2.0), (-0.6, 1.3)]
    d.polygon([rotate_point(x, y) for x, y in shard], fill=(*color, int(238 * pulse)))
    hot = (255, 241, 177, int(255 * pulse))
    d.point(rotate_point(0, 0), fill=hot)
    d.point(rotate_point(0.8, -0.35), fill=(255, 214, 100, int(248 * pulse)))

    # A broken, tapered trail and two tiny flecks sell airborne fire debris.
    tail = [(-3.1, 2.4), (-3.8, 3.2), (-4.7, 3.1), (-3.7, 2.1)]
    d.polygon([rotate_point(x, y) for x, y in tail], fill=(255, 105, 31, int(205 * pulse)))
    d.point(rotate_point(-4.7, 3.1), fill=(255, 190, 75, int(210 * pulse)))
    flick_x = 3.7 + 0.45 * math.sin(phase + 1.0)
    flick_y = -2.7 + 0.4 * math.cos(phase)
    d.point(rotate_point(flick_x, flick_y), fill=(255, 159, 48, int(195 * pulse)))
    if frame in (1, 4, 7):
        d.point(rotate_point(-2.6, 0.0), fill=(255, 224, 120, int(220 * pulse)))

    glow.alpha_composite(art)
    return glow.resize((EMBER_CELL, EMBER_CELL), Image.Resampling.LANCZOS)


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
    embers = make_strip(EMBER_CELL, EMBER_CELL, EMBER_FRAMES, ember_frame)
    SMOKE_OUT.parent.mkdir(parents=True, exist_ok=True)
    smoke.save(SMOKE_OUT, optimize=True)
    embers.save(EMBER_OUT, optimize=True)

    html = ROOT / "index.html"
    source = html.read_text()
    source = embed_asset(source, "ambient_smoke", smoke)
    source = embed_asset(source, "ambient_embers", embers)
    source = re.sub(r"\n  SPR\.ambient_smoke = \{[^\n]*\};", "", source)
    source = re.sub(r"\n  SPR\.ambient_embers = \{[^\n]*\};", "", source)
    source = re.sub(r"\n  ASSETS\.ambient_motes = 'data:image/png;base64,[^']+';", "", source)
    source = re.sub(r"\n  SPR\.ambient_motes = \{[^\n]*\};", "", source)
    marker = "  ASSETS.ambient_embers = 'data:image/png;base64,"
    pos = source.find(marker)
    if pos < 0:
        raise SystemExit("Could not find embedded ambient ember sprite")
    end = source.find("';", pos) + 2
    metadata = (
        "\n  SPR.ambient_smoke = { img: 'ambient_smoke', kind: 'fx', cw: 28, ch: 32, frames: 8, fps: 7, loop: true, ax: 14, ay: 30 };"
        "\n  SPR.ambient_embers = { img: 'ambient_embers', kind: 'fx', cw: 12, ch: 12, frames: 8, fps: 10, loop: true, ax: 6, ay: 6 };"
    )
    source = source[:end] + metadata + source[end:]
    html.write_text(source)
    print(f"Wrote {SMOKE_OUT.relative_to(ROOT)} ({smoke.width}x{smoke.height})")
    print(f"Wrote {EMBER_OUT.relative_to(ROOT)} ({embers.width}x{embers.height})")
    print("Embedded both animated sprite strips in index.html")


if __name__ == "__main__":
    main()
