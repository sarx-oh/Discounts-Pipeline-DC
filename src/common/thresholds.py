"""Immutable threshold snapshots keyed by validated input, code and configuration."""
import hashlib
import json


def snapshot_key(bronze_versions, code_hash, config_hash):
    """Hash input versions, code, configuration and method into the immutable threshold identity."""
    payload = {'bronze': bronze_versions, 'code': code_hash, 'config': config_hash,
               'method': 'percentile_approx_0.95_accuracy_10000'}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def materialize_thresholds(ctx, compute, code_hash, job_run_id):
    """Create or reuse a version-zero threshold snapshot, verify its provenance, and refresh the Gold reference table."""
    from pyspark.sql import functions as F
    bronze = ctx.require_complete('bronze')
    key = snapshot_key(bronze, code_hash, ctx.config_hash)
    table = ctx.table('gold', 'threshold_snapshot_' + key[:32])
    reused = ctx.spark.catalog.tableExists(table)
    if not reused:
        values = compute()
        envelope = values.agg(F.collect_list(F.struct(*[F.col(c) for c in values.columns])).alias('thresholds'))
        envelope = (envelope.withColumn('snapshot_key', F.lit(key))
                    .withColumn('code_hash', F.lit(code_hash))
                    .withColumn('bronze_versions_json', F.lit(json.dumps(bronze, sort_keys=True)))
                    .withColumn('created_at', F.current_timestamp()))
        envelope.write.format('delta').mode('error').saveAsTable(table)
    snapshot = ctx.spark.read.option('versionAsOf', 0).table(table)
    metadata = snapshot.select('snapshot_key', 'code_hash', 'bronze_versions_json').collect()
    assert len(metadata) == 1 and metadata[0].snapshot_key == key
    assert metadata[0].code_hash == code_hash
    assert json.loads(metadata[0].bronze_versions_json) == bronze
    assert ctx.require_complete('bronze') == bronze
    values = snapshot.select(F.explode('thresholds').alias('threshold')).select('threshold.*')
    values.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable(ctx.table('gold','review_thresholds'))
    ctx.threshold_snapshot = {'key': key, 'table': table, 'version': 0, 'reused': reused,
                              'bronze_versions': bronze, 'code_hash': code_hash, 'job_run_id': job_run_id}
    return values


def record_threshold_use(ctx):
    """Append idempotent usage metadata only after Gold is COMPLETE; link thresholds to input and output versions."""
    from datetime import datetime, timezone
    metadata = dict(ctx.threshold_snapshot)
    outputs = ctx.require_complete('gold')
    metadata.update({'gold_run_id': ctx.run_id, 'silver_versions': ctx.inputs,
                     'gold_versions': outputs, 'status': 'GOLD_COMPLETE',
                     'recorded_at': datetime.now(timezone.utc).isoformat()})
    target = ctx.table('gold', 'threshold_run_history')
    ctx.spark.sql(f'CREATE TABLE IF NOT EXISTS {target} (gold_run_id STRING, job_run_id STRING, snapshot_key STRING, metadata_json STRING) USING DELTA')
    row = [(ctx.run_id, metadata['job_run_id'], metadata['key'], json.dumps(metadata, sort_keys=True))]
    view = 'threshold_use_' + ctx.run_id.replace('-', '')
    ctx.spark.createDataFrame(row, 'gold_run_id STRING,job_run_id STRING,snapshot_key STRING,metadata_json STRING').createOrReplaceTempView(view)
    ctx.spark.sql(f'MERGE INTO {target} t USING {view} s ON t.gold_run_id=s.gold_run_id WHEN NOT MATCHED THEN INSERT *')
    ctx.spark.catalog.dropTempView(view)
    return metadata
