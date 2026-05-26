"""Реестр моделей WaveSpeed с метаданными.

Цены — справочные, для прикидки usage в UsageLog. Обновлять вручную.
Источник: https://wavespeed.ai/models
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WaveSpeedModel:
    name: str               # внутренний id (slug в нашем registry)
    title: str              # как показывать в UI
    model_id: str           # путь WaveSpeed: "wavespeed-ai/wan-2.2/t2v-a14b"
    kind: str               # "t2v" | "i2v"
    max_duration_sec: float = 5.0   # сколько секунд видео отдаёт за один вызов
    default_fps: int = 24
    price_per_sec_usd: float = 0.0  # ориентировочно, для UsageLog
    description: str = ""


CATALOG: list[WaveSpeedModel] = [
    WaveSpeedModel(
        name="ws-wan22-t2v-a14b",
        title="WaveSpeed · Wan 2.2 T2V-A14B (flagship)",
        model_id="wavespeed-ai/wan-2.2/t2v-a14b",
        kind="t2v",
        max_duration_sec=5.0,
        default_fps=24,
        price_per_sec_usd=0.20,
        description="Wan 2.2 14B текст→видео, высокое качество.",
    ),
    WaveSpeedModel(
        name="ws-wan22-ti2v-5b",
        title="WaveSpeed · Wan 2.2 TI2V-5B (fast)",
        model_id="wavespeed-ai/wan-2.2/ti2v-5b",
        kind="t2v",
        max_duration_sec=5.0,
        default_fps=24,
        price_per_sec_usd=0.05,
        description="Wan 2.2 5B — быстрее и дешевле, чуть слабее качество.",
    ),
    WaveSpeedModel(
        name="ws-wan22-i2v-a14b",
        title="WaveSpeed · Wan 2.2 I2V-A14B (image→video)",
        model_id="wavespeed-ai/wan-2.2/i2v-a14b",
        kind="i2v",
        max_duration_sec=5.0,
        default_fps=24,
        price_per_sec_usd=0.20,
        description="Wan 2.2 14B картинка→видео.",
    ),
    WaveSpeedModel(
        name="ws-hunyuan-video",
        title="WaveSpeed · Hunyuan Video",
        model_id="wavespeed-ai/hunyuan-video/t2v",
        kind="t2v",
        max_duration_sec=5.0,
        default_fps=24,
        price_per_sec_usd=0.18,
        description="Tencent Hunyuan Video — реалистичное движение.",
    ),
    WaveSpeedModel(
        name="ws-ltx-video",
        title="WaveSpeed · LTX-Video",
        model_id="wavespeed-ai/ltx-video",
        kind="t2v",
        max_duration_sec=5.0,
        default_fps=24,
        price_per_sec_usd=0.03,
        description="Lightricks LTX-Video — очень быстрый.",
    ),
]


def get(name: str) -> Optional[WaveSpeedModel]:
    for m in CATALOG:
        if m.name == name:
            return m
    return None
