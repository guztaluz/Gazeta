"""Anthropic Claude wrapper. One function in, one string out."""
from __future__ import annotations

from anthropic import AsyncAnthropic

from src.config import get_settings


async def generate(system: str, user: str) -> str:
    s = get_settings()
    if not s.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")

    client = AsyncAnthropic(api_key=s.anthropic_api_key)

    response = await client.messages.create(
        model=s.anthropic_model,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text
    return ""
