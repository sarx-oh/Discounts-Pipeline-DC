# Payment association and within-employee support

Historical intermediate analysis. The [completed deeper investigation](deep_discount_findings.md) includes subsequent full-data work; earlier authentication/pending-status statements below describe the state at this intermediate stage.


Status: exploratory local evidence only. This does not replace the pending full-snapshot payment, product and gratuity investigation.

The existing 103,495-ticket sample contains 85,905 pure cash/card tickets with attributable employees. Eleven sampled tickets lack a usable employee key. All results below concern previously examined periods, not an untouched holdout.

## Direct matched-cell comparison

Common weights equal combined cash and card tickets in each supported cell. Each method receives the same weights. The baseline cells share location, channel and week; employee cells additionally share the recorded payment employee. Only cells with the required count for both methods contribute.

| Cell definition | Minimum per method | Supported tickets | Coverage of 85,905 | Cash minus card frequency |
|---|---:|---:|---:|---:|
| Location/channel/week | 1 | 78,204 | 91.04% | +7.32 pp |
| Location/channel/week | 2 | 75,813 | 88.25% | +7.41 pp |
| Location/channel/week | 5 | 66,709 | 77.65% | +7.34 pp |
| Employee/location/channel/week | 1 | 44,493 | 51.79% | +7.25 pp |
| Employee/location/channel/week | 2 | 16,288 | 18.96% | +6.91 pp |
| Employee/location/channel/week | 5 | 355 | 0.41% | -1.53 pp |

The last row is a different, tiny selected population (30 cells), not evidence of a general reversal. Raising support thresholds changes both precision and the estimand's population. Neither unrestricted aggregation nor demanding large cells alone solves this problem. The 5% sample is insufficient for detailed direct matching across employees, weeks and product context. These descriptive differences have no inferential intervals and are not causal effects.

## Model-standardized payment contrasts

Models use preceding dates only and include location, channel, hour, weekday, gross, line count and traffic. A regularized employee indicator is added in the second specification. Evaluation is restricted to employee/location/channel combinations with both cash and card observed during training; this is coarse overlap support, not proof of overlap across every continuous covariate. The same evaluation records are predicted with payment set first to cash and then to card. This is a model-based descriptive contrast, not an observed intervention.

| Evaluation window | Supported evaluation tickets | Coverage of eligible pure attributed evaluation | Difference without employee | Difference with employee |
|---|---:|---:|---:|---:|
| June | 16,958 | 76.72% | +8.02 pp | +8.03 pp |
| July 1-25 | 15,232 | 81.14% | +7.47 pp | +7.47 pp |
| July 26-August 20 | 15,166 | 83.60% | +7.43 pp | +7.46 pp |

The association is not materially attenuated by this particular regularized employee specification. That does not establish absence of employee confounding: shrinkage, sparse profiles, missing product mix and common-effect assumptions limit interpretation. Payment may itself be downstream of the discount process. The fitted odds ratios of approximately 1.95-2.02 are conditional associations, not causal risk ratios.

Saved crossed location/date intervals reflect variation in evaluation composition with model coefficients held fixed. They omit coefficient estimation uncertainty and must not be presented as inferential effect confidence intervals. Full refitting or an appropriate clustered inferential model is still needed. Statistical employee controls do not prove authorization roles.

## Implication for the investigation

H1 receives additional exploratory support in part of the local sample, while remaining unresolved at the requested full-data/product-adjusted level. The priority is to execute the prepared full-data within-employee query, quantify coverage under several thresholds, and then extend it to promotion and product context. A universal cash restriction is not justified by these results. No employee or ticket is labeled improper.

## Reproduction

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 tools/deep_payment_support.py ../output/discount_solution ../output/discount_deep_20261027/payment_support.json
```

[Aggregate evidence](../evidence/discount_deep_20261027/payment_support.json) contains input hashes, pinned source versions, code hash, support counts and model results. No individual identifiers are exported. Sources and sample keys are verified before fitting. Remote queries remain unexecuted because the CLI profile has no cached credentials.
