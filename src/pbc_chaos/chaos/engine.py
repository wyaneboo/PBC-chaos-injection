"""Composable chaos injection engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from pbc_chaos.chaos.base import ChaosInjector, ChaosResult
from pbc_chaos.chaos.events import ChaosEvent
from pbc_chaos.core.context import ClientContext
from pbc_chaos.workbook.plan import WorkbookPlan


@dataclass
class ChaosEngine:
    injectors: list[ChaosInjector] = field(default_factory=list)

    def apply(self, plan: WorkbookPlan, context: ClientContext) -> ChaosResult:
        events: list[ChaosEvent] = []
        current = plan

        for injector in self.injectors:
            result = injector.apply(current, context)
            current = result.plan
            events.extend(result.events)

        return ChaosResult(plan=current, events=tuple(events))

