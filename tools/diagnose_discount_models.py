"""Diagnostics of already selected candidates. No retuning on the test period."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.pipeline import make_pipeline
from compare_discount_models import prepare,preprocessor,class_metrics

p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args()
comparison=json.loads((a.workdir/'model_comparison.json').read_text())
data={s:prepare(json.loads((a.workdir/f'discount_model_{s}_data.json').read_text())['rows']) for s in ['train','validation','test']}
tr,va,te=[data[s] for s in ['train','validation','test']]
C=comparison['classification']['logistic_context_with_payment']['chosen_C']
model=make_pipeline(preprocessor(True),LogisticRegression(C=C,max_iter=1500,solver='lbfgs')).fit(tr,tr.has_discount)
pv=model.predict_proba(va)[:,1];pt=model.predict_proba(te)[:,1]
assert np.isclose(class_metrics(te.has_discount,pt)['log_loss'],comparison['classification']['logistic_context_with_payment']['test']['log_loss'])
out={'status':'RUNNING','retuning':False,'calibration':[],'weekly':[],'unknown_employees':{}}
for lo,hi in zip([0,.05,.1,.2,.4],[.05,.1,.2,.4,1.000001]):
 mask=(pt>=lo)&(pt<hi)
 if mask.sum():out['calibration'].append({'lower':lo,'upper':hi,'n':int(mask.sum()),'predicted':float(pt[mask].mean()),'observed':float(te.has_discount[mask].mean())})
temp=te.copy();temp['prediction']=pt;temp['week']=pd.to_datetime(te.BusinessDate).dt.to_period('W').astype(str)
for week,g in temp.groupby('week'):
 out['weekly'].append({'week':week,'n':len(g),**class_metrics(g.has_discount,g.prediction)})
seen=te.employee_key.isin(tr.employee_key)
for label,mask in [('seen',seen),('unseen_or_missing',~seen)]:
 if mask.sum():out['unknown_employees'][label]={'n':int(mask.sum()),**class_metrics(te.has_discount[mask],pt[mask])}
# Paired uncertainty by business date; fixes all selected parameters.
temp['brier_gain']=(te.has_discount-tr.has_discount.mean())**2-(te.has_discount-pt)**2
daily=temp.groupby('BusinessDate').brier_gain.agg(['sum','count'])
rng=np.random.default_rng(42);boot=[]
for _ in range(1000):
 rows=daily.iloc[rng.integers(0,len(daily),size=len(daily))]
 boot.append(float(rows['sum'].sum()/rows['count'].sum()))
out['brier_gain_over_prevalence']={'point':float(temp.brier_gain.mean()),'date_bootstrap_95_interval':np.quantile(boot,[.025,.975]).tolist(),
 'limitation':'26 dates; does not capture all cross-location dependence or new-period uncertainty'}
alpha=comparison['regression']['ridge']['chosen_alpha']
ridge=make_pipeline(preprocessor(True),Ridge(alpha=alpha,solver='lsqr')).fit(tr,tr.discount_ratio)
rv=va.discount_ratio.to_numpy()-ridge.predict(va).clip(0,1)
rt=te.discount_ratio.to_numpy()-ridge.predict(te).clip(0,1)
threshold=float(np.quantile(rv,.99))
out['illustrative_review_capacity']={'selection':'positive ratio residual > validation 99th percentile',
 'validation_threshold':threshold,'test_selected':int((rt>threshold).sum()),'test_total':len(te),
 'selected_discount_amount':float(te.loc[rt>threshold,'discount_amount'].sum()),
 'interpretation':'review volume only, not accuracy, recoverable loss or confirmed misuse'}
out['status']='PASS'
(a.workdir/'model_diagnostics.json').write_text(json.dumps(out,indent=2,allow_nan=False))
print(json.dumps(out,indent=2))
