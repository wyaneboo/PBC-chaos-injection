from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.ap_aging import APAgingGenerator
from pbc_chaos.generators.ar_aging import ARAgingGenerator
from pbc_chaos.generators.bank_recon import BankReconciliationGenerator
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.generators.expense_claims import ExpenseClaimListingGenerator
from pbc_chaos.generators.fixed_assets import FixedAssetRegisterGenerator
from pbc_chaos.generators.general_ledger import GeneralLedgerGenerator
from pbc_chaos.generators.inventory import InventoryListingGenerator
from pbc_chaos.generators.journal_entries import JournalEntryListingGenerator
from pbc_chaos.generators.pbc_request_list import PBCRequestListGenerator
from pbc_chaos.generators.payroll import PayrollSummaryGenerator
from pbc_chaos.generators.trial_balance import TrialBalanceGenerator


def company_and_period():
    return (
        CompanyProfile(company_id="client_001", company_name="Example Sdn Bhd"),
        FinancialPeriod.calendar_year(2025),
    )


def test_all_phase5_generators_return_dataframe_and_metadata():
    company, period = company_and_period()
    generators = (
        PBCRequestListGenerator(),
        TrialBalanceGenerator(),
        GeneralLedgerGenerator(),
        APAgingGenerator(),
        ARAgingGenerator(),
        BankReconciliationGenerator(),
        FixedAssetRegisterGenerator(),
        PayrollSummaryGenerator(),
        InventoryListingGenerator(),
        JournalEntryListingGenerator(),
        ExpenseClaimListingGenerator(),
    )

    for index, generator in enumerate(generators):
        result = generator.generate(company, period, seed=100 + index)

        assert not result.data.empty
        assert result.metadata["document_type"] == generator.document_type.value
        assert result.metadata["company"]["company_id"] == company.company_id
        assert result.metadata["period"]["financial_year"] == period.financial_year
        assert result.metadata["row_count"] == len(result.data)
        assert "client_id" in result.metadata["expected_canonical_schema"]


def test_trial_balance_is_roughly_balanced():
    company, period = company_and_period()
    result = TrialBalanceGenerator().generate(company, period, seed=1)

    assert round(result.data["closing_balance"].sum(), 2) == 0.0
    assert {"asset", "liability", "equity", "revenue", "expense"}.issubset(
        set(result.data["account_category"])
    )


def test_general_ledger_and_journals_balance_by_journal():
    company, period = company_and_period()
    gl = GeneralLedgerGenerator().generate(company, period, seed=2).data
    journals = JournalEntryListingGenerator().generate(company, period, seed=3).data

    assert (gl.groupby("journal_id")["debit"].sum() - gl.groupby("journal_id")["credit"].sum()).abs().max() == 0
    assert (
        journals.groupby("journal_id")["debit"].sum()
        - journals.groupby("journal_id")["credit"].sum()
    ).abs().max() == 0


def test_requested_document_types_are_covered():
    generated_types = {
        PBCRequestListGenerator().document_type,
        TrialBalanceGenerator().document_type,
        GeneralLedgerGenerator().document_type,
        APAgingGenerator().document_type,
        ARAgingGenerator().document_type,
        BankReconciliationGenerator().document_type,
        FixedAssetRegisterGenerator().document_type,
        PayrollSummaryGenerator().document_type,
        InventoryListingGenerator().document_type,
        JournalEntryListingGenerator().document_type,
        ExpenseClaimListingGenerator().document_type,
    }

    assert generated_types == {
        DocumentType.TRIAL_BALANCE,
        DocumentType.PBC_REQUEST_LIST,
        DocumentType.GENERAL_LEDGER,
        DocumentType.AP_AGING,
        DocumentType.AR_AGING,
        DocumentType.BANK_RECONCILIATION,
        DocumentType.FIXED_ASSET_REGISTER,
        DocumentType.PAYROLL_SUMMARY,
        DocumentType.INVENTORY_LISTING,
        DocumentType.JOURNAL_ENTRY_LISTING,
        DocumentType.EXPENSE_CLAIM_LISTING,
    }
