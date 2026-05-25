from __future__ import annotations

from fastapi import APIRouter

from ..config import settings
from ..core import alignment
from ..generators import comfyui_client

router = APIRouter()


@router.get("")
async def health() -> dict:
    comfy_alive = await comfyui_client.ping()
    backend = alignment._whisper_backend  # инициализируется лениво
    whisper_device = backend[0] if backend else settings.whisper_device
    whisper_compute = backend[1] if backend else settings.whisper_compute_type
    return {
        "ok": comfy_alive,
        "comfy_alive": comfy_alive,
        "comfyui_url": settings.comfyui_url,
        "openrouter_configured": bool(settings.openrouter_api_key.strip()),
        "whisper_device": whisper_device,
        "whisper_compute_type": whisper_compute,
        "whisper_loaded": backend is not None,
    }
