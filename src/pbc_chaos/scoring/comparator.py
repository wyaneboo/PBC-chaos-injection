"""Compare extraction output against simulator ground truth."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from pbc_chaos.core.types import DocumentType
from pbc_chaos.schemas.registry import get_schema
from pbc_chaos.scoring.metrics import (
    best_fuzzy_matches,
    bounded_score,
    dates_equal,
    exact_match,
    fuzzy_ratio,
    normalize_field_name,
    normalize_scalar,
    numbers_close,
    precision_recall_f1,
    prf_from_sets,
    row_count_difference,
    row_count_score,
    safe_div,
    table_boundary_exact,
    table_boundary_iou,
)
from pbc_chaos.scoring.report import (
    DocumentScore,
    MetricResult,
    ScoreReport,
    write_score_report,
)


@dataclass(frozen=True)
class ScoringConfig:
    """Scoring thresholds and tolerances."""

    fuzzy_column_threshold: float = 0.82
    fuzzy_discrepancy_threshold: float = 0.72
    numeric_abs_tolerance: Decimal = Decimal("0.01")
    numeric_rel_tolerance: Decimal = Decimal("0.0001")


@dataclass(frozen=True)
class NormalizedExtractionDocument:
    """Internal normalized representation of one extracted table/document."""

    document_type: str | None
    sheet_name: str | None
    table_location: dict[str, Any]
    headers: tuple[str, ...]
    column_mapping: dict[str, str]
    rows: tuple[dict[str, Any], ...]
    discrepancies: tuple[dict[str, Any], ...]


def compare_extraction_files(
    *,
    groundtruth_path: str | Path,
    extraction_output_path: str | Path,
    json_report_path: str | Path | None = None,
    markdown_report_path: str | Path | None = None,
    config: ScoringConfig | None = None,
) -> ScoreReport:
    """Compare extraction output file against a ground-truth sidecar."""

    groundtruth = load_ground_truth(groundtruth_path)
    extraction_output = load_extraction_output(extraction_output_path)
    report = compare_extraction(
        groundtruth,
        extraction_output,
        extraction_name=Path(extraction_output_path).name,
        config=config,
    )
    if json_report_path and markdown_report_path:
        write_score_report(
            report,
            json_path=json_report_path,
            markdown_path=markdown_report_path,
        )
    return report


def compare_extraction(
    groundtruth: dict[str, Any],
    extraction_output: Any,
    *,
    extraction_name: str | None = None,
    config: ScoringConfig | None = None,
) -> ScoreReport:
    """Score an extracted workbook/table output against ground truth."""

    cfg = config or ScoringConfig()
    expected_sheets = _groundtruth_sheets(groundtruth)
    extraction_documents = _normalize_extraction_documents(extraction_output, expected_sheets)
    matched_documents = _match_documents(expected_sheets, extraction_documents)

    document_scores = tuple(
        _score_sheet(sheet, matched_documents.get(index), cfg)
        for index, sheet in enumerate(expected_sheets)
    )
    summary_metrics = _summary_metrics(
        groundtruth,
        extraction_output,
        expected_sheets,
        extraction_documents,
        document_scores,
        cfg,
    )
    overall_score = _average(metric.score for metric in summary_metrics.values())
    issues = []
    if not expected_sheets:
        issues.append("Ground truth contains no sheet-level scoring records.")
    if not extraction_documents:
        issues.append("Extraction output contains no recognized document/table records.")

    return ScoreReport(
        workbook_id=_optional_string(groundtruth.get("workbook_id")),
        company_name=_optional_string(groundtruth.get("company_name")),
        extraction_name=extraction_name,
        overall_score=overall_score,
        summary_metrics=summary_metrics,
        documents=document_scores,
        issues=tuple(issues),
    )


def load_ground_truth(path: str | Path) -> dict[str, Any]:
    """Load a simulator `.groundtruth.json` file."""

    groundtruth_path = Path(path)
    raw = json.loads(groundtruth_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Ground truth must be a JSON object: {groundtruth_path}")
    return raw


def load_extraction_output(path: str | Path) -> Any:
    """Load JSON extraction output or one-table CSV extraction output."""

    extraction_path = Path(path)
    if extraction_path.suffix.lower() == ".csv":
        with extraction_path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    raw = json.loads(extraction_path.read_text(encoding="utf-8"))
    return raw


def _score_sheet(
    sheet: dict[str, Any],
    extraction: NormalizedExtractionDocument | None,
    config: ScoringConfig,
) -> DocumentScore:
    expected_type = str(sheet.get("document_type", ""))
    expected_schema = tuple(str(field) for field in sheet.get("clean_canonical_schema", ()))
    expected_rows = tuple(_dict_rows(sheet.get("expected_extraction_output", ())))
    issues: list[str] = []

    if extraction is None:
        issues.append("No extraction document matched this ground-truth sheet.")
        return DocumentScore(
            sheet_name=str(sheet.get("sheet_name", "")),
            document_type=expected_type,
            matched_sheet_name=None,
            matched_document_type=None,
            metrics=_zero_document_metrics(
                expected_rows=expected_rows,
                expected_schema=expected_schema,
            ),
            issues=tuple(issues),
        )

    actual_headers = _document_headers(extraction)
    column_mapping, column_details = _build_column_mapping(
        expected_schema,
        actual_headers,
        extraction.column_mapping,
        config=config,
    )
    canonical_rows = tuple(
        _canonicalize_row(row, column_mapping, expected_schema)
        for row in extraction.rows
    )
    row_matches = _match_rows(expected_rows, canonical_rows, expected_type)

    metrics = {
        "document_classification_accuracy": _score_document_classification(
            expected_type,
            extraction.document_type,
        ),
        "table_boundary_detection_accuracy": _score_table_boundary(
            _table_location(sheet),
            extraction.table_location,
        ),
        "header_detection_accuracy": _score_headers(
            expected_schema,
            actual_headers,
            _table_location(sheet),
            extraction.table_location,
            config=config,
        ),
        "column_mapping_accuracy": MetricResult(
            name="column_mapping_accuracy",
            score=safe_div(column_details["mapped_count"], column_details["expected_count"]),
            details=column_details,
        ),
        "row_extraction_accuracy": _score_rows(expected_rows, canonical_rows, row_matches),
        "numeric_value_accuracy": _score_numeric_values(
            expected_rows,
            canonical_rows,
            row_matches,
            expected_type,
            config,
        ),
        "date_normalization_accuracy": _score_date_values(
            expected_rows,
            canonical_rows,
            row_matches,
            expected_type,
        ),
    }
    return DocumentScore(
        sheet_name=str(sheet.get("sheet_name", "")),
        document_type=expected_type,
        matched_sheet_name=extraction.sheet_name,
        matched_document_type=extraction.document_type,
        metrics=metrics,
        issues=tuple(issues),
    )


def _summary_metrics(
    groundtruth: dict[str, Any],
    extraction_output: Any,
    expected_sheets: tuple[dict[str, Any], ...],
    extraction_documents: tuple[NormalizedExtractionDocument, ...],
    document_scores: tuple[DocumentScore, ...],
    config: ScoringConfig,
) -> dict[str, MetricResult]:
    expected_types = tuple(str(sheet.get("document_type", "")) for sheet in expected_sheets)
    actual_types = tuple(
        document.document_type
        for document in extraction_documents
        if document.document_type
    )
    classification = prf_from_sets(expected_types, actual_types)
    discrepancy_metric = _score_discrepancies(
        tuple(_dict_rows(groundtruth.get("injected_discrepancies", ()))),
        _collect_actual_discrepancies(extraction_output, extraction_documents),
        config=config,
    )

    summary = {
        "document_classification_accuracy": MetricResult(
            name="document_classification_accuracy",
            score=classification.f1,
            details={
                **classification.as_dict(),
                "expected_document_types": list(expected_types),
                "actual_document_types": list(actual_types),
            },
        ),
        "table_boundary_detection_accuracy": _average_document_metric(
            document_scores,
            "table_boundary_detection_accuracy",
        ),
        "header_detection_accuracy": _average_document_metric(
            document_scores,
            "header_detection_accuracy",
        ),
        "column_mapping_accuracy": _average_document_metric(
            document_scores,
            "column_mapping_accuracy",
        ),
        "row_extraction_accuracy": _average_document_metric(
            document_scores,
            "row_extraction_accuracy",
        ),
        "numeric_value_accuracy": _average_document_metric(
            document_scores,
            "numeric_value_accuracy",
        ),
        "date_normalization_accuracy": _average_document_metric(
            document_scores,
            "date_normalization_accuracy",
        ),
        "discrepancy_detection_accuracy": discrepancy_metric,
    }
    return summary


def _score_document_classification(
    expected_document_type: str,
    actual_document_type: str | None,
) -> MetricResult:
    is_exact = exact_match(expected_document_type, actual_document_type)
    return MetricResult(
        name="document_classification_accuracy",
        score=1.0 if is_exact else 0.0,
        details={
            "exact_match": is_exact,
            "expected_document_type": expected_document_type,
            "actual_document_type": actual_document_type,
        },
    )


def _score_table_boundary(
    expected_location: dict[str, Any],
    actual_location: dict[str, Any],
) -> MetricResult:
    if not actual_location:
        return MetricResult(
            name="table_boundary_detection_accuracy",
            score=0.0,
            details={
                "exact_match": False,
                "iou": 0.0,
                "expected": expected_location,
                "actual": {},
            },
        )
    exact = table_boundary_exact(expected_location, actual_location)
    iou = table_boundary_iou(expected_location, actual_location)
    header_exact = _int_or_none(expected_location.get("header_row")) == _int_or_none(
        actual_location.get("header_row")
    )
    score = 1.0 if exact else (iou * 0.85 + (0.15 if header_exact else 0.0))
    return MetricResult(
        name="table_boundary_detection_accuracy",
        score=bounded_score(score),
        details={
            "exact_match": exact,
            "iou": iou,
            "header_row_exact": header_exact,
            "expected": expected_location,
            "actual": actual_location,
        },
    )


def _score_headers(
    expected_headers: tuple[str, ...],
    actual_headers: tuple[str, ...],
    expected_location: dict[str, Any],
    actual_location: dict[str, Any],
    *,
    config: ScoringConfig,
) -> MetricResult:
    exact_header_set = {
        normalize_field_name(header)
        for header in expected_headers
    } == {
        normalize_field_name(header)
        for header in actual_headers
    }
    matches = best_fuzzy_matches(
        expected_headers,
        actual_headers,
        threshold=config.fuzzy_column_threshold,
    )
    prf = precision_recall_f1(
        len(matches),
        max(0, len(actual_headers) - len(matches)),
        max(0, len(expected_headers) - len(matches)),
    )
    header_row_available = "header_row" in actual_location
    header_row_exact = _int_or_none(expected_location.get("header_row")) == _int_or_none(
        actual_location.get("header_row")
    )
    score = prf.f1
    if header_row_available:
        score = (score + (1.0 if header_row_exact else 0.0)) / 2
    return MetricResult(
        name="header_detection_accuracy",
        score=bounded_score(score),
        details={
            "exact_match": exact_header_set,
            "precision": prf.precision,
            "recall": prf.recall,
            "f1": prf.f1,
            "header_row_exact": header_row_exact if header_row_available else None,
            "fuzzy_matches": [match.as_dict() for match in matches],
        },
    )


def _score_rows(
    expected_rows: tuple[dict[str, Any], ...],
    actual_rows: tuple[dict[str, Any], ...],
    row_matches: tuple[tuple[int, int], ...],
) -> MetricResult:
    match_count = len(row_matches)
    prf = precision_recall_f1(
        match_count,
        max(0, len(actual_rows) - match_count),
        max(0, len(expected_rows) - match_count),
    )
    count_score = row_count_score(len(expected_rows), len(actual_rows))
    return MetricResult(
        name="row_extraction_accuracy",
        score=(prf.f1 + count_score) / 2,
        details={
            **prf.as_dict(),
            "expected_row_count": len(expected_rows),
            "actual_row_count": len(actual_rows),
            "row_count_difference": row_count_difference(len(expected_rows), len(actual_rows)),
            "row_count_score": count_score,
        },
    )


def _score_numeric_values(
    expected_rows: tuple[dict[str, Any], ...],
    actual_rows: tuple[dict[str, Any], ...],
    row_matches: tuple[tuple[int, int], ...],
    document_type: str,
    config: ScoringConfig,
) -> MetricResult:
    numeric_fields = _fields_by_kind(document_type, {"decimal", "integer", "percentage"})
    total = 0
    correct = 0
    mismatches = []
    for expected_index, actual_index in row_matches:
        expected = expected_rows[expected_index]
        actual = actual_rows[actual_index]
        for field in numeric_fields:
            if field not in expected:
                continue
            total += 1
            if numbers_close(
                expected.get(field),
                actual.get(field),
                abs_tolerance=config.numeric_abs_tolerance,
                rel_tolerance=config.numeric_rel_tolerance,
            ):
                correct += 1
            elif len(mismatches) < 10:
                mismatches.append(
                    {
                        "field": field,
                        "expected": expected.get(field),
                        "actual": actual.get(field),
                        "row": expected_index,
                    }
                )
    return MetricResult(
        name="numeric_value_accuracy",
        score=safe_div(correct, total),
        details={
            "correct": correct,
            "total": total,
            "numeric_abs_tolerance": str(config.numeric_abs_tolerance),
            "numeric_rel_tolerance": str(config.numeric_rel_tolerance),
            "sample_mismatches": mismatches,
        },
    )


def _score_date_values(
    expected_rows: tuple[dict[str, Any], ...],
    actual_rows: tuple[dict[str, Any], ...],
    row_matches: tuple[tuple[int, int], ...],
    document_type: str,
) -> MetricResult:
    date_fields = _fields_by_kind(document_type, {"date", "datetime"})
    total = 0
    correct = 0
    mismatches = []
    for expected_index, actual_index in row_matches:
        expected = expected_rows[expected_index]
        actual = actual_rows[actual_index]
        for field in date_fields:
            if field not in expected:
                continue
            total += 1
            if dates_equal(expected.get(field), actual.get(field)):
                correct += 1
            elif len(mismatches) < 10:
                mismatches.append(
                    {
                        "field": field,
                        "expected": expected.get(field),
                        "actual": actual.get(field),
                        "row": expected_index,
                    }
                )
    return MetricResult(
        name="date_normalization_accuracy",
        score=safe_div(correct, total),
        details={
            "correct": correct,
            "total": total,
            "sample_mismatches": mismatches,
        },
    )


def _score_discrepancies(
    expected_discrepancies: tuple[dict[str, Any], ...],
    actual_discrepancies: tuple[dict[str, Any], ...],
    *,
    config: ScoringConfig,
) -> MetricResult:
    if not expected_discrepancies and not actual_discrepancies:
        prf = precision_recall_f1(0, 0, 0)
        return MetricResult(
            name="discrepancy_detection_accuracy",
            score=1.0,
            details=prf.as_dict(),
        )

    matches = _match_discrepancies(
        expected_discrepancies,
        actual_discrepancies,
        threshold=config.fuzzy_discrepancy_threshold,
    )
    prf = precision_recall_f1(
        len(matches),
        max(0, len(actual_discrepancies) - len(matches)),
        max(0, len(expected_discrepancies) - len(matches)),
    )
    return MetricResult(
        name="discrepancy_detection_accuracy",
        score=prf.f1,
        details={
            **prf.as_dict(),
            "expected_count": len(expected_discrepancies),
            "actual_count": len(actual_discrepancies),
            "matches": matches,
        },
    )


def _zero_document_metrics(
    *,
    expected_rows: tuple[dict[str, Any], ...],
    expected_schema: tuple[str, ...],
) -> dict[str, MetricResult]:
    return {
        "document_classification_accuracy": MetricResult(
            "document_classification_accuracy",
            0.0,
            {"exact_match": False},
        ),
        "table_boundary_detection_accuracy": MetricResult(
            "table_boundary_detection_accuracy",
            0.0,
            {"exact_match": False, "iou": 0.0},
        ),
        "header_detection_accuracy": MetricResult(
            "header_detection_accuracy",
            0.0,
            {"expected_count": len(expected_schema), "actual_count": 0},
        ),
        "column_mapping_accuracy": MetricResult(
            "column_mapping_accuracy",
            0.0,
            {"expected_count": len(expected_schema), "mapped_count": 0},
        ),
        "row_extraction_accuracy": MetricResult(
            "row_extraction_accuracy",
            0.0,
            {
                "expected_row_count": len(expected_rows),
                "actual_row_count": 0,
                "row_count_difference": -len(expected_rows),
            },
        ),
        "numeric_value_accuracy": MetricResult("numeric_value_accuracy", 0.0, {"total": 0}),
        "date_normalization_accuracy": MetricResult("date_normalization_accuracy", 0.0, {"total": 0}),
    }


def _normalize_extraction_documents(
    extraction_output: Any,
    expected_sheets: tuple[dict[str, Any], ...],
) -> tuple[NormalizedExtractionDocument, ...]:
    payloads = _extract_document_payloads(extraction_output)
    if not payloads:
        payloads = _payloads_from_document_type_mapping(extraction_output)

    if not payloads and isinstance(extraction_output, list):
        payloads = [{"rows": extraction_output}]
    if not payloads and isinstance(extraction_output, dict):
        payloads = [extraction_output]

    documents = []
    single_expected = expected_sheets[0] if len(expected_sheets) == 1 else None
    for index, payload in enumerate(payloads):
        default_sheet = single_expected if len(payloads) == 1 else None
        if not isinstance(payload, dict):
            continue
        documents.append(_document_from_payload(payload, index=index, default_sheet=default_sheet))
    return tuple(document for document in documents if document.rows or document.headers or document.document_type)


def _extract_document_payloads(extraction_output: Any) -> list[dict[str, Any]]:
    if isinstance(extraction_output, list):
        if extraction_output and all(isinstance(item, dict) for item in extraction_output):
            if any(_looks_like_document_payload(item) for item in extraction_output):
                return list(extraction_output)
        return []
    if not isinstance(extraction_output, dict):
        return []

    payloads = []
    for key in ("documents", "sheets", "tables", "extracted_documents", "worksheets"):
        value = extraction_output.get(key)
        if isinstance(value, list):
            payloads.extend(item for item in value if isinstance(item, dict))
    expected_output = extraction_output.get("expected_extraction_output")
    if isinstance(expected_output, dict) and not payloads:
        for document_type, rows in expected_output.items():
            if isinstance(rows, list):
                payloads.append({"document_type": document_type, "rows": rows})
    return payloads


def _payloads_from_document_type_mapping(extraction_output: Any) -> list[dict[str, Any]]:
    if not isinstance(extraction_output, dict):
        return []
    payloads = []
    valid_types = {document_type.value for document_type in DocumentType}
    for key, value in extraction_output.items():
        if normalize_field_name(key) in valid_types and isinstance(value, list):
            payloads.append({"document_type": normalize_field_name(key), "rows": value})
    return payloads


def _document_from_payload(
    payload: dict[str, Any],
    *,
    index: int,
    default_sheet: dict[str, Any] | None,
) -> NormalizedExtractionDocument:
    rows = tuple(_dict_rows(_first_value(payload, ("rows", "records", "data", "extracted_rows", "expected_extraction_output"))))
    document_type = _optional_string(
        _first_value(
            payload,
            ("document_type", "doc_type", "type", "classification", "predicted_document_type"),
        )
    )
    sheet_name = _optional_string(_first_value(payload, ("sheet_name", "sheet", "worksheet", "name")))

    if default_sheet:
        document_type = document_type or _optional_string(default_sheet.get("document_type"))
        sheet_name = sheet_name or _optional_string(default_sheet.get("sheet_name"))

    headers = _headers_from_payload(payload, rows)
    mapping = _raw_column_mapping(payload)
    if not headers and mapping:
        headers = tuple(mapping.keys())
    if not headers and rows:
        headers = tuple(rows[0].keys())

    return NormalizedExtractionDocument(
        document_type=document_type,
        sheet_name=sheet_name or f"extracted_table_{index + 1}",
        table_location=_coerce_table_location(payload),
        headers=tuple(str(header) for header in headers),
        column_mapping=mapping,
        rows=rows,
        discrepancies=tuple(_dict_rows(_first_value(payload, ("discrepancies", "detected_discrepancies", "issues", "findings")))),
    )


def _match_documents(
    expected_sheets: tuple[dict[str, Any], ...],
    extraction_documents: tuple[NormalizedExtractionDocument, ...],
) -> dict[int, NormalizedExtractionDocument]:
    available = set(range(len(extraction_documents)))
    matches: dict[int, NormalizedExtractionDocument] = {}
    for expected_index, sheet in enumerate(expected_sheets):
        best_index = None
        best_score = 0.0
        for actual_index in available:
            score = _document_match_score(sheet, extraction_documents[actual_index])
            if score > best_score:
                best_score = score
                best_index = actual_index
        if best_index is not None and best_score > 0:
            matches[expected_index] = extraction_documents[best_index]
            available.remove(best_index)
    return matches


def _document_match_score(
    sheet: dict[str, Any],
    extraction: NormalizedExtractionDocument,
) -> float:
    expected_type = str(sheet.get("document_type", ""))
    expected_sheet = str(sheet.get("sheet_name", ""))
    score = 0.0
    if extraction.document_type and exact_match(expected_type, extraction.document_type):
        score += 3.0
    elif extraction.document_type:
        score += fuzzy_ratio(expected_type, extraction.document_type)
    if extraction.sheet_name and exact_match(expected_sheet, extraction.sheet_name):
        score += 2.0
    elif extraction.sheet_name:
        score += fuzzy_ratio(expected_sheet, extraction.sheet_name)
    if not extraction.document_type and not extraction.sheet_name:
        score += 0.1
    return score


def _build_column_mapping(
    expected_schema: tuple[str, ...],
    actual_headers: tuple[str, ...],
    raw_mapping: dict[str, str],
    *,
    config: ScoringConfig,
) -> tuple[dict[str, str], dict[str, Any]]:
    expected_lookup = {normalize_field_name(field): field for field in expected_schema}
    actual_to_expected: dict[str, str] = {}
    explicit_matches = []

    for raw_key, raw_value in raw_mapping.items():
        key = str(raw_key)
        value = str(raw_value)
        value_expected = _resolve_expected_field(value, expected_lookup, config)
        key_expected = _resolve_expected_field(key, expected_lookup, config)
        if value_expected:
            actual_to_expected[key] = value_expected
            explicit_matches.append({"actual": key, "expected": value_expected})
        elif key_expected:
            actual_to_expected[value] = key_expected
            explicit_matches.append({"actual": value, "expected": key_expected})

    unmapped_headers = [header for header in actual_headers if header not in actual_to_expected]
    exact_matches = []
    for header in tuple(unmapped_headers):
        expected = expected_lookup.get(normalize_field_name(header))
        if expected:
            actual_to_expected[header] = expected
            exact_matches.append({"actual": header, "expected": expected})
            unmapped_headers.remove(header)

    used_expected = set(actual_to_expected.values())
    fuzzy_expected = [field for field in expected_schema if field not in used_expected]
    fuzzy_matches = best_fuzzy_matches(
        fuzzy_expected,
        unmapped_headers,
        threshold=config.fuzzy_column_threshold,
    )
    for match in fuzzy_matches:
        actual_to_expected[match.actual] = match.expected

    mapped_expected = set(actual_to_expected.values())
    details = {
        "expected_count": len(expected_schema),
        "mapped_count": len(mapped_expected),
        "exact_match_count": len(exact_matches),
        "explicit_match_count": len(explicit_matches),
        "fuzzy_match_count": len(fuzzy_matches),
        "fuzzy_column_match": [match.as_dict() for match in fuzzy_matches],
        "unmapped_expected_columns": [
            field for field in expected_schema if field not in mapped_expected
        ],
    }
    return actual_to_expected, details


def _canonicalize_row(
    row: dict[str, Any],
    actual_to_expected: dict[str, str],
    expected_schema: tuple[str, ...],
) -> dict[str, Any]:
    expected_lookup = {normalize_field_name(field): field for field in expected_schema}
    normalized_mapping = {
        normalize_field_name(actual): expected
        for actual, expected in actual_to_expected.items()
    }
    canonical: dict[str, Any] = {}
    for key, value in row.items():
        key_text = str(key)
        expected = (
            actual_to_expected.get(key_text)
            or normalized_mapping.get(normalize_field_name(key_text))
            or expected_lookup.get(normalize_field_name(key_text))
        )
        if expected:
            canonical[expected] = value
    return canonical


def _match_rows(
    expected_rows: tuple[dict[str, Any], ...],
    actual_rows: tuple[dict[str, Any], ...],
    document_type: str,
) -> tuple[tuple[int, int], ...]:
    primary_key = _primary_key(document_type)
    if primary_key:
        actual_by_key: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for actual_index, row in enumerate(actual_rows):
            signature = _row_signature(row, primary_key)
            if signature is not None:
                actual_by_key[signature].append(actual_index)

        matches = []
        for expected_index, row in enumerate(expected_rows):
            signature = _row_signature(row, primary_key)
            if signature is None or not actual_by_key.get(signature):
                continue
            matches.append((expected_index, actual_by_key[signature].pop(0)))
        if matches:
            return tuple(matches)

    return tuple(
        (index, index)
        for index in range(min(len(expected_rows), len(actual_rows)))
    )


def _score_from_document_scores(
    document_scores: tuple[DocumentScore, ...],
    metric_name: str,
) -> float:
    return _average(
        document.metrics[metric_name].score
        for document in document_scores
        if metric_name in document.metrics
    )


def _average_document_metric(
    document_scores: tuple[DocumentScore, ...],
    metric_name: str,
) -> MetricResult:
    score = _score_from_document_scores(document_scores, metric_name)
    return MetricResult(
        name=metric_name,
        score=score,
        details={"document_count": len(document_scores)},
    )


def _collect_actual_discrepancies(
    extraction_output: Any,
    extraction_documents: tuple[NormalizedExtractionDocument, ...],
) -> tuple[dict[str, Any], ...]:
    discrepancies: list[dict[str, Any]] = []
    if isinstance(extraction_output, dict):
        discrepancies.extend(
            _dict_rows(
                _first_value(
                    extraction_output,
                    ("discrepancies", "detected_discrepancies", "issues", "findings"),
                )
            )
        )
    for document in extraction_documents:
        discrepancies.extend(document.discrepancies)
    return tuple(discrepancies)


def _match_discrepancies(
    expected_discrepancies: tuple[dict[str, Any], ...],
    actual_discrepancies: tuple[dict[str, Any], ...],
    *,
    threshold: float,
) -> list[dict[str, Any]]:
    actual_by_signature = {
        _discrepancy_signature(discrepancy): index
        for index, discrepancy in enumerate(actual_discrepancies)
    }
    matched_actual: set[int] = set()
    matches = []
    for expected_index, expected in enumerate(expected_discrepancies):
        signature = _discrepancy_signature(expected)
        actual_index = actual_by_signature.get(signature)
        if actual_index is not None and actual_index not in matched_actual:
            matched_actual.add(actual_index)
            matches.append(
                {
                    "expected_index": expected_index,
                    "actual_index": actual_index,
                    "method": "exact_signature",
                    "score": 1.0,
                }
            )
            continue

        expected_text = _discrepancy_text(expected)
        best_index = None
        best_score = 0.0
        for candidate_index, actual in enumerate(actual_discrepancies):
            if candidate_index in matched_actual:
                continue
            score = fuzzy_ratio(expected_text, _discrepancy_text(actual))
            if score > best_score:
                best_index = candidate_index
                best_score = score
        if best_index is not None and best_score >= threshold:
            matched_actual.add(best_index)
            matches.append(
                {
                    "expected_index": expected_index,
                    "actual_index": best_index,
                    "method": "fuzzy",
                    "score": best_score,
                }
            )
    return matches


def _discrepancy_signature(discrepancy: dict[str, Any]) -> tuple[str, ...]:
    explicit_id = _optional_string(
        discrepancy.get("discrepancy_id")
        or discrepancy.get("id")
        or discrepancy.get("finding_id")
    )
    if explicit_id:
        return ("id", normalize_scalar(explicit_id))
    fields = (
        "source_document",
        "target_document",
        "affected_field",
        "reason",
        "relationship_name",
    )
    return tuple(normalize_scalar(discrepancy.get(field)) for field in fields)


def _discrepancy_text(discrepancy: dict[str, Any]) -> str:
    parts = []
    for key in (
        "discrepancy_id",
        "source_document",
        "target_document",
        "affected_field",
        "reason",
        "relationship_name",
        "severity",
        "description",
    ):
        value = discrepancy.get(key)
        if value not in (None, ""):
            parts.append(f"{key}: {value}")
    return " ".join(parts) or json.dumps(discrepancy, sort_keys=True, default=str)


def _fields_by_kind(document_type: str, kind_values: set[str]) -> tuple[str, ...]:
    try:
        schema = get_schema(DocumentType(document_type))
    except (KeyError, ValueError):
        return ()
    return tuple(
        field.name
        for field in schema.fields
        if field.data_type.value in kind_values
    )


def _primary_key(document_type: str) -> tuple[str, ...]:
    try:
        return get_schema(DocumentType(document_type)).primary_key
    except (KeyError, ValueError):
        return ()


def _row_signature(row: dict[str, Any], primary_key: tuple[str, ...]) -> tuple[str, ...] | None:
    values = []
    for field in primary_key:
        if field not in row or row.get(field) in (None, ""):
            return None
        values.append(normalize_scalar(row.get(field)))
    return tuple(values)


def _headers_from_payload(
    payload: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
) -> tuple[str, ...]:
    headers = _first_value(payload, ("headers", "detected_headers"))
    if isinstance(headers, list):
        return tuple(str(item) for item in headers)

    columns = payload.get("columns")
    if isinstance(columns, list):
        output = []
        for column in columns:
            if isinstance(column, dict):
                value = _first_value(column, ("header", "name", "source", "actual", "column"))
                if value is not None:
                    output.append(str(value))
            else:
                output.append(str(column))
        return tuple(output)
    if isinstance(columns, dict):
        return tuple(str(key) for key in columns)
    if rows:
        return tuple(rows[0].keys())
    return ()


def _raw_column_mapping(payload: dict[str, Any]) -> dict[str, str]:
    mapping = _first_value(
        payload,
        ("column_mapping", "columns_mapping", "canonical_columns", "field_mapping"),
    )
    if isinstance(mapping, dict):
        return {str(key): str(value) for key, value in mapping.items()}

    columns = payload.get("columns")
    if isinstance(columns, list):
        output = {}
        for column in columns:
            if not isinstance(column, dict):
                continue
            source = _first_value(column, ("header", "source", "actual", "name", "column"))
            target = _first_value(column, ("canonical", "target", "field", "mapped_to"))
            if source is not None and target is not None:
                output[str(source)] = str(target)
        return output
    return {}


def _coerce_table_location(payload: dict[str, Any]) -> dict[str, Any]:
    source = _first_value(payload, ("table_location", "table_bounds", "bounds", "table"))
    if not isinstance(source, dict):
        source = payload
    location = {
        "start_row": _first_location_value(source, "start_row", "min_row", "top_row", "row_start"),
        "start_column": _first_location_value(
            source,
            "start_column",
            "start_col",
            "min_column",
            "min_col",
            "left_column",
            "column_start",
        ),
        "end_row": _first_location_value(source, "end_row", "max_row", "bottom_row", "row_end"),
        "end_column": _first_location_value(
            source,
            "end_column",
            "end_col",
            "max_column",
            "max_col",
            "right_column",
            "column_end",
        ),
        "header_row": _first_location_value(source, "header_row", "header", "header_row_index"),
    }
    start_cell = _optional_string(source.get("start_cell") or source.get("top_left"))
    end_cell = _optional_string(source.get("end_cell") or source.get("bottom_right"))
    if start_cell:
        row, column = _cell_to_row_column(start_cell)
        location["start_row"] = location["start_row"] or row
        location["start_column"] = location["start_column"] or column
    if end_cell:
        row, column = _cell_to_row_column(end_cell)
        location["end_row"] = location["end_row"] or row
        location["end_column"] = location["end_column"] or column
    return {key: value for key, value in location.items() if value is not None}


def _table_location(sheet: dict[str, Any]) -> dict[str, Any]:
    value = sheet.get("table_location")
    return dict(value) if isinstance(value, dict) else {}


def _document_headers(extraction: NormalizedExtractionDocument) -> tuple[str, ...]:
    headers = list(extraction.headers)
    for row in extraction.rows[:1]:
        headers.extend(key for key in row if key not in headers)
    return tuple(dict.fromkeys(str(header) for header in headers if str(header)))


def _groundtruth_sheets(groundtruth: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(_dict_rows(groundtruth.get("sheets", ())))


def _dict_rows(value: Any) -> tuple[dict[str, Any], ...]:
    if isinstance(value, dict):
        return (dict(value),)
    if not isinstance(value, list | tuple):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, dict))


def _looks_like_document_payload(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "document_type",
            "doc_type",
            "sheet_name",
            "table_location",
            "table_bounds",
            "rows",
            "records",
            "extracted_rows",
            "headers",
            "columns",
        )
    )


def _resolve_expected_field(
    value: str,
    expected_lookup: dict[str, str],
    config: ScoringConfig,
) -> str | None:
    exact = expected_lookup.get(normalize_field_name(value))
    if exact:
        return exact
    best = None
    best_score = 0.0
    for expected in expected_lookup.values():
        score = fuzzy_ratio(value, expected)
        if score > best_score:
            best = expected
            best_score = score
    if best is not None and best_score >= config.fuzzy_column_threshold:
        return best
    return None


def _first_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _first_location_value(source: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _cell_to_row_column(cell: str) -> tuple[int | None, int | None]:
    match = re.match(r"^\$?([A-Za-z]+)\$?(\d+)$", cell.strip())
    if not match:
        return None, None
    letters, row_text = match.groups()
    column = 0
    for char in letters.upper():
        column = column * 26 + ord(char) - ord("A") + 1
    return int(row_text), column


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _average(values: Any) -> float:
    value_list = [float(value) for value in values]
    if not value_list:
        return 0.0
    return sum(value_list) / len(value_list)
