"""Report-archetype layer for workbook-facing financial documents.

The financial generators produce canonical open-item DataFrames. Real finance
teams do not send canonical schemas; they send *reports*: an aging is a
vendor-summary pivot with day-band columns, a balance, and a footed grand total,
under a named report title ("Aged Creditors as at 31/12/2025").

This module sits above ``visible_schema``. It reshapes canonical data into the
*form* a finance team would actually save, while leaving the canonical
``GeneratedDocument.data`` untouched for reconciliation and ground truth. The
visible-export schema then aliases the headers of the reshaped frame, and the
layout engine renders the report title and chrome.

Severity ramp:

- Severity 0-2: ``listing`` form (flat open items), but with a finance report
  title and header band recorded.
- Severity 3+: ``summary_pivot`` for AP/AR aging - one row per counterparty,
  bucket columns spread across, a balance column, and a grand-total row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from random import Random
from typing import Any, Mapping

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod, GeneratedDocument
from pbc_chaos.workbook.visible_schema import COMMON_CONTEXT_FIELDS


#: Severity at which aging documents become summary pivots rather than flat lists.
PIVOT_MIN_SEVERITY = 3

#: Severity at which transaction listings group by account/employee with subtotals.
GROUP_MIN_SEVERITY = 3

#: Severity at which workbooks carry an accounting-software export signature.
SIGNATURE_MIN_SEVERITY = 4

#: Recognisable Malaysian SME accounting packages, used as export signatures.
SOFTWARE_SIGNATURES = ("SQL Account", "AutoCount", "Sage UBS", "Million", "MYOB")


def choose_software_signature(seed: int) -> str:
    """Pick one accounting-software signature deterministically per workbook."""

    return SOFTWARE_SIGNATURES[Random(seed).randrange(len(SOFTWARE_SIGNATURES))]

_BUCKET_FIELDS = (
    "current_amount",
    "bucket_1_30",
    "bucket_31_60",
    "bucket_61_90",
    "bucket_over_90",
)


@dataclass(frozen=True)
class HeaderLine:
    """One line of the report header band rendered above the table."""

    value: str
    label: str | None = None
    canonical_field: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "value": self.value, "canonical_field": self.canonical_field}


@dataclass(frozen=True)
class ReportFrame:
    """A canonical document re-expressed in the form a finance team would save."""

    document_type: DocumentType
    archetype_id: str
    report_form: str  # "summary_pivot" | "listing"
    report_title: str
    report_subtitle: str | None
    header_band: tuple[HeaderLine, ...]
    table: pd.DataFrame  # what feeds visible-export aliasing and the worksheet
    grouping_key: str | None
    grand_total: bool
    bucket_label_mapping: dict[str, str]
    software_signature: str | None
    report_grain_schema: tuple[str, ...]
    aggregated_canonical_view: pd.DataFrame  # report-grain rows, canonical names, no total row
    detail_schema: tuple[str, ...]
    subtotal_labels: tuple[str, ...] = ()


def build_report_frame(
    *,
    document: GeneratedDocument,
    company: CompanyProfile,
    period: FinancialPeriod,
    sheet_name: str,
    seed: int,
    severity: int,
    software_signature: str | None = None,
) -> ReportFrame:
    """Return a report-shaped frame for one canonical document.

    The canonical ``document.data`` is never mutated. For non-aging documents and
    for severities below :data:`PIVOT_MIN_SEVERITY`, the frame is a flat listing
    whose table equals the canonical data; only the report title and header band
    are added. For AP/AR aging at higher severity, the frame is a summary pivot.
    """

    rng = Random(seed)
    document_type = document.document_type
    columns = document.data.columns
    detail_schema = tuple(str(column) for column in columns)

    pivot_spec = _AGING_PIVOTS.get(document_type)
    can_pivot = (
        pivot_spec is not None
        and severity >= PIVOT_MIN_SEVERITY
        and pivot_spec["id_field"] in columns
        and pivot_spec["name_field"] in columns
        and any(field_name in columns for field_name in _BUCKET_FIELDS)
    )

    group_spec = _DETAIL_GROUPS.get(document_type)
    can_group = (
        group_spec is not None
        and severity >= GROUP_MIN_SEVERITY
        and group_spec["group_key"] in columns
        and group_spec["label_field"] in columns
        and any(field_name in columns for field_name in group_spec["subtotal_fields"])
    )

    total_spec = _TOTALED_LISTINGS.get(document_type)
    can_total = (
        total_spec is not None
        and severity >= GROUP_MIN_SEVERITY
        and total_spec["label_field"] in columns
        and any(field_name in columns for field_name in total_spec["subtotal_fields"])
    )

    title_base = _report_title_base(document_type, rng)
    report_title = _report_title(title_base, document_type, period)
    currency = company.currency
    header_band = _header_band(
        company=company,
        period=period,
        title=report_title,
        currency=currency,
    )
    subtitle = f"All amounts in {currency}" if currency else None

    if can_pivot:
        aggregated, sum_fields = _aggregate_aging(
            document.data,
            id_field=pivot_spec["id_field"],
            name_field=pivot_spec["name_field"],
        )
        table = _append_grand_total(
            aggregated,
            sum_fields=sum_fields,
            name_field=pivot_spec["name_field"],
            id_field=pivot_spec["id_field"],
        )
        bucket_label_mapping = _bucket_label_family(
            present=tuple(f for f in _BUCKET_FIELDS if f in aggregated.columns),
            rng=rng,
        )
        return ReportFrame(
            document_type=document_type,
            archetype_id=pivot_spec["archetype_id"],
            report_form="summary_pivot",
            report_title=report_title,
            report_subtitle=subtitle,
            header_band=header_band,
            table=table,
            grouping_key=pivot_spec["id_field"],
            grand_total=True,
            bucket_label_mapping=bucket_label_mapping,
            software_signature=software_signature,
            report_grain_schema=tuple(str(column) for column in aggregated.columns),
            aggregated_canonical_view=aggregated,
            detail_schema=detail_schema,
            subtotal_labels=("Grand Total",),
        )

    if can_group:
        table, aggregated, subtotal_labels = _grouped_detail(
            document.data,
            group_key=group_spec["group_key"],
            label_column=group_spec["label_field"],
            display_field=group_spec.get("display_field", group_spec["label_field"]),
            subtotal_fields=tuple(
                f for f in group_spec["subtotal_fields"] if f in columns
            ),
        )
        return ReportFrame(
            document_type=document_type,
            archetype_id=group_spec["archetype_id"],
            report_form="detail_grouped",
            report_title=report_title,
            report_subtitle=subtitle,
            header_band=header_band,
            table=table,
            grouping_key=group_spec["group_key"],
            grand_total=True,
            bucket_label_mapping={},
            software_signature=software_signature,
            report_grain_schema=detail_schema,
            aggregated_canonical_view=aggregated,
            detail_schema=detail_schema,
            subtotal_labels=subtotal_labels,
        )

    if can_total:
        subtotal_fields = tuple(f for f in total_spec["subtotal_fields"] if f in columns)
        table = _totaled_listing(
            document.data,
            label_column=total_spec["label_field"],
            subtotal_fields=subtotal_fields,
        )
        return ReportFrame(
            document_type=document_type,
            archetype_id=total_spec["archetype_id"],
            report_form="totaled_listing",
            report_title=report_title,
            report_subtitle=subtitle,
            header_band=header_band,
            table=table,
            grouping_key=None,
            grand_total=True,
            bucket_label_mapping={},
            software_signature=software_signature,
            report_grain_schema=detail_schema,
            aggregated_canonical_view=document.data.copy(),
            detail_schema=detail_schema,
            subtotal_labels=("Grand Total",),
        )

    listing = document.data.copy()
    return ReportFrame(
        document_type=document_type,
        archetype_id=f"{document_type.value}_listing",
        report_form="listing",
        report_title=report_title,
        report_subtitle=subtitle,
        header_band=header_band,
        table=listing,
        grouping_key=None,
        grand_total=False,
        bucket_label_mapping={},
        software_signature=software_signature,
        report_grain_schema=detail_schema,
        aggregated_canonical_view=listing,
        detail_schema=detail_schema,
        subtotal_labels=(),
    )


def _aggregate_aging(
    data: pd.DataFrame,
    *,
    id_field: str,
    name_field: str,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Collapse open items to one row per counterparty, summing bucket columns."""

    bucket_fields = [field_name for field_name in _BUCKET_FIELDS if field_name in data.columns]
    sum_fields = list(bucket_fields)
    if "outstanding_amount" in data.columns:
        sum_fields.append("outstanding_amount")

    grouped = (
        data.groupby([id_field, name_field], as_index=False, sort=True)[sum_fields].sum()
    )
    for field_name in sum_fields:
        grouped[field_name] = grouped[field_name].round(2)

    common = [field_name for field_name in COMMON_CONTEXT_FIELDS if field_name in data.columns]
    for field_name in common:
        grouped[field_name] = data[field_name].iloc[0]

    ordered = common + [id_field, name_field] + bucket_fields
    if "outstanding_amount" in sum_fields:
        ordered.append("outstanding_amount")
    return grouped.loc[:, ordered].copy(), tuple(sum_fields)


def _append_grand_total(
    aggregated: pd.DataFrame,
    *,
    sum_fields: tuple[str, ...],
    name_field: str,
    id_field: str,
) -> pd.DataFrame:
    """Append a footed grand-total row beneath the aggregated rows."""

    total: dict[str, Any] = {column: None for column in aggregated.columns}
    total[name_field] = "Grand Total"
    total[id_field] = None
    for field_name in sum_fields:
        total[field_name] = round(float(aggregated[field_name].sum()), 2)
    total_row = pd.DataFrame([total], columns=aggregated.columns)
    return pd.concat([aggregated, total_row], ignore_index=True)


def _grouped_detail(
    data: pd.DataFrame,
    *,
    group_key: str,
    label_column: str,
    display_field: str,
    subtotal_fields: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[str, ...]]:
    """Order detail rows by group and foot each group with a labelled subtotal.

    ``group_key`` decides how rows are grouped, ``display_field`` provides the
    human name shown in the subtotal label, and ``label_column`` is the visible
    column the label text is written into.

    Returns the rendered table (detail rows + subtotal rows + grand total), the
    detail-only aggregated view (the report grain an extractor should return),
    and the labels of the inserted subtotal/total rows.
    """

    columns = list(data.columns)
    detail_rows: list[dict[str, Any]] = []
    rendered_rows: list[dict[str, Any]] = []
    subtotal_labels: list[str] = []

    for _, group_df in data.groupby(group_key, sort=True):
        for _, row in group_df.iterrows():
            record = row.to_dict()
            detail_rows.append(record)
            rendered_rows.append(record)
        label = f"Total - {group_df.iloc[0][display_field]}"
        rendered_rows.append(_total_row(columns, label_column, label, group_df, subtotal_fields))
        subtotal_labels.append(label)

    rendered_rows.append(_total_row(columns, label_column, "Grand Total", data, subtotal_fields))
    subtotal_labels.append("Grand Total")

    table = pd.DataFrame(rendered_rows, columns=columns)
    aggregated = pd.DataFrame(detail_rows, columns=columns)
    return table, aggregated, tuple(subtotal_labels)


def _totaled_listing(
    data: pd.DataFrame,
    *,
    label_column: str,
    subtotal_fields: tuple[str, ...],
) -> pd.DataFrame:
    """Keep every detail row and append a single footed grand-total row."""

    columns = list(data.columns)
    rendered_rows = [row.to_dict() for _, row in data.iterrows()]
    rendered_rows.append(_total_row(columns, label_column, "Grand Total", data, subtotal_fields))
    return pd.DataFrame(rendered_rows, columns=columns)


def _total_row(
    columns: list[str],
    label_column: str,
    label: str,
    frame: pd.DataFrame,
    subtotal_fields: tuple[str, ...],
) -> dict[str, Any]:
    row: dict[str, Any] = {column: None for column in columns}
    row[label_column] = label
    for field_name in subtotal_fields:
        row[field_name] = round(float(frame[field_name].sum()), 2)
    return row


def _bucket_label_family(*, present: tuple[str, ...], rng: Random) -> dict[str, str]:
    """Pick a coherent finance day-band label family for the buckets present."""

    family = _BUCKET_LABEL_FAMILIES[rng.randrange(len(_BUCKET_LABEL_FAMILIES))]
    return {field_name: family[field_name] for field_name in present if field_name in family}


def _report_title_base(document_type: DocumentType, rng: Random) -> str:
    titles = _REPORT_TITLES.get(document_type)
    if not titles:
        return _humanize(document_type.value)
    return titles[rng.randrange(len(titles))]


def _report_title(base: str, document_type: DocumentType, period: FinancialPeriod) -> str:
    as_at = _format_date(period.end_date)
    if document_type in _FLOW_DOCUMENTS:
        return f"{base} for the year ended {as_at}"
    return f"{base} as at {as_at}"


def _header_band(
    *,
    company: CompanyProfile,
    period: FinancialPeriod,
    title: str,
    currency: str,
) -> tuple[HeaderLine, ...]:
    lines = [
        HeaderLine(value=company.company_name, canonical_field="client_id"),
        HeaderLine(value=title),
        HeaderLine(
            value=_format_date(period.end_date),
            label="As at",
            canonical_field="period_end",
        ),
    ]
    if currency:
        lines.append(
            HeaderLine(
                value=f"All amounts in {currency}",
                label="Currency",
                canonical_field="currency",
            )
        )
    return tuple(lines)


def _format_date(value: date | datetime) -> str:
    return value.strftime("%d/%m/%Y")


def _humanize(value: str) -> str:
    return " ".join(word.title() for word in value.split("_") if word)


_AGING_PIVOTS: Mapping[DocumentType, dict[str, str]] = {
    DocumentType.AP_AGING: {
        "id_field": "vendor_id",
        "name_field": "vendor_name",
        "archetype_id": "ap_aged_creditors_summary",
    },
    DocumentType.AR_AGING: {
        "id_field": "customer_id",
        "name_field": "customer_name",
        "archetype_id": "ar_aged_debtors_summary",
    },
}


_DETAIL_GROUPS: Mapping[DocumentType, dict[str, Any]] = {
    DocumentType.GENERAL_LEDGER: {
        "group_key": "account_code",
        "label_field": "account_name",
        "subtotal_fields": ("debit", "credit", "amount_signed"),
        "archetype_id": "gl_account_detail",
    },
    DocumentType.JOURNAL_ENTRY_LISTING: {
        "group_key": "journal_id",
        "label_field": "account_name",
        "display_field": "journal_id",
        "subtotal_fields": ("debit", "credit", "amount_signed"),
        "archetype_id": "je_voucher_listing",
    },
    DocumentType.PAYROLL_DETAIL: {
        "group_key": "department",
        "label_field": "employee_name",
        "display_field": "department",
        "subtotal_fields": ("gross_pay", "net_pay"),
        "archetype_id": "payroll_department_detail",
    },
    DocumentType.EXPENSE_CLAIM_LISTING: {
        "group_key": "employee_id",
        "label_field": "employee_name",
        "subtotal_fields": ("amount_gross", "tax_amount", "amount_net"),
        "archetype_id": "expense_employee_listing",
    },
    DocumentType.FIXED_ASSET_REGISTER: {
        "group_key": "asset_class",
        "label_field": "asset_description",
        "display_field": "asset_class",
        "subtotal_fields": ("cost", "accumulated_depreciation_closing", "net_book_value"),
        "archetype_id": "fa_class_register",
    },
    DocumentType.INVENTORY_LISTING: {
        "group_key": "category",
        "label_field": "item_description",
        "display_field": "category",
        "subtotal_fields": ("total_cost", "write_down_amount"),
        "archetype_id": "inventory_category_listing",
    },
    DocumentType.BANK_RECONCILIATION: {
        "group_key": "recon_item_type",
        "label_field": "description",
        "display_field": "recon_item_type",
        "subtotal_fields": ("bank_amount", "book_amount", "difference_amount"),
        "archetype_id": "bank_recon_by_type",
    },
}


#: Listings that keep every row but append a footed grand total (e.g. a TB).
_TOTALED_LISTINGS: Mapping[DocumentType, dict[str, Any]] = {
    DocumentType.TRIAL_BALANCE: {
        "label_field": "account_name",
        "subtotal_fields": (
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
        ),
        "archetype_id": "tb_nominal_totaled",
    },
}


_BUCKET_LABEL_FAMILIES: tuple[dict[str, str], ...] = (
    {
        "current_amount": "Current",
        "bucket_1_30": "30 Days",
        "bucket_31_60": "60 Days",
        "bucket_61_90": "90 Days",
        "bucket_over_90": "120+",
    },
    {
        "current_amount": "Current",
        "bucket_1_30": "1-30",
        "bucket_31_60": "31-60",
        "bucket_61_90": "61-90",
        "bucket_over_90": "90+",
    },
    {
        "current_amount": "Not Due",
        "bucket_1_30": "0-30",
        "bucket_31_60": "31-60",
        "bucket_61_90": "61-90",
        "bucket_over_90": "Over 90",
    },
)


#: Documents whose report title reads "for the year ended" rather than "as at".
_FLOW_DOCUMENTS = frozenset(
    {
        DocumentType.GENERAL_LEDGER,
        DocumentType.JOURNAL_ENTRY_LISTING,
        DocumentType.PAYROLL_SUMMARY,
        DocumentType.PAYROLL_DETAIL,
        DocumentType.EXPENSE_CLAIM_LISTING,
    }
)


_REPORT_TITLES: Mapping[DocumentType, tuple[str, ...]] = {
    DocumentType.AP_AGING: ("Aged Creditors", "Creditor Listing", "AP Ageing Summary", "Supplier Aging"),
    DocumentType.AR_AGING: ("Aged Debtors", "Debtor Listing", "AR Ageing", "Collection Report"),
    DocumentType.TRIAL_BALANCE: ("Trial Balance", "Nominal Ledger", "TB"),
    DocumentType.GENERAL_LEDGER: ("GL Detail", "Ledger Listing", "Account Transactions"),
    DocumentType.BANK_RECONCILIATION: ("Bank Reconciliation", "Cash Book Recon", "Bank Rec"),
    DocumentType.FIXED_ASSET_REGISTER: ("Fixed Asset Register", "FA Listing", "Asset Schedule"),
    DocumentType.PAYROLL_SUMMARY: ("Payroll Summary", "Salary Summary", "Payroll Run"),
    DocumentType.PAYROLL_DETAIL: ("Payroll Detail", "Salary Detail", "Employee Payroll"),
    DocumentType.INVENTORY_LISTING: ("Stock Listing", "Inventory Valuation", "Stock Report"),
    DocumentType.JOURNAL_ENTRY_LISTING: ("Journal Listing", "JV Listing", "Manual Journals"),
    DocumentType.EXPENSE_CLAIM_LISTING: ("Expense Claims", "Staff Claims", "Reimbursement Listing"),
    DocumentType.PBC_REQUEST_LIST: ("PBC Request List",),
}
