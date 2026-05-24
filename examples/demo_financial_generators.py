"""Generate one messy PBC workbook containing all Phase 5 document types."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

from pbc_chaos.generators.ap_aging import APAgingGenerator
from pbc_chaos.generators.ar_aging import ARAgingGenerator
from pbc_chaos.generators.bank_recon import BankReconciliationGenerator
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.generators.expense_claims import ExpenseClaimListingGenerator
from pbc_chaos.generators.fixed_assets import FixedAssetRegisterGenerator
from pbc_chaos.generators.general_ledger import GeneralLedgerGenerator
from pbc_chaos.generators.inventory import InventoryListingGenerator
from pbc_chaos.generators.journal_entries import JournalEntryListingGenerator
from pbc_chaos.generators.payroll import PayrollSummaryGenerator
from pbc_chaos.generators.trial_balance import TrialBalanceGenerator
from pbc_chaos.workbook import layout_engine


SHEET_NAMES = {
    "trial_balance": "Trial Balance",
    "general_ledger": "General Ledger",
    "ap_aging": "AP Aging",
    "ar_aging": "AR Aging",
    "bank_reconciliation": "Bank Recon",
    "fixed_asset_register": "Fixed Assets",
    "payroll_summary": "Payroll",
    "inventory_listing": "Inventory",
    "journal_entry_listing": "Journal Entries",
    "expense_claim_listing": "Expense Claims",
}


def main() -> None:
    company = CompanyProfile(
        company_id="client_001",
        company_name="Contoso Manufacturing Sdn Bhd",
        currency="MYR",
        industry="manufacturing",
    )
    period = FinancialPeriod.calendar_year(2025)
    generators = (
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

    workbook = Workbook()
    workbook.remove(workbook.active)
    for index, generator in enumerate(generators, start=1):
        generated = generator.generate(company=company, period=period, seed=10_000 + index)
        worksheet = workbook.create_sheet(SHEET_NAMES[generated.document_type.value])
        for row in dataframe_to_rows(generated.data, index=False, header=True):
            worksheet.append(row)
        layout_engine.apply_layout_chaos(
            workbook=workbook,
            worksheet=worksheet,
            config={
                "client_name": company.company_name,
                "prepared_by": "Finance close team",
                "reviewer_name": "Audit Senior",
                "financial_year": period.financial_year,
                "title": f"{SHEET_NAMES[generated.document_type.value]} - PBC support",
                "old_version_tab_count": 1 if index <= 3 else 0,
                "add_hidden_reconciliation_tabs": index == 1,
            },
            seed=42 + index,
        )

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    workbook.save(output_dir / "demo_phase5_all_documents.xlsx")


if __name__ == "__main__":
    main()

