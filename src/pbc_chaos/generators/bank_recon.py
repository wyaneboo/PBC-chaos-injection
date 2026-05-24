"""Clean Bank Reconciliation generator."""

from __future__ import annotations

from datetime import timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import base_common, money
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class BankReconciliationGenerator(BaseFinancialDocumentGenerator):
    """Generate a bank reconciliation summary and reconciling items."""

    document_type = DocumentType.BANK_RECONCILIATION

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        common = base_common(company, period)
        book_balance = money(rng, 120_000, 800_000)
        deposits = [money(rng, 5_000, 55_000) for _ in range(4)]
        cheques = [money(rng, 2_000, 40_000) for _ in range(6)]
        bank_charges = money(rng, 100, 1_500)
        interest = money(rng, 50, 800)
        statement_balance = round(book_balance - sum(deposits) + sum(cheques) + bank_charges - interest, 2)
        account = {
            "bank_account_id": "BANK001",
            "bank_name": "Maybank",
            "bank_account_number": "****-****-3488",
        }
        rows = [
            {
                **common,
                **account,
                "recon_item_id": "BR-BOOK",
                "recon_item_type": "book_balance",
                "transaction_date": period.end_date,
                "reference": "GL-CASH",
                "description": "Balance per cash book",
                "bank_amount": None,
                "book_amount": book_balance,
                "difference_amount": 0.0,
                "statement_balance": None,
                "book_balance": book_balance,
                "adjusted_bank_balance": None,
                "adjusted_book_balance": book_balance,
                "variance": 0.0,
                "cleared_flag": True,
                "matched_gl_entry_id": None,
                "matched_bank_reference": None,
                "remarks": "",
            },
            {
                **common,
                **account,
                "recon_item_id": "BR-STMT",
                "recon_item_type": "statement_balance",
                "transaction_date": period.end_date,
                "reference": "BANK-STMT",
                "description": "Balance per bank statement",
                "bank_amount": statement_balance,
                "book_amount": None,
                "difference_amount": 0.0,
                "statement_balance": statement_balance,
                "book_balance": None,
                "adjusted_bank_balance": statement_balance,
                "adjusted_book_balance": None,
                "variance": 0.0,
                "cleared_flag": True,
                "matched_gl_entry_id": None,
                "matched_bank_reference": None,
                "remarks": "",
            },
        ]
        item_no = 1
        for amount in deposits:
            rows.append(_recon_item(common, account, period, rng, item_no, "deposit_in_transit", amount))
            item_no += 1
        for amount in cheques:
            rows.append(_recon_item(common, account, period, rng, item_no, "outstanding_cheque", -amount))
            item_no += 1
        rows.append(_recon_item(common, account, period, rng, item_no, "bank_charge", -bank_charges))
        rows.append(_recon_item(common, account, period, rng, item_no + 1, "interest", interest))
        return pd.DataFrame(rows)


def _recon_item(common, account, period, rng, item_no, item_type, amount):
    return {
        **common,
        **account,
        "recon_item_id": f"BR-{item_no:03d}",
        "recon_item_type": item_type,
        "transaction_date": period.end_date - timedelta(days=rng.randint(1, 20)),
        "reference": f"BNK-{rng.randint(100000, 999999)}",
        "description": item_type.replace("_", " ").title(),
        "bank_amount": amount if item_type in {"bank_charge", "interest"} else None,
        "book_amount": None,
        "difference_amount": amount,
        "statement_balance": None,
        "book_balance": None,
        "adjusted_bank_balance": None,
        "adjusted_book_balance": None,
        "variance": 0.0,
        "cleared_flag": False,
        "matched_gl_entry_id": None,
        "matched_bank_reference": None,
        "remarks": "",
    }

