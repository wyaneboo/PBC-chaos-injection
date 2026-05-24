"""Metadata records emitted by chaos injectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChaosEvent:
    injector: str
    category: str
    description: str
    sheet_name: str | None = None
    cell_range: str | None = None
    severity: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

