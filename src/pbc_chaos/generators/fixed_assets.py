"""Clean Fixed Asset Register generator."""

from __future__ import annotations

from datetime import timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import VENDORS, base_common, money
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class FixedAssetRegisterGenerator(BaseFinancialDocumentGenerator):
    """Generate an asset register with cost, depreciation, and NBV."""

    document_type = DocumentType.FIXED_ASSET_REGISTER

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        classes = (
            ("Computer equipment", 36),
            ("Office furniture", 60),
            ("Plant and machinery", 84),
            ("Motor vehicles", 60),
            ("Leasehold improvements", 72),
        )
        rows = []
        common = base_common(company, period)
        for index in range(30):
            asset_class, life_months = rng.choice(classes)
            acquired_days = rng.randint(60, 1_800)
            acquisition_date = period.end_date - timedelta(days=acquired_days)
            cost = money(rng, 2_000, 180_000)
            monthly_dep = cost / life_months
            age_months = min(life_months, max(1, acquired_days // 30))
            accumulated_opening = round(monthly_dep * max(0, age_months - 12), 2)
            current_dep = round(monthly_dep * min(12, age_months), 2)
            accumulated_closing = min(cost, round(accumulated_opening + current_dep, 2))
            nbv = round(cost - accumulated_closing, 2)
            rows.append(
                {
                    **common,
                    "asset_id": f"FA{index + 1:05d}",
                    "asset_class": asset_class,
                    "asset_description": f"{asset_class} #{index + 1:03d}",
                    "acquisition_date": acquisition_date,
                    "in_service_date": acquisition_date + timedelta(days=rng.randint(0, 20)),
                    "supplier_name": rng.choice(VENDORS),
                    "invoice_number": f"CAP-{period.financial_year}-{index + 1:04d}",
                    "location": rng.choice(["HQ", "Warehouse", "Branch A", "Branch B"]),
                    "department": rng.choice(["Operations", "Sales", "IT", "Admin"]),
                    "cost": cost,
                    "additions": cost if acquisition_date.year == period.financial_year else 0.0,
                    "disposals": 0.0,
                    "depreciation_method": "Straight line",
                    "useful_life_months": life_months,
                    "residual_value": 0.0,
                    "accumulated_depreciation_opening": accumulated_opening,
                    "depreciation_current_year": current_dep,
                    "accumulated_depreciation_closing": accumulated_closing,
                    "net_book_value": nbv,
                    "disposal_date": None,
                    "disposal_proceeds": 0.0,
                    "gain_loss_on_disposal": 0.0,
                    "status": "fully_depreciated" if nbv <= 0 else "active",
                    "remarks": "",
                }
            )
        return pd.DataFrame(rows)

