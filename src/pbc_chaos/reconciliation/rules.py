"""Context-aware generators and relationship rule definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from random import Random
from typing import Iterable

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import (
    ACCOUNT_MASTER,
    CUSTOMERS,
    DEPARTMENTS,
    EMPLOYEES,
    VENDORS,
    aging_bucket,
    base_common,
    bucket_amounts,
    customer_id,
    employee_id,
    month_end,
    random_date,
    vendor_id,
)
from pbc_chaos.generators.base import GeneratedDocument
from pbc_chaos.reconciliation.context import ReconciliationContext
from pbc_chaos.reconciliation.discrepancies import DiscrepancyReason


@dataclass(frozen=True)
class ReconciliationRule:
    """Description of a supported cross-document reconciliation."""

    name: str
    source_document: DocumentType
    target_document: DocumentType
    source_field: str
    target_field: str
    description: str


DEFAULT_RECONCILIATION_RULES: tuple[ReconciliationRule, ...] = (
    ReconciliationRule(
        "trial_balance_cash_to_bank_reconciliation",
        DocumentType.TRIAL_BALANCE,
        DocumentType.BANK_RECONCILIATION,
        "closing_balance",
        "book_balance",
        "TB cash should roughly match the bank reconciliation closing book balance.",
    ),
    ReconciliationRule(
        "general_ledger_to_trial_balance",
        DocumentType.GENERAL_LEDGER,
        DocumentType.TRIAL_BALANCE,
        "amount_signed",
        "closing_balance",
        "GL account totals should roll up to TB balances.",
    ),
    ReconciliationRule(
        "ap_aging_to_trial_balance",
        DocumentType.AP_AGING,
        DocumentType.TRIAL_BALANCE,
        "outstanding_amount",
        "closing_balance",
        "AP aging should match the AP control account in TB.",
    ),
    ReconciliationRule(
        "ar_aging_to_trial_balance",
        DocumentType.AR_AGING,
        DocumentType.TRIAL_BALANCE,
        "outstanding_amount",
        "closing_balance",
        "AR aging should match the AR control account in TB.",
    ),
    ReconciliationRule(
        "payroll_detail_to_summary",
        DocumentType.PAYROLL_DETAIL,
        DocumentType.PAYROLL_SUMMARY,
        "gross_pay",
        "gross_pay",
        "Payroll detail should aggregate to payroll summary.",
    ),
    ReconciliationRule(
        "fixed_asset_register_to_trial_balance",
        DocumentType.FIXED_ASSET_REGISTER,
        DocumentType.TRIAL_BALANCE,
        "cost",
        "closing_balance",
        "Fixed asset register cost should reconcile to PPE in TB.",
    ),
    ReconciliationRule(
        "inventory_listing_to_trial_balance",
        DocumentType.INVENTORY_LISTING,
        DocumentType.TRIAL_BALANCE,
        "total_cost",
        "closing_balance",
        "Inventory listing value should reconcile to inventory in TB.",
    ),
    ReconciliationRule(
        "journal_entry_listing_to_general_ledger",
        DocumentType.JOURNAL_ENTRY_LISTING,
        DocumentType.GENERAL_LEDGER,
        "amount_signed",
        "amount_signed",
        "Journal entry listing should explain selected GL movements.",
    ),
)


ACCOUNT_BY_CODE = {account["code"]: account for account in ACCOUNT_MASTER}
RETAINED_EARNINGS_CODE = "3100"


def generate_trial_balance(context: ReconciliationContext) -> GeneratedDocument:
    """Generate a TB with shared control account balances for later documents."""

    rng = context.rng("trial_balance")
    balances = _control_balances(context)
    rows = []
    common = base_common(context.company, context.period)
    for account in ACCOUNT_MASTER:
        closing_balance = round(float(balances[account["code"]]), 2)
        rows.append(
            {
                **common,
                "account_code": account["code"],
                "account_name": account["name"],
                "account_category": account["category"],
                "normal_balance": account["normal"],
                "opening_debit": 0.0,
                "opening_credit": 0.0,
                "period_debit": closing_balance if closing_balance > 0 else 0.0,
                "period_credit": abs(closing_balance) if closing_balance < 0 else 0.0,
                "closing_debit": closing_balance if closing_balance > 0 else 0.0,
                "closing_credit": abs(closing_balance) if closing_balance < 0 else 0.0,
                "closing_balance": closing_balance,
                "comparative_balance": round(closing_balance * rng.uniform(0.82, 1.12), 2),
                "adjustment_amount": 0.0,
                "final_balance": closing_balance,
                "remarks": "",
            }
        )
    return context.make_document(DocumentType.TRIAL_BALANCE, pd.DataFrame(rows))


def generate_general_ledger(context: ReconciliationContext) -> GeneratedDocument:
    """Generate GL lines that mostly roll up to the TB, with controlled extras."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)

    rng = context.rng("general_ledger")
    common = base_common(context.company, context.period)
    tb = context.get_dataframe(DocumentType.TRIAL_BALANCE)
    rows: list[dict[str, object]] = []
    journal_no = 1
    journal_entry_candidate_ids: list[str] = []

    for tb_row in tb.itertuples(index=False):
        account_code = tb_row.account_code
        if account_code == RETAINED_EARNINGS_CODE:
            continue
        amount = round(float(tb_row.closing_balance), 2)
        if amount == 0:
            continue
        posting_date = random_date(rng, context.period)
        journal_id = f"GLREC{journal_no:05d}"
        module = _source_module_for_account(account_code)
        description = f"{module} movement supporting TB {account_code}"
        rows.extend(
            _balanced_gl_lines(
                common,
                rng,
                journal_id=journal_id,
                posting_date=posting_date,
                debit_code=account_code if amount > 0 else RETAINED_EARNINGS_CODE,
                credit_code=RETAINED_EARNINGS_CODE if amount > 0 else account_code,
                amount=abs(amount),
                source_module=module,
                description=description,
                entry_no=journal_no,
            )
        )
        journal_no += 1

    duplicate_amount = abs(
        context.controlled_difference(
            "gl_duplicate_payroll",
            context.account_balance("6000"),
            cap=context.materiality_threshold * 0.45,
            minimum=75.0,
        )
    )
    duplicate_journal_id = f"GLDUP{journal_no:05d}"
    rows.extend(
        _balanced_gl_lines(
            common,
            rng,
            journal_id=duplicate_journal_id,
            posting_date=context.period.end_date,
            debit_code="6000",
            credit_code="1000",
            amount=duplicate_amount,
            source_module="Payroll",
            description="Duplicated payroll posting retained in GL extract",
            entry_no=journal_no,
            remarks="Intentional reconciliation discrepancy: duplicated transaction",
        )
    )
    journal_entry_candidate_ids.append(duplicate_journal_id)
    context.log_discrepancy(
        source_document=DocumentType.GENERAL_LEDGER,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="account_code=6000.amount_signed",
        expected_value=context.account_balance("6000"),
        actual_value=context.account_balance("6000") + duplicate_amount,
        reason=DiscrepancyReason.DUPLICATED_TRANSACTION,
        relationship_name="general_ledger_to_trial_balance",
        details={"journal_id": duplicate_journal_id},
    )
    context.log_discrepancy(
        source_document=DocumentType.GENERAL_LEDGER,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="account_code=1000.amount_signed",
        expected_value=context.account_balance("1000"),
        actual_value=context.account_balance("1000") - duplicate_amount,
        reason=DiscrepancyReason.DUPLICATED_TRANSACTION,
        relationship_name="general_ledger_to_trial_balance",
        details={"journal_id": duplicate_journal_id},
    )
    journal_no += 1

    wrong_period_amount = abs(
        context.controlled_difference(
            "gl_wrong_period_bank_charge",
            context.account_balance("6400"),
            cap=context.materiality_threshold * 0.25,
            minimum=40.0,
        )
    )
    wrong_period_date = context.period.end_date + timedelta(days=1)
    wrong_period_journal_id = f"GLWP{journal_no:05d}"
    rows.extend(
        _balanced_gl_lines(
            common,
            rng,
            journal_id=wrong_period_journal_id,
            posting_date=wrong_period_date,
            debit_code="6400",
            credit_code="1000",
            amount=wrong_period_amount,
            source_module="Bank",
            description="Bank charge posted in wrong accounting period",
            entry_no=journal_no,
            remarks="Intentional reconciliation discrepancy: wrong-period transaction",
        )
    )
    journal_entry_candidate_ids.append(wrong_period_journal_id)
    context.log_discrepancy(
        source_document=DocumentType.GENERAL_LEDGER,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="account_code=6400.amount_signed",
        expected_value=context.account_balance("6400"),
        actual_value=context.account_balance("6400") + wrong_period_amount,
        reason=DiscrepancyReason.WRONG_PERIOD_TRANSACTION,
        relationship_name="general_ledger_to_trial_balance",
        details={"journal_id": wrong_period_journal_id, "posting_date": wrong_period_date.isoformat()},
    )
    context.log_discrepancy(
        source_document=DocumentType.GENERAL_LEDGER,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="account_code=1000.amount_signed",
        expected_value=context.account_balance("1000"),
        actual_value=context.account_balance("1000") - duplicate_amount - wrong_period_amount,
        reason=DiscrepancyReason.WRONG_PERIOD_TRANSACTION,
        relationship_name="general_ledger_to_trial_balance",
        details={"journal_id": wrong_period_journal_id, "posting_date": wrong_period_date.isoformat()},
    )

    data = pd.DataFrame(rows)
    context.state["journal_entry_candidate_ids"] = tuple(journal_entry_candidate_ids)
    return context.make_document(DocumentType.GENERAL_LEDGER, data)


def generate_bank_reconciliation(context: ReconciliationContext) -> GeneratedDocument:
    """Generate a bank reconciliation tied to TB cash with a timing difference."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)

    rng = context.rng("bank_reconciliation")
    common = base_common(context.company, context.period)
    cash_balance = context.account_balance("1000")
    timing_difference = context.controlled_difference(
        "bank_cash_timing",
        cash_balance,
        cap=context.max_bank_recon_difference_amount,
        minimum=30.0,
    )
    book_balance = round(cash_balance + timing_difference, 2)
    deposits = _split_amount(abs(book_balance) * rng.uniform(0.08, 0.18), 4, rng)
    cheques = _split_amount(abs(book_balance) * rng.uniform(0.05, 0.15), 5, rng)
    bank_charges = round(rng.uniform(100, 1_500), 2)
    interest = round(rng.uniform(50, 800), 2)
    statement_balance = round(book_balance - sum(deposits) + sum(cheques) + bank_charges - interest, 2)
    account = {
        "bank_account_id": "BANK001",
        "bank_name": "Maybank",
        "bank_account_number": "****-****-3488",
    }
    rows = [
        {
            **common,
            **account,
            "recon_item_id": "BR-BOOK",
            "recon_item_type": "book_balance",
            "transaction_date": context.period.end_date,
            "reference": "GL-CASH",
            "description": "Balance per cash book",
            "bank_amount": None,
            "book_amount": book_balance,
            "difference_amount": 0.0,
            "statement_balance": None,
            "book_balance": book_balance,
            "adjusted_bank_balance": None,
            "adjusted_book_balance": book_balance,
            "variance": 0.0,
            "cleared_flag": True,
            "matched_gl_entry_id": None,
            "matched_bank_reference": None,
            "remarks": "Timing difference retained for reconciliation testing",
        },
        {
            **common,
            **account,
            "recon_item_id": "BR-STMT",
            "recon_item_type": "statement_balance",
            "transaction_date": context.period.end_date,
            "reference": "BANK-STMT",
            "description": "Balance per bank statement",
            "bank_amount": statement_balance,
            "book_amount": None,
            "difference_amount": 0.0,
            "statement_balance": statement_balance,
            "book_balance": None,
            "adjusted_bank_balance": statement_balance,
            "adjusted_book_balance": None,
            "variance": 0.0,
            "cleared_flag": True,
            "matched_gl_entry_id": None,
            "matched_bank_reference": None,
            "remarks": "",
        },
    ]
    item_no = 1
    for amount in deposits:
        rows.append(_bank_recon_item(common, account, context, rng, item_no, "deposit_in_transit", amount))
        item_no += 1
    for amount in cheques:
        rows.append(_bank_recon_item(common, account, context, rng, item_no, "outstanding_cheque", -amount))
        item_no += 1
    rows.append(_bank_recon_item(common, account, context, rng, item_no, "bank_charge", -bank_charges))
    rows.append(_bank_recon_item(common, account, context, rng, item_no + 1, "interest", interest))

    context.log_discrepancy(
        source_document=DocumentType.TRIAL_BALANCE,
        target_document=DocumentType.BANK_RECONCILIATION,
        affected_field="book_balance",
        expected_value=cash_balance,
        actual_value=book_balance,
        reason=DiscrepancyReason.TIMING_DIFFERENCE,
        relationship_name="trial_balance_cash_to_bank_reconciliation",
    )
    return context.make_document(DocumentType.BANK_RECONCILIATION, pd.DataFrame(rows))


def generate_ap_aging(context: ReconciliationContext) -> GeneratedDocument:
    """Generate AP aging that nearly ties to the TB AP control account."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)
    expected = abs(context.account_balance("2000"))
    difference = -abs(
        context.controlled_difference(
            "ap_missing_invoice",
            expected,
            cap=context.materiality_threshold * 0.7,
            minimum=125.0,
        )
    )
    actual = round(expected + difference, 2)
    rows = _subledger_aging_rows(
        context,
        rng=context.rng("ap_aging"),
        total=actual,
        count=45,
        counterparties=VENDORS,
        id_builder=vendor_id,
        id_field="vendor_id",
        name_field="vendor_name",
        number_field="invoice_number",
        number_prefix="SUP",
        terms_field="payment_terms",
        terms_label="Net",
        po_field="purchase_order_number",
    )
    context.log_discrepancy(
        source_document=DocumentType.AP_AGING,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="outstanding_amount",
        expected_value=expected,
        actual_value=actual,
        reason=DiscrepancyReason.MISSING_TRANSACTION,
        relationship_name="ap_aging_to_trial_balance",
        details={"control_account": "2000"},
    )
    return context.make_document(DocumentType.AP_AGING, pd.DataFrame(rows))


def generate_ar_aging(context: ReconciliationContext) -> GeneratedDocument:
    """Generate AR aging that includes a small rounding difference."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)
    rng = context.rng("ar_rounding")
    expected = context.account_balance("1100")
    rounding_difference = rng.choice([-0.07, -0.03, 0.04, 0.08])
    actual = round(expected + rounding_difference, 2)
    rows = _subledger_aging_rows(
        context,
        rng=context.rng("ar_aging"),
        total=actual,
        count=50,
        counterparties=CUSTOMERS,
        id_builder=customer_id,
        id_field="customer_id",
        name_field="customer_name",
        number_field="invoice_number",
        number_prefix="INV",
        terms_field="credit_terms",
        terms_label="Net",
        extra_fields=("salesperson", "collection_status"),
    )
    context.log_discrepancy(
        source_document=DocumentType.AR_AGING,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="outstanding_amount",
        expected_value=expected,
        actual_value=actual,
        reason=DiscrepancyReason.ROUNDING_DIFFERENCE,
        relationship_name="ar_aging_to_trial_balance",
        details={"control_account": "1100"},
    )
    return context.make_document(DocumentType.AR_AGING, pd.DataFrame(rows))


def generate_payroll_summary(context: ReconciliationContext) -> GeneratedDocument:
    """Generate payroll summaries using TB payroll expense as the gross-pay anchor."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)
    rng = context.rng("payroll_summary")
    common = base_common(context.company, context.period)
    total_gross = max(250_000.0, context.account_balance("6000"))
    departments = DEPARTMENTS[:5]
    line_count = 12 * len(departments)
    gross_values = _split_amount(total_gross, line_count, rng)
    rows = []
    value_index = 0
    for month in range(1, 13):
        period_end = month_end(context.period, month)
        period_start = period_end.replace(day=1)
        for department in departments:
            gross = gross_values[value_index]
            value_index += 1
            employee_count = rng.randint(4, 12)
            overtime = round(gross * rng.uniform(0.00, 0.04), 2)
            allowance = round(gross * rng.uniform(0.03, 0.09), 2)
            bonus = round(gross * rng.choice([0.0, 0.0, 0.05, 0.10]), 2)
            basic = round(gross - overtime - allowance - bonus, 2)
            employee_deductions = round(gross * rng.uniform(0.08, 0.14), 2)
            employer_contributions = round(gross * rng.uniform(0.10, 0.13), 2)
            tax = round(gross * rng.uniform(0.03, 0.08), 2)
            net = round(gross - employee_deductions - tax, 2)
            rows.append(
                {
                    **common,
                    "pay_run_id": f"PAY{context.period.financial_year}{month:02d}",
                    "pay_period_start": period_start,
                    "pay_period_end": period_end,
                    "payment_date": period_end,
                    "department": department,
                    "employee_count": employee_count,
                    "basic_salary": basic,
                    "overtime_amount": overtime,
                    "allowance_amount": allowance,
                    "bonus_amount": bonus,
                    "gross_pay": gross,
                    "employee_deductions": employee_deductions,
                    "employer_contributions": employer_contributions,
                    "tax_withheld": tax,
                    "net_pay": net,
                    "remarks": "",
                }
            )
    return context.make_document(DocumentType.PAYROLL_SUMMARY, pd.DataFrame(rows))


def generate_payroll_detail(context: ReconciliationContext) -> GeneratedDocument:
    """Generate payroll detail rows that aggregate near, but not exactly to, summary."""

    if not context.has_document(DocumentType.PAYROLL_SUMMARY):
        generate_payroll_summary(context)

    rng = context.rng("payroll_detail")
    common = base_common(context.company, context.period)
    summary = context.get_dataframe(DocumentType.PAYROLL_SUMMARY)
    discrepancy_target = summary.iloc[min(4, len(summary) - 1)]
    missing_amount = abs(
        context.controlled_difference(
            "payroll_missing_employee",
            float(discrepancy_target["gross_pay"]),
            cap=context.materiality_threshold * 0.55,
            minimum=90.0,
        )
    )
    rows: list[dict[str, object]] = []
    employee_counter = 1
    for summary_row in summary.itertuples(index=False):
        employee_count = int(summary_row.employee_count)
        gross_total = float(summary_row.gross_pay)
        if (
            summary_row.pay_run_id == discrepancy_target["pay_run_id"]
            and summary_row.department == discrepancy_target["department"]
        ):
            gross_total = round(gross_total - missing_amount, 2)
        gross_values = _split_amount(gross_total, employee_count, rng)
        for employee_number, gross in enumerate(gross_values, start=1):
            basic = round(gross * rng.uniform(0.78, 0.90), 2)
            overtime = round(gross * rng.uniform(0.00, 0.03), 2)
            allowance = round(gross * rng.uniform(0.02, 0.08), 2)
            bonus = round(max(0.0, gross - basic - overtime - allowance), 2)
            epf_employee = round(gross * 0.11, 2)
            socso_employee = round(gross * 0.005, 2)
            eis_employee = round(gross * 0.002, 2)
            pcb_tax = round(gross * rng.uniform(0.02, 0.06), 2)
            other_deductions = round(gross * rng.choice([0.0, 0.0, 0.005]), 2)
            net_pay = round(
                gross
                - epf_employee
                - socso_employee
                - eis_employee
                - pcb_tax
                - other_deductions,
                2,
            )
            rows.append(
                {
                    **common,
                    "pay_run_id": summary_row.pay_run_id,
                    "employee_id": employee_id((employee_counter - 1) % len(EMPLOYEES)),
                    "employee_name": EMPLOYEES[(employee_counter - 1) % len(EMPLOYEES)],
                    "department": summary_row.department,
                    "position": rng.choice(["Executive", "Analyst", "Supervisor", "Manager"]),
                    "pay_period_start": summary_row.pay_period_start,
                    "pay_period_end": summary_row.pay_period_end,
                    "payment_date": summary_row.payment_date,
                    "basic_salary": basic,
                    "overtime_amount": overtime,
                    "allowance_amount": allowance,
                    "bonus_amount": bonus,
                    "commission_amount": 0.0,
                    "gross_pay": gross,
                    "epf_employee": epf_employee,
                    "socso_employee": socso_employee,
                    "eis_employee": eis_employee,
                    "pcb_tax": pcb_tax,
                    "other_deductions": other_deductions,
                    "net_pay": net_pay,
                    "epf_employer": round(gross * 0.13, 2),
                    "socso_employer": round(gross * 0.018, 2),
                    "eis_employer": round(gross * 0.002, 2),
                    "payment_method": "bank_transfer",
                    "bank_account_masked": f"****-****-{rng.randint(1000, 9999)}",
                    "join_date": context.period.start_date - timedelta(days=rng.randint(30, 2_000)),
                    "termination_date": None,
                    "remarks": "" if employee_number != employee_count else "Detail generated from summary split",
                }
            )
            employee_counter += 1

    expected = round(float(summary["gross_pay"].sum()), 2)
    actual = round(sum(float(row["gross_pay"]) for row in rows), 2)
    context.log_discrepancy(
        source_document=DocumentType.PAYROLL_DETAIL,
        target_document=DocumentType.PAYROLL_SUMMARY,
        affected_field="gross_pay",
        expected_value=expected,
        actual_value=actual,
        reason=DiscrepancyReason.MISSING_TRANSACTION,
        relationship_name="payroll_detail_to_summary",
        details={
            "pay_run_id": discrepancy_target["pay_run_id"],
            "department": discrepancy_target["department"],
        },
    )
    return context.make_document(DocumentType.PAYROLL_DETAIL, pd.DataFrame(rows))


def generate_fixed_asset_register(context: ReconciliationContext) -> GeneratedDocument:
    """Generate fixed assets that nearly reconcile to TB PPE and accumulated depreciation."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)

    rng = context.rng("fixed_asset_register")
    common = base_common(context.company, context.period)
    ppe_expected = context.account_balance("1500")
    acc_dep_expected = abs(context.account_balance("1590"))
    timing_difference = context.controlled_difference(
        "fa_timing",
        ppe_expected,
        cap=context.materiality_threshold * 0.6,
        minimum=150.0,
    )
    ppe_actual = round(ppe_expected + timing_difference, 2)
    costs = _split_amount(ppe_actual, 30, rng)
    accumulated_values = _split_amount(acc_dep_expected, 30, rng)
    classes = (
        ("Computer equipment", 36),
        ("Office furniture", 60),
        ("Plant and machinery", 84),
        ("Motor vehicles", 60),
        ("Leasehold improvements", 72),
    )
    rows = []
    for index, (cost, accumulated) in enumerate(zip(costs, accumulated_values, strict=True), start=1):
        asset_class, life_months = rng.choice(classes)
        acquired_days = rng.randint(60, 1_800)
        acquisition_date = context.period.end_date - timedelta(days=acquired_days)
        accumulated = min(cost, accumulated)
        current_dep = round(min(accumulated, cost / life_months * min(12, max(1, acquired_days // 30))), 2)
        opening_dep = round(max(0.0, accumulated - current_dep), 2)
        nbv = round(cost - accumulated, 2)
        rows.append(
            {
                **common,
                "asset_id": f"FA{index:05d}",
                "asset_class": asset_class,
                "asset_description": f"{asset_class} #{index:03d}",
                "acquisition_date": acquisition_date,
                "in_service_date": acquisition_date + timedelta(days=rng.randint(0, 20)),
                "supplier_name": rng.choice(VENDORS),
                "invoice_number": f"CAP-{context.period.financial_year}-{index:04d}",
                "location": rng.choice(["HQ", "Warehouse", "Branch A", "Branch B"]),
                "department": rng.choice(["Operations", "Sales", "IT", "Admin"]),
                "cost": cost,
                "additions": cost if acquisition_date.year == context.period.financial_year else 0.0,
                "disposals": 0.0,
                "depreciation_method": "Straight line",
                "useful_life_months": life_months,
                "residual_value": 0.0,
                "accumulated_depreciation_opening": opening_dep,
                "depreciation_current_year": current_dep,
                "accumulated_depreciation_closing": accumulated,
                "net_book_value": nbv,
                "disposal_date": None,
                "disposal_proceeds": 0.0,
                "gain_loss_on_disposal": 0.0,
                "status": "fully_depreciated" if nbv <= 0 else "active",
                "remarks": "",
            }
        )
    context.log_discrepancy(
        source_document=DocumentType.FIXED_ASSET_REGISTER,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="cost",
        expected_value=ppe_expected,
        actual_value=ppe_actual,
        reason=DiscrepancyReason.TIMING_DIFFERENCE,
        relationship_name="fixed_asset_register_to_trial_balance",
        details={"control_account": "1500"},
    )
    return context.make_document(DocumentType.FIXED_ASSET_REGISTER, pd.DataFrame(rows))


def generate_inventory_listing(context: ReconciliationContext) -> GeneratedDocument:
    """Generate inventory listing values near the TB inventory control account."""

    if not context.has_document(DocumentType.TRIAL_BALANCE):
        generate_trial_balance(context)

    rng = context.rng("inventory_listing")
    common = base_common(context.company, context.period)
    expected = context.account_balance("1200")
    duplicated_amount = abs(
        context.controlled_difference(
            "inventory_duplicate_lot",
            expected,
            cap=context.materiality_threshold * 0.6,
            minimum=100.0,
        )
    )
    actual = round(expected + duplicated_amount, 2)
    totals = _split_amount(actual, 65, rng)
    categories = ("Raw materials", "Finished goods", "Packaging", "Spare parts")
    rows = []
    for index, total_cost in enumerate(totals, start=1):
        quantity = round(rng.uniform(5, 2_500), 2)
        unit_cost = round(total_cost / quantity, 2) if quantity else 0.0
        physical_count = round(quantity + rng.choice([0, 0, 0, rng.uniform(-5, 5)]), 2)
        variance_qty = round(physical_count - quantity, 2)
        obsolete = rng.random() < 0.06
        write_down = round(total_cost * rng.uniform(0.05, 0.20), 2) if obsolete else 0.0
        rows.append(
            {
                **common,
                "item_id": f"ITEM{index:05d}",
                "sku": f"SKU-{rng.randint(10000, 99999)}",
                "item_description": f"{rng.choice(categories)} item {index:03d}",
                "category": rng.choice(categories),
                "warehouse": rng.choice(["Main WH", "Raw Mat WH", "3PL", "Branch WH"]),
                "location": rng.choice(["A01", "A02", "B12", "C05", "D09"]),
                "lot_serial_number": f"LOT{rng.randint(1000, 9999)}",
                "quantity_on_hand": quantity,
                "uom": rng.choice(["EA", "KG", "BOX", "M"]),
                "unit_cost": unit_cost,
                "total_cost": total_cost,
                "valuation_method": rng.choice(["fifo", "weighted_average", "standard_cost"]),
                "last_movement_date": context.period.end_date - timedelta(days=rng.randint(1, 180)),
                "obsolete_flag": obsolete,
                "write_down_amount": write_down,
                "physical_count_quantity": physical_count,
                "variance_quantity": variance_qty,
                "variance_amount": round(variance_qty * unit_cost, 2),
                "remarks": "",
            }
        )
    context.log_discrepancy(
        source_document=DocumentType.INVENTORY_LISTING,
        target_document=DocumentType.TRIAL_BALANCE,
        affected_field="total_cost",
        expected_value=expected,
        actual_value=actual,
        reason=DiscrepancyReason.DUPLICATED_TRANSACTION,
        relationship_name="inventory_listing_to_trial_balance",
        details={"control_account": "1200"},
    )
    return context.make_document(DocumentType.INVENTORY_LISTING, pd.DataFrame(rows))


def generate_journal_entry_listing(context: ReconciliationContext) -> GeneratedDocument:
    """Generate a JE listing that explains selected GL movements, with omissions."""

    if not context.has_document(DocumentType.GENERAL_LEDGER):
        generate_general_ledger(context)

    rng = context.rng("journal_entry_listing")
    common = base_common(context.company, context.period)
    gl = context.get_dataframe(DocumentType.GENERAL_LEDGER)
    candidate_ids = context.state.get("journal_entry_candidate_ids") or tuple(sorted(gl["journal_id"].unique())[:8])
    selected_ids = tuple(candidate_ids[: min(10, len(candidate_ids))])
    missing_id = selected_ids[0] if selected_ids else None
    selected = gl.loc[gl["journal_id"].isin(selected_ids)].copy()
    if missing_id:
        selected = selected.loc[selected["journal_id"] != missing_id]
    rows = []
    for row in selected.itertuples(index=False):
        rows.append(_journal_row_from_gl(common, rng, row))

    if selected_ids:
        source_rows = gl.loc[gl["journal_id"] == selected_ids[-1]]
        for row in source_rows.itertuples(index=False):
            wrong_period_row = _journal_row_from_gl(common, rng, row)
            wrong_period_date = context.period.end_date + timedelta(days=3)
            wrong_period_row["posting_date"] = wrong_period_date
            wrong_period_row["journal_date"] = wrong_period_date
            wrong_period_row["remarks"] = "Intentional reconciliation discrepancy: wrong-period JE"
            rows.append(wrong_period_row)
        amount = round(float(source_rows["amount_signed"].abs().sum()), 2)
        context.log_discrepancy(
            source_document=DocumentType.JOURNAL_ENTRY_LISTING,
            target_document=DocumentType.GENERAL_LEDGER,
            affected_field="posting_date",
            expected_value=0.0,
            actual_value=amount,
            reason=DiscrepancyReason.WRONG_PERIOD_TRANSACTION,
            relationship_name="journal_entry_listing_to_general_ledger",
            details={"journal_id": selected_ids[-1]},
        )

    if missing_id:
        expected = round(float(gl.loc[gl["journal_id"] == missing_id, "amount_signed"].abs().sum()), 2)
        context.log_discrepancy(
            source_document=DocumentType.JOURNAL_ENTRY_LISTING,
            target_document=DocumentType.GENERAL_LEDGER,
            affected_field="journal_id",
            expected_value=expected,
            actual_value=0.0,
            reason=DiscrepancyReason.MISSING_TRANSACTION,
            relationship_name="journal_entry_listing_to_general_ledger",
            details={"journal_id": missing_id},
        )
    context.state["journal_entry_selected_ids"] = selected_ids
    return context.make_document(DocumentType.JOURNAL_ENTRY_LISTING, pd.DataFrame(rows))


def _control_balances(context: ReconciliationContext) -> dict[str, float]:
    if "control_balances" in context.state:
        return context.state["control_balances"]

    rng = context.rng("control_balances")
    balances = {
        "1000": round(rng.uniform(240_000, 720_000), 2),
        "1100": round(rng.uniform(350_000, 1_150_000), 2),
        "1200": round(rng.uniform(280_000, 950_000), 2),
        "1300": round(rng.uniform(30_000, 170_000), 2),
        "1500": round(rng.uniform(900_000, 2_500_000), 2),
        "2000": -round(rng.uniform(280_000, 980_000), 2),
        "2100": -round(rng.uniform(80_000, 350_000), 2),
        "2200": -round(rng.uniform(60_000, 260_000), 2),
        "3000": -round(rng.uniform(500_000, 1_200_000), 2),
        "4000": -round(rng.uniform(900_000, 1_900_000), 2),
        "4100": -round(rng.uniform(250_000, 850_000), 2),
        "5000": round(rng.uniform(550_000, 1_450_000), 2),
        "6000": round(rng.uniform(850_000, 2_250_000), 2),
        "6100": round(rng.uniform(120_000, 420_000), 2),
        "6200": round(rng.uniform(45_000, 210_000), 2),
        "6300": round(rng.uniform(80_000, 260_000), 2),
        "6400": round(rng.uniform(4_000, 28_000), 2),
    }
    balances["1590"] = -round(balances["1500"] * rng.uniform(0.18, 0.42), 2)
    balances[RETAINED_EARNINGS_CODE] = round(-sum(balances.values()), 2)
    context.state["control_balances"] = balances
    return balances


def _split_amount(total: float, count: int, rng: Random) -> list[float]:
    """Split an amount into positive rounded parts that sum to total."""

    if count <= 0:
        return []
    total = round(float(total), 2)
    if count == 1:
        return [total]
    weights = [rng.uniform(0.5, 1.5) for _ in range(count)]
    weight_sum = sum(weights)
    values = [round(total * weight / weight_sum, 2) for weight in weights]
    values[-1] = round(total - sum(values[:-1]), 2)
    return values


def _source_module_for_account(account_code: str) -> str:
    if account_code == "1000":
        return "Bank"
    if account_code == "1100":
        return "AR"
    if account_code == "1200":
        return "Inventory"
    if account_code == "1500" or account_code == "1590" or account_code == "6300":
        return "Fixed Assets"
    if account_code == "2000":
        return "AP"
    if account_code == "2200" or account_code == "6000":
        return "Payroll"
    return "Year-end close"


def _balanced_gl_lines(
    common: dict[str, object],
    rng: Random,
    *,
    journal_id: str,
    posting_date,
    debit_code: str,
    credit_code: str,
    amount: float,
    source_module: str,
    description: str,
    entry_no: int,
    remarks: str = "",
) -> list[dict[str, object]]:
    period_label = posting_date.strftime("%Y-%m")
    reference = f"{source_module[:2].upper()}-{journal_id}"
    lines = []
    for line_number, account_code, debit, credit in (
        (1, debit_code, amount, 0.0),
        (2, credit_code, 0.0, amount),
    ):
        account = ACCOUNT_BY_CODE[account_code]
        lines.append(
            {
                **common,
                "entry_id": f"{journal_id}-{line_number}",
                "journal_id": journal_id,
                "line_number": line_number,
                "posting_date": posting_date,
                "document_date": posting_date,
                "period": period_label,
                "account_code": account_code,
                "account_name": account["name"],
                "account_category": account["category"],
                "debit": round(debit, 2),
                "credit": round(credit, 2),
                "amount_signed": round(debit - credit, 2),
                "counterparty_id": None,
                "counterparty_name": None,
                "counterparty_type": "other",
                "source_module": source_module,
                "document_number": reference,
                "reference": reference,
                "description": description,
                "cost_center": rng.choice(["CC100", "CC200", "CC300", None]),
                "department": rng.choice(["Finance", "Sales", "Operations", None]),
                "project_code": rng.choice(["PRJ-A", "PRJ-B", None]),
                "tax_code": rng.choice(["TX-0", "TX-6", None]),
                "created_by": rng.choice(["finance.user", "ap.clerk", "system"]),
                "posted_by": "finance.manager",
                "batch_id": f"B{posting_date.month:02d}{entry_no // 10:03d}",
                "reversal_flag": False,
                "remarks": remarks,
            }
        )
    return lines


def _bank_recon_item(common, account, context, rng, item_no, item_type, amount):
    return {
        **common,
        **account,
        "recon_item_id": f"BR-{item_no:03d}",
        "recon_item_type": item_type,
        "transaction_date": context.period.end_date - timedelta(days=rng.randint(1, 20)),
        "reference": f"BNK-{rng.randint(100000, 999999)}",
        "description": item_type.replace("_", " ").title(),
        "bank_amount": amount if item_type in {"bank_charge", "interest"} else None,
        "book_amount": None,
        "difference_amount": amount,
        "statement_balance": None,
        "book_balance": None,
        "adjusted_bank_balance": None,
        "adjusted_book_balance": None,
        "variance": 0.0,
        "cleared_flag": False,
        "matched_gl_entry_id": None,
        "matched_bank_reference": None,
        "remarks": "",
    }


def _subledger_aging_rows(
    context: ReconciliationContext,
    *,
    rng: Random,
    total: float,
    count: int,
    counterparties: Iterable[str],
    id_builder,
    id_field: str,
    name_field: str,
    number_field: str,
    number_prefix: str,
    terms_field: str,
    terms_label: str,
    po_field: str | None = None,
    extra_fields: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    rows = []
    common = base_common(context.company, context.period)
    amounts = _split_amount(total, count, rng)
    names = tuple(counterparties)
    for index, outstanding in enumerate(amounts):
        party_index = rng.randrange(len(names))
        days_old = rng.randint(0, 150)
        invoice_date = context.period.end_date - timedelta(days=days_old)
        terms = rng.choice((30, 45, 60))
        due_date = invoice_date + timedelta(days=terms)
        days_past_due = (context.period.end_date - due_date).days
        bucket = aging_bucket(days_past_due)
        original = round(outstanding * rng.uniform(1.05, 1.8), 2)
        row = {
            **common,
            id_field: id_builder(party_index),
            name_field: names[party_index],
            number_field: f"{number_prefix}-{context.period.financial_year}-{index + 1:05d}",
            "invoice_date": invoice_date,
            "due_date": due_date,
            "aging_date": context.period.end_date,
            "days_past_due": days_past_due,
            "aging_bucket": bucket,
            "original_amount": original,
            "outstanding_amount": outstanding,
            **bucket_amounts(outstanding, bucket),
            terms_field: f"{terms_label} {terms}",
            "disputed_flag": rng.random() < 0.06,
            "remarks": "",
        }
        if po_field:
            row[po_field] = f"PO-{rng.randint(10000, 99999)}"
            row["hold_flag"] = rng.random() < 0.08
        if "salesperson" in extra_fields:
            row["salesperson"] = rng.choice(["Lim", "Tan", "Rahman", "Wong"])
        if "collection_status" in extra_fields:
            row["collection_status"] = rng.choice(
                ["Not due", "Reminder sent", "Promise to pay", "Escalated", "Disputed"]
            )
        rows.append(row)
    return rows


def _journal_row_from_gl(common: dict[str, object], rng: Random, row) -> dict[str, object]:
    return {
        **common,
        "journal_id": row.journal_id,
        "line_number": row.line_number,
        "posting_date": row.posting_date,
        "journal_date": row.posting_date,
        "journal_type": row.source_module,
        "account_code": row.account_code,
        "account_name": row.account_name,
        "debit": row.debit,
        "credit": row.credit,
        "amount_signed": row.amount_signed,
        "description": row.description,
        "reference": row.reference,
        "prepared_by": rng.choice(["Aisha", "Daniel", "Finance Ops"]),
        "approved_by": rng.choice(["Controller", "Finance Manager"]),
        "approval_date": row.posting_date,
        "manual_entry_flag": row.source_module in {"Payroll", "Inventory", "Year-end close"},
        "recurring_flag": row.source_module == "Fixed Assets",
        "adjustment_flag": row.source_module != "Bank",
        "source_module": "Manual Journal",
        "cost_center": row.cost_center,
        "department": row.department,
        "remarks": "",
    }
