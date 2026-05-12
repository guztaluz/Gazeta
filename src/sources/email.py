"""Scoped Gmail fetch: unread + important inbox messages from the last 24h.

Only sender + subject + Gmail's own 1-line snippet leave the service. No bodies.
"""
from __future__ import annotations

import asyncio

from googleapiclient.discovery import build

from src.sources.google_auth import load_credentials

# Last 24h, unread, in inbox, important, NOT promotions/social/forums.
QUERY = "newer_than:1d is:unread label:inbox label:important -category:promotions -category:social -category:forums"
MAX_RESULTS = 5


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _fetch_sync() -> list[dict]:
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("Google OAuth not configured — run scripts/google_oauth.py")

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    listing = service.users().messages().list(
        userId="me", q=QUERY, maxResults=MAX_RESULTS,
    ).execute()

    messages = listing.get("messages", []) or []
    out: list[dict] = []
    for m in messages:
        full = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = full.get("payload", {}).get("headers", [])
        out.append({
            "from": _header(headers, "From"),
            "subject": _header(headers, "Subject"),
            "snippet": full.get("snippet", ""),
        })
    return out


async def fetch() -> dict:
    try:
        items = await asyncio.to_thread(_fetch_sync)
    except Exception as e:
        return {"error": str(e), "items": [], "count": 0}
    return {"items": items, "count": len(items)}
