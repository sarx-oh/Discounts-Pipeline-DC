# Databricks release validation — October 28, 2026

- `pipeline_validation.json`: fresh Job 546964718724235; all five scenario checks passed, including expected duplicate failure and successful recovery. Exact transformation/common-module hashes identify the tested implementation.
- `standalone_detector.json`: successful independent native notebook run 789881187167631, pinned inputs, model aggregates, 100 receipts, 31 contract tests and 25 unchanged protected tables. Private paths and selected cases are excluded.
- `prototype_reproduction_comparison.json`: the counts match the earlier local prototype; maximum metric differences are at floating-point precision. This is reproducibility evidence, not proof of detection usefulness.
- `original_job_unchanged.json`: the original Job settings are unchanged and its only tasks remain Bronze, Silver, Gold and audit.
- `release_checks.json`: local source checks and correspondence of delivered pipeline source with the fresh tested bundle. Three exporter tests were added after the native detector run, making 34 final local tests.

The finalized ZIP is created from a fresh workspace export. Its `SHA256.json` covers every packaged source/evidence file. The external export report records the ZIP hash; that hash is not embedded recursively in the ZIP itself. Earlier local and remote evidence elsewhere in the repository remains historical and is not relabeled as this execution.
