M18.7 PROCESSOR TIMESTAMP-CHECK CORRECTION

Purpose
-------
This package fixes an overly strict timestamp assumption in the M18.7 processor.
The original processor rejected a dataset if any adjacent timestamps were not exactly
one hour apart. The earlier timestamp audit established monotonicity and uniqueness,
but did not establish that every interval was exactly one hour.

The corrected processor:
- still requires the expected number of timestamps;
- still rejects duplicate or non-monotonic timestamps;
- accepts irregular intervals without inventing missing observations;
- records interval diagnostics in provenance;
- stores output time coordinates in seconds since 1970-01-01, preserving minute-level times.

Install
-------
Extract this ZIP into the project root:
D:\Project Simulator\monsoon_cloud_research

Allow folders to merge/overwrite the existing M18.7 processor and test files.

Run targeted tests
------------------
python -m pytest tests/test_m18_7_processor.py -v

Then rerun the storage estimate
-------------------------------
python "src/06_feature_engineering/process_m18_7_datasets.py" --estimate

Do not run --all yet. If the estimate succeeds, run the pilot and inspect its output.

Important
---------
No raw CERES files are modified. Existing failed --estimate invocation stopped during
input discovery, before any processing outputs were created.
