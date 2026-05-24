"""Execution context passed to chaos injectors."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Any, TypeVar

from pbc_chaos.chaos.events import ChaosEvent
from pbc_chaos.chaos.randomness import clamp_probability, seeded_random, stable_seed
from pbc_chaos.config.settings import ChaosSettings
from pbc_chaos.core.context import ClientContext
from pbc_chaos.core.types import DocumentType
from pbc_chaos.workbook.plan import WorkbookPlan

T = TypeVar("T")


@dataclass(frozen=True)
class ChaosContext:
    """Context for one workbook chaos run or one injector execution."""

    client: ClientContext
    settings: ChaosSettings
    document_type: DocumentType
    workbook_name: str
    root_seed: int
    rng: random.Random
    injector_name: str | None = None

    @classmethod
    def for_plan(
        cls,
        *,
        client: ClientContext,
        settings: ChaosSettings,
        plan: WorkbookPlan,
        root_seed: int,
    ) -> "ChaosContext":
        rng = seeded_random(
            "chaos",
            root_seed,
            client.client_id,
            client.financial_year,
            plan.document_type.value,
            plan.suggested_filename,
        )
        return cls(
            client=client,
            settings=settings,
            document_type=plan.document_type,
            workbook_name=plan.suggested_filename,
            root_seed=root_seed,
            rng=rng,
        )

    def for_injector(self, injector_name: str) -> "ChaosContext":
        seed = stable_seed(
            "chaos-injector",
            self.root_seed,
            self.client.client_id,
            self.client.financial_year,
            self.document_type.value,
            self.workbook_name,
            injector_name,
        )
        return replace(self, injector_name=injector_name, rng=random.Random(seed))

    def injector_enabled(self, injector_name: str) -> bool:
        """Return whether an injector is enabled by config."""
        return bool(self.settings.injectors.get(injector_name, True))

    def probability(self, key: str | None, default: float = 1.0) -> float:
        """Return a configured probability or default."""
        if key is None:
            return clamp_probability(default)
        return clamp_probability(self.settings.probabilities.get(key, default))

    def chance(self, probability: float) -> bool:
        """Return true when the deterministic RNG passes the probability gate."""
        return self.rng.random() < clamp_probability(probability)

    def randint(self, start: int, stop: int) -> int:
        return self.rng.randint(start, stop)

    def uniform(self, start: float, stop: float) -> float:
        return self.rng.uniform(start, stop)

    def choice(self, values: tuple[T, ...]) -> T:
        if not values:
            raise ValueError("choice requires at least one value.")
        return self.rng.choice(values)

    def event(
        self,
        *,
        category: str,
        description: str,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        details: dict[str, Any] | None = None,
        event_type: str = "mutation",
    ) -> ChaosEvent:
        """Create a metadata event with standard workbook/client context."""
        return ChaosEvent(
            injector=self.injector_name or "unknown",
            category=category,
            description=description,
            sheet_name=sheet_name,
            cell_range=cell_range,
            severity=self.settings.severity.value,
            event_type=event_type,
            document_type=self.document_type.value,
            client_id=self.client.client_id,
            financial_year=self.client.financial_year,
            details=details or {},
        )

