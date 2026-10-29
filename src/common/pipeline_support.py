"""Batch support shared by the three notebooks. Importing this file makes no writes.

Run one chain at a time. Stage status gates downstream notebooks; it is not a
distributed lock or a transaction spanning all dashboard tables. See docs/operacion.md.
Spark/Delta imports are lazy so contract tests can run without a Spark installation.
"""

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def load_config():
    """Load configuration from APPLEBEES_CONFIG_PATH or the repository default and validate its remapping contract."""
    import os
    config = json.loads(Path(os.environ.get("APPLEBEES_CONFIG_PATH", str(Path(__file__).resolve().parents[2] / "configs/pipeline.json"))).read_text())
    for value in [config["catalog"], *config["schemas"].values()]:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError("Invalid configuration identifier")
    if config["catalog"] != "workspace" or config["schemas"] != {
        "bronze": "applebees_bronze", "silver": "applebees_silver", "gold": "applebees_gold"
    }:
        raise ValueError("SQL logic and relationships require the configured namespace contract")
    if config["correction_mode"] not in {"upsert_tickets", "replace_files"}:
        raise ValueError("Unsupported correction mode")
    from decimal import Decimal
    if not Decimal(config["tolerance"]).is_finite() or Decimal(config["tolerance"]) <= 0:
        raise ValueError("Tolerance must be positive and finite")
    return config


def canonical_path(path):
    """Normalize the optional dbfs: prefix without changing the underlying volume path."""
    return path.removeprefix("dbfs:")


def sql_string(value):
    # Spark SQL escapes a quote with a backslash. Escape existing backslashes too.
    """Quote a literal for generated Spark SQL, escaping backslashes and single quotes."""
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def plan_files(inventory, recorded, forced=()):
    """Missing files stop the batch; omission is never an implicit tombstone."""
    missing = set(recorded) - set(inventory)
    if missing:
        raise ValueError(f"Recorded files are missing; review before continuing: {sorted(missing)}")
    unknown = set(forced) - set(inventory)
    if unknown:
        raise ValueError(f"force_files contains nonexistent paths: {sorted(unknown)}")
    return sorted(p for p in inventory if p in forced or inventory[p] != recorded.get(p))


def adoptable_files(inventory, provenance):
    """Adopt only files evidenced by stored rows, not newly discovered files."""
    adopted = []
    for row in provenance:
        if row["path"] not in inventory or row["null_ingests"] or row["first_ingest"] is None:
            raise ValueError("Insufficient provenance to adopt Bronze without rereading files")
        if inventory[row["path"]][1] > row["first_ingest"] * 1000:
            raise ValueError("Source changed after ingestion: explicit review required before adoption")
        adopted.append(row["path"])
    return adopted


def unknown_fields(observed, expected, prefix=""):
    """Reject new fields before using an established JSON reader schema."""
    if isinstance(observed, dict) and isinstance(expected, dict):
        if observed.get("type") == expected.get("type") == "struct":
            known = {f["name"]: f["type"] for f in expected["fields"]}
            result = []
            for field in observed["fields"]:
                name = prefix + field["name"]
                if field["name"] not in known:
                    result.append(name)
                else:
                    result.extend(unknown_fields(field["type"], known[field["name"]], name + "."))
            return result
        if observed.get("type") == expected.get("type") == "array":
            return unknown_fields(observed["elementType"], expected["elementType"], prefix + "[].")
    return []


def merge_sql(target, view, columns, keys, mode="upsert_tickets", files=()):
    """One Delta transaction: replace complete matching records, never append blindly."""
    for name in [*columns, *keys]:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"Invalid column: {name}")
    join = " AND ".join(f"t.`{k}` = s.`{k}`" for k in keys)
    payload = [c for c in columns if c != "ingested_at"]
    changed = " OR ".join(f"NOT (t.`{c}` <=> s.`{c}`)" for c in payload)
    updates = ", ".join(f"t.`{c}` = s.`{c}`" for c in columns)
    names = ", ".join(f"`{c}`" for c in columns)
    values = ", ".join(f"s.`{c}`" for c in columns)
    sql = (f"MERGE INTO {target} t USING {view} s ON {join}\n"
           f"WHEN MATCHED AND ({changed}) THEN UPDATE SET {updates}\n"
           f"WHEN NOT MATCHED THEN INSERT ({names}) VALUES ({values})")
    if mode == "replace_files":
        if not files:
            raise ValueError("Deletion requires an explicit file scope")
        scope = ", ".join(sql_string(p) for p in files)
        sql += f"\nWHEN NOT MATCHED BY SOURCE AND regexp_replace(t.source_file, '^dbfs:', '') IN ({scope}) THEN DELETE"
    elif mode == "replace_dimension":
        sql += "\nWHEN NOT MATCHED BY SOURCE THEN DELETE"
    elif mode != "upsert_tickets":
        raise ValueError("Unsupported merge mode")
    return sql


def assert_key(df, keys, name):
    """Reject null or duplicate composite keys before a write; never choose an arbitrary duplicate."""
    if df.filter(" OR ".join(f"`{k}` IS NULL" for k in keys)).limit(1).count():
        raise ValueError(f"Incomplete key: {name}")
    if df.groupBy(*keys).count().filter("count>1").limit(1).count():
        raise ValueError(f"Duplicate key: {name}; an arbitrary version will not be selected")


def assert_same_keys(left, right, keys, name):
    """Require multiset equality of keys so joins cannot silently lose or multiply tickets."""
    a, b = left.select(*keys), right.select(*keys)
    if a.exceptAll(b).limit(1).count() or b.exceptAll(a).limit(1).count():
        raise ValueError(f"Tickets lost, added or multiplied: {name}")


def require_isolated_destination(config):
    """Reject original or mixed destinations before any Spark operation."""
    schemas = config.get('schemas', {})
    bronze = schemas.get('bronze', '')
    match = re.fullmatch(r'(applebees_test_[a-f0-9]{12})_bronze', bronze)
    if not match or config.get('catalog') != 'workspace':
        raise ValueError('Execution requires a sandbox generated by build_sandbox.py')
    prefix = match.group(1)
    if schemas != {layer: prefix+'_'+layer for layer in ('bronze','silver','gold')}:
        raise ValueError('All three layers must belong to the same sandbox')
    if config.get('base_path') != f'/Volumes/workspace/{prefix}_bronze/raw':
        raise ValueError('Source must be the sandbox-owned volume')


class PipelineContext:
    """Manage version-pinned layer state in an isolated sandbox. This is a completion gate, not a distributed lock."""
    def __init__(self, spark, config, layer):
        require_isolated_destination(config)
        self.spark, self.config, self.layer = spark, config, layer
        self.run_id = str(uuid4())
        self.inputs = {}
        parameters = {k: v for k, v in config.items() if k not in {"force_files", "adopt_existing_files"}}
        self.config_hash = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        self.state_table = self.table("bronze", "pipeline_state")
        self.manifest_table = self.table("bronze", "ingestion_manifest")

    def table(self, layer, name):
        """Resolve a table name inside the configured medallion layer."""
        return f"{self.config['catalog']}.{self.config['schemas'][layer]}.{name}"

    def versions(self, tables):
        """Read the latest Delta version for each requested table."""
        return {t: int(self.spark.sql(f"DESCRIBE HISTORY {t} LIMIT 1").first().version) for t in tables}

    def state(self, layer):
        """Return the single persisted state row for a layer; missing or ambiguous state fails closed."""
        from pyspark.sql import functions as F
        if not self.spark.catalog.tableExists(self.state_table):
            raise ValueError("Pipeline state is missing; start with Bronze")
        rows = self.spark.table(self.state_table).filter(F.col("layer") == layer).collect()
        if len(rows) != 1:
            raise ValueError(f"Missing or ambiguous state for {layer}")
        return rows[0].asDict()

    def require_complete(self, layer):
        """Verify completion, configuration and unchanged upstream/output versions before consumption."""
        state = self.state(layer)
        if state["status"] != "COMPLETE":
            raise ValueError(f"{layer} is incomplete; rerun that layer before continuing")
        if state["config_hash"] != self.config_hash:
            raise ValueError(f"Configuration changed since {layer}; rerun the chain in order")
        outputs = json.loads(state["outputs_json"])
        if self.versions(outputs) != outputs:
            raise ValueError(f"Tables in {layer} changed outside the validated execution")
        if layer != "bronze":
            upstream = "bronze" if layer == "silver" else "silver"
            expected = json.loads(state["inputs_json"])
            actual = self.require_complete(upstream)
            if expected != actual:
                raise ValueError(f"{layer} is stale relative to {upstream}")
        return outputs

    def _write_state(self, status, outputs):
        row = [(self.layer, status, self.run_id, json.dumps(self.inputs, sort_keys=True),
                json.dumps(outputs, sort_keys=True), self.config_hash, datetime.now(timezone.utc).isoformat())]
        df = self.spark.createDataFrame(row, "layer STRING,status STRING,run_id STRING,inputs_json STRING,outputs_json STRING,config_hash STRING,updated_at STRING")
        view = "pipeline_state_" + self.run_id.replace("-", "")
        df.createOrReplaceTempView(view)
        self.spark.sql(f"MERGE INTO {self.state_table} t USING {view} s ON t.layer=s.layer "
                       "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *")
        self.spark.catalog.dropTempView(view)

    def begin(self):
        # All stages must run serially. RUNNING is deliberately left after a crash.
        """Record RUNNING after checking upstream state; a crash intentionally leaves this status visible."""
        if self.layer != "bronze":
            self.inputs = self.require_complete("bronze" if self.layer == "silver" else "silver")
        self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {self.config['catalog']}.{self.config['schemas']['bronze']}")
        self.spark.sql(f"CREATE TABLE IF NOT EXISTS {self.state_table} "
                       "(layer STRING,status STRING,run_id STRING,inputs_json STRING,outputs_json STRING,config_hash STRING,updated_at STRING) USING DELTA")
        self._write_state("RUNNING", {})

    def read_input(self, table):
        """Read exactly the Delta version captured when the layer began."""
        return self.spark.read.option("versionAsOf", self.inputs[table]).table(table)

    def finish(self, tables):
        """Publish COMPLETE only if this run still owns the layer and upstream versions remain unchanged."""
        if self.state(self.layer)["run_id"] != self.run_id:
            raise ValueError("Another run owns the layer; this run cannot approve it")
        if self.layer != "bronze":
            actual = self.require_complete("bronze" if self.layer == "silver" else "silver")
            if self.inputs != actual:
                raise ValueError("Sources changed during execution; retry in order")
        self._write_state("COMPLETE", self.versions(tables))
        print(f"{self.layer}: COMPLETE; run_id={self.run_id}")

    def sql(self, query):
        # Pin Silver sources in Gold's SELECTs. DDL/constraints use spark.sql directly.
        for index, name in enumerate(sorted(self.inputs, key=len, reverse=True)):
            if name in query:
                view = "pipeline_input_" + self.run_id.replace("-", "") + "_" + str(index)
                self.read_input(name).createOrReplaceTempView(view)
                query = query.replace(name, view)
        return self.spark.sql(query)


def list_json_files(dbutils, root):
    """Inventory source JSON files through dbutils; an empty checks input is a blocking error."""
    files, pending = {}, [root]
    while pending:
        for entry in dbutils.fs.ls(pending.pop()):
            if entry.isDir():
                pending.append(entry.path)
            elif entry.name == "checks.json":
                files[canonical_path(entry.path)] = (int(entry.size), int(entry.modificationTime))
    if not files:
        raise ValueError("No checks.json files; an accidental empty load will not be published")
    return files


def ingest_source(ctx, dbutils, name, inventory, keys):
    """Persist changed files and merge complete tickets; checkpoint only after commit.

    Dimensions are complete catalog snapshots; facts default to ticket upserts.
    A staging Delta table freezes each incoming batch before destination changes.
    """
    from pyspark.sql import functions as F
    from pyspark.sql.types import StructType
    spark = ctx.spark
    target = ctx.table("bronze", name + "_raw")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {ctx.manifest_table} "
              "(target_table STRING,file_path STRING,file_size LONG,modified_ms LONG,run_id STRING) USING DELTA")
    records = spark.table(ctx.manifest_table).filter(F.col("target_table") == target).collect()
    recorded = {r.file_path: (r.file_size, r.modified_ms) for r in records}
    exists = spark.catalog.tableExists(target)
    if recorded and not exists:
        raise ValueError(f"Manifest exists but {target} is missing; explicit recovery required")

    def checkpoint(paths):
        rows = [(target, p, *inventory[p], ctx.run_id) for p in paths]
        if not rows:
            return
        df = spark.createDataFrame(rows, "target_table STRING,file_path STRING,file_size LONG,modified_ms LONG,run_id STRING")
        view = "manifest_" + ctx.run_id.replace("-", "")
        df.createOrReplaceTempView(view)
        spark.sql(f"MERGE INTO {ctx.manifest_table} t USING {view} s "
                  "ON t.target_table=s.target_table AND t.file_path=s.file_path "
                  "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *")
        spark.catalog.dropTempView(view)

    if exists and not recorded:
        if not ctx.config["adopt_existing_files"]:
            raise ValueError("Existing Bronze has no manifest; review adoption before rereading the source")
        old = spark.table(target)
        assert_key(old, keys, target)
        provenance = old.select(F.regexp_replace("source_file", "^dbfs:", "").alias("path"),
                                F.col("ingested_at").cast("double").alias("ingested"))
        observed = provenance.groupBy("path").agg(F.min("ingested").alias("first_ingest"),
            F.sum(F.when(F.col("ingested").isNull(), 1).otherwise(0)).alias("null_ingests")).collect()
        adopted = adoptable_files(inventory, [r.asDict() for r in observed])
        checkpoint(adopted)
        recorded = {p: inventory[p] for p in adopted}
        print(f"{name}: {len(adopted)} archivos existentes adoptados por procedencia y fecha; sin releer JSON")

    forced = {canonical_path(p) for p in ctx.config["force_files"]}
    # The global force list is validated against the complete inventory in Bronze.
    changed = plan_files(inventory, recorded, forced.intersection(inventory))
    if not changed:
        print(f"{name}: sin archivos nuevos/modificados")
        return target
    def reader():
        # New reader each time: schema() mutates a DataFrameReader.
        return spark.read.option("multiLine", "true").option("mode", "FAILFAST").option("recursiveFileLookup", "true")
    if exists:
        schema = StructType([f for f in spark.table(target).schema.fields if f.name not in {"source_file", "ingested_at"}])
        incoming = reader().schema(schema).json(changed)
        # Empty array snapshots are allowed only with a known schema.
        if incoming.limit(1).count():
            inferred = reader().json(changed).schema
            extra = unknown_fields(inferred.jsonValue(), schema.jsonValue())
            if extra:
                raise ValueError(f"New fields require schema review: {extra}")
    else:
        incoming = reader().json(changed)
    incoming = incoming.select("*", F.regexp_replace(F.col("_metadata.file_path"), "^dbfs:", "").alias("source_file"))
    incoming = incoming.withColumn("ingested_at", F.current_timestamp())
    staging = ctx.table("bronze", "pipeline_incoming_" + name)
    incoming.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(staging)
    version = ctx.versions([staging])[staging]
    incoming = spark.read.option("versionAsOf", version).table(staging)
    assert_key(incoming, keys, "entrada " + name)
    if name == "checks":
        bad_date = incoming.filter("try_cast(BusinessDate AS DATE) IS NULL OR "
            "cast(try_cast(BusinessDate AS DATE) AS STRING) <> BusinessDate OR "
            "BusinessDate <> regexp_extract(source_file, 'dt=([0-9]{4}-[0-9]{2}-[0-9]{2})', 1)")
        if bad_date.limit(1).count():
            raise ValueError("Invalid date or date differs from its partition")
    elif not incoming.limit(1).count():
        raise ValueError("Empty catalog: dimension will not be deleted automatically")
    for path in changed:
        info = dbutils.fs.ls(path)
        if len(info) != 1 or (int(info[0].size), int(info[0].modificationTime)) != inventory[path]:
            raise ValueError("File changed during reading; retry")
    if exists:
        if name == "checks":
            previous = spark.table(target).select(*keys, F.regexp_replace("source_file", "^dbfs:", "").alias("previous_file"))
            collisions = incoming.select(*keys, "source_file").join(previous, keys)
            if collisions.filter(F.col("source_file") != F.col("previous_file")).limit(1).count():
                raise ValueError("The same ticket appears in different files; resolve precedence explicitly")
        view = "incoming_" + ctx.run_id.replace("-", "")
        incoming.createOrReplaceTempView(view)
        mode = ctx.config["correction_mode"] if name == "checks" else "replace_dimension"
        spark.sql(merge_sql(target, view, incoming.columns, keys, mode, changed))
        spark.catalog.dropTempView(view)
    else:
        # Spark Connect accepts "error", but rejects its "errorifexists" alias.
        incoming.write.format("delta").mode("error").saveAsTable(target)
    assert_key(spark.table(target), keys, target)
    checkpoint(changed)
    print(f"{name}: {len(changed)} archivos procesados; run_id={ctx.run_id}")
    return target
