from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "src" / "08_dimensionality_reduction"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import numpy as np
import pandas as pd
import pytest

from established_monsoon_tsne import run_tsne, stratified_year_date_sample


def make_metadata(rows_per_date=20):
    rows = []
    for year in (2010, 2011):
        for day in range(1, 4):
            for cell in range(rows_per_date):
                rows.append({
                    "year": year,
                    "date": f"{year}-07-{day:02d}",
                    "latitude": 6.5 + cell * 0.1,
                    "longitude": 68.5 + cell * 0.1,
                })
    return pd.DataFrame(rows)


def test_sample_is_reproducible_and_unique():
    metadata = make_metadata()
    first = stratified_year_date_sample(metadata, sample_per_year=12, random_state=7)
    second = stratified_year_date_sample(metadata, sample_per_year=12, random_state=7)
    assert np.array_equal(first, second)
    assert len(first) == 24
    assert len(np.unique(first)) == 24


def test_sample_balances_years_and_dates():
    metadata = make_metadata()
    indices = stratified_year_date_sample(metadata, sample_per_year=12, random_state=7)
    sampled = metadata.iloc[indices]
    assert sampled.groupby("year").size().to_dict() == {2010: 12, 2011: 12}
    for _, group in sampled.groupby("year"):
        counts = group.groupby("date").size().tolist()
        assert max(counts) - min(counts) <= 1


def test_sample_rejects_insufficient_year_rows():
    metadata = make_metadata(rows_per_date=2)
    with pytest.raises(ValueError, match="only"):
        stratified_year_date_sample(metadata, sample_per_year=10)


def test_sample_rejects_insufficient_date_rows():
    rows = []
    for year in (2010, 2011):
        for day, count in ((1, 2), (2, 5), (3, 5)):
            for cell in range(count):
                rows.append({
                    "year": year,
                    "date": f"{year}-07-{day:02d}",
                    "latitude": 6.5 + cell * 0.1,
                    "longitude": 68.5 + cell * 0.1,
                })
    metadata = pd.DataFrame(rows)
    with pytest.raises(ValueError, match="requires"):
        stratified_year_date_sample(metadata, sample_per_year=10)


def test_tsne_returns_finite_two_dimensional_embedding():
    rng = np.random.default_rng(10)
    scores = rng.normal(size=(120, 5))
    embedding, kl, iterations = run_tsne(scores, perplexity=10, random_state=3)
    assert embedding.shape == (120, 2)
    assert np.isfinite(embedding).all()
    assert np.isfinite(kl)
    assert iterations > 0


def test_tsne_rejects_sample_not_larger_than_perplexity():
    with pytest.raises(ValueError, match="more rows than perplexity"):
        run_tsne(np.ones((10, 3)), perplexity=10)
