# Operations and recovery

1. Maintain the Databricks project source tree as the delivery source of truth. Reconcile reviewed edits there, then export it into a fresh directory for packaging; see [source and release workflow](databricks_source_release.md). Do not confuse source files with the isolated runtime folders referenced by Jobs.
2. Generate an isolated deployment with `tools/build_sandbox.py`, inspect its names, and authenticate using Databricks CLI. No tokens or GitHub access are included.
3. Use `tools/remote_test.py` for synthetic validation only. Saved IDs and idempotency tokens allow resuming without duplicate Jobs or submissions.
4. Inspect all four tasks and verification reports. Creating a Job does not prove successful execution.

## Contract for future real loads

Tests cover the current input format. Structure, type or business-rule changes require a new version and validation; arbitrary schema adaptation is not promised.

Files must be complete and stable before execution. Preserve the existing fact/catalog directory structure. Detection uses path, size and modification time, not full-file hashes. Changes preserving those signals require `force_files`. Concurrent partial writes are not supported.

Corrections replace the complete ticket with the same key. They do not change its identity or delete omitted records. Moving an identity between files requires provenance review. Changing date, location or ID creates another key and requires an explicit replacement policy.

`replace_files` applies only to files confirmed as complete snapshots; it can delete omitted tickets and is not the default. Adoption avoids rereading history only when provenance controls pass; it cannot bypass changed-file checks.

## Failures

For duplicates, correct the input and rerun the chain. Do not manually mark COMPLETE, delete checkpoints or use VACUUM as a recovery mechanism. A Silver/Gold failure may leave tables at different versions; the layer remains incomplete. Recover through a full successful execution before consumption.

Do not run concurrent writers against the same schemas. External readers that ignore `pipeline_state` lack automatic protection from partial reconstruction. Future dashboard promotion needs a coherent publication policy; this package does not change the existing dashboard source.

Identical inputs reuse threshold snapshots. New data or corrections create another snapshot. Verify snapshot history and final Audit.

The synthetic Job is not a production Job for future real deliveries. Promotion requires data paths, permissions, destinations, load windows and publication policy. No schedule or promotion is automatic.

## Observed serverless retries

`max_retries=0` does not disable serverless auto-optimization. Duplicate tests produced another Bronze attempt that rejected the same input again. No at-most-once guarantee is made. Idempotency and state gates remain necessary. Disabling these attempts requires explicitly disabling auto-optimization and validating that configuration.

Reference: [serverless auto-optimization and retries](https://docs.databricks.com/aws/en/jobs/run-serverless-jobs#configure-serverless-compute-auto-optimization-to-disallow-retries).
