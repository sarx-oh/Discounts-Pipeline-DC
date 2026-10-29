# Discount misuse detection: first working prototype

## Decision and intended output

Build a retrospective, isolated case generator and review workflow. A case contains reasons, source references, policy scope, model/context evidence and a human decision history. It does not classify anyone as fraudulent. Success means better reviewed-case yield at equal review effort, not merely a higher predictive AUC.

The first implementation includes policy candidates, contextual severity candidates and persistent employee-frequency context. Isolation Forest, additional clustering and quantile regression are deferred until the first comparison exposes a specific gap. This avoids adding models without evidence of benefit.

## Scope of this implementation

- Policy review: extract every positive discount event on tickets containing a provisional EMP50 ID and another positive type from the fixed full-data sandbox. Classify overlapping scope, distinct lines and unresolved positions separately. The current mapping is provisional, so every result requires policy confirmation.
- Statistical ticket review: use the already verified deterministic 5% eligible sample. Fit product/payment-context logistic occurrence and fractional conditional severity models before July 1. Set an illustrative severity residual cutoff on July 1-25; evaluate July 26-August 20. These dates were previously explored: this is a retrospective prototype, not new validation. Exclude employee identity, tips, manager IDs, discount labels and outcome amounts from predictors.
- Employee context: summarize the existing full-data supported peer weeks with shrinkage and temporal persistence. Display these as separate profile cases, not additional independent ticket alerts. No significance or misuse claim is attached.
- Review: provide a private browsable case report, structured JSON cases, a deterministic pilot sampling manifest, and an append-only review CLI using the existing review contract. Human decisions remain empty until actually submitted.

Only policy detection covers the full snapshot. Statistical ticket detection covers 21,796 late-period sampled eligible tickets. The report must show that coverage. The prototype must not imply complete chain-wide statistical detection.

## Detection and priority contract

Policy cases retain each positive application, type, amount, scope and line position. Repeated records of one type alone do not trigger the combination rule. Zero and negative amounts do not activate it. Employee Meal is disabled because its mapping is unresolved. MIT MEAL is not silently substituted.

Severity is observed discount/gross minus the predicted conditional mean. Its calibration percentile ranks retrospective review candidates; it is neither a fraud probability nor a validated upper prediction bound. Use a validation-only cutoff, then report candidate counts and instability at neighboring cutoffs. Rank by excess source-currency amount above the expected conditional amount, a review measure rather than recoverable loss. Ordinary cash payment and zero recorded gratuity never trigger a case.

Employee profiles use early complete weeks to select persistent peer differences, fixed shrinkage and subsequent complete weeks to describe persistence. Any minimum volume, gap or shrinkage value is a configurable pilot setting, not a compliance threshold. Profile cases reference private weekly evidence, separate from ticket-case sampling.

No fabricated composite risk score: policy and statistical reasons remain distinguishable. A ticket appearing in both queues has one case and multiple reasons. Stable case IDs include the source snapshot and detector version. Human resolutions never alter model evidence.

## Pilot and usefulness gate

Compare A (policy candidates) and B (policy plus contextual-severity candidates) on the SAME late-period sampled ticket universe. Select up to 50 cases from each arm, deduplicate, and add up to 50 deterministic random non-alerted controls. Fewer policy cases are reported as fewer, not filled with unrelated alerts. Sampling probabilities and membership are retained privately; controls are explicitly NOT alerts. Profile investigations form a separate workload and must not be mixed into ticket precision.

Reviewers inspect underlying receipts, applicability, scope and exceptions. Record JUSTIFIED, CONFIRMED_POLICY_BREACH, DATA_ISSUE or INSUFFICIENT_EVIDENCE with a reason, reviewer, timestamp, snapshot and policy version. A breach decision is rejected while policy mapping/scope is unconfirmed. Corrections link to the previous event for the same case and remain append-only.

Report confirmed-breach share, justified share, unresolved share, review minutes and extra useful cases found by B at the same capacity. Unresolved cases stay in the denominator. Missing decisions produce null metrics, never zero precision or simulated success. Discovery probabilities for flagged and random-control strata remain separate. Recall is not claimed from a small control sample.

Only add an anomaly detector or clusters if review evidence identifies a blind spot and the new component improves case yield or effort at the same budget. No operational model is selected in this implementation.

## Integration and delivery

The local build stages are: validate inputs -> policy cases -> contextual scoring -> profile cases -> deduplicated cases -> pilot sample -> audit -> report. They form a runnable offline extension after Gold; they do not modify the validated Bronze/Silver/Gold/Audit Job. A future Databricks task can consume the same contract after performance and human-review validation. No new Job deployment is part of this prototype.

Deliver code under `src/detection` and `tools`, settings under `configs`, tests under `tests`, English documentation and sanitized evidence. Private cases, samples, model predictions and the HTML report remain under `output/detection_prototype_20261028`. Preserve the existing release ZIP. No credentials or private case files enter a release.

## Acceptance checks

1. Independently reconcile full policy candidate tickets to the baseline (2,135), or stop and explain a discrepancy.
2. Validate source versions, unique keys, temporal separation and exact sampled target reconciliation.
3. Test scope combinations, zero amounts, repeated types, missing lines and deterministic IDs.
4. Verify reruns are deterministic and never overwrite decisions or an existing run directory.
5. Test review authorization fields, immutable history, same-case corrections, evidence-snapshot matching and unconfirmed-policy blocking.
6. Verify A/B comparison uses a shared population, controls are not alerts, no duplicate pilot tickets, and empty review logs yield unknown usefulness.
7. Produce real candidate cases and a report without claiming confirmed misuse or demonstrated detection precision.
