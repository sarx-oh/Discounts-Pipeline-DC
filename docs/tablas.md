# Tables and relationships

Names below omit catalog and schema. The builder assigns each layer to its isolated schema. The normalized ticket key is `CheckId, LocationId, BusinessDate`; raw data uses `Id` instead of `CheckId`.

| Layer and table | Grain and purpose |
|---|---|
| Bronze / checks_raw | Complete ticket with original arrays and provenance; correction source |
| Bronze / locations_raw, items_raw, revenue_centers_raw, employees_raw | Raw reference catalogs |
| Silver / checks | Normalized ticket, timestamps and amounts |
| Silver / dim_locations, dim_items, dim_revenue_centers, dim_employees | Normalized reference catalogs; employee deletion flags retained |
| Silver / items_sold | Item line per ticket and array position |
| Silver / payments | Payment per ticket and position; supports mixed payments and reversals |
| Silver / discounts | Ticket/item discount with scope and positions |
| Silver / taxes, voids | Tax/void event per ticket and position |
| Silver / item_quality | Line reconciliation, discrepancies and unassessable cases |
| Silver / ticket_quality | Missing data, time and reconciliation flags per ticket |
| Silver / reference_quality | Unmatched-reference counts by check |
| Gold / ticket_metrics | Enriched ticket with metrics and quality flags |
| Gold / daily_location_channel | Daily location/channel aggregate for dashboard consumption |
| Gold / discount_type_daily | Daily location/channel/type/scope aggregate |
| Gold / employee_ticket_activity | Employee participation in ticket; not automatic responsibility for anomalies |
| Gold / employee_activity_daily | Daily location/channel/employee activity |
| Gold / review_thresholds | Thresholds and cohort sizes for the execution |
| Gold / review_cases | Exploratory review candidates, not confirmed fraud |

Catalog relationships follow keys declared in Silver. Array positions are not persistent business IDs and can change after corrections. PK/FK declarations follow data checks; they are NOT ENFORCED. Optional unmatched references prevent declaring the corresponding whole-table FK. Conditional item-discount relationships are checked in data.

## Operational support

- `ingestion_manifest`: processed/adopted file metadata prevents unnecessary rereads.
- `pipeline_state`: layer status and input/output versions.
- `pipeline_incoming_*`: ingestion staging tables, not analytical outputs.
- `threshold_snapshot_<hash>`: immutable row with typed threshold array and provenance, read at Delta version 0.
- `threshold_run_history`: Gold execution, snapshot and version history.

Tests protect all 25 original main tables. Test support tables exist only in generated schemas.

## Discount review base

`workspace.applebees_test_fdab42c8d6ad_discount_review` contains `ticket_features`, `discount_events`, `policy_review_candidates`, `employee_weekly` and `review_decision_log`, all version 0. See [results](descuentos_soluciones.md).

Relationships use the composite ticket key. `event_key` includes discount scope and positions and identifies an event only within the snapshot. `case_id` connects candidates to future decisions. New tables use process-level uniqueness and reconciliation checks, without additional declared FKs. The decision log is empty; its local validation contract is not a deployed application.
