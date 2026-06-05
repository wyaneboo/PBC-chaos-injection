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

## First-Time User Guide

Follow these steps from the repository root.

1. Check Python.

   Use Python 3.11 or newer:

   ```powershell
   python --version
   ```

2. Create and activate a virtual environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the project.

   Install with development tools if you want to run tests:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```

   For generation only, this is enough:

   ```powershell
   python -m pip install -e .
   ```

4. Set up secrets only if you want unreproducible nightmare mode.

   Copy the example file and put your real Gemini API key in `.env`:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   The file should contain:

   ```dotenv
   GEMINI_API_KEY=your-gemini-api-key
   ```

   Keep `.env` local. It is ignored by Git.

5. Generate one workbook.

   ```powershell
   pbc-chaos generate-one --company "ABC Sdn Bhd" --period "FY2025" --chaos-level 3 --seed 42 --output ./data/generated
   ```

   This writes an `.xlsx`, a matching `.groundtruth.json`, and `manifest.csv`.

6. Generate a nightmare workbook.

   This uses the LangGraph post-pass. If `.env` has `GEMINI_API_KEY`, the Gemma
   planner is used; otherwise the local heuristic planner is used.

   ```powershell
   pbc-chaos generate-one --company "ABC Sdn Bhd" --period "FY2025" --chaos-level 5 --unreproducible-nightmare --output ./data/nightmare
   ```

7. Generate a dataset.

   ```powershell
   pbc-chaos generate-dataset --companies 25 --min-chaos 0 --max-chaos 5 --output ./data/dataset
   ```

   Add `--unreproducible-nightmare` if every generated workbook should get the
   non-deterministic review-agent post-pass.

8. Validate generated files.

   ```powershell
   pbc-chaos validate --input ./data/generated
   pbc-chaos validate --input ./data/dataset
   ```

9. Run the tests.

   ```powershell
   pytest
   ```

10. Inspect the outputs.

    Open the `.xlsx` file in Excel or LibreOffice. Use the `.groundtruth.json`
    sidecar to compare what a parser or AI extraction tool should have found.

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

Generate a nightmare workbook with the non-deterministic Gemma-backed review
agent:

Create a local `.env` file in the directory where you run `pbc-chaos`:

```dotenv
GEMINI_API_KEY=your-gemini-api-key
```

```powershell
pbc-chaos generate-one --company "ABC Sdn Bhd" --period "FY2025" --chaos-level 5 --unreproducible-nightmare --output ./data/generated
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

Add `--unreproducible-nightmare` to any generation command when you want the
non-deterministic review agent post-pass.

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
- PBC Request List
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

### Unreproducible Nightmare Mode

`unreproducible_nightmare_mode` is an optional post-pass for severity 5 style
workbooks. The normal deterministic workbook is generated first, then a review
agent chooses extra chaos actions and adds human-style notations anywhere in the
spreadsheet as visible reminder cells or Excel comments. Workbooks also include
a PBC request tracker sheet; severity 4 and 5 configs add tracker-specific
workflow chaos such as mixed statuses, unclear due dates, follow-up flags,
visible auditor comments, highlighted update rows, and client instruction
blocks.

The LLM planner uses Google's Gemini API with `gemma-4-31b-it` by default:

```yaml
severity: 5

unreproducible_nightmare_mode:
  enabled: true
  use_llm_planner: true
  llm_model: gemma-4-31b-it
  gemini_api_key_env: GEMINI_API_KEY
  notation_count: 30
  extra_tool_count: 5
```

Use the ready-made config:

```python
from pbc_chaos.config_loader import load_config
from pbc_chaos.pbc_workbook import generate_pbc_workbook

config = load_config("config/unreproducible-nightmare.yaml")
workbook = generate_pbc_workbook(company, period, config=config, seed=42)
```

The mode always runs through LangGraph. If `GEMINI_API_KEY` is not set, the
LangGraph planning node uses the local heuristic planner and records the
fallback reason in the ground-truth sidecar. Because this mode intentionally
uses non-seeded randomness in the final review pass, two runs with the same seed
can produce different workbook IDs, notations, and extra chaos choices.

Store the actual Gemini API key in a local `.env` file in the current working
directory. `.env` is ignored by Git; `.env.example` documents the required
variable name.

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
