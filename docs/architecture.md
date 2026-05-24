# PBC Chaos Simulator Architecture

This project is structured as an enterprise-style synthetic audit evidence generator.
The design separates clean accounting truth from messy workbook presentation.

## Pipeline

1. Load YAML configuration.
2. Create a deterministic run context.
3. Generate client and engagement profiles.
4. Generate canonical financial data.
5. Build clean workbook plans for each document type.
6. Apply controlled cross-document discrepancies.
7. Apply chaos injectors.
8. Render real `.xlsx` files.
9. Write metadata and run manifests.
10. Validate workbook integrity and configured relationships.

## Core Principle

The simulator should not generate random broken spreadsheets directly. It should first
create a coherent financial model, then degrade the resulting documents through explicit,
metadata-tracked chaos.

## Module Boundaries

- `config`: YAML loading and typed simulator settings.
- `core`: shared enums, run contexts, and stable project types.
- `reference_data`: reusable fake names, chart-of-accounts templates, ERP presets, and terms.
- `financial_model`: canonical accounting data generation.
- `schemas`: normalized target schemas for every supported financial document type.
- `generators`: pluggable document generators that produce workbook plans.
- `workbook`: intermediate workbook representation and `.xlsx` rendering.
- `chaos`: reusable chaos injectors and chaos event logging.
- `metadata`: run manifests, sidecar metadata, and chaos audit trail records.
- `batch`: orchestration for many clients, years, and document types.
- `validation`: workbook and accounting relationship checks.

## Extension Points

New document type:

1. Add a `DocumentType` enum value.
2. Add a normalized `DocumentSchema`.
3. Create a generator implementing `DocumentGenerator`.
4. Register it in the schema and generator registries.
5. Add validation rules if the document participates in reconciliation.

New chaos pattern:

1. Implement `ChaosInjector`.
2. Declare order, probability key, category, and document scope.
3. Use `ChaosContext` for deterministic randomness.
4. Return a replacement `WorkbookPlan`.
5. Emit `ChaosEvent` records for each mutation.
6. Register it in `ChaosInjectorRegistry`.

New ERP style:

1. Add a reference profile under `reference_data`.
2. Map document generator defaults to the profile.
3. Add semantic and formatting terms that match the profile.
