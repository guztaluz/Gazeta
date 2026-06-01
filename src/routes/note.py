"""POST /print/note — print a note from NoteKeep.

Routes by tag:
  #shopping  -> categorized checklist (items grouped by supermarket section
                via the LLM)
  #recipe    -> recipe layout
  (default)  -> plain note

Payload: {"title": "...", "body": "...", "tags": ["shopping"]}
Tags may include or omit the leading '#'.
"""
from __future__ import annotations

import json
import re

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ai import client as ai_client
from src.ai.prompts import SHOPPING_SYSTEM, SHOPPING_USER
from src.printer.driver import get_driver
from src.printer.renderer import render_html_to_png, render_template

router = APIRouter()
log = structlog.get_logger()

_PT_DOW = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
_PT_MON = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


class NotePrint(BaseModel):
    title: str | None = None
    body: str = ""
    tags: list[str] = []


def _date_strip() -> str:
    from datetime import date

    t = date.today()
    return f"{_PT_DOW[t.weekday()]} {t.day:02d} {_PT_MON[t.month - 1]} {t.year}"


def _norm_tags(tags: list[str]) -> set[str]:
    return {t.lstrip("#").strip().lower() for t in tags if t.strip()}


def _paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def _split_items(body: str) -> list[str]:
    """Split a shopping body into individual items (newlines, commas, bullets)."""
    items: list[str] = []
    for line in body.splitlines():
        line = line.strip().lstrip("-•*").strip()
        if not line:
            continue
        # also split comma-separated lines
        parts = [p.strip() for p in line.split(",")] if "," in line else [line]
        items.extend(p for p in parts if p)
    return items


async def _categorize_shopping(body: str) -> list[dict]:
    items = _split_items(body)
    if not items:
        return []
    try:
        raw = await ai_client.generate(
            SHOPPING_SYSTEM, SHOPPING_USER.format(items="\n".join(items))
        )
        # The model may wrap JSON in fences; extract the object.
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)
        sections = data.get("sections") or []
        # Validate shape; fall back if malformed.
        cleaned = [
            {"name": str(s.get("name", "Outros")), "things": [str(i) for i in s.get("items", [])]}
            for s in sections
            if s.get("items")
        ]
        if cleaned:
            return cleaned
    except Exception as e:
        log.warning("shopping_categorize_failed", error=str(e))
    # Fallback: one "Lista" section with all items, uncategorized.
    return [{"name": "Lista", "things": items}]


@router.post("/print/note")
async def print_note(req: NotePrint) -> dict:
    tags = _norm_tags(req.tags)

    if "shopping" in tags or "compras" in tags:
        kind = "shopping"
        sections = await _categorize_shopping(req.body)
        ctx = {"kind": kind, "title": req.title, "date_strip": _date_strip(), "sections": sections}
    elif "recipe" in tags or "receita" in tags:
        kind = "recipe"
        ctx = {"kind": kind, "title": req.title, "date_strip": _date_strip(),
               "paragraphs": _paragraphs(req.body)}
    else:
        kind = "note"
        ctx = {"kind": kind, "title": req.title, "date_strip": _date_strip(),
               "paragraphs": _paragraphs(req.body)}

    html = render_template("note.html.j2", **ctx)
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

    log.info("note_printed", kind=kind, title=req.title)
    return {"status": "ok", "kind": kind, "path": str(path), "bytes": len(png)}
