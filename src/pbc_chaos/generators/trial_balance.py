"""Clean Trial Balance generator."""

from __future__ import annotations

from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import ACCOUNT_MASTER, base_common, money
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class TrialBalanceGenerator(BaseFinancialDocumentGenerator):
    """Generate a financially plausible, roughly balanced trial balance."""

    document_type = DocumentType.TRIAL_BALANCE

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        common = base_common(company, period)
        balances: list[float] = []
        for account in ACCOUNT_MASTER[:-1]:
            if account["category"] == "asset":
                amount = money(rng, 15_000, 650_000)
            elif account["category"] in {"liability", "equity"}:
                amount = -money(rng, 20_000, 500_000)
            elif account["category"] == "revenue":
                amount = -money(rng, 250_000, 1_200_000)
            else:
                amount = money(rng, 40_000, 650_000)
            if account["code"] == "1590":
                amount = -money(rng, 40_000, 200_000)
            balances.append(amount)

        balances.append(round(-sum(balances), 2))

        rows = []
        for account, closing_balance in zip(ACCOUNT_MASTER, balances, strict=True):
            opening_balance = round(closing_balance * rng.uniform(0.65, 0.95), 2)
            movement = round(closing_balance - opening_balance, 2)
            period_debit = movement if movement > 0 else 0.0
            period_credit = abs(movement) if movement < 0 else 0.0
            rows.append(
                {
                    **common,
                    "account_code": account["code"],
                    "account_name": account["name"],
                    "account_category": account["category"],
                    "normal_balance": account["normal"],
                    "opening_debit": opening_balance if opening_balance > 0 else 0.0,
                    "opening_credit": abs(opening_balance) if opening_balance < 0 else 0.0,
                    "period_debit": period_debit,
                    "period_credit": period_credit,
                    "closing_debit": closing_balance if closing_balance > 0 else 0.0,
                    "closing_credit": abs(closing_balance) if closing_balance < 0 else 0.0,
                    "closing_balance": closing_balance,
                    "comparative_balance": round(closing_balance * rng.uniform(0.82, 1.12), 2),
                    "adjustment_amount": 0.0,
                    "final_balance": closing_balance,
                    "remarks": "",
                }
            )
        return pd.DataFrame(rows)

