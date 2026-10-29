# Deeper discount analysis protocol

Update: the [deeper investigation findings and options](deep_discount_findings.md) now include completed remote analyses and replication. Earlier recommendations and pending-status notes below are retained as historical context; no final operational model has been selected.


Status: active investigation, registered October 27, 2026 before new model results. This supplements the validated baseline; no operational model is selected. The earlier recommendation of rules plus logistic regression is provisional and is being reassessed.

## Evidence and estimands

The full pinned snapshot has 2,142,846 tickets. Existing local model extracts contain 103,495 eligible tickets selected by `pmod(xxhash64(CheckId,LocationId,BusinessDate),20)=0`. They omit gratuities, products, detailed mixed payments and manager context. They cannot answer those questions. The original final period has already been examined, so repeated evaluation is exploratory temporal replication, not untouched confirmation.

Occurrence is any positive discount event. Intensity is net recorded discount divided by gross on valid positive accounts; positive-event occurrence and net positive amount must be checked separately. Policy compatibility is a separate target requiring confirmed mappings. No misuse labels exist.

Code audit: gratuity follows the confirmed POS convention; `payment_amount_raw + gratuity_raw = account_candidate`. Interpreted gratuity is `-gratuity_raw` only with compatible signs and reconciliation. SQL SUM ignores null components, so payment-level completeness must be checked before interpreting ticket totals. Final-account tip rates mechanically increase when the denominator falls. Analyze recorded amount, gross-based rate and final-account rate separately. Gross plus current taxes is not an observed pre-discount account; do not reconstruct pre-discount taxes without evidence.

## Locked initial experiments

1. Existing sample: expanding temporal fits through May 31, June 30 and July 25, evaluated respectively in June, July 1-25 and July 26-August 20. Fixed regularization and fixed tree complexity; no selection on later results. Compare prevalence, context logistic, payment logistic, employee-context logistic and shallow boosted trees. Report predictive metrics, calibration, location/date block-bootstrap paired differences and group permutation importance. Bootstrap intervals conditional on fitted models do not include training uncertainty.
2. Separate conditional positive-intensity models: constant conditional mean, fractional logistic mean and bounded boosted regression. Compare conditional performance and the product of occurrence probability and conditional intensity on all eligible tickets. Clip only tolerance-level ratios above one and report their count; do not silently change target definitions.
3. Remote audit: payment-level sign/null counts, composite-key join preservation, discounts with mixed signs, final versus decision-time variables, voids and product coverage. Keep nonpositive accounts, refunds/reversals of unresolved meaning, and fully discounted tickets in explicit separate cohorts.
4. Remote cash/card contrasts: within employee-location-week-channel, then product and ticket-context adjustment; report common support and sensitivity to minimum support and promotion exclusions. Mixed payments use payment-line presence and positive-amount variants, not a single residual category.
5. Gratuity: card, cash and mixed recording coverage; zero recorded versus missing; conditional associations with discount occurrence/type/intensity, amount and both denominators. Tip variables describe retrospective outcomes, not information available for authorization.
6. Employee and manager context: adjusted persistence with shrinkage, sample-size coverage, temporal changes, concentration conditional on operational opportunity and promotion composition. Identify manager fields as recorded associations, not verified authorizers. Multiple comparisons require false-discovery control and temporal replication before prioritization claims.

## Confirmation and hypothesis register

| ID | Hypothesis | Initial status | Confirmation requirement |
|---|---|---|---|
| H1 | Cash association persists within employee and operating context | Unresolved | Independent hash partition, time replication, support audit |
| H2 | Recorded gratuity association survives denominator and context adjustment | Unresolved | Completeness audit, gross-rate and amount consistency, temporal replication |
| H3 | Conditional intensity modeling improves over constant severity | Unresolved | Fixed-model temporal metrics and clustered uncertainty |
| H4 | Nonlinearity improves frequency prediction materially | Unresolved | Paired out-of-period loss and calibration, not AUC alone |
| H5 | Employee differences persist beyond payment, location and composition | Unresolved | Shrinkage, opportunity coverage, multiplicity and later-period replication |
| H6 | Manager pair concentration adds useful review context | Unresolved | Opportunity-adjusted comparisons and policy interpretation |
| H7 | Clustering improves comparison coverage or stability | Unresolved | Demonstrated utility over explicit context; otherwise omit |

For new remote confirmation reserve hash residue 19 of 20, excluding the old residue 0 sample. Freeze specifications before reading its outcomes. Full-population aggregates have already informed hypotheses, so this is partially held-out record-level replication, not pristine external confirmation. Later independent dates or locations and human-reviewed cases remain necessary. Secondary discoveries are exploratory and are logged before any separate confirmation.

## Outputs and protections

New work files: `output/discount_deep_20261027/`, outside release. New source scripts use `deep_` names. Preserve existing evidence and release ZIP. Read only pinned sandbox tables; no original table, Job or dashboard edits, no raw reingestion. Record source versions, hashes, counts, executed SQL, failures and runtime. Export only aggregate evidence. Private examples keep identifiers outside the release.

Authentication check on October 27 failed with `no cached credentials`; user login is required for new remote queries. Local analysis proceeds independently. Completion requires remote payment/tip and contextual investigations plus evidence-backed options; completion is not implied by local model comparison.

## First experiment update

The fixed local temporal experiment is complete; see [preliminary results](deep_analysis_preliminary.md). H3 has exploratory support in three windows. H4 has mixed evidence. H1 remains unresolved within employee/product context; H2 and H5-H7 remain unresolved. The remote recording audit and within-employee cash/card and tip-denominator queries are prepared, not executed.

## Payment-support extension

[Local within-employee support and payment contrasts](deep_payment_support.md) provide exploratory evidence for H1 on part of the existing sample. Coverage falls to 18.96% at two records per method per employee/location/channel/week and to 0.41% at five. Full-data and product-adjusted confirmation remains required. Three prepared remote queries remain unexecuted; authentication is still unavailable.

## Locked record-partition replication after enriched exploration

Before extracting residue 19 outcomes: evaluate July 26-August 20 residue 19 tickets using models fit on residue 0 through July 25. Fixed comparisons: payment logistic versus context logistic, product/detailed-payment versus legacy-payment logistic, retrospective tip versus product/employee logistic, and conditional fractional severity versus conditional mean. Do not tune on residue 19. Evaluate fixed shallow boosted occurrence as a sensitivity to the previously mixed H4 result. This partition was excluded from sample fitting but included in earlier full-population aggregates, so it is partially reserved replication, not pristine external confirmation. Preserve all results, including failures and small gains. No operational model selection follows from the replication alone.
