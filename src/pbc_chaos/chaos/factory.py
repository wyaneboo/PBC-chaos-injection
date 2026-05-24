"""Factory helpers for chaos framework wiring."""

from __future__ import annotations

from pbc_chaos.chaos.default_registry import build_default_chaos_registry
from pbc_chaos.chaos.engine import ChaosEngine
from pbc_chaos.config.settings import ChaosSettings


def build_chaos_engine(settings: ChaosSettings, *, seed: int | None = None) -> ChaosEngine:
    registry = build_default_chaos_registry()
    return ChaosEngine(
        injectors=list(registry.all()),
        settings=settings,
        seed=seed,
    )

