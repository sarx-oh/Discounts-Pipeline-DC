"""Prepare a fresh review-base deployment locally; no network or SQL execution."""
import argparse,hashlib,json,re
from pathlib import Path
from uuid import uuid4
from prepare_discount_query import render

p=argparse.ArgumentParser();p.add_argument('--state',required=True,type=Path)
p.add_argument('--protected-tables',required=True,type=Path)
p.add_argument('--remote-parent',required=True);p.add_argument('--workdir',required=True,type=Path)
a=p.parse_args();root=Path(__file__).resolve().parents[1]
if not a.remote_parent.startswith('/Users/') or '/Applebees_tests' not in a.remote_parent or '..' in a.remote_parent:raise ValueError('Sandbox workspace parent required')
if (a.workdir/'base_manifest.json').exists():raise ValueError('Existing manifest: collect existing run or choose a fresh directory')
_,sources=render('SELECT * FROM {{ticket_metrics}} JOIN {{discounts}} USING(CheckId,LocationId,BusinessDate) JOIN {{employee_ticket_activity}} USING(CheckId,LocationId,BusinessDate)',json.loads(a.state.read_text()))
if any('applebees_test_0eef22876f8b_' not in t for t in sources):raise ValueError('This notebook targets the validated original-data sandbox')
protected=json.loads(a.protected_tables.read_text())
if len(protected)!=25 or len(set(protected))!=25 or any(not re.fullmatch(r'workspace\.applebees_(bronze|silver|gold)\.[a-z_]+',t) for t in protected):raise ValueError('Expected original 25-table protection list')
tag=uuid4().hex[:12];remote=a.remote_parent.rstrip('/')+'/discount_review_'+tag
cfg={'output_schema':f'workspace.applebees_test_{tag}_discount_review',
     'output_path':f'/Volumes/workspace/applebees_test_0eef22876f8b_bronze/raw/discount_review_{tag}/report.json',
     'sources':sources,'protected_tables':protected}
src=root/'src/analysis/discount_review_base.py'
manifest={'id':tag,'root':remote,'config':cfg,'source_hash':hashlib.sha256(src.read_bytes()).hexdigest()}
request={'run_name':'Applebees discount review base '+tag,'idempotency_token':'review-base-'+tag,
 'tasks':[{'task_key':'review_base','timeout_seconds':3600,'max_retries':0,'disable_auto_optimization':True,
 'notebook_task':{'notebook_path':remote+'/discount_review_base','source':'WORKSPACE','base_parameters':{'config':json.dumps(cfg)}}}]}
a.workdir.mkdir(parents=True,exist_ok=True)
(a.workdir/'base_manifest.json').write_text(json.dumps(manifest,indent=2))
(a.workdir/'base_request.json').write_text(json.dumps(request,indent=2))
print(a.workdir)
