from __future__ import annotations

import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageFilter
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


async def render_html_to_png(
    html: str, width: int | None = None, dither: bool = False, bold: bool = False
) -> bytes:
    """Render an HTML string to a PNG sized for the thermal printer.

    The viewport width is fixed at PRINTER_WIDTH_PX. Height grows with content
    via full_page screenshot.

    By default we THRESHOLD to pure black/white (every dark pixel -> solid
    black). Floyd-Steinberg dithering — the previous default — turns black
    regions into a 50% checkerboard of dots, which a thermal head prints as
    faint grey because it only heats half the dots. For text and line art,
    thresholding prints dark and crisp. Pass dither=True only for photos.
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

    return _to_one_bit(png_bytes, target_width, dither=dither, bold=bold)


def _to_one_bit(
    png_bytes: bytes, width: int, dither: bool = False, threshold: int = 160, bold: bool = True
) -> bytes:
    img = Image.open(io.BytesIO(png_bytes)).convert("L")
    if img.width != width:
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)

    if bold:
        # Fatten dark strokes before thresholding. This low-power thermal head
        # prints thin (1-dot) strokes as faint grey; a MinFilter grows every
        # dark region by ~1px so text/lines become 2-3 dots wide and print
        # solid black. MinFilter on an 'L' image = grayscale erosion = darks
        # expand (smaller value wins).
        img = img.filter(ImageFilter.MinFilter(3))

    if dither:
        out_img = img.convert("1", dither=Image.FLOYDSTEINBERG)
    else:
        # Hard threshold: pixel darker than `threshold` -> black (0), else white.
        out_img = img.point(lambda px: 0 if px < threshold else 255, mode="1")

    out = io.BytesIO()
    out_img.save(out, format="PNG", optimize=True)
    return out.getvalue()
