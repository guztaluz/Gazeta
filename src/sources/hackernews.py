from __future__ import annotations

import asyncio

import httpx

TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


async def fetch(client: httpx.AsyncClient | None = None, n: int = 5) -> dict:
    own = client is None
    c = client or httpx.AsyncClient(timeout=5)
    try:
        r = await c.get(TOP_URL)
        r.raise_for_status()
        ids = r.json()[:n]
        items = await asyncio.gather(*(c.get(ITEM_URL.format(id=i)) for i in ids), return_exceptions=True)
        stories = []
        for resp in items:
            if isinstance(resp, Exception):
                continue
            try:
                item = resp.json()
            except Exception:
                continue
            stories.append({
                "title": item.get("title", ""),
                "url": item.get("url"),
                "score": item.get("score"),
                "by": item.get("by"),
            })
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()

    return {"stories": stories}
