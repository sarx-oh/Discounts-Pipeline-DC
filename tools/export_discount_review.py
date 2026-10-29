"""Export aggregates only; exclude ticket samples and employee profile identifiers."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];dest=root/'evidence/discount_review';dest.mkdir(parents=True,exist_ok=True)
mapping={
 'discount_combinations':'combinations',
 'discount_weekly':'weekly',
 'discount_employee_context_v3':'employee_context',
 'discount_employee_dynamics':'employee_dynamics',
 'discount_model_population':'model_population'}
excluded={'high_review_candidates','compatible_with_peer_frequency','flagged_profiles','largest_jumps'}
for source,name in mapping.items():
 data=json.loads((a.workdir/(source+'_data.json')).read_text())
 data['rows']=[r for r in data['rows'] if r.get('section') not in excluded]
 (dest/(name+'.json')).write_text(json.dumps(data,indent=2))
roles=json.loads((a.workdir/'roles_response.json').read_text())
assert roles['status']['state']=='SUCCEEDED'
(dest/'roles.json').write_text(json.dumps({'statement_id':roles['statement_id'],
 'sources':json.loads((a.workdir/'roles_request.sources.json').read_text()),
 'sections':{r[0]:json.loads(r[1]) for r in roles['result']['data_array']}},indent=2))
for name in ['model_comparison','model_diagnostics']:
 data=json.loads((a.workdir/(name+'.json')).read_text());assert data['status']=='PASS'
 (dest/(name+'.json')).write_text(json.dumps(data,indent=2))
if (a.workdir/'base_validation.json').exists():
 data=json.loads((a.workdir/'base_validation.json').read_text());assert data['status']=='PASS'
 (dest/'base_validation.json').write_text(json.dumps(data,indent=2))
print(dest)
