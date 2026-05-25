from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


class CogVideoXGenerator(ComfyWorkflowGenerator):
    name = "cogvideox"
    title = "CogVideoX (2B/5B)"
    description = "Text-to-video, хорошее качество, длинные клипы из коробки."
    workflow_name = "cogvideox"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        frames = max(49, int(req.duration * req.fps))
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "EMPTY_LATENT": {"width": req.width, "height": req.height, "num_frames": frames},
            "SAMPLER": {"seed": self.random_seed()},
        }
