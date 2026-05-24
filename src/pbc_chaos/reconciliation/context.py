"""Shared context for generating related reconciliation documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from random import Random
from typing import Any

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod, GeneratedDocument
from pbc_chaos.reconciliation.discrepancies import (
    DiscrepancyReason,
    ReconciliationDiscrepancy,
    as_reason,
    classify_severity,
    signed_difference,
)
from pbc_chaos.schemas.registry import get_schema


@dataclass
class ReconciliationContext:
    """State shared by document generators in one client-period reconciliation set."""

    company: CompanyProfile
    period: FinancialPeriod
    seed: int | None = None
    materiality_threshold: float = 1_000.0
    discrepancy_mode: str = "controlled"
    rounding_tolerance: float = 1.0
    max_trial_balance_gl_difference_pct: float = 0.02
    max_bank_recon_difference_amount: float = 500.0
    max_payroll_summary_difference_pct: float = 0.015
    max_inventory_summary_difference_pct: float = 0.03
    documents: dict[DocumentType, GeneratedDocument] = field(default_factory=dict, init=False)
    discrepancies: list[ReconciliationDiscrepancy] = field(default_factory=list, init=False)
    state: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.seed = 0 if self.seed is None else int(self.seed)

    def rng(self, namespace: str) -> Random:
        """Return deterministic randomness scoped to a context namespace."""

        payload = (
            f"{self.seed}:{self.company.company_id}:"
            f"{self.period.financial_year}:{namespace}"
        ).encode("utf-8")
        digest = sha256(payload).digest()
        return Random(int.from_bytes(digest[:8], "big"))

    def make_document(
        self,
        document_type: DocumentType,
        data: pd.DataFrame,
    ) -> GeneratedDocument:
        """Build a generated document using standard metadata plus reconciliation state."""

        schema = get_schema(document_type)
        document = GeneratedDocument(
            document_type=document_type,
            data=data,
            metadata={
                "document_type": document_type.value,
                "period": {
                    "financial_year": self.period.financial_year,
                    "start_date": self.period.start_date.isoformat(),
                    "end_date": self.period.end_date.isoformat(),
                },
                "company": {
                    "company_id": self.company.company_id,
                    "company_name": self.company.company_name,
                    "currency": self.company.currency,
                    "industry": self.company.industry,
                },
                "row_count": len(data),
                "expected_canonical_schema": schema.field_names(),
            },
        )
        return self.register_document(document)

    def register_document(self, document: GeneratedDocument) -> GeneratedDocument:
        """Store a generated document and attach relevant reconciliation metadata."""

        self.documents[document.document_type] = document
        self._refresh_document_metadata(document.document_type)
        return document

    def get_document(self, document_type: DocumentType) -> GeneratedDocument:
        try:
            return self.documents[document_type]
        except KeyError as exc:
            raise KeyError(f"{document_type.value} has not been generated in this context.") from exc

    def get_dataframe(self, document_type: DocumentType) -> pd.DataFrame:
        return self.get_document(document_type).data

    def has_document(self, document_type: DocumentType) -> bool:
        return document_type in self.documents

    @property
    def discrepancy_metadata(self) -> list[dict[str, Any]]:
        """Return all discrepancy records in sidecar-ready form."""

        return [discrepancy.as_metadata() for discrepancy in self.discrepancies]

    def log_discrepancy(
        self,
        *,
        source_document: DocumentType | str,
        target_document: DocumentType | str,
        affected_field: str,
        expected_value: float,
        actual_value: float,
        reason: DiscrepancyReason | str,
        relationship_name: str | None = None,
        intentional: bool = True,
        severity: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> ReconciliationDiscrepancy:
        """Append discrepancy metadata and update already generated document sidecars."""

        source = source_document.value if isinstance(source_document, DocumentType) else source_document
        target = target_document.value if isinstance(target_document, DocumentType) else target_document
        difference = signed_difference(expected_value, actual_value)
        record = ReconciliationDiscrepancy(
            discrepancy_id=f"DISC-{len(self.discrepancies) + 1:05d}",
            source_document=source,
            target_document=target,
            affected_field=affected_field,
            expected_value=round(float(expected_value), 2),
            actual_value=round(float(actual_value), 2),
            difference=difference,
            reason=as_reason(reason),
            severity=severity
            or classify_severity(
                difference,
                self.materiality_threshold,
                rounding_tolerance=self.rounding_tolerance,
            ),
            intentional=bool(intentional),
            relationship_name=relationship_name,
            materiality_threshold=float(self.materiality_threshold),
            details=details or {},
        )
        self.discrepancies.append(record)
        self._refresh_all_document_metadata()
        return record

    def account_balance(self, account_code: str) -> float:
        """Return a TB closing balance for an account code."""

        trial_balance = self.get_dataframe(DocumentType.TRIAL_BALANCE)
        matches = trial_balance.loc[trial_balance["account_code"] == account_code, "closing_balance"]
        if matches.empty:
            raise KeyError(f"Account {account_code} is not present in the trial balance.")
        return round(float(matches.iloc[0]), 2)

    def relationship_tolerance(self, relationship_name: str, expected_value: float) -> float:
        """Return the configured tolerance for a named relationship."""

        baseline = abs(float(expected_value))
        if relationship_name == "trial_balance_cash_to_bank_reconciliation":
            return min(self.materiality_threshold, self.max_bank_recon_difference_amount)
        if relationship_name == "general_ledger_to_trial_balance":
            return min(self.materiality_threshold, baseline * self.max_trial_balance_gl_difference_pct)
        if relationship_name == "payroll_detail_to_summary":
            return min(self.materiality_threshold, baseline * self.max_payroll_summary_difference_pct)
        if relationship_name == "inventory_listing_to_trial_balance":
            return min(self.materiality_threshold, baseline * self.max_inventory_summary_difference_pct)
        return self.materiality_threshold

    def controlled_difference(
        self,
        namespace: str,
        expected_value: float,
        *,
        cap: float | None = None,
        minimum: float = 25.0,
    ) -> float:
        """Return a deterministic non-zero difference below the relevant cap."""

        rng = self.rng(f"discrepancy:{namespace}")
        max_amount = self.materiality_threshold * 0.85 if cap is None else cap
        max_amount = max(0.01, min(abs(max_amount), self.materiality_threshold * 0.95))
        scaled = abs(float(expected_value)) * rng.uniform(0.0005, 0.004)
        amount = max(minimum, scaled)
        amount = min(amount, max_amount)
        if amount <= 1:
            amount = max(0.01, amount)
        sign = -1 if rng.random() < 0.5 else 1
        return round(sign * amount, 2)

    def _refresh_all_document_metadata(self) -> None:
        for document_type in tuple(self.documents):
            self._refresh_document_metadata(document_type)

    def _refresh_document_metadata(self, document_type: DocumentType) -> None:
        document = self.documents[document_type]
        document_value = document_type.value
        relevant = [
            discrepancy.as_metadata()
            for discrepancy in self.discrepancies
            if discrepancy.source_document == document_value
            or discrepancy.target_document == document_value
        ]
        document.metadata["reconciliation"] = {
            "context_seed": self.seed,
            "discrepancy_mode": self.discrepancy_mode,
            "materiality_threshold": self.materiality_threshold,
            "rounding_tolerance": self.rounding_tolerance,
            "discrepancy_count": len(relevant),
            "discrepancies": relevant,
        }
