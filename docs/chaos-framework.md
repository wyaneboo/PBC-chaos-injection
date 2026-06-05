# Chaos Injection Framework

The chaos framework provides execution infrastructure only. Concrete spreadsheet
mutation behavior should be implemented later inside individual injectors.

## Responsibilities

- Register chaos injectors by stable name.
- Execute injectors in deterministic order.
- Respect config-level enabled/disabled injector gates.
- Respect probability gates.
- Provide deterministic per-client, per-workbook, per-injector randomness.
- Record execution status for every injector.
- Emit metadata-friendly `ChaosEvent` records for actual mutations.
- Provide immutable workbook-plan mutation helpers.

## Main Types

- `ChaosEngine`: orchestrates injector execution for a workbook plan.
- `ChaosContext`: per-workbook and per-injector execution context.
- `BaseChaosInjector`: base class for concrete injectors.
- `ChaosResult`: return value from injectors and engine runs.
- `InjectorExecution`: status record for one injector execution.
- `ChaosEvent`: mutation metadata record.
- `ChaosInjectorRegistry`: named injector registry.

## Injector Lifecycle

For each workbook:

1. `ChaosEngine` builds a root `ChaosContext`.
2. Injectors are sorted by `order`.
3. For each injector, the engine creates a deterministic forked context.
4. The engine checks whether the injector is enabled.
5. The engine checks whether the injector supports the document type.
6. `BaseChaosInjector` applies the probability gate.
7. The injector mutates the `WorkbookPlan` and emits `ChaosEvent` records.
8. The engine records `InjectorExecution` status.

## Default Injector Slots

The default registry contains no-op placeholders in this order:

1. `structural`
2. `semantic`
3. `formatting`
4. `human_residue`
5. `data_quality`
6. `formula`
7. `versioning`
8. `file_naming`

These are framework participants only. Their actual mutation logic has not been
implemented yet.

## Concrete Workbook Path

The current production workbook generator also has direct openpyxl mutation
helpers for generated `.xlsx` files. The PBC request tracker chaos is implemented
there first because it needs precise worksheet layout control: instruction
blocks, filters, freeze panes, mixed status/date/comment cells, highlighted
update rows, and bounded nightmare-agent row tools. These behaviors can later be
ported into formal injector classes once the workbook-plan injector layer becomes
the primary rendering path.

## Implementing a Real Injector Later

Create a class that subclasses `BaseChaosInjector` and overrides `mutate`.

```python
class HiddenRowsInjector(BaseChaosInjector):
    name = "hidden_rows"
    category = "structural"
    order = 120
    probability_key = "hidden_rows"

    def mutate(self, plan, context):
        # Build a replacement WorkbookPlan using helpers from chaos.mutations.
        event = self.event(
            context,
            "Hid rows in the selected worksheet.",
            sheet_name="GL",
            details={"rows": [12, 13]},
        )
        return ChaosResult(plan=updated_plan, events=(event,))
```

## Determinism

Randomness is seeded from:

- root seed
- client ID
- financial year
- document type
- suggested filename
- injector name

This lets the same run reproduce the same chaos while keeping each injector's
random stream isolated.
