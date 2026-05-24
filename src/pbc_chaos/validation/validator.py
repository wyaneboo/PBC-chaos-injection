"""Run validation contract."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pbc_chaos.validation.checks import ValidationReport


class RunValidator(Protocol):
    def validate(self, run_path: Path) -> ValidationReport:
        """Validate generated files and metadata for a run."""
        ...


class DefaultRunValidator:
    def validate(self, run_path: Path) -> ValidationReport:
        raise NotImplementedError("Run validation is not implemented yet.")

