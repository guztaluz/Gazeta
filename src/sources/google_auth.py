"""Shared Google OAuth helpers for Calendar + Gmail."""
from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from src.config import get_settings

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
        token_path.write_text(creds.to_json())

    return creds if creds.valid else None
