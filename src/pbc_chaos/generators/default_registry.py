"""Factory for the default generator registry."""

from pbc_chaos.generators.placeholders import (
    APAgingGenerator,
    ARAgingGenerator,
    BankReconciliationGenerator,
    CashFlowSummaryGenerator,
    CommissionStatementGenerator,
    CustomerConfirmationListGenerator,
    ExpenseClaimListingGenerator,
    FixedAssetRegisterGenerator,
    GeneralLedgerGenerator,
    InsuranceProductionReportGenerator,
    InventoryListingGenerator,
    JournalEntryListingGenerator,
    PayrollDetailGenerator,
    PayrollSummaryGenerator,
    SSTGSTReportGenerator,
    SupplierConfirmationListGenerator,
    TaxComputationGenerator,
    TrialBalanceGenerator,
)
from pbc_chaos.generators.registry import DocumentGeneratorRegistry


def build_default_registry() -> DocumentGeneratorRegistry:
    registry = DocumentGeneratorRegistry()
    for generator in (
        TrialBalanceGenerator(),
        GeneralLedgerGenerator(),
        APAgingGenerator(),
        ARAgingGenerator(),
        BankReconciliationGenerator(),
        PayrollSummaryGenerator(),
        PayrollDetailGenerator(),
        FixedAssetRegisterGenerator(),
        InventoryListingGenerator(),
        TaxComputationGenerator(),
        SSTGSTReportGenerator(),
        CommissionStatementGenerator(),
        InsuranceProductionReportGenerator(),
        CustomerConfirmationListGenerator(),
        SupplierConfirmationListGenerator(),
        CashFlowSummaryGenerator(),
        JournalEntryListingGenerator(),
        ExpenseClaimListingGenerator(),
    ):
        registry.register(generator)
    return registry

