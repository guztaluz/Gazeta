from __future__ import annotations

import asyncio
import re
from typing import Any

import feedparser
import httpx

# Feeds grouped by topic Gustavo cares about. The topic tag travels with each
# item so the LLM curation step can balance variety and skip the war-news loop.
# Buckets are NOT printed separately anymore — everything is merged into one
# flat pool that the LLM picks from.
FEEDS: dict[str, list[str]] = {
    "tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "brasil": [
        "https://g1.globo.com/rss/g1/",
        "https://www.bbc.com/portuguese/index.xml",
    ],
    "ciencia": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/top/science.xml",
    ],
    "irlanda": [
        "https://www.rte.ie/news/rss/news-headlines.xml",
        "https://www.thejournal.ie/feed/",
    ],
    # Kept only so genuinely major world news can surface; the LLM is told to
    # ignore the repetitive war coverage unless something is truly urgent.
    "mundo": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
}

PER_FEED = 6
POOL_MAX = 32

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# Video / clickbait prefixes — useless on paper, dropped before the LLM sees them.
_VIDEO_RE = re.compile(r"^\s*(v[íi]deo|assista|veja o v[íi]deo|ao vivo|podcast)\b[:\s]", re.I)
# Common trailing junk in feed summaries.
_TRAIL_RE = re.compile(r"(Read more on|Continue reading|The post .* appeared first.*)$", re.I)


def _clean_summary(entry: Any, max_chars: int = 220) -> str:
    raw = getattr(entry, "summary", None) or getattr(entry, "description", "") or ""
    text = _TAG_RE.sub("", raw)
    text = _WS_RE.sub(" ", text).strip()
    text = _TRAIL_RE.sub("", text).strip()
    if not text:
        return ""
    if len(text) > max_chars:
        # Prefer cutting at a sentence end within range; else at a word.
        window = text[:max_chars]
        cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
        if cut >= max_chars * 0.5:
            text = window[:cut + 1]
        else:
            text = window.rsplit(" ", 1)[0].rstrip(",;:.") + "…"
    return text


async def _fetch_feed(client: httpx.AsyncClient, url: str, topic: str) -> list[dict[str, Any]]:
    try:
        r = await client.get(url, timeout=8, follow_redirects=True)
        r.raise_for_status()
        parsed = feedparser.parse(r.text)
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:PER_FEED]:
        title = (getattr(entry, "title", "") or "").strip()
        if not title or _VIDEO_RE.match(title):
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
            "topic": topic,
        })
    return items


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    own = client is None
    c = client or httpx.AsyncClient(timeout=5, headers={"User-Agent": "gazeta/0.1"})
    try:
        jobs = [
            _fetch_feed(c, url, topic)
            for topic, urls in FEEDS.items()
            for url in urls
        ]
        results = await asyncio.gather(*jobs)
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()

    by_topic: dict[str, list[dict]] = {t: [] for t in FEEDS}
    for r in results:
        for item in r:
            by_topic.setdefault(item["topic"], []).append(item)

    # Round-robin across topics so every theme is represented in the pool (a
    # straight concat + cap would starve whatever comes last). The LLM then
    # picks the most interesting items for Gustavo (see prompts.NEWS rules).
    queues = [list(by_topic[t]) for t in FEEDS]
    pool: list[dict] = []
    seen: set[str] = set()
    while any(queues) and len(pool) < POOL_MAX:
        for q in queues:
            if not q:
                continue
            item = q.pop(0)
            key = item["title"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            pool.append(item)
            if len(pool) >= POOL_MAX:
                break

    return {"pool": pool}
