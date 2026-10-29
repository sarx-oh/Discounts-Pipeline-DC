# Databricks notebook source
"""Setup/mutation/verification restricted to generated synthetic test namespaces."""
import hashlib,json,sys
from pathlib import Path
from pyspark.sql import functions as F
ROOT='/Workspace__WORKSPACE_ROOT__';PREFIX='__PREFIX__'
assert PREFIX.startswith('applebees_test_')
sys.path.insert(0,ROOT)
from fixtures import initial,changed,dimensions
BASE=f'/Volumes/workspace/{PREFIX}_bronze/raw'
action=dbutils.widgets.get('action');phase=dbutils.widgets.get('phase');job_run_id=dbutils.widgets.get('job_run_id')
def table(layer,name):return f'workspace.{PREFIX}_{layer}.{name}'
def put(relative,obj):
 assert not relative.startswith('/') and '..' not in relative.split('/')
 dbutils.fs.mkdirs((BASE+'/'+relative).rsplit('/',1)[0]);dbutils.fs.put(BASE+'/'+relative,json.dumps(obj,default=str),True)
def get(relative):return json.loads(dbutils.fs.head(BASE+'/'+relative,1048576))
def version(t):return int(spark.sql(f'DESCRIBE HISTORY {t} LIMIT 1').first().version)
def digest(df):return hashlib.sha256(json.dumps([r.asDict(recursive=True) for r in df.orderBy('Id').collect()],default=str,sort_keys=True).encode()).hexdigest()
day1='facts/checks/brand=rmh/dt=2099-01-01/checks.json';day2='facts/checks/brand=rmh/dt=2099-01-02/checks.json'
report={'action':action,'phase':phase,'checks':[]}
def check(name,value):
 assert value,name
 report['checks'].append(name)
if action=='setup':
 for layer in ['bronze','silver','gold']:spark.sql(f'CREATE SCHEMA workspace.{PREFIX}_{layer}')
 spark.sql(f'CREATE VOLUME workspace.{PREFIX}_bronze.raw')
 for path,rows in dimensions().items():put('dimensions/'+path,rows)
 put(day1,initial())
elif action in ['changed','failure','recovery']:
 rows,new=changed()
 if action=='failure':rows=rows+[rows[0]]
 put(day1,rows)
 if action=='changed':put(day2,new)
elif action=='verify':
 raw=spark.table(table('bronze','checks_raw'));metrics=spark.table(table('gold','ticket_metrics'))
 if phase=='failure':
  previous=get('control/stable_outputs.json')
  check('failure_keeps_all_data_versions',all(version(t)==v for t,v in previous.items()))
  state=spark.table(table('bronze','pipeline_state')).filter("layer='bronze'").first()
  check('bronze_incomplete_after_rejected_batch',state.status=='RUNNING')
 else:
  expected=40 if phase in ['initial','repeat'] else 41
  check('unique_tickets',raw.count()==expected and raw.select('Id','LocationId','BusinessDate').distinct().count()==expected and metrics.count()==expected)
  gold_report=get(f'job_reports/{job_run_id}/gold.json')
  snapshot=gold_report['threshold_snapshot'];report['snapshot']=snapshot
  check('snapshot_registered',spark.catalog.tableExists(table('gold','threshold_run_history')))
  if phase=='initial':
   put('control/initial.json',{'raw_digest':digest(raw),'snapshot_key':snapshot['key'],'raw_version':version(table('bronze','checks_raw'))})
   check('initial_snapshot_created',not snapshot['reused'])
  elif phase=='repeat':
   before=get('control/initial.json');br=get(f'job_reports/{job_run_id}/bronze.json')
   check('repeat_no_json_read',br['json_read_calls']==0)
   check('repeat_no_raw_write',br['bronze_before']==br['bronze_after'])
   check('repeat_payload_and_timestamps_identical',digest(raw)==before['raw_digest'])
   check('repeat_same_snapshot',snapshot['reused'] and snapshot['key']==before['snapshot_key'])
  else:
   check('new_snapshot_for_changed_input',snapshot['key']!=get('control/initial.json')['snapshot_key'])
   check('omitted_ticket_retained',metrics.filter('CheckId=9002').count()==1)
   check('removed_children_not_retained',spark.table(table('silver','items_sold')).filter('CheckId=9001').count()==1 and spark.table(table('silver','discounts')).filter('CheckId=9001').count()==0 and spark.table(table('silver','voids')).filter('CheckId=9001').count()==0)
   check('corrected_channel',metrics.filter('CheckId=9001 AND RevenueCenterId=9002').count()==1)
   check('incomplete_retained',spark.table(table('silver','ticket_quality')).filter('CheckId=9999 AND missing_items AND missing_payments').count()==1)
  daily=spark.table(table('gold','daily_location_channel'))
  totals=daily.agg(F.sum('net_sales_reconciled'),F.sum('discounts_reconciled')).first()
  check('reconciled_totals',float(totals[0])==(488. if phase in ['initial','repeat'] else 490.) and float(totals[1])==(117. if phase in ['initial','repeat'] else 114.))
  states=spark.table(table('bronze','pipeline_state')).collect()
  check('all_layers_complete',len(states)==3 and all(x.status=='COMPLETE' for x in states))
  outputs={t:v for row in states for t,v in json.loads(row.outputs_json).items()}
  put('control/stable_outputs.json',outputs)
else:raise ValueError(action)
report['status']='PASS'
put(f'control/{action}_{phase}.json',report)
dbutils.notebook.exit(json.dumps(report,default=str))
