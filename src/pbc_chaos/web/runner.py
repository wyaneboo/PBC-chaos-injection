"""Structured web runner around the existing batch and CLI helpers."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from random import Random
from typing import Any, Callable

from pbc_chaos.batch import pipeline
from pbc_chaos.batch.pipeline import (
    BatchPipelineError,
    export_manifest,
    generate_single_workbook,
    simulated_companies,
    validate_generated_directory,
    write_manifest_rows,
)
from pbc_chaos.config_loader import DEFAULT_PROBABILITIES_BY_SEVERITY
from pbc_chaos.config.settings import load_settings
from pbc_chaos.core.types import DocumentType
from pbc_chaos.env import load_env_file
from pbc_chaos.scoring import ScoringConfig, compare_extraction_files
from pbc_chaos.web.events import GENERATION_STAGES, PROBABILITY_KEYS, SEVERITY_LABELS, now_iso

Emitter = Callable[[dict[str, Any]], None]


def run_web_command(mode: str, options: dict[str, Any], command_preview: str, emit: Emitter) -> dict[str, Any]:
    """Execute one UI command and emit progress events."""

    if mode in {"generate-one", "generate-batch", "generate-dataset", "generate-yaml"}:
        return _run_generation(mode, options, command_preview, emit)
    if mode == "validate":
        return _run_validate(options, command_preview, emit)
    if mode == "manifest":
        return _run_manifest(options, command_preview, emit)
    if mode == "score":
        return _run_score(options, command_preview, emit)
    if mode == "doc-types":
        return _run_doc_types(command_preview, emit)
    raise BatchPipelineError(f"Unsupported web run mode: {mode}")


def _run_generation(
    mode: str,
    options: dict[str, Any],
    command_preview: str,
    emit: Emitter,
) -> dict[str, Any]:
    _emit(emit, command_preview, "validate_options", "running", "Checking command options", 1)

    generation_plan = _generation_plan(mode, options)
    output_dir = Path(generation_plan["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(generation_plan["companies"])
    nightmare = bool(generation_plan["unreproducible_nightmare"])

    warnings: list[str] = []
    if nightmare and not _gemini_configured():
        warnings.append(
            "GEMINI_API_KEY is not set. Nightmare mode will use the LangGraph heuristic fallback."
        )
        _emit(
            emit,
            command_preview,
            "resolve_config",
            "warning",
            warnings[-1],
            5,
            severity="warning",
        )

    if (output_dir / "manifest.csv").exists():
        warnings.append("Output directory already contains manifest.csv and it will be overwritten.")

    _emit(emit, command_preview, "validate_options", "succeeded", "Options accepted", 5)
    _emit(emit, command_preview, "resolve_config", "succeeded", "Chaos configuration resolved", 10)
    _emit(
        emit,
        command_preview,
        "prepare_companies",
        "succeeded",
        f"Prepared {total} workbook target(s)",
        15,
    )
    _emit(
        emit,
        command_preview,
        "parse_period",
        "succeeded",
        f"Parsed period {generation_plan['period_label']}",
        20,
    )

    rows = []
    records = []
    artifacts: list[dict[str, Any]] = []
    total_weight = sum(stage["weight"] for stage in GENERATION_STAGES)
    weighted_before_work = 20
    per_workbook_span = 72

    for index, company in enumerate(generation_plan["companies"], start=1):
        chaos_level = generation_plan["chaos_levels"][index - 1]
        seed = generation_plan["seed"] + index if generation_plan["seed"] is not None else None
        workbook_base = weighted_before_work + ((index - 1) / total) * per_workbook_span
        workbook = {
            "index": index,
            "total": total,
            "company_name": company.company_name,
            "chaos_level": chaos_level,
            "stage_percent": 0,
        }
        for stage_id, message, local_percent in (
            ("build_financial_truth", "Building canonical financial truth", 0.12),
            ("generate_documents", "Generating clean PBC tracker and schedules", 0.35),
            ("render_workbook", "Rendering workbook sheets", 0.58),
            ("apply_layout_chaos", "Applying layout and tracker chaos", 0.78),
        ):
            workbook = dict(workbook, stage_percent=local_percent)
            _emit(
                emit,
                command_preview,
                stage_id,
                "running",
                message,
                workbook_base + local_percent * (per_workbook_span / total),
                workbook=workbook,
            )

        if nightmare:
            _emit(
                emit,
                command_preview,
                "nightmare_post_pass",
                "running",
                "Applying unreproducible nightmare post-pass",
                workbook_base + 0.88 * (per_workbook_span / total),
                workbook=dict(workbook, stage_percent=0.88),
            )
        else:
            _emit(
                emit,
                command_preview,
                "nightmare_post_pass",
                "skipped",
                "Nightmare mode is off",
                workbook_base + 0.88 * (per_workbook_span / total),
                workbook=dict(workbook, stage_percent=0.88),
            )

        result = generate_single_workbook(
            company_name=company.company_name,
            period_label=generation_plan["period_label"],
            chaos_level=chaos_level,
            output_dir=output_dir,
            seed=seed,
            company_id=company.company_id,
            filename_stem=generation_plan["filename_stems"][index - 1],
            unreproducible_nightmare_mode=nightmare,
        )
        record = result.records[0]
        records.append(record)
        rows.append(pipeline._manifest_row_from_record(record))
        for stage_id, message, local_percent in (
            ("build_financial_truth", "Canonical financial truth built", 0.18),
            ("generate_documents", "Clean PBC tracker and schedules generated", 0.42),
            ("render_workbook", "Workbook sheets rendered", 0.66),
            ("apply_layout_chaos", "Layout and tracker chaos applied", 0.86),
        ):
            _emit(
                emit,
                command_preview,
                stage_id,
                "succeeded",
                message,
                workbook_base + local_percent * (per_workbook_span / total),
                workbook=dict(workbook, stage_percent=local_percent),
            )
        for artifact_type, artifact_path in (
            ("workbook", record.exported.workbook_path),
            ("groundtruth", record.exported.ground_truth_path),
        ):
            artifact = _artifact(artifact_type, artifact_path)
            artifacts.append(artifact)
            _emit(
                emit,
                command_preview,
                "save_artifacts",
                "succeeded",
                f"Wrote {artifact_type}: {artifact_path.name}",
                workbook_base + 0.96 * (per_workbook_span / total),
                workbook=dict(workbook, stage_percent=0.96),
                artifact=artifact,
            )

        workbook_done_percent = weighted_before_work + (index / total) * per_workbook_span
        _emit(
            emit,
            command_preview,
            "record_ground_truth",
            "succeeded",
            f"Completed workbook {index} of {total}",
            workbook_done_percent,
            workbook=dict(workbook, stage_percent=1),
        )

    manifest_path = write_manifest_rows(rows, output_path=output_dir / "manifest.csv")
    manifest_artifact = _artifact("manifest", manifest_path)
    artifacts.append(manifest_artifact)
    _emit(
        emit,
        command_preview,
        "write_manifest",
        "succeeded",
        f"Wrote manifest: {manifest_path}",
        97,
        artifact=manifest_artifact,
    )
    _emit(
        emit,
        command_preview,
        "complete",
        "succeeded",
        f"Generated {len(records)} workbook(s)",
        100,
    )

    return {
        "mode": mode,
        "command": command_preview,
        "workbook_count": len(records),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path),
        "chaos_levels": sorted(set(generation_plan["chaos_levels"])),
        "nightmare_enabled": nightmare,
        "warnings": warnings,
        "artifacts": artifacts,
        "stage_weight_total": total_weight,
    }


def _run_validate(
    options: dict[str, Any],
    command_preview: str,
    emit: Emitter,
) -> dict[str, Any]:
    input_dir = Path(str(options.get("input") or ""))
    _emit(emit, command_preview, "validate_options", "running", "Checking input directory", 5)
    report = validate_generated_directory(input_dir)
    _emit(
        emit,
        command_preview,
        "validate_outputs",
        "succeeded" if report.passed else "failed",
        "Validation passed" if report.passed else f"Validation found {len(report.issues)} issue(s)",
        90,
        severity="info" if report.passed else "error",
    )
    _emit(emit, command_preview, "complete", "succeeded" if report.passed else "failed", "Complete", 100)
    return {
        "mode": "validate",
        "passed": report.passed,
        "run_path": str(report.run_path),
        "workbook_count": len(tuple(report.run_path.glob("*.xlsx"))) if report.run_path.exists() else 0,
        "issues": [
            {"code": issue.code, "message": issue.message, "path": str(issue.path) if issue.path else ""}
            for issue in report.issues
        ],
    }


def _run_manifest(
    options: dict[str, Any],
    command_preview: str,
    emit: Emitter,
) -> dict[str, Any]:
    input_dir = Path(str(options.get("input") or ""))
    output = Path(str(options.get("output") or "manifest.csv"))
    _emit(emit, command_preview, "validate_options", "running", "Checking manifest inputs", 5)
    path = export_manifest(input_dir=input_dir, output_path=output)
    artifact = _artifact("manifest", path)
    _emit(emit, command_preview, "write_manifest", "succeeded", f"Wrote manifest: {path}", 90, artifact=artifact)
    _emit(emit, command_preview, "complete", "succeeded", "Complete", 100)
    return {"mode": "manifest", "manifest_path": str(path), "artifacts": [artifact]}


def _run_score(options: dict[str, Any], command_preview: str, emit: Emitter) -> dict[str, Any]:
    _emit(emit, command_preview, "validate_options", "running", "Checking scoring inputs", 5)
    config = ScoringConfig(
        fuzzy_column_threshold=float(options.get("fuzzyColumnThreshold") or 0.82),
        numeric_abs_tolerance=_decimal(options.get("numericAbsTolerance") or "0.01", "numeric abs tolerance"),
        numeric_rel_tolerance=_decimal(options.get("numericRelTolerance") or "0.0001", "numeric rel tolerance"),
    )
    report = compare_extraction_files(
        groundtruth_path=Path(str(options.get("groundtruth") or "")),
        extraction_output_path=Path(str(options.get("extraction") or "")),
        json_report_path=Path(str(options.get("outputJson") or "score_report.json")),
        markdown_report_path=Path(str(options.get("outputMd") or "score_report.md")),
        config=config,
    )
    artifacts = [
        _artifact("score-json", Path(str(options.get("outputJson") or "score_report.json"))),
        _artifact("score-markdown", Path(str(options.get("outputMd") or "score_report.md"))),
    ]
    _emit(
        emit,
        command_preview,
        "score_extraction",
        "succeeded",
        f"Overall score: {report.overall_score:.3f}",
        90,
    )
    _emit(emit, command_preview, "complete", "succeeded", "Complete", 100)
    return {
        "mode": "score",
        "overall_score": report.overall_score,
        "artifacts": artifacts,
    }


def _run_doc_types(command_preview: str, emit: Emitter) -> dict[str, Any]:
    doc_types = [doc_type.value for doc_type in DocumentType]
    _emit(emit, command_preview, "validate_options", "succeeded", "No input required", 20)
    _emit(emit, command_preview, "complete", "succeeded", f"Listed {len(doc_types)} document types", 100)
    return {"mode": "doc-types", "document_types": doc_types}


def _generation_plan(mode: str, options: dict[str, Any]) -> dict[str, Any]:
    if mode == "generate-yaml":
        config_path = Path(str(options.get("config") or "configs/default.yaml"))
        settings = load_settings(config_path)
        severity_by_name = {"low": 1, "medium": 3, "high": 5}
        chaos_level = severity_by_name[settings.chaos.severity.value]
        period_label = f"FY{settings.batch.financial_years[0]}"
        seed = int(settings.run.seed)
        companies = simulated_companies(int(settings.batch.client_count), seed=seed)
        output_dir = str(settings.run.output_dir)
        nightmare = bool(options.get("unreproducibleNightmare"))
        levels = [chaos_level for _ in companies]
    elif mode == "generate-one":
        period_label = str(options.get("period") or "")
        seed = _optional_int(options.get("seed"))
        output_dir = str(options.get("output") or "outputs")
        company_name = str(options.get("company") or "").strip()
        company = pipeline.CompanyProfile(
            company_id=pipeline.company_id_from_name(company_name),
            company_name=company_name,
        )
        companies = (company,)
        levels = [int(options.get("chaosLevel"))]
        nightmare = bool(options.get("unreproducibleNightmare"))
    else:
        period_label = str(options.get("period") or "FY2025")
        seed = int(options.get("seed") or 1)
        output_dir = str(options.get("output") or "")
        companies = simulated_companies(int(options.get("companies") or 1), seed=seed)
        nightmare = bool(options.get("unreproducibleNightmare"))
        if mode == "generate-batch":
            levels = [int(options.get("chaosLevel")) for _ in companies]
        elif mode == "generate-dataset":
            min_chaos = int(options.get("minChaos") if options.get("minChaos") is not None else 0)
            max_chaos = int(options.get("maxChaos") if options.get("maxChaos") is not None else 5)
            level_range = tuple(range(min_chaos, max_chaos + 1))
            offset = Random(seed).randrange(len(level_range))
            levels = [level_range[(index + offset) % len(level_range)] for index in range(len(companies))]
        else:
            raise BatchPipelineError(f"Unsupported generation mode: {mode}")

    period = pipeline.parse_period(period_label)
    stems = [
        pipeline._filename_stem(company, period, levels[index - 1], index)
        for index, company in enumerate(companies, start=1)
    ]
    for level in levels:
        pipeline.validate_chaos_level(level)
    return {
        "companies": tuple(companies),
        "chaos_levels": levels,
        "period_label": period_label,
        "seed": seed,
        "output_dir": output_dir,
        "filename_stems": stems,
        "unreproducible_nightmare": nightmare,
    }


def metadata_payload() -> dict[str, Any]:
    """Return static UI metadata used by the React app."""

    return {
        "severityLabels": SEVERITY_LABELS,
        "probabilityKeys": list(PROBABILITY_KEYS),
        "probabilityDefaults": {
            str(severity): defaults.as_dict()
            for severity, defaults in DEFAULT_PROBABILITIES_BY_SEVERITY.items()
        },
        "stages": list(GENERATION_STAGES),
        "documentTypes": [doc_type.value for doc_type in DocumentType],
        "geminiConfigured": _gemini_configured(),
    }


def _emit(
    emit: Emitter,
    command: str,
    stage_id: str,
    status: str,
    message: str,
    overall_percent: float,
    *,
    workbook: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    severity: str = "info",
) -> None:
    emit(
        {
            "command": command,
            "status": status,
            "stage_id": stage_id,
            "stage_label": _stage_label(stage_id),
            "message": message,
            "overall_percent": max(0, min(100, round(overall_percent, 1))),
            "workbook": workbook,
            "artifact": artifact,
            "severity": severity,
            "timestamp": now_iso(),
        }
    )


def _stage_label(stage_id: str) -> str:
    for stage in GENERATION_STAGES:
        if stage["id"] == stage_id:
            return str(stage["label"])
    labels = {
        "validate_outputs": "Validate outputs",
        "score_extraction": "Score extraction",
    }
    return labels.get(stage_id, stage_id.replace("_", " ").title())


def _artifact(artifact_type: str, path: Path) -> dict[str, Any]:
    return {
        "type": artifact_type,
        "path": str(path),
        "name": path.name,
        "size": path.stat().st_size if path.exists() else None,
    }


def _gemini_configured() -> bool:
    load_env_file()
    return bool(os.getenv("GEMINI_API_KEY"))


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _decimal(value: object, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise BatchPipelineError(f"{label} must be a decimal number.") from exc
