"""Wan 2.2 TI2V-5B (одна модель) — компактнее и быстрее 14B dual."""

from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


def _wan_length(duration: float, fps: int) -> int:
    """Wan требует длину латента вида 4k+1. Минимум 17 кадров."""
    raw = max(17, int(round(duration * fps)))
    k = (raw - 1 + 3) // 4
    return 4 * k + 1


class Wan5BGenerator(ComfyWorkflowGenerator):
    name = "wan5b"
    title = "Wan 2.2 TI2V-5B"
    description = "Wan 2.2 5B (single-model) — влезает в 32 ГБ VRAM, быстрее 14B."
    workflow_name = "wan5b"
    output_node = "VIDEO_OUT"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        length = _wan_length(req.duration, req.fps)
        seed = self.random_seed()
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "LATENT": {
                "width": req.width,
                "height": req.height,
                "length": length,
                "batch_size": 1,
            },
            "SAMPLER": {"seed": seed},
            "VIDEO_OUT": {"frame_rate": req.fps},
        }
