# NoteKeep → Gazeta printer integration

Hand this file to a Claude session opened in the **NoteKeep** codebase. It is a
complete spec for adding a "Print" action that sends a note to the Gazeta
thermal-printer service. You do NOT need any Gazeta internals — just call the
HTTP endpoint below.

## What already exists (Gazeta side — done)

Gazeta runs an HTTP service that drives a 57mm Bluetooth thermal printer. It
exposes:

```
POST http://<gazeta-host>:8080/print/note
Content-Type: application/json
```

Request body:

```json
{
  "title": "string (optional) — shown as the note/section heading",
  "body":  "string — the note content (plain text)",
  "tags":  ["shopping"]    // optional; leading '#' is fine too
}
```

Behaviour (decided by tags, case-insensitive, '#' optional):

| tag                     | layout produced                                            |
|-------------------------|------------------------------------------------------------|
| `shopping` / `compras`  | items split by line/comma, auto-grouped by supermarket section, printed as a checkbox list |
| `recipe` / `receita`    | recipe layout (title + paragraphs)                         |
| (none / anything else)  | plain note (title + paragraphs)                            |

Response: `200` with `{"status":"ok","kind":"note|shopping|recipe","bytes":N}`.
On error: `4xx/5xx` with `{"detail":"..."}`.

The printer is single-user, no auth. Print takes ~10–20s; the POST returns
after the print is sent.

## What to build (NoteKeep side)

1. A **"Print" action** on a note (per-note menu item / long-press / button —
   whatever fits NoteKeep's UI).
2. On tap, POST the note to the endpoint above:
   - `title` = note title
   - `body`  = note body (plain text; strip markdown if NoteKeep stores it)
   - `tags`  = the note's tags (send them as-is; Gazeta handles `#shopping`,
     `#recipe`, etc.)
3. Show a lightweight result toast: "Printing…" → "Printed" / "Print failed".
4. Make the Gazeta base URL **configurable** (env var or setting), default
   `http://<gazeta-host>:8080`. On the same LAN this is the NAS/Mac running
   Gazeta. Don't hardcode an IP in source.

### Example call (any language)

```bash
curl -X POST http://gazeta.local:8080/print/note \
  -H 'Content-Type: application/json' \
  -d '{"title":"Compras da semana","body":"banana\nleite\nalface\npão","tags":["shopping"]}'
```

```ts
await fetch(`${GAZETA_URL}/print/note`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ title, body, tags }),
});
```

## Notes / gotchas

- Network only: NoteKeep must be able to reach the Gazeta host over the LAN.
  When Gazeta moves to the NAS, only the base URL changes.
- Keep `body` as plain text. For shopping lists, one item per line (or
  comma-separated) works best — Gazeta splits on newlines and commas.
- Tags drive the layout; if a note has no relevant tag it prints as a plain
  note, which is fine.
- No auth/rate-limiting by design (single-user hobby project).

## Test without NoteKeep

Once Gazeta is running (`uvicorn src.main:app --port 8080`), you can verify the
endpoint with the curl above before wiring the UI.
