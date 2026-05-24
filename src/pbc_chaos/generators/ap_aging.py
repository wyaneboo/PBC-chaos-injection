"""Clean AP Aging generator."""

from __future__ import annotations

from datetime import timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import (
    VENDORS,
    aging_bucket,
    base_common,
    bucket_amounts,
    money,
    vendor_id,
)
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class APAgingGenerator(BaseFinancialDocumentGenerator):
    """Generate supplier open-item aging with bucket columns."""

    document_type = DocumentType.AP_AGING

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        rows = []
        common = base_common(company, period)
        terms = (30, 45, 60)
        for index in range(45):
            vendor_index = rng.randrange(len(VENDORS))
            days_old = rng.randint(5, 135)
            invoice_date = period.end_date - timedelta(days=days_old)
            due_days = rng.choice(terms)
            due_date = invoice_date + timedelta(days=due_days)
            days_past_due = (period.end_date - due_date).days
            bucket = aging_bucket(days_past_due)
            original = money(rng, 450, 75_000)
            outstanding = round(original * rng.uniform(0.35, 1.0), 2)
            rows.append(
                {
                    **common,
                    "vendor_id": vendor_id(vendor_index),
                    "vendor_name": VENDORS[vendor_index],
                    "invoice_number": f"SUP-{period.financial_year}-{index + 1:05d}",
                    "invoice_date": invoice_date,
                    "due_date": due_date,
                    "aging_date": period.end_date,
                    "days_past_due": days_past_due,
                    "aging_bucket": bucket,
                    "original_amount": original,
                    "outstanding_amount": outstanding,
                    **bucket_amounts(outstanding, bucket),
                    "payment_terms": f"Net {due_days}",
                    "purchase_order_number": f"PO-{rng.randint(10000, 99999)}",
                    "hold_flag": rng.random() < 0.08,
                    "disputed_flag": rng.random() < 0.06,
                    "remarks": "",
                }
            )
        return pd.DataFrame(rows)

