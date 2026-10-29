# Setup and execution

All commands below start at the extracted repository root (`Applebees_Fase2/`). The repository may be renamed; no command requires the original developer folder name. Examples use a POSIX shell. The review log uses `fcntl` file locking and is supported on macOS/Linux, not native Windows; use WSL for that optional tool.

## 1. Local validation: no credentials or data required

Observed Python version: 3.13.5. Python 3.13 is the tested release family; other versions have not been certified.

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/validate_release.py
```

Tests use synthetic in-memory records and temporary directories. They do not execute Spark notebooks, prove production performance or reproduce the real-data model results.

## 2. Optional local analysis environment

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-analysis.txt
```

The pins record the observed scientific Python environment, including statsmodels. Installation needs network access or an approved wheel cache. A clean network installation is not part of the local release audit. Use this environment for analysis and plotting only. Databricks provides Spark/Delta and notebook globals separately.

## 3. Databricks prerequisites

Install the official Databricks CLI separately and verify `databricks version`. Authenticate using an existing authorized account and a chosen CLI profile. The release includes no credentials. Commands requiring `--profile YOUR_PROFILE`, `--warehouse YOUR_WAREHOUSE`, or `/Users/YOUR_USER/` require replacement with actual authorized values.

The synthetic test harness expects the Applebee's workspace, its existing 25 protected original tables and existing dashboard. It creates new isolated schemas, volume and notebooks. It cannot bootstrap an empty account or copy the original challenge data. Analytical reproduction additionally needs the documented original-data sandbox and retained Delta versions; synthetic fixtures are not analytical training data.

## 4. Prepare an isolated test locally

```sh
python3 tools/build_sandbox.py --remote-parent /Users/YOUR_USER/Applebees_tests
```

This creates `.deployment/<generated-id>/` locally. Inspect `manifest.json`, `pipeline_config.json`, `protected_tables.json` and `job.json`. The source configuration intentionally retains original names as remapping anchors. Do not run notebooks directly against those destinations: the runtime rejects them.

## 5. Explicit remote execution

Only after the generated manifest and workspace permissions have been checked:

```sh
python3 tools/remote_test.py .deployment/GENERATED_ID --profile YOUR_PROFILE
```

This command creates remote test resources and executes the five synthetic scenarios. It is not a read-only validation command. Reuse its saved execution state to resume the same run; do not start another writer against the same schema. Inspect the final reports and [recovery contract](operacion.md). A failed duplicate run is expected only when independent checks confirm rejection and unchanged protected outputs.

## 6. Optional analytical reproduction

Start with [discount analysis](descuentos_reproduccion.md), then [deeper investigation](deep_reproduction.md), then the [detector](detection_prototype_reproduction.md). Each guide distinguishes preparation from remote execution. Full reproduction requires authorized private extracts that are deliberately excluded from the archive. Preserve input versions and do not substitute synthetic fixtures to claim reproduction of the published real-data metrics.

Private work directories belong under `.deployment/`. The analysis tools expect `discount_solution/` and the deep-analysis directory to be siblings. Follow the shared directory convention in the analytical guides. Keep statement responses and source-version manifests with their extracts.

## 7. Native Databricks prototype and source export

See [Databricks source and release workflow](databricks_source_release.md) for the independent native notebook, its managed environment, private-volume outputs and the reproducible workspace-to-ZIP export command. This path obtains its own version-pinned inputs inside Databricks; it does not require the developer’s local private extracts. It remains outside the four-task ingestion Job.
