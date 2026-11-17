"""
M26 — Master End-to-End Orchestrator Pipeline

Executes the complete, integrated M26 empirical analysis pipeline deterministically:
1. Phase 2: Daily cloud aggregation (Shifted & Calendar), IMD rainfall extraction, and Space-Time Join.
2. Phase 3: Regime-conditioned rainfall statistics, continuous fraction regressions, spatial/temporal dynamics.
3. Phase 4: Multi-dimensional sensitivity suite and spatial-temporal block bootstrap inference.
4. Phase 5: Publication-quality figure generation.
"""

from pathlib import Path
import time
import json

from src.integration.rainfall_association.daily_regime_aggregation import run_daily_aggregation
from src.integration.rainfall_association.imd_rainfall_loader import run_rainfall_loader
from src.integration.rainfall_association.spatial_temporal_join import run_spatial_temporal_join
from src.integration.rainfall_association.regime_rainfall_statistics import run_regime_statistics
from src.integration.rainfall_association.continuous_fraction_association import run_continuous_fraction_analysis
from src.integration.rainfall_association.spatial_temporal_analysis import run_spatial_temporal_analysis
from src.integration.rainfall_association.sensitivity_suite import run_sensitivity_suite
from src.integration.rainfall_association.statistical_inference_framework import run_statistical_inference
from src.integration.rainfall_association.generate_m26_figures import run_figure_generation

ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT / "reports/integration/m26"


def main():
    start_time = time.time()
    print("=" * 80)
    print("STARTING MILESTONE M26: INTEGRATED END-TO-END RAINFALL VALIDATION")
    print("=" * 80)
    
    timings = {}
    
    # Stage 1: Daily Aggregation
    t0 = time.time()
    print("\n>>> Stage 1: Daily Cloud Regime Aggregation")
    run_daily_aggregation()
    timings["daily_cloud_aggregation_seconds"] = round(time.time() - t0, 2)
    
    # Stage 2: IMD Rainfall Extraction
    t0 = time.time()
    print("\n>>> Stage 2: IMD Gridded Rainfall Extraction and QC Masking")
    run_rainfall_loader()
    timings["imd_rainfall_extraction_seconds"] = round(time.time() - t0, 2)
    
    # Stage 3: Spatial-Temporal Join
    t0 = time.time()
    print("\n>>> Stage 3: Space-Time Join and Population Verification")
    run_spatial_temporal_join()
    timings["spatial_temporal_join_seconds"] = round(time.time() - t0, 2)
    
    # Stage 4: Regime Distribution & Occurrence Statistics
    t0 = time.time()
    print("\n>>> Stage 4: Regime Distribution, Occurrence, and Extreme Attribution Statistics")
    run_regime_statistics()
    timings["regime_statistics_seconds"] = round(time.time() - t0, 2)
    
    # Stage 5: Continuous Soft Fraction Regressions
    t0 = time.time()
    print("\n>>> Stage 5: Continuous Fraction Spearman Correlations & Multivariable Regression")
    run_continuous_fraction_analysis()
    timings["continuous_fraction_seconds"] = round(time.time() - t0, 2)
    
    # Stage 6: Spatial and Temporal Dynamics
    t0 = time.time()
    print("\n>>> Stage 6: Cell-Wise Spatial Composites and Daily Regime Persistence Dynamics")
    run_spatial_temporal_analysis()
    timings["spatial_temporal_dynamics_seconds"] = round(time.time() - t0, 2)
    
    # Stage 7: Sensitivity Analysis Suite
    t0 = time.time()
    print("\n>>> Stage 7: Multi-Dimensional Sensitivity Analysis Suite")
    run_sensitivity_suite()
    timings["sensitivity_suite_seconds"] = round(time.time() - t0, 2)
    
    # Stage 8: Spatial-Temporal Block Bootstrap Inference
    t0 = time.time()
    print("\n>>> Stage 8: Spatial-Temporal Block Bootstrap (1,000 Replicates)")
    run_statistical_inference()
    timings["block_bootstrap_seconds"] = round(time.time() - t0, 2)
    
    # Stage 9: Diagnostic Visualizations
    t0 = time.time()
    print("\n>>> Stage 9: Publication-Quality Diagnostic Figure Generation")
    run_figure_generation()
    timings["figure_generation_seconds"] = round(time.time() - t0, 2)
    
    total_duration = round(time.time() - start_time, 2)
    timings["total_pipeline_duration_seconds"] = total_duration
    
    print("\n" + "=" * 80)
    print(f"MILESTONE M26 EXECUTION COMPLETED SUCCESSFULLY IN {total_duration} SECONDS")
    print("=" * 80)
    print(json.dumps(timings, indent=2))
    
    # Save timings log
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "m26_execution_timings.json", "w") as f:
        json.dump(timings, f, indent=2)


if __name__ == "__main__":
    main()
