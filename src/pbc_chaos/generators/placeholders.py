"""Placeholder classes for required document generators."""

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import BaseDocumentGenerator


class TrialBalanceGenerator(BaseDocumentGenerator):
    document_type = DocumentType.TRIAL_BALANCE


class GeneralLedgerGenerator(BaseDocumentGenerator):
    document_type = DocumentType.GENERAL_LEDGER


class APAgingGenerator(BaseDocumentGenerator):
    document_type = DocumentType.AP_AGING


class ARAgingGenerator(BaseDocumentGenerator):
    document_type = DocumentType.AR_AGING


class BankReconciliationGenerator(BaseDocumentGenerator):
    document_type = DocumentType.BANK_RECONCILIATION


class PayrollSummaryGenerator(BaseDocumentGenerator):
    document_type = DocumentType.PAYROLL_SUMMARY


class PayrollDetailGenerator(BaseDocumentGenerator):
    document_type = DocumentType.PAYROLL_DETAIL


class FixedAssetRegisterGenerator(BaseDocumentGenerator):
    document_type = DocumentType.FIXED_ASSET_REGISTER


class InventoryListingGenerator(BaseDocumentGenerator):
    document_type = DocumentType.INVENTORY_LISTING


class TaxComputationGenerator(BaseDocumentGenerator):
    document_type = DocumentType.TAX_COMPUTATION


class SSTGSTReportGenerator(BaseDocumentGenerator):
    document_type = DocumentType.SST_GST_REPORT


class CommissionStatementGenerator(BaseDocumentGenerator):
    document_type = DocumentType.COMMISSION_STATEMENT


class InsuranceProductionReportGenerator(BaseDocumentGenerator):
    document_type = DocumentType.INSURANCE_PRODUCTION_REPORT


class CustomerConfirmationListGenerator(BaseDocumentGenerator):
    document_type = DocumentType.CUSTOMER_CONFIRMATION_LIST


class SupplierConfirmationListGenerator(BaseDocumentGenerator):
    document_type = DocumentType.SUPPLIER_CONFIRMATION_LIST


class CashFlowSummaryGenerator(BaseDocumentGenerator):
    document_type = DocumentType.CASH_FLOW_SUMMARY


class JournalEntryListingGenerator(BaseDocumentGenerator):
    document_type = DocumentType.JOURNAL_ENTRY_LISTING


class ExpenseClaimListingGenerator(BaseDocumentGenerator):
    document_type = DocumentType.EXPENSE_CLAIM_LISTING

