"""Clean Expense Claim Listing generator."""

from __future__ import annotations

from datetime import timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import DEPARTMENTS, EMPLOYEES, base_common, employee_id, money, random_date
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class ExpenseClaimListingGenerator(BaseFinancialDocumentGenerator):
    """Generate employee expense claim lines."""

    document_type = DocumentType.EXPENSE_CLAIM_LISTING

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        categories = ("Travel", "Meals", "Accommodation", "Client entertainment", "Office supplies")
        merchants = ("Grab", "AirAsia", "Marriott", "Shell", "Popular Bookstore", "City Cafe")
        rows = []
        common = base_common(company, period)
        claim_no = 1
        for _ in range(55):
            employee_index = rng.randrange(len(EMPLOYEES))
            line_count = rng.choice([1, 1, 2, 3])
            claim_date = random_date(rng, period)
            for line_number in range(1, line_count + 1):
                expense_date = claim_date - timedelta(days=rng.randint(0, 21))
                gross = money(rng, 25, 3_500)
                tax = round(gross * rng.choice([0.0, 0.06]), 2)
                net = round(gross - tax, 2)
                approved = rng.random() > 0.06
                paid = approved and rng.random() > 0.18
                rows.append(
                    {
                        **common,
                        "claim_id": f"CLM{period.financial_year}{claim_no:05d}",
                        "line_number": line_number,
                        "employee_id": employee_id(employee_index),
                        "employee_name": EMPLOYEES[employee_index],
                        "department": rng.choice(DEPARTMENTS),
                        "claim_date": claim_date,
                        "receipt_date": expense_date,
                        "expense_date": expense_date,
                        "expense_category": rng.choice(categories),
                        "merchant": rng.choice(merchants),
                        "description": "Employee reimbursement claim",
                        "amount_gross": gross,
                        "tax_amount": tax,
                        "amount_net": net,
                        "reimbursement_status": "Paid" if paid else "Pending payment",
                        "payment_date": claim_date + timedelta(days=10) if paid else None,
                        "approval_status": "Approved" if approved else "Pending approval",
                        "approved_by": rng.choice(["Finance Manager", "Department Head"]),
                        "project_code": rng.choice(["PRJ-A", "PRJ-B", None]),
                        "cost_center": rng.choice(["CC100", "CC200", "CC300"]),
                        "receipt_available_flag": rng.random() > 0.08,
                        "policy_exception_flag": rng.random() < 0.05,
                        "remarks": "",
                    }
                )
            claim_no += 1
        return pd.DataFrame(rows)

