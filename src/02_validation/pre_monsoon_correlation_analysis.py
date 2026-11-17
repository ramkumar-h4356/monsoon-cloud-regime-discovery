
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

DATA_DIR = Path("data/interim/ceres_seasonal/pre_monsoon")
REPORT_DIR = Path("reports/feature_analysis")
FIGURE_DIR = Path("results/figures/pre_monsoon")

REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(DATA_DIR.glob("*.nc"))

if len(files) != 12:
    raise ValueError(f"Expected 12 files, found {len(files)}")

# Use a reproducible sample to keep memory usage manageable.
# Sampling is for exploratory correlation analysis, not a
# replacement for full-resolution scientific validation.
rng = np.random.default_rng(42)
samples = []

for file in files:
    print("Processing:", file.name)

    with xr.open_dataset(file) as ds:
        variables = [
            name for name in ds.data_vars
            if ds[name].ndim == 3
            and set(ds[name].dims) == {"time", "lat", "lon"}
            and np.issubdtype(ds[name].dtype, np.number)
        ]

        if len(variables) != 45:
            print(
                f"WARNING: {file.name} contains "
                f"{len(variables)} eligible variables"
            )

        # Sample identical time-space locations for all
        # variables, preserving their pairwise relationships.
        n_total = (
            ds.sizes["time"]
            * ds.sizes["lat"]
            * ds.sizes["lon"]
        )

        n_sample = min(10000, n_total)
        indices = rng.choice(
            n_total, size=n_sample, replace=False
        )

        frame = pd.DataFrame(index=range(n_sample))

        for variable in variables:
            values = ds[variable].transpose(
                "time", "lat", "lon"
            ).values.reshape(-1)

            frame[variable] = values[indices]

        frame["year"] = int(
            pd.Timestamp(ds.time.values[0]).year
        )

        samples.append(frame)

data = pd.concat(samples, ignore_index=True)

print("\nTotal sampled observations:", len(data))

features = data.drop(columns=["year"])

# Pairwise Pearson correlation uses only observations
# where both variables have valid values.
correlation = features.corr(method="pearson")

correlation.to_csv(
    REPORT_DIR / "01_correlation_matrix.csv"
)

availability = (
    features.notna().mean() * 100
).sort_values()

availability.rename(
    "sample_availability_percent"
).to_csv(
    REPORT_DIR / "02_feature_availability.csv"
)

pairs = []

names = correlation.columns

for i in range(len(names)):
    for j in range(i + 1, len(names)):
        value = correlation.iloc[i, j]

        if pd.notna(value):
            valid_pairs = int(
                (
                    features[names[i]].notna()
                    & features[names[j]].notna()
                ).sum()
            )

            pairs.append({
                "feature_1": names[i],
                "feature_2": names[j],
                "correlation": float(value),
                "absolute_correlation": float(abs(value)),
                "paired_observations": valid_pairs,
            })

pairs_df = pd.DataFrame(pairs)

pairs_df = pairs_df.sort_values(
    "absolute_correlation",
    ascending=False
)

pairs_df.to_csv(
    REPORT_DIR / "03_all_correlation_pairs.csv",
    index=False
)

strong_pairs = pairs_df[
    (pairs_df["absolute_correlation"] >= 0.90)
    & (pairs_df["paired_observations"] >= 1000)
]

strong_pairs.to_csv(
    REPORT_DIR / "04_strong_correlations.csv",
    index=False
)

# Correlation heatmap
fig, ax = plt.subplots(figsize=(16, 14))

masked = np.ma.masked_invalid(correlation.values)

image = ax.imshow(
    masked,
    cmap="coolwarm",
    vmin=-1,
    vmax=1
)

ax.set_xticks(range(len(names)))
ax.set_yticks(range(len(names)))

ax.set_xticklabels(
    names, rotation=90, fontsize=6
)
ax.set_yticklabels(
    names, fontsize=6
)

ax.set_title(
    "Pre-Monsoon CERES Cloud-Property Correlations\n"
    "2010–2021 | Sampled Pearson Correlation"
)

fig.colorbar(
    image, ax=ax,
    label="Pearson correlation"
)

fig.tight_layout()

figure_path = (
    FIGURE_DIR / "06_correlation_heatmap.png"
)

fig.savefig(
    figure_path,
    dpi=200,
    bbox_inches="tight"
)

plt.close(fig)

print("\n=== CORRELATION ANALYSIS COMPLETE ===")
print("Strongly correlated pairs:", len(strong_pairs))

print("\nTop correlated pairs:")
print(strong_pairs.head(15).to_string(index=False))

print("\nLowest-availability features:")
print(availability.head(10))

print("\nReports saved to:", REPORT_DIR)
print("Heatmap saved to:", figure_path)
