# Workspace inventory and status

Validated means the stated checks passed. It does not mean production deployment. A retrospective detector is implemented as an independent Databricks notebook; it is not part of the four-task Job and has not been validated through human review.

## Databricks resources

Paths are relative to `/Users/a01645653@tec.mx`.

| Resource | Classification | Purpose |
|---|---|---|
| `Appleebees/` | Original baseline | Existing EDA and medallion notebooks; spelling retained for compatibility |
| `Applebee’s EDA.lvdash.json` | Original baseline | Existing dashboard; unchanged |
| `Applebees_tests/0eef22876f8b` | Validated original-data sandbox | Regression copy and cash/card analysis |
| `Applebees_tests/incremental_076460f5ea95` | Fresh release validation | Job 546964718724235; five scenario checks passed |
| `Applebees_tests/incremental_f1e4901c804c` | Original validated pipeline test | Job 372187525837578; five scenarios passed |
| `Applebees_tests/incremental_f0de23f153c9` | Historical pipeline test | Previous validated Job 337993819559583 |
| `Applebees_tests/d0a4f8d1cc99` | Historical test evidence | Earlier synthetic validation |
| `Applebees_tests/d4fb633aad86` | Historical attempt | Earlier runner, test and protected-table files; not the current deliverable |
| `Applebees_tests/discount_review_fdab42c8d6ad` | Validated analytical deliverable | Full review base; run 608560147970208 |
| `Applebees_tests/discount_review_26953f62f546` | Failed attempt | Spark Connect write-mode failure; not approved for use |

Job paths and runtime roots depend on these locations. Moving a folder requires updating references and validating the result. Current cleanup preserves these dependencies.

## Data namespaces

Original tables remain in `workspace.applebees_bronze`, `workspace.applebees_silver` and `workspace.applebees_gold`.

The validated review base is `workspace.applebees_test_fdab42c8d6ad_discount_review`. The similarly named `26953f62f546` schema belongs to a failed attempt. Namespaces containing `f1e4901c804c` contain current synthetic tests; `f0de23f153c9` contains historical synthetic tests. Namespaces containing `0eef22876f8b` belong to the original-data sandbox and related analyses.

## Local files

| Location | Purpose |
|---|---|
| `entrega_fase2/` | Local editing and verification copy of workspace source |
| `entrega_fase2/src/` | Pipeline, audit, analysis and review-contract code |
| `entrega_fase2/docs/` | Maintained documentation |
| `entrega_fase2/evidence/` | Selected shareable aggregate evidence |
| `entrega_fase2/tests/` | Synthetic fixtures and local tests |
| `entrega_fase2/.deployment/` | Operational manifests and remote state; excluded from ZIP |
| `output/discount_solution/` | Working results and pseudonymized samples; excluded from repository |
| `output/Applebees_Fase2_20261028_Databricks.zip` | Final workspace-exported release; regenerate after validated source changes |
| `output/archive/Applebees_Fase2_previous_extraction/` | Archived older extracted package; not canonical |
| `DB/` | Original local dataset; excluded from repository |
| `references/` | Supplied PDF challenge instructions and template |
| `tests/`, `tmp/`, `output/databricks/` | Earlier work and evidence; inspect before archiving |

Cleanup inventories and pre-translation backups are in `output/workspace_cleanup/`, outside the release. Historical evidence retains original system labels. Maintained release documentation is in English. Original source identifiers, business labels and recorded historical errors are preserved verbatim.

## Project navigation hub

The Databricks project hub is `/Users/a01645653@tec.mx/Applebees_project`. Its numbered folders separate the validated release snapshot, current test evidence, original baseline and archived attempts. The release ZIP is a source snapshot, not a deployed pipeline. English index files point to existing execution locations; runtime folders, Jobs, tables and the original dashboard are unchanged by this cleanup.

## Deeper statistical investigation

The [new findings and options](deep_discount_findings.md) and [reproduction guide](deep_reproduction.md) extend the baseline. Source scripts use `deep_` names; aggregate exports are in `evidence/discount_deep_20261027`. Private samples, exact requests and case details remain in `output/discount_deep_20261027`. Remote work consists only of pinned read-only queries; no new deployment or final model selection occurred. The October 28 source release includes this investigation.

## Working detection prototype

The [implemented prototype](detection_prototype_results.md) extends Gold with policy candidates, contextual severity and separate peer profiles. Its original local execution is recorded under `evidence/detection_prototype_20261028`; the successful standalone Databricks execution is recorded under `evidence/databricks_release_20261028`. The native notebook obtains its own pinned inputs and writes private receipts, cases and reports to a new isolated volume. Earlier local private runs remain outside the release under `output/detection_prototype_20261028`. Actual human review uses the separate local review CLI; it is not a shared-volume review service. No production scheduling or integration into the four-task Job occurred. Utility has not yet been demonstrated by human review.

## Maintained workspace source and exported release

The maintained project source is `/Users/a01645653@tec.mx/Applebees_project/01_validated_release/Applebees_Fase2`. Its repository layout matches the exported ZIP. Most objects are regular workspace files, including `.ipynb` sources; `notebooks/02_run_detection_prototype.py` is a native executable notebook. This tree is separate from the runtime folder referenced by the original validated Job.

The detector reads the pinned analytical sandbox and writes a fresh private volume. It is not added to the pipeline Job. The older local prototype and historical runs remain documented; see [Databricks execution and export](databricks_source_release.md) for the current workflow. The final ZIP is built from a fresh workspace export and checked against its manifest. Later workspace edits require a new export; there is no automatic synchronization.

The hub retains the October 27 archive and earlier convenience documents as history. Runtime folders, the original Job, tables and dashboard retain their existing paths.
