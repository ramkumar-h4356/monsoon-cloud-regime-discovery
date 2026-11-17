M5 refinement package

This is an additive package. It does not overwrite the original M5 script or outputs.

Prerequisites:
- Original M5 source and outputs must exist.
- M4 PCA score archives must exist.
- matplotlib must be installed.

Run tests:
python -m pytest tests/test_established_monsoon_tsne_refinement.py -q

Run refinement:
python src/08_dimensionality_reduction/established_monsoon_tsne_refinement.py

Refined outputs:
data/processed/clustering/established_monsoon/m5_tsne_refined/
