from __future__ import annotations

from fastapi import APIRouter

from ..config import settings
from ..generators import comfyui_client

router = APIRouter()


@router.get("")
async def health() -> dict:
    comfy_alive = await comfyui_client.ping()
    return {
        "ok": comfy_alive,
        "comfy_alive": comfy_alive,
        "comfyui_url": settings.comfyui_url,
        "openrouter_configured": bool(settings.openrouter_api_key.strip()),
    }
