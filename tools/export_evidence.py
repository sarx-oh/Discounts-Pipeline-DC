"""Export test outcomes without dashboard contents, transaction rows or credentials."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);p.add_argument('--output',type=Path,help='Optional new evidence destination; preserves historical snapshots');a=p.parse_args();b=a.bundle
state=json.loads((b/'execution.json').read_text());manifest=json.loads((b/'manifest.json').read_text())
out={'status':state.get('status','IN_PROGRESS'),'job_id':state['job_id'],'sandbox':manifest['prefix'],'code_hash':manifest['code_hash'],'source_hashes':manifest['source_hashes'],'completed_phases':state.get('completed_phases',[]),'dashboard_unchanged':state.get('dashboard_unchanged'),'phases':{}}
for phase,run_id in state['runs'].items():
 run=json.loads((b/(phase+'_run.json')).read_text())
 item={'run_id':run_id,'run_page_url':run.get('run_page_url'),'job_state':run['state'],'tasks':{t['task_key']:t['state'] for t in run.get('tasks',[])},'stages':{},'attempts':[{'task_key':t['task_key'],'run_id':t['run_id'],'attempt_number':t.get('attempt_number',0),'state':t['state']} for t in run.get('tasks',[])]}
 if phase=='failure' and (b/'failure_error.json').exists():item['expected_failure_reason']=json.loads((b/'failure_error.json').read_text()).get('error','').split('\n')[0]
 f=b/('verify_'+phase+'_output.json')
 if f.exists():item['verification']=json.loads(json.loads(f.read_text())['notebook_output']['result'])
 for stage in ['bronze','silver','gold','auditoria']:
  f=b/(phase+'_'+stage+'_report.json')
  if not f.exists():continue
  report=json.loads(f.read_text());item['stages'][stage]={k:report[k] for k in ['status','seconds','json_read_calls','protected_tables_unchanged','threshold_snapshot','bronze_before','bronze_after'] if k in report}
  if 'audit_checks' in report:item['stages'][stage]['audit_checks']=[{k:x[k] for k in ['name','status']} for x in report['audit_checks']]
 out['phases'][phase]=item
root=Path(__file__).resolve().parents[1];dest=a.output or root/'evidence/incremental_job.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2))
print(json.dumps({'path':str(dest),'status':out['status'],'completed':out['completed_phases']}))
