"""Минимальный клиент ComfyUI HTTP API.

Логика: подставить промт/seed в шаблон workflow (API format), отправить через
POST /prompt, дождаться окончания через polling /history/{prompt_id}, выгрузить
итоговое видео из /view (выходной node должен называться "OUTPUT_VIDEO" или
быть SaveAnimatedWEBP/SaveVideo с известным именем — определяется в шаблоне).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from ..config import settings


WORKFLOWS_DIR = Path(__file__).parent / "workflows"


class ComfyError(RuntimeError):
    pass


class ComfyCancelled(RuntimeError):
    """Генерация прервана через cancel_check."""


def load_workflow(name: str) -> dict:
    p = WORKFLOWS_DIR / f"{name}.json"
    if not p.exists():
        raise ComfyError(f"workflow '{name}' не найден: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def patch_workflow(wf: dict, patches: dict[str, dict[str, Any]]) -> dict:
    """Подменяет поля inputs у узлов. patches: {node_id: {input_name: value}}."""
    wf = deepcopy(wf)
    for node_id, fields in patches.items():
        if node_id not in wf:
            raise ComfyError(f"node {node_id} отсутствует в workflow")
        wf[node_id].setdefault("inputs", {}).update(fields)
    return wf


async def _post_prompt(client: httpx.AsyncClient, wf: dict, client_id: str) -> str:
    try:
        r = await client.post(
            f"{settings.comfyui_url}/prompt",
            json={"prompt": wf, "client_id": client_id},
        )
    except httpx.ConnectError as e:
        raise ComfyError(
            f"Нет соединения с ComfyUI: {settings.comfyui_url}. "
            "Проверьте, что ComfyUI запущен и COMFYUI_URL указан верно."
        ) from e
    if r.status_code >= 400:
        raise ComfyError(f"/prompt {r.status_code}: {r.text[:300]}")
    return r.json()["prompt_id"]


async def _wait_history(
    client: httpx.AsyncClient,
    prompt_id: str,
    timeout: float = 1800,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        if cancel_check is not None and cancel_check():
            await _cancel_prompt(client, prompt_id)
            raise ComfyCancelled()
        if asyncio.get_event_loop().time() > deadline:
            raise ComfyError("ComfyUI timeout")
        try:
            r = await client.get(f"{settings.comfyui_url}/history/{prompt_id}")
        except httpx.ConnectError as e:
            raise ComfyError(
                f"Потеряно соединение с ComfyUI: {settings.comfyui_url}. "
                "Проверьте, что ComfyUI не остановился во время генерации."
            ) from e
        if r.status_code == 200:
            data = r.json()
            if prompt_id in data:
                entry = data[prompt_id]
                status = entry.get("status", {}) or {}
                # ждём, пока ComfyUI пометит запуск как завершённый
                if status.get("completed") is True or status.get("status_str") in ("success", "error"):
                    if status.get("status_str") == "error":
                        msgs = status.get("messages") or []
                        # вытащим текст ошибки из execution_error
                        details = []
                        for m in msgs:
                            if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                                d = m[1] or {}
                                details.append(
                                    f"node {d.get('node_id')} ({d.get('node_type')}): {d.get('exception_message')}"
                                )
                        raise ComfyError(
                            "ComfyUI вернул ошибку выполнения: "
                            + ("; ".join(details) if details else str(msgs)[:500])
                        )
                    return entry
        await asyncio.sleep(1.0)


async def _cancel_prompt(client: httpx.AsyncClient, prompt_id: str) -> None:
    """Убрать prompt_id из очереди + прервать текущий шаг сэмплера."""
    try:
        await client.post(
            f"{settings.comfyui_url}/queue",
            json={"delete": [prompt_id]},
            timeout=5,
        )
    except Exception:
        pass
    try:
        await client.post(f"{settings.comfyui_url}/interrupt", timeout=5)
    except Exception:
        pass


async def interrupt_all() -> None:
    """Прервать всё + очистить pending."""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{settings.comfyui_url}/queue", json={"clear": True})
            await c.post(f"{settings.comfyui_url}/interrupt")
    except Exception:
        pass


async def _download_view(client: httpx.AsyncClient, filename: str, subfolder: str, ftype: str, dst: Path) -> None:
    try:
        r = await client.get(
            f"{settings.comfyui_url}/view",
            params={"filename": filename, "subfolder": subfolder, "type": ftype},
        )
    except httpx.ConnectError as e:
        raise ComfyError(
            f"Нет соединения с ComfyUI при скачивании результата: {settings.comfyui_url}"
        ) from e
    if r.status_code >= 400:
        raise ComfyError(f"/view {r.status_code}: {r.text[:300]}")
    dst.write_bytes(r.content)


async def run_workflow(
    wf: dict,
    out_path: Path,
    output_key: Optional[str] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Path:
    """Выполнить workflow и сохранить ПЕРВЫЙ найденный видео-выход в out_path.

    Если output_key задан — берётся только этот node_id из истории.
    Если cancel_check вернёт True в процессе ожидания — посылаем отмену в ComfyUI и бросаем ComfyCancelled.
    """
    client_id = uuid.uuid4().hex
    async with httpx.AsyncClient(timeout=60) as client:
        prompt_id = await _post_prompt(client, wf, client_id)
        hist = await _wait_history(client, prompt_id, cancel_check=cancel_check)
        outputs = hist.get("outputs", {}) or {}
        # ищем первый видео/гиф/webp файл
        candidates = []
        node_ids = [output_key] if output_key else list(outputs.keys())
        for nid in node_ids:
            node_out = outputs.get(nid, {}) or {}
            for key in ("gifs", "videos", "images"):
                for item in node_out.get(key, []) or []:
                    candidates.append(item)
        if not candidates:
            if output_key and output_key not in outputs:
                raise ComfyError(
                    f"нода {output_key!r} не дала выход (есть: {list(outputs.keys())}). "
                    "Возможно, не установлен ComfyUI-VideoHelperSuite (VHS_VideoCombine) "
                    "или workflow прерван до этой ноды."
                )
            raise ComfyError(f"в outputs нет файлов: {outputs}")
        # предпочтительно видео
        candidates.sort(key=lambda x: 0 if x.get("filename", "").lower().endswith((".mp4", ".webm", ".mov")) else 1)
        item = candidates[0]
        await _download_view(
            client,
            item["filename"],
            item.get("subfolder", ""),
            item.get("type", "output"),
            out_path,
        )
    return out_path


async def ping() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.comfyui_url}/system_stats")
            return r.status_code == 200
    except Exception:
        return False
