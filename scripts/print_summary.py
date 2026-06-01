"""Build and print today's Gazeta — the full daily summary.

Runs the same pipeline the HTTP endpoint does (gather sources -> Claude ->
render -> printer), but as a one-shot command. This is what the morning cron
job will call on the NAS; for now you run it by hand from Terminal.app.

    cd /Users/gustavoluz/Desktop/Gazeta && .venv/bin/python scripts/print_summary.py

Honours PRINTER_DRIVER in .env: 'ble' prints for real, 'mock' just writes the
PNG to output/latest.png (useful for previewing without burning paper).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.routes.summary import print_summary


async def main() -> None:
    result = await print_summary()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
