# Reproducing discount analysis

The release contains code and aggregate evidence. Complete data remains in Databricks. Analysis uses pinned versions of the original-data sandbox; synthetic Job fixtures validate engineering and are not training data.

## Environment

Access to the Applebee’s workspace and an authenticated Databricks CLI profile are required. The warehouse used was `1e882596e2d90b44`; verify access or configure another warehouse. The full-base notebook requires the existing `applebees_test_0eef22876f8b` sandbox. Signing into another workspace does not transport data.

Install the optional pinned dependencies using [setup](setup.md). Local models require NumPy, pandas, SciPy and scikit-learn; plots require matplotlib. Observed versions are in `configs/analysis_environment.json`. Work from the release root and place execution files under `.deployment`, excluded from the ZIP. Never save transaction samples under `evidence`.

## Queries and pinned versions

Read `workspace.applebees_test_0eef22876f8b_bronze.pipeline_state` using SQL Statements and save the complete response as `state_response.json`. It must be SUCCEEDED, untruncated, and contain three COMPLETE layers.

Create `.deployment/discount_solution/` first. Save the following as `.deployment/discount_solution/state_request.json`, replacing `YOUR_WAREHOUSE`:

```json
{
  "warehouse_id": "YOUR_WAREHOUSE",
  "statement": "SELECT * FROM workspace.applebees_test_0eef22876f8b_bronze.pipeline_state",
  "wait_timeout": "50s",
  "on_wait_timeout": "CONTINUE",
  "disposition": "INLINE",
  "format": "JSON_ARRAY"
}
```

Then submit this read-only state query:

```sh
mkdir -p .deployment/discount_solution
databricks api post /api/2.0/sql/statements --json @.deployment/discount_solution/state_request.json --profile YOUR_PROFILE --output json > .deployment/discount_solution/state_response.json
```

If the response is PENDING/RUNNING, use its `statement_id` with `databricks api get /api/2.0/sql/statements/STATEMENT_ID --profile YOUR_PROFILE --output json` and save the completed response to the same `state_response.json`. Do not resubmit the query merely to poll. Confirm SUCCEEDED, exactly three COMPLETE layers, no truncation and all three rows in `result.data_array`; the preparation tool checks coherence. This query reads existing state and does not create the analytical sandbox.


```sh
python3 tools/prepare_discount_suite.py --state .deployment/discount_solution/state_response.json --workdir .deployment/discount_solution --warehouse YOUR_WAREHOUSE
```

This prepares nine requests with the filenames expected by the exporter. For each returned request:

```sh
python3 tools/run_readonly_query.py .deployment/discount_solution/discount_combinations_request.json --profile YOUR_PROFILE
```

The preparer checks coherent layer versions and pins sources with VERSION AS OF. The runner persists statement IDs, resumes existing submissions and downloads all result chunks. Use a new request filename for changed SQL; never edit an already submitted request. The context filename retains `v3` to match the validated query convention.

The deterministic 5% sample exceeded the INLINE response limit as one request, so the suite partitions it into training before July 1, validation July 1–25 and test from July 26. Do not reduce sampling or add LIMIT to bypass response limits. The three output filenames are `discount_model_train_data.json`, `discount_model_validation_data.json`, and `discount_model_test_data.json`.

## Local model comparison

```sh
python3 tools/compare_discount_models.py .deployment/discount_solution
python3 tools/diagnose_discount_models.py .deployment/discount_solution
```

The comparison verifies unique keys, disjoint dates, valid targets and identical pinned sources. Imputation, scaling and categories are fitted only on training; validation selects parameters and test evaluates them. Diagnostics reproduce selected parameters without retuning. No model is published or applied to workspace cases. Metrics concern discounts, not violations.

## Complete analytical base

The original 25-table protection list comes from `tools/build_sandbox.py` as `protected_tables.json`. Prepare a fresh directory and inspect its manifest before explicitly deploying:

```sh
python3 tools/prepare_review_base.py --state .deployment/discount_solution/state_response.json --protected-tables .deployment/SANDBOX_ID/protected_tables.json --remote-parent /Users/YOUR_USER/Applebees_tests --workdir .deployment/new_base
python3 tools/submit_review_base.py .deployment/new_base --profile YOUR_PROFILE
python3 tools/collect_review_base.py .deployment/new_base --profile YOUR_PROFILE
```

Submission creates an isolated notebook and run. Collection observes that same run and checks output tables, source versions, originals and dashboard. A fresh schema is required; prior results are not overwritten. A failed run may leave a partial schema that must not be treated as approved. Preserve failed IDs and reasons; correct code and prepare a fresh directory. Do not restart a remotely active execution.

The base contains full tickets, discount events, EMP50 candidates, employee weeks and an empty decision log. Event positions identify snapshot-local events, not stable identities across corrections. `src/common/review_contract.py` validates future human decisions; it is not a deployed application or workspace authorization mechanism.

## Export and package

The exporter retains selected aggregates and validations, excluding ticket samples, individual employee profiles and dashboard definitions. If the base ran in a different directory, copy only its approved `base_validation.json` into the analysis directory before export.

```sh
python3 tools/export_discount_review.py .deployment/discount_solution
python3 tools/plot_discount_review.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/package.py --output ../output/Applebees_Fase2_local.zip
```

The ZIP contains the repository files under `Applebees_Fase2/` and a SHA256 manifest. Uploading those files does not execute or deploy the final solution.
