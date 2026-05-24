"""Command-line entry points for the simulator.

The CLI is wired as an architecture placeholder. Generation behavior is implemented
inside the batch pipeline in later phases.
"""

from pathlib import Path

import typer

from pbc_chaos.config.settings import load_settings

app = typer.Typer(help="Generate messy synthetic audit PBC Excel workbooks.")


@app.command()
def generate(config: Path = typer.Option(Path("configs/default.yaml"), exists=True)) -> None:
    """Generate a batch run from a YAML config."""
    settings = load_settings(config)
    raise NotImplementedError(
        "Batch generation is not implemented yet. "
        f"Loaded config for {settings.batch.client_count} clients."
    )


@app.command()
def validate(run: Path = typer.Argument(..., exists=True)) -> None:
    """Validate a generated run directory."""
    raise NotImplementedError(f"Validation is not implemented yet for run: {run}")


@app.command("list-doc-types")
def list_doc_types() -> None:
    """List supported document type identifiers."""
    from pbc_chaos.core.types import DocumentType

    for doc_type in DocumentType:
        typer.echo(doc_type.value)

