"""Reproduce immutable deep-analysis SQL requests; never execute or overwrite them."""
import argparse,json
from pathlib import Path
from prepare_discount_query import render
p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--workdir',type=Path,required=True);p.add_argument('--warehouse',required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1];state=json.loads(a.state.read_text());a.workdir.mkdir(parents=True,exist_ok=True)
pairs={'product_patterns':'deep_product_patterns','recording_audit':'deep_recording_audit','cash_within_employee':'deep_cash_within_employee','tip_denominators':'deep_tip_denominators','source_schema':'deep_source_schema','tip_account_sensitivity':'deep_tip_account_sensitivity','employee_weeks':'deep_employee_weeks','composition_context':'deep_composition_context','tip_exclude_emp50':'deep_tip_exclude_emp50'}
queries={k:(root/'src/analysis'/f'{v}.sql').read_text() for k,v in pairs.items()}
s=(root/'src/analysis/deep_enriched_sample.sql').read_text()
periods={'train_early':"BusinessDate<DATE'2026-06-01'",'train_late':"BusinessDate>=DATE'2026-06-01' AND BusinessDate<DATE'2026-07-01'",'validation':"BusinessDate>=DATE'2026-07-01' AND BusinessDate<DATE'2026-07-26'",'test':"BusinessDate>=DATE'2026-07-26'"}
for name,clause in periods.items():queries['enriched_'+name]=s.replace('{{period_filter}}',clause)
# Preserve the historical request exactly. Its inherited header describes the
# exploration template; the executable residue predicate is explicitly 19.
queries['confirmation_residue19']=queries['enriched_test'].replace('),20)=0','),20)=19')
for name,source in queries.items():
 sql,used=render(source,state);req={'warehouse_id':a.warehouse,'statement':sql,'wait_timeout':'10s','on_wait_timeout':'CONTINUE','disposition':'INLINE','format':'JSON_ARRAY'}
 dest=a.workdir/(name+'_request.json')
 for f,obj in [(dest,req),(dest.with_suffix('.sources.json'),used)]:
  if f.exists():assert json.loads(f.read_text())==obj,f'Mismatch: {f}'
  elif a.verify:raise FileNotFoundError(f)
  else:f.write_text(json.dumps(obj,indent=2))
print('Verified' if a.verify else 'Prepared',len(queries),'immutable requests')
