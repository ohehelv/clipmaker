from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


class SVDGenerator(ComfyWorkflowGenerator):
    name = "svd"
    title = "Stable Video Diffusion (img2video)"
    description = "Требует входное изображение (см. workflow). Делает короткое видео из кадра."
    workflow_name = "svd"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        frames = max(14, min(25, int(req.duration * req.fps)))
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "SVD_LATENT": {"width": req.width, "height": req.height, "video_frames": frames},
            "SAMPLER": {"seed": self.random_seed()},
        }
