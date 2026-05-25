"""Базовый класс для генераторов поверх ComfyUI workflow-шаблонов."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, ClassVar

from .base import GenRequest, VideoGenerator
from . import comfyui_client as comfy


class ComfyWorkflowGenerator(VideoGenerator):
    """Подкласс реализует:
    - workflow_name (имя файла в workflows/)
    - PROMPT_NODE, NEGATIVE_NODE, LATENT_NODE, SAMPLER_NODE, OUTPUT_NODE (id строки)
    - build_patches(req): возвращает dict для patch_workflow.
    """

    workflow_name: ClassVar[str] = ""
    output_node: ClassVar[str | None] = None
    negative_default: ClassVar[str] = "low quality, blurry, watermark, text, bad anatomy"

    def build_patches(self, req: GenRequest) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    async def is_available(self) -> bool:
        return await comfy.ping()

    async def generate(self, req: GenRequest) -> Path:
        wf = comfy.load_workflow(self.workflow_name)
        patches = self.build_patches(req)
        wf = comfy.patch_workflow(wf, patches)
        req.out_path.parent.mkdir(parents=True, exist_ok=True)
        await comfy.run_workflow(wf, req.out_path, output_key=self.output_node, cancel_check=req.cancel_check)
        return req.out_path

    @staticmethod
    def random_seed() -> int:
        return random.randint(1, 2**31 - 1)
