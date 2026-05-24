"""Validation result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: Path | None = None
    severity: str = "error"


@dataclass(frozen=True)
class ValidationReport:
    run_path: Path
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

