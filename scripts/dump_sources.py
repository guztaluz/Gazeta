"""Run every data source and print the resulting JSON. Eyeball it."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

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


async def main() -> None:
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

    labels = ["weather", "crypto", "quote", "joke", "wikipedia", "hackernews", "news", "calendar", "email"]
    out = {}
    for label, r in zip(labels, results):
        if isinstance(r, Exception):
            out[label] = {"error": repr(r)}
        else:
            out[label] = r
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
