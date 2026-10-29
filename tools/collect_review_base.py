"""Resume observation of an existing base run; never resubmits or modifies it."""
import argparse,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);p.add_argument('--profile',default='applebees');a=p.parse_args()
b=a.workdir;m=json.loads((b/'base_manifest.json').read_text());run_id=json.loads((b/'base_submission.json').read_text())['run_id']
def call(args):
 r=subprocess.run(['databricks',*args,'-p',a.profile,'-o','json'],capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stderr)
 return json.loads(r.stdout)
previous=None
while True:
 run=call(['jobs','get-run',str(run_id)]);(b/'base_run.json').write_text(json.dumps(run,indent=2))
 state=run['state']
 if state!=previous:print(state,flush=True);previous=state
 if state['life_cycle_state'] in ['TERMINATED','SKIPPED','INTERNAL_ERROR']:break
 time.sleep(10)
output=call(['jobs','get-run-output',str(run['tasks'][0]['run_id'])]);(b/'base_output.json').write_text(json.dumps(output,indent=2))
if state.get('result_state')!='SUCCESS':raise RuntimeError(output.get('error',state))
report=json.loads(output['notebook_output']['result'])
assert report['status']=='PASS' and report['schema']==m['config']['output_schema']
assert report['sources']==m['config']['sources'] and report['source_after']==report['sources']
assert report['protected_before']==report['protected_after']
after=call(['lakeview','get','01f1c1ed3060178b8863556752d5aa45'])
(b/'base_dashboard_after.json').write_text(json.dumps(after,indent=2))
assert after==json.loads((b/'base_dashboard_before.json').read_text())
report.update({'dashboard_unchanged':True,'run_id':run_id,'source_hash':m['source_hash']})
(b/'base_validation.json').write_text(json.dumps(report,indent=2))
print('PASS',report['tables'],flush=True)
