"""Evaluate locked models on residue 19; no tuning or model selection.

These records appeared in prior full-population aggregates, so this is partially
reserved record-level replication, not external or pristine temporal validation.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from deep_enriched_models import load,model
from deep_temporal_models import logistic,tree,losses
from deep_model_diagnostics import crossed_interval
from compare_discount_models import prepare,class_metrics,ratio_metrics
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args()
df,sources=load(a.workdir);tr=df[df.BusinessDate<='2026-07-25'].copy()
raw=json.loads((a.workdir/'confirmation_residue19_data.json').read_text());assert raw['sources']==sources
te=prepare(raw['rows']);assert te.ticket_key.is_unique and not set(te.ticket_key)&set(df.ticket_key)
assert te.BusinessDate.min()>'2026-07-25'
for c in ['final_account','net_sales','gratuity_raw','missing_tip_rows','positive_tip_rows','category_count','dominant_category_share','void_count','emp50_present','discount_types']:te[c]=pd.to_numeric(te[c],errors='coerce')
valid=(te.missing_tip_rows==0)&(te.positive_tip_rows==0)&(te.gratuity_raw<=0)
te['tip_observed']=valid.astype(float);te['tip_amount']=(-te.gratuity_raw).where(valid);te['log_tip']=np.log1p(te.tip_amount);te['tip_zero']=(te.tip_amount==0).astype(float)
for c in ['employee_key','dominant_category','payment_bits']:te[c]=te[c].fillna('UNKNOWN').astype(str)
y=te.has_discount.to_numpy();report={'status':'RUNNING','train_n':len(tr),'replication_n':len(te),'source_statement_id':raw['statement_id'],'sources':sources,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'partition':'hash residue 19, July 26-August 20; no shared sample keys','limitation':'Previously included in full-population summaries; partially reserved replication only','models':{}};preds={}
models={'context':logistic(False),'payment':logistic(),'product':model(enriched=True),'product_employee':model(enriched=True,employee=True),'retrospective_tip':model(enriched=True,employee=True,tips=True),'boosted_payment':tree()}
for name,m in models.items():
 m.fit(tr,tr.has_discount);pred=m.predict_proba(te)[:,1];preds[name]=pred;report['models'][name]=class_metrics(y,pred);print(name,report['models'][name]['log_loss'],flush=True)
report['paired']={}
for better,ref in [('payment','context'),('product','payment'),('retrospective_tip','product_employee'),('boosted_payment','payment')]:report['paired'][better+'_vs_'+ref]=crossed_interval(losses(y,preds[ref])-losses(y,preds[better]),te)
pt=tr[(tr.has_discount==1)&(tr.discount_ratio>0)];z=pt.discount_ratio.clip(0,1).to_numpy();m=logistic();m.fit(pd.concat([pt,pt],ignore_index=True),np.r_[np.ones(len(pt)),np.zeros(len(pt))],logisticregression__sample_weight=np.r_[z,1-z]);pred=m.predict_proba(te)[:,1];mask=(y==1)&(te.discount_ratio>0);target=te.discount_ratio.to_numpy()[mask]
report['severity']={'mean_baseline':ratio_metrics(target,np.full(mask.sum(),z.mean())),'fractional':ratio_metrics(target,pred[mask]),'squared_error_gain':crossed_interval((target-z.mean())**2-(target-pred[mask])**2,te.loc[mask].reset_index(drop=True))}
report['status']='PASS';(a.workdir/'confirmation_results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
