"""Prepare the exact analysis requests including partitioned sample extraction."""
import argparse,json
from pathlib import Path
from prepare_discount_query import render
p=argparse.ArgumentParser();p.add_argument('--state',required=True,type=Path)
p.add_argument('--workdir',required=True,type=Path);p.add_argument('--warehouse',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];state=json.loads(a.state.read_text());a.workdir.mkdir(parents=True,exist_ok=True)
templates={'discount_roles':'roles','discount_combinations':'discount_combinations','discount_weekly':'discount_weekly',
 'discount_employee_context':'discount_employee_context_v3','discount_employee_dynamics':'discount_employee_dynamics',
 'discount_model_population':'discount_model_population'}
requests=[]
def save(name,sql,sources):
 f=a.workdir/(name+'_request.json')
 if f.exists():raise ValueError('Request already exists: '+str(f))
 f.write_text(json.dumps({'warehouse_id':a.warehouse,'statement':sql,'wait_timeout':'10s','on_wait_timeout':'CONTINUE','disposition':'INLINE','format':'JSON_ARRAY'},indent=2))
 f.with_suffix('.sources.json').write_text(json.dumps(sources,indent=2));requests.append(str(f))
for template,name in templates.items():
 sql,sources=render((root/'src/analysis'/(template+'.sql')).read_text(),state);save(name,sql,sources)
sql,sources=render((root/'src/analysis/discount_model_sample.sql').read_text(),state)
for split,condition in [('train',"BusinessDate<DATE'2026-07-01'"),('validation',"BusinessDate>=DATE'2026-07-01' AND BusinessDate<DATE'2026-07-26'"),('test',"BusinessDate>=DATE'2026-07-26'")]:
 save('discount_model_'+split,sql+'\n AND '+condition,sources)
print(json.dumps(requests,indent=2))
