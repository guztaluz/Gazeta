from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from src.config import get_settings
from src.sources.google_auth import load_credentials


# How many days ahead (beyond today) to scan for upcoming events.
WEEK_AHEAD = 7

_PT_DOW = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _event_date(start_obj: dict, tz: ZoneInfo):
    """Local date of an event, all-day or timed."""
    raw = start_obj.get("dateTime") or start_obj.get("date")
    if not raw:
        return None
    if "date" in start_obj and "dateTime" not in start_obj:
        return datetime.fromisoformat(raw).date()
    return datetime.fromisoformat(raw).astimezone(tz).date()


def _list_week_sync() -> dict:
    s = get_settings()
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("Google OAuth not configured — run scripts/google_oauth.py")

    tz = ZoneInfo(s.weather_tz)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)
    start = datetime.combine(today, time.min, tzinfo=tz)
    end = start + timedelta(days=WEEK_AHEAD)

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    resp = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=50,
    ).execute()

    today_events: list[dict] = []
    tomorrow_events: list[dict] = []
    upcoming: list[dict] = []

    for e in resp.get("items", []):
        start_obj = e.get("start", {})
        d = _event_date(start_obj, tz)
        if d is None:
            continue
        recurring = bool(e.get("recurringEventId"))
        # Google tags birthday/anniversary entries with eventType="birthday".
        # Without this, the LLM reads a bare name ("Berna") as a meeting.
        event_type = e.get("eventType", "default")
        item = {
            "summary": e.get("summary", "(sem título)"),
            "start": start_obj.get("dateTime") or start_obj.get("date"),
            "location": e.get("location"),
            "all_day": "date" in start_obj and "dateTime" not in start_obj,
            "weekday": _PT_DOW[d.weekday()],
            "recurring": recurring,
            "type": event_type,
        }
        if d == today:
            today_events.append(item)
        elif d == tomorrow:
            # The day-before reminder — this is where recurring chores (lixo na
            # quarta, printed on terça) surface, without spamming every day.
            tomorrow_events.append(item)
        else:
            # Later this week: only one-off events get a heads-up. Recurring
            # series are intentionally dropped here — we only nudge them on the
            # eve, so they don't repeat in the briefing every single day.
            if not recurring:
                upcoming.append(item)

    return {
        "today": today_events,
        "tomorrow": tomorrow_events,
        "upcoming": upcoming,
    }


async def fetch() -> dict:
    try:
        buckets = await asyncio.to_thread(_list_week_sync)
    except Exception as e:
        return {"error": str(e)}
    buckets["empty"] = len(buckets["today"]) == 0
    return buckets
