"""Executed inside a Databricks task with native spark/dbutils globals."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
from datetime import datetime, timezone

ROOT = Path(RUNTIME_ROOT)
manifest = json.loads((ROOT/'manifest.json').read_text())
PREFIX = manifest['prefix']
assert PREFIX.startswith('applebees_test_')
for path, expected in manifest['hashes'].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, path
CODE_HASH = manifest['code_hash']
os.environ['APPLEBEES_CONFIG_PATH'] = str(ROOT/'pipeline_config.json')
sys.path.insert(0, str(ROOT))
from pipeline_support import load_config, PipelineContext
from thresholds import record_threshold_use
CFG = load_config()
BASE = CFG['base_path']
assert BASE == f'/Volumes/workspace/{PREFIX}_bronze/raw'
assert set(CFG['schemas'].values()) == {PREFIX+'_'+l for l in ['bronze','silver','gold']}
assert not CFG['run_original_regression']
report = {'status':'RUNNING','stage':STAGE,'job_run_id':JOB_RUN_ID,'prefix':PREFIX,
          'fixture_kind':'synthetic','code_hash':CODE_HASH,'json_read_calls':0,'checks':[]}
NATIVE_SPARK, NATIVE_DBUTILS = spark, dbutils


def safe_path(path):
    path = path.removeprefix('dbfs:')
    assert path.startswith(BASE+'/') and '..' not in path.split('/'), path
    return path


class Reader:
    def __init__(self, reader): self.reader=reader
    def option(self,*a,**k): self.reader=self.reader.option(*a,**k);return self
    def schema(self,*a,**k): self.reader=self.reader.schema(*a,**k);return self
    def table(self,name):
        assert name.replace('`','').startswith('workspace.'+PREFIX+'_'),name
        return self.reader.table(name)
    def json(self,paths):
        for path in ([paths] if isinstance(paths,str) else paths):safe_path(path)
        report['json_read_calls'] += 1
        return self.reader.json(paths)


class GuardSpark:
    @property
    def read(self): return Reader(NATIVE_SPARK.read)
    def sql(self,query,*a,**k):
        normalized=query.lower().replace('`','')
        assert not any('workspace.applebees_'+layer in normalized for layer in ['bronze','silver','gold','eda']),query
        assert not any(x in normalized for x in ['vacuum','read_files(']),query
        return NATIVE_SPARK.sql(query,*a,**k)
    def table(self,name):return self.read.table(name)
    def __getattr__(self,name):return getattr(NATIVE_SPARK,name)


class FS:
    def ls(self,path):safe_path(path);return NATIVE_DBUTILS.fs.ls(path)
class GuardDbutils:
    fs=FS()


def persist():
    NATIVE_DBUTILS.fs.put(BASE+f'/job_reports/{JOB_RUN_ID}/{STAGE}.json',json.dumps(report,default=str),True)


def versions(tables):
    return {t:int(NATIVE_SPARK.sql(f'DESCRIBE HISTORY {t} LIMIT 1').first().version) for t in tables}


def execute():
    names={'bronze':'01_bronze_ingesta','silver':'02_silver_preparacion','gold':'03_gold_metricas','auditoria':'00_auditoria_modelo'}
    namespace={'spark':GuardSpark(),'dbutils':GuardDbutils(),'display':lambda *_:None,
               '__name__':'__main__','CODE_HASH':CODE_HASH,'JOB_RUN_ID':JOB_RUN_ID}
    started=time.monotonic()
    try:
        if STAGE=='bronze':
            protected=json.loads((ROOT/'protected_tables.json').read_text())
            report['protected_before']=versions(protected)
            raw=[f"workspace.{CFG['schemas']['bronze']}.{n}_raw" for n in ['checks','locations','items','revenue_centers','employees']]
            report['bronze_before']=versions([t for t in raw if NATIVE_SPARK.catalog.tableExists(t)])
        notebook=json.loads((ROOT/'notebooks'/f'{names[STAGE]}.ipynb.json').read_text())
        for i,cell in enumerate(notebook['cells']):
            if cell['cell_type']!='code':continue
            report['current_cell']=i+1;persist()
            exec(compile(''.join(cell['source']),f'{STAGE}:cell{i+1}','exec'),namespace)
        if STAGE=='bronze':report['bronze_after']=namespace['ctx'].require_complete('bronze')
        if STAGE=='gold':report['threshold_snapshot']=record_threshold_use(namespace['ctx'])
        if STAGE=='auditoria':
            report['audit_checks']=[{'name':n,'status':s,'details':d} for n,s,d in namespace['audit']]
            prior=json.loads(NATIVE_DBUTILS.fs.head(BASE+f'/job_reports/{JOB_RUN_ID}/bronze.json',1048576))
            report['protected_after']=versions(prior['protected_before'])
            assert report['protected_after']==prior['protected_before'],'Protected tables changed'
            report['protected_tables_unchanged']=True
        report['status']='PASS'
    except Exception as error:
        report.update({'status':'FAIL','error':str(error),'traceback':traceback.format_exc()})
        raise
    finally:
        report['seconds']=round(time.monotonic()-started,3);persist()
execute()
