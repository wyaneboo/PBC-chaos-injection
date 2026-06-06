"""Score report data structures and writers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MetricResult:
    """One named scoring metric."""

    name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentScore:
    """Metrics for one expected ground-truth document sheet."""

    sheet_name: str
    document_type: str
    matched_sheet_name: str | None
    matched_document_type: str | None
    metrics: dict[str, MetricResult]
    issues: tuple[str, ...] = ()
    report_form: str | None = None
    scored_grain: str | None = None

    @property
    def score(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(metric.score for metric in self.metrics.values()) / len(self.metrics)

    def as_dict(self) -> dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "document_type": self.document_type,
            "report_form": self.report_form,
            "scored_grain": self.scored_grain,
            "matched_sheet_name": self.matched_sheet_name,
            "matched_document_type": self.matched_document_type,
            "score": self.score,
            "metrics": {
                name: metric.as_dict()
                for name, metric in self.metrics.items()
            },
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class ScoreReport:
    """Workbook-level extraction scoring report."""

    workbook_id: str | None
    company_name: str | None
    extraction_name: str | None
    overall_score: float
    summary_metrics: dict[str, MetricResult]
    documents: tuple[DocumentScore, ...]
    issues: tuple[str, ...] = ()
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "workbook_id": self.workbook_id,
            "company_name": self.company_name,
            "extraction_name": self.extraction_name,
            "generated_at": self.generated_at,
            "overall_score": self.overall_score,
            "summary_metrics": {
                name: metric.as_dict()
                for name, metric in self.summary_metrics.items()
            },
            "documents": [document.as_dict() for document in self.documents],
            "issues": list(self.issues),
        }

    def to_markdown(self) -> str:
        """Render a compact human-readable Markdown report."""

        lines = [
            "# Extraction Score Report",
            "",
            f"- Workbook ID: {self.workbook_id or 'unknown'}",
            f"- Company: {self.company_name or 'unknown'}",
            f"- Extraction: {self.extraction_name or 'unknown'}",
            f"- Overall score: {_format_score(self.overall_score)}",
            "",
            "## Summary Metrics",
            "",
            "| Metric | Score | Key details |",
            "| --- | ---: | --- |",
        ]
        for metric in self.summary_metrics.values():
            lines.append(
                f"| {metric.name} | {_format_score(metric.score)} | "
                f"{_summarize_details(metric.details)} |"
            )

        lines.extend(["", "## Document Scores", ""])
        for document in self.documents:
            lines.extend(
                [
                    f"### {document.sheet_name} ({document.document_type})",
                    "",
                    f"- Report form: {document.report_form or 'listing'}"
                    + (f" (scored at {document.scored_grain} grain)" if document.scored_grain else ""),
                    f"- Matched sheet: {document.matched_sheet_name or 'none'}",
                    f"- Matched document type: {document.matched_document_type or 'none'}",
                    f"- Document score: {_format_score(document.score)}",
                    "",
                    "| Metric | Score | Key details |",
                    "| --- | ---: | --- |",
                ]
            )
            for metric in document.metrics.values():
                lines.append(
                    f"| {metric.name} | {_format_score(metric.score)} | "
                    f"{_summarize_details(metric.details)} |"
                )
            if document.issues:
                lines.extend(["", "Issues:"])
                lines.extend(f"- {issue}" for issue in document.issues)
            lines.append("")

        if self.issues:
            lines.extend(["## Workbook Issues", ""])
            lines.extend(f"- {issue}" for issue in self.issues)
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"


def write_score_report(
    report: ScoreReport,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown score reports."""

    json_output = Path(json_path)
    markdown_output = Path(markdown_path)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    markdown_output.write_text(report.to_markdown(), encoding="utf-8")
    return json_output, markdown_output


def _format_score(value: float) -> str:
    return f"{value:.3f}"


def _summarize_details(details: dict[str, Any]) -> str:
    if not details:
        return ""
    preferred = (
        "precision",
        "recall",
        "f1",
        "exact_match",
        "row_count_difference",
        "correct",
        "total",
        "numeric_abs_tolerance",
        "numeric_rel_tolerance",
    )
    parts = []
    for key in preferred:
        if key not in details:
            continue
        parts.append(f"{key}={_detail_value(details[key])}")
    if not parts:
        for key, value in tuple(details.items())[:4]:
            parts.append(f"{key}={_detail_value(value)}")
    return "; ".join(parts).replace("|", "\\|")


def _detail_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list | tuple):
        return str(len(value))
    if isinstance(value, dict):
        return str(len(value))
    return str(value)
