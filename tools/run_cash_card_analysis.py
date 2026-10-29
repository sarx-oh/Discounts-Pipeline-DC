"""Run the three analysis notebooks against the existing original-data sandbox.

Requires a new work directory, or the same directory to resume submissions.
Writes only fresh analysis resources. No production deployment or GitHub access.
"""
import argparse,hashlib,json,subprocess,time,uuid
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--remote-parent',required=True);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--profile',default='applebees');a=p.parse_args()
assert a.remote_parent.startswith('/Users/') and '..' not in a.remote_parent
root=Path(__file__).resolve().parents[1];b=a.work_dir.resolve();b.mkdir(parents=True,exist_ok=True);mf=b/'manifest.json'
sources={phase:root/'src/analysis'/file for phase,file in [('profile','profile_payments.py'),('analysis','cash_card_analysis.py'),('sensitivity','cash_card_sensitivity.py')]}
hashes={phase:hashlib.sha256(path.read_bytes()).hexdigest() for phase,path in sources.items()}
if mf.exists():
 m=json.loads(mf.read_text());assert m['source_hashes']==hashes,'Code changed: use a new work directory'
 assert m['root'].startswith(a.remote_parent.rstrip('/')+'/')
else:
 id=uuid.uuid4().hex[:12];m={'id':id,'root':a.remote_parent.rstrip('/')+'/analysis_cash_card_'+id,'volume_root':'/Volumes/workspace/applebees_test_0eef22876f8b_bronze/raw/analysis_cash_card_'+id,'output_schema':'workspace.applebees_test_0eef22876f8b_analysis_'+id,'source_hashes':hashes,'runs':{},'imported':[]}
def save():mf.write_text(json.dumps(m,indent=2))
def call(args,as_json=True):
 r=subprocess.run(['databricks',*args,'-p',a.profile,*(['-o','json'] if as_json else [])],capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stderr)
 return json.loads(r.stdout) if as_json and r.stdout.strip() else r.stdout
save();print('Local execution directory:',b,flush=True)
if 'dashboard_before' not in m:m['dashboard_before']=call(['lakeview','get','01f1c1ed3060178b8863556752d5aa45']);save()
call(['workspace','mkdirs',m['root']])
for phase,src in sources.items():
 if phase not in m['imported']:
  call(['workspace','import',m['root']+'/'+src.stem,'--format','SOURCE','--language','PYTHON','--file',str(src)]);m['imported'].append(phase);save()
 params={'output_path':m['volume_root']+'/'+phase+'.json'}
 if phase!='profile':params['input_versions']=json.dumps(json.loads((b/'profile.json').read_text())['versions'])
 if phase=='analysis':params['output_schema']=m['output_schema']
 if phase=='sensitivity':params['protected_versions']=json.dumps(json.loads((b/'analysis.json').read_text())['protected_before'])
 if phase not in m['runs']:
  request={'run_name':'Applebees cash card '+phase,'idempotency_token':m['id']+'-'+phase,'tasks':[{'task_key':phase,'timeout_seconds':3600,'max_retries':0,'disable_auto_optimization':True,'notebook_task':{'notebook_path':m['root']+'/'+src.stem,'source':'WORKSPACE','base_parameters':params}}]}
  f=b/(phase+'_request.json');f.write_text(json.dumps(request,indent=2));m['runs'][phase]=call(['jobs','submit','--json','@'+str(f),'--no-wait'])['run_id'];save()
 previous=None
 while True:
  run=call(['jobs','get-run',str(m['runs'][phase])]);(b/(phase+'_run.json')).write_text(json.dumps(run,indent=2));state=run['state']
  if state!=previous:print(phase,state,flush=True);previous=state
  if state['life_cycle_state'] in ['TERMINATED','SKIPPED','INTERNAL_ERROR']:
   if state.get('result_state')!='SUCCESS':
    out=call(['jobs','get-run-output',str(run['tasks'][-1]['run_id'])]);(b/(phase+'_error.json')).write_text(json.dumps(out,indent=2));raise RuntimeError(out.get('error',str(state)))
   break
  time.sleep(15)
 result=call(['fs','cat','dbfs:'+params['output_path']],as_json=False);(b/(phase+'.json')).write_text(result);assert json.loads(result)['status']=='PASS'
after=call(['lakeview','get','01f1c1ed3060178b8863556752d5aa45']);(b/'dashboard_after.json').write_text(json.dumps(after,indent=2));m['dashboard_unchanged']=after==m['dashboard_before'];assert m['dashboard_unchanged'];m['status']='PASS';save();print('Analysis and sensitivity PASS; dashboard unchanged',flush=True)
