"""Audit saved temporal predictions and quantify paired model stability.

Crossed location/date multiplier bootstrap is a sensitivity analysis, conditional
on fitted models. It does not establish future performance or causal effects.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from deep_temporal_models import losses,block_interval
from compare_discount_models import class_metrics


def crossed_interval(v,df):
    z=pd.DataFrame({'l':df.LocationId.astype(str),'d':df.BusinessDate,'v':v}).groupby(['l','d']).agg(s=('v','sum'),n=('v','size')).reset_index()
    l,ls=pd.factorize(z.l);d,ds=pd.factorize(z.d);rng=np.random.default_rng(722);draws=[]
    for _ in range(1500):
        w=rng.exponential(size=len(ls))[l]*rng.exponential(size=len(ds))[d]
        draws.append(np.dot(w,z.s)/np.dot(w,z.n))
    return {'point':float(np.mean(v)),'interval95':np.quantile(draws,[.025,.975]).tolist(),'locations':len(ls),'dates':len(ds),'method':'independent exponential weights crossed by location and date'}


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();out={'status':'PASS','folds':[]}
    for f in sorted(a.directory.glob('private_predictions_*.pkl')):
        d=pd.read_pickle(f);y=d.has_discount.to_numpy();fold={'evaluation_end':f.stem[-10:],'n':len(d),'paired':{},'calibration':{},'groups':{}}
        assert d.ticket_key.is_unique and not d.isna().any().any()
        for better,reference in [('boosted_context_payment','payment_logistic'),('employee_logistic','payment_logistic'),('payment_logistic','context_logistic')]:
            v=losses(y,d[reference].to_numpy())-losses(y,d[better].to_numpy())
            fold['paired'][better+'_vs_'+reference]=crossed_interval(v,d)
        for name in ['payment_logistic','employee_logistic','boosted_context_payment']:
            pred=d[name].to_numpy();assert np.isfinite(pred).all() and ((pred>=0)&(pred<=1)).all()
            b=pd.cut(pred,[0,.05,.1,.2,.4,1],include_lowest=True)
            cal=pd.DataFrame({'band':b.astype(str),'y':y,'p':pred}).groupby('band').agg(n=('y','size'),observed=('y','mean'),predicted=('p','mean'))
            fold['calibration'][name]=cal.reset_index().to_dict('records')
            fold['groups'][name]={}
            for group,dd in d.groupby('payment_family'):
                fold['groups'][name][group]={'n':len(dd),**class_metrics(dd.has_discount,dd[name])}
        r=d.discount_ratio.to_numpy();positive=(y==1)&(r>0)
        fold['severity_paired']={}
        for name in ['fractional_logistic','boosted_conditional']:
            v=(r[positive]-d.conditional_mean.to_numpy()[positive])**2-(r[positive]-d[name].to_numpy()[positive])**2
            fold['severity_paired'][name]=crossed_interval(v,d.loc[positive].reset_index(drop=True))
        out['folds'].append(fold)
    (a.directory/'model_diagnostics.json').write_text(json.dumps(out,indent=2,allow_nan=False))

if __name__=='__main__':main()
