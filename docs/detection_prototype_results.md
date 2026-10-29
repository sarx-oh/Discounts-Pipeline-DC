# Detection prototype: implementation and observed results

The [proposal](detection_proposal.md) was initially implemented as a local retrospective extension after Gold. It generates review cases, retrieves original receipt evidence and supports recording actual human decisions. The same prototype has since run successfully as an independent Databricks notebook; see [current execution and export](databricks_source_release.md). It remains separate from the validated Bronze/Silver/Gold/Audit Job, original tables and dashboard, and its source is included in the release ZIP. It is not a deployed or validated fraud classifier.

## What was built and why

| Component | Purpose | Current result |
|---|---|---|
| Positive-discount combination rules | Find provisional EMP50 combinations and distinguish scope | 2,135 full-snapshot tickets: 2,050 overlapping scope, 85 distinct lines |
| Logistic occurrence model | Estimate contextual discount frequency; supporting evidence only | Evaluation AUC 0.7215; this is not misuse precision |
| Fractional conditional severity regression | Find discounts larger than their contextual expected proportion | 95 candidates among 21,796 late-period sampled eligible tickets |
| Shrunk peer frequency profiles | Surface persistent frequency differences for separate investigation | Four employee-location profiles; descriptive, not validated anomalies |
| Review workflow | Inspect receipts, append decisions and measure yield and effort | 100 unique pilot tickets with source lines, discounts and payments; no human decisions yet |

Context includes location, channel, time, gross amount, line count, traffic, product mix and payment detail. Employee identity, tips, manager and discount labels are excluded from model predictors. The severity regression uses weighted binary logistic fitting to model a fractional conditional mean. The anomaly signal is its observed-minus-expected residual. Isolation Forest and clustering were not added: the first test is whether these explainable residuals find useful additional cases.

The occurrence model does not drive the profile detector. Profiles use full-data supported peer-week aggregates with shrinkage, rather than employee estimates from the sparse ticket sample. Their four investigations are excluded from ticket-pilot metrics. Ordinary cash payments or zero tips never trigger an alert.

## Coverage and calibration

Models fit 59,169 tickets through June 30, calibrate on 22,530 tickets from July 1-25 and evaluate 21,796 tickets from July 26-August 20. Dates were previously explored, so this is retrospective evidence, not a pristine holdout. Full policy extraction and sampled statistical coverage must not be conflated.

The 95th percentile of positive-ticket calibration residuals is 0.353859, producing 95 evaluation candidates. Using the 90th percentile produces 174; the 99th produces 26. This sensitivity makes the workload tradeoff explicit. The threshold is an experimental review setting, not a compliance threshold or predictive confidence bound. Severity MAE is 0.1380 in discount-ratio units. Neither predictive metric demonstrates detection value. Excess amount above the conditional mean is not recoverable loss.

## Pilot and the utility decision

Both arms use the same 21,796-ticket universe. A contains all 33 available policy candidates; B contains those 33 plus 17 statistical candidates, reaching its 50-case cap. Fifty deterministic pseudorandom non-alerted controls bring the deduplicated review workload to 100. Controls are not alerts. Sixteen of the 95 statistical candidates overlap policy candidates in this universe.

A and B have the same maximum capacity but different actual counts, so a raw comparison of total findings is not an equal-effort efficacy result. Inspect reviewed-case shares, unresolved cases, review minutes and the incremental yield of B's 17 additional tickets. Report cost per useful reviewed case and retain all unresolved outcomes in the denominator. The small control sample cannot establish recall. Selection probabilities and memberships are preserved in the private pilot manifest; deterministic priority selection is not representative population sampling.

Usefulness is **unknown** until actual reviewers assess receipts and applicable policy. The current mapping and scope are unconfirmed, so the review CLI blocks CONFIRMED_POLICY_BREACH. Business-confirmed policy requires an explicitly versioned subsequent case build; do not edit frozen cases to bypass the gate. A case may still be reviewed as JUSTIFIED, DATA_ISSUE or INSUFFICIENT_EVIDENCE with actual supporting evidence.

Retain the model only if reviewed additional cases justify their review effort. Add another technique only after documented misses reveal a specific blind spot, then compare it at a fixed review budget on a new period. This prototype demonstrates an executable detection-and-review process, not proven fraud detection.

## Verification and artifacts

All 31 local tests passed, including 15 prototype tests. Two independent builds produced byte-identical cases, pilot selections, summaries, manifests and scored samples. Existing-run overwrite was rejected without altering the decision log. Source versions, temporal separation and all 103,495 sampled targets were checked against the analytical baseline. Full policy tickets reconcile to 2,135. Receipt hydration verifies exact coverage of all 100 selected keys and matching source versions. The private report was visually inspected in the local browser.

Shareable aggregates and provenance are in `evidence/detection_prototype_20261028`. Private cases, receipts and HTML are in `output/detection_prototype_20261028/run_v1` at the workspace root. The report is an evidence snapshot, not a live decision dashboard. `review_metrics.json` records the initial empty state; use the review CLI for current metrics. No private cases or receipt records were copied into release evidence. The existing ZIP remains the earlier snapshot; the new canonical source is not yet repackaged.

See [execution and review instructions](detection_prototype_reproduction.md).
