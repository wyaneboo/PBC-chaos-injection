"""Financial model builder contract."""

from __future__ import annotations

from typing import Protocol

from pbc_chaos.core.context import ClientContext
from pbc_chaos.financial_model.domain import CanonicalDataset


class FinancialModelBuilder(Protocol):
    """Build clean canonical accounting data for a client/year."""

    def build(self, context: ClientContext) -> CanonicalDataset:
        """Return clean financial source data for downstream generators."""
        ...


class SyntheticFinancialModelBuilder:
    """Default canonical data builder placeholder."""

    def build(self, context: ClientContext) -> CanonicalDataset:
        raise NotImplementedError("Canonical financial data generation is not implemented yet.")

