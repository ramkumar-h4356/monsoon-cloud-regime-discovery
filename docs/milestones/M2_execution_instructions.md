# M2 execution instructions

1. Extract the M2 ZIP into the repository root, preserving folders and allowing the two new validation files to be added.
2. From the repository root, run:

   ```powershell
   python -m pytest tests/test_established_monsoon_rainfall_validation.py -q
   ```

3. If unit tests pass, run the local-data preflight:

   ```powershell
   python src/02_validation/validate_established_monsoon_rainfall_pipeline.py
   ```

4. Share the complete terminal output. The preflight reads the existing prepared rainfall NetCDF files and cluster assignment CSV. It does not overwrite existing data or research outputs.

If the preflight reports an existing audit file, do not delete it. Share the message so the existing evidence can be reviewed and a new output name can be agreed.
