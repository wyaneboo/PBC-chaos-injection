"""Chaos injector contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pbc_chaos.chaos.events import ChaosEvent
from pbc_chaos.core.context import ClientContext
from pbc_chaos.workbook.plan import WorkbookPlan


@dataclass(frozen=True)
class ChaosResult:
    plan: WorkbookPlan
    events: tuple[ChaosEvent, ...] = field(default_factory=tuple)


class ChaosInjector(Protocol):
    """Mutate or replace a workbook plan and record what changed."""

    name: str
    category: str

    def apply(self, plan: WorkbookPlan, context: ClientContext) -> ChaosResult:
        """Apply chaos to a workbook plan."""
        ...


class BaseChaosInjector:
    """Base class for concrete chaos injectors."""

    name = "base"
    category = "unknown"

    def apply(self, plan: WorkbookPlan, context: ClientContext) -> ChaosResult:
        raise NotImplementedError(f"{self.__class__.__name__} has no implementation.")

