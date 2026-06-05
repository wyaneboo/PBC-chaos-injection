"""Clean PBC request list generator."""

from __future__ import annotations

from datetime import date, timedelta
from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class PBCRequestListGenerator(BaseFinancialDocumentGenerator):
    """Generate a clean audit request tracker before workflow chaos is applied."""

    document_type = DocumentType.PBC_REQUEST_LIST

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        due_base = date(period.financial_year, 5, 15)
        rows = []
        for index, request in enumerate(_request_templates(period.financial_year), start=1):
            due_date = due_base + timedelta(days=int(request.get("due_offset", 0)))
            status = str(request.get("status", "not_started"))
            received = _received_date(status, due_date, rng)
            rows.append(
                {
                    "request_number": index,
                    "request_id": f"A.{index}",
                    "request_description": request["description"],
                    "detail_remark": request["detail"],
                    "purpose": request["purpose"],
                    "period_label": request["period"],
                    "file_type_requested": request["format"],
                    "owner_pic": request["owner"],
                    "due_date": due_date,
                    "status": status,
                    "date_received": received,
                    "review_status": request.get("review_status", ""),
                    "auditor_comment": request.get("auditor_comment", ""),
                    "follow_up_required": bool(request.get("follow_up", False)),
                    "update_flag": bool(request.get("updated", False)),
                    "remarks": request.get("remarks", ""),
                    "client_id": company.company_id,
                    "financial_year": period.financial_year,
                }
            )
        return pd.DataFrame(rows)


def _received_date(status: str, due_date: date, rng: Random) -> date | None:
    if status in {"done", "received", "partial"}:
        return due_date - timedelta(days=rng.randint(0, 2))
    if status == "in_progress" and rng.random() < 0.35:
        return due_date + timedelta(days=rng.randint(1, 3))
    return None


def _request_templates(financial_year: int) -> tuple[dict[str, object], ...]:
    prior_year = financial_year - 1
    return (
        {
            "description": "Trial Balance",
            "detail": f"YE {prior_year}",
            "purpose": "F/S",
            "period": f"31.12.{str(prior_year)[-2:]}",
            "format": "Excel",
            "owner": "SL",
            "status": "done",
            "review_status": "under_review",
            "auditor_comment": "Some balance diff, checking",
            "follow_up": True,
        },
        {
            "description": "GL Detail",
            "detail": "Full listing",
            "purpose": "Vouching",
            "period": f"FY{prior_year}",
            "format": "xlsx / csv",
            "owner": "Finance",
            "status": "in_progress",
            "follow_up": False,
        },
        {
            "description": "Bank Recon - All banks",
            "detail": f"Dec {prior_year}",
            "purpose": "Bank Conf",
            "period": f"Dec'{str(prior_year)[-2:]}",
            "format": "PDF",
            "owner": "KC",
            "due_offset": 1,
            "status": "received",
            "review_status": "pending",
        },
        {
            "description": "Bank Statement",
            "detail": "All operating bank accounts",
            "purpose": "Cut-off",
            "period": f"Dec {prior_year}",
            "format": "PDF",
            "owner": "KC",
            "status": "partial",
            "auditor_comment": "Missing page range",
            "follow_up": True,
        },
        {
            "description": "AR Aging",
            "detail": f"As at 31.12.{str(prior_year)[-2:]}",
            "purpose": "Existence",
            "period": f"31.12.{str(prior_year)[-2:]}",
            "format": "Excel",
            "owner": "Irene",
            "status": "done",
            "review_status": "ok",
        },
        {
            "description": "AP Aging Report",
            "detail": "Please include supplier name",
            "purpose": "Completeness",
            "period": f"Dec {prior_year}",
            "format": "Excel",
            "owner": "Irene",
            "status": "done",
            "review_status": "ok",
            "follow_up": False,
        },
        {
            "description": "Fixed Asset Register",
            "detail": "Include WDV & depreciation",
            "purpose": "Existence & Ownership",
            "period": f"31/12/{str(prior_year)[-2:]}",
            "format": "Excel / PDF",
            "owner": "FA team",
            "due_offset": 1,
            "status": "not_started",
            "auditor_comment": "Not provided",
            "follow_up": True,
            "updated": True,
        },
        {
            "description": "FA Addition Supporting",
            "detail": "Inv, DO, GRN",
            "purpose": "Cut-off",
            "period": f"FY{str(prior_year)[-2:]}",
            "format": "PDF",
            "owner": "SL",
            "status": "not_started",
            "follow_up": True,
        },
        {
            "description": "Payroll Summary",
            "detail": "Monthly total",
            "purpose": "Accuracy",
            "period": f"Jan - Dec {prior_year}",
            "format": "Excel",
            "owner": "HR",
            "status": "done",
            "review_status": "ok",
        },
        {
            "description": "Payroll Detail",
            "detail": "Full listing",
            "purpose": "Accuracy",
            "period": f"FY{prior_year}",
            "format": "Excel",
            "owner": "HR",
            "status": "in_progress",
            "auditor_comment": "Hardcopy only so far",
            "follow_up": True,
        },
        {
            "description": "Sales Listing",
            "detail": "By customer",
            "purpose": "Cut-off",
            "period": f"Dec {prior_year}",
            "format": "Excel",
            "owner": "Sales",
            "status": "done",
            "review_status": "under_review",
            "auditor_comment": "Need aging analysis",
            "follow_up": True,
        },
        {
            "description": "Customer Confirmation",
            "detail": "Top 20",
            "purpose": "Existence",
            "period": f"Dec {prior_year}",
            "format": "Word / Excel",
            "owner": "SL",
            "due_offset": 7,
            "status": "not_started",
            "follow_up": True,
        },
        {
            "description": "Supplier Confirmation",
            "detail": "Top 20",
            "purpose": "Existence",
            "period": f"Dec-{str(prior_year)[-2:]}",
            "format": "email copy",
            "owner": "Irene",
            "due_offset": 7,
            "status": "not_applicable",
            "follow_up": False,
        },
        {
            "description": "Inventory Listing",
            "detail": "All location",
            "purpose": "Existence",
            "period": f"31.12.{str(prior_year)[-2:]}",
            "format": "Excel",
            "owner": "Store",
            "due_offset": 1,
            "status": "partial",
            "review_status": "pending",
            "auditor_comment": "Qty not tally",
            "follow_up": True,
        },
        {
            "description": "Stock Count Sheet",
            "detail": "All counted sites",
            "purpose": "Cut-off",
            "period": f"Dec {prior_year}",
            "format": "xlsx",
            "owner": "Store",
            "status": "received",
            "review_status": "ok",
        },
        {
            "description": "Tax Computation",
            "detail": f"FY{str(prior_year)[-2:]}",
            "purpose": "Compliance",
            "period": str(prior_year),
            "format": "PDF",
            "owner": "Acc",
            "status": "not_started",
            "follow_up": True,
        },
        {
            "description": "GST / SST Report",
            "detail": f"Jan - Dec {str(prior_year)[-2:]}",
            "purpose": "Compliance",
            "period": f"Jan-Dec {str(prior_year)[-2:]}",
            "format": "Excel / PDF",
            "owner": "Acc",
            "due_offset": 1,
            "status": "done",
            "review_status": "ok",
        },
        {
            "description": "Journal Entry Listing",
            "detail": "Manual and system journals",
            "purpose": "Vouching",
            "period": f"FY{prior_year}",
            "format": "Excel",
            "owner": "Acc",
            "status": "partial",
            "review_status": "pending",
            "auditor_comment": "Need preparer / approver columns",
            "follow_up": True,
            "updated": True,
        },
        {
            "description": "Expense Claim Listing",
            "detail": "Claims with receipt availability",
            "purpose": "Completeness",
            "period": f"FY{prior_year}",
            "format": "xlsx / csv",
            "owner": "HR",
            "due_offset": 2,
            "status": "in_progress",
            "auditor_comment": "Receipt support still pending",
            "follow_up": True,
        },
        {
            "description": "Related Party Listing",
            "detail": "Please include all related parties",
            "purpose": "Disclosure",
            "period": f"Dec {prior_year}",
            "format": "Excel",
            "owner": "SL",
            "due_offset": 7,
            "status": "not_started",
            "follow_up": True,
        },
        {
            "description": "Minutes of Meeting",
            "detail": "AGM / BOD",
            "purpose": "Existence",
            "period": f"FY{str(prior_year)[-2:]}",
            "format": "PDF",
            "owner": "Admin",
            "status": "received",
            "review_status": "pending",
            "auditor_comment": "Blurry scan",
            "follow_up": True,
        },
        {
            "description": "Subsequent Events Request",
            "detail": "Any events after YE",
            "purpose": "Disclosure",
            "period": f"after 31.12.{str(prior_year)[-2:]}",
            "format": "Word",
            "owner": "SL",
            "due_offset": 5,
            "status": "not_started",
            "follow_up": True,
        },
    )
