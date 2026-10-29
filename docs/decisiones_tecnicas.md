# Technical decisions

| Topic | Current decision and reconsideration criteria |
|---|---|
| Orchestration | A Job with dependencies, layer states and audit. The Phase 2 deliverable explicitly asks for a Databricks job or workflow; this implementation uses that option and explains its dependencies and recovery. |
| Streaming | Complete-file batches make corrections explicit. Consider streaming only with a latency requirement and update contract; it is not implemented. |
| Materialized views | Silver and Gold rebuild in batches. Evaluate supported queries and sources for maintenance cost and latency improvements; none have been measured. |
| Liquid clustering | Not enabled. Evaluate representative queries and volumes; date and location are candidates, not proven optimal keys. |
| Expectations | Assertions, layer states and quality tables are implemented. Lakeflow expectations are not used; incomplete tickets are not silently discarded. |
| Percentiles | Approximate values support exploration and are persisted in snapshots; exact percentiles were used for historical comparison. |
| New loads | Bronze merges complete tickets; downstream layers rebuild. Incremental Silver/Gold optimization requires measurement. |

References: [materialized views](https://docs.databricks.com/aws/en/ldp/materialized-views), [liquid clustering](https://docs.databricks.com/aws/en/delta/clustering), [percentile_approx](https://docs.databricks.com/aws/en/sql/language-manual/functions/percentile_approx), [percentile](https://docs.databricks.com/aws/en/sql/language-manual/functions/percentile).

The Phase 2 guide asks teams to explain the use or consideration of these technologies. The layout follows the Basic Databricks GitHub Repository Template, retaining existing notebook filenames for compatibility. `resources/pipelines` documents a decision, not a deployed declarative pipeline.

Statistical clustering in the discount analysis is separate from Delta liquid clustering: the former groups observations; the latter concerns table storage layout.
