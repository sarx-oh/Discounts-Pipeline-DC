# Code guide

This guide explains entry points, contracts and side effects. Notebook Markdown describes the transformation steps next to their code. Core reusable functions also have English docstrings. Names inherited from source data and stable Spanish filenames are not translated into new data contracts. Historical audit/status labels and some notebook diagnostics retain their original Spanish wording to preserve the validated notebook behavior; English Markdown and this guide explain their meaning.

## Pipeline execution path

1. `tools/build_sandbox.py` renders a new local bundle with unique sandbox names, source hashes, a Job definition and a protected-table list. It does not submit a Job.
2. `tools/remote_test.py` explicitly imports the bundle, creates test resources, runs fixtures and collects independent checks. It has remote side effects.
3. `src/common/runtime.py` runs inside each Databricks task with injected globals (`RUNTIME_ROOT`, `STAGE`, `JOB_RUN_ID`, `spark`, `dbutils`). It verifies the bundle hashes, wraps source access and records execution evidence. Do not import it as a normal local library.
4. Each transformation notebook uses `PipelineContext`: verify upstream completion, record RUNNING, read pinned versions, compute/check outputs, then record COMPLETE. Audit runs after Gold.

## Shared contracts

| Module | Important behavior | Failure / side effect |
|---|---|---|
| `src/common/pipeline_support.py` | Validates remapped configuration, detects file changes, generates complete-record MERGE SQL and manages layer state | Rejects original/mixed destinations, duplicate keys, unsupported source changes and stale upstream versions; writes Delta tables only during explicit execution |
| `src/common/thresholds.py` | Keys threshold snapshots by source versions, code and config; reads immutable version zero | Publishes a Gold reference and usage history only after provenance/completion checks |
| `src/common/runtime.py` | Restricts the generated task to its sandbox, checks bundle hashes and writes task evidence | Not a general security boundary; workspace permissions and one-writer discipline are still required |
| `src/common/review_contract.py` | Requires review identity, timestamp, reason, policy and evidence linkage | Rejects malformed, duplicate or invalid correction events; no automatic enforcement |

Bronze updates complete tickets, including their arrays. A correction therefore removes stale child records when Silver rebuilds. Gold aggregates each child relation before joining so multiple items and payments do not multiply amounts. `SoldPrice` already reflects item discounts; ticket-level discounts are handled separately. See [tables](tablas.md) for grain and formulas and [quality](calidad.md) for controls.

The state gate is not a cross-table transaction or distributed lock. A failed rebuild may leave tables at different versions. Consumers must honor completion/version checks. Recovery requires fixing the input and successfully rerunning the chain; do not manually mark a layer COMPLETE.

## Standalone detector contracts

`src/detection/core.py` is a pure-Python contract layer. `policy_cases` creates provisional combinations from positive discount events, retaining scope uncertainty. `merge_ticket_cases` combines rule and statistical reasons using snapshot-specific IDs. `pilot_sample` selects two overlapping review arms and non-alerted controls within the same evaluation universe; it does not estimate population recall.

`tools/build_detection_prototype.py` reads authorized private extracts, reconciles sample targets, fits contextual models with chronological splits, creates cases and writes a new private run directory. It refuses to overwrite an existing directory. Expected inputs are listed in the [reproduction guide](detection_prototype_reproduction.md). Historical policy counts are deliberate baseline assertions, not adjustable tuning targets.

`tools/detection_review.py` records actual human decisions under an exclusive file lock and flushes/fsyncs them. Corrections append events and reference the preceding decision. A model score cannot confirm a policy breach without confirmed policy mapping/scope. Reports are build-time snapshots; current metrics come from the CLI. No human review has yet established usefulness.

`notebooks/02_run_detection_prototype.py` calls `tools/databricks_prototype.py` inside a managed serverless environment. The wrapper uses Spark to obtain version-pinned inputs, creates a fresh private volume, runs the same model builder and receipt hydrator, executes contract tests and confirms the 25 protected table versions remain unchanged. It never modifies the pipeline Job. The local review CLI remains separate from this notebook.

## Tool groups

- **Remote source processing:** `build_sandbox.py`, `remote_test.py`, `prepare_review_base.py`, `submit_review_base.py`, `collect_review_base.py`.
- **Read-only analytical queries:** `prepare_discount_query.py`, `prepare_discount_suite.py`, `prepare_deep_queries.py` prepare requests locally; `run_readonly_query.py` submits SELECT/CTE queries against pinned sources, resumes statement IDs and checks all result chunks.
- **Local analytical models:** `compare_discount_models.py`, `diagnose_discount_models.py`, and `deep_*.py` consume private extracts. Some deep tools export aggregate evidence; inspect each module's opening description and CLI before use.
- **Private review:** `build_detection_prototype.py`, `hydrate_detection_pilot.py`, `detection_review.py` produce or consume ticket-level evidence. Never publish their run folders.
- **Release maintenance:** `export_evidence.py` and analytical exporters select evidence; plotting tools generate figures; `export_databricks_release.py` downloads the workspace source into a fresh directory; `package.py` and `validate_release.py` create and check the source archive.

## Tests and evidence

`tests/test_contracts.py` covers ingestion/state-related contracts; `tests/test_analysis_safety.py` covers isolated destinations and analysis preparation; `tests/test_review_contract.py` covers review events; `tests/test_detection_prototype.py` covers cases, scope, pilot selection and review logging. `tests/test_workspace_export.py` verifies remote-byte export, native notebook format selection and rejection of private/out-of-root paths. `tests/fixture_control.py` is a Databricks fixture controller, not a local test module.

Recorded remote evidence remains tied to the source hashes of the original runs. Documentation/docstring changes alter hashes even when processing logic is unchanged. Do not edit old manifests to make a new source revision appear remotely tested. See [release notes](release_notes.md) for precisely what was checked for this package.
