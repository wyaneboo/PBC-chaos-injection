# Finance Report Shape Upgrade

## Implementation Status

**All four phases are implemented.**

Phase 3 (finance-native formatting + software signatures) and Phase 4 (remaining
archetypes + score-report/UI surfacing) on top of Phases 1-2:

- `src/pbc_chaos/workbook/report_archetypes.py` - adds **totaled_listing** for the
  trial balance and extends **detail_grouped** to fixed assets (by class),
  inventory (by category), and bank reconciliation (by item type). Also chooses a
  per-workbook accounting-software signature (`SQL Account`, `AutoCount`,
  `Sage UBS`, `Million`, `MYOB`) at severity >= 4.
- `src/pbc_chaos/workbook/formatting.py` - `apply_finance_value_formats()` gives
  amount columns thousands separators, parenthesised negatives, dash-for-zero and
  an occasional inline `RM`, and date columns a finance date format with a
  minority in a second format. Values stay numeric/date, so scoring is unaffected.
- `src/pbc_chaos/workbook/{layout_engine,workbook_mutations}.py` - render the
  software-signature stamp, a finance footer band (prepared/reviewed/system/page),
  and an as-at + currency line in the title block.
- `src/pbc_chaos/scoring/{report,comparator}.py` - `DocumentScore` now carries
  `report_form` and `scored_grain`, surfaced in the JSON and Markdown reports.
- `src/pbc_chaos/web/runner.py` + `ui/src/components/ArtifactTable.tsx` - the score
  result and UI list each sheet's report form, scored grain, and score.

Phases 1-2 (recap):

Phase 1 (AP/AR summary pivots) + Phase 2 (grouped-detail forms):

- `src/pbc_chaos/workbook/report_archetypes.py` - `build_report_frame()` dispatches
  per document type at severity >= 3:
  - **summary_pivot** for AP/AR aging - one row per vendor/customer, day-band
    bucket family, a balance column, and a footed grand-total row.
  - **detail_grouped** for general ledger, journal entries, payroll detail, and
    expense claims - detail rows ordered by account/voucher/department/employee,
    each group footed with a labelled subtotal, plus a grand total.
  - **listing** otherwise (and below severity 3).
  Every form carries a finance report title and header band. Canonical
  `GeneratedDocument.data` is never mutated.
- `src/pbc_chaos/pbc_workbook.py` - runs the report frame before visible aliasing
  and feeds the report title into the layout title block.
- `src/pbc_chaos/workbook/visible_schema.py` - `header_overrides` lets the
  archetype's chosen bucket family drive the visible headers while keeping the
  canonical-to-visible mapping accurate.
- `src/pbc_chaos/metadata/{schema,logger}.py` - records `report_form`,
  `report_grain_schema`, `expected_report_output`, `report_header_band`,
  bucket labels, subtotal labels, and the grand-total flag.
- `src/pbc_chaos/scoring/comparator.py` - `_expected_grain()` routes pivot and
  grouped sheets to the report grain (detail-only rows, no subtotal/total rows)
  so a finance-shaped extraction is scored fairly.
- Tests: `tests/test_report_archetypes.py` (23 tests).

The TB form is implemented as a footed totaled listing (rather than a full
open/move/close movement schedule) and bank recon as a grouped-by-item-type
listing (rather than a full statement form); both are reasonable finance shapes
and can be deepened later if needed.

## The Core Insight

Real accountants do not think in canonical schemas. They think in **reports**.

When a finance executive sends an "AP Aging", they do not send a normalized
open-item table. They send something that *reads like a report*:

```text
                 ABC Sdn Bhd
        Aged Creditors as at 31/12/2025
              (All amounts in RM)

Supp Code   Supplier                 Current     30 Days    60 Days   90 Days    120+       Balance
V0003       Capital Equipment Sdn Bhd  12,300.00   4,150.00       -          -      8,900.00   25,350.00
V0001       Alpha Office Supplies       2,100.00       -      1,250.00       -          -       3,350.00
...
                                       ----------  ---------  ---------  --------  ---------  ----------
            Grand Total               148,220.50  61,005.10  22,430.00  9,800.00  41,260.75  282,716.35

            Prepared by: Finance      Printed 04/01/2026     Page 1 of 1
```

or, from a smaller shop, something terser and worse formatted:

```text
Creditor Listing

Supp Code | Supplier Name | Outstanding
```

What the simulator currently produces instead, even after the visible-export
header aliasing, is a 45-row transaction-level dump whose spine is the canonical
model:

```text
client_id  financial_year  period_start  period_end  vendor_id  vendor_name  invoice_number  ...
```

`client_id`, `financial_year`, `period_start`, `period_end` are **backend-system
fields**. A finance executive would almost never type those into a workbook by
hand. They live in the report's *title block* ("as at 31/12/2025", "FY2025",
"ABC Sdn Bhd"), not as repeated table columns.

This upgrade is therefore **not** another round of column renaming. It is a new
layer that changes the **shape of the report**.

## What We Already Have (and Why It Is Not Enough)

The repo already implements a strong header layer:

- `src/pbc_chaos/workbook/visible_schema.py`
  - Per-document `VisibleExportProfile` with `department` and `erp_style`.
  - Header aliasing (`vendor_name` -> `Supplier` / `Creditor` / `Name`).
  - Column reordering to a finance-style `field_order`.
  - Drops `client_id`, `financial_year`, `period_start`, `period_end`,
    `currency` from the table at severity >= 3 and records them as
    `context_fields` instead.
  - Aging buckets already exist as discrete columns
    (`current_amount`, `bucket_1_30`, `bucket_31_60`, `bucket_61_90`,
    `bucket_over_90`) with aliases (`Current`, `1-30`, `31-60`, `61-90`, `90+`).
- `src/pbc_chaos/workbook/layout_engine.py`
  - Adds title blocks, client notes, subtotal rows, footer notes, merged cells,
    hidden rows/columns, reviewer comments, old tabs, hidden recon tabs.

So the *headers* and *workbook chrome* are already believable. The gap is the
**report archetype**: the overall form of the document.

Concretely, look at `src/pbc_chaos/generators/ap_aging.py`. It emits one row per
**open invoice** (45 of them), each with exactly one bucket column populated and
the other four zeroed. That is a perfectly good *canonical open-item ledger*. It
is **not** the *report* a finance team produces. A finance AP Aging is almost
always one of:

1. **Summary pivot** - one row per supplier, all bucket columns spread across,
   a `Balance` column that foots the buckets, and a grand-total row.
2. **Detail listing grouped by supplier** - invoice lines, but visually grouped
   under each supplier with a per-supplier subtotal and a grand total.

The current output is neither. It is a flat normalized table with a backend
spine. Aliasing the headers does not fix the *shape*; it just renames the spine.

## Proposed Upgrade: A Report Archetype Layer

Add one layer **above** the visible-export schema. It takes canonical document
data and re-expresses it in the *form* a finance team would actually save.

```text
canonical GeneratedDocument.data          (open items, backend spine)
  -> ReportArchetype.shape(...)           NEW: choose report form, pivot/group,
                                               foot totals, build the report
                                               header band, relocate context
        -> ReportFrame
  -> visible_schema aliasing              (existing: alias the frame's headers)
  -> layout_engine render + chrome        (existing: render header band, table,
                                               totals, then layout chaos)
  -> nightmare / human residue post-pass  (existing)
```

The canonical `GeneratedDocument.data` is **unchanged** - it stays the ground
truth for reconciliation and scoring. The `ReportFrame` is the client-facing
representation.

Suggested new module:

```text
src/pbc_chaos/workbook/report_archetypes.py
```

Suggested core types:

```python
@dataclass(frozen=True)
class ReportFrame:
    report_title: str                 # "Aged Creditors as at 31/12/2025"
    report_subtitle: str | None       # "(All amounts in RM)"
    header_band: tuple[HeaderLine, ...]   # company / period / currency lines
    table: pd.DataFrame               # the body finance would recognize
    grouping_key: str | None          # e.g. "vendor_id" for detail-grouped form
    group_subtotals: bool
    grand_total: bool
    report_form: str                  # "summary_pivot" | "detail_grouped" | "listing"
    archetype_id: str                 # "ap_aged_creditors_summary"
    software_signature: str | None    # "SQL Account" | "AutoCount" | "UBS" | None
    aggregated_canonical_view: pd.DataFrame  # canonical data at the report grain


@dataclass(frozen=True)
class HeaderLine:
    label: str | None                 # "As at" / None for a free line
    value: str                        # "31/12/2025"
    canonical_field: str | None       # which context field this represents
```

### 1. Aging Summary Pivot (the headline change)

For AP Aging and AR Aging, add a `summary_pivot` form that aggregates the
canonical open items by counterparty:

- Group by `vendor_id` / `vendor_name` (AP) or `customer_id` / `customer_name`
  (AR).
- Sum each bucket column across the group:
  `current_amount`, `bucket_1_30`, `bucket_31_60`, `bucket_61_90`,
  `bucket_over_90`.
- Add a `Balance` / `Outstanding` column = sum of the buckets (ties to
  `outstanding_amount`).
- Append a **grand-total row** that foots every bucket and the balance.

Bucket labels then become real finance day-bands. Map the canonical buckets to
a label family chosen per seed:

| Canonical column  | Label family A | Label family B | Label family C |
| ----------------- | -------------- | -------------- | -------------- |
| `current_amount`  | `Current`      | `Not Due`      | `0-30`         |
| `bucket_1_30`     | `30 Days`      | `1-30`         | `31-60`        |
| `bucket_31_60`    | `60 Days`      | `31-60`        | `61-90`        |
| `bucket_61_90`    | `90 Days`      | `61-90`        | `91-120`       |
| `bucket_over_90`  | `120+`         | `90+`          | `120+`         |

Note the deliberate ambiguity finance reports actually contain: family A's
"30 Days" means "1-30 days" and family C shifts the whole window by one band.
This is realistic and is exactly the kind of messiness extractors should be
tested against. Record the chosen mapping in ground truth so scoring stays fair.

Optional generator change for a true five-overdue-band report (`30/60/90/120+`
as five *overdue* columns): extend `aging_bucket()` in
`src/pbc_chaos/generators/_finance_seed.py` to split `91_120` and `over_120`.
Today it tops out at `over_90`, so "120+" is currently a relabel of `over_90`,
not a distinct band. Splitting is optional and only needed if you want the fifth
band to carry independent values.

A finance AP Aging summary at moderate severity should look like:

```text
Supp Code   Supplier                 Current     30 Days    60 Days   90 Days    120+       Balance
V0003       Capital Equipment Sdn Bhd  12,300.00   4,150.00       -          -      8,900.00   25,350.00
...
            Grand Total               148,220.50  61,005.10  22,430.00  9,800.00  41,260.75  282,716.35
```

### 2. Report Title Vocabulary

The current sheet title is a backend string:

```text
AP Aging - PBC support FY2025 RM (2025-01-01 to 2025-12-31)
```

That is robotic. Finance reports carry a *named* report title plus a "as at"
line. Add a per-document title vocabulary, selected by seed:

| Document         | Report titles a finance team would use                         |
| ---------------- | -------------------------------------------------------------- |
| AP Aging         | `Aged Creditors`, `Creditor Listing`, `AP Ageing Summary`, `Supplier Aging` |
| AR Aging         | `Aged Debtors`, `Debtor Listing`, `AR Ageing`, `Collection Report` |
| Trial Balance    | `Trial Balance`, `Nominal Ledger`, `TB as at <date>`           |
| General Ledger   | `GL Detail`, `Ledger Listing`, `Account Transactions`          |
| Fixed Assets     | `Fixed Asset Register`, `FA Listing`, `Asset Schedule`         |
| Bank Recon       | `Bank Reconciliation`, `Cash Book Recon`, `Bank Rec`           |
| Payroll Summary  | `Payroll Summary`, `Salary Summary`, `Payroll Run`            |
| Inventory        | `Stock Listing`, `Inventory Valuation`, `Stock Report`         |

Render it as `"<title> as at <dd/mm/yyyy>"` (or `for the year ended ...`),
not as the canonical period range.

### 3. The Report Header Band (where context belongs)

The fields the user flagged - `client_id`, `financial_year`, `period_start`,
`period_end`, `currency` - are exactly the context that finance puts in the
**report header band**, not in table columns. The `header_band` should carry
them as merged title lines above the table:

```text
ABC Sdn Bhd                          <- company_name (client_id is implicit)
Aged Creditors                       <- report title
as at 31 December 2025               <- period_end
All amounts in Ringgit Malaysia      <- currency
```

`visible_schema` already relocates these to `context_fields` at severity >= 3.
The upgrade is to actually **render them in the report header band** with finance
phrasing, instead of leaving them as abstract `context_field_locations` entries
that nothing draws. Record each header line's `canonical_field` so the scorer
knows the period/currency are present-but-contextual, not missing.

### 4. Report-Native Totals and Subtotals

Finance reports always foot. Replace the generic `add_subtotal_rows()` (which
inserts crude subtotal rows) with **archetype-aware totals**:

- `summary_pivot`: one grand-total row footing every numeric column.
- `detail_grouped`: a labelled subtotal per group ("Total - Alpha Office
  Supplies") plus a grand total. Label vocabulary: `Total`, `Sub-total`,
  `Grand Total`, sometimes blank with just a top border.
- `listing`: optional single total row, sometimes none.

Totals should *tie out* (the grand total equals the column sum), because real
exports compute. Tie-out also lets the scorer verify reconstruction.

### 5. Finance-Native Formatting

The chaos engine already does generic damage. Add formatting that is specific to
finance exports rather than generic Excel mess:

- Inline currency text: `RM 1,234.56`, `RM1,234.56`, or a leading `RM` column.
- Thousands separators, with some amounts stored as text (already supported via
  `stringify_numeric_cells`) so totals silently break.
- Negatives in parentheses: `(1,234.56)`.
- Zero shown as `-` or blank in bucket cells (very common in aging reports).
- Dates as `31/12/2025`, `31-Dec-25`, or `31.12.2025`, inconsistent within a
  sheet.
- A footer band: `Prepared by:`, `Reviewed by:`, `Printed on <date>`,
  `Page 1 of 1`.

### 6. Accounting-Software Signatures (optional, high realism)

Malaysian SME books come out of a handful of packages, each with a recognizable
export header/footer. `visible_schema` already carries an `erp_style` string but
nothing renders it. Promote it to a `software_signature` that draws a signature
band:

- `SQL Account`, `AutoCount`, `UBS` / `Sage`, `Million`, `MYOB`.
- Each gets a small header tag line and/or footer (e.g. a "Generated by ..."
  footer, a company-registration line, a specific column captioning style).

This makes different workbooks look like they came from different clients'
systems, not from one generator.

## Per-Document Archetypes

| Document        | Default report form | Alternate forms                       |
| --------------- | ------------------- | ------------------------------------- |
| AP Aging        | `summary_pivot`     | `detail_grouped`                      |
| AR Aging        | `summary_pivot`     | `detail_grouped`, statement-style     |
| Trial Balance   | `listing` (Dr/Cr)   | movement schedule (open/move/close)   |
| General Ledger  | `detail_grouped` by account | flat `listing`                |
| Journal Entries | `detail_grouped` by JV | flat `listing`                     |
| Fixed Assets    | `listing` w/ class subtotals | movement schedule            |
| Bank Recon      | recon statement form | `listing`                            |
| Payroll Summary | `listing` w/ dept subtotals | `summary_pivot` by dept       |
| Payroll Detail  | `detail_grouped` by dept | flat `listing`                   |
| Inventory       | `listing` w/ category subtotals | `summary_pivot` by warehouse |
| Expense Claims  | `detail_grouped` by employee | flat `listing`               |
| PBC Request List | unchanged (tracker) | unchanged                            |

Aging documents are where the gap is widest and the payoff is highest, so build
`summary_pivot` first.

## Component Changes

### 1. Add the archetype module

Create `src/pbc_chaos/workbook/report_archetypes.py`:

- `build_report_frame(document, company, period, sheet_name, seed, severity)
  -> ReportFrame`.
- Deterministic from `(document_type, seed, severity)`.
- Produces the reshaped `table`, the `header_band`, totals flags, the
  `report_title`, the `software_signature`, and the `aggregated_canonical_view`.
- Leaves `document.data` untouched.

### 2. Wire it into `pbc_workbook.py`

In `generate_pbc_workbook_with_ground_truth`, insert the archetype step before
`build_visible_export` and feed its `table` into the visible-export aliasing:

```python
frame = build_report_frame(
    document=document,
    company=company,
    period=period,
    sheet_name=sheet_name,
    seed=(0 if seed is None else seed) + index,
    severity=resolved.severity,
)
visible_export = build_visible_export(
    document=document.with_data(frame.table),  # alias the reshaped frame
    company=company,
    period=period,
    sheet_name=sheet_name,
    seed=(0 if seed is None else seed) + index,
    severity=resolved.severity,
)
```

Then have the layout step render `frame.header_band` and totals as the report's
own title block, instead of the generic backend-style `title=` string currently
passed to `layout_config(...)`. The generic `add_title_block` becomes a fallback
only when an archetype provides no header band.

### 3. Extend ground truth

Add optional fields to `SheetGroundTruth`
(`src/pbc_chaos/metadata/schema.py`), all backward-compatible:

```python
report_archetype_id: str | None = None
report_form: str | None = None              # summary_pivot | detail_grouped | listing
report_title_text: str | None = None
grouping_key: str | None = None
bucket_label_mapping: dict[str, str] = field(default_factory=dict)
header_band_fields: dict[str, str] = field(default_factory=dict)   # canonical_field -> rendered text
software_signature: str | None = None
report_grain_schema: tuple[str, ...] = ()   # columns at the report grain
expected_report_output: tuple[dict[str, Any], ...] = ()  # aggregated_canonical_view rows
```

Keep `clean_canonical_schema` and `expected_extraction_output` (open-item grain)
for reconciliation. The new `report_grain_schema` / `expected_report_output`
describe the *report* grain so a pivot can be scored against the right truth.

### 4. Scoring impact (the main dependency)

This is the one part that needs care, because `summary_pivot` **changes the
grain**. The comparator in `src/pbc_chaos/scoring/comparator.py` currently
compares extraction output to canonical open-item rows. A vendor-summary
extraction cannot be compared row-for-row to 45 open items.

Recommended scorer model:

- Detect `report_form` from ground truth.
- For `summary_pivot`, score against `expected_report_output`
  (`aggregated_canonical_view`), not the open-item rows.
- For `detail_grouped`, score row values against canonical open items but
  ignore inserted subtotal/total rows (tag them in ground truth).
- Treat `header_band_fields` (period, currency, FY) as **context fields**: do
  not penalize an extractor for not returning them as row columns when they are
  represented in the header band.
- Header/column-mapping metrics use the visible (aliased) headers of the report
  frame.

This keeps scoring fair while still testing the harder skill: mapping a messy
finance report back to canonical concepts and the right grain.

### 5. Severity ramp

- Severity 0: canonical clean export (unchanged baseline; no archetype).
- Severity 1-2: report title + header band, but keep the flat listing form and
  most columns; light formatting.
- Severity 3-4: full archetype (summary pivot / grouped detail), totals, context
  relocated to the header band, day-band labels, inline currency.
- Severity 5: add software signatures, inconsistent date/number formats,
  parenthesized negatives, blank-as-`-`, footer bands, and the existing layout +
  nightmare chaos on top.

## Implementation Phases

### Phase 1: Aging summary pivot + report titles (highest payoff) - DONE

- `report_archetypes.py` with `summary_pivot` for AP and AR.
- Report title vocabulary and a rendered header band carrying
  company / as-at / currency.
- Grand-total row that ties out.
- Ground truth records `report_form`, `report_grain_schema`,
  `expected_report_output`, `bucket_label_mapping`.
- Scoring routes aging pivots to the report-grain truth.

### Phase 2: Grouped-detail form + report-native totals - DONE

- `detail_grouped` for GL, JE, payroll detail, expense claims.
- Per-group subtotals + grand total, replacing generic `add_subtotal_rows()` on
  archetype sheets.
- Ground truth tags subtotal/total rows so scoring ignores them.

### Phase 3: Finance-native formatting + software signatures - DONE

- Inline currency, parenthesized negatives, blank/`-` zeros, mixed date formats.
- `software_signature` header/footer bands per package.
- Tests that different seeds yield different signatures.

### Phase 4: Remaining archetypes + scoring/UI reporting - DONE

- TB movement schedule, FA/inventory subtotal-by-class forms, bank recon
  statement form.
- Score reports surface report-form detection and report-grain accuracy.
- UI metadata displays archetype id, report form, and header-band placement.

## Test Plan

Unit tests:

- AP/AR `summary_pivot` collapses open items to one row per counterparty and the
  grand total foots every bucket and balance.
- Bucket label family is deterministic per seed and recorded in ground truth.
- Header band carries `period_end` / `currency` and they are absent from the
  table columns at severity >= 3.
- Report titles are drawn from the finance vocabulary, never the backend string.
- `aggregated_canonical_view` ties to `outstanding_amount` totals from canonical.

Integration tests:

- Generate at severity 4 and assert no aging sheet contains `client_id`,
  `financial_year`, `period_start`, or `period_end` as table columns.
- Assert each aging sheet has a report title row and a grand-total row.
- Workbook opens with `openpyxl`; ground-truth sidecar stays valid.
- Scoring runs against both an open-item extraction (detail) and a vendor-summary
  extraction (pivot) and scores each against the correct grain.

Regression tests:

- Severity 0 remains a clean canonical export.
- Existing visible-schema tests (`tests/test_visible_schema.py`) still pass for
  non-report documents.
- Reconciliation still uses canonical generator data, untouched by the frame.
- `renamed_columns_mapping` and `visible_columns_mapping` remain populated.

## Risks and Mitigations

Risk: pivoting changes the grain and breaks row-level scoring.
Mitigation: record `report_grain_schema` + `expected_report_output` and route
the scorer by `report_form`.

Risk: totals and pivots drift from canonical (don't tie out).
Mitigation: compute the frame *from* canonical and assert tie-out in tests.

Risk: the "120+" band implies a fifth overdue bucket the generator does not
produce. Mitigation: by default relabel `over_90` as `120+`/`90+`; only split
`aging_bucket()` into `91_120` / `over_120` if a distinct fifth band is wanted.

Risk: archetype + visible-schema + layout chaos compound into unrealistic mess.
Mitigation: the archetype owns the report's title block and totals; reduce the
generic `add_title_block` / `add_subtotal_rows` to fallbacks on archetype sheets.

## Recommendation

Implement this as a **report-archetype layer above the existing visible-export
schema**, not as a generator rewrite. The canonical open-item data is valuable
and stays internal. The client-facing workbook should become a *report* - named,
pivoted-or-grouped, footed, with context in the header band and amounts in
finance formatting.

The smallest useful first release is Phase 1: AP and AR as summary pivots, with
finance report titles, a rendered header band, a tie-out grand total, and
scoring routed to the report grain. That directly answers the feedback - the
workbook should look like a report a finance team produced, not a canonical data
model with formatting chaos applied on top.
