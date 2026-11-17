# M25.3 pre-monsoon handoff

The package contains the independently developed pre-monsoon outputs for comparison with the combined three-season model.

- The selected Stage 2 model bundle is under `results/models/phase2/pre_monsoon/stage2_v1/`.
- The 2010?2018 Stage 2 labels cover the development years. They are under `data/processed/model_ready/phase2/pre_monsoon/stage2_v1/`.
- The 2019?2021 Stage 3 labels cover the holdout years. They are under `data/processed/model_ready/phase3/pre_monsoon/stage3_v1/`. Stage 3 applied the frozen Stage 2 model without refitting.
- The two original configurations and three original manifests are under `config/` and `reports/`. `GIT_COMMIT.txt` identifies the commit containing those five files.

## Verify before correspondence analysis

1. Extract into a new directory and preserve the relative paths. Open PowerShell at the extraction root and run:

~~~powershell
$rows = @(Import-Csv ./pre-monsoon-checksums.csv)
if ($rows.Count -ne 13) { throw 'Expected 13 output rows' }
foreach ($row in $rows) {
    $file = Get-Item -LiteralPath $row.RelativePath -ErrorAction Stop
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    if ($file.Length -ne [long]$row.Bytes -or
        $hash -ne $row.SHA256 -or $hash -ne $row.RecordedSHA256) {
        throw "Verification failed for $($row.RelativePath)"
    }
}
'All 13 output files verified'
~~~

2. Cross-check the recorded hash in each CSV row against the output_sha256 map in its named manifest. The Stage 3 evaluation manifest also records the bundle hash in model_sha256. If you have the Git repository, compare the five metadata files with their versions at the commit in GIT_COMMIT.txt.
3. Keep the development and holdout years identifiable in the comparison. Load the Joblib bundle only in a trusted environment.
