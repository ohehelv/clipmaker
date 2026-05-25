from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


class AnimateDiffGenerator(ComfyWorkflowGenerator):
    name = "animatediff"
    title = "AnimateDiff (SD 1.5)"
    description = "Лёгкая text-to-video модель на базе SD1.5."
    workflow_name = "animatediff"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        # ID нод в workflow указаны как строки в шаблоне (см. workflows/animatediff.json).
        # Замените под реальный экспорт workflow API из ComfyUI.
        frames = max(8, int(req.duration * req.fps))
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "LATENT": {"width": req.width, "height": req.height, "batch_size": frames},
            "SAMPLER": {"seed": self.random_seed()},
        }
