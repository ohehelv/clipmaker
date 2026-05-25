"""Тонкий клиент OpenRouter (OpenAI-совместимый /chat/completions)."""

from __future__ import annotations

import json
from typing import Optional

import httpx

from ..config import settings


class LLMError(RuntimeError):
    pass


async def chat(system: str, user: str, model: Optional[str] = None, temperature: float = 0.7) -> str:
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY не задан")
    url = settings.openrouter_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model or settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "ClipMaker",
    }
    async with httpx.AsyncClient(timeout=120) as cli:
        r = await cli.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            raise LLMError(f"OpenRouter {r.status_code}: {r.text[:300]}")
        data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"Неожиданный ответ: {json.dumps(data)[:300]}") from e
