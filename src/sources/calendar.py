from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from src.config import get_settings
from src.sources.google_auth import load_credentials


def _list_today_sync() -> list[dict]:
    s = get_settings()
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("Google OAuth not configured — run scripts/google_oauth.py")

    tz = ZoneInfo(s.weather_tz)
    today = datetime.now(tz).date()
    start = datetime.combine(today, time.min, tzinfo=tz)
    end = start + timedelta(days=1)

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    resp = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=20,
    ).execute()

    events = []
    for e in resp.get("items", []):
        start_obj = e.get("start", {})
        end_obj = e.get("end", {})
        events.append({
            "summary": e.get("summary", "(no title)"),
            "start": start_obj.get("dateTime") or start_obj.get("date"),
            "end": end_obj.get("dateTime") or end_obj.get("date"),
            "location": e.get("location"),
            "all_day": "date" in start_obj,
        })
    return events


async def fetch() -> dict:
    try:
        events = await asyncio.to_thread(_list_today_sync)
    except Exception as e:
        return {"error": str(e)}
    return {"events": events, "empty": len(events) == 0}
