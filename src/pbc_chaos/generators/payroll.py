"""Clean Payroll Summary generator."""

from __future__ import annotations

from random import Random

import pandas as pd

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators._finance_seed import DEPARTMENTS, base_common, month_end, money
from pbc_chaos.generators.base import BaseFinancialDocumentGenerator, CompanyProfile, FinancialPeriod


class PayrollSummaryGenerator(BaseFinancialDocumentGenerator):
    """Generate payroll summaries by pay run and department."""

    document_type = DocumentType.PAYROLL_SUMMARY

    def build_dataframe(
        self,
        company: CompanyProfile,
        period: FinancialPeriod,
        rng: Random,
    ) -> pd.DataFrame:
        rows = []
        common = base_common(company, period)
        for month in range(1, 13):
            period_end = month_end(period, month)
            period_start = period_end.replace(day=1)
            for department in DEPARTMENTS[:5]:
                employee_count = rng.randint(4, 35)
                basic = money(rng, employee_count * 2_400, employee_count * 7_500)
                overtime = round(basic * rng.uniform(0.00, 0.06), 2)
                allowance = round(basic * rng.uniform(0.02, 0.12), 2)
                bonus = round(basic * rng.choice([0.0, 0.0, 0.08, 0.15]), 2)
                gross = round(basic + overtime + allowance + bonus, 2)
                employee_deductions = round(gross * rng.uniform(0.08, 0.16), 2)
                employer_contributions = round(gross * rng.uniform(0.10, 0.14), 2)
                tax = round(gross * rng.uniform(0.03, 0.09), 2)
                net = round(gross - employee_deductions - tax, 2)
                rows.append(
                    {
                        **common,
                        "pay_run_id": f"PAY{period.financial_year}{month:02d}",
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
        return pd.DataFrame(rows)

