from __future__ import annotations

import httpx

ENDPOINT = "https://icanhazdadjoke.com/"


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    own = client is None
    c = client or httpx.AsyncClient(timeout=5)
    try:
        r = await c.get(
            ENDPOINT,
            headers={"Accept": "application/json", "User-Agent": "gazeta (https://github.com/guztaluz/Gazeta)"},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()
    return {"text": data.get("joke", "")}
