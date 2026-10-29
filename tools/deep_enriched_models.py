"""Fixed enriched retrospective benchmarks; tips are post-transaction observations.

No model is fit on the reserved residue 19 partition. Discount identifiers,
manager identifiers, discount amounts and final accounts are never predictors.
"""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from compare_discount_models import prepare,class_metrics,ratio_metrics,NUM,CAT
from deep_model_diagnostics import crossed_interval
from deep_temporal_models import losses


def load(directory):
    frames=[];sources=None
    for period in ['train_early','train_late','validation','test']:
        obj=json.loads((directory/f'enriched_{period}_data.json').read_text())
        if sources is None:sources=obj['sources']
        assert sources==obj['sources']
        frames.append(prepare(obj['rows']))
    d=pd.concat(frames,ignore_index=True);assert d.ticket_key.is_unique and len(d)==103495
    for c in ['final_account','net_sales','gratuity_raw','missing_tip_rows','positive_tip_rows','category_count','dominant_category_share','void_count','emp50_present','discount_types']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    valid=(d.missing_tip_rows==0)&(d.positive_tip_rows==0)&(d.gratuity_raw<=0)
    d['tip_observed']=valid.astype(float);d['tip_amount']=(-d.gratuity_raw).where(valid)
    d['log_tip']=np.log1p(d.tip_amount);d['tip_zero']=(d.tip_amount==0).astype(float)
    for c in ['employee_key','dominant_category','payment_bits']:d[c]=d[c].fillna('UNKNOWN').astype(str)
    return d,sources


def model(enriched=False,tips=False,employee=False):
    numeric=NUM+(['category_count','dominant_category_share'] if enriched else [])+(['log_tip','tip_zero','tip_observed'] if tips else [])
    cats=CAT+(['payment_bits','dominant_category'] if enriched else ['payment_family'])+(['employee_key'] if employee else [])
    pre=ColumnTransformer([('numeric',make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler()),numeric),('cat',OneHotEncoder(handle_unknown='ignore'),cats)])
    return make_pipeline(pre,LogisticRegression(C=.1,max_iter=1500))


def main():
    p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);p.add_argument('--bootstrap',type=int,default=150);a=p.parse_args();start=time.monotonic()
    df,sources=load(a.workdir)
    # Independently verify enriched target values against the original sample.
    old=pd.concat([pd.DataFrame(json.loads((a.workdir.parent/'discount_solution'/f'discount_model_{s}_data.json').read_text())['rows']) for s in ['train','validation','test']])
    z=df.set_index('ticket_key').sort_index();o=old.set_index('ticket_key').sort_index();assert z.index.equals(o.index)
    for c in ['has_discount','gross','discount_ratio','discount_amount']:assert np.allclose(z[c].astype(float),o[c].astype(float),atol=1e-10)
    report={'status':'RUNNING','n':len(df),'sources':sources,'target_reconciliation':'all 103495 keys and target values match prior sample',
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'folds':[],
            'limitations':'Retrospective association. Recorded gratuity may follow discount. Product category is final basket composition. Previously inspected time windows.'}
    configs={'baseline_payment':{},'product_detailed_payment':{'enriched':True},'product_employee':{'enriched':True,'employee':True},'retrospective_tip':{'enriched':True,'employee':True,'tips':True}}
    for end,stop in [('2026-05-31','2026-06-30'),('2026-06-30','2026-07-25'),('2026-07-25','2026-08-20')]:
        tr=df[df.BusinessDate<=end];te=df[(df.BusinessDate>end)&(df.BusinessDate<=stop)].reset_index(drop=True);y=te.has_discount.to_numpy()
        fold={'train_end':end,'end':stop,'train_n':len(tr),'evaluation_n':len(te),'models':{}};preds={}
        for name,config in configs.items():
            m=model(**config).fit(tr,tr.has_discount);pred=m.predict_proba(te)[:,1];preds[name]=pred
            fold['models'][name]=class_metrics(y,pred)
            ref='baseline_payment' if name in ['product_detailed_payment','product_employee'] else 'product_employee'
            if name!='baseline_payment':fold['models'][name]['gain_vs_'+ref]=crossed_interval(losses(y,preds[ref])-losses(y,pred),te)
            card=te.payment_bits=='010';fold['models'][name]['card_only']=class_metrics(y[card],pred[card])
            print(end,name,fold['models'][name]['log_loss'],flush=True)
        report['folds'].append(fold)
        (a.workdir/'enriched_models.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    # Refit uncertainty for payment contrast, including employee and product categories,
    # but excluding tips: tips could be downstream and mechanically linked to payment.
    tr=df[df.BusinessDate<='2026-07-25'].copy();te=df[(df.BusinessDate>'2026-07-25')&df.payment_bits.isin(['100','010'])].copy()
    counts=tr[tr.payment_bits.isin(['100','010'])].groupby(['employee_key','LocationId','channel_name']).payment_bits.nunique()
    keys=counts[counts==2].reset_index()[['employee_key','LocationId','channel_name']]
    te=te.merge(keys,on=['employee_key','LocationId','channel_name']).reset_index(drop=True)
    fitted=model(enriched=True,employee=True).fit(tr,tr.has_discount);pre=fitted[0];x=pre.transform(tr)
    cash=te.copy();card=te.copy();cash['payment_bits']='100';card['payment_bits']='010'
    xc=pre.transform(cash);xk=pre.transform(card);point=float(100*np.mean(fitted[-1].predict_proba(xc)[:,1]-fitted[-1].predict_proba(xk)[:,1]))
    loc,locs=pd.factorize(tr.LocationId);weeks,week_names=pd.factorize(pd.to_datetime(tr.BusinessDate).dt.to_period('W-SUN'))
    rng=np.random.default_rng(811);draws=[]
    for b in range(a.bootstrap):
        w=rng.exponential(size=len(locs))[loc]*rng.exponential(size=len(week_names))[weeks];w=w/w.mean()
        m=LogisticRegression(C=.1,max_iter=1500).fit(x,tr.has_discount,sample_weight=w)
        draws.append(float(100*np.mean(m.predict_proba(xc)[:,1]-m.predict_proba(xk)[:,1])))
        if (b+1)%25==0:print('Refit bootstrap',b+1,flush=True)
    report['payment_refit_contrast']={'point_pp':point,'interval95_pp':np.quantile(draws,[.025,.975]).tolist(),
        'evaluation_n':len(te),'draws':a.bootstrap,'training_locations':len(locs),'training_weeks':len(week_names),
        'method':'Crossed location/week exponential-weight refits; fixed preprocessing and evaluation population; regularization retained',
        'interpretation':'Associational model contrast; limited training weeks and no causal identification. Not a fixed-coefficient composition interval.'}
    report['status']='PASS';report['runtime_seconds']=time.monotonic()-start
    (a.workdir/'enriched_models.json').write_text(json.dumps(report,indent=2,allow_nan=False))

if __name__=='__main__':main()
