from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.generators.payroll import PayrollDetailGenerator
from pbc_chaos.reconciliation import (
    ReconciliationContext,
    generate_ap_aging,
    generate_ar_aging,
    generate_bank_reconciliation,
    generate_fixed_asset_register,
    generate_general_ledger,
    generate_inventory_listing,
    generate_journal_entry_listing,
    generate_payroll_detail,
    generate_payroll_summary,
    generate_trial_balance,
    validator,
)


def company_and_period():
    return (
        CompanyProfile(company_id="client_001", company_name="Example Sdn Bhd"),
        FinancialPeriod.calendar_year(2025),
    )


def generate_relationship_set(seed=42):
    company, period = company_and_period()
    context = ReconciliationContext(company, period, seed=seed)
    for generate in (
        generate_trial_balance,
        generate_general_ledger,
        generate_bank_reconciliation,
        generate_ap_aging,
        generate_ar_aging,
        generate_payroll_summary,
        generate_payroll_detail,
        generate_fixed_asset_register,
        generate_inventory_listing,
        generate_journal_entry_listing,
    ):
        generate(context)
    return context


def test_phase6_context_api_generates_controlled_discrepancy_metadata():
    context = generate_relationship_set()

    reasons = {discrepancy.reason for discrepancy in context.discrepancies}
    assert reasons.issuperset(
        {
            "rounding_difference",
            "timing_difference",
            "missing_transaction",
            "duplicated_transaction",
            "wrong_period_transaction",
        }
    )

    for discrepancy in context.discrepancies:
        metadata = discrepancy.as_metadata()
        assert {
            "discrepancy_id",
            "source_document",
            "target_document",
            "affected_field",
            "expected_value",
            "actual_value",
            "difference",
            "reason",
            "severity",
            "intentional",
        }.issubset(metadata)
        assert metadata["intentional"] is True

    trial_balance_metadata = context.get_document(DocumentType.TRIAL_BALANCE).metadata
    assert trial_balance_metadata["reconciliation"]["discrepancy_count"] > 0


def test_phase6_validator_accepts_intentional_near_reconciliations():
    context = generate_relationship_set()
    report = validator.validate_relationships(context)

    assert report.passed
    assert len(report.checks) >= 8
    assert any(check.difference != 0 for check in report.checks)
    assert all(check.within_tolerance or check.intentional for check in report.checks)

    bank_check = next(
        check
        for check in report.checks
        if check.relationship_name == "trial_balance_cash_to_bank_reconciliation"
    )
    assert 0 < abs(bank_check.difference) <= context.max_bank_recon_difference_amount

    ar_check = next(check for check in report.checks if check.relationship_name == "ar_aging_to_trial_balance")
    assert 0 < abs(ar_check.difference) <= context.rounding_tolerance


def test_context_general_ledger_stays_balanced_by_journal_after_injection():
    context = generate_relationship_set()
    gl = context.get_dataframe(DocumentType.GENERAL_LEDGER)
    by_journal = gl.groupby("journal_id")["debit"].sum() - gl.groupby("journal_id")["credit"].sum()

    assert by_journal.abs().max() == 0


def test_payroll_detail_class_generator_is_available():
    company, period = company_and_period()
    result = PayrollDetailGenerator().generate(company, period, seed=100)

    assert result.document_type == DocumentType.PAYROLL_DETAIL
    assert not result.data.empty
    assert {"employee_id", "gross_pay", "net_pay"}.issubset(result.data.columns)
    assert result.metadata["expected_canonical_schema"]
