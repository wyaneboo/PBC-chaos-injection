"""Clean Journal Entry Listing generator."""

from __future__ import annotations

from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import ACCOUNT_MASTER, base_common, money, random_date
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class JournalEntryListingGenerator(BaseFinancialDocumentGenerator):
    """Generate balanced manual and recurring journal entries."""

    document_type = DocumentType.JOURNAL_ENTRY_LISTING

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        common = base_common(company, period)
        by_code = {account["code"]: account for account in ACCOUNT_MASTER}
        patterns = (
            ("Accrual", "6100", "2100", True),
            ("Depreciation", "6300", "1590", False),
            ("Inventory adjustment", "5000", "1200", True),
            ("Payroll accrual", "6000", "2200", True),
            ("Prepayment release", "6100", "1300", False),
        )
        rows = []
        for journal_no in range(1, 41):
            journal_type, debit_code, credit_code, manual = rng.choice(patterns)
            posting_date = random_date(rng, period)
            amount = money(rng, 500, 85_000)
            journal_id = f"JE{period.financial_year}{journal_no:05d}"
            for line_number, code, debit, credit in (
                (1, debit_code, amount, 0.0),
                (2, credit_code, 0.0, amount),
            ):
                account = by_code[code]
                rows.append(
                    {
                        **common,
                        "journal_id": journal_id,
                        "line_number": line_number,
                        "posting_date": posting_date,
                        "journal_date": posting_date,
                        "journal_type": journal_type,
                        "account_code": code,
                        "account_name": account["name"],
                        "debit": debit,
                        "credit": credit,
                        "amount_signed": debit - credit,
                        "description": f"{journal_type} for {posting_date:%b %Y}",
                        "reference": f"SUPP-{rng.randint(1000, 9999)}",
                        "prepared_by": rng.choice(["Aisha", "Daniel", "Finance Ops"]),
                        "approved_by": rng.choice(["Controller", "Finance Manager"]),
                        "approval_date": posting_date,
                        "manual_entry_flag": manual,
                        "recurring_flag": journal_type in {"Depreciation", "Prepayment release"},
                        "adjustment_flag": journal_type != "Depreciation",
                        "source_module": "Manual Journal",
                        "cost_center": rng.choice(["CC100", "CC200", "CC300"]),
                        "department": rng.choice(["Finance", "Operations", "Admin"]),
                        "remarks": "",
                    }
                )
        return pd.DataFrame(rows)

