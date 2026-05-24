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

This repository now includes the single-workbook generator, ground-truth sidecar
export, chaos severity configuration, and a Phase 9 batch simulation CLI.

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

## CLI Usage

Install the package in editable mode if the `pbc-chaos` command is not already
available:

```powershell
pip install -e .
```

Generate one workbook:

```powershell
pbc-chaos generate-one --company "ABC Sdn Bhd" --period "FY2025" --chaos-level 4 --seed 42
```

Generate a batch of simulated companies at one chaos level:

```powershell
pbc-chaos generate-batch --companies 50 --period "FY2025" --chaos-level 3 --output ./data/generated
```

Generate a mixed-chaos dataset. The dataset command defaults to `FY2025` unless
`--period` is provided:

```powershell
pbc-chaos generate-dataset --companies 100 --min-chaos 0 --max-chaos 5 --output ./data/dataset
```

Validate generated workbooks and ground-truth JSON sidecars:

```powershell
pbc-chaos validate --input ./data/generated
```

Export or rebuild a manifest CSV from an existing generated directory:

```powershell
pbc-chaos manifest --input ./data/generated --output manifest.csv
```

Score an AI/data extraction output against simulator ground truth:

```powershell
pbc-chaos score --groundtruth ./data/generated/ABC.groundtruth.json --extraction ./outputs/extraction_output.json --output-json score_report.json --output-md score_report.md
```

Legacy config-based generation is still available:

```powershell
pbc-chaos generate --config configs/default.yaml
pbc-chaos list-doc-types
```

Generation commands write `.xlsx` files, `.groundtruth.json` sidecars, and a
`manifest.csv` in the output directory. CLI validation exits with status code `1`
and prints actionable errors when input directories are missing, sidecars are
missing or invalid, workbooks cannot be opened, or workbook sheet names no longer
match ground truth.

## Extraction Scoring

The scoring framework compares an extractor's normalized JSON or one-table CSV
output against a simulator `.groundtruth.json` sidecar. It writes both
`score_report.json` and a human-readable `score_report.md`.

Supported metrics:

- document classification accuracy
- table boundary detection accuracy
- header detection accuracy
- column mapping accuracy
- row extraction accuracy
- numeric value accuracy with configurable tolerance
- date normalization accuracy
- discrepancy detection accuracy

Extractor JSON can use `documents`, `sheets`, `tables`, or
`extracted_documents`. Each document/table can include:

```json
{
  "document_type": "trial_balance",
  "sheet_name": "Trial Balance",
  "table_location": {
    "start_row": 3,
    "start_column": 2,
    "end_row": 55,
    "end_column": 18,
    "header_row": 3
  },
  "headers": ["client_id", "financial_year", "account_code", "closing_balance"],
  "column_mapping": {
    "Closing Bal": "closing_balance"
  },
  "rows": [
    {
      "client_id": "client_001",
      "financial_year": 2025,
      "account_code": "1000",
      "closing_balance": 12345.67
    }
  ],
  "detected_discrepancies": []
}
```

The comparator includes exact matching, fuzzy column matching, row count
difference, numeric tolerance checks, and precision/recall/F1 summaries.

### Manifest Columns

Dataset manifests use this schema:

- `workbook_id`
- `company_name`
- `period`
- `chaos_level`
- `file_path`
- `groundtruth_path`
- `document_types`
- `row_count`
- `discrepancy_count`
- `generated_at`

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
