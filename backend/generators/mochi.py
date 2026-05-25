from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


class MochiGenerator(ComfyWorkflowGenerator):
    name = "mochi"
    title = "Mochi-1"
    description = "Genmo Mochi-1, text-to-video, требует много VRAM."
    workflow_name = "mochi"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        frames = max(85, int(req.duration * req.fps))
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "LATENT": {"width": req.width, "height": req.height, "length": frames},
            "SAMPLER": {"seed": self.random_seed()},
        }
