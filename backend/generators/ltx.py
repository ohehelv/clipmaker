from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


class LTXGenerator(ComfyWorkflowGenerator):
    name = "ltx"
    title = "LTX-Video (быстрый)"
    description = "Lightricks LTX-Video. Очень быстрая генерация."
    workflow_name = "ltx"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        frames = max(97, int(req.duration * req.fps))
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "LATENT": {"width": req.width, "height": req.height, "length": frames},
            "SAMPLER": {"seed": self.random_seed()},
        }
