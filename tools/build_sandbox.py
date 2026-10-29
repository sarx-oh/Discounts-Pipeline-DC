"""Render a fresh isolated deployment from the portable local source tree."""
import argparse,hashlib,json
from pathlib import Path
from uuid import uuid4
p=argparse.ArgumentParser();p.add_argument('--remote-parent',required=True);a=p.parse_args()
assert a.remote_parent.startswith('/Users/') and '..' not in a.remote_parent
root=Path(__file__).resolve().parents[1];id=uuid4().hex[:12]
prefix='applebees_test_'+id;remote=a.remote_parent.rstrip('/')+'/incremental_'+id
b=root/'.deployment'/id;(b/'notebooks').mkdir(parents=True)
def remap(s):
 for layer in ['bronze','silver','gold']:s=s.replace('applebees_'+layer,prefix+'_'+layer)
 return s
hashes={};origins={}
for source in (root/'src').rglob('*.ipynb'):
 name='notebooks/'+source.name+'.json';(b/name).write_text(remap(source.read_text()))
 origins[str(source.relative_to(root))]=hashlib.sha256(source.read_bytes()).hexdigest()
for source in (root/'src/common').glob('*.py'):
 (b/source.name).write_text(remap(source.read_text()))
 origins[str(source.relative_to(root))]=hashlib.sha256(source.read_bytes()).hexdigest()
cfg=json.loads(remap((root/'configs/pipeline.json').read_text()));cfg['base_path']=f'/Volumes/workspace/{prefix}_bronze/raw';cfg['run_original_regression']=False
(b/'pipeline_config.json').write_text(json.dumps(cfg,indent=2))
groups={'bronze':[n+'_raw' for n in ['checks','locations','items','revenue_centers','employees']],
'silver':['checks','dim_locations','dim_items','dim_revenue_centers','dim_employees','items_sold','payments','discounts','taxes','voids','item_quality','ticket_quality','reference_quality'],
'gold':['ticket_metrics','daily_location_channel','discount_type_daily','employee_ticket_activity','employee_activity_daily','review_thresholds','review_cases']}
(b/'protected_tables.json').write_text(json.dumps(['workspace.applebees_'+layer+'.'+n for layer,names in groups.items() for n in names]))
for f in b.rglob('*'):
 if f.is_file():hashes[str(f.relative_to(b))]=hashlib.sha256(f.read_bytes()).hexdigest()
codehash=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
manifest={'id':id,'prefix':prefix,'root':remote,'hashes':hashes,'code_hash':codehash,'source_hashes':origins,'fixture_kind':'synthetic'}
(b/'manifest.json').write_text(json.dumps(manifest,indent=2))
for stage in ['bronze','silver','gold','auditoria']:
 (b/(stage+'.py')).write_text(f'''# Databricks notebook source
from pathlib import Path
RUNTIME_ROOT="/Workspace{remote}"
STAGE="{stage}"
JOB_RUN_ID=dbutils.widgets.get("job_run_id")
assert JOB_RUN_ID.isdigit()
exec(compile(Path(RUNTIME_ROOT+"/runtime.py").read_text(),"runtime.py","exec"))
''')
job=(root/'resources/jobs/incremental_job.json').read_text().replace('__WORKSPACE_ROOT__',remote).replace('__ID__',id)
(b/'job.json').write_text(job)
(b/'fixtures.py').write_bytes((root/'tests/fixtures.py').read_bytes())
control=(root/'tests/fixture_control.py').read_text().replace('__WORKSPACE_ROOT__',remote).replace('__PREFIX__',prefix)
(b/'fixture_control.py').write_text(control)
print(b)
