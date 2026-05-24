"""Clean AR Aging generator."""

from __future__ import annotations

from datetime import timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import (
    CUSTOMERS,
    aging_bucket,
    base_common,
    bucket_amounts,
    customer_id,
    money,
)
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class ARAgingGenerator(BaseFinancialDocumentGenerator):
    """Generate customer open-item aging with realistic collection status."""

    document_type = DocumentType.AR_AGING

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        rows = []
        common = base_common(company, period)
        statuses = ("Not due", "Reminder sent", "Promise to pay", "Escalated", "Disputed")
        for index in range(50):
            customer_index = rng.randrange(len(CUSTOMERS))
            days_old = rng.randint(0, 150)
            invoice_date = period.end_date - timedelta(days=days_old)
            term_days = rng.choice((30, 45, 60))
            due_date = invoice_date + timedelta(days=term_days)
            days_past_due = (period.end_date - due_date).days
            bucket = aging_bucket(days_past_due)
            original = money(rng, 800, 95_000)
            outstanding = round(original * rng.uniform(0.25, 1.0), 2)
            rows.append(
                {
                    **common,
                    "customer_id": customer_id(customer_index),
                    "customer_name": CUSTOMERS[customer_index],
                    "invoice_number": f"INV-{period.financial_year}-{index + 1:05d}",
                    "invoice_date": invoice_date,
                    "due_date": due_date,
                    "aging_date": period.end_date,
                    "days_past_due": days_past_due,
                    "aging_bucket": bucket,
                    "original_amount": original,
                    "outstanding_amount": outstanding,
                    **bucket_amounts(outstanding, bucket),
                    "credit_terms": f"Net {term_days}",
                    "salesperson": rng.choice(["Lim", "Tan", "Rahman", "Wong"]),
                    "collection_status": rng.choice(statuses),
                    "disputed_flag": rng.random() < 0.05,
                    "remarks": "",
                }
            )
        return pd.DataFrame(rows)

