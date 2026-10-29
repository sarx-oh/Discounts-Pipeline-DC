"""Deploy a fresh synthetic sandbox and exercise the actual four-task Job.

Explicit command: requires Databricks CLI authentication. No GitHub access.
State is saved after every submission so resuming does not launch duplicates.
"""
import argparse,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);p.add_argument('--profile',default='applebees');a=p.parse_args()
b=a.bundle.resolve();m=json.loads((b/'manifest.json').read_text());root=m['root'];prefix=m['prefix']
assert prefix=='applebees_test_'+m['id'] and '/Applebees_tests/incremental_'+m['id']==root[root.index('/Applebees_tests/'):]
sfile=b/'execution.json';state=json.loads(sfile.read_text()) if sfile.exists() else {'runs':{},'controls':{},'events':[]}
def save():sfile.write_text(json.dumps(state,indent=2))
def log(msg):
 print(msg,flush=True);state['events'].append({'time':time.time(),'message':msg});save()
def call(args,json_output=True,required=True):
 flags=['-p',a.profile]+(['-o','json'] if json_output else [])
 r=subprocess.run(['databricks',*args,*flags],capture_output=True,text=True)
 if r.returncode and required:raise RuntimeError(r.stderr)
 return json.loads(r.stdout) if json_output and r.returncode==0 and r.stdout.strip() else r.stdout

def wait(run_id,label):
 previous=None
 while True:
  r=call(['jobs','get-run',str(run_id)]);(b/(label+'_run.json')).write_text(json.dumps(r,indent=2))
  status=(r.get('state',{}).get('life_cycle_state'),[(x['task_key'],x.get('state',{}).get('life_cycle_state'),x.get('state',{}).get('result_state')) for x in r.get('tasks',[])])
  if status!=previous:log(label+': '+str(status));previous=status
  if r.get('state',{}).get('life_cycle_state') in ['TERMINATED','SKIPPED','INTERNAL_ERROR']:
   if r['state'].get('result_state')!='SUCCESS':
    for t in r.get('tasks',[]):
     if t.get('state',{}).get('result_state')=='FAILED':
      o=call(['jobs','get-run-output',str(t['run_id'])]);(b/(label+'_error.json')).write_text(json.dumps(o,indent=2));log(str(o.get('error'))[:3000])
   return r
  time.sleep(15)

def control(action,phase):
 key=action+'_'+phase
 if key in state.get('completed_controls',[]):return
 if key not in state['controls']:
  req={'run_name':'Synthetic fixture '+key,'idempotency_token':m['id']+'-'+key,
       'tasks':[{'task_key':'control','timeout_seconds':1200,'max_retries':0,'notebook_task':{'notebook_path':root+'/fixture_control','source':'WORKSPACE','base_parameters':{'action':action,'phase':phase,'job_run_id':str(state['runs'].get(phase,0))}}}]}
  f=b/(key+'_submit.json');f.write_text(json.dumps(req));r=call(['jobs','submit','--json','@'+str(f),'--no-wait']);state['controls'][key]=r['run_id'];save()
 r=wait(state['controls'][key],key);assert r['state'].get('result_state')=='SUCCESS',key
 out=call(['jobs','get-run-output',str(r['tasks'][0]['run_id'])]);(b/(key+'_output.json')).write_text(json.dumps(out,indent=2))
 report=json.loads(out['notebook_output']['result']);assert report['status']=='PASS'
 state.setdefault('completed_controls',[]).append(key);save()

if not state.get('deployed'):
 if 'dashboard_before' not in state:
  state['dashboard_before']=call(['lakeview','get','01f1c1ed3060178b8863556752d5aa45']);save()
 call(['workspace','mkdirs',root+'/notebooks'])
 imported=state.setdefault('imported',[])
 # Upload every manifest-tracked dependency, including newly added common modules.
 # A handwritten filename list previously omitted review_contract.py.
 raw=[b/relative for relative in m['hashes']]+[b/'manifest.json',b/'fixtures.py']
 import hashlib
 assert all(hashlib.sha256((b/name).read_bytes()).hexdigest()==expected for name,expected in m['hashes'].items()),'Bundle changed since preparation'
 for f in raw:
  dest=f.relative_to(b).as_posix()
  if dest not in imported:call(['workspace','import',root+'/'+dest,'--format','RAW','--file',str(f)]);imported.append(dest);save()
 for stage in ['bronze','silver','gold','auditoria','fixture_control']:
  if stage not in imported:call(['workspace','import',root+'/'+stage,'--format','SOURCE','--language','PYTHON','--file',str(b/(stage+'.py'))]);imported.append(stage);save()
 if 'job_id' not in state:state['job_id']=call(['jobs','create','--json','@'+str(b/'job.json')])['job_id'];save()
 state['deployed']=True;save();log('Job created '+str(state['job_id']))
control('setup','initial')
for phase in ['initial','repeat','changed','failure','recovery']:
 if phase in state.get('completed_phases',[]):continue
 if phase in ['changed','failure','recovery']:control(phase,phase)
 if phase not in state['runs']:
  r=call(['jobs','run-now',str(state['job_id']),'--idempotency-token',m['id']+'-'+phase,'--no-wait']);state['runs'][phase]=r['run_id'];save()
 run=wait(state['runs'][phase],phase)
 if phase=='failure':
  assert run['state'].get('result_state')=='FAILED'
  states={t['task_key']:t['state'] for t in run['tasks']}
  assert states['bronze']['result_state']=='FAILED'
  assert all(states[s].get('result_state')=='UPSTREAM_FAILED' for s in ['silver','gold','auditoria']),states
  error=json.loads((b/'failure_error.json').read_text())
  assert 'Duplicate key:' in error.get('error',''),error.get('error')
 else:assert run['state'].get('result_state')=='SUCCESS',phase
 control('verify',phase)
 for stage in ['bronze','silver','gold','auditoria']:
  if phase=='failure' and stage!='bronze':continue
  text=call(['fs','cat',f'dbfs:/Volumes/workspace/{prefix}_bronze/raw/job_reports/{state["runs"][phase]}/{stage}.json'],json_output=False)
  (b/(phase+'_'+stage+'_report.json')).write_text(text)
 state.setdefault('completed_phases',[]).append(phase);save();log('VERIFIED '+phase)
after=call(['lakeview','get','01f1c1ed3060178b8863556752d5aa45'])
state['dashboard_unchanged']=after==state['dashboard_before'];assert state['dashboard_unchanged']
state['status']='PASS';save();log('ALL FIVE SCENARIOS PASS; dashboard unchanged')
