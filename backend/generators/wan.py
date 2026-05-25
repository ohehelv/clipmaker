"""Wan 2.2 14B T2V (dual-model: high_noise + low_noise) поверх ComfyUI native nodes."""

from __future__ import annotations

from typing import Any

from ._comfy_base import ComfyWorkflowGenerator
from .base import GenRequest


def _wan_length(duration: float, fps: int) -> int:
    """Wan требует длину латента вида 4k+1. Минимум 17 кадров (~1с при 16fps)."""
    raw = max(17, int(round(duration * fps)))
    # округлить вверх до ближайшего 4k+1
    k = (raw - 1 + 3) // 4
    return 4 * k + 1


class WanGenerator(ComfyWorkflowGenerator):
    name = "wan"
    title = "Wan 2.2 14B"
    description = "Wan 2.2 14B fp8 T2V (high+low noise) — лучший open-source видеогенератор."
    workflow_name = "wan"
    output_node = "VIDEO_OUT"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        length = _wan_length(req.duration, req.fps)
        seed = self.random_seed()
        return {
            "POSITIVE": {"text": req.prompt},
            "NEGATIVE": {"text": self.negative_default},
            "LATENT": {"width": req.width, "height": req.height, "length": length, "batch_size": 1},
            "SAMPLER_HIGH": {"noise_seed": seed},
            "SAMPLER_LOW": {"noise_seed": seed},
            "VIDEO_OUT": {"frame_rate": req.fps},
        }
