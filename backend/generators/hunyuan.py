from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


class HunyuanGenerator(ComfyWorkflowGenerator):
    name = "hunyuan"
    title = "HunyuanVideo"
    description = "Тяжёлая модель, на 5090 идёт в FP8/Q8 кванте."
    workflow_name = "hunyuan"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        frames = max(73, int(req.duration * req.fps))
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "LATENT": {"width": req.width, "height": req.height, "length": frames},
            "SAMPLER": {"seed": self.random_seed()},
        }
