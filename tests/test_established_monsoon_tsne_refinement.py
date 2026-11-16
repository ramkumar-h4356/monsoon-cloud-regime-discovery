from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "src" / "08_dimensionality_reduction"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from established_monsoon_tsne_refinement import MAX_ITERATIONS, make_tsne


def test_refinement_uses_3000_iteration_budget():
    assert MAX_ITERATIONS == 3000


def test_tsne_configuration_preserves_requested_perplexity_and_seed():
    model = make_tsne(perplexity=30, random_state=42)
    assert model.perplexity == 30
    assert model.random_state == 42
    assert model.n_components == 2
    assert model.init == "pca"
    assert model.learning_rate == "auto"
    assert model.method == "barnes_hut"
