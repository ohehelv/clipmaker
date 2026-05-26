from __future__ import annotations

from typing import Dict, List

from ..schemas import GeneratorInfo
from .base import VideoGenerator


_REGISTRY: Dict[str, VideoGenerator] = {}


def register(gen: VideoGenerator) -> None:
    _REGISTRY[gen.name] = gen


def get(name: str) -> VideoGenerator:
    if name not in _REGISTRY:
        raise KeyError(f"Generator '{name}' не зарегистрирован. Доступно: {list(_REGISTRY)}")
    return _REGISTRY[name]


def list_generators(include_local: bool = False) -> List[GeneratorInfo]:
    out: list[GeneratorInfo] = []
    for g in _REGISTRY.values():
        if getattr(g, "local", False) and not include_local:
            continue
        out.append(
            GeneratorInfo(name=g.name, title=g.title, description=g.description, available=True)
        )
    return out


def _bootstrap() -> None:
    # отложенные импорты, чтобы избежать циклов
    from .stub import StubGenerator
    from .animatediff import AnimateDiffGenerator
    from .svd import SVDGenerator
    from .cogvideox import CogVideoXGenerator
    from .hunyuan import HunyuanGenerator
    from .wan import WanGenerator
    from .wan5b import Wan5BGenerator
    from .mochi import MochiGenerator
    from .ltx import LTXGenerator
    from .wavespeed_gen import WaveSpeedGenerator
    from ..services.wavespeed_models import CATALOG as WS_CATALOG

    for g in [
        StubGenerator(),
        AnimateDiffGenerator(),
        SVDGenerator(),
        CogVideoXGenerator(),
        HunyuanGenerator(),
        WanGenerator(),
        Wan5BGenerator(),
        MochiGenerator(),
        LTXGenerator(),
    ]:
        register(g)

    for meta in WS_CATALOG:
        register(WaveSpeedGenerator(meta))


_bootstrap()
