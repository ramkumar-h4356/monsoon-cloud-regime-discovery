# M5 execution instructions

## 1. Extract
Extract the package into the repository root, preserving the included relative paths. Do not extract into `src`, `tests` or `docs`.

## 2. Run unit tests
From the repository root:

```powershell
python -m pytest tests/test_established_monsoon_tsne.py -q
```

Expected: 6 tests pass.

## 3. Run M5
The M3 and M4 outputs must already exist. Run:

```powershell
python src/08_dimensionality_reduction/established_monsoon_tsne.py
```

The script performs four t-SNE fits. Runtime depends on CPU and installed scikit-learn version.

## 4. Inspect outputs
```powershell
$dir = "data/processed/clustering/established_monsoon/m5_tsne"
Get-ChildItem $dir

Import-Csv "$dir/m5_tsne_model_summary.csv" | Format-Table -AutoSize
Get-Content "$dir/established_monsoon_m5_tsne_manifest.json"
```

## 5. Report back
Send:
- Complete test output.
- Complete execution summary.
- `m5_tsne_model_summary.csv` contents.
- Output file listing.

Do not commit M5 until execution, output review and scoped Git staging are complete.
