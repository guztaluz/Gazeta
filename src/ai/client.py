"""Thin async wrapper over the Groq SDK.

Swappable later: replace the body of `generate()` with an Anthropic call.
The function signature is the only thing callers depend on.
"""
from __future__ import annotations

import asyncio

from groq import Groq

from src.config import get_settings


async def generate(prompt: str) -> str:
    s = get_settings()
    if not s.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set in .env")

    def _call() -> str:
        client = Groq(api_key=s.groq_api_key)
        resp = client.chat.completions.create(
            model=s.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
        return resp.choices[0].message.content or ""

    return await asyncio.to_thread(_call)
