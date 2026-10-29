# Data quality and threshold policy

## Dynamic controls

New-load validation checks unique keys, structure, relationships, monetary reconciliation and consistency across layers. Amounts retain their signs and use decimal types; the configured tolerance is 0.02. Ambiguous duplicates are rejected before MERGE. Incomplete layers prevent downstream consumption of failed executions.

Incomplete tickets and unmatched references remain available with quality flags. A reconciliation difference alone does not establish fraud or justify deleting a ticket. Metric filters and denominators must respect quality flags.

Original controls remain in `configs/pipeline.json`: 2,142,846 tickets over 115 days, April 28 through August 20, 2026, plus historical totals. `run_original_regression=false` prevents requiring those fixed totals for new data. Enable it only for regression against the original-data copy.

The POS `Sequence/ParentSequence` hierarchy remains `PENDIENTE_DEFINICION` (definition pending): it is measured without asserting an unconfirmed business relationship. `NO_APLICA` (not applicable) is expected for historical regression checks on fixtures and new loads. A successful Job does not resolve semantic questions.

## Reproducible thresholds

Exploratory P95 thresholds use `percentile_approx` with accuracy 10000. Historical review found 9,037 cases versus the earlier 9,034. The three additional cases also appeared with exact percentiles. This indicates estimator sensitivity, not confirmed real-world anomalies.

The Job derives a SHA-256 key from Bronze versions, code, configuration and method. Existing keys reuse an immutable snapshot at Delta version 0. Changed inputs or implementation create a new snapshot. A Delta version change without changed values may also create a snapshot: this policy is conservative.

Each snapshot stores a typed threshold array in one row with metadata, including when no cohorts qualify. `review_thresholds` exposes the version used for cases. `threshold_run_history` connects snapshots to Gold input/output versions and executions. GOLD_COMPLETE means Gold finished; full Job success also requires Audit.

Snapshots must not be deleted or overwritten. Retaining tables and versions is part of the traceability contract.

## Business semantics requiring confirmation

The meanings of EmployeeId=0, ManagerId=0 and the manager's authorization role are not assumed. An unmatched ID does not prove the catalog is incomplete. Tip signs follow the convention confirmed by the organizers. Distinguishing refunds or reversals from ordinary payments requires business evidence. Missing recorded cash tips do not prove that no cash tips were paid.

According to the clarification received, Employee Meal Discount and Employee Fifty must not combine with other discounts. Their exact IDs/labels and the scope of incompatibility (whole ticket or same item line) require confirmation before declaring violations. The [candidate registry](../configs/review_policy_candidates.json) and [analysis](descuentos_soluciones.md) document exploratory checks, not automatic enforcement.
