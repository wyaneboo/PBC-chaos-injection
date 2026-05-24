"""Document generator contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from random import Random
from typing import Any, Protocol

import pandas as pd

from pbc_chaos.core.context import ClientContext
from pbc_chaos.core.types import DocumentType
from pbc_chaos.financial_model.domain import CanonicalDataset
from pbc_chaos.schemas.registry import get_schema
from pbc_chaos.workbook.plan import WorkbookPlan


@dataclass(frozen=True)
class CompanyProfile:
    """Minimal company context accepted by Phase 5 clean-data generators."""

    company_id: str
    company_name: str
    currency: str = "MYR"
    industry: str = "manufacturing"


@dataclass(frozen=True)
class FinancialPeriod:
    """Financial reporting period used by generated documents."""

    financial_year: int
    start_date: date
    end_date: date

    @classmethod
    def calendar_year(cls, financial_year: int) -> "FinancialPeriod":
        """Build a Jan-Dec financial period."""

        return cls(
            financial_year=financial_year,
            start_date=date(financial_year, 1, 1),
            end_date=date(financial_year, 12, 31),
        )


@dataclass(frozen=True)
class GeneratedDocument:
    """Clean tabular output and metadata for one financial document."""

    document_type: DocumentType
    data: pd.DataFrame
    metadata: dict[str, Any]


class FinancialDocumentGenerator(Protocol):
    """Build a clean pandas DataFrame for a document type."""

    document_type: DocumentType

    def generate(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        seed: int | None = None,
    ) -> GeneratedDocument:
        """Generate clean data and metadata."""
        ...


class BaseFinancialDocumentGenerator:
    """Base class for Phase 5 clean financial document generators."""

    document_type: DocumentType

    def generate(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        seed: int | None = None,
    ) -> GeneratedDocument:
        rng = Random(seed)
        data = self.build_dataframe(company, period, rng)
        return GeneratedDocument(
            document_type=self.document_type,
            data=data,
            metadata=self.build_metadata(company, period, data),
        )

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        """Build a clean document DataFrame."""

        raise NotImplementedError(f"{self.__class__.__name__} has no implementation.")

    def build_metadata(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        data: pd.DataFrame,
    ) -> dict[str, Any]:
        """Build standard metadata describing the generated document."""

        schema = get_schema(self.document_type)
        return {
            "document_type": self.document_type.value,
            "period": {
                "financial_year": period.financial_year,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
            },
            "company": {
                "company_id": company.company_id,
                "company_name": company.company_name,
                "currency": company.currency,
                "industry": company.industry,
            },
            "row_count": len(data),
            "expected_canonical_schema": schema.field_names(),
        }


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
