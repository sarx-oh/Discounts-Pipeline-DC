"""Run the standalone detector on Databricks using pinned Spark SQL inputs.

Read-only against analytical/source tables. Writes only a new, explicitly named
prototype volume. Never updates the ingestion Job, source tables or dashboard.
Private extracts and receipts stay in that volume and are excluded from exports.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import date, datetime
from prepare_discount_query import render


def encode_value(value):
    """Match SQL Statements JSON_ARRAY string values for existing model contracts."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def run(spark, dbutils, source_root, schema):
    """Extract pinned data, fit models, hydrate receipts and return aggregate evidence.

    schema must be a fresh isolated name; existing schemas are rejected to avoid
    overwriting private runs. Run state is written progressively for diagnosis.
    No actual review decisions are fabricated or submitted.
    """
    source_root = Path(source_root)
    if not re.fullmatch(r'workspace\.applebees_test_[a-f0-9]{12}_prototype', schema):
        raise ValueError('Expected a fresh workspace.applebees_test_<12 hex>_prototype schema')
    state = json.loads((source_root/'configs/pinned_analysis_state.json').read_text())
    # Validate version coherence using the same renderer as the analytical CLI.
    _, pinned = render('SELECT * FROM {{ticket_metrics}} JOIN {{payments}} USING(CheckId,LocationId,BusinessDate) JOIN {{items_sold}} USING(CheckId,LocationId,BusinessDate) JOIN {{discounts}} USING(CheckId,LocationId,BusinessDate)', state)
    protected = [f'workspace.applebees_{layer}.{name}' for layer, names in {
        'bronze': [n+'_raw' for n in ['checks','locations','items','revenue_centers','employees']],
        'silver': ['checks','dim_locations','dim_items','dim_revenue_centers','dim_employees','items_sold','payments','discounts','taxes','voids','item_quality','ticket_quality','reference_quality'],
        'gold': ['ticket_metrics','daily_location_channel','discount_type_daily','employee_ticket_activity','employee_activity_daily','review_thresholds','review_cases'],
    }.items() for name in names]
    def versions():
        return {t:int(spark.sql(f'DESCRIBE HISTORY {t} LIMIT 1').first().version) for t in protected}
    before = versions()
    # CREATE without IF NOT EXISTS deliberately refuses reuse of a prior run.
    spark.sql(f'CREATE SCHEMA {schema}')
    spark.sql(f'CREATE VOLUME {schema}.artifacts')
    volume = Path('/Volumes')/schema.replace('.', '/')/'artifacts'
    run_id = uuid.uuid4().hex
    work = volume/run_id
    work.mkdir()
    base = work/'discount_solution'; base.mkdir()
    analysis = work/'discount_deep_20261027'; analysis.mkdir()
    report = {'status':'RUNNING', 'execution':'DATABRICKS_STANDALONE', 'run_id':run_id,
              'private_work_dir':str(work), 'queries':[], 'source_versions':pinned,
              'main_job_modified':False, 'human_reviews_submitted':0,
              'versions':{'python':sys.version.split()[0], **{p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','statsmodels','matplotlib']}}}
    def persist():
        (work/'databricks_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    def query(name, sql_template, destination):
        sql, used = render(sql_template, state)
        rows = spark.sql(sql).collect()
        data = {'statement_id':'spark:'+run_id+':'+name, 'sources':used,
                'rows':[{k:encode_value(v) for k,v in r.asDict().items()} for r in rows]}
        destination.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
        report['queries'].append({'name':name,'rows':len(rows),'sql_sha256':hashlib.sha256(sql.encode()).hexdigest(), 'sources':used})
        persist()
        print(f'{name}: {len(rows)} rows (private output retained in volume)',flush=True)
    def template(name):
        return (source_root/'src/analysis'/name).read_text()
    def script(name,*args):
        env = dict(os.environ, OPENBLAS_NUM_THREADS='2', OMP_NUM_THREADS='2')
        result = subprocess.run([sys.executable,str(source_root/'tools'/name),*map(str,args)],env=env,capture_output=True,text=True)
        if result.returncode:
            # Save diagnostics privately; do not emit private rows into notebook output.
            (work/(name+'.error.txt')).write_text(result.stdout+'\n'+result.stderr)
            raise RuntimeError(f'{name} failed; inspect private diagnostics in the run volume')
        return result.stdout
    persist()
    try:
        (base/'state_response.json').write_text(json.dumps(state,indent=2))
        periods={'train':"BusinessDate<DATE'2026-07-01'", 'validation':"BusinessDate>=DATE'2026-07-01' AND BusinessDate<DATE'2026-07-26'", 'test':"BusinessDate>=DATE'2026-07-26'"}
        for name, condition in periods.items():
            query('baseline_'+name,template('discount_model_sample.sql')+'\n AND '+condition,base/f'discount_model_{name}_data.json')
        periods={'train_early':"BusinessDate<DATE'2026-06-01'",'train_late':"BusinessDate>=DATE'2026-06-01' AND BusinessDate<DATE'2026-07-01'",'validation':"BusinessDate>=DATE'2026-07-01' AND BusinessDate<DATE'2026-07-26'",'test':"BusinessDate>=DATE'2026-07-26'"}
        for name, condition in periods.items():
            query('enriched_'+name,template('deep_enriched_sample.sql').replace('{{period_filter}}',condition),analysis/f'enriched_{name}_data.json')
        query('employee_weeks',template('deep_employee_weeks.sql'),analysis/'employee_weeks_data.json')
        query('policy_events',template('detection_policy_events.sql'),work/'policy_events_data.json')
        output = work/'review_run'
        script('build_detection_prototype.py','--analysis',analysis,'--policy-events',work/'policy_events_data.json','--output',output)
        pilot = json.loads((output/'pilot.json').read_text())
        keys = sorted(row['ticket_key'] for row in pilot['selected'])
        if len(keys)!=100 or len(set(keys))!=100 or any(not re.fullmatch('[0-9a-f]{64}',key) for key in keys):
            raise ValueError('Expected 100 distinct fixed pilot keys')
        receipts_sql=template('detection_pilot_receipts.sql').replace('{{ticket_filter}}',','.join("'"+key+"'" for key in keys))
        query('pilot_receipts',receipts_sql,output/'pilot_receipts_data.json')
        script('hydrate_detection_pilot.py','collect','--run',output)
        # POSIX review-event tests run in temporary driver storage, never on volume logs.
        tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(source_root/'tests'),'-p','test_*.py'],cwd='/tmp',capture_output=True,text=True)
        (work/'local_contract_tests.txt').write_text(tests.stdout+tests.stderr)
        if tests.returncode:raise RuntimeError('Contract tests failed on Databricks driver')
        summary=json.loads((output/'summary.json').read_text())
        after=versions()
        if before!=after:raise RuntimeError('Protected source versions changed during execution')
        report.update(status='PASS', summary=summary,
                      pilot={k:v for k,v in pilot.items() if k!='selected'},
                      receipt_coverage=len(json.loads((output/'receipt_evidence.json').read_text())['records']),
                      private_report_path=str(output/'review.html'), protected_tables_unchanged=True,
                      protected_table_count=len(before), contract_tests_passed=True,
                      source_sha256={str(p.relative_to(source_root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['src','tools','configs'] for p in (source_root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        persist()
        return report
    except Exception as exc:
        report.update(status='FAILED',error_type=type(exc).__name__,error=str(exc))
        persist()
        raise
