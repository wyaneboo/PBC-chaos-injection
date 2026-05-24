# CLI Usage Examples

Generate one workbook:

```powershell
pbc-chaos generate-one --company "ABC Sdn Bhd" --period "FY2025" --chaos-level 4 --seed 42
```

Generate a batch:

```powershell
pbc-chaos generate-batch --companies 50 --period "FY2025" --chaos-level 3 --output ./data/generated
```

Generate a mixed chaos dataset:

```powershell
pbc-chaos generate-dataset --companies 100 --min-chaos 0 --max-chaos 5 --output ./data/dataset
```

Validate generated files:

```powershell
pbc-chaos validate --input ./data/generated
```

Export a manifest:

```powershell
pbc-chaos manifest --input ./data/generated --output manifest.csv
```

All generation commands write `.xlsx` workbooks, `.groundtruth.json` sidecars,
and a `manifest.csv` with the Phase 9 dataset schema.
