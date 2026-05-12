from __future__ import annotations

import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from playwright.async_api import async_playwright

from src.config import get_settings


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_template(name: str, **context) -> str:
    return _env.get_template(name).render(**context)


async def render_html_to_png(html: str, width: int | None = None) -> bytes:
    """Render an HTML string to a PNG sized for the thermal printer.

    The viewport width is fixed at PRINTER_WIDTH_PX. Height grows with content
    via full_page screenshot. The result is then converted to 1-bit with
    Floyd-Steinberg dithering so the printer firmware doesn't have to guess.
    """
    settings = get_settings()
    target_width = width or settings.printer_width_px

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            context = await browser.new_context(
                viewport={"width": target_width, "height": 1},
                device_scale_factor=1,
            )
            page = await context.new_page()
            await page.set_content(html, wait_until="networkidle")
            png_bytes = await page.screenshot(full_page=True, type="png", omit_background=False)
        finally:
            await browser.close()

    return _to_one_bit(png_bytes, target_width)


def _to_one_bit(png_bytes: bytes, width: int) -> bytes:
    img = Image.open(io.BytesIO(png_bytes)).convert("L")
    if img.width != width:
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
    dithered = img.convert("1", dither=Image.FLOYDSTEINBERG)
    out = io.BytesIO()
    dithered.save(out, format="PNG", optimize=True)
    return out.getvalue()
