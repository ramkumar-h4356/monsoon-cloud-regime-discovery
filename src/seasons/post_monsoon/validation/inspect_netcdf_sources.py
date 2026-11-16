from pathlib import Path
import json
import xarray as xr
import numpy as np

BASE = Path(r"D:\Project Simulator\monsoon_cloud_research")

SOURCES = {
    "CERES_POST_MONSOON": BASE / "data/interim/ceres_seasonal/post_monsoon",
    "IMD_RAINFALL": BASE / "raw_data/IMD_Rainfall",
}

OUTPUT = Path(
    r"D:\Project Simulator\post_monsoon_research"
    r"\post_monsoon_review_package\M19_netcdf_structure.json"
)

result = {}

for dataset_name, folder in SOURCES.items():
    result[dataset_name] = {
        "folder": str(folder),
        "files": []
    }

    files = sorted(folder.glob("*.nc"))

    for file in files:
        entry = {
            "filename": file.name,
            "size_mb": round(file.stat().st_size / (1024 * 1024), 3)
        }

        try:
            with xr.open_dataset(file, decode_times=True) as ds:
                entry["dimensions"] = {
                    str(k): int(v) for k, v in ds.sizes.items()
                }

                entry["coordinates"] = {}

                for name, coord in ds.coords.items():
                    values = np.asarray(coord.values)
                    info = {
                        "dimensions": list(coord.dims),
                        "dtype": str(coord.dtype),
                        "attributes": {
                            str(k): str(v)
                            for k, v in coord.attrs.items()
                        }
                    }

                    if values.size:
                        info["first_values"] = [
                            str(v) for v in values.flat[:5]
                        ]
                        info["last_values"] = [
                            str(v) for v in values.flat[-5:]
                        ]

                    entry["coordinates"][name] = info

                entry["variables"] = {}

                for name, var in ds.data_vars.items():
                    entry["variables"][name] = {
                        "dimensions": list(var.dims),
                        "shape": list(var.shape),
                        "dtype": str(var.dtype),
                        "attributes": {
                            str(k): str(v)
                            for k, v in var.attrs.items()
                        }
                    }

                entry["global_attributes"] = {
                    str(k): str(v)
                    for k, v in ds.attrs.items()
                }

                entry["status"] = "OPENED"

        except Exception as exc:
            entry["status"] = "ERROR"
            entry["error"] = repr(exc)

        result[dataset_name]["files"].append(entry)

OUTPUT.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("Inspection complete.")
print("Output:", OUTPUT)

for name, data in result.items():
    successful = sum(
        f["status"] == "OPENED" for f in data["files"]
    )
    print(f"{name}: {successful}/{len(data['files'])} files opened")
