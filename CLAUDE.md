# Receipt Printer Daily Summary — Project Spec

A self-hosted service running on a UGREEN NASync DXP2800 that drives a cheap Bluetooth thermal printer (Tiny Print app / X6 model, MX-series chip). Prints a personalized daily summary every morning, plus on-demand prints from NoteKeep (a self-hosted PWA), and a growing list of other use cases.

This file is the long-term project memory. Update it as the project evolves. Keep it as the source of truth for Claude Code sessions.

---

## 1. Goals

**Primary goal:** Print a daily morning summary on a cheap thermal printer.

**Secondary goals:**

- Print arbitrary content from NoteKeep (shopping lists, recipes, notes) on demand.
- Expose a generic HTTP "print this" endpoint that any service on the NAS can call.
- Keep total ongoing cost under €10/year.
- Keep the codebase small, readable, and easy to extend.

**Non-goals (for now):**

- Real-time printing (BLE 4.0 latency is fine for the use cases).
- Color, high-resolution photo printing (200 DPI dithered B&W is the constraint, lean into it).
- Mobile-out-of-home use (the printer lives on the desk, plugged in).

---

## 2. Hardware

| Component | Detail |
|---|---|
| Printer | Generic X6-series mini thermal printer (MX-family chip, paired via "Tiny Print" app on phone for initial test) |
| Paper width | 57mm thermal roll, non-adhesive (sticker rolls also compatible if needed) |
| Resolution | 200 DPI, black & white only |
| Connection | Bluetooth Low Energy 4.0 |
| Battery | 800 mAh, USB-C charging — keep plugged in 24/7 on desk |
| NAS | UGREEN NASync DXP2800 (Intel N100, 32GB DDR5, single SO-DIMM slot, no Bluetooth onboard) |
| BT dongle | Add a CSR8510-based USB Bluetooth adapter to the NAS (~€8 on Amazon). Confirm BlueZ compatibility before buying. |

**Important:** The NAS has no built-in Bluetooth, so a USB BT dongle is required and must be passed through to the Docker container running the printer service.

---

## 3. Software architecture

A single Python service running in a Docker container on the NAS. Exposes an HTTP API. Cron schedules call it. NoteKeep and other services also call it.

```
                       ┌─────────────────────────────┐
                       │     printer-service (Docker)│
                       │                             │
   cron (07:00) ──────▶│  POST /print/summary        │──┐
   NoteKeep   ─────────▶│  POST /print/note           │──┤
   any service ────────▶│  POST /print/raw            │──┤
                       │                             │  │
                       │  ┌───────────────────────┐  │  ▼
                       │  │ render → PNG → BLE    │  │ ┌──────────┐
                       │  │ (via TiMini-Print CLI)│  │ │ Printer  │
                       │  └───────────────────────┘  │ │ (X6 BLE) │
                       └─────────────────────────────┘ └──────────┘
```

### Why this shape

- **One service**: avoids tangled microservices for a hobby project.
- **HTTP API**: any future caller (an iOS Shortcut, a Home Assistant automation, a webhook, a physical button) can use it without knowing about Bluetooth.
- **Render → PNG → printer** as a single pipeline: keeps the printer driver layer dumb. Everything upstream just produces an image.

---

## 4. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Mature BLE libraries, Pillow for image rendering, simple deployment |
| Web framework | FastAPI | Async, auto-docs, type hints, tiny |
| Image rendering | Pillow + html2image (or weasyprint) | HTML/CSS templates are easier to iterate on than raw PIL drawing |
| Printer driver | TiMini-Print CLI (https://github.com/Dejniel/TiMini-Print) | Supports the X6 explicitly, has CLI mode |
| BLE backend | bleak (used internally by TiMini-Print) | Cross-platform, async |
| LLM | Anthropic API (Claude Sonnet via console.anthropic.com pay-as-you-go) | ~€5-10/year for this volume |
| Container | Docker, host network mode | Easiest BLE passthrough |
| Scheduling | host cron calling `curl http://localhost:8080/print/summary` | Simple, debuggable, no extra dependency |
| Config | `.env` file + Pydantic settings | API keys, printer MAC, schedule overrides |
| Logging | structlog → stdout → Docker logs | Searchable, no separate log file management |

---

## 5. Repository layout (proposed)

```
printer-service/
├── README.md
├── CLAUDE.md                 ← this file
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── src/
│   ├── main.py               ← FastAPI app entry
│   ├── config.py             ← Settings (Pydantic)
│   ├── printer/
│   │   ├── driver.py         ← Wraps TiMini-Print CLI
│   │   └── renderer.py       ← Text/HTML → 384px-wide PNG
│   ├── routes/
│   │   ├── summary.py        ← POST /print/summary
│   │   ├── note.py           ← POST /print/note (from NoteKeep)
│   │   └── raw.py            ← POST /print/raw (generic)
│   ├── sources/              ← Data fetchers
│   │   ├── weather.py        ← Open-Meteo API (free, no key)
│   │   ├── calendar.py       ← Google Calendar (OAuth) or CalDAV
│   │   ├── news.py           ← Hacker News, RSS, etc.
│   │   ├── immich.py         ← "On this day" photos
│   │   └── obsidian.py       ← Today's daily note from NAS vault
│   ├── ai/
│   │   ├── client.py         ← Anthropic SDK wrapper
│   │   └── prompts.py        ← Prompt templates as Python constants
│   └── templates/
│       ├── summary.html.j2   ← Daily summary layout
│       ├── shopping.html.j2  ← Shopping list layout (for NoteKeep)
│       ├── recipe.html.j2    ← Recipe layout
│       └── _base.html.j2     ← Common 57mm-width CSS
├── scripts/
│   ├── test_print.py         ← Print a test page (CLI, no service)
│   └── find_printer.py       ← BLE scan to discover printer MAC
└── tests/
    └── test_renderer.py      ← Snapshot tests for templates
```

---

## 6. Implementation phases

Build it in order. Each phase delivers something working.

### Phase 1: Hello, printer

**Goal:** Get a single PNG image to print from the NAS.

- [ ] Plug USB BT dongle into NAS. Verify `lsusb` and `hciconfig` see it.
- [ ] Set up a Python venv on the NAS (not Docker yet — easier to debug).
- [ ] Install `bleak`, run a BLE scan, find the printer's MAC address. Save it to `.env`.
- [ ] Clone TiMini-Print, install dependencies.
- [ ] Generate a 384×500px PNG of "Hello Gustavo" using Pillow.
- [ ] Print it via TiMini-Print CLI. Adjust contrast/dither until legible.

**Success:** A piece of paper with "Hello Gustavo" comes out of the printer.

### Phase 2: HTTP wrapper

**Goal:** Print over HTTP.

- [ ] FastAPI app with one endpoint: `POST /print/raw` accepting `{"text": "..."}` or `{"image_base64": "..."}`.
- [ ] Renderer function: text → PNG (Pillow, monospace font, 384px wide).
- [ ] Driver function: PNG → printer (shell out to TiMini-Print CLI).
- [ ] Test with `curl`.

**Success:** `curl -X POST -d '{"text":"hello"}' localhost:8080/print/raw` prints "hello".

### Phase 3: Dockerize

**Goal:** Service runs in Docker, survives reboots.

- [ ] Dockerfile with Python 3.12, bluez, TiMini-Print, the service.
- [ ] docker-compose.yml with `network_mode: host`, device passthrough for the BT dongle, `--cap-add NET_ADMIN`.
- [ ] Auto-restart policy.
- [ ] Test from another machine: `curl -X POST nas.local:8080/print/raw -d ...`.

**Success:** NAS reboots, printer service is back up automatically.

### Phase 4: Daily summary

**Goal:** Cron prints a summary every morning at 07:00.

- [ ] Add Anthropic API key to `.env`. Top up €5 at console.anthropic.com.
- [ ] Implement minimal data sources first: weather (Open-Meteo, no key needed) + a Stoic quote (static list, pick random).
- [ ] Write the summary prompt template. Keep it personal but tight.
- [ ] Implement `POST /print/summary` endpoint.
- [ ] Add a Jinja2 HTML template for the summary, render via html2image to PNG.
- [ ] Host cron: `0 7 * * * curl -X POST http://localhost:8080/print/summary`.

**Success:** Wake up, summary is waiting on the desk.

### Phase 5: More data sources

**Goal:** Make the summary genuinely useful.

Add sources one at a time, in this priority order:

1. Google Calendar (today's events) — needs OAuth setup, do this once and store refresh token
2. Hacker News top stories (no auth, simple API)
3. Immich "on this day" — Immich has a Python SDK, runs on the same NAS
4. Obsidian — read today's daily note from the vault on disk, summarize unfinished tasks
5. RSS digest — feedparser, pick 2-3 most recent items from a curated list

Each source is a separate module under `src/sources/`. Each returns a structured dict. The Anthropic prompt receives all dicts and writes the narrative summary.

### Phase 6: NoteKeep integration

**Goal:** Print notes from NoteKeep with a tap.

- [ ] Add `POST /print/note` endpoint accepting `{"title": "...", "body": "...", "tags": [...]}`.
- [ ] Route based on tag: `#shopping` → shopping template, `#recipe` → recipe template, default → plain note template.
- [ ] For shopping lists: send to Claude with a "categorize by supermarket section, output as markdown checklist" prompt before rendering.
- [ ] In NoteKeep, add a print button (per-note menu) that POSTs to the printer service.

**Success:** Long-press a note in NoteKeep → "Print" → comes out of the printer in 20 seconds.

### Phase 7: Future fun

Pick from the brainstorm list. Suggested first additions, in order of ROI:

- Physical button (iOS Shortcut via webhook is fine to start; physical Shelly button later).
- "On this day" photo printing from Immich.
- Sunday-night meal plan + shopping list generation.

---

## 7. The summary prompt (starting point)

This is the meat of the daily summary. Iterate on this freely.

```
You are writing a short morning briefing for Gustavo, a Brazilian living in Dublin.
He'll read this on a 57mm thermal receipt printout while having coffee.

Constraints:
- Total length: 200-300 words maximum.
- Tone: warm, calm, like a smart friend writing him a note. Not corporate.
  Not relentlessly cheerful. Honest about the weather.
- No emoji (the printer dithers them badly).
- No markdown headers or asterisks. Plain text only.
- Use short paragraphs separated by blank lines. Each paragraph ≤ 3 sentences.
- Acceptable to use 1-2 Brazilian Portuguese words if it fits naturally
  (he speaks both). Don't overdo it.

Structure (loose, adapt if the data calls for it):
1. One-line greeting + date.
2. Weather paragraph — what to wear, whether to take a jacket.
3. Calendar paragraph — what today looks like, anything notable.
4. One thing worth knowing — pick from the news/HN items.
5. Closing line — a thought, a question, a Stoic line, or a small prompt.

Data for today:
{data_json}

Write the briefing now.
```

Refine this over time. Save iterations in a `prompts/` directory if needed.

---

## 8. Rendering constraints

The printer is 384 pixels wide (57mm × 200 DPI ≈ 384). Plan for that.

- **Font:** Use a monospace font for body text (JetBrains Mono, Inconsolata, or built-in DejaVu Sans Mono). Easier to predict line wrapping.
- **Font size:** 16-20px body, 24-28px headers.
- **Character width:** Roughly 30-32 monospace characters per line at 16px.
- **Margins:** 8px on each side. Don't print to the edge.
- **Dither:** When converting to 1-bit, use Floyd-Steinberg dithering for any photo content.
- **Separator lines:** Use `─` characters or thin horizontal rules, not heavy blocks.
- **Total height:** No limit really, but keep summaries under ~600px (about 9cm of paper) to stay readable.

HTML/CSS approach for templates:

```css
@page { size: 384px auto; margin: 0; }
body { width: 368px; padding: 0 8px; font-family: 'JetBrains Mono', monospace; font-size: 16px; }
h1 { font-size: 24px; }
.separator { border-top: 1px dashed black; margin: 12px 0; }
```

---

## 9. Data sources (free tier / open APIs)

| Source | URL | Auth | Notes |
|---|---|---|---|
| Open-Meteo | https://open-meteo.com | None | Best free weather API. Dublin lat/lon: 53.35, -6.26 |
| Google Calendar | https://developers.google.com/calendar | OAuth | One-time setup, store refresh token |
| Hacker News | https://github.com/HackerNews/API | None | Public Firebase, just fetch top stories |
| Immich | self-hosted on NAS | API key | Has "on this day" built in |
| RSS | local list | None | Use `feedparser` Python lib |
| Wikipedia | https://en.wikipedia.org/api/rest_v1/ | None | "On this day" endpoint |

Add new sources as needed. Each should be its own file under `src/sources/` with a single `fetch() -> dict` function.

---

## 10. Configuration

`.env` file (not committed):

```bash
# Printer
PRINTER_MAC=XX:XX:XX:XX:XX:XX
PRINTER_WIDTH_PX=384

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5  # check current model name when implementing

# Service
SERVICE_PORT=8080
LOG_LEVEL=INFO

# Sources
WEATHER_LAT=53.35
WEATHER_LON=-6.26
GOOGLE_CALENDAR_REFRESH_TOKEN=...
IMMICH_URL=http://localhost:2283
IMMICH_API_KEY=...
OBSIDIAN_VAULT_PATH=/mnt/vault
```

---

## 11. Open questions (to decide as we go)

- **OAuth flow for Google Calendar**: do a one-time manual flow on a laptop, copy the refresh token into `.env`. Don't build a full OAuth UI.
- **Failure modes**: what if Claude API is down at 07:00? Print a fallback "minimal summary" with just weather + calendar from raw data, no narrative.
- **Time zone**: NAS time zone vs. user time zone (currently same: Europe/Dublin). Note this when adding travel handling.
- **Multiple users**: not a goal. Single-user app.
- **Web UI**: not in scope. Configuration is `.env`-based. Maybe a simple `/preview` endpoint that renders the next summary as HTML without printing.

---

## 12. Working agreements with Claude Code

When working on this project:

- **Don't suggest pausing or breaking tasks across sessions.** Keep going until the current task is done.
- **Show diffs and changes inline** before applying.
- **For new data sources**, follow the existing pattern in `src/sources/` — one file, one `fetch()` function.
- **Avoid over-engineering.** This is a single-user hobby project. No auth, no rate limiting, no fancy queues. Just direct calls.
- **When choosing dependencies**, prefer the boring, well-maintained ones. Avoid anything that looks abandoned.
- **Templates over hardcoded strings.** Anything user-visible goes in a Jinja2 template, not in Python source.
- **Default to incremental commits** with descriptive messages, even on a personal repo.

---

## 13. Quick links

- TiMini-Print: https://github.com/Dejniel/TiMini-Print
- Bleak (BLE library): https://github.com/hbldh/bleak
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- Open-Meteo docs: https://open-meteo.com/en/docs
- Immich API: https://immich.app/docs/api
- FastAPI: https://fastapi.tiangolo.com

---

*Last updated: project inception. Update this file as architecture decisions are made.*
