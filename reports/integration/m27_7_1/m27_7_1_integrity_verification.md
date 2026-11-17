# M27.7.1 — Artifact Integrity, Checksums, and Dual-Repository Parity Verification

## 1. M27.7 Manifest and ZIP Archive Audit

The M27.7 manifest (`m27_7_manifest.json`) claims 21 deliverable artifacts (9 reports, 8 tables, 4 figures).
An independent audit verified:
1. **File Existence:** 21 of 21 claimed files exist on disk in the canonical repository.
2. **File Sizes:** 21 of 21 files match their exact manifest-claimed byte sizes.
3. **Cryptographic Checksums:** 21 of 21 files match their exact manifest-claimed SHA-256 hashes.
4. **ZIP Archive Integrity:** `M27.7-independent-scientific-acceptance-audit.zip` (1,099,338 bytes) passed the internal CRC test (`testzip() == None`) with 22 entries (21 deliverables + manifest).

---

## 2. Frozen Baseline Checksums

All foundational frozen arrays and raw data files were cryptographically audited:
- `combined_3season_cluster_labels.npy`: 24,883,328 bytes, SHA256: `903fffc4d5962882...` (MATCH)
- `combined_3season_years.npy`: 49,766,528 bytes, SHA256: `a55949386956c095...` (MATCH)
- `combined_3season_season_ids.npy`: 24,883,328 bytes, SHA256: `80b43aa542842d63...` (MATCH)
- `m26_cloud_rainfall_matched_primary.parquet`: 2,553,297 bytes, SHA256: `8e2994a371e3c421...` (MATCH)
- `raw_data/NOAA_RONI/RONI.ascii.txt`: 27,272 bytes, SHA256: `6e12e1ec7316710b...` (MATCH)
- `raw_data/NOAA_DMI/dmi.had.long.csv`: 20,490 bytes, SHA256: `31c3c9c91b12b5f7...` (MATCH)

---

## 3. Dual-Repository Bit-for-Bit Parity

All 36 mirrored artifacts across `monsoon_cloud_research` and `post_monsoon_research` were evaluated.
- **Total Files Audited:** 36
- **Parity Matches:** 36 / 36 (100.0%)
- **Mismatches:** 0
- Output table: `reports/integration/m27_7_1/tables/m27_7_1_dual_repo_parity.csv`
