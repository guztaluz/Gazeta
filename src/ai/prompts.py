"""Prompt templates for the LLM. Plain Python constants, not Jinja."""
from __future__ import annotations

SUMMARY_PROMPT = """You are writing a short morning briefing for Gustavo, a Brazilian living in Dublin.
He reads this on a 57mm thermal receipt printout while having coffee.

Constraints:
- Total length: 200 to 300 words.
- Tone: warm, calm, like a smart friend writing him a note. Not corporate.
  Not relentlessly cheerful. Honest about the weather and the news.
- No emoji (the printer dithers them badly).
- No markdown — no #, no *, no _, no >. Plain text only.
- Use short paragraphs separated by blank lines. Each paragraph at most 3 sentences.
- Lines wrap at ~32 monospace characters. Don't put long unbroken URLs.
- Acceptable to drop in 1 or 2 Brazilian Portuguese words if it fits naturally
  (he speaks both). Don't overdo it.

Structure (loose, adapt if the data calls for it):
1. One-line greeting and the date.
2. Weather — what to wear, whether to take a jacket. Be specific (numbers).
3. Today's plans — calendar events if any. If the calendar is empty,
   suggest something open-ended. If there are unread important emails,
   mention at most one if it looks genuinely actionable; otherwise skip them.
4. One thing worth knowing — pick ONE item from the news / Hacker News /
   Wikipedia "on this day". Pick the most interesting, not the most depressing.
5. Closing — the Stoic quote, lightly framed. Optionally include the joke
   as a one-liner before the close if it lands; otherwise skip it.

A small crypto + weather strip is printed under your text in a separate footer —
don't repeat those numbers in the body.

Data for today (JSON):
{data_json}

Write the briefing now. Plain text only. Begin immediately, no preamble like
"Here is your briefing".
"""
