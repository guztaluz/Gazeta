from __future__ import annotations

import asyncio
from typing import Any

import feedparser
import httpx

FEEDS: dict[str, list[str]] = {
    "dublin": [
        "https://www.rte.ie/news/rss/news-headlines.xml",
        "https://www.thejournal.ie/feed/",
    ],
    "porto_alegre": [
        "https://gauchazh.clicrbs.com.br/rss/ultimas-noticias/",
        "https://g1.globo.com/rss/g1/rs/rio-grande-do-sul/",
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.reuters.com/world/feeds/",
    ],
}

PER_BUCKET = 3


async def _fetch_feed(client: httpx.AsyncClient, url: str) -> list[dict[str, Any]]:
    try:
        r = await client.get(url, timeout=5, follow_redirects=True)
        r.raise_for_status()
        parsed = feedparser.parse(r.text)
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:PER_BUCKET]:
        items.append({
            "title": getattr(entry, "title", "").strip(),
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
            out[bucket] = merged[:PER_BUCKET]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()
    return out
