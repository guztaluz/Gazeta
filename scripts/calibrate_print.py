"""First-contact hardware test. Draws a calibration pattern with PIL (no
Playwright, no network, no fonts to fetch) and prints it over BLE.

Run from Terminal.app (which has Bluetooth permission granted):

    cd /Users/gustavoluz/Desktop/Gazeta && .venv/bin/python scripts/calibrate_print.py

What to check on the paper:
- "GAZETA" reads upright and left-to-right (not mirrored or upside-down).
- The solid bar is fully black; the gradient steps go light -> dark.
- The border frame is fully on the paper (nothing clipped at the edges).
"""
from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont

from src.printer.driver import get_driver
from src.printer.protocol import PRINTER_WIDTH


def _font(size: int):
    for p in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_pattern() -> bytes:
    h = 260
    img = Image.new("L", (PRINTER_WIDTH, h), 255)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, PRINTER_WIDTH - 1, h - 1], outline=0, width=2)
    d.text((20, 16), "GAZETA", fill=0, font=_font(44))
    d.rectangle([20, 78, PRINTER_WIDTH - 20, 110], fill=0)  # solid black bar

    steps = 8
    sw = (PRINTER_WIDTH - 40) // steps
    for i in range(steps):
        shade = 255 - int(255 * i / (steps - 1))
        d.rectangle([20 + i * sw, 130, 20 + (i + 1) * sw, 175], fill=shade)

    d.text((20, 195), "esquerda  <-->  direita", fill=0, font=_font(22))
    d.text((20, 225), "teste de impressao", fill=0, font=_font(22))

    out = io.BytesIO()
    img.convert("1").save(out, format="PNG")
    return out.getvalue()


async def main() -> None:
    driver = get_driver()
    print(f"Driver: {type(driver).__name__}")
    png = make_pattern()
    print(f"Pattern: {len(png)} bytes PNG. Sending over BLE...")
    path = await driver.print(png)
    print(f"Done. Saved copy to {path}")


if __name__ == "__main__":
    asyncio.run(main())
