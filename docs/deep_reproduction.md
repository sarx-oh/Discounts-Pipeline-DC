# Reproduce the deeper discount investigation

The maintained scripts consume pinned SQL API outputs or existing verified samples. They do not deploy a pipeline or publish a model. Run commands from the extracted repository root. Install the pinned optional environment from `requirements-analysis.txt`; see [setup](setup.md). Statsmodels supplies the BY multiplicity diagnostic; versions should be recorded on a fresh run.

## Remote requests

Use a new work directory for a new run. Existing requests and statement IDs are immutable; the runner resumes an existing response instead of submitting again. Never change an executed request. The prepared suite fixes exploration to hash residue 0 and reserves residue 19 for the locked replication.

```sh
python3 tools/prepare_deep_queries.py --state .deployment/discount_solution/state_response.json --workdir .deployment/discount_deep_20261027 --warehouse YOUR_WAREHOUSE
```

The command creates requests in a fresh directory. Add `--verify` only to check an already prepared directory. For each generated request, explicitly execute:

```sh
python3 tools/run_readonly_query.py .deployment/discount_deep_20261027/recording_audit_request.json --profile YOUR_PROFILE
```

Repeat for the suite's other request names. Inspect the protocol before extracting the confirmation partition; do not tune models on its results. The 14 generated requests comprise recording audit, schema inspection, matched cash/card, three tip analyses, four enriched temporal extracts, employee weeks, composition context, item-product patterns and residue-19 replication. A fifteenth private case-event query derives its keys from the ten returned private examples; its exact executed request is stored outside the release. The main case selection and all aggregate results are reproduced by the public suite.

The confirmation request preserves the historical template header describing exploration residue 0. Its executable predicate is explicitly residue 19; the immutable request hash and disjoint-key check establish the actual evaluated partition. Do not infer its predicate from that inherited comment.

The SQL runner rejects mutation keywords, requires pinned source manifests, checks success and truncation, collects every result chunk, and verifies returned row counts. Credentials are supplied by the installed CLI profile. In the Codex restricted environment, authentication may require expanded access to the credential cache/network; a sandbox `no cached credentials` error does not by itself prove expiry. Never print credentials or token output.

## Local work

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 tools/deep_temporal_models.py .deployment/discount_solution .deployment/discount_deep_20261027
python3 tools/deep_model_diagnostics.py .deployment/discount_deep_20261027
python3 tools/deep_payment_support.py .deployment/discount_solution .deployment/discount_deep_20261027/payment_support.json
python3 tools/deep_full_aggregates.py .deployment/discount_deep_20261027
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 tools/deep_enriched_models.py .deployment/discount_deep_20261027 --bootstrap 150
python3 tools/deep_employee_persistence.py .deployment/discount_deep_20261027
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 tools/deep_confirm_models.py .deployment/discount_deep_20261027
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 tools/deep_interaction_check.py .deployment/discount_deep_20261027
python3 tools/deep_export_evidence.py .deployment/discount_deep_20261027
python3 tools/deep_plot_findings.py
```

The enrichment check independently matches 103,495 ticket keys and targets to prior extracts. Confirmation checks disjoint keys, identical source versions and later dates. Fixed preprocessing, regularization and model settings are in source. Source hashes accompany results. Local predictions, employee weeks, manager keys, full enriched samples and case details stay in `.deployment/`, excluded from the release.

## Statistical limitations

Location/date or location/week multiplier intervals use crossed independent exponential weights. They are resampling sensitivity intervals, not guarantees of coverage with only 13-17 weeks or 25-30 evaluation dates. Most intervals condition on fitted models; the separate 150-refit payment contrast captures fitted-coefficient variation while holding preprocessing and evaluation records fixed. They do not identify causal effects or correct all adaptive comparisons.

The weekly sign diagnostic assumes independent signs for its binomial reference; serial independence is not established. BY correction addresses dependence across tested profiles, not dependence between weeks within a profile. No employee alert is declared statistically validated. Official method references: [SciPy binomial test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html), [statsmodels multiple-testing correction](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html), and [scikit-learn correlated-feature permutation guidance](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html).

The private sample includes no real-time discount authorization labels. Final basket and gratuity predictors are retrospective; no operational authorization model was deployed.

## Private input layout

Use `.deployment/discount_solution/` for the original three temporal sample extracts and `state_response.json`, and `.deployment/discount_deep_20261027/` for the enriched extracts. These directories must share a parent because model reconciliation intentionally reads the sibling baseline samples. Generate the baseline with the [discount analysis guide](descuentos_reproduccion.md), choosing `.deployment/discount_solution` as its work directory. Generate enriched inputs with `prepare_deep_queries.py` and execute every prepared request with `run_readonly_query.py`. Do not copy aggregate files from `evidence/` in place of private row-level extracts.

The date in these directory names identifies the study convention, not a requirement to overwrite a previous run. For another study, use a new private parent directory containing the same `discount_solution/` sibling and update all paths consistently. If source Delta versions are no longer retained, exact historical reproduction is unavailable; document the new snapshot and revalidate the baseline.
