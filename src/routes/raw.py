from __future__ import annotations

import base64

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.printer.driver import get_driver
from src.printer.renderer import render_html_to_png, render_template

router = APIRouter()
log = structlog.get_logger()


class RawPrint(BaseModel):
    text: str | None = None
    html: str | None = None
    image_base64: str | None = None


@router.post("/print/raw")
async def print_raw(req: RawPrint) -> dict:
    driver = get_driver()

    if req.image_base64:
        try:
            png = base64.b64decode(req.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"bad base64: {e}") from e
    elif req.html:
        png = await render_html_to_png(req.html)
    elif req.text:
        html = render_template("raw_text.html.j2", text=req.text) if _has_raw_template() else _wrap_text(req.text)
        png = await render_html_to_png(html)
    else:
        raise HTTPException(status_code=400, detail="provide text, html, or image_base64")

    path = await driver.print(png)
    return {"status": "ok", "path": str(path), "bytes": len(png)}


def _has_raw_template() -> bool:
    from pathlib import Path
    return (Path(__file__).resolve().parent.parent / "templates" / "raw_text.html.j2").exists()


def _wrap_text(text: str) -> str:
    return render_template_from_string(text)


def render_template_from_string(text: str) -> str:
    # Inline minimal _base derivative so we don't need an extra template file.
    from html import escape
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: 384px auto; margin: 0; }}
  body {{ margin:0; padding:12px 8px; width:368px; font-family: "Menlo", "DejaVu Sans Mono", monospace; font-size:16px; line-height:1.35; white-space:pre-wrap; }}
</style></head><body>{escape(text)}</body></html>
"""
