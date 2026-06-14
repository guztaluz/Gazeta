"""FIFA World Cup 2026 fixtures & results via TheSportsDB (free, no key).

We hit the per-day endpoint across a small window around today, because the
free-tier next/past-league endpoints only return a single event. Times come
back in UTC; we localize to the user's timezone for display.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from src.config import get_settings

# TheSportsDB league id for the FIFA World Cup. Free test key "3".
LEAGUE_ID = "4429"
ENDPOINT = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php"

# How far back / forward to look for results and fixtures.
DAYS_BACK = 2
DAYS_AHEAD = 3

_FINISHED = {"FT", "AET", "PEN", "Match Finished", "AP"}
_LIVE = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INPLAY"}

_PT_DOW = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


async def _fetch_day(c: httpx.AsyncClient, day: str) -> list[dict]:
    try:
        r = await c.get(ENDPOINT, params={"d": day, "l": LEAGUE_ID}, timeout=6)
        r.raise_for_status()
        return r.json().get("events") or []
    except Exception:
        return []


def _kickoff_local(ev: dict, tz: ZoneInfo) -> datetime | None:
    ts = ev.get("strTimestamp")
    if ts:
        try:
            return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc).astimezone(tz)
        except ValueError:
            pass
    # Fallback: date + UTC time fields.
    d, t = ev.get("dateEvent"), ev.get("strTime") or "00:00:00"
    if not d:
        return None
    try:
        naive = datetime.fromisoformat(f"{d}T{t[:8]}")
        return naive.replace(tzinfo=timezone.utc).astimezone(tz)
    except ValueError:
        return None


def _day_label(when: datetime, today) -> str:
    delta = (when.date() - today).days
    if delta == 0:
        return "HOJE"
    if delta == 1:
        return "AMANHÃ"
    if delta == -1:
        return "ONTEM"
    return _PT_DOW[when.weekday()]


def _is_brazil(ev: dict) -> bool:
    return "brazil" in (
        f"{ev.get('strHomeTeam', '')} {ev.get('strAwayTeam', '')}".lower()
    )


async def fetch(client: httpx.AsyncClient | None = None) -> dict:
    s = get_settings()
    tz = ZoneInfo(s.weather_tz)
    today = datetime.now(tz).date()

    days = [
        (today + timedelta(days=n)).isoformat()
        for n in range(-DAYS_BACK, DAYS_AHEAD + 1)
    ]

    own = client is None
    c = client or httpx.AsyncClient(timeout=6, headers={"User-Agent": "gazeta/0.1"})
    try:
        batches = await asyncio.gather(*(_fetch_day(c, d) for d in days))
    except Exception as e:
        return {"error": str(e)}
    finally:
        if own:
            await c.aclose()

    seen: set[str] = set()
    results: list[dict] = []
    upcoming: list[dict] = []

    for batch in batches:
        for ev in batch:
            eid = ev.get("idEvent")
            if eid in seen:
                continue
            seen.add(eid)

            when = _kickoff_local(ev, tz)
            status = (ev.get("strStatus") or "").strip()
            hs, as_ = ev.get("intHomeScore"), ev.get("intAwayScore")
            has_score = hs is not None and as_ is not None

            row = {
                "home": ev.get("strHomeTeam", "?"),
                "away": ev.get("strAwayTeam", "?"),
                "home_score": hs,
                "away_score": as_,
                "when": when,
                "day": _day_label(when, today) if when else "",
                "time": when.strftime("%H:%M") if when else "",
                "brazil": _is_brazil(ev),
                "live": status in _LIVE,
            }

            if status in _LIVE:
                row["live"] = True
                results.append(row)
            elif status in _FINISHED or (has_score and when and when.date() < today):
                results.append(row)
            elif when is not None:
                upcoming.append(row)

    results.sort(key=lambda r: r["when"] or datetime.min.replace(tzinfo=tz), reverse=True)
    upcoming.sort(key=lambda r: r["when"] or datetime.max.replace(tzinfo=tz))

    # Drop the datetime objects before handing off (not JSON-serializable, and
    # the template only needs the formatted day/time strings).
    def _clean(rows: list[dict]) -> list[dict]:
        for r in rows:
            r.pop("when", None)
        return rows

    return {
        "results": _clean(results[:4]),
        "upcoming": _clean(upcoming[:5]),
    }
