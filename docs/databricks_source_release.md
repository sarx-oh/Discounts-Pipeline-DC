# Databricks source and release workflow

## Source, execution and export are different objects

The maintained source tree is `/Users/a01645653@tec.mx/Applebees_project/01_validated_release/Applebees_Fase2`. It contains the repository layout: configuration, resources, transformation notebooks, common Python modules, tests, tools, English documentation and aggregate evidence. The local `entrega_fase2/` folder is an editing/verification copy. To deliver a Databricks-sourced release, reconcile reviewed changes into the workspace first, then export that workspace tree into a fresh directory and package those exported bytes.

The original four-task Job `372187525837578` retains its existing runtime folder. Its tasks are Bronze, Silver, Gold and audit. The detector is not a task in this Job. Fresh release tests use another isolated Job and schemas; they do not repoint or update the original Job.

Most project objects are regular workspace files, including `.ipynb` sources. The test harness imports executable task wrappers into a separate runtime folder. The standalone detector entry point is an actual Databricks notebook: `notebooks/02_run_detection_prototype.py`. A source tree and a runtime tree intentionally have different roles.

## Run the standalone detector inside Databricks

Open the native notebook in the source tree and use serverless compute. Its environment metadata pins the optional scientific dependencies before execution. When submitting through Jobs, use the same environment specification from `resources/jobs/standalone_detector_run.json`, replacing the source path if the project was moved. This definition is for a one-time run and does not update the four-task pipeline.

To submit the independent run from the repository root after verifying its notebook path:

```sh
databricks jobs submit --json @resources/jobs/standalone_detector_run.json --profile YOUR_PROFILE --no-wait
```

Save the returned run ID and inspect its task output after completion. Do not resubmit merely to check status; use `databricks jobs get-run RUN_ID --profile YOUR_PROFILE`. A new submission creates a fresh private run.

The notebook obtains its own inputs using Spark SQL and the retained Delta versions in `configs/pinned_analysis_state.json`. It validates source coherence, extracts temporal model samples, builds review candidates, selects a 100-ticket pilot and retrieves supporting receipts. It creates a fresh `workspace.applebees_test_<id>_prototype` schema with an `artifacts` volume. Private extracts, case reports and diagnostics stay there. Only aggregate execution evidence belongs in the release.

Use a new schema/run for every execution. Permissions must allow reading the pinned analytical tables and creating the isolated schema and volume. This is a retrospective prototype, not scheduled production scoring. It collects a bounded analytical sample to the driver; it does not claim distributed model training or unlimited-scale review. Exact historical reproduction depends on retained Delta versions and the documented source snapshot.

The review CLI uses POSIX file locks. Run it against one authorized local copy if collecting actual human decisions; do not treat a shared volume as a distributed review database. The notebook creates no human review events. Candidates are unconfirmed signals, and usefulness remains unmeasured until genuine review occurs.

## Export the release from Databricks

Use the official Databricks CLI with the authorized profile. The following command reads workspace source and writes only local export files:

```sh
python3 tools/export_databricks_release.py \
  --remote-root /Users/YOUR_USER/Applebees_project/01_validated_release/Applebees_Fase2 \
  --profile YOUR_PROFILE \
  --destination ../output/fresh_workspace_export/Applebees_Fase2 \
  --archive ../output/Applebees_Fase2_databricks.zip \
  --report ../output/fresh_workspace_export/export_report.json
```

The destination must not exist. Regular files use AUTO export; native notebooks use SOURCE export so their Databricks formatting/environment metadata is preserved. The tool checks the downloaded source and builds the archive from that downloaded tree. It generates a fresh `SHA256.json` for all packaged members. It excludes the old workspace manifest from manifest generation, interpreter caches and deployment state, and rejects unexpected private/runtime paths.

Run the standard-library tests from the fresh export as a separate check:

```sh
python3 -m unittest discover -s ../output/fresh_workspace_export/Applebees_Fase2/tests -p 'test_*.py'
```

For a finalized workspace snapshot, upload the generated manifest from the ZIP back to the source root, then verify it and all release files against the exported inventory. Do not edit source during export. Any later source change requires a new snapshot and new manifest; a green historical run does not automatically validate a changed release.

## Provenance and honest scope

The project includes both local development and Databricks execution history. Exporting from Databricks establishes the origin and content of the delivered snapshot; it does not retroactively mean every file was originally authored in the web editor. Historical evidence remains separate from fresh release validation. Private data, credentials and operational deployment state never belong in the ZIP.
