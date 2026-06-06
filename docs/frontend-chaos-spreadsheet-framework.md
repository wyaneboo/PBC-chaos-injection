# Frontend Framework for Chaos Spreadsheet Generation

This document defines the frontend framework before implementation. It does not
change the CLI, pipeline, or workbook generation behavior.

## Goal

Build a local operator UI that lets a user configure chaos workbook generation
without memorizing CLI flags, preview the exact command that will run, execute
the run, and track pipeline progress from configuration through workbook export
and validation.

The frontend should feel like an operational audit-data generation tool, not a
marketing page. The first screen should be the generator workspace.

## Non-Goals for This Phase

- Do not replace the existing `pbc-chaos` CLI.
- Do not change workbook generation logic.
- Do not change chaos severity behavior.
- Do not implement the frontend yet.
- Do not add a web server yet.

## Recommended Future Stack

- Frontend: React + Vite, because the repo has no existing frontend framework.
- UI style: dense, quiet dashboard with clear forms, command preview, run log,
  progress timeline, and output artifact table.
- Backend runner: thin Python API or worker around the existing
  `pbc_chaos.batch.pipeline` functions.
- CLI fallback: spawn `pbc-chaos` only where direct Python integration is not
  enough.

## Primary User Flow

1. User opens the generator workspace.
2. User chooses a run mode.
3. UI shows only the relevant options for that mode.
4. UI validates required fields and ranges.
5. UI builds a read-only command preview.
6. User starts the run.
7. UI shows live pipeline stages, current workbook, event log, and output files.
8. UI runs validation or lets the user run it manually.
9. UI displays generated `.xlsx`, `.groundtruth.json`, and `manifest.csv`
   artifacts.

## Screen Layout

### App Shell

- Left rail: run modes and utilities.
- Main panel: selected command options.
- Right panel: command preview and run summary.
- Bottom panel: pipeline progress, event log, and output artifacts.

### Run Modes

- `Generate One`: one workbook for one named company.
- `Generate Batch`: many simulated companies at one chaos level.
- `Generate Dataset`: many simulated companies across a chaos range.
- `Generate From YAML`: legacy config-based generation.
- `Validate`: validate generated workbooks and sidecars.
- `Manifest`: rebuild or export a manifest CSV.
- `Score Extraction`: score external extraction output against ground truth.
- `Document Types`: list supported document type identifiers.

## CLI-to-UI Option Map

### Generate One

Command:

```powershell
pbc-chaos generate-one --company "ABC Sdn Bhd" --period "FY2025" --chaos-level 3 --seed 42 --output ./data/generated
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Company name | `--company` | Text input | Yes | Non-empty |
| Period | `--period` | Text input | Yes | `FY2025` or `2025` format |
| Chaos level | `--chaos-level` | Slider or segmented control `0..5` | Yes | Integer from `0` to `5` |
| Seed | `--seed` | Number input | No | Integer when present |
| Output directory | `--output` | Path input | No | Defaults to `outputs` |
| Unreproducible nightmare | `--unreproducible-nightmare` | Toggle | No | Boolean |

Expected artifacts:

- One `.xlsx` workbook.
- One `.groundtruth.json` sidecar.
- One `manifest.csv`.

### Generate Batch

Command:

```powershell
pbc-chaos generate-batch --companies 50 --period "FY2025" --chaos-level 3 --seed 1 --output ./data/generated
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Companies | `--companies` | Stepper or number input | Yes | Positive integer |
| Period | `--period` | Text input | Yes | `FY2025` or `2025` format |
| Chaos level | `--chaos-level` | Slider or segmented control `0..5` | Yes | Integer from `0` to `5` |
| Seed | `--seed` | Number input | No | Defaults to `1` |
| Output directory | `--output` | Path input | Yes | Non-empty path |
| Unreproducible nightmare | `--unreproducible-nightmare` | Toggle | No | Boolean |

Expected artifacts:

- One `.xlsx` workbook per simulated company.
- One `.groundtruth.json` sidecar per workbook.
- One combined `manifest.csv`.

### Generate Dataset

Command:

```powershell
pbc-chaos generate-dataset --companies 100 --min-chaos 0 --max-chaos 5 --period "FY2025" --seed 1 --output ./data/dataset
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Companies | `--companies` | Stepper or number input | Yes | Positive integer |
| Minimum chaos | `--min-chaos` | Slider or segmented control `0..5` | No | Integer from `0` to `5`; default `0` |
| Maximum chaos | `--max-chaos` | Slider or segmented control `0..5` | No | Integer from `0` to `5`; default `5`; must be `>= min-chaos` |
| Period | `--period` | Text input | No | Defaults to `FY2025` |
| Seed | `--seed` | Number input | No | Defaults to `1` |
| Output directory | `--output` | Path input | Yes | Non-empty path |
| Unreproducible nightmare | `--unreproducible-nightmare` | Toggle | No | Boolean |

Expected artifacts:

- One `.xlsx` workbook per simulated company.
- One `.groundtruth.json` sidecar per workbook.
- One combined `manifest.csv`.
- Manifest rows distributed across the selected chaos range.

### Generate From YAML

Command:

```powershell
pbc-chaos generate --config configs/default.yaml
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Config file | `--config` | Path input or file picker | No | Existing YAML path; defaults to `configs/default.yaml` |
| Unreproducible nightmare | `--unreproducible-nightmare` | Toggle | No | Boolean |

Notes:

- This mode maps legacy severity names to numeric chaos levels:
  `low -> 1`, `medium -> 3`, `high -> 5`.
- The UI should show a read-only summary after parsing the config:
  client count, output directory, seed, first financial year, and severity.

### Validate

Command:

```powershell
pbc-chaos validate --input ./data/generated
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Input directory | `--input` | Path input | Yes | Existing directory |

UI result:

- Passed or failed state.
- Workbook count when validation passes.
- Actionable issue list when validation fails.

### Manifest

Command:

```powershell
pbc-chaos manifest --input ./data/generated --output manifest.csv
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Input directory | `--input` | Path input | Yes | Existing directory |
| Output manifest path | `--output` | Path input | Yes | `.csv` path |

UI result:

- Manifest path.
- Row count.
- Missing workbook or sidecar errors.

### Score Extraction

Command:

```powershell
pbc-chaos score --groundtruth ./data/generated/ABC.groundtruth.json --extraction ./outputs/extraction_output.json --output-json score_report.json --output-md score_report.md
```

UI controls:

| UI label | CLI flag | Control | Required | Validation |
| --- | --- | --- | --- | --- |
| Ground truth file | `--groundtruth` | File picker | Yes | `.groundtruth.json` path |
| Extraction output | `--extraction` | File picker | Yes | JSON or one-table CSV path |
| JSON report path | `--output-json` | Path input | No | Defaults to `score_report.json` |
| Markdown report path | `--output-md` | Path input | No | Defaults to `score_report.md` |
| Fuzzy column threshold | `--fuzzy-column-threshold` | Slider or decimal input | No | Defaults to `0.82` |
| Numeric absolute tolerance | `--numeric-abs-tolerance` | Decimal input | No | Defaults to `0.01` |
| Numeric relative tolerance | `--numeric-rel-tolerance` | Decimal input | No | Defaults to `0.0001` |

UI result:

- Overall score.
- Links to JSON and Markdown reports.
- Metric summary table.

### Document Types

Command:

```powershell
pbc-chaos list-doc-types
```

UI controls:

- No input required.

UI result:

- Display supported document type IDs in a compact table.
- Use this as reference material for scoring and extraction workflows.

## Chaos Level Visualization

The chaos-level selector should show both number and meaning:

| Level | Label |
| --- | --- |
| `0` | Clean export |
| `1` | Minor formatting mess |
| `2` | Common finance team mess |
| `3` | Messy audit season file |
| `4` | Highly chaotic client submission |
| `5` | Nightmare PBC file |

For advanced users, add an expandable "Probability profile" panel. It should
show the effective probability keys for the selected severity:

- `merged_cells`
- `hidden_rows`
- `hidden_columns`
- `duplicated_headers`
- `inserted_notes`
- `subtotal_rows`
- `wrong_period_rows`
- `renamed_columns`
- `stringified_numbers`
- `formula_errors`
- `multiple_tables_in_one_sheet`
- `old_version_tabs`
- `hidden_reconciliation_tabs`
- `pbc_request_list`
- `tracker_status_noise`
- `tracker_deadline_noise`
- `tracker_visible_comments`
- `tracker_update_highlights`
- `tracker_instruction_blocks`

This panel should be read-only at first. Editing probabilities can be a later
feature that writes a custom YAML config.

## Command Preview Rules

The command preview is built from the selected mode and validated options.

Rules:

- Quote string values containing spaces.
- Hide optional flags when the user leaves them blank.
- Show defaulted values when they materially change output, such as `--period`
  on `generate-dataset`.
- Show `--unreproducible-nightmare` only when the toggle is on.
- Disable "Run" until all required options are valid.

Example preview for dataset mode:

```powershell
pbc-chaos generate-dataset --companies 25 --min-chaos 0 --max-chaos 5 --period "FY2025" --seed 1 --output ./data/dataset
```

## Progress Framework

The current CLI prints a completion summary after a generation command finishes.
Visible progress requires future instrumentation around the Python pipeline or a
structured event wrapper around CLI execution.

### Progress Model

Use two progress layers:

- Run progress: the whole command from start to finish.
- Workbook progress: the active workbook or company inside batch and dataset
  runs.

Statuses:

- `queued`
- `running`
- `succeeded`
- `failed`
- `warning`
- `skipped`

### Generation Pipeline Stages

| Stage ID | Label | Applies To | Notes |
| --- | --- | --- | --- |
| `validate_options` | Validate options | All commands | Check required fields, ranges, paths, and command shape |
| `resolve_config` | Resolve config | Generation | Load severity defaults, YAML config, and nightmare-mode settings |
| `prepare_companies` | Prepare companies | Batch, dataset | Build deterministic simulated company profiles |
| `parse_period` | Parse period | Generation | Accept `FY2025` or `2025` |
| `build_financial_truth` | Build financial truth | Generation | Create reconciliation context and canonical accounting data |
| `generate_documents` | Generate clean documents | Generation | Build PBC tracker and supporting schedules |
| `render_workbook` | Render workbook sheets | Generation | Create `.xlsx` workbook and sheets |
| `apply_layout_chaos` | Apply layout chaos | Generation | Insert layout, formatting, tracker, and workbook-level mess |
| `nightmare_post_pass` | Apply nightmare post-pass | Conditional | Runs only when unreproducible nightmare mode is enabled |
| `record_ground_truth` | Record ground truth | Generation | Build metadata sidecar content |
| `save_artifacts` | Save artifacts | Generation | Write workbook and `.groundtruth.json` |
| `write_manifest` | Write manifest | Generation, manifest | Write or rebuild `manifest.csv` |
| `validate_outputs` | Validate outputs | Validate, optional after generation | Check workbook and sidecar integrity |
| `score_extraction` | Score extraction | Score | Compare extraction output against ground truth |
| `complete` | Complete | All commands | Show artifacts, summary, warnings, and next actions |

### Stage Weighting

Initial weighting for generation runs:

| Stage | Weight |
| --- | --- |
| Validate options | 5% |
| Resolve config | 5% |
| Prepare companies and period | 5% |
| Build financial truth | 15% |
| Generate clean documents | 20% |
| Render workbook sheets | 15% |
| Apply layout chaos | 15% |
| Nightmare post-pass | 10% when enabled, otherwise skipped |
| Save artifacts and ground truth | 5% |
| Write manifest | 3% |
| Complete summary | 2% |

For batch and dataset runs, overall progress should combine completed workbook
count with active workbook stage progress:

```text
overall_percent =
  ((completed_workbooks + active_workbook_stage_percent) / total_workbooks) * 100
```

### Event Contract

Future backend events should use a stable JSON shape:

```json
{
  "run_id": "run_20260605_221500",
  "command": "generate-dataset",
  "status": "running",
  "stage_id": "apply_layout_chaos",
  "stage_label": "Apply layout chaos",
  "message": "Applying tracker status/date/comment noise",
  "overall_percent": 42.5,
  "workbook": {
    "index": 7,
    "total": 25,
    "company_name": "Apex Manufacturing 007 Sdn Bhd",
    "chaos_level": 4,
    "stage_percent": 0.6
  },
  "artifact": null,
  "timestamp": "2026-06-05T22:15:00+08:00"
}
```

Artifact event example:

```json
{
  "run_id": "run_20260605_221500",
  "command": "generate-one",
  "status": "running",
  "stage_id": "save_artifacts",
  "stage_label": "Save artifacts",
  "message": "Workbook and ground truth sidecar written",
  "overall_percent": 96,
  "workbook": {
    "index": 1,
    "total": 1,
    "company_name": "ABC Sdn Bhd",
    "chaos_level": 3,
    "stage_percent": 1
  },
  "artifact": {
    "type": "workbook",
    "path": "./data/generated/ABC_Sdn_Bhd_PBC_2025_severity_3.xlsx"
  },
  "timestamp": "2026-06-05T22:15:05+08:00"
}
```

### Progress UI Components

- Run header: command name, status, elapsed time, output directory.
- Overall progress bar: percentage and workbook count.
- Stage timeline: each stage with status icon, label, duration, and latest
  message.
- Active workbook card: company name, index, chaos level, seed, current stage.
- Event log: filterable rows for info, warning, error, and artifact events.
- Artifact table: type, file path, size when available, and open/copy actions.
- Validation panel: pass/fail summary and issue list.

## Backend Integration Options

### Option A: Direct Python Runner, Recommended

Create a small runner that calls existing Python functions instead of shelling
out to the CLI:

- `generate_single_workbook`
- `generate_batch_workbooks`
- `generate_mixed_chaos_dataset`
- `validate_generated_directory`
- `export_manifest`
- `compare_extraction_files`

Benefits:

- Stronger typing.
- Easier progress callbacks.
- Easier structured errors.
- No command parsing.

Required future change:

- Add an optional progress callback or event sink to batch pipeline helpers.

### Option B: CLI Process Wrapper

Spawn `pbc-chaos` commands from a local backend and stream stdout/stderr.

Benefits:

- Minimal changes to generation internals.
- Preserves exact CLI behavior.

Limitations:

- Current generation commands only print final summaries.
- Progress would be coarse until the CLI emits structured progress lines.
- Parsing human-readable output is fragile.

### Option C: Hybrid

Use direct Python integration for generation and validation, but keep a command
preview that mirrors the CLI exactly.

This is the preferred product behavior: users learn the CLI while the app gets
structured progress from Python internals.

## Future Directory Sketch

No files should be added yet beyond this framework document, but a future
implementation could use:

```text
ui/
  package.json
  index.html
  src/
    App.tsx
    components/
      CommandPreview.tsx
      OptionPanel.tsx
      ProgressTimeline.tsx
      ArtifactTable.tsx
      ValidationPanel.tsx
    features/
      generator/
      validation/
      scoring/
    lib/
      commandBuilder.ts
      optionSchema.ts
      progressEvents.ts

src/pbc_chaos/web/
  app.py
  runner.py
  events.py
```

## Validation Rules for the UI

- `chaos-level`, `min-chaos`, and `max-chaos` must be integers from `0` to `5`.
- `min-chaos` must be less than or equal to `max-chaos`.
- `companies` must be a positive integer.
- `period` must match `FY2025` or `2025`.
- Required path fields must be non-empty.
- `validate` input must be an existing directory.
- `score` ground truth should end with `.groundtruth.json`.
- Numeric scoring tolerances must be decimal values.
- Nightmare mode should show a credentials hint:
  if `GEMINI_API_KEY` is unavailable, the generator still runs with the local
  heuristic fallback and records that provider in metadata.

## Error and Warning States

Common user-facing failures:

- Invalid chaos level.
- Invalid period.
- Missing output path.
- Input directory does not exist.
- No workbooks found.
- Missing ground-truth sidecar.
- Invalid ground-truth JSON.
- Workbook sheet names do not match sidecar metadata.
- Extraction scoring input cannot be parsed.

Warnings:

- Nightmare mode enabled without `GEMINI_API_KEY`.
- Output directory already contains files.
- Dataset run will overwrite `manifest.csv`.
- Seed omitted for single generation, so filename and output may vary more.

## Output Summary

After a generation run, the UI should show:

- Workbook count.
- Output directory.
- Manifest path.
- Chaos level or chaos range.
- Whether nightmare mode was enabled.
- Number of `.groundtruth.json` sidecars.
- Validation status if validation was run.

Manifest columns to display:

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

## Acceptance Criteria for Future Implementation

- Every current CLI command is represented as a visible mode or utility.
- Every CLI flag has a corresponding UI control or documented default.
- The command preview exactly matches the selected options.
- Invalid options block execution before the backend starts.
- Batch and dataset runs show total workbook progress.
- Active workbook stage progress is visible.
- Skipped conditional stages, such as nightmare mode, are shown as skipped.
- Generated artifacts appear in a table as soon as they are written.
- Validation errors are shown as structured actionable messages.
- The UI remains usable for both one-workbook and 100-workbook runs.
