"""Primitive metrics used by extraction scoring."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Iterable


@dataclass(frozen=True)
class PrecisionRecallF1:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True)
class FuzzyMatch:
    expected: str
    actual: str
    score: float

    def as_dict(self) -> dict[str, str | float]:
        return asdict(self)


def exact_match(expected: Any, actual: Any) -> bool:
    """Return whether two scalar values match after conservative normalization."""

    return normalize_scalar(expected) == normalize_scalar(actual)


def normalize_text(value: Any) -> str:
    """Normalize a value for label and classification comparisons."""

    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_field_name(value: Any) -> str:
    """Normalize a field/header name to a snake-like comparison key."""

    return normalize_text(value).replace(" ", "_")


def normalize_scalar(value: Any) -> str:
    """Normalize scalar values for exact row-key comparisons."""

    parsed_date = parse_date(value)
    if parsed_date is not None:
        return parsed_date.isoformat()
    parsed_number = parse_decimal(value)
    if parsed_number is not None:
        return str(parsed_number.normalize())
    return normalize_text(value)


def fuzzy_ratio(expected: Any, actual: Any) -> float:
    """Return a SequenceMatcher ratio for normalized labels."""

    expected_text = normalize_text(expected)
    actual_text = normalize_text(actual)
    if not expected_text and not actual_text:
        return 1.0
    if not expected_text or not actual_text:
        return 0.0
    return SequenceMatcher(None, expected_text, actual_text).ratio()


def best_fuzzy_matches(
    expected: Iterable[str],
    actual: Iterable[str],
    *,
    threshold: float = 0.82,
) -> tuple[FuzzyMatch, ...]:
    """Greedily match expected labels to actual labels using fuzzy similarity."""

    expected_values = tuple(dict.fromkeys(str(item) for item in expected if str(item)))
    actual_values = tuple(dict.fromkeys(str(item) for item in actual if str(item)))
    candidates: list[FuzzyMatch] = []
    for expected_value in expected_values:
        for actual_value in actual_values:
            score = fuzzy_ratio(expected_value, actual_value)
            if score >= threshold:
                candidates.append(FuzzyMatch(expected_value, actual_value, score))
    candidates.sort(key=lambda item: item.score, reverse=True)

    used_expected: set[str] = set()
    used_actual: set[str] = set()
    matches: list[FuzzyMatch] = []
    for candidate in candidates:
        if candidate.expected in used_expected or candidate.actual in used_actual:
            continue
        used_expected.add(candidate.expected)
        used_actual.add(candidate.actual)
        matches.append(candidate)
    return tuple(matches)


def precision_recall_f1(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> PrecisionRecallF1:
    """Build precision/recall/F1 metrics from confusion counts."""

    precision = safe_div(true_positives, true_positives + false_positives)
    recall = safe_div(true_positives, true_positives + false_negatives)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return PrecisionRecallF1(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def prf_from_sets(expected: Iterable[Any], actual: Iterable[Any]) -> PrecisionRecallF1:
    """Return precision/recall/F1 for two exact-match sets."""

    expected_set = {normalize_scalar(item) for item in expected}
    actual_set = {normalize_scalar(item) for item in actual}
    if not expected_set and not actual_set:
        return PrecisionRecallF1(1.0, 1.0, 1.0, 0, 0, 0)
    true_positives = len(expected_set & actual_set)
    false_positives = len(actual_set - expected_set)
    false_negatives = len(expected_set - actual_set)
    return precision_recall_f1(true_positives, false_positives, false_negatives)


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    return float(numerator) / float(denominator)


def bounded_score(value: float) -> float:
    """Clamp a metric score to the public 0..1 range."""

    return max(0.0, min(1.0, float(value)))


def row_count_difference(expected_count: int, actual_count: int) -> int:
    """Return actual row count less expected row count."""

    return int(actual_count) - int(expected_count)


def row_count_score(expected_count: int, actual_count: int) -> float:
    """Return a 0..1 score for row-count closeness."""

    baseline = max(int(expected_count), int(actual_count), 1)
    return bounded_score(1.0 - abs(row_count_difference(expected_count, actual_count)) / baseline)


def parse_decimal(value: Any) -> Decimal | None:
    """Parse common numeric extraction values, including commas and parentheses."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return None

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    has_percent = "%" in text
    text = text.replace("%", "")
    text = re.sub(r"[,\s$€£¥]|RM|MYR|USD|SGD", "", text, flags=re.IGNORECASE)
    if not text or text in {"-", ".", "-."}:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if negative:
        number = -number
    if has_percent:
        number = number / Decimal("100")
    return number


def numbers_close(
    expected: Any,
    actual: Any,
    *,
    abs_tolerance: Decimal = Decimal("0.01"),
    rel_tolerance: Decimal = Decimal("0.0001"),
) -> bool:
    """Return whether two numbers match within absolute or relative tolerance."""

    expected_number = parse_decimal(expected)
    actual_number = parse_decimal(actual)
    if expected_number is None or actual_number is None:
        return expected_number is None and actual_number is None
    difference = abs(expected_number - actual_number)
    if difference <= abs_tolerance:
        return True
    denominator = max(abs(expected_number), Decimal("1"))
    return difference / denominator <= rel_tolerance


def parse_date(value: Any) -> date | None:
    """Parse common date outputs to a normalized date."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, int | float):
        if 20_000 <= float(value) <= 60_000:
            return date(1899, 12, 30) + timedelta(days=int(value))
        return None

    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def dates_equal(expected: Any, actual: Any) -> bool:
    """Return whether two date values normalize to the same calendar date."""

    expected_date = parse_date(expected)
    actual_date = parse_date(actual)
    if expected_date is None or actual_date is None:
        return expected_date is None and actual_date is None
    return expected_date == actual_date


def table_boundary_iou(expected: dict[str, Any], actual: dict[str, Any]) -> float:
    """Return intersection-over-union for expected and actual table rectangles."""

    expected_rect = _table_rect(expected)
    actual_rect = _table_rect(actual)
    if expected_rect is None or actual_rect is None:
        return 0.0

    er1, ec1, er2, ec2 = expected_rect
    ar1, ac1, ar2, ac2 = actual_rect
    intersection_rows = max(0, min(er2, ar2) - max(er1, ar1) + 1)
    intersection_cols = max(0, min(ec2, ac2) - max(ec1, ac1) + 1)
    intersection = intersection_rows * intersection_cols
    expected_area = max(0, er2 - er1 + 1) * max(0, ec2 - ec1 + 1)
    actual_area = max(0, ar2 - ar1 + 1) * max(0, ac2 - ac1 + 1)
    union = expected_area + actual_area - intersection
    return safe_div(intersection, union)


def table_boundary_exact(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Return whether core table boundary coordinates exactly match."""

    keys = ("start_row", "start_column", "end_row", "end_column", "header_row")
    return all(_int_or_none(expected.get(key)) == _int_or_none(actual.get(key)) for key in keys)


def _table_rect(location: dict[str, Any]) -> tuple[int, int, int, int] | None:
    try:
        start_row = int(location["start_row"])
        start_column = int(location["start_column"])
        end_row = int(location["end_row"])
        end_column = int(location["end_column"])
    except (KeyError, TypeError, ValueError):
        return None
    if end_row < start_row or end_column < start_column:
        return None
    return start_row, start_column, end_row, end_column


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
