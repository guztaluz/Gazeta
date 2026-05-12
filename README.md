# Gazeta

Daily morning summary printed on a 57mm Bluetooth thermal printer. Self-hosted on a UGREEN NASync DXP2800. See [CLAUDE.md](CLAUDE.md) for the full spec.

## Quick start (dev, no printer)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

cp .env.example .env
# fill in GROQ_API_KEY at minimum; defaults work for Dublin weather

uvicorn src.main:app --reload --port 8080
```

Trigger a summary:

```bash
curl -X POST http://localhost:8080/print/summary
open output/latest.png
```

While the printer is in transit, `PRINTER_DRIVER=mock` writes PNGs to `output/`. Flip to `ble` once the device arrives.
