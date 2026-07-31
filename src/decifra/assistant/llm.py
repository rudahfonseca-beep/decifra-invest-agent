"""Shared OpenAI-compatible chat completion helper."""

from __future__ import annotations

from typing import Any

import httpx

from decifra.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    timeout: float = 120.0,
    model: str | None = None,
) -> str | None:
    """Call chat completions; return assistant content or None if unavailable/failed."""
    if not OPENAI_API_KEY:
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": model or OPENAI_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
