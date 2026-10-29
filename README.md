# Applebee's data pipeline — Phase 2

A Databricks workflow that converts nested restaurant tickets and reference catalogs into validated ticket metrics and business aggregates. It handles complete-ticket corrections, preserves data-quality exceptions, and supports discount analysis without duplicating monetary amounts.

## Start here

1. Read the [architecture](docs/arquitectura.md) and [table dictionary](docs/tablas.md).
2. Follow [setup and execution](docs/setup.md) to check the release locally or prepare an isolated Databricks test.
3. Review [quality controls](docs/calidad.md), [fresh Job results](docs/current_release_job_results.md), and [operations and recovery](docs/operacion.md).
4. For implementation details, use the [code guide](docs/code_guide.md).
5. For the native detector and Databricks-to-ZIP export, see [source and release workflow](docs/databricks_source_release.md).
6. For optional extensions, see [discount findings](docs/deep_discount_findings.md) and the [retrospective detection prototype](docs/detection_prototype_results.md).

## What is implemented

| Component | Inputs and outputs | Validation and limits |
|---|---|---|
| Bronze | JSON tickets and catalogs → current source records, file manifest and layer state | New/changed files; full-ticket upsert; duplicate keys rejected; unchanged repeats preserve data |
| Silver | Approved Bronze versions → separate items, payments, discounts, taxes, voids, dimensions and quality tables | Batch rebuild; preserves array positions and decimal amounts; flags incomplete/inconsistent records |
| Gold | Approved Silver versions → ticket metrics, daily aggregates, discount summaries and review outputs | Child records aggregate before joins; batch rebuild removes stale contributions from corrections |
| Audit | Completed layers → consistency checks and execution evidence | Read-only model checks; distinguishes exceptions from blocking failures |
| Optional analysis | Version-pinned real-data sandbox → aggregate findings | Separate from synthetic Job tests; no causal or confirmed-misuse claims |
| Optional detector | Pinned Databricks tables → private candidate and receipt reports in a separate volume | Independent native notebook; absent from the four-task Job; effectiveness awaits human review |

The original validation Job `372187525837578` remains unchanged. Fresh release Job `546964718724235` passed all five scenario checks: initial load, unchanged repetition, correction, duplicate rejection and recovery. Duplicate rejection is an intentionally failed run whose independent verification passed. The standalone detector also ran successfully in Databricks, separately from both pipeline Jobs. The final local suite contains 34 tests. See [current evidence](evidence/databricks_release_20261028/README.md) and [release notes](docs/release_notes.md).

## Repository structure

Extract `Applebees_Fase2/` and upload its **contents** as the GitHub repository root.

```text
README.md
requirements-analysis.txt       # Pinned scientific Python dependencies
notebooks/                     # Independent native Databricks detector entry point
resources/
  jobs/incremental_job.json     # Four-task Job template
  pipelines/README.md           # Declarative-pipeline design decision
src/
  transformations/bronze/       # Source ingestion notebook
  transformations/silver/       # Preparation and quality notebook
  transformations/gold/         # Business metrics notebook
  common/                      # State, ingestion, runtime and review contracts
  quality/                     # Read-only audit notebook
  analysis/                    # Optional analytical SQL and notebooks
  dashboard/                   # Reference SQL for dashboard outputs
  detection/                   # Optional review-candidate contracts
configs/                       # Pipeline and analysis configuration
tests/                        # Synthetic fixtures and local tests
tools/                        # Preparation, execution, analysis and packaging tools
docs/                         # English guides and historical study reports
evidence/                     # Selected aggregate evidence, no private case extracts
.gitignore
SHA256.json                    # Generated archive contents and hashes
```

The organization follows the supplied template's separation of orchestration (`resources/`) and transformation logic (`src/transformations/`). This implementation uses JSON Job definitions and `.ipynb` notebooks rather than the example YAML/Python/SQL filenames. It does not implement Lakeflow Declarative Pipelines; [technical decisions](docs/decisiones_tecnicas.md) explain the evaluated alternatives. Existing Spanish filenames and source-field names remain stable so links and data contracts continue to work; maintained explanations are in English.

## Quick local check

From the extracted repository root, using Python 3.13:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/validate_release.py
```

These checks require only Python's standard library and do not contact Databricks. Spark notebooks require Databricks; they are not standalone local Python programs. The analysis environment is optional for these checks.

## Workspace source location

The maintained source tree is stored in Databricks at `/Users/a01645653@tec.mx/Applebees_project/01_validated_release/Applebees_Fase2`. It preserves this repository layout as source files, including the independent detector. This is separate from the notebooks used by the validated Job. See [workspace inventory](docs/workspace_inventory.md).

## Scope and delivery

The final package is a source snapshot exported from that Databricks tree. It does not publish GitHub, execute Jobs, schedule production ingestion, or change the existing dashboard. Databricks tests require access to the documented Applebee's workspace and its protected original resources. An empty workspace is not supported without a deliberate configuration adaptation.

Read [release scope](docs/alcance_entrega.md) and the [delivery audit](docs/auditoria_entrega.md) before submission. Production promotion and verified detection usefulness remain future work. A green synthetic test is not a throughput benchmark.

## Verify or rebuild a local archive

For a deliverable whose source is Databricks, use the [workspace export workflow](docs/databricks_source_release.md). The commands below package the current local tree only.

```sh
python3 tools/package.py --output ../output/Applebees_Fase2_local_rebuild.zip
python3 tools/validate_release.py --archive ../output/Applebees_Fase2_local_rebuild.zip
```

Packaging includes maintained source, configuration, documentation and selected evidence; excludes deployment state, environments, caches and private extracts; and generates SHA256 hashes. Do not place private samples or credentials under source or evidence directories. The validator is an additional check, not a substitute for reviewing release contents.
