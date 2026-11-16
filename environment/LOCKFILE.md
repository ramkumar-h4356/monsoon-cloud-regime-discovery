# Environment lock scope

`requirements-windows-py313.lock` captures all 31 installed distributions in
the reference Windows CPython 3.13.7 environment, including pip and active
transitive dependencies. `environment-reference.json` records the exact
versions, platform, and each distribution's `Requires-Dist` metadata.

The artifact-only `environment` command checks exact versions and evaluates
active dependency markers/specifiers. `pip check` also passes. No packages
were installed/upgraded and no model was refitted during remediation.

This is an exact **version** lock, not a wheel-hash lock. It does not include
offline wheels, compiled system-library hashes or a cross-platform guarantee.
The installed environment was checked; a fresh environment was not provisioned
or tested against the package index during this limited pass. Keep those
limits in any reproducibility claim. Historical manifests remain the source
of the package versions actually used for the scientific evaluation.
