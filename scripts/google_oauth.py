"""One-time OAuth setup for Google Calendar + Gmail.

Prerequisites:
1. Go to https://console.cloud.google.com/, create a new project (or use one).
2. Enable both APIs: Google Calendar API and Gmail API.
3. APIs & Services → OAuth consent screen → External → fill the basics.
   Add your own email as a Test User. Scopes: leave default.
4. APIs & Services → Credentials → Create credentials → OAuth client ID.
   Application type: Desktop app. Download the JSON.
5. Save it as secrets/client_secret.json in this repo.
6. Run this script: python scripts/google_oauth.py
   A browser tab opens; sign in, click Continue past the "unverified app" warning.
7. The token is written to secrets/google_token.json. You're done.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow

from src.config import get_settings
from src.sources.google_auth import SCOPES


def main() -> None:
    s = get_settings()
    client_secret = Path(s.google_client_secret_path)
    token_path = Path(s.google_token_path)

    if not client_secret.exists():
        print(f"ERROR: {client_secret} not found.")
        print("Download the OAuth client JSON from GCP and save it there.")
        print("See the docstring of this script for full instructions.")
        sys.exit(1)

    token_path.parent.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    token_path.write_text(creds.to_json())

    print(f"OK. Token written to {token_path}")
    print(f"Granted scopes: {', '.join(SCOPES)}")


if __name__ == "__main__":
    main()
