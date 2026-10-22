#!/usr/bin/env python3
"""Generate and embed pixel-art sprites for the Sector 20 ending teaser.

Run: python tools/generate_sector20_ending.py
Requires Pillow. Generated PNGs are also embedded in index.html for offline PWA use.
"""
from __future__ import annotations

import base64
import io
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SCALE = 3
CORE = (32, 32, 8)
BEAST = (64, 52, 6)
SIGNAL = (24, 24, 8)
OUTS = {
    "ending_core": ROOT / "assets" / "sector20_ending_core.png",
    "ashfall_beast": ROOT / "assets" / "sector21_ashfall_beast.png",
    "ending_signal": ROOT / "assets" / "sector20_signal.png",
}


def core_frame(frame: int) -> Image.Image:
    w = CORE[0] * SCALE
    h = CORE[1] * SCALE
    pulse = (0.75, 0.94, 1.0, 0.88, 1.0, 0.56, 0.28, 0.10)[frame]
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx = cy = w / 2
    gd.ellipse((cx - 13 * SCALE, cy - 13 * SCALE,
                cx + 13 * SCALE, cy + 13 * SCALE),
               fill=(255, 111, 37, int(72 * pulse)))
    glow = glow.filter(ImageFilter.GaussianBlur(3.0 * SCALE))
    art = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    px = lambda n: int(round(n * SCALE))
    turn = frame * 0.06
    if frame < 5:
        outer = [(16 + math.cos(turn + i * math.tau / 8) * 11,
                  16 + math.sin(turn + i * math.tau / 8) * 11) for i in range(8)]
        inner = [(16 + math.cos(turn + i * math.tau / 8) * 8,
                  16 + math.sin(turn + i * math.tau / 8) * 8) for i in range(8)]
        d.polygon([(px(x), px(y)) for x, y in outer], fill=(255, 184, 72, int(240 * pulse)))
        d.polygon([(px(x), px(y)) for x, y in inner], fill=(47, 25, 25, int(255 * pulse)))
        c = (96, 226, 240, int(255 * pulse)) if frame < 4 else (255, 167, 60, int(255 * pulse))
        d.polygon([(px(16), px(9)), (px(22), px(16)), (px(16), px(23)), (px(10), px(16))], fill=c)
        d.rectangle((px(15), px(13), px(17), px(19)), fill=(255, 248, 197, int(255 * pulse)))
    # Cracks race outward, then the housing breaks into angular fragments.
    cracks = [((15, 8), (12, 13), (15, 16), (10, 21)),
              ((20, 10), (18, 14), (22, 16), (20, 22)),
              ((8, 16), (12, 16), (14, 19), (13, 24))]
    if frame >= 2:
        for path in cracks[:min(3, frame - 1)]:
            pts = [(px(x), px(y)) for x, y in path]
            d.line(pts, fill=(255, 235, 154, int(245 * pulse)), width=px(1))
    if frame >= 4:
        for i in range(frame - 3):
            a = i * 2.31 + frame * 0.55
            dist = 8 + (frame - 4) * 2
            x, y = 16 + math.cos(a) * dist, 16 + math.sin(a) * dist
            shard = [(x, y - 2), (x + 2, y), (x, y + 2), (x - 1, y)]
            d.polygon([(px(a), px(b)) for a, b in shard],
                      fill=(255, (157 + i * 18) % 256, 63, int(230 * pulse)))
    glow.alpha_composite(art)
    return glow.resize((CORE[0], CORE[1]), Image.Resampling.LANCZOS)


def beast_frame(frame: int) -> Image.Image:
    w, h = BEAST[0] * SCALE, BEAST[1] * SCALE
    art = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    px = lambda n: int(round(n * SCALE))
    sway = math.sin(frame * math.tau / BEAST[2]) * 1.2
    dark = (13, 12, 19, 255)
    edge = (38, 19, 24, 255)
    # Horned, broad-shouldered hive silhouette emerging from a jagged ridge.
    shape = [(5, 49), (8, 41), (14, 36), (13, 30), (18, 24),
             (18, 16), (22, 21), (25, 12), (29, 20), (33, 15),
             (37, 22), (43, 18), (44, 29), (51, 33), (58, 44),
             (62, 49), (54, 47), (48, 50), (40, 47), (33, 50),
             (25, 47), (17, 50), (10, 47)]
    points = [(px(x + sway), px(y)) for x, y in shape]
    d.polygon(points, fill=dark)
    d.line(points + [points[0]], fill=edge, width=px(1))
    # Hanging spines and rib-like cuts make the distant form read as organic.
    for x in (18, 23, 29, 35, 41, 46):
        d.line([(px(x + sway), px(34)), (px(x - 1 + sway), px(45))], fill=(25, 16, 22, 255), width=px(1))
    d.polygon([(px(7), px(43)), (px(12), px(36)), (px(14), px(46))], fill=(21, 15, 21, 255))
    # Three hot eyes breathe in a warm fire palette; this stays a teaser silhouette.
    eye_alpha = (125, 185, 255, 215, 140, 85)[frame]
    for ex, ey, rad in ((27, 30, 1.35), (35, 29, 1.55), (43, 32, 1.0)):
        d.ellipse((px(ex - rad + sway), px(ey - rad), px(ex + rad + sway), px(ey + rad)),
                  fill=(255, 119, 42, eye_alpha))
        d.point((px(ex + sway), px(ey)), fill=(255, 223, 137, min(255, eye_alpha + 35)))
    # A few ash flecks in each frame give the sprite independent life.
    for i in range(5):
        x = (i * 13 + frame * 7) % 64
        y = 35 + (i * 7 + frame * 3) % 15
        d.point((px(x), px(y)), fill=(145, 74, 48, 95))
    return art.resize((BEAST[0], BEAST[1]), Image.Resampling.LANCZOS)


def signal_frame(frame: int) -> Image.Image:
    w = h = SIGNAL[0] * SCALE
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = cy = w / 2
    gd = ImageDraw.Draw(glow)
    pulse = (0.55, 0.72, 0.95, 1.0, 0.72, 0.52, 0.82, 1.0)[frame]
    gd.ellipse((cx - 4 * SCALE, cy - 4 * SCALE, cx + 4 * SCALE, cy + 4 * SCALE),
               fill=(255, 112, 39, int(155 * pulse)))
    glow = glow.filter(ImageFilter.GaussianBlur(2.1 * SCALE))
    d = ImageDraw.Draw(img)
    px = lambda n: int(round(n * SCALE))
    # Antenna mast, beacon and two rotating pulse arcs.
    d.line((px(12), px(13), px(12), px(19)), fill=(190, 106, 61, 230), width=px(1))
    d.rectangle((px(10), px(18), px(14), px(20)), fill=(255, 147, 54, int(235 * pulse)))
    d.point((px(12), px(10)), fill=(255, 232, 154, int(255 * pulse)))
    radius = (4.5, 6.0, 7.5, 9.2, 7.8, 6.3, 8.3, 9.5)[frame]
    alpha = (80, 110, 140, 200, 160, 100, 175, 210)[frame]
    d.arc((px(12 - radius), px(12 - radius), px(12 + radius), px(12 + radius)),
          205, 335, fill=(255, 151, 63, alpha), width=px(1))
    d.arc((px(12 - radius), px(12 - radius), px(12 + radius), px(12 + radius)),
          25, 155, fill=(255, 190, 92, int(alpha * 0.8)), width=px(1))
    glow.alpha_composite(img)
    return glow.resize((SIGNAL[0], SIGNAL[1]), Image.Resampling.LANCZOS)


def strip(cell_w: int, cell_h: int, frames: int, draw_frame) -> Image.Image:
    sheet = Image.new("RGBA", (cell_w * frames, cell_h), (0, 0, 0, 0))
    for frame in range(frames):
        sheet.alpha_composite(draw_frame(frame), (cell_w * frame, 0))
    return sheet


def embed(source: str, key: str, image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    source = re.sub(rf"\n  ASSETS\.{re.escape(key)} = 'data:image/png;base64,[^']+';", "", source)
    marker = "  var ASSETS = window.__A__, SPR = window.__S__, DATA = window.__D__, FONT = window.__F__;"
    if marker not in source:
        raise SystemExit("Could not find the runtime asset registry in index.html")
    return source.replace(marker, marker + f"\n  ASSETS.{key} = 'data:image/png;base64,{encoded}';", 1)


def main() -> None:
    sheets = {
        "ending_core": strip(*CORE, core_frame),
        "ashfall_beast": strip(*BEAST, beast_frame),
        "ending_signal": strip(*SIGNAL, signal_frame),
    }
    for key, image in sheets.items():
        image.save(OUTS[key], optimize=True)

    html = ROOT / "index.html"
    source = html.read_text()
    for key, image in sheets.items():
        source = embed(source, key, image)
        source = re.sub(rf"\n  SPR\.{re.escape(key)} = \{{[^\n]*\}};", "", source)
    last_key = "ending_signal"
    marker = f"  ASSETS.{last_key} = 'data:image/png;base64,"
    pos = source.find(marker)
    if pos < 0:
        raise SystemExit("Could not find generated ending signal asset")
    end = source.find("';", pos) + 2
    metadata = (
        "\n  SPR.ending_core = { img: 'ending_core', kind: 'fx', cw: 32, ch: 32, frames: 8, fps: 6, loop: false, ax: 16, ay: 16 };"
        "\n  SPR.ashfall_beast = { img: 'ashfall_beast', kind: 'fx', cw: 64, ch: 52, frames: 6, fps: 4, loop: true, ax: 32, ay: 48 };"
        "\n  SPR.ending_signal = { img: 'ending_signal', kind: 'fx', cw: 24, ch: 24, frames: 8, fps: 8, loop: true, ax: 12, ay: 12 };"
    )
    source = source[:end] + metadata + source[end:]
    html.write_text(source)
    for key, image in sheets.items():
        print(f"Wrote {OUTS[key].relative_to(ROOT)} ({image.width}x{image.height})")
    print("Embedded the ending sprites in index.html")


if __name__ == "__main__":
    main()
