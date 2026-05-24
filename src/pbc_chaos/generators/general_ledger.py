"""Clean General Ledger generator."""

from __future__ import annotations

from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import ACCOUNT_MASTER, base_common, money, random_date
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class GeneralLedgerGenerator(BaseFinancialDocumentGenerator):
    """Generate balanced double-entry GL lines."""

    document_type = DocumentType.GENERAL_LEDGER

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        common = base_common(company, period)
        by_code = {account["code"]: account for account in ACCOUNT_MASTER}
        patterns = (
            ("Sales invoice", "1100", "4000", "AR"),
            ("Customer receipt", "1000", "1100", "AR"),
            ("Supplier invoice", "5000", "2000", "AP"),
            ("Supplier payment", "2000", "1000", "AP"),
            ("Payroll posting", "6000", "2200", "Payroll"),
            ("Depreciation charge", "6300", "1590", "Fixed Assets"),
            ("Bank charges", "6400", "1000", "Bank"),
        )
        rows = []
        entry_no = 1
        for _ in range(90):
            description, debit_code, credit_code, module = rng.choice(patterns)
            amount = money(rng, 200, 35_000)
            posting_date = random_date(rng, period)
            journal_id = f"JRN{entry_no:05d}"
            reference = f"{module[:2].upper()}-{period.financial_year}-{entry_no:05d}"
            for line_number, account_code, debit, credit in (
                (1, debit_code, amount, 0.0),
                (2, credit_code, 0.0, amount),
            ):
                account = by_code[account_code]
                rows.append(
                    {
                        **common,
                        "entry_id": f"GL{entry_no:06d}-{line_number}",
                        "journal_id": journal_id,
                        "line_number": line_number,
                        "posting_date": posting_date,
                        "document_date": posting_date,
                        "period": posting_date.strftime("%Y-%m"),
                        "account_code": account_code,
                        "account_name": account["name"],
                        "account_category": account["category"],
                        "debit": debit,
                        "credit": credit,
                        "amount_signed": debit - credit,
                        "counterparty_id": None,
                        "counterparty_name": None,
                        "counterparty_type": "other",
                        "source_module": module,
                        "document_number": reference,
                        "reference": reference,
                        "description": description,
                        "cost_center": rng.choice(["CC100", "CC200", "CC300", None]),
                        "department": rng.choice(["Finance", "Sales", "Operations", None]),
                        "project_code": rng.choice(["PRJ-A", "PRJ-B", None]),
                        "tax_code": rng.choice(["TX-0", "TX-6", None]),
                        "created_by": rng.choice(["finance.user", "ap.clerk", "system"]),
                        "posted_by": "finance.manager",
                        "batch_id": f"B{posting_date.month:02d}{entry_no // 10:03d}",
                        "reversal_flag": False,
                        "remarks": "",
                    }
                )
            entry_no += 1
        return pd.DataFrame(rows)

