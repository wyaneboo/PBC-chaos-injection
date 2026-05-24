"""Discrepancy records and helpers for cross-document reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DiscrepancyReason(str, Enum):
    """Supported reasons for controlled reconciliation differences."""

    ROUNDING_DIFFERENCE = "rounding_difference"
    TIMING_DIFFERENCE = "timing_difference"
    MISSING_TRANSACTION = "missing_transaction"
    DUPLICATED_TRANSACTION = "duplicated_transaction"
    WRONG_PERIOD_TRANSACTION = "wrong_period_transaction"
    CONTROLLED_VARIANCE = "controlled_variance"


class DiscrepancySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ReconciliationDiscrepancy:
    """Metadata emitted for one intentional or discovered reconciliation mismatch."""

    discrepancy_id: str
    source_document: str
    target_document: str
    affected_field: str
    expected_value: float
    actual_value: float
    difference: float
    reason: str
    severity: str
    intentional: bool
    relationship_name: str | None = None
    materiality_threshold: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        """Return JSON-serializable sidecar metadata."""

        return {
            "discrepancy_id": self.discrepancy_id,
            "source_document": self.source_document,
            "target_document": self.target_document,
            "affected_field": self.affected_field,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "difference": self.difference,
            "reason": self.reason,
            "severity": self.severity,
            "intentional": self.intentional,
            "relationship_name": self.relationship_name,
            "materiality_threshold": self.materiality_threshold,
            "details": dict(self.details),
        }


def classify_severity(
    difference: float,
    materiality_threshold: float,
    *,
    rounding_tolerance: float = 1.0,
) -> str:
    """Classify a reconciliation difference against configured materiality."""

    absolute = abs(difference)
    if absolute <= rounding_tolerance:
        return DiscrepancySeverity.LOW.value
    if absolute >= materiality_threshold:
        return DiscrepancySeverity.HIGH.value
    if absolute >= materiality_threshold * 0.5:
        return DiscrepancySeverity.MEDIUM.value
    return DiscrepancySeverity.LOW.value


def signed_difference(expected_value: float, actual_value: float) -> float:
    """Return actual less expected, rounded to cents."""

    return round(float(actual_value) - float(expected_value), 2)


def as_reason(value: str | DiscrepancyReason) -> str:
    if isinstance(value, DiscrepancyReason):
        return value.value
    return str(value)

