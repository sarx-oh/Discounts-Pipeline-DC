# Validation and remaining decisions

## Historical evidence

- Synthetic layer suite: PASS, identifier d0a4f8d1cc99.
- Original-data sandbox: PASS_WITH_EXPLORATORY_DIFFERENCES, identifier 0eef22876f8b. Eighteen of twenty outputs matched; threshold/case differences were reviewed.
- Frozen-threshold original regression: Job 813906415264245, run 513937693170625. Four successful tasks without rereading original JSON. This Job does not accept new loads.

Sanitized reports are in `evidence`. `source_comparison.json` records the earlier notebook comparison: Bronze, Silver and Audit were identical; Gold changed only its threshold cell. Shared support subsequently added portable configuration, snapshots and execution protection. The current Job source hashes are in `incremental_job.json`.

## Current adaptable test Job

Job 372187525837578, sandbox `applebees_test_f1e4901c804c`. All five independent scenario checks passed. Four valid runs succeeded; the duplicate run failed as expected with downstream tasks blocked. The dashboard remained unchanged. See [results](resultado_job.md).

| Scenario | Verified behavior |
|---|---|
| Initial | 40 unique tickets, reconciled totals and registered snapshot |
| Repeat | No JSON reads or raw writes; identical data, timestamps and snapshot |
| New file and correction | 41 tickets; omitted ticket retained; removed children absent; channel corrected; incomplete ticket flagged; new snapshot |
| Invalid duplicate | Bronze rejects it; dependents blocked; all data-table versions unchanged |
| Recovery | Corrected input; all four tasks and checks pass |

Sixteen local tests cover ingestion contracts, snapshots, dependencies, original constants, clean notebooks, destination guards and future review decisions. Remote tests execute the real notebooks; they are not production performance measurements.

## Analytical preparation

The original-data sandbox supports cash/card analysis and its extension to employees, rules and temporal model comparisons. See [solution options](descuentos_soluciones.md) and [delivery audit](auditoria_entrega.md). There are no confirmed-fraud labels or final operational deployment. Publication, presentation, policy mapping and evaluator clarification remain separate decisions.
