# Run and review the detection prototype

For direct execution inside Databricks with automatic extraction into a private volume, follow the [native notebook workflow](databricks_source_release.md). The commands below preserve the optional local reproduction and human-review route. Neither route adds the detector to the ingestion Job.

Run commands from the extracted repository root. Install the pinned optional environment from `requirements-analysis.txt`; see [setup](setup.md). Databricks read-only queries require the authenticated profile and warehouse used by the analytical sandbox. Recreate prerequisite samples using [deep reproduction](deep_reproduction.md). Preserve the original `.deployment/discount_solution` samples: the build reconciles targets to them.

## Prepare full policy evidence

```sh
mkdir -p .deployment/detection_prototype_20261028
python3 tools/prepare_discount_query.py src/analysis/detection_policy_events.sql --state .deployment/discount_solution/state_response.json --output .deployment/detection_prototype_20261028/policy_events_request.json --warehouse YOUR_WAREHOUSE
python3 tools/run_readonly_query.py .deployment/detection_prototype_20261028/policy_events_request.json --profile YOUR_PROFILE
```

These queries use version-pinned sandbox sources. They do not create or update tables. The current reproduction is tied to the documented 2,135-ticket baseline; a different data snapshot requires deliberate baseline validation, not disabling the assertion.

## Build a fresh run

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 tools/build_detection_prototype.py --analysis .deployment/discount_deep_20261027 --policy-events .deployment/detection_prototype_20261028/policy_events_data.json --output .deployment/detection_prototype_20261028/run_new
```

The output directory must not exist. Input hashes, detector code hashes, source versions and configuration determine the evidence snapshot. Preserve original inputs and the Python environment for exact reproduction.

## Retrieve supporting receipts

```sh
python3 tools/hydrate_detection_pilot.py prepare --run .deployment/detection_prototype_20261028/run_new --state .deployment/discount_solution/state_response.json --warehouse YOUR_WAREHOUSE
python3 tools/run_readonly_query.py .deployment/detection_prototype_20261028/run_new/pilot_receipts_request.json --profile YOUR_PROFILE
python3 tools/hydrate_detection_pilot.py collect --run .deployment/detection_prototype_20261028/run_new
```

Open `review.html` locally; its supporting-receipts link opens `receipts.html`. Both contain private transaction evidence. Do not publish them or include them in a release. The completed first run is `run_v1`.

## Record actual human review

Inspect a case using its ID from `pilot.json` or the report:

```sh
python3 tools/detection_review.py .deployment/detection_prototype_20261028/run_v1 show CASE_ID
```

Copy `review_template.json` to a new event file. Replace the case ID, UUID, actual reviewer, timezone-aware review timestamp, reason, justification and actual review minutes. Preserve the case's snapshot and policy version. Select a decision only after reviewing the receipt and policy evidence. The sample minute value is a placeholder, not measured effort. Do not submit fabricated reviews to test the real log; automated tests use temporary synthetic fixtures.

```sh
python3 tools/detection_review.py .deployment/detection_prototype_20261028/run_v1 record PATH_TO_COMPLETED_EVENT.json
python3 tools/detection_review.py .deployment/detection_prototype_20261028/run_v1 metrics
```

Events append under an exclusive file lock, flush and fsync. IDs cannot repeat. Corrections need a new ID and `previous_review_event_id` pointing to the latest event for that same case; original events remain. Mapping/scope confirmation is mandatory before a confirmed breach can be recorded. Empty review metrics are null rather than zero. Metrics are printed from the current log; the initial HTML and metrics JSON do not update automatically.

## Test

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

The prototype is an offline post-Gold pipeline: validate inputs, generate policy cases, score contextual severity, summarize profiles, deduplicate cases, sample the pilot and render evidence. A scheduled Databricks task remains future work after policy confirmation and measured review benefit. No remote deployment is required to run this local prototype. Its source is included in this release; generated private runs remain excluded.

## Private input layout

Use `.deployment/discount_solution/` for the original three temporal sample extracts and `state_response.json`, and `.deployment/discount_deep_20261027/` for the enriched extracts. These directories must share a parent because model reconciliation intentionally reads the sibling baseline samples. Generate the baseline with the [discount analysis guide](descuentos_reproduccion.md), choosing `.deployment/discount_solution` as its work directory. Generate enriched inputs with `prepare_deep_queries.py` and execute every prepared request with `run_readonly_query.py`. Do not copy aggregate files from `evidence/` in place of private row-level extracts.

The date in these directory names identifies the study convention, not a requirement to overwrite a previous run. For another study, use a new private parent directory containing the same `discount_solution/` sibling and update all paths consistently. If source Delta versions are no longer retained, exact historical reproduction is unavailable; document the new snapshot and revalidate the baseline.
