"""Clean Inventory Listing generator."""

from __future__ import annotations

from datetime import timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import base_common, money
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class InventoryListingGenerator(BaseFinancialDocumentGenerator):
    """Generate inventory quantities and valuation by SKU/location/lot."""

    document_type = DocumentType.INVENTORY_LISTING

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        categories = ("Raw materials", "Finished goods", "Packaging", "Spare parts")
        rows = []
        common = base_common(company, period)
        for index in range(65):
            quantity = round(rng.uniform(5, 2_500), 2)
            unit_cost = money(rng, 1.5, 450)
            total_cost = round(quantity * unit_cost, 2)
            physical_count = round(quantity + rng.choice([0, 0, 0, rng.uniform(-5, 5)]), 2)
            variance_qty = round(physical_count - quantity, 2)
            obsolete = rng.random() < 0.08
            write_down = round(total_cost * rng.uniform(0.05, 0.35), 2) if obsolete else 0.0
            rows.append(
                {
                    **common,
                    "item_id": f"ITEM{index + 1:05d}",
                    "sku": f"SKU-{rng.randint(10000, 99999)}",
                    "item_description": f"{rng.choice(categories)} item {index + 1:03d}",
                    "category": rng.choice(categories),
                    "warehouse": rng.choice(["Main WH", "Raw Mat WH", "3PL", "Branch WH"]),
                    "location": rng.choice(["A01", "A02", "B12", "C05", "D09"]),
                    "lot_serial_number": f"LOT{rng.randint(1000, 9999)}",
                    "quantity_on_hand": quantity,
                    "uom": rng.choice(["EA", "KG", "BOX", "M"]),
                    "unit_cost": unit_cost,
                    "total_cost": total_cost,
                    "valuation_method": rng.choice(["fifo", "weighted_average", "standard_cost"]),
                    "last_movement_date": period.end_date - timedelta(days=rng.randint(1, 180)),
                    "obsolete_flag": obsolete,
                    "write_down_amount": write_down,
                    "physical_count_quantity": physical_count,
                    "variance_quantity": variance_qty,
                    "variance_amount": round(variance_qty * unit_cost, 2),
                    "remarks": "",
                }
            )
        return pd.DataFrame(rows)

