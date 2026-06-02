"""Shared Google OAuth helpers for Calendar + Gmail."""
from __future__ import annotations

import json
from pathlib import Path

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from src.config import get_settings

log = structlog.get_logger()

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
]


def load_credentials() -> Credentials | None:
    """Load saved OAuth credentials, refreshing if needed. None if not set up."""
    s = get_settings()
    token_path = Path(s.google_token_path)
    if not token_path.exists():
        return None

    data = json.loads(token_path.read_text())
    creds = Credentials.from_authorized_user_info(data, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist the refreshed token, but DON'T fail the whole fetch if the
        # write can't happen (e.g. read-only mount). The in-memory creds are
        # already valid for this run.
        try:
            token_path.write_text(creds.to_json())
        except OSError as e:
            log.warning("token_write_failed", error=str(e))

    return creds if creds.valid else None
