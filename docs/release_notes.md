# Release notes — October 28, 2026

## Included scope

This release combines the four-stage Databricks pipeline, original-data analysis, deeper discount investigation and later offline detection prototype. The pipeline is the Phase 2 core. The analytical and review extensions are optional and do not alter the validated Job or original dashboard.

## Documentation and packaging revision

- Reorganized the English README around source, processing and output, with separate entry points for the pipeline and extensions.
- Added setup, code-contract and clean-package validation guides, plus pinned optional analysis dependencies from the observed local environment.
- Normalized later reproduction commands to the extracted repository root and private `.deployment/` hierarchy. Explained external data access, retained source versions and sibling baseline-sample requirements.
- Added docstrings to important pipeline and review functions; translated ingestion/state error messages to English. Notebook processing logic remains unchanged; remaining Spanish code comments were translated. Dashboard SQL comments were translated while identifiers and queries were retained.
- Included investigation/prototype files absent from the October 27 archive. Preserved that archive separately.
- Added checks for exact manifest coverage, hashes, source syntax, notebook outputs, Markdown links, private-file exclusions and selected credential patterns.

## Validation boundaries

Historical five-scenario remote evidence belongs to the recorded Job and its original hashes. This revision does not rerun that Job, reingest the full dataset, change its schedule, publish a model or update the dashboard. Local checks and reproduction results are recorded separately in `evidence/release_validation_20261028.json`.

Docstrings and diagnostic-message changes alter hashes. Historical manifests are deliberately preserved. A new detector execution receives a new evidence snapshot because source hashes are part of case identity; do not mix review events across snapshots.

Dependency pins reflect the observed environment; a new network installation and other operating systems have not been certified. The review CLI requires POSIX file locking. Private row-level data is excluded; full reproduction requires authorized access to the documented sandbox and retained Delta versions.

## Outstanding external delivery tasks

Publish the extracted repository contents to GitHub and verify evaluator access. Confirm policies and perform actual human review before claiming detection usefulness or savings. Production requires paths, permissions, load windows, coherent publication and performance validation; it is outside this release.

## Databricks execution and authoritative source revision

The source tree now contains a native standalone detector notebook and a managed serverless environment specification. The wrapper obtains its own pinned inputs with Spark, stores private extracts and reports in a fresh isolated volume, and executes the existing model/receipt tools. It does not add a detector task to the original ingestion Job.

Standalone run `789881187167631` passed on Python 3.12.3 with the pinned scientific packages. It reproduced 2,135 policy candidates, 95 statistical candidates, four peer-profile cases and a pilot with 100 supporting receipts. The 31 contract tests passed on the Databricks driver, and all 25 protected table versions remained unchanged. Aggregate evidence is in `evidence/databricks_release_20261028/standalone_detector.json`. No human decisions were submitted, so detection usefulness remains unknown.

Two earlier notebook attempts failed during Python/Spark initialization after a notebook-level dependency restart. Dependencies are now declared in the managed environment before execution. This correction was validated in the successful run; failed attempts are retained as operational history outside the source ZIP.

Fresh pipeline validation exposed a packaging omission: the remote uploader used a handwritten dependency list and omitted `review_contract.py`, although the generated manifest required it. The uploader now copies every manifest-tracked dependency and verifies its hash. Its expected-duplicate assertion now matches the English error message. The original Job and historical evidence are preserved; fresh tests use a separate Job.

The final archive is built from a new Databricks workspace export. English documentation describes the distinction between source objects and executable runtime objects, private-volume outputs, and the reproducible export procedure. Export provenance does not imply every file was originally authored in the Databricks editor.

Three additional local tests verify workspace-export provenance and path restrictions, bringing the final local suite to 34. They were added after the successful native detector run, whose evidence correctly records the earlier 31-test suite. They do not change the detector or pipeline transformations.

Fresh release Job `546964718724235` subsequently passed all five scenario checks: initial load, unchanged repetition, complete-ticket correction, expected duplicate rejection and recovery. The duplicate run intentionally failed at Bronze and blocked downstream tasks; its independent verifier passed. The original dashboard remained unchanged. See `evidence/databricks_release_20261028/pipeline_validation.json` for run links and exact tested source hashes. This adds current evidence without changing the original Job `372187525837578` or rewriting its historical results.
