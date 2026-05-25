"""Управление жизненным циклом ComfyUI: автозапуск, healthcheck, остановка."""

from __future__ import annotations

import asyncio
import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import httpx

from ..config import settings


_proc: Optional[subprocess.Popen] = None


async def is_alive(timeout: float = 3.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(f"{settings.comfyui_url}/system_stats")
            return r.status_code == 200
    except Exception:
        return False


async def wait_ready(timeout: float = 180.0) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if await is_alive(timeout=2.0):
            return True
        await asyncio.sleep(2.0)
    return False


def _terminate() -> None:
    global _proc
    if _proc and _proc.poll() is None:
        try:
            if os.name == "nt":
                _proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                _proc.terminate()
            _proc.wait(timeout=10)
        except Exception:
            try:
                _proc.kill()
            except Exception:
                pass
    _proc = None


async def start_if_needed() -> None:
    """Стартует ComfyUI в фоне, если включён autostart и он недоступен."""
    if not settings.comfyui_autostart:
        return
    if await is_alive(timeout=2.0):
        return

    comfy_dir: Path = settings.comfyui_path.resolve()
    main_py = comfy_dir / "main.py"
    if not main_py.exists():
        # не установлен — молча выходим, пользователь сможет указать внешний URL
        return

    venv_py = Path(sys.executable)
    log_path = settings.data_dir / "comfyui.log"
    log_f = log_path.open("a", encoding="utf-8", errors="ignore")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    global _proc
    _proc = subprocess.Popen(
        [
            str(venv_py),
            str(main_py),
            "--listen", "127.0.0.1",
            "--port", str(settings.comfyui_port),
        ],
        cwd=str(comfy_dir),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    atexit.register(_terminate)

    # ждём, пока поднимется
    await wait_ready(timeout=180.0)


async def shutdown() -> None:
    _terminate()
