# PBC Chaos Simulator

Architecture-first scaffold for a production-style synthetic audit PBC workbook
generator.

The simulator is designed to create realistic messy Excel workbooks for testing:

- document intelligence systems
- table extraction systems
- AI audit agents
- financial ETL pipelines
- schema normalization engines
- reconciliation systems
- layout understanding models

## Current Status

This repository currently contains the architecture and extension contracts only.
Workbook generation, chaos mutation logic, rendering, metadata writing, and validation
are intentionally stubbed for later implementation.

## Architecture

The system is built around one principle: create clean accounting truth first, then
turn it into messy human workbooks through controlled chaos injection.

Pipeline:

```text
YAML Config
  -> Run Context
  -> Client Profiles
  -> Canonical Financial Dataset
  -> Clean Document Generators
  -> Workbook Plans
  -> Chaos Engine
  -> XLSX Renderer
  -> Metadata Writer
  -> Validator
```

## Project Layout

```text
configs/                  YAML settings and severity profiles
docs/                     architecture and implementation roadmap
src/pbc_chaos/
  batch/                  multi-client orchestration
  chaos/                  chaos injector interfaces and placeholders
  config/                 typed settings
  core/                   shared enums and contexts
  financial_model/        clean accounting truth layer
  schemas/                normalized target schemas for supported documents
  generators/             document generator registry and placeholders
  metadata/               run manifest and sidecar metadata contracts
  reference_data/         reusable fake terms and future data libraries
  validation/             validation contracts
  workbook/               workbook plan IR and renderer contract
tests/                    architecture contract tests
```

## CLI Shape

Planned commands:

```powershell
pbc-chaos generate --config configs/default.yaml
pbc-chaos validate outputs/run_001
pbc-chaos list-doc-types
```

Only `list-doc-types` is meaningful before implementation. `generate` and `validate`
are wired but intentionally raise `NotImplementedError`.

## Required Document Types

The generator registry has placeholders for:

- Trial Balance
- General Ledger
- AP Aging
- AR Aging
- Bank Reconciliation
- Payroll Summary
- Payroll Detail
- Fixed Asset Register
- Inventory Listing
- Tax Computation
- SST/GST Report
- Commission Statement
- Insurance Production Report
- Customer Confirmation List
- Supplier Confirmation List
- Cash Flow Summary
- Journal Entry Listing
- Expense Claim Listing

## Next Implementation Step

Start with the canonical financial model and one clean document generator:

1. Generate chart of accounts and GL entries.
2. Implement Trial Balance generator.
3. Render a clean `.xlsx`.
4. Add metadata sidecars.
5. Add structural and semantic chaos.

See `docs/implementation-roadmap.md` for the full sequence.

## Normalized Schemas

The normalized target schema design is documented in
`docs/normalized-schemas.md` and implemented in `src/pbc_chaos/schemas`.

## Chaos Framework

The chaos injection framework is documented in `docs/chaos-framework.md`.
Current default chaos injectors are no-op placeholders that provide execution
slots for later mutation logic.

## Phase 7 Severity Config

Workbook messiness can be controlled with YAML presets in `config/`:

```python
from config_loader import load_config
from pbc_chaos import generate_pbc_workbook

config = load_config("config/nightmare.yaml")
workbook = generate_pbc_workbook(company, period, config=config, seed=42)
```

See `docs/chaos-severity-config.md` for every severity level and probability option.

## Ground Truth Metadata

Use the metadata exporter when you want a workbook and matching machine-readable
ground truth sidecar:

```python
from pbc_chaos.metadata import export_pbc_workbook

exported = export_pbc_workbook(
    company,
    period,
    output_dir="outputs",
    config="config/nightmare.yaml",
    seed=42,
)
```

This writes files such as `ABC_Sdn_Bhd_PBC_2025_nightmare.xlsx` and
`ABC_Sdn_Bhd_PBC_2025_nightmare.groundtruth.json`.
