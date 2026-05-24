"""Command-line entry points for the simulator."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, TypeVar

import typer

from pbc_chaos.batch.pipeline import (
    BatchGenerationResult,
    BatchPipelineError,
    export_manifest,
    generate_batch_workbooks,
    generate_mixed_chaos_dataset,
    generate_single_workbook,
    validate_generated_directory,
)
from pbc_chaos.config.settings import load_settings
from pbc_chaos.scoring import ScoringConfig, compare_extraction_files


app = typer.Typer(help="Generate messy synthetic audit PBC Excel workbooks.")
T = TypeVar("T")


@app.command("generate-one")
def generate_one(
    company: str = typer.Option(..., "--company", help="Company name for the workbook."),
    period: str = typer.Option(..., "--period", help="Financial period, for example FY2025."),
    chaos_level: int = typer.Option(..., "--chaos-level", help="Integer chaos level from 0 to 5."),
    seed: int | None = typer.Option(None, "--seed", help="Optional deterministic seed."),
    output: Path = typer.Option(
        Path("outputs"),
        "--output",
        help="Directory where the workbook, sidecar JSON, and manifest are written.",
    ),
) -> None:
    """Generate one workbook and matching ground-truth JSON."""

    result = _handle_cli_error(
        lambda: generate_single_workbook(
            company_name=company,
            period_label=period,
            chaos_level=chaos_level,
            output_dir=output,
            seed=seed,
        )
    )
    _echo_generation_summary(result)


@app.command("generate-batch")
def generate_batch(
    companies: int = typer.Option(..., "--companies", help="Number of simulated companies."),
    period: str = typer.Option(..., "--period", help="Financial period, for example FY2025."),
    chaos_level: int = typer.Option(..., "--chaos-level", help="Integer chaos level from 0 to 5."),
    output: Path = typer.Option(..., "--output", help="Output directory for generated files."),
    seed: int = typer.Option(1, "--seed", help="Deterministic base seed."),
) -> None:
    """Generate many workbooks at a single chaos level."""

    result = _handle_cli_error(
        lambda: generate_batch_workbooks(
            company_count=companies,
            period_label=period,
            chaos_level=chaos_level,
            output_dir=output,
            seed=seed,
        )
    )
    _echo_generation_summary(result)


@app.command("generate-dataset")
def generate_dataset(
    companies: int = typer.Option(..., "--companies", help="Number of simulated companies."),
    min_chaos: int = typer.Option(0, "--min-chaos", help="Minimum chaos level from 0 to 5."),
    max_chaos: int = typer.Option(5, "--max-chaos", help="Maximum chaos level from 0 to 5."),
    output: Path = typer.Option(..., "--output", help="Output directory for generated files."),
    period: str = typer.Option("FY2025", "--period", help="Financial period, for example FY2025."),
    seed: int = typer.Option(1, "--seed", help="Deterministic base seed."),
) -> None:
    """Generate many workbooks with mixed chaos levels."""

    result = _handle_cli_error(
        lambda: generate_mixed_chaos_dataset(
            company_count=companies,
            period_label=period,
            min_chaos=min_chaos,
            max_chaos=max_chaos,
            output_dir=output,
            seed=seed,
        )
    )
    _echo_generation_summary(result)


@app.command()
def validate(
    input: Path = typer.Option(..., "--input", help="Directory containing generated files."),
) -> None:
    """Validate generated workbooks and ground-truth JSON sidecars."""

    report = validate_generated_directory(input)
    if report.passed:
        workbook_count = len(tuple(report.run_path.glob("*.xlsx"))) if report.run_path.exists() else 0
        typer.echo(f"Validation passed: {workbook_count} workbook(s) checked in {report.run_path}")
        raise typer.Exit(0)

    typer.secho(f"Validation failed: {len(report.issues)} issue(s).", fg=typer.colors.RED, err=True)
    for issue in report.issues:
        path = f" ({issue.path})" if issue.path else ""
        typer.secho(f"- [{issue.code}] {issue.message}{path}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command("manifest")
def manifest_command(
    input: Path = typer.Option(..., "--input", help="Directory containing generated files."),
    output: Path = typer.Option(..., "--output", help="Manifest CSV path to write."),
) -> None:
    """Export a dataset manifest CSV from generated files."""

    manifest_path = _handle_cli_error(lambda: export_manifest(input_dir=input, output_path=output))
    typer.echo(f"Wrote manifest: {manifest_path}")


@app.command("score")
def score_extraction(
    groundtruth: Path = typer.Option(
        ...,
        "--groundtruth",
        help="Simulator .groundtruth.json file.",
    ),
    extraction: Path = typer.Option(
        ...,
        "--extraction",
        help="Extractor output JSON or one-table CSV.",
    ),
    output_json: Path = typer.Option(
        Path("score_report.json"),
        "--output-json",
        help="JSON score report path.",
    ),
    output_md: Path = typer.Option(
        Path("score_report.md"),
        "--output-md",
        help="Markdown score report path.",
    ),
    fuzzy_column_threshold: float = typer.Option(
        0.82,
        "--fuzzy-column-threshold",
        help="Minimum fuzzy similarity for header/column matches.",
    ),
    numeric_abs_tolerance: str = typer.Option(
        "0.01",
        "--numeric-abs-tolerance",
        help="Absolute tolerance for numeric value matches.",
    ),
    numeric_rel_tolerance: str = typer.Option(
        "0.0001",
        "--numeric-rel-tolerance",
        help="Relative tolerance for numeric value matches.",
    ),
) -> None:
    """Score extraction output against simulator ground truth."""

    abs_tolerance = _decimal_option(numeric_abs_tolerance, "numeric-abs-tolerance")
    rel_tolerance = _decimal_option(numeric_rel_tolerance, "numeric-rel-tolerance")
    config = ScoringConfig(
        fuzzy_column_threshold=fuzzy_column_threshold,
        numeric_abs_tolerance=abs_tolerance,
        numeric_rel_tolerance=rel_tolerance,
    )
    report = _handle_cli_error(
        lambda: compare_extraction_files(
            groundtruth_path=groundtruth,
            extraction_output_path=extraction,
            json_report_path=output_json,
            markdown_report_path=output_md,
            config=config,
        )
    )
    typer.echo(f"Overall score: {report.overall_score:.3f}")
    typer.echo(f"Wrote JSON report: {output_json}")
    typer.echo(f"Wrote Markdown report: {output_md}")


@app.command()
def generate(config: Path = typer.Option(Path("configs/default.yaml"), exists=True)) -> None:
    """Generate a batch run from a legacy YAML config."""

    settings = _handle_cli_error(lambda: load_settings(config))
    severity_by_name = {"low": 1, "medium": 3, "high": 5}
    chaos_level = severity_by_name[settings.chaos.severity.value]
    year = settings.batch.financial_years[0]
    result = _handle_cli_error(
        lambda: generate_batch_workbooks(
            company_count=settings.batch.client_count,
            period_label=f"FY{year}",
            chaos_level=chaos_level,
            output_dir=settings.run.output_dir,
            seed=settings.run.seed,
        )
    )
    _echo_generation_summary(result)


@app.command("list-doc-types")
def list_doc_types() -> None:
    """List supported document type identifiers."""

    from pbc_chaos.core.types import DocumentType

    for doc_type in DocumentType:
        typer.echo(doc_type.value)


def _handle_cli_error(callback: Callable[[], T]) -> T:
    try:
        return callback()
    except BatchPipelineError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    except (KeyError, ValueError) as exc:
        typer.secho(f"Configuration error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    except OSError as exc:
        typer.secho(f"File error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _decimal_option(value: str, name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        typer.secho(f"Error: {name} must be a decimal number.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _echo_generation_summary(result: BatchGenerationResult) -> None:
    workbook_word = "workbook" if len(result.records) == 1 else "workbooks"
    typer.echo(f"Generated {len(result.records)} {workbook_word}.")
    typer.echo(f"Output directory: {result.records[0].exported.workbook_path.parent}")
    typer.echo(f"Manifest: {result.manifest_path}")


if __name__ == "__main__":
    app()
