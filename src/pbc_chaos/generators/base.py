"""Document generator contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pbc_chaos.core.context import ClientContext
from pbc_chaos.core.types import DocumentType
from pbc_chaos.financial_model.domain import CanonicalDataset
from pbc_chaos.workbook.plan import WorkbookPlan


@dataclass(frozen=True)
class GeneratorResult:
    document_type: DocumentType
    workbook: WorkbookPlan
    relationship_expectations: dict[str, object] = field(default_factory=dict)


class DocumentGenerator(Protocol):
    """Build a clean workbook plan from canonical financial data."""

    document_type: DocumentType

    def generate(self, dataset: CanonicalDataset, context: ClientContext) -> GeneratorResult:
        """Generate a clean workbook plan."""
        ...


class BaseDocumentGenerator:
    """Base class for document generators."""

    document_type: DocumentType

    def generate(self, dataset: CanonicalDataset, context: ClientContext) -> GeneratorResult:
        raise NotImplementedError(f"{self.__class__.__name__} has no implementation.")

