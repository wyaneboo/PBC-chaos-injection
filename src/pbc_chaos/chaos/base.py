"""Chaos injector contracts and lifecycle primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pbc_chaos.chaos.context import ChaosContext
from pbc_chaos.chaos.events import ChaosEvent
from pbc_chaos.core.types import DocumentType
from pbc_chaos.workbook.plan import WorkbookPlan


@dataclass(frozen=True)
class InjectorExecution:
    name: str
    category: str
    order: int
    status: str
    enabled: bool
    supported: bool
    event_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class ChaosResult:
    plan: WorkbookPlan
    events: tuple[ChaosEvent, ...] = field(default_factory=tuple)
    executions: tuple[InjectorExecution, ...] = field(default_factory=tuple)
    applied: bool = True
    skipped_reason: str | None = None


class ChaosInjector(Protocol):
    """Mutate or replace a workbook plan and record what changed."""

    name: str
    category: str
    order: int
    probability_key: str | None
    default_probability: float
    supported_document_types: tuple[DocumentType, ...] | None

    def supports(self, document_type: DocumentType) -> bool:
        """Return whether this injector supports a document type."""
        ...

    def apply(self, plan: WorkbookPlan, context: ChaosContext) -> ChaosResult:
        """Apply chaos to a workbook plan."""
        ...


class BaseChaosInjector:
    """Base class for concrete chaos injectors."""

    name = "base"
    category = "unknown"
    order = 1000
    probability_key: str | None = None
    default_probability = 1.0
    supported_document_types: tuple[DocumentType, ...] | None = None

    def supports(self, document_type: DocumentType) -> bool:
        if self.supported_document_types is None:
            return True
        return document_type in self.supported_document_types

    def configured_probability(self, context: ChaosContext) -> float:
        key = self.probability_key or self.name
        return context.probability(key, self.default_probability)

    def should_apply(self, plan: WorkbookPlan, context: ChaosContext) -> bool:
        return context.chance(self.configured_probability(context))

    def apply(self, plan: WorkbookPlan, context: ChaosContext) -> ChaosResult:
        if not self.should_apply(plan, context):
            return ChaosResult(
                plan=plan,
                applied=False,
                skipped_reason="probability_gate",
            )
        return self.mutate(plan, context)

    def mutate(self, plan: WorkbookPlan, context: ChaosContext) -> ChaosResult:
        """Override in concrete injectors to mutate a workbook plan.

        The default implementation is intentionally a no-op so placeholder
        injectors can be registered before their actual mutation logic exists.
        """
        return ChaosResult(plan=plan)

    def event(
        self,
        context: ChaosContext,
        description: str,
        *,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        details: dict[str, object] | None = None,
        event_type: str = "mutation",
    ) -> ChaosEvent:
        return context.event(
            category=self.category,
            description=description,
            sheet_name=sheet_name,
            cell_range=cell_range,
            details=dict(details or {}),
            event_type=event_type,
        )
