# Fresh release pipeline results

Job `546964718724235`, isolated sandbox `applebees_test_076460f5ea95`. All five scenario checks passed. The original Job `372187525837578` was not modified.

| Scenario | Run | Job outcome | Independent check |
|---|---|---|---|
| initial | [369266779524390](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/546964718724235/run/369266779524390) | SUCCESS | PASS |
| repeat | [967132151154348](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/546964718724235/run/967132151154348) | SUCCESS | PASS |
| changed | [657015725481567](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/546964718724235/run/657015725481567) | SUCCESS | PASS |
| failure | [516619814095417](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/546964718724235/run/516619814095417) | FAILED | PASS |
| recovery | [969124821786572](https://dbc-16eae557-a41d.cloud.databricks.com/?o=7474660351820655#job/546964718724235/run/969124821786572) | SUCCESS | PASS |

The fixtures begin with 40 unique tickets. Repeating input leaves the raw payload and timestamps unchanged, reads no JSON and reuses the same threshold snapshot. A correction plus a new file produces 41 unique tickets, removes stale child rows for the corrected ticket, preserves an omitted existing ticket and retains an incomplete ticket with quality flags. Reconciled synthetic net sales change from 488 to 490 and discounts from 117 to 114. These are controlled test amounts, not restaurant business findings.

The duplicate case must fail in Bronze and block downstream tasks. Its verifier checks that data-table versions remain unchanged and the layer stays incomplete. Recovery succeeds after correcting the input. The suite also checks the original dashboard remains unchanged. Source hashes and detailed checks are retained in [the fresh evidence](../evidence/databricks_release_20261028/pipeline_validation.json); [historical results](resultado_job.md) are preserved separately. This is functional evidence, not a throughput benchmark.
