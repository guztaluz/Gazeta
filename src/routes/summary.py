from __future__ import annotations

import asyncio
import json
from datetime import date

import httpx
import structlog
from fastapi import APIRouter, HTTPException

from src.ai import client as ai_client
from src.ai.prompts import SUMMARY_PROMPT
from src.printer.driver import get_driver
from src.printer.renderer import render_html_to_png, render_template
from src.sources import (
    calendar as calendar_src,
    crypto,
    email as email_src,
    hackernews,
    joke,
    news,
    quote,
    weather,
    wikipedia,
)

router = APIRouter()
log = structlog.get_logger()


async def _gather_sources() -> dict:
    async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "gazeta/0.1"}) as client:
        results = await asyncio.gather(
            weather.fetch(client),
            crypto.fetch(client),
            quote.fetch(),
            joke.fetch(client),
            wikipedia.fetch(client),
            hackernews.fetch(client),
            news.fetch(client),
            calendar_src.fetch(),
            email_src.fetch(),
            return_exceptions=True,
        )
    labels = ["weather", "crypto", "quote", "joke", "wikipedia",
              "hackernews", "news", "calendar", "email"]
    out: dict = {}
    for label, r in zip(labels, results):
        out[label] = {"error": repr(r)} if isinstance(r, Exception) else r
    return out


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


@router.post("/print/summary")
async def print_summary() -> dict:
    data = await _gather_sources()

    prompt = SUMMARY_PROMPT.format(data_json=json.dumps(data, ensure_ascii=False, default=str))

    try:
        narrative = await ai_client.generate(prompt)
    except Exception as e:
        log.error("llm_failed", error=str(e))
        narrative = _fallback_narrative(data)

    today = date.today()
    html = render_template(
        "summary.html.j2",
        date_human=today.strftime("%A, %d %b %Y"),
        narrative_paragraphs=_split_paragraphs(narrative),
        weather=data.get("weather", {}),
        crypto=data.get("crypto", {}),
        quote=data.get("quote", {}),
    )

    try:
        png = await render_html_to_png(html)
    except Exception as e:
        log.error("render_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"render failed: {e}") from e

    driver = get_driver()
    try:
        path = await driver.print(png)
    except Exception as e:
        log.error("driver_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"driver failed: {e}") from e

    log.info("summary_printed", path=str(path))
    return {"status": "ok", "path": str(path), "bytes": len(png)}


def _fallback_narrative(data: dict) -> str:
    """Used only if the LLM call fails — keep the morning summary alive."""
    w = data.get("weather", {})
    cal = data.get("calendar", {})
    lines = []
    if w and not w.get("error"):
        lines.append(
            f"Dublin today: {w.get('summary')}, "
            f"{int(round(w.get('temp_min_c') or 0))}-{int(round(w.get('temp_max_c') or 0))} C, "
            f"{w.get('precip_prob')}% rain. "
            f"{'Take a jacket.' if w.get('wear_jacket') else 'Should be fine without a jacket.'}"
        )
    events = (cal or {}).get("events") or []
    if events:
        lines.append("Today: " + "; ".join(e["summary"] for e in events[:3]) + ".")
    else:
        lines.append("Calendar is open today.")
    lines.append("LLM unavailable; printed the fallback briefing.")
    return "\n\n".join(lines)
