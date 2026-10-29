"""Explicit remote deployment into the fresh sandbox described by the manifest."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);p.add_argument('--profile',default='applebees');a=p.parse_args()
b=a.workdir;m=json.loads((b/'base_manifest.json').read_text());root=Path(__file__).resolve().parents[1]
src=root/'src/analysis/discount_review_base.py'
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_hash'],'Source changed; prepare a new deployment'
assert m['root'].endswith('/discount_review_'+m['id']) and '/Applebees_tests/' in m['root']
assert m['config']['output_schema']=='workspace.applebees_test_'+m['id']+'_discount_review'
if (b/'base_submission.json').exists():raise SystemExit('Already submitted; use collect_review_base.py')
def call(args):
 r=subprocess.run(['databricks',*args,'-p',a.profile,'-o','json'],capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stderr)
 return json.loads(r.stdout) if r.stdout.strip() else {}
if not (b/'base_dashboard_before.json').exists():
 (b/'base_dashboard_before.json').write_text(json.dumps(call(['lakeview','get','01f1c1ed3060178b8863556752d5aa45']),indent=2))
call(['workspace','mkdirs',m['root']])
if not (b/'base_imported.json').exists():
 call(['workspace','import',m['root']+'/discount_review_base','--format','SOURCE','--language','PYTHON','--file',str(src)])
 (b/'base_imported.json').write_text(json.dumps({'source_hash':m['source_hash']}))
request=json.loads((b/'base_request.json').read_text())
assert request['idempotency_token']=='review-base-'+m['id']
task=request['tasks'][0]
assert len(request['tasks'])==1 and task['notebook_task']['notebook_path']==m['root']+'/discount_review_base'
assert json.loads(task['notebook_task']['base_parameters']['config'])==m['config']
result=call(['jobs','submit','--json','@'+str(b/'base_request.json'),'--no-wait'])
(b/'base_submission.json').write_text(json.dumps(result,indent=2));print(result)
