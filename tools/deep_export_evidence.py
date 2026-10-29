"""Export only aggregate deep-study evidence and verify executed query records."""
import argparse,json,hashlib,re,shutil,platform
import numpy,scipy,sklearn,statsmodels
from pathlib import Path
import pandas as pd
from deep_enriched_models import load
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'evidence/discount_deep_20261027';out.mkdir(exist_ok=True)
queries=[]
for req in sorted(a.workdir.glob('*_request.json')):
 obj=json.loads(req.read_text());sql=obj['statement'];assert not re.search(r'\b(CREATE|INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|TRUNCATE|VACUUM)\b',sql,re.I)
 stem=req.stem.removesuffix('_request');res=json.loads((a.workdir/(stem+'_response.json')).read_text());data=json.loads((a.workdir/(stem+'_data.json')).read_text())
 assert res['status']['state']=='SUCCEEDED' and not res['manifest'].get('truncated')
 assert res['manifest']['total_row_count']==len(data['rows'])
 queries.append({'query':stem,'statement_id':res['statement_id'],'returned_rows':len(data['rows']),'request_sha256':hashlib.sha256(req.read_bytes()).hexdigest(),'result_sha256':hashlib.sha256((a.workdir/(stem+'_data.json')).read_bytes()).hexdigest(),'warehouse_id':obj['warehouse_id'],'read_only':True})
for name in ['full_population_results','enriched_models','confirmation_results','employee_persistence','interaction_results']:
 d=json.loads((a.workdir/(name+'.json')).read_text());assert d['status']=='PASS';shutil.copy2(a.workdir/(name+'.json'),out/(name+'.json'))
shutil.copy2(a.workdir/'product_patterns_data.json',out/'product_patterns.json')
r=json.loads((a.workdir/'composition_context_data.json').read_text());r['rows']=[x for x in r['rows'] if x['section']!='private_policy_examples'];(out/'composition_context.json').write_text(json.dumps(r,indent=2))
sensitivity=json.loads((a.workdir/'tip_exclude_emp50_data.json').read_text());g=pd.DataFrame(json.loads(next(r['payload'] for r in sensitivity['rows'] if r['section']=='within_employee_contrasts')));s=[]
for k,x in g.groupby('minimum_account'):
 n=x.comparable_tickets.sum();s.append({'minimum_account':int(k),'matched_n':int(n),'coverage':float(n/x.eligible_tickets.sum()),**{c:float(x[c].sum()/n) for c in x if c.startswith('weighted')}})
(out/'tip_emp50_sensitivity.json').write_text(json.dumps({'source_statement_id':sensitivity['statement_id'],'results':s},indent=2))
df,src=load(a.workdir);pos=df[df.has_discount==1].copy();pos['rounded_pct']=(pos.discount_ratio*100).round(1)
ratios=[]
for pct,g in pos.groupby('rounded_pct'):
 if len(g)<100:continue
 ratios.append({'rounded_pct':float(pct),'sample_tickets':len(g),'emp50_share':float(g.emp50_present.mean()),'most_common_dominant_category':g.dominant_category.mode().iloc[0]})
(out/'percentage_patterns.json').write_text(json.dumps({'sample_positive_tickets':len(pos),'interpretation':'Rounded percentages in existing 5% sample; expected promotions and product mix can produce repetition. Not anomaly labels.','patterns':ratios},indent=2))
manifest={'versions':{'python':platform.python_version(),'numpy':numpy.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,'statsmodels':statsmodels.__version__},'status':'PASS','query_records':queries,'remote_mutations_executed':0,'scope':'Read-only SELECT/CTE queries against pinned sandbox sources; no notebook, table, Job or dashboard write. This does not audit changes by other actors.','sample_reconciliation':'Enriched sample keys and all targets match prior 103495 rows','private_exports_excluded':['ticket-level samples','employee weekly keys','manager keys','case keys and event details'],'source_code_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(root.glob('tools/deep_*.py'))}}
(out/'execution_manifest.json').write_text(json.dumps(manifest,indent=2));print('Verified',len(queries),'executed queries; aggregate exports only')
