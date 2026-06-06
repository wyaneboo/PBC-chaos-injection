"""Visible client-export schemas for workbook-facing tables.

The financial generators produce canonical DataFrames for reconciliation and
scoring. This module turns those canonical rows into the visible Excel schema a
client might actually send: department-specific column order, shorthand headers,
and relocated workbook context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from random import Random
from typing import Any, Mapping

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod, GeneratedDocument


COMMON_CONTEXT_FIELDS = (
    "client_id",
    "financial_year",
    "period_start",
    "period_end",
    "currency",
)

_AMBIGUOUS_HEADERS = {"AC", "Description", "Name", "Ref", "Amount", "Date"}


@dataclass(frozen=True)
class VisibleExportProfile:
    profile_id: str
    department: str
    erp_style: str
    column_map: Mapping[str, tuple[str, ...]]
    visible_fields: tuple[str, ...]
    context_fields: Mapping[str, str]
    ambiguous_headers: Mapping[str, str]


@dataclass(frozen=True)
class VisibleExportResult:
    data: pd.DataFrame
    profile_id: str
    department: str
    erp_style: str
    visible_to_canonical: dict[str, str]
    canonical_to_visible: dict[str, str]
    omitted_fields: tuple[str, ...]
    context_fields: dict[str, str]
    context_field_values: dict[str, Any]
    visible_table_schema: tuple[str, ...]
    visible_column_headers: tuple[str, ...]
    ambiguous_visible_headers: dict[str, str]


def build_visible_export(
    *,
    document: GeneratedDocument,
    company: CompanyProfile,
    period: FinancialPeriod,
    sheet_name: str,
    seed: int,
    severity: int,
) -> VisibleExportResult:
    """Return a workbook-facing DataFrame and mapping metadata.

    Severity 0 intentionally remains canonical for clean baseline generation.
    Severities 1-2 rename and reorder visible headers while retaining common
    metadata fields. Severities 3-5 relocate common workbook context out of most
    main tables.
    """

    data = document.data.copy()
    if severity <= 0:
        return _identity_export(data, profile_id="canonical_clean_export")

    document_type = document.document_type
    if document_type == DocumentType.PBC_REQUEST_LIST:
        return _identity_export(data, profile_id="pbc_request_tracker_source")

    rng = Random(seed)
    columns = tuple(str(column) for column in data.columns)
    definition = _profile_definition(document_type)
    omit_common = severity >= 3
    context_fields = {
        field: _context_location(field, sheet_name=sheet_name)
        for field in COMMON_CONTEXT_FIELDS
        if omit_common and field in columns
    }
    omitted_fields = tuple(field for field in columns if field in context_fields)
    visible_fields = _visible_fields(
        columns,
        preferred_order=definition["field_order"],
        omitted_fields=omitted_fields,
    )
    aliases = dict(_COMMON_ALIASES)
    aliases.update(definition["aliases"])

    canonical_to_visible: dict[str, str] = {}
    visible_to_canonical: dict[str, str] = {}
    ambiguous_headers: dict[str, str] = {}
    used_headers: set[str] = set()
    for field in visible_fields:
        header = _choose_header(field, aliases.get(field), rng=rng, severity=severity)
        header = _unique_header(header, used_headers)
        canonical_to_visible[field] = header
        visible_to_canonical[header] = field
        if header in _AMBIGUOUS_HEADERS:
            ambiguous_headers[header] = field

    visible_data = data.loc[:, list(visible_fields)].rename(columns=canonical_to_visible)
    profile = VisibleExportProfile(
        profile_id=str(definition["profile_id"]),
        department=str(definition["department"]),
        erp_style=str(definition["erp_style"]),
        column_map=aliases,
        visible_fields=visible_fields,
        context_fields=context_fields,
        ambiguous_headers=ambiguous_headers,
    )
    return VisibleExportResult(
        data=visible_data,
        profile_id=profile.profile_id,
        department=profile.department,
        erp_style=profile.erp_style,
        visible_to_canonical=visible_to_canonical,
        canonical_to_visible=canonical_to_visible,
        omitted_fields=omitted_fields,
        context_fields=dict(profile.context_fields),
        context_field_values={
            field: _context_value(data[field])
            for field in omitted_fields
            if field in data.columns
        },
        visible_table_schema=visible_fields,
        visible_column_headers=tuple(canonical_to_visible[field] for field in visible_fields),
        ambiguous_visible_headers=dict(profile.ambiguous_headers),
    )


def _identity_export(data: pd.DataFrame, *, profile_id: str) -> VisibleExportResult:
    fields = tuple(str(column) for column in data.columns)
    mapping = {field: field for field in fields}
    return VisibleExportResult(
        data=data,
        profile_id=profile_id,
        department="canonical",
        erp_style="canonical",
        visible_to_canonical=dict(mapping),
        canonical_to_visible=dict(mapping),
        omitted_fields=(),
        context_fields={},
        context_field_values={},
        visible_table_schema=fields,
        visible_column_headers=fields,
        ambiguous_visible_headers={},
    )


def _profile_definition(document_type: DocumentType) -> dict[str, Any]:
    return _PROFILE_DEFINITIONS.get(
        document_type,
        {
            "profile_id": f"{document_type.value}_department_export",
            "department": "Finance close team",
            "erp_style": "Manual Excel export",
            "field_order": (),
            "aliases": {},
        },
    )


def _visible_fields(
    columns: tuple[str, ...],
    *,
    preferred_order: tuple[str, ...],
    omitted_fields: tuple[str, ...],
) -> tuple[str, ...]:
    omitted = set(omitted_fields)
    ordered = [field for field in preferred_order if field in columns and field not in omitted]
    ordered_set = set(ordered)
    ordered.extend(
        field
        for field in columns
        if field not in ordered_set and field not in omitted
    )
    return tuple(ordered)


def _choose_header(
    field: str,
    choices: tuple[str, ...] | None,
    *,
    rng: Random,
    severity: int,
) -> str:
    if choices:
        if severity >= 3:
            return choices[0]
        return choices[rng.randrange(len(choices))]
    return _humanize_header(field)


def _unique_header(header: str, used_headers: set[str]) -> str:
    candidate = header
    suffix = 2
    while candidate in used_headers:
        candidate = f"{header} {suffix}"
        suffix += 1
    used_headers.add(candidate)
    return candidate


def _humanize_header(field: str) -> str:
    words = [word for word in field.split("_") if word]
    if not words:
        return field
    return " ".join(_WORD_ABBREVIATIONS.get(word, word.title()) for word in words)


def _context_location(field: str, *, sheet_name: str) -> str:
    if field == "client_id":
        return "workbook_properties.company_id"
    if field == "financial_year":
        return f"{sheet_name}.title_block.fy"
    if field in {"period_start", "period_end"}:
        return f"{sheet_name}.title_block.reporting_period"
    if field == "currency":
        return f"{sheet_name}.title_block.currency"
    return f"{sheet_name}.context"


def _context_value(series: pd.Series) -> Any:
    values = [value for value in series.tolist() if not pd.isna(value)]
    if not values:
        return None
    return _json_safe(values[0])


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return value


_WORD_ABBREVIATIONS = {
    "account": "Account",
    "amount": "Amt",
    "balance": "Bal",
    "category": "Cat",
    "closing": "Close",
    "credit": "Cr",
    "current": "Current",
    "customer": "Customer",
    "debit": "Dr",
    "department": "Dept",
    "description": "Desc",
    "document": "Doc",
    "employee": "Employee",
    "financial": "Fin",
    "invoice": "Inv",
    "number": "No",
    "opening": "Open",
    "outstanding": "OS",
    "period": "Period",
    "posting": "Post",
    "reference": "Ref",
    "transaction": "Txn",
    "vendor": "Vendor",
    "year": "Year",
}


_COMMON_ALIASES: dict[str, tuple[str, ...]] = {
    "client_id": ("Client ID", "Entity", "Co Code"),
    "financial_year": ("FY", "Year", "FYE"),
    "period_start": ("From", "Period From", "Start"),
    "period_end": ("As At", "Period End", "To"),
    "currency": ("Curr", "CCY", "Currency"),
}


_PROFILE_DEFINITIONS: dict[DocumentType, dict[str, Any]] = {
    DocumentType.TRIAL_BALANCE: {
        "profile_id": "tb_nominal_listing",
        "department": "Finance close team",
        "erp_style": "Nominal ledger export",
        "field_order": (
            "account_code",
            "account_name",
            "account_category",
            "opening_debit",
            "opening_credit",
            "period_debit",
            "period_credit",
            "closing_debit",
            "closing_credit",
            "closing_balance",
            "comparative_balance",
            "adjustment_amount",
            "final_balance",
            "normal_balance",
            "remarks",
        ),
        "aliases": {
            "account_code": ("A/C", "Nominal Code", "GL Code"),
            "account_name": ("Description", "Nominal Description", "Account"),
            "account_category": ("FS Cat", "Class", "Type"),
            "normal_balance": ("Dr/Cr", "Natural Bal", "Normal Bal"),
            "opening_debit": ("Opening Dr", "B/F Dr", "Open Debit"),
            "opening_credit": ("Opening Cr", "B/F Cr", "Open Credit"),
            "period_debit": ("Movement Dr", "YTD Dr", "Period Dr"),
            "period_credit": ("Movement Cr", "YTD Cr", "Period Cr"),
            "closing_debit": ("Dr", "Closing Dr", "Close Debit"),
            "closing_credit": ("Cr", "Closing Cr", "Close Credit"),
            "closing_balance": ("CY Bal", "Balance", "RM"),
            "comparative_balance": ("PY", "Last Year", "Comparative"),
            "adjustment_amount": ("Adj", "Audit Adj", "Reclass"),
            "final_balance": ("Final", "After Adj", "Audit Final"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.GENERAL_LEDGER: {
        "profile_id": "gl_transaction_dump",
        "department": "Finance systems",
        "erp_style": "ERP transaction export",
        "field_order": (
            "posting_date",
            "journal_id",
            "line_number",
            "account_code",
            "account_name",
            "description",
            "document_number",
            "reference",
            "counterparty_name",
            "debit",
            "credit",
            "amount_signed",
            "source_module",
            "cost_center",
            "department",
            "tax_code",
            "created_by",
            "posted_by",
            "batch_id",
            "entry_id",
            "document_date",
            "period",
            "counterparty_id",
            "counterparty_type",
            "reversal_flag",
            "remarks",
        ),
        "aliases": {
            "posting_date": ("Post Dt", "GL Date", "Posted On"),
            "journal_id": ("JV No", "Journal", "Voucher"),
            "line_number": ("Line", "Ln", "Seq"),
            "account_code": ("AC", "GL Account", "Ledger"),
            "account_name": ("Account Name", "Acct Desc", "Ledger Desc"),
            "description": ("Description", "Narration", "Particulars"),
            "document_number": ("Doc No", "Ref Doc", "Source Doc"),
            "reference": ("Ref", "External Ref", "Support Ref"),
            "counterparty_name": ("Vendor", "Name", "Party"),
            "debit": ("Dr", "Debit RM", "Debit Amt"),
            "credit": ("Cr", "Credit RM", "Credit Amt"),
            "amount_signed": ("Net Amt", "Txn Amount", "Line Amount"),
            "source_module": ("Module", "Source", "ERP Module"),
            "cost_center": ("CC", "Cost Ctr", "Dept Code"),
            "department": ("Dept", "Division", "BU"),
            "tax_code": ("Tax", "SST Code", "Tax Code"),
            "created_by": ("Maker", "Input By", "User"),
            "posted_by": ("Checker", "Posted By", "Poster"),
            "batch_id": ("Batch", "Import Batch", "Upload Batch"),
            "entry_id": ("Entry ID", "Posting ID", "Txn ID"),
            "document_date": ("Doc Date", "Invoice Date", "Source Date"),
            "period": ("Period", "Month", "YYYY-MM"),
            "counterparty_id": ("Party ID", "Name Code", "Subledger ID"),
            "counterparty_type": ("Party Type", "Subledger Type", "Cust/Supp"),
            "reversal_flag": ("Rev", "Reversal?", "Reverse Flag"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.BANK_RECONCILIATION: {
        "profile_id": "treasury_bank_recon",
        "department": "Treasury",
        "erp_style": "Cash book reconciliation",
        "field_order": (
            "bank_name",
            "bank_account_number",
            "recon_item_type",
            "transaction_date",
            "reference",
            "description",
            "bank_amount",
            "book_amount",
            "difference_amount",
            "statement_balance",
            "book_balance",
            "adjusted_bank_balance",
            "adjusted_book_balance",
            "variance",
            "cleared_flag",
            "matched_bank_reference",
            "matched_gl_entry_id",
            "bank_account_id",
            "recon_item_id",
            "remarks",
        ),
        "aliases": {
            "bank_name": ("Bank", "Bank Name", "Acct Bank"),
            "bank_account_number": ("Bank Acct", "Account No", "Bank A/C"),
            "recon_item_type": ("Type", "Recon Type", "Item Type"),
            "transaction_date": ("Date", "Txn Date", "Bank Date"),
            "reference": ("Ref", "Cheque/Ref", "Bank Ref"),
            "description": ("Description", "Details", "Narration"),
            "bank_amount": ("Per Bank", "Bank Amt", "Stmt Amt"),
            "book_amount": ("Per Book", "Book Amt", "GL Amt"),
            "difference_amount": ("Diff", "Variance", "Recon Diff"),
            "statement_balance": ("Stmt Bal", "Bank Statement", "Bank Closing"),
            "book_balance": ("Book Bal", "Cash Book", "GL Closing"),
            "adjusted_bank_balance": ("Adj Bank", "Adjusted Bank", "Recon Bank"),
            "adjusted_book_balance": ("Adj Book", "Adjusted Book", "Recon Book"),
            "variance": ("Variance", "Check", "Diff Check"),
            "cleared_flag": ("Cleared?", "Clr", "Matched"),
            "matched_bank_reference": ("Bank Match Ref", "Matched Bank", "Bank Ref 2"),
            "matched_gl_entry_id": ("GL Match", "Matched GL", "GL Entry"),
            "bank_account_id": ("Bank ID", "Acct ID", "Cash Acct"),
            "recon_item_id": ("Recon Ref", "Item Ref", "Recon ID"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.AP_AGING: {
        "profile_id": "ap_supplier_aging",
        "department": "AP/payables",
        "erp_style": "Supplier aging export",
        "field_order": (
            "vendor_name",
            "vendor_id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "aging_date",
            "days_past_due",
            "current_amount",
            "bucket_1_30",
            "bucket_31_60",
            "bucket_61_90",
            "bucket_over_90",
            "original_amount",
            "outstanding_amount",
            "payment_terms",
            "purchase_order_number",
            "hold_flag",
            "disputed_flag",
            "aging_bucket",
            "remarks",
        ),
        "aliases": {
            "vendor_name": ("Name", "Supplier", "Creditor"),
            "vendor_id": ("Supplier Code", "Creditor Code", "Payee Code"),
            "invoice_number": ("Bill No", "Inv #", "Invoice"),
            "invoice_date": ("Inv Date", "Bill Date", "Doc Date"),
            "due_date": ("Due Dt", "Payment Due", "Maturity Date"),
            "aging_date": ("As At", "Ageing Date", "Report Date"),
            "days_past_due": ("Days OD", "DPD", "Overdue Days"),
            "aging_bucket": ("Age Band", "Bucket", "Ageing"),
            "original_amount": ("Inv Amt", "Original Amt", "Gross Amt"),
            "outstanding_amount": ("Open Amt", "Unpaid Amount", "O/S"),
            "current_amount": ("Current", "Not Due", "0-Current"),
            "bucket_1_30": ("1-30", "0-30", "30 Days"),
            "bucket_31_60": ("31-60", "60 Days", "31 to 60"),
            "bucket_61_90": ("61-90", "90 Days", "61 to 90"),
            "bucket_over_90": ("90+", "Over 90", ">90"),
            "payment_terms": ("Terms", "Pay Terms", "Credit Term"),
            "purchase_order_number": ("PO", "PO No", "Purchase Order"),
            "hold_flag": ("Hold?", "Payment Hold", "On Hold"),
            "disputed_flag": ("Dispute?", "Disputed", "Query"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.AR_AGING: {
        "profile_id": "ar_customer_aging",
        "department": "AR collections",
        "erp_style": "Debtor aging export",
        "field_order": (
            "customer_name",
            "customer_id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "aging_date",
            "days_past_due",
            "current_amount",
            "bucket_1_30",
            "bucket_31_60",
            "bucket_61_90",
            "bucket_over_90",
            "original_amount",
            "outstanding_amount",
            "credit_terms",
            "salesperson",
            "collection_status",
            "disputed_flag",
            "aging_bucket",
            "remarks",
        ),
        "aliases": {
            "customer_name": ("Name", "Customer", "Debtor"),
            "customer_id": ("Cust No", "Debtor Code", "Customer Code"),
            "invoice_number": ("Inv No", "Invoice", "Bill No"),
            "invoice_date": ("Inv Date", "Invoice Dt", "Doc Date"),
            "due_date": ("Due Dt", "Collection Due", "Maturity Date"),
            "aging_date": ("As At", "Ageing Date", "Cutoff Date"),
            "days_past_due": ("Days OD", "DPD", "Age Days"),
            "aging_bucket": ("Age Band", "Bucket", "Ageing"),
            "original_amount": ("Inv Amt", "Original Amt", "Gross Amt"),
            "outstanding_amount": ("O/S", "Balance Due", "Open Amount"),
            "current_amount": ("Current", "Not Due", "0-Current"),
            "bucket_1_30": ("1-30", "0-30", "30 Days"),
            "bucket_31_60": ("31-60", "60 Days", "31 to 60"),
            "bucket_61_90": ("61-90", "90 Days", "61 to 90"),
            "bucket_over_90": ("90+", "Over 90", ">90"),
            "credit_terms": ("Terms", "Credit Term", "Cust Terms"),
            "salesperson": ("Sales PIC", "Salesperson", "Collector"),
            "collection_status": ("Collection", "Chase Status", "Status"),
            "disputed_flag": ("Dispute?", "Disputed", "Query"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.FIXED_ASSET_REGISTER: {
        "profile_id": "fa_register_ops",
        "department": "Fixed assets",
        "erp_style": "Asset module export",
        "field_order": (
            "asset_id",
            "asset_class",
            "asset_description",
            "acquisition_date",
            "in_service_date",
            "supplier_name",
            "invoice_number",
            "department",
            "location",
            "cost",
            "additions",
            "disposals",
            "depreciation_method",
            "useful_life_months",
            "accumulated_depreciation_opening",
            "depreciation_current_year",
            "accumulated_depreciation_closing",
            "net_book_value",
            "status",
            "residual_value",
            "disposal_date",
            "disposal_proceeds",
            "gain_loss_on_disposal",
            "remarks",
        ),
        "aliases": {
            "asset_id": ("Asset Ref", "Asset No", "FA No"),
            "asset_class": ("AC", "Asset Cat", "Class"),
            "asset_description": ("Asset Desc", "Description", "Particulars"),
            "acquisition_date": ("Cap Date", "Acq Date", "Purchase Date"),
            "in_service_date": ("In Service", "Start Use", "Placed in Use"),
            "supplier_name": ("Supplier", "Vendor", "Payee"),
            "invoice_number": ("Inv No", "CAP Ref", "Bill No"),
            "department": ("Dept", "Cost Ctr", "BU"),
            "location": ("Location", "Site", "Loc"),
            "cost": ("Cost", "Orig Cost", "Gross Cost"),
            "additions": ("Additions", "Current Add", "CAP Add"),
            "disposals": ("Disposals", "Disp", "Asset Sold"),
            "depreciation_method": ("Depn Method", "Method", "Dep Method"),
            "useful_life_months": ("Life Mths", "Useful Life", "Life"),
            "accumulated_depreciation_opening": ("Open Acc Depn", "B/F Depn", "Acc Depn OP"),
            "depreciation_current_year": ("CY Depn", "Depn Charge", "Current Depn"),
            "accumulated_depreciation_closing": ("Close Acc Depn", "C/F Depn", "Acc Depn CL"),
            "net_book_value": ("NBV", "Carrying Amt", "Book Value"),
            "status": ("Status", "Asset Status", "State"),
            "residual_value": ("Residual", "Scrap Value", "RV"),
            "disposal_date": ("Disp Date", "Sold Date", "Disposal Dt"),
            "disposal_proceeds": ("Proceeds", "Sale Proceeds", "Disp Proceeds"),
            "gain_loss_on_disposal": ("Gain/Loss", "Disposal GL", "P/L on Disposal"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.PAYROLL_SUMMARY: {
        "profile_id": "payroll_hr_summary",
        "department": "Payroll/HR",
        "erp_style": "Payroll run summary",
        "field_order": (
            "pay_run_id",
            "pay_period_start",
            "pay_period_end",
            "payment_date",
            "department",
            "employee_count",
            "basic_salary",
            "overtime_amount",
            "allowance_amount",
            "bonus_amount",
            "gross_pay",
            "employee_deductions",
            "employer_contributions",
            "tax_withheld",
            "net_pay",
            "remarks",
        ),
        "aliases": {
            "pay_run_id": ("Run", "Pay Run", "Batch"),
            "pay_period_start": ("From", "Pay From", "Period Start"),
            "pay_period_end": ("To", "Pay To", "Period End"),
            "payment_date": ("Pay Date", "Payment Dt", "Bank Date"),
            "department": ("Dept", "Cost Ctr", "Division"),
            "employee_count": ("Headcount", "HC", "Emp Count"),
            "basic_salary": ("Basic", "Basic Salary", "Base Pay"),
            "overtime_amount": ("OT", "Overtime", "OT Amt"),
            "allowance_amount": ("Allowance", "Allow", "Allw Amt"),
            "bonus_amount": ("Bonus", "Bonus Amt", "Incentive"),
            "gross_pay": ("Gross", "Gross Pay", "Gross Amt"),
            "employee_deductions": ("Deduction", "Emp Ded", "Staff Ded"),
            "employer_contributions": ("Employer Cost", "Co Contrib", "Employer EPF"),
            "tax_withheld": ("PCB", "Tax", "Tax Deducted"),
            "net_pay": ("Net", "Net Pay", "Bank Amt"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.PAYROLL_DETAIL: {
        "profile_id": "payroll_hr_detail",
        "department": "Payroll/HR",
        "erp_style": "Employee payroll detail",
        "field_order": (
            "employee_id",
            "employee_name",
            "department",
            "position",
            "pay_run_id",
            "pay_period_start",
            "pay_period_end",
            "payment_date",
            "basic_salary",
            "overtime_amount",
            "allowance_amount",
            "bonus_amount",
            "commission_amount",
            "gross_pay",
            "epf_employee",
            "socso_employee",
            "eis_employee",
            "pcb_tax",
            "other_deductions",
            "net_pay",
            "epf_employer",
            "socso_employer",
            "eis_employer",
            "payment_method",
            "bank_account_masked",
            "join_date",
            "termination_date",
            "remarks",
        ),
        "aliases": {
            "employee_id": ("Emp No", "Staff ID", "Employee Code"),
            "employee_name": ("Employee", "Name", "Staff Name"),
            "department": ("Dept", "Cost Ctr", "Division"),
            "position": ("Title", "Position", "Job"),
            "pay_run_id": ("Run", "Pay Run", "Batch"),
            "pay_period_start": ("From", "Pay From", "Period Start"),
            "pay_period_end": ("To", "Pay To", "Period End"),
            "payment_date": ("Pay Date", "Payment Dt", "Bank Date"),
            "basic_salary": ("Basic", "Basic Salary", "Base Pay"),
            "overtime_amount": ("OT", "Overtime", "OT Amt"),
            "allowance_amount": ("Allowance", "Allow", "Allw Amt"),
            "bonus_amount": ("Bonus", "Bonus Amt", "Incentive"),
            "commission_amount": ("Comm", "Commission", "Sales Comm"),
            "gross_pay": ("Gross", "Gross Pay", "Gross Amt"),
            "epf_employee": ("EPF", "EPF Emp", "Staff EPF"),
            "socso_employee": ("SOCSO", "SOCSO Emp", "Staff SOCSO"),
            "eis_employee": ("EIS", "EIS Emp", "Staff EIS"),
            "pcb_tax": ("PCB", "Tax", "Tax Deducted"),
            "other_deductions": ("Other Ded", "Deduction", "Staff Ded"),
            "net_pay": ("Net", "Net Pay", "Bank Amt"),
            "epf_employer": ("ER EPF", "Employer EPF", "Co EPF"),
            "socso_employer": ("ER SOCSO", "Employer SOCSO", "Co SOCSO"),
            "eis_employer": ("ER EIS", "Employer EIS", "Co EIS"),
            "payment_method": ("Pay Mode", "Method", "Payment Method"),
            "bank_account_masked": ("Bank A/C", "Acct Mask", "Bank Acct"),
            "join_date": ("Join Date", "Start Date", "Date Joined"),
            "termination_date": ("Term Date", "End Date", "Left Date"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.INVENTORY_LISTING: {
        "profile_id": "warehouse_stock_listing",
        "department": "Warehouse/inventory",
        "erp_style": "Stock valuation export",
        "field_order": (
            "sku",
            "item_id",
            "item_description",
            "category",
            "warehouse",
            "location",
            "lot_serial_number",
            "quantity_on_hand",
            "uom",
            "unit_cost",
            "total_cost",
            "valuation_method",
            "last_movement_date",
            "obsolete_flag",
            "write_down_amount",
            "physical_count_quantity",
            "variance_quantity",
            "variance_amount",
            "remarks",
        ),
        "aliases": {
            "sku": ("SKU", "Stock Code", "Item Code"),
            "item_id": ("Item Ref", "Item ID", "ERP Item"),
            "item_description": ("Description", "Item Desc", "Particulars"),
            "category": ("Cat", "Stock Cat", "Class"),
            "warehouse": ("WH", "Warehouse", "Store"),
            "location": ("Loc", "Bin", "Location"),
            "lot_serial_number": ("Lot/Serial", "Batch No", "Lot No"),
            "quantity_on_hand": ("Qty", "QOH", "On Hand"),
            "uom": ("UOM", "Unit", "Measure"),
            "unit_cost": ("Unit Cost", "Cost/Unit", "Avg Cost"),
            "total_cost": ("Stock Value", "Total Cost", "Value"),
            "valuation_method": ("Valuation", "Cost Method", "Method"),
            "last_movement_date": ("Last Move", "Last Txn", "Movement Date"),
            "obsolete_flag": ("Obsolete?", "Slow Moving", "OBS"),
            "write_down_amount": ("Write Down", "NRV Adj", "Provision"),
            "physical_count_quantity": ("Count Qty", "Physical Qty", "Stocktake"),
            "variance_quantity": ("Var Qty", "Qty Var", "Diff Qty"),
            "variance_amount": ("Var Amt", "Value Diff", "Diff Amt"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.JOURNAL_ENTRY_LISTING: {
        "profile_id": "je_manual_listing",
        "department": "Finance close team",
        "erp_style": "Manual journal listing",
        "field_order": (
            "journal_id",
            "line_number",
            "posting_date",
            "journal_date",
            "journal_type",
            "account_code",
            "account_name",
            "description",
            "debit",
            "credit",
            "amount_signed",
            "reference",
            "prepared_by",
            "approved_by",
            "approval_date",
            "manual_entry_flag",
            "recurring_flag",
            "adjustment_flag",
            "source_module",
            "cost_center",
            "department",
            "remarks",
        ),
        "aliases": {
            "journal_id": ("JV No", "Journal", "Voucher"),
            "line_number": ("Line", "Ln", "Seq"),
            "posting_date": ("Post Dt", "GL Date", "Posted On"),
            "journal_date": ("JV Date", "Journal Date", "Created Dt"),
            "journal_type": ("JV Type", "Type", "Journal Class"),
            "account_code": ("AC", "GL Code", "Ledger"),
            "account_name": ("Account Name", "Acct Desc", "Ledger Desc"),
            "description": ("Description", "Narration", "Particulars"),
            "debit": ("Dr", "Debit", "Debit RM"),
            "credit": ("Cr", "Credit", "Credit RM"),
            "amount_signed": ("Net Amt", "Signed Amt", "Line Amount"),
            "reference": ("Ref", "Support Ref", "Voucher Ref"),
            "prepared_by": ("Prepared By", "Maker", "Input By"),
            "approved_by": ("Approved By", "Checker", "Reviewer"),
            "approval_date": ("Approval Dt", "Approved On", "Review Dt"),
            "manual_entry_flag": ("Manual?", "Manual JV", "ME"),
            "recurring_flag": ("Recurring?", "Recurr", "Repeat"),
            "adjustment_flag": ("Adj?", "Adjustment", "Audit Adj"),
            "source_module": ("Module", "Source", "ERP Module"),
            "cost_center": ("CC", "Cost Ctr", "Dept Code"),
            "department": ("Dept", "Division", "BU"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
    DocumentType.EXPENSE_CLAIM_LISTING: {
        "profile_id": "hr_expense_claims",
        "department": "Payroll/HR",
        "erp_style": "Expense reimbursement export",
        "field_order": (
            "claim_id",
            "line_number",
            "employee_id",
            "employee_name",
            "department",
            "claim_date",
            "expense_date",
            "receipt_date",
            "expense_category",
            "merchant",
            "description",
            "amount_gross",
            "tax_amount",
            "amount_net",
            "approval_status",
            "approved_by",
            "reimbursement_status",
            "payment_date",
            "project_code",
            "cost_center",
            "receipt_available_flag",
            "policy_exception_flag",
            "remarks",
        ),
        "aliases": {
            "claim_id": ("Claim No", "Claim ID", "Ref"),
            "line_number": ("Line", "Ln", "Item"),
            "employee_id": ("Emp No", "Staff ID", "Employee Code"),
            "employee_name": ("Employee", "Name", "Staff Name"),
            "department": ("Dept", "Cost Ctr", "Division"),
            "claim_date": ("Claim Date", "Submitted", "Date"),
            "receipt_date": ("Receipt Dt", "Receipt Date", "Rcpt Date"),
            "expense_date": ("Expense Dt", "Spend Date", "Txn Date"),
            "expense_category": ("Expense Cat", "Category", "Type"),
            "merchant": ("Merchant", "Vendor", "Payee"),
            "description": ("Description", "Purpose", "Narration"),
            "amount_gross": ("Gross", "Claim Amt", "Amount"),
            "tax_amount": ("Tax", "SST", "Tax Amt"),
            "amount_net": ("Net", "Net Amt", "Reimb Amt"),
            "reimbursement_status": ("Pay Status", "Reimb Status", "Payment"),
            "payment_date": ("Pay Date", "Paid On", "Payment Dt"),
            "approval_status": ("AC", "Approval", "Approved?"),
            "approved_by": ("Approver", "Approved By", "Manager"),
            "project_code": ("Project", "PRJ", "Job"),
            "cost_center": ("CC", "Cost Ctr", "Dept Code"),
            "receipt_available_flag": ("Receipt?", "Rcpt Avail", "Support?"),
            "policy_exception_flag": ("Exception?", "Policy Breach", "Policy?"),
            "remarks": ("Notes", "Remark", "Comments"),
        },
    },
}
