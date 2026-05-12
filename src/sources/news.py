from __future__ import annotations

import asyncio
import re
from typing import Any

import feedparser
import httpx

FEEDS: dict[str, list[str]] = {
    "dublin": [
        "https://www.rte.ie/news/rss/news-headlines.xml",
        "https://www.thejournal.ie/feed/",
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.reuters.com/world/feeds/",
    ],
    "tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
}

PER_FEED = 5
PER_BUCKET = 8

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# Common trailing junk in feed summaries.
_TRAIL_RE = re.compile(r"(Read more on|Continue reading|The post .* appeared first.*)$", re.I)


def _clean_summary(entry: Any, max_chars: int = 160) -> str:
    raw = getattr(entry, "summary", None) or getattr(entry, "description", "") or ""
    text = _TAG_RE.sub("", raw)
    text = _WS_RE.sub(" ", text).strip()
    text = _TRAIL_RE.sub("", text).strip()
    if not text:
        return ""
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
    return text


async def _fetch_feed(client: httpx.AsyncClient, url: str) -> list[dict[str, Any]]:
    try:
        r = await client.get(url, timeout=5, follow_redirects=True)
        r.raise_for_status()
        parsed = feedparser.parse(r.text)
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:PER_FEED]:
        title = (getattr(entry, "title", "") or "").strip()
        if not title:
            continue
        summary = _clean_summary(entry)
        # Drop summary that just repeats the title.
        if summary and summary.lower().startswith(title.lower()[:40]):
            summary = ""
        items.append({
            "title": title,
            "summary": summary,
            "link": getattr(entry, "link", None),
            "published": getattr(entry, "published", None),
        })
    return items


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    own = client is None
    c = client or httpx.AsyncClient(timeout=5, headers={"User-Agent": "gazeta/0.1"})
    try:
        out: dict[str, list] = {}
        for bucket, urls in FEEDS.items():
            results = await asyncio.gather(*(_fetch_feed(c, u) for u in urls))
            merged: list[dict] = []
            for r in results:
                merged.extend(r)
            # Deduplicate by title to avoid the same story from both feeds.
            seen: set[str] = set()
            unique: list[dict] = []
            for item in merged:
                key = item["title"].lower()
                if key in seen:
                    continue
                seen.add(key)
                unique.append(item)
            out[bucket] = unique[:PER_BUCKET]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()
    return out
