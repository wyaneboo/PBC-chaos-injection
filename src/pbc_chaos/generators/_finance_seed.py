"""Shared deterministic finance data helpers for Phase 5 generators."""

from __future__ import annotations

from datetime import date, timedelta
from random import Random
from typing import Any

from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod


ACCOUNT_MASTER: tuple[dict[str, str], ...] = (
    {"code": "1000", "name": "Cash at bank", "category": "asset", "normal": "debit"},
    {"code": "1100", "name": "Trade receivables", "category": "asset", "normal": "debit"},
    {"code": "1200", "name": "Inventory", "category": "asset", "normal": "debit"},
    {"code": "1300", "name": "Prepayments", "category": "asset", "normal": "debit"},
    {"code": "1500", "name": "Property, plant and equipment", "category": "asset", "normal": "debit"},
    {"code": "1590", "name": "Accumulated depreciation", "category": "asset", "normal": "credit"},
    {"code": "2000", "name": "Trade payables", "category": "liability", "normal": "credit"},
    {"code": "2100", "name": "Accruals", "category": "liability", "normal": "credit"},
    {"code": "2200", "name": "Payroll liabilities", "category": "liability", "normal": "credit"},
    {"code": "3000", "name": "Share capital", "category": "equity", "normal": "credit"},
    {"code": "3100", "name": "Retained earnings", "category": "equity", "normal": "credit"},
    {"code": "4000", "name": "Product revenue", "category": "revenue", "normal": "credit"},
    {"code": "4100", "name": "Service revenue", "category": "revenue", "normal": "credit"},
    {"code": "5000", "name": "Cost of sales", "category": "expense", "normal": "debit"},
    {"code": "6000", "name": "Payroll expense", "category": "expense", "normal": "debit"},
    {"code": "6100", "name": "Rent expense", "category": "expense", "normal": "debit"},
    {"code": "6200", "name": "Travel and entertainment", "category": "expense", "normal": "debit"},
    {"code": "6300", "name": "Depreciation expense", "category": "expense", "normal": "debit"},
    {"code": "6400", "name": "Bank charges", "category": "expense", "normal": "debit"},
)

VENDORS = (
    "Alpha Office Supplies",
    "Beta Logistics",
    "Capital Equipment Sdn Bhd",
    "Delta Components",
    "Evergreen Utilities",
    "FastCloud Software",
    "Metro Facility Services",
    "Northstar Packaging",
)
CUSTOMERS = (
    "Apex Retail Group",
    "Beacon Distribution",
    "CityMart Trading",
    "Eastern Healthcare",
    "Greenline Industries",
    "Harbor Wholesale",
    "Orion Services",
    "Vertex Manufacturing",
)
DEPARTMENTS = ("Finance", "Operations", "Sales", "Warehouse", "HR", "IT", "Admin")
EMPLOYEES = (
    "Aisha Rahman",
    "Daniel Lim",
    "Mei Tan",
    "Raj Kumar",
    "Sarah Lee",
    "Farah Hassan",
    "Kevin Wong",
    "Nadia Ong",
    "Jason Teo",
    "Priya Nair",
)


def base_common(company: CompanyProfile, period: FinancialPeriod) -> dict[str, Any]:
    """Return fields common to normalized financial schemas."""

    return {
        "client_id": company.company_id,
        "financial_year": period.financial_year,
        "period_start": period.start_date,
        "period_end": period.end_date,
        "currency": company.currency,
    }


def money(rng: Random, low: float, high: float, *, round_to: int = 2) -> float:
    """Return a realistic positive money amount."""

    return round(rng.uniform(low, high), round_to)


def random_date(rng: Random, period: FinancialPeriod) -> date:
    """Return a random date inside the financial period."""

    days = (period.end_date - period.start_date).days
    return period.start_date + timedelta(days=rng.randint(0, days))


def month_end(period: FinancialPeriod, month: int) -> date:
    """Return a simple month-end date for the period year."""

    if month == 12:
        return date(period.financial_year, 12, 31)
    return date(period.financial_year, month + 1, 1) - timedelta(days=1)


def aging_bucket(days_past_due: int) -> str:
    """Map days past due to a standard aging bucket."""

    if days_past_due <= 0:
        return "current"
    if days_past_due <= 30:
        return "1_30"
    if days_past_due <= 60:
        return "31_60"
    if days_past_due <= 90:
        return "61_90"
    return "over_90"


def bucket_amounts(amount: float, bucket: str) -> dict[str, float]:
    """Place an amount into one aging bucket column."""

    return {
        "current_amount": amount if bucket == "current" else 0.0,
        "bucket_1_30": amount if bucket == "1_30" else 0.0,
        "bucket_31_60": amount if bucket == "31_60" else 0.0,
        "bucket_61_90": amount if bucket == "61_90" else 0.0,
        "bucket_over_90": amount if bucket == "over_90" else 0.0,
    }


def vendor_id(index: int) -> str:
    return f"V{index + 1:04d}"


def customer_id(index: int) -> str:
    return f"C{index + 1:04d}"


def employee_id(index: int) -> str:
    return f"E{index + 1:04d}"

