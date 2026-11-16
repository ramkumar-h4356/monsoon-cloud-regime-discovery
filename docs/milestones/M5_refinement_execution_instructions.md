# M5 refinement — convergence and visual review

## Purpose
The original M5 runs reported 999 iterations against a 1,000-iteration budget. This refinement reruns the same four experiments with a 3,000-iteration budget and produces year-coloured visualizations.

## Preservation
Original results remain in:
`data/processed/clustering/established_monsoon/m5_tsne/`

Refined results are written separately to:
`data/processed/clustering/established_monsoon/m5_tsne_refined/`

No original M5 output is overwritten.

## Fixed experimental conditions
- Same M4 PCA score archives.
- Same deterministic sample: 500 observations per year, approximately balanced across dates.
- Same 10 PCA input dimensions.
- Same random seed: 42.
- Same perplexities: 30 and 50.
- Same t-SNE initialization, learning rate, Barnes-Hut method and angle.
- Only the iteration budget changes from 1,000 to 3,000.

## Run
```powershell
python -m pytest tests/test_established_monsoon_tsne_refinement.py -q
python src/08_dimensionality_reduction/established_monsoon_tsne_refinement.py
```

## Inspect
```powershell
$dir = "data/processed/clustering/established_monsoon/m5_tsne_refined"
Get-ChildItem $dir
Import-Csv "$dir/m5_refined_model_summary.csv" | Format-Table -AutoSize
```

Open the four `*_by_year.png` files. Review whether years are intermixed or concentrated in local regions. Do not interpret visual separation as causality or physical cloud regimes.

## Convergence interpretation
- If `iterations_used` is below 2,999, the optimizer stopped before reaching the configured ceiling.
- If `reached_iteration_limit` is true, convergence was not demonstrated within the 3,000-iteration budget.
- Compare KL divergence and trustworthiness with the original M5 summary. More iterations do not guarantee a better scientific embedding.
