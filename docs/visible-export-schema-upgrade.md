# Visible Export Schema Upgrade

## Purpose

This upgrade addresses auditor feedback that generated PBC workbooks still look
AI-generated because visible table headers expose the simulator's canonical data
model. The current output can contain fields such as `client_id`,
`financial_year`, `period_start`, `period_end`, `currency`, `account_code`, and
`account_name` across many sheets. Real client files more often look like
department exports, ERP extracts, and manually maintained schedules with
inconsistent terminology.

The goal is to keep canonical data internally for reconciliation, scoring, and
ground truth, while making the Excel workbook look like it came from multiple
client departments.

## Repo Feasibility Check

The upgrade is doable without rewriting the financial generators.

Checked components:

- `src/pbc_chaos/generators/base.py`
  - `GeneratedDocument.data` is a canonical pandas DataFrame.
  - `build_metadata()` already records `expected_canonical_schema`.
- `src/pbc_chaos/generators/_finance_seed.py`
  - `base_common()` injects shared canonical fields into financial schedules.
  - This is useful for internal consistency, but should not always become
    visible workbook columns.
- `src/pbc_chaos/pbc_workbook.py`
  - This is the best insertion point. The workbook currently writes
    `document.data` directly to Excel using `dataframe_to_rows(...)`.
  - A visible export transform can run immediately before the worksheet append.
- `src/pbc_chaos/workbook/layout_engine.py`
  - Layout chaos already runs after the worksheet table is written.
  - Existing formatting, notes, subtotal rows, hidden rows, old tabs, comments,
    and nightmare-mode mutations can remain mostly unchanged.
- `src/pbc_chaos/workbook/workbook_mutations.py`
  - `rename_random_columns()` already proves aliasing is supported.
  - It is too narrow for this upgrade because it only renames a limited number
    of existing headers and cannot drop, reorder, or semantically profile whole
    document types.
- `src/pbc_chaos/reference_data/terms.py`
  - Existing alias families are reusable, but need document-specific and
    department-specific profiles.
- `src/pbc_chaos/metadata/logger.py`
  - Ground truth logs clean canonical records before scoring.
  - It already records renamed column mappings, so it can be extended to record
    visible export mappings, omitted canonical fields, and context-field
    locations.
- `src/pbc_chaos/metadata/schema.py`
  - Backward-compatible optional fields can be added to `SheetGroundTruth`.
- `src/pbc_chaos/scoring/comparator.py`
  - Scoring currently compares extraction output to `clean_canonical_schema`.
  - Dropping common metadata columns from visible tables is feasible, but scoring
    needs to distinguish table-visible fields from context fields inferred from
    titles, filenames, or side cells.

## Current Problem

The current architecture generates correct canonical records first, then applies
mostly layout and formatting chaos. This means the workbook can still preserve a
single clean data model underneath the mess:

```text
canonical DataFrame
  -> written directly to worksheet
  -> layout chaos
  -> occasional column renames
```

That produces believable Excel damage, but not enough client-department
fingerprint. The problem is semantic consistency, not only formatting
consistency.

## Proposed Architecture

Add a visible export schema layer between canonical document generation and
Excel writing:

```text
canonical GeneratedDocument.data
  -> VisibleExportProfile
  -> visible DataFrame for Excel
  -> layout chaos
  -> nightmare/human residue post-pass
```

Canonical records remain unchanged for reconciliation and ground truth. The
visible DataFrame is only the client-facing representation.

Suggested new module:

```text
src/pbc_chaos/workbook/visible_schema.py
```

Suggested core types:

```python
@dataclass(frozen=True)
class VisibleExportProfile:
    profile_id: str
    department: str
    erp_style: str
    column_map: Mapping[str, str]
    visible_fields: tuple[str, ...]
    context_fields: Mapping[str, str]
    ambiguous_headers: Mapping[str, str]


@dataclass(frozen=True)
class VisibleExportResult:
    data: pd.DataFrame
    profile_id: str
    visible_to_canonical: dict[str, str]
    canonical_to_visible: dict[str, str]
    omitted_fields: tuple[str, ...]
    context_fields: dict[str, str]
```

## Visible Schema Rules

The visible export transform should do more than randomly rename columns.

1. Choose a profile per document type and seed.
2. Select a field subset suitable for that document.
3. Drop or relocate repeated common fields:
   - `client_id`
   - `financial_year`
   - `period_start`
   - `period_end`
   - `currency`
4. Reorder columns to match common ERP or department exports.
5. Rename headers using document-specific terms.
6. Allow the same visible label to mean different canonical fields on different
   sheets.
7. Record the mapping in ground truth, not in the workbook.

## Example Department Fingerprints

Trial Balance:

| Canonical field | Possible visible header |
| --- | --- |
| `account_code` | `A/C`, `Nominal Code`, `GL Code` |
| `account_name` | `Description`, `Nominal Description` |
| `closing_debit` | `Dr` |
| `closing_credit` | `Cr` |
| `closing_balance` | `CY Bal`, `Balance`, `RM` |
| `financial_year` | title cell such as `FY2025` |

General Ledger:

| Canonical field | Possible visible header |
| --- | --- |
| `account_code` | `Acct`, `GL Account`, `Ledger` |
| `posting_date` | `Post Dt`, `GL Date` |
| `document_number` | `Doc No`, `Ref Doc` |
| `counterparty_name` | `Vendor`, `Name`, `Party` |
| `amount_signed` | `Net Amt`, `Txn Amount` |

AR Aging:

| Canonical field | Possible visible header |
| --- | --- |
| `customer_name` | `Customer`, `Debtor`, `Bill To` |
| `invoice_number` | `Inv No` |
| `aging_date` | `As At` |
| `outstanding_amount` | `O/S`, `Balance Due` |
| `bucket_over_90` | `90+`, `Over 90` |

AP Aging:

| Canonical field | Possible visible header |
| --- | --- |
| `vendor_name` | `Supplier`, `Creditor`, `Payee` |
| `invoice_number` | `Bill No`, `Inv #` |
| `due_date` | `Due Dt` |
| `outstanding_amount` | `Open Amt`, `Unpaid Amount` |
| `currency` | `Curr` or omitted if workbook currency is in title |

Fixed Assets:

| Canonical field | Possible visible header |
| --- | --- |
| `asset_id` | `Asset Ref`, `Asset No` |
| `asset_category` | `AC`, `Class`, `Asset Cat` |
| `acquisition_date` | `Cap Date`, `In Service` |
| `cost` | `Cost`, `Orig Cost` |
| `net_book_value` | `NBV`, `Carrying Amt` |

Payroll:

| Canonical field | Possible visible header |
| --- | --- |
| `employee_id` | `Emp No`, `Staff ID` |
| `employee_name` | `Employee`, `Name` |
| `department` | `Dept`, `Cost Ctr` |
| `gross_pay` | `Gross` |
| `net_pay` | `Net` |

Semantic ambiguity examples:

| Sheet | Visible header | Canonical meaning |
| --- | --- | --- |
| General Ledger | `AC` | `account_code` |
| Fixed Assets | `AC` | `asset_category` |
| Expense Claims | `AC` | `approval_code` or `approval_status` |
| Trial Balance | `Description` | `account_name` |
| GL | `Description` | `transaction description` |
| AP Aging | `Name` | `vendor_name` |
| AR Aging | `Name` | `customer_name` |

## Component Changes

### 1. Add Visible Export Profiles

Create `src/pbc_chaos/workbook/visible_schema.py`.

Responsibilities:

- Build deterministic visible profiles from `DocumentType`, company, period,
  severity, and seed.
- Produce the visible DataFrame to write to Excel.
- Return mapping metadata.
- Keep canonical `GeneratedDocument.data` unchanged.

The first implementation should cover generated workbook document types in
`src/pbc_chaos/pbc_workbook.py`:

- PBC Request List
- Trial Balance
- General Ledger
- Bank Recon
- AP Aging
- AR Aging
- Fixed Assets
- Payroll Summary
- Payroll Detail
- Inventory
- Journal Entries
- Expense Claims

### 2. Insert Transform in Workbook Generation

Update `src/pbc_chaos/pbc_workbook.py`:

```python
visible_export = build_visible_export(
    document=document,
    company=company,
    period=period,
    sheet_name=sheet_name,
    seed=(0 if seed is None else seed) + index,
    severity=resolved.severity,
)

for row in dataframe_to_rows(visible_export.data, index=False, header=True):
    worksheet.append(row)
```

Then start the ground-truth sheet with both canonical and visible metadata:

```python
logger.start_sheet(document, worksheet)
logger.record_visible_export(worksheet.title, visible_export)
```

### 3. Extend Ground Truth

Add optional fields to `SheetGroundTruth`:

```python
visible_export_profile: str | None = None
visible_columns_mapping: dict[str, str] = field(default_factory=dict)
canonical_to_visible_columns: dict[str, str] = field(default_factory=dict)
omitted_canonical_fields: tuple[str, ...] = ()
context_field_locations: dict[str, str] = field(default_factory=dict)
ambiguous_visible_headers: dict[str, str] = field(default_factory=dict)
```

Keep `renamed_columns_mapping` for backward compatibility with layout chaos.
The new mapping should represent the intentional export profile. Existing layout
renames can still happen afterward as secondary human edits.

### 4. Adjust Layout Column Renaming

Once visible export profiles are active, `rename_random_columns()` should become
a secondary mutation only. It should not be responsible for realism.

Recommended behavior:

- At severity 0, keep clean canonical exports for baseline tests.
- At severity 1 to 2, apply visible aliases but keep most canonical fields.
- At severity 3 to 5, use department profiles, drop common metadata columns, and
  allow semantic ambiguity.

### 5. Update Scoring Semantics

This is the main dependency to handle carefully.

Current scoring uses:

- `clean_canonical_schema`
- `expected_extraction_output`
- document primary keys from `src/pbc_chaos/schemas/documents.py`

If common context fields are dropped from visible tables, extractors may not
return `client_id`, `financial_year`, or `period_end` as row fields. Scoring
should avoid penalizing that when those fields are intentionally represented in
workbook context.

Recommended scorer model:

- `clean_canonical_schema`: all canonical fields.
- `visible_table_schema`: canonical fields represented as table columns.
- `context_fields`: canonical fields represented outside the table.
- Header and column mapping metrics use `visible_table_schema`.
- Row, numeric, and date metrics compare canonicalized rows after applying
  context fields from workbook-level or sheet-level metadata.

This keeps extraction scoring fair while still testing whether systems can map
messy client headers back to canonical concepts.

## Implementation Phases

### Phase 1: Header Profile Layer

Doable with low risk.

- Add visible export profiles.
- Rename all visible headers by document type before layout chaos.
- Keep all canonical columns present.
- Record `visible_columns_mapping`.
- Add tests that no severity 3 to 5 sheet exposes raw canonical headers such as
  `account_code` unless the profile intentionally allows it.

### Phase 2: Common Metadata Relocation

Medium risk because scoring expectations need refinement.

- Drop or relocate `client_id`, `financial_year`, `period_start`, `period_end`,
  and `currency` from most tables.
- Place context in title blocks, subtitle rows, sheet names, workbook filename,
  or note cells.
- Extend ground truth with `context_field_locations`.
- Update scoring to treat these as context fields.

### Phase 3: Semantic Ambiguity and Department Dialects

Medium risk, high realism payoff.

- Add same-header-different-meaning profiles.
- Add department vocabulary:
  - Finance close team
  - AR collections
  - AP/payables
  - Payroll/HR
  - Fixed assets
  - Warehouse/inventory
- Add tests that the same canonical field does not always use the same alias
  across workbook sheets.

### Phase 4: Scoring and UI Reporting

Medium risk.

- Update score reports to show visible-to-canonical mapping accuracy.
- Update UI metadata displays if they currently assume only
  `renamed_columns_mapping`.
- Surface profile IDs and context-field placement in debug artifacts.

## Test Plan

Unit tests:

- `visible_schema` maps canonical fields to deterministic visible headers for a
  fixed seed.
- Different document types produce different aliases for common fields.
- The same visible header can intentionally map to different canonical fields on
  different sheets.
- Common metadata fields are omitted only at configured severities.
- Ground truth records visible mappings and omitted fields.

Integration tests:

- Generate a workbook at severity 5 and assert visible table headers do not
  expose the canonical schema spine across all sheets.
- Confirm workbook opens with `openpyxl`.
- Confirm ground-truth sidecar remains valid.
- Confirm scoring still works with a canonical extraction output.
- Confirm layout chaos still records table location after visible export.

Regression tests:

- Severity 0 remains a clean export.
- Existing PBC request list layout tests continue to pass.
- Existing reconciliation tests continue to use canonical generator data.
- `renamed_columns_mapping` remains populated for older consumers.

## Risks and Mitigations

Risk: scoring becomes unfair when fields are not visible table columns.

Mitigation: add explicit `visible_table_schema` and `context_fields` to ground
truth, then score table header extraction against visible fields and row values
against canonical rows plus inferred context.

Risk: layout chaos renames already-profiled headers into weaker aliases.

Mitigation: reduce `rename_random_columns()` after profiles are enabled, or make
it profile-aware.

Risk: too many aliases make generated files inconsistent in unrealistic ways.

Mitigation: use profiles, not fully random aliases. A sheet should look like one
department's export, while different sheets can disagree.

Risk: primary-key row matching degrades when `client_id`, `financial_year`, or
`period_end` are omitted.

Mitigation: scorer should use visible business keys where available, then apply
context fields during canonicalization. It can still fall back to row order for
small schedules.

## Recommendation

Implement this as a workbook export-layer upgrade, not as a generator rewrite.
The current canonical data model is valuable and should stay internal. The
visible Excel representation should become a lossy, department-specific export
profile with explicit ground-truth mappings.

The smallest useful first release is Phase 1 plus partial Phase 2:

- Profiled headers for every non-tracker sheet.
- Reordered columns.
- Common metadata columns renamed or hidden at moderate severity.
- Common metadata columns relocated out of the main table at high severity.
- Ground truth records profile mappings.

This directly addresses the auditor's strongest point: the workbook should no
longer look like one canonical data model with formatting chaos applied on top.
