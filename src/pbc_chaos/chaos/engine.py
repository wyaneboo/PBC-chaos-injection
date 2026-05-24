"""Composable chaos injection engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from pbc_chaos.chaos.base import ChaosInjector, ChaosResult, InjectorExecution
from pbc_chaos.chaos.context import ChaosContext
from pbc_chaos.chaos.events import ChaosEvent
from pbc_chaos.config.settings import ChaosSettings
from pbc_chaos.core.context import ClientContext
from pbc_chaos.workbook.plan import WorkbookPlan


@dataclass
class ChaosEngine:
    injectors: list[ChaosInjector] = field(default_factory=list)
    settings: ChaosSettings | None = None
    seed: int | None = None
    fail_fast: bool = True

    def apply(self, plan: WorkbookPlan, context: ClientContext) -> ChaosResult:
        events: list[ChaosEvent] = []
        executions: list[InjectorExecution] = []
        current = plan
        settings = self.settings or context.run.settings.chaos
        root_seed = self.seed if self.seed is not None else context.seed
        root_context = ChaosContext.for_plan(
            client=context,
            settings=settings,
            plan=plan,
            root_seed=root_seed,
        )

        for injector in sorted(self.injectors, key=lambda item: item.order):
            injector_context = root_context.for_injector(injector.name)
            enabled = injector_context.injector_enabled(injector.name)
            supported = injector.supports(current.document_type)

            if not enabled:
                executions.append(
                    InjectorExecution(
                        name=injector.name,
                        category=injector.category,
                        order=injector.order,
                        status="skipped_disabled",
                        enabled=False,
                        supported=supported,
                    )
                )
                continue

            if not supported:
                executions.append(
                    InjectorExecution(
                        name=injector.name,
                        category=injector.category,
                        order=injector.order,
                        status="skipped_unsupported",
                        enabled=True,
                        supported=False,
                    )
                )
                continue

            try:
                result = injector.apply(current, injector_context)
            except Exception as exc:
                executions.append(
                    InjectorExecution(
                        name=injector.name,
                        category=injector.category,
                        order=injector.order,
                        status="error",
                        enabled=True,
                        supported=True,
                        error=str(exc),
                    )
                )
                if self.fail_fast:
                    raise
                continue

            current = result.plan
            events.extend(result.events)
            executions.append(
                InjectorExecution(
                    name=injector.name,
                    category=injector.category,
                    order=injector.order,
                    status=result.skipped_reason or "completed",
                    enabled=True,
                    supported=True,
                    event_count=len(result.events),
                )
            )

        return ChaosResult(
            plan=current,
            events=tuple(events),
            executions=tuple(executions),
        )

    def register(self, injector: ChaosInjector) -> None:
        self.injectors.append(injector)
