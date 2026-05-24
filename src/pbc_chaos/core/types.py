"""Shared enums and identifiers."""

from __future__ import annotations

from enum import Enum


class ChaosSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DocumentType(str, Enum):
    TRIAL_BALANCE = "trial_balance"
    GENERAL_LEDGER = "general_ledger"
    AP_AGING = "ap_aging"
    AR_AGING = "ar_aging"
    BANK_RECONCILIATION = "bank_reconciliation"
    PAYROLL_SUMMARY = "payroll_summary"
    PAYROLL_DETAIL = "payroll_detail"
    FIXED_ASSET_REGISTER = "fixed_asset_register"
    INVENTORY_LISTING = "inventory_listing"
    TAX_COMPUTATION = "tax_computation"
    SST_GST_REPORT = "sst_gst_report"
    COMMISSION_STATEMENT = "commission_statement"
    INSURANCE_PRODUCTION_REPORT = "insurance_production_report"
    CUSTOMER_CONFIRMATION_LIST = "customer_confirmation_list"
    SUPPLIER_CONFIRMATION_LIST = "supplier_confirmation_list"
    CASH_FLOW_SUMMARY = "cash_flow_summary"
    JOURNAL_ENTRY_LISTING = "journal_entry_listing"
    EXPENSE_CLAIM_LISTING = "expense_claim_listing"


class WorkbookFormat(str, Enum):
    XLSX = "xlsx"

