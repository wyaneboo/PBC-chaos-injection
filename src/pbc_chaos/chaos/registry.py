"""Registry for chaos injectors."""

from __future__ import annotations

from dataclasses import dataclass, field

from pbc_chaos.chaos.base import ChaosInjector


@dataclass
class ChaosInjectorRegistry:
    injectors: dict[str, ChaosInjector] = field(default_factory=dict)

    def register(self, injector: ChaosInjector) -> None:
        if injector.name in self.injectors:
            raise ValueError(f"Chaos injector already registered: {injector.name}")
        self.injectors[injector.name] = injector

    def get(self, name: str) -> ChaosInjector:
        try:
            return self.injectors[name]
        except KeyError as exc:
            raise KeyError(f"No chaos injector registered for {name}") from exc

    def all(self) -> tuple[ChaosInjector, ...]:
        return tuple(sorted(self.injectors.values(), key=lambda injector: injector.order))

    def names(self) -> tuple[str, ...]:
        return tuple(injector.name for injector in self.all())

