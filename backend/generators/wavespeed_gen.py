"""WaveSpeed-генератор: один класс на все модели через model_id.

Ключ WaveSpeed читается из GenRequest.user_wavespeed_key (прокидывает runner).
"""

from __future__ import annotations

from pathlib import Path

from .base import GenRequest, VideoGenerator
from ..services import wavespeed
from ..services.wavespeed_models import WaveSpeedModel


class WaveSpeedGenerator(VideoGenerator):
    local = False  # облачная модель, доступна всем юзерам с ключом

    def __init__(self, meta: WaveSpeedModel) -> None:
        self.meta = meta
        self.name = meta.name
        self.title = meta.title
        self.description = meta.description

    async def is_available(self) -> bool:
        return True

    async def generate(self, req: GenRequest) -> Path:
        api_key = getattr(req, "user_wavespeed_key", "") or ""
        if not api_key:
            raise RuntimeError(
                "WaveSpeed API ключ не задан. Откройте Настройки и добавьте ключ."
            )

        # Клампим длительность под модель.
        duration = min(float(req.duration), float(self.meta.max_duration_sec))
        body: dict = {
            "prompt": req.prompt,
            "duration": duration,
            "aspect_ratio": _aspect_ratio(req.width, req.height),
            "size": f"{req.width}*{req.height}",
            "seed": -1,
        }

        task_id = await wavespeed.submit(self.meta.model_id, body, api_key)
        result = await wavespeed.poll_result(task_id, api_key, cancel_check=req.cancel_check)
        url = wavespeed.extract_first_video_url(result)
        if not url:
            raise RuntimeError(f"WaveSpeed: пустой ответ без URL видео: {str(result)[:300]}")

        await wavespeed.download(url, req.out_path)
        return req.out_path


def _aspect_ratio(w: int, h: int) -> str:
    # Самые частые: 16:9, 9:16, 1:1, 4:3, 3:4
    candidates = {
        (16, 9): "16:9",
        (9, 16): "9:16",
        (1, 1): "1:1",
        (4, 3): "4:3",
        (3, 4): "3:4",
        (21, 9): "21:9",
    }
    best = "16:9"
    best_err = 1e9
    target = w / max(1, h)
    for (a, b), label in candidates.items():
        err = abs(target - a / b)
        if err < best_err:
            best_err = err
            best = label
    return best
