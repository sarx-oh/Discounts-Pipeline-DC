# Test Job results

Suite status: **PASS**.

Job: `372187525837578`. Sandbox: `applebees_test_f1e4901c804c`.

| Scenario | Run | Job status | Independent verification |
|---|---|---|---|
| Initial load | [1002764398858282](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/372187525837578/run/1002764398858282) | SUCCESS | PASS |
| Unchanged repeat | [14430882277484](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/372187525837578/run/14430882277484) | SUCCESS | PASS |
| New file and correction | [98450439332572](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/372187525837578/run/98450439332572) | SUCCESS | PASS |
| Duplicate rejection | [294698028124863](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/372187525837578/run/294698028124863) | FAILED | PASS |
| Recovery | [857356524085370](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/372187525837578/run/857356524085370) | SUCCESS | PASS |

The duplicate scenario expects FAILED and downstream UPSTREAM_FAILED. Suite PASS confirms rejection and unchanged data tables, not acceptance of the invalid batch.

Dashboard unchanged after completion: `True`.

Every successful run checks all 25 original table versions. Inputs are synthetic; the 11 GB are not reingested. Reports contain no real tickets.

## Independent checks

### Initial load

- unique_tickets
- snapshot_registered
- initial_snapshot_created
- reconciled_totals
- all_layers_complete

### Unchanged repeat

- unique_tickets
- snapshot_registered
- repeat_no_json_read
- repeat_no_raw_write
- repeat_payload_and_timestamps_identical
- repeat_same_snapshot
- reconciled_totals
- all_layers_complete

### New file and correction

- unique_tickets
- snapshot_registered
- new_snapshot_for_changed_input
- omitted_ticket_retained
- removed_children_not_retained
- corrected_channel
- incomplete_retained
- reconciled_totals
- all_layers_complete

### Duplicate rejection

- failure_keeps_all_data_versions
- bronze_incomplete_after_rejected_batch

### Recovery

- unique_tickets
- snapshot_registered
- new_snapshot_for_changed_input
- omitted_ticket_retained
- removed_children_not_retained
- corrected_channel
- incomplete_retained
- reconciled_totals
- all_layers_complete

Observed 2 Bronze attempts during duplicate testing. Serverless auto-optimization can retry even with max_retries=0; see [operations](operacion.md).

## Limitations

These tests verify functional correctness with fixtures and retain historical regression evidence. They do not measure real-load performance or promote the pipeline to the current dashboard. POS hierarchy and business questions remain documented under [quality](calidad.md).
