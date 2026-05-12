from __future__ import annotations

from datetime import date

import httpx

BASE = "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events"

# Wikipedia REST API requires a User-Agent with contact info.
_UA = "gazeta/0.1 (https://github.com/guztaluz/Gazeta; guztaluz@gmail.com)"


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    today = date.today()
    url = f"{BASE}/{today.month:02d}/{today.day:02d}"

    own = client is None
    c = client or httpx.AsyncClient(timeout=5)
    try:
        r = await c.get(url, headers={"User-Agent": _UA})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()

    events = data.get("events", []) or []
    # Wikipedia returns them oldest-first sometimes; pick a spread.
    trimmed = []
    for e in events[:25]:
        text = e.get("text", "").strip()
        year = e.get("year")
        if text and year:
            trimmed.append({"year": year, "text": text})
    # Hand 5 to the LLM and let it pick.
    return {"events": trimmed[:5]}
