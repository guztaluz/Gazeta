from __future__ import annotations

import asyncio
import json
import re
from datetime import date

import httpx
import structlog
from fastapi import APIRouter, HTTPException

from src.ai import client as ai_client
from src.ai.prompts import SUMMARY_SYSTEM, USER_TEMPLATE
from src.printer.driver import get_driver
from src.printer.renderer import render_html_to_png, render_template
from src.sources import (
    calendar as calendar_src,
    crypto,
    email as email_src,
    news,
    quote,
    weather,
)

router = APIRouter()
log = structlog.get_logger()

_SECTION_RE = re.compile(r"###\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ]+)\s*###", re.IGNORECASE)

_PT_DOW = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
_PT_MON = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


async def _gather_sources() -> dict:
    async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "gazeta/0.1"}) as client:
        results = await asyncio.gather(
            weather.fetch(client),
            crypto.fetch(client),
            quote.fetch(),
            news.fetch(client),
            calendar_src.fetch(),
            email_src.fetch(),
            return_exceptions=True,
        )
    labels = ["weather", "crypto", "quote", "news", "calendar", "email"]
    out: dict = {}
    for label, r in zip(labels, results):
        out[label] = {"error": repr(r)} if isinstance(r, Exception) else r
    return out


def _parse_sections(text: str) -> dict[str, list[str]]:
    """Split LLM output on '### NAME ###' headers into {name: [paragraphs]}."""
    parts = _SECTION_RE.split(text)
    sections: dict[str, list[str]] = {}
    for i in range(1, len(parts) - 1, 2):
        name = parts[i].lower()
        content = parts[i + 1].strip()
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if paragraphs:
            sections[name] = paragraphs
    return sections


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _format_date_strip(today: date) -> tuple[str, str]:
    dow = _PT_DOW[today.weekday()]
    mon = _PT_MON[today.month - 1]
    issue = f"{today.timetuple().tm_yday:03d}"
    left = f"{dow} {today.day:02d} {mon} {today.year}"
    right = f"Dublin · Ed. {issue}".upper()
    return left, right


@router.post("/print/summary")
async def print_summary() -> dict:
    data = await _gather_sources()

    user_msg = USER_TEMPLATE.format(
        data_json=json.dumps(data, ensure_ascii=False, default=str)
    )

    try:
        narrative = await ai_client.generate(SUMMARY_SYSTEM, user_msg)
        sections = _parse_sections(narrative)
        if not sections:
            sections = {"nota": _split_paragraphs(narrative)}
    except Exception as e:
        log.error("llm_failed", error=str(e))
        sections = _fallback_sections(data)

    today = date.today()
    issue_no = f"{today.timetuple().tm_yday:03d}"
    date_left, date_right = _format_date_strip(today)

    news_buckets = _build_news_buckets(data)

    ctx = dict(
        date_strip_left=date_left,
        date_strip_right=date_right,
        issue_no=issue_no,
        sections=sections,
        weather=data.get("weather") or {},
        crypto=data.get("crypto") or {},
        quote=data.get("quote") or {},
        news_buckets=news_buckets,
    )

    # Render and print as separate, smaller jobs — the printer handles short
    # images far more reliably than one long strip. The paper is continuous so
    # the blocks read as one summary.
    blocks = ["header", "agenda", "news", "closing"]
    driver = get_driver()
    last_path = None
    total_bytes = 0

    # Render all blocks first, skip blank ones, so we know which is truly last.
    rendered: list[tuple[str, bytes]] = []
    for block in blocks:
        html = render_template("summary_block.html.j2", block=block, **ctx)
        try:
            png = await render_html_to_png(html)
        except Exception as e:
            log.error("render_failed", block=block, error=str(e))
            raise HTTPException(status_code=500, detail=f"render failed ({block}): {e}") from e
        if _is_blank(png):
            log.info("block_skipped_blank", block=block)
            continue
        rendered.append((block, png))

    # Small feed between blocks so they sit close together; full feed only on
    # the last block to clear the tear edge.
    GAP_FEED = 2
    for i, (block, png) in enumerate(rendered):
        is_last = i == len(rendered) - 1
        try:
            last_path = await driver.print(png, feed_lines=None if is_last else GAP_FEED)
            total_bytes += len(png)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.error("driver_failed", block=block, etype=type(e).__name__,
                      error=repr(e), traceback=tb)
            detail = f"driver failed ({block}): {type(e).__name__}: {e!r}"
            raise HTTPException(status_code=500, detail=detail) from e
        log.info("block_printed", block=block, bytes=len(png))

    log.info("summary_printed", path=str(last_path))
    return {"status": "ok", "path": str(last_path), "bytes": total_bytes, "blocks": len(blocks)}


def _is_blank(png_bytes: bytes) -> bool:
    """True if the rendered PNG has essentially no black pixels."""
    import io as _io

    from PIL import Image

    img = Image.open(_io.BytesIO(png_bytes)).convert("1")
    px = img.load()
    w, h = img.size
    black = sum(1 for y in range(h) for x in range(w) if px[x, y] == 0)
    return black < (w * h) * 0.002


# (key, label, icon, how many items to show). "world" already includes a tech
# story (folded in by src/sources/news.py), so we surface 4 there.
_NEWS_BUCKETS = [
    ("dublin", "Dublin", "map-pin", 3),
    ("world",  "Mundo",  "globe",   4),
]


def _build_news_buckets(data: dict) -> list[dict]:
    """Assemble the Notícias widget from the RSS news source."""
    news_data = data.get("news") or {}
    if news_data.get("error"):
        return []
    out: list[dict] = []
    for key, label, icon_name, count in _NEWS_BUCKETS:
        items = [i for i in (news_data.get(key) or []) if i.get("title")][:count]
        if not items:
            continue
        out.append({"label": label, "icon": icon_name, "headlines": items})
    return out


def _fallback_sections(data: dict) -> dict[str, list[str]]:
    cal = data.get("calendar") or {}
    events = cal.get("events") or []
    if events:
        agenda = "Hoje: " + "; ".join(e["summary"] for e in events[:3]) + "."
    else:
        agenda = "Agenda livre hoje — um bom dia para fazer uma coisa de propósito."
    return {
        "agenda": [agenda],
        "piada": ["Por que o livro de matemática é triste? Porque tem muitos problemas."],
    }
