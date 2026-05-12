from __future__ import annotations

import httpx

ENDPOINT = "https://api.coingecko.com/api/v3/simple/price"
_IDS = {"bitcoin": "btc", "ethereum": "eth"}


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    own = client is None
    c = client or httpx.AsyncClient(timeout=5)
    try:
        r = await c.get(
            ENDPOINT,
            params={
                "ids": ",".join(_IDS),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            headers={"User-Agent": "gazeta/0.1"},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()

    out: dict = {}
    for gecko_id, key in _IDS.items():
        row = data.get(gecko_id, {})
        if not row:
            continue
        price = row.get("usd")
        change = row.get("usd_24h_change")
        out[key] = {
            "price_usd": price,
            "change_24h_pct": change,
            "arrow": "up" if (change or 0) >= 0 else "down",
        }
    return out
