"""Validate aggregate evidence and render the local analysis report and figure."""
import argparse,ast,hashlib,json,math
from decimal import Decimal
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
p=argparse.ArgumentParser();p.add_argument('work_dir',type=Path);a=p.parse_args();b=a.work_dir;root=Path(__file__).resolve().parents[1]
r=json.loads((b/'analysis.json').read_text());s=json.loads((b/'sensitivity.json').read_text());profile=json.loads((b/'profile.json').read_text());m=json.loads((b/'manifest.json').read_text())
assert r['status']==s['status']=='PASS'
assert r['input_versions']==s['input_versions']==profile['versions']
for phase,name in [('analysis','cash_card_analysis.py'),('sensitivity','cash_card_sensitivity.py')]:
 expected=m.get(phase+'_sha256') or m.get('source_hashes',{}).get(phase)
 assert expected==hashlib.sha256((root/'src/analysis'/name).read_bytes()).hexdigest(),phase
for phase in ['profile','analysis','sensitivity']:assert json.loads((b/(phase+'_run.json')).read_text())['state']['result_state']=='SUCCESS'
assert r['protected_before']==r['protected_after'] and s['protected_tables_unchanged'] and s['input_versions_unchanged']
assert m['dashboard_before']==json.loads((b/'dashboard_after.json').read_text())
g={x['family']:x for x in r['global']}
assert sum(x['n'] for x in g.values())==2142846 and sum(x['d'] for x in g.values())==268580
for family,row in g.items():
 daily=[x for x in r['daily'] if x['family']==family]
 for key in ['n','d','all_n','positive_n','positive_d','positive_valid_n','positive_discount','positive_gross']:
  assert sum(Decimal(str(x[key])) for x in daily)==Decimal(str(row[key])),(family,key)
 assert 0<=row['d']<=row['n']
def adjusted(cohort='positive',minimum=5,outcome='frequency',scope='total',channel=None):
 return next(x for x in r['adjustment'] if x['level']=='canal_sucursal_fecha' and x['cohort']==cohort and x['minimum']==minimum and x['outcome']==outcome and x['scope']==scope and x['RevenueCenterId']==channel)
f=adjusted();i=adjusted(outcome='intensity');sp=next(x for x in s['adjusted_frequency'] if x['scenario']=='primary')
for key,other in [('cash_standardized_pct','cash_pct'),('card_standardized_pct','card_pct')]:assert math.isclose(float(f[key]),float(sp[other]),abs_tol=1e-9)
for x in r['adjustment']:
 if x['cells']:
  assert x['weight_sum'] is not None and float(x['weight_sum'])>0
  for k in ['cash_standardized_pct','card_standardized_pct']:assert 0<=float(x[k])<=100.01
cash=g['SOLO_EFECTIVO'];card=g['SOLO_TARJETA'];eligible=cash['positive_n']+card['positive_n'];covered=f['cash_tickets']+f['card_tickets'];coverage=100*covered/eligible
checks=['source_and_sensitive_tables_unchanged','dashboard_unchanged','original_ticket_and_discount_counts','daily_rollups_match_global_exactly','standardization_reproduced_by_independent_sensitivity_query','rates_and_weights_valid']
validation={'status':'PASS','checks':checks,'dashboard_unchanged':True,'protected_tables_unchanged':True,'source_versions':r['input_versions'],'outputs':r['tables'],'scope':'original_dataset_isolated_sandbox','source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src/analysis').glob('*.py')},'runs':{phase:json.loads((b/(phase+'_run.json')).read_text())['run_page_url'] for phase in ['profile','analysis','sensitivity']}}
# Explicit aggregates only; never include full dashboard JSON or row-level transaction data.
for name,value in [('cash_card_analysis.json',r),('cash_card_sensitivity.json',s),('cash_card_profile.json',{k:profile[k] for k in ['status','versions','totals','payment_labels','families']}),('cash_card_validation.json',validation)]:
 (root/'evidence'/name).write_text(json.dumps(value,indent=2,ensure_ascii=False))
figdir=root/'docs/figures';figdir.mkdir(exist_ok=True)
colors=['#BD6700','#236B8E'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(12,6));x=np.arange(3);width=.34
frequency=[[100*cash['d']/cash['n'],100*cash['positive_d']/cash['positive_n'],float(f['cash_standardized_pct'])],[100*card['d']/card['n'],100*card['positive_d']/card['positive_n'],float(f['card_standardized_pct'])]]
intensity=[[100*float(cash['all_discount'])/float(cash['all_gross']),100*float(cash['positive_discount'])/float(cash['positive_gross']),float(i['cash_standardized_pct'])],[100*float(card['all_discount'])/float(card['all_gross']),100*float(card['positive_discount'])/float(card['positive_gross']),float(i['card_standardized_pct'])]]
for ax,values,title in zip(axes,[frequency,intensity],['Tickets with discounts','Intensity: discounts / valid gross']):
 for j,(label,color) in enumerate(zip(['Cash','Card'],colors)):
  bars=ax.bar(x+(j-.5)*width,values[j],width,color=color,label=label)
  ax.bar_label(bars,labels=[f'{v:.2f}%' for v in values[j]],padding=5,fontsize=10)
 ax.set_xticks(x,['All\ntickets¹','Positive\nsales','Comparable\npositive sales²']);ax.set_title(title,loc='left',fontsize=12,pad=18);ax.set_ylabel('%');ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.set_ylim(0,max(max(v) for v in values)*1.23)
fig.suptitle('Cash and card: nonpositive accounts change the comparison',x=.065,ha='left',fontsize=15,fontweight='bold',y=.98)
fig.legend(handles=axes[0].containers,labels=['Cash','Card'],loc='upper left',bbox_to_anchor=(.06,.92),ncol=2,frameon=False)
fig.text(.065,.12,'¹ Frequency uses all tickets; intensity uses reconciled tickets with valid denominators.',fontsize=9,color='#444444')
fig.text(.065,.085,f'² Common channel/location/date mix; ≥5 tickets per method. Coverage: {coverage:.1f}% of pure-family positive sales.',fontsize=9,color='#444444')
fig.text(.065,.05,'Cohorts differ across columns. In-Store dominates the adjusted comparison; no causality is established.',fontsize=9,color='#444444')
fig.subplots_adjust(left=.065,right=.98,top=.78,bottom=.26,wspace=.22);fig.savefig(figdir/'efectivo_tarjeta.png',dpi=180,facecolor='white');plt.close(fig)

# Keep the reviewed narrative intact; regenerate a separate numerical appendix.
lines=['# Generated cash and card metrics','',
       'This appendix is generated from validated aggregate evidence. See [interpretation](efectivo_tarjeta_resultados.md).','',
       '| Measure | Cash | Card | Difference |','|---|---:|---:|---:|']
for label,c,t in [('Frequency, all tickets',frequency[0][0],frequency[1][0]),('Frequency, positive sales',frequency[0][1],frequency[1][1]),('Frequency, standardized positive sales',frequency[0][2],frequency[1][2]),('Intensity, positive sales',intensity[0][1],intensity[1][1]),('Intensity, standardized positive sales',intensity[0][2],intensity[1][2])]:
 lines.append(f'| {label} | {c:.2f}% | {t:.2f}% | {c-t:.2f} pp |')
lines += ['', f'Common-support coverage: {coverage:.2f}%.', '', 'These are descriptive associations, not causal effects or confirmed abuse.']
(root/'docs/cash_card_generated_metrics.md').write_text('\n'.join(lines))
print(json.dumps({'status':'PASS','coverage_pct':coverage,'report':'docs/cash_card_generated_metrics.md'}))
