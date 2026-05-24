"""Validation for generated cross-document reconciliation relationships."""

from __future__ import annotations

from dataclasses import dataclass

from pbc_chaos.core.types import DocumentType
from pbc_chaos.reconciliation.context import ReconciliationContext
from pbc_chaos.reconciliation.discrepancies import (
    ReconciliationDiscrepancy,
    classify_severity,
    signed_difference,
)


@dataclass(frozen=True)
class RelationshipCheck:
    """Result of comparing one reconciliation relationship."""

    relationship_name: str
    source_document: str
    target_document: str
    affected_field: str
    expected_value: float
    actual_value: float
    difference: float
    tolerance: float
    within_tolerance: bool
    intentional: bool
    severity: str
    discrepancy_ids: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.within_tolerance or self.intentional

    def as_metadata(self) -> dict[str, object]:
        return {
            "relationship_name": self.relationship_name,
            "source_document": self.source_document,
            "target_document": self.target_document,
            "affected_field": self.affected_field,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "difference": self.difference,
            "tolerance": self.tolerance,
            "within_tolerance": self.within_tolerance,
            "intentional": self.intentional,
            "severity": self.severity,
            "discrepancy_ids": self.discrepancy_ids,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class ReconciliationValidationReport:
    """Relationship validation report for one reconciliation context."""

    checks: tuple[RelationshipCheck, ...]
    discrepancies: tuple[ReconciliationDiscrepancy, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def as_metadata(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checks": [check.as_metadata() for check in self.checks],
            "discrepancies": [discrepancy.as_metadata() for discrepancy in self.discrepancies],
        }


class ReconciliationValidator:
    """Validate available document relationships in a reconciliation context."""

    def validate_relationships(self, context: ReconciliationContext) -> ReconciliationValidationReport:
        checks: list[RelationshipCheck] = []
        if _has(context, DocumentType.TRIAL_BALANCE, DocumentType.BANK_RECONCILIATION):
            checks.append(self._tb_cash_to_bank(context))
        if _has(context, DocumentType.GENERAL_LEDGER, DocumentType.TRIAL_BALANCE):
            checks.extend(self._gl_to_tb(context))
        if _has(context, DocumentType.AP_AGING, DocumentType.TRIAL_BALANCE):
            checks.append(self._ap_to_tb(context))
        if _has(context, DocumentType.AR_AGING, DocumentType.TRIAL_BALANCE):
            checks.append(self._ar_to_tb(context))
        if _has(context, DocumentType.PAYROLL_DETAIL, DocumentType.PAYROLL_SUMMARY):
            checks.append(self._payroll_detail_to_summary(context))
        if _has(context, DocumentType.FIXED_ASSET_REGISTER, DocumentType.TRIAL_BALANCE):
            checks.append(self._fixed_assets_to_tb(context))
        if _has(context, DocumentType.INVENTORY_LISTING, DocumentType.TRIAL_BALANCE):
            checks.append(self._inventory_to_tb(context))
        if _has(context, DocumentType.JOURNAL_ENTRY_LISTING, DocumentType.GENERAL_LEDGER):
            checks.append(self._journal_entries_to_gl(context))
        return ReconciliationValidationReport(
            checks=tuple(checks),
            discrepancies=tuple(context.discrepancies),
        )

    def _tb_cash_to_bank(self, context: ReconciliationContext) -> RelationshipCheck:
        bank = context.get_dataframe(DocumentType.BANK_RECONCILIATION)
        expected = context.account_balance("1000")
        actual = _first_float(bank.loc[bank["recon_item_type"] == "book_balance", "book_balance"])
        return _check(
            context,
            "trial_balance_cash_to_bank_reconciliation",
            DocumentType.TRIAL_BALANCE,
            DocumentType.BANK_RECONCILIATION,
            "book_balance",
            expected,
            actual,
        )

    def _gl_to_tb(self, context: ReconciliationContext) -> list[RelationshipCheck]:
        tb = context.get_dataframe(DocumentType.TRIAL_BALANCE)
        gl = context.get_dataframe(DocumentType.GENERAL_LEDGER)
        gl_totals = gl.groupby("account_code", dropna=False)["amount_signed"].sum()
        checks: list[RelationshipCheck] = []
        for row in tb.itertuples(index=False):
            expected = round(float(row.closing_balance), 2)
            actual = round(float(gl_totals.get(row.account_code, 0.0)), 2)
            if abs(signed_difference(expected, actual)) <= 0.01:
                continue
            checks.append(
                _check(
                    context,
                    "general_ledger_to_trial_balance",
                    DocumentType.GENERAL_LEDGER,
                    DocumentType.TRIAL_BALANCE,
                    f"account_code={row.account_code}.amount_signed",
                    expected,
                    actual,
                )
            )
        return checks

    def _ap_to_tb(self, context: ReconciliationContext) -> RelationshipCheck:
        ap = context.get_dataframe(DocumentType.AP_AGING)
        expected = abs(context.account_balance("2000"))
        actual = round(float(ap["outstanding_amount"].sum()), 2)
        return _check(
            context,
            "ap_aging_to_trial_balance",
            DocumentType.AP_AGING,
            DocumentType.TRIAL_BALANCE,
            "outstanding_amount",
            expected,
            actual,
        )

    def _ar_to_tb(self, context: ReconciliationContext) -> RelationshipCheck:
        ar = context.get_dataframe(DocumentType.AR_AGING)
        expected = context.account_balance("1100")
        actual = round(float(ar["outstanding_amount"].sum()), 2)
        return _check(
            context,
            "ar_aging_to_trial_balance",
            DocumentType.AR_AGING,
            DocumentType.TRIAL_BALANCE,
            "outstanding_amount",
            expected,
            actual,
        )

    def _payroll_detail_to_summary(self, context: ReconciliationContext) -> RelationshipCheck:
        summary = context.get_dataframe(DocumentType.PAYROLL_SUMMARY)
        detail = context.get_dataframe(DocumentType.PAYROLL_DETAIL)
        expected = round(float(summary["gross_pay"].sum()), 2)
        actual = round(float(detail["gross_pay"].sum()), 2)
        return _check(
            context,
            "payroll_detail_to_summary",
            DocumentType.PAYROLL_DETAIL,
            DocumentType.PAYROLL_SUMMARY,
            "gross_pay",
            expected,
            actual,
        )

    def _fixed_assets_to_tb(self, context: ReconciliationContext) -> RelationshipCheck:
        assets = context.get_dataframe(DocumentType.FIXED_ASSET_REGISTER)
        expected = context.account_balance("1500")
        actual = round(float(assets["cost"].sum()), 2)
        return _check(
            context,
            "fixed_asset_register_to_trial_balance",
            DocumentType.FIXED_ASSET_REGISTER,
            DocumentType.TRIAL_BALANCE,
            "cost",
            expected,
            actual,
        )

    def _inventory_to_tb(self, context: ReconciliationContext) -> RelationshipCheck:
        inventory = context.get_dataframe(DocumentType.INVENTORY_LISTING)
        expected = context.account_balance("1200")
        actual = round(float(inventory["total_cost"].sum()), 2)
        return _check(
            context,
            "inventory_listing_to_trial_balance",
            DocumentType.INVENTORY_LISTING,
            DocumentType.TRIAL_BALANCE,
            "total_cost",
            expected,
            actual,
        )

    def _journal_entries_to_gl(self, context: ReconciliationContext) -> RelationshipCheck:
        gl = context.get_dataframe(DocumentType.GENERAL_LEDGER)
        journals = context.get_dataframe(DocumentType.JOURNAL_ENTRY_LISTING)
        selected_ids = context.state.get("journal_entry_selected_ids") or tuple(
            sorted(journals["journal_id"].unique())
        )
        expected_rows = gl.loc[gl["journal_id"].isin(selected_ids)]
        merged = expected_rows.merge(
            journals[["journal_id", "line_number", "amount_signed"]],
            on=["journal_id", "line_number"],
            how="left",
            suffixes=("_gl", "_je"),
        )
        expected = round(float(expected_rows["amount_signed"].abs().sum()), 2)
        actual = round(float(merged["amount_signed_je"].fillna(0).abs().sum()), 2)
        return _check(
            context,
            "journal_entry_listing_to_general_ledger",
            DocumentType.JOURNAL_ENTRY_LISTING,
            DocumentType.GENERAL_LEDGER,
            "journal_id",
            expected,
            actual,
        )


def validate_relationships(context: ReconciliationContext) -> ReconciliationValidationReport:
    """Convenience wrapper for the default validator."""

    return validator.validate_relationships(context)


validator = ReconciliationValidator()


def _has(context: ReconciliationContext, *document_types: DocumentType) -> bool:
    return all(context.has_document(document_type) for document_type in document_types)


def _check(
    context: ReconciliationContext,
    relationship_name: str,
    source_document: DocumentType,
    target_document: DocumentType,
    affected_field: str,
    expected_value: float,
    actual_value: float,
) -> RelationshipCheck:
    expected = round(float(expected_value), 2)
    actual = round(float(actual_value), 2)
    difference = signed_difference(expected, actual)
    tolerance = round(float(context.relationship_tolerance(relationship_name, expected)), 2)
    within_tolerance = abs(difference) <= tolerance
    matches = tuple(
        discrepancy.discrepancy_id
        for discrepancy in context.discrepancies
        if discrepancy.relationship_name == relationship_name
        and discrepancy.source_document == source_document.value
        and discrepancy.target_document == target_document.value
        and discrepancy.affected_field == affected_field
    )
    return RelationshipCheck(
        relationship_name=relationship_name,
        source_document=source_document.value,
        target_document=target_document.value,
        affected_field=affected_field,
        expected_value=expected,
        actual_value=actual,
        difference=difference,
        tolerance=tolerance,
        within_tolerance=within_tolerance,
        intentional=bool(matches),
        severity=classify_severity(
            difference,
            context.materiality_threshold,
            rounding_tolerance=context.rounding_tolerance,
        ),
        discrepancy_ids=matches,
    )


def _first_float(values) -> float:
    if values.empty:
        return 0.0
    return round(float(values.iloc[0]), 2)

