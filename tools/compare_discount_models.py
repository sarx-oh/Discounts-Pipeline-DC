"""Exploratory temporal benchmarks, not a classifier of abuse or final deployment.

Input: deterministic 5% ticket sample from pinned sandbox versions, split by date.
No trained model or ticket-level data is exported into the delivery package.
"""
import argparse,hashlib,json,platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.metrics import (log_loss,roc_auc_score,average_precision_score,brier_score_loss,
                            mean_absolute_error,mean_squared_error,silhouette_score,adjusted_rand_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler

NUM=['log_gross','log_lines','TrafficCount']
CAT=['LocationId','channel_name','open_hour','day_of_week']

def prepare(rows):
    df=pd.DataFrame(rows)
    for col in ['gross','item_line_count','TrafficCount','has_discount','discount_ratio','discount_amount',
                'mismatched_item_lines','unassessable_item_lines']:
        df[col]=pd.to_numeric(df[col],errors='coerce')
    df['log_gross']=np.log1p(df.gross.clip(lower=0))
    df['log_lines']=np.log1p(df.item_line_count.clip(lower=0))
    for col in CAT+['payment_family']:df[col]=df[col].fillna('UNKNOWN').astype(str)
    return df

def preprocessor(payment=False):
    return ColumnTransformer([
        ('numeric',make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler()),NUM),
        ('category',OneHotEncoder(handle_unknown='ignore'),CAT+(['payment_family'] if payment else []))])

def class_metrics(y,p):
    return {'log_loss':float(log_loss(y,p)),'roc_auc':float(roc_auc_score(y,p)),
            'average_precision':float(average_precision_score(y,p)),
            'brier':float(brier_score_loss(y,p)),'observed_rate':float(np.mean(y)),
            'predicted_rate':float(np.mean(p))}

def ratio_metrics(y,p):
    return {'mae':float(mean_absolute_error(y,p)),'rmse':float(mean_squared_error(y,p)**.5),
            'observed_mean':float(np.mean(y)),'predicted_mean':float(np.mean(p))}

def compare(data):
    tr,va,te=(data[s] for s in ['train','validation','test'])
    assert tr.BusinessDate.max()<va.BusinessDate.min()<=va.BusinessDate.max()<te.BusinessDate.min()
    allkeys=pd.concat([d.ticket_key for d in data.values()]);assert allkeys.is_unique
    for d in data.values():
        assert d.has_discount.isin([0,1]).all() and d.discount_ratio.notna().all()
        assert d.discount_ratio.between(0,1.01).all()
    report={'status':'RUNNING','versions':{'python':platform.python_version(),'sklearn':sklearn.__version__},
            'targets':{'classification':'any positive discount, NOT abuse','regression':'discount / gross on eligible positive accounts'},
            'excluded_predictors':['employee_key','discount_amount','discount_ratio','has_discount','manager','discount type','net sales','gratuity'],
            'sample':{},'classification':{},'regression':{}}
    for split,d in data.items():
        report['sample'][split]={'tickets':len(d),'discounted':int(d.has_discount.sum()),'first_date':d.BusinessDate.min(),
            'last_date':d.BusinessDate.max(),'locations':d.LocationId.nunique(),'employees':d.employee_key.nunique(),
            'unseen_employee_share':float((~d.employee_key.isin(tr.employee_key)).mean()),
            'line_quality_issue_tickets':int(((d.mismatched_item_lines>0)|(d.unassessable_item_lines>0)).sum())}
    ytr,yva,yte=tr.has_discount,va.has_discount,te.has_discount
    report['classification']['baseline']={s:class_metrics(d.has_discount,np.full(len(d),ytr.mean())) for s,d in [('validation',va),('test',te)]}
    for with_payment in [False,True]:
        label='logistic_context'+('_with_payment' if with_payment else '')
        candidates=[];models=[]
        for C in [.1,1.,10.]:
            model=make_pipeline(preprocessor(with_payment),LogisticRegression(C=C,max_iter=1500,solver='lbfgs'))
            model.fit(tr,ytr);pred=model.predict_proba(va)[:,1]
            candidates.append({'C':C,**class_metrics(yva,pred)});models.append(model)
        best=int(np.argmin([r['log_loss'] for r in candidates]));model=models[best]
        pred=model.predict_proba(te)[:,1]
        groups=[]
        for family,idx in te.groupby('payment_family').groups.items():
            positions=te.index.get_indexer(idx);sub=te.loc[idx]
            if len(sub)>=100 and sub.has_discount.nunique()==2:
                groups.append({'family':family,'n':len(sub),**class_metrics(sub.has_discount,pred[positions])})
        report['classification'][label]={'validation_candidates':candidates,'chosen_C':candidates[best]['C'],
            'test':class_metrics(yte,pred),'test_payment_groups':groups,
            'max_solver_iterations':int(model[-1].n_iter_.max()),'features':NUM+CAT+(['payment_family'] if with_payment else [])}
        print(label,report['classification'][label]['test'],flush=True)
    ratio_train=tr.discount_ratio
    report['regression']['mean_baseline']={s:ratio_metrics(d.discount_ratio,np.full(len(d),ratio_train.mean())) for s,d in [('validation',va),('test',te)]}
    report['regression']['zero_baseline']={s:ratio_metrics(d.discount_ratio,np.zeros(len(d))) for s,d in [('validation',va),('test',te)]}
    models=[];candidates=[]
    for alpha in [.1,10.,100.]:
        model=make_pipeline(preprocessor(True),Ridge(alpha=alpha,solver='lsqr'))
        model.fit(tr,ratio_train);pred=model.predict(va).clip(0,1)
        candidates.append({'alpha':alpha,**ratio_metrics(va.discount_ratio,pred)});models.append(model)
    best=int(np.argmin([r['rmse'] for r in candidates]));model=models[best]
    raw=model.predict(te);pred=raw.clip(0,1)
    report['regression']['ridge']={'validation_candidates':candidates,'chosen_alpha':candidates[best]['alpha'],
        'test':ratio_metrics(te.discount_ratio,pred),'test_clipped_fraction':float(((raw<0)|(raw>1)).mean()),
        'test_discounted_only':ratio_metrics(te.loc[te.has_discount==1,'discount_ratio'],pred[te.has_discount.to_numpy()==1])}
    # Context clusters use no discount outcomes. Summaries of outcomes are descriptive.
    def profiles(df):
        x=df.copy();x['cash']=(x.payment_family=='SOLO_EFECTIVO').astype(float)
        x['instore']=(x.channel_name=='In-Store').astype(float)
        x['weekend']=x.day_of_week.isin(['1','7']).astype(float)
        return x.groupby(['employee_key','LocationId']).agg(n=('ticket_key','count'),cash=('cash','mean'),
            instore=('instore','mean'),weekend=('weekend','mean'),log_gross=('log_gross','mean'),
            log_lines=('log_lines','mean'),discount_rate=('has_discount','mean'),ratio=('discount_ratio','mean')).query('n>=20')
    features=['cash','instore','weekend','log_gross','log_lines']
    pt=profiles(tr);pv=profiles(va);pe=profiles(te)
    scale=StandardScaler().fit(pt[features]);xt=scale.transform(pt[features]);xv=scale.transform(pv[features])
    clusters=[];models=[]
    for k in [2,3,4,5]:
        model=KMeans(n_clusters=k,n_init=10,random_state=42).fit(xt)
        labels=model.predict(xv)
        silhouette=float(silhouette_score(xv,labels,sample_size=min(2000,len(xv)),random_state=42)) if len(set(labels))>1 else -1.
        alternative=KMeans(n_clusters=k,n_init=10,random_state=17).fit(xt)
        clusters.append({'k':k,'validation_silhouette':silhouette,
            'train_seed_stability_ari':float(adjusted_rand_score(model.labels_,alternative.labels_))})
        models.append(model)
    best=int(np.argmax([r['validation_silhouette'] for r in clusters]));model=models[best]
    pe=pe.copy();pe['cluster']=model.predict(scale.transform(pe[features]))
    records=[]
    for cluster,g in pe.groupby('cluster'):
        records.append({'cluster':int(cluster),'profiles':len(g),'sample_tickets':int(g.n.sum()),
            **{f:float(np.average(g[f],weights=g.n)) for f in features+['discount_rate','ratio']}})
    report['clustering']={'unit':'employee-location profile with >=20 sampled tickets per period',
        'features':features,'train_profiles':len(pt),'validation_profiles':len(pv),'test_profiles':len(pe),
        'candidates':clusters,'chosen_k':clusters[best]['k'],'test_profiles_summary':records,
        'interpretation':'context segmentation only, not good/bad labels; 5% sample limits small employees'}
    report['status']='PASS'
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args()
    data={};hashes={};sources=None
    for split in ['train','validation','test']:
        f=a.workdir/f'discount_model_{split}_data.json';hashes[split]=hashlib.sha256(f.read_bytes()).hexdigest()
        raw=json.loads(f.read_text())
        if sources is None:sources=raw['sources']
        assert raw['sources']==sources,'All periods must use identical pinned sources'
        data[split]=prepare(raw['rows'])
        assert set(data[split].temporal_split)=={split}
    report=compare(data);report['sample_hashes']=hashes;report['sources']=sources
    (a.workdir/'model_comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print('Saved model_comparison.json',flush=True)
