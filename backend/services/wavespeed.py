"""Тонкий клиент WaveSpeed.ai REST API v3.

Сценарий:
1) POST /{model_id}  с {prompt, ...}  → {data: {id: "<task_id>"}}
2) GET  /predictions/{task_id}/result → polling до status="completed"|"failed"
3) Скачать первый URL из outputs в локальный файл.

Ошибки → WaveSpeedError. Cancel → CancelledError (если cancel_check).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from ..config import settings


class WaveSpeedError(RuntimeError):
    pass


class WaveSpeedCancelled(RuntimeError):
    pass


CancelCheck = Optional[Callable[[], bool]]


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def submit(model_id: str, body: dict[str, Any], api_key: str) -> str:
    url = f"{settings.wavespeed_base_url.rstrip('/')}/{model_id}"
    async with httpx.AsyncClient(timeout=60) as cli:
        try:
            r = await cli.post(url, json=body, headers=_headers(api_key))
        except httpx.HTTPError as e:
            raise WaveSpeedError(f"WaveSpeed submit transport error: {e}") from e
    if r.status_code == 401:
        raise WaveSpeedError("WaveSpeed: 401 — неверный API ключ")
    if r.status_code >= 400:
        raise WaveSpeedError(f"WaveSpeed submit {r.status_code}: {r.text[:400]}")
    data = r.json()
    task_id = (data.get("data") or {}).get("id") or data.get("id")
    if not task_id:
        raise WaveSpeedError(f"WaveSpeed: нет id задачи в ответе: {str(data)[:400]}")
    return str(task_id)


async def poll_result(
    task_id: str,
    api_key: str,
    cancel_check: CancelCheck = None,
) -> dict[str, Any]:
    url = f"{settings.wavespeed_base_url.rstrip('/')}/predictions/{task_id}/result"
    waited = 0.0
    interval = max(0.5, settings.wavespeed_poll_interval)
    max_wait = settings.wavespeed_max_wait
    async with httpx.AsyncClient(timeout=30) as cli:
        while True:
            if cancel_check and cancel_check():
                raise WaveSpeedCancelled("cancelled")
            try:
                r = await cli.get(url, headers=_headers(api_key))
            except httpx.HTTPError as e:
                raise WaveSpeedError(f"WaveSpeed poll transport error: {e}") from e
            if r.status_code >= 400:
                raise WaveSpeedError(f"WaveSpeed poll {r.status_code}: {r.text[:400]}")
            data = (r.json() or {}).get("data") or r.json()
            status = (data.get("status") or "").lower()
            if status in ("completed", "succeeded", "success"):
                return data
            if status in ("failed", "error", "canceled", "cancelled"):
                err = data.get("error") or data.get("message") or str(data)[:300]
                raise WaveSpeedError(f"WaveSpeed: {status}: {err}")
            await asyncio.sleep(interval)
            waited += interval
            if waited > max_wait:
                raise WaveSpeedError(f"WaveSpeed: timeout {max_wait}s, task {task_id}")


async def download(url: str, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as cli:
        async with cli.stream("GET", url) as r:
            if r.status_code >= 400:
                raise WaveSpeedError(f"WaveSpeed download {r.status_code}: {url}")
            with open(dst, "wb") as f:
                async for chunk in r.aiter_bytes(64 * 1024):
                    f.write(chunk)
    return dst


async def verify_key(api_key: str) -> bool:
    """Лёгкая проверка ключа: дёргаем /predictions/_check_/result — ждём 401 либо 404.
    401 → ключ невалиден. Любой другой ответ (включая 404) → ключ валиден."""
    if not api_key.strip():
        return False
    url = f"{settings.wavespeed_base_url.rstrip('/')}/predictions/__verify__/result"
    async with httpx.AsyncClient(timeout=15) as cli:
        try:
            r = await cli.get(url, headers=_headers(api_key))
        except httpx.HTTPError:
            return False
    return r.status_code != 401


def extract_first_video_url(result: dict[str, Any]) -> Optional[str]:
    outputs = result.get("outputs") or result.get("output") or []
    if isinstance(outputs, str):
        return outputs
    if isinstance(outputs, list) and outputs:
        first = outputs[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url") or first.get("video_url") or first.get("uri")
    # fallback ключи
    for k in ("video", "video_url", "url"):
        v = result.get(k)
        if isinstance(v, str):
            return v
    return None
