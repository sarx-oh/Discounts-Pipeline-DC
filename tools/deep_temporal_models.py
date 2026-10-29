"""Fixed-specification exploratory temporal replication on the existing 5% sample.

No pristine holdout claim: all periods have previously informed project analysis.
Outputs are aggregate metrics; predictions with pseudonymous IDs stay private.
"""
import argparse, hashlib, json, time, platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from scipy.special import expit
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
from compare_discount_models import prepare, class_metrics, ratio_metrics, NUM, CAT


def preprocessing(payment=True, employee=False, tree=False):
    cats=CAT+(['payment_family'] if payment else [])+(['employee_key'] if employee else [])
    enc=OrdinalEncoder(handle_unknown='use_encoded_value',unknown_value=np.nan) if tree else OneHotEncoder(handle_unknown='ignore')
    return ColumnTransformer([('num',make_pipeline(SimpleImputer(strategy='median'),StandardScaler()),NUM),('cat',enc,cats)])


def logistic(payment=True,employee=False):
    return make_pipeline(preprocessing(payment,employee),LogisticRegression(C=.1,max_iter=1500))


def tree(regression=False):
    cls=HistGradientBoostingRegressor if regression else HistGradientBoostingClassifier
    # Mark encoded categories explicitly; numerical category codes are not ordered.
    return make_pipeline(preprocessing(tree=True),cls(max_iter=150,max_leaf_nodes=15,
        min_samples_leaf=50,l2_regularization=10,learning_rate=.08,
        categorical_features=[False]*len(NUM)+[True]*(len(CAT)+1),early_stopping=False,random_state=721))


def block_interval(values, groups, seed=721):
    z=pd.DataFrame({'v':values,'g':np.asarray(groups)}).groupby('g').agg(s=('v','sum'),n=('v','size'))
    rng=np.random.default_rng(seed); draws=rng.integers(0,len(z),(1500,len(z)))
    means=z.s.to_numpy()[draws].sum(axis=1)/z.n.to_numpy()[draws].sum(axis=1)
    return {'mean':float(np.mean(values)),'interval95':np.quantile(means,[.025,.975]).tolist(),'clusters':len(z)}


def losses(y,p):
    p=np.clip(p,1e-8,1-1e-8);return -(y*np.log(p)+(1-y)*np.log1p(-p))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('inputs',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);start=time.monotonic();frames=[];hashes={};sources=None
    for split in ['train','validation','test']:
        f=a.inputs/f'discount_model_{split}_data.json';raw=json.loads(f.read_text());hashes[split]=hashlib.sha256(f.read_bytes()).hexdigest()
        if sources is None:sources=raw['sources']
        assert raw['sources']==sources
        frames.append(prepare(raw['rows']))
    df=pd.concat(frames,ignore_index=True);assert df.ticket_key.is_unique
    df['employee_key']=df.employee_key.fillna('UNKNOWN').astype(str)
    assert df.discount_ratio.between(0,1.01).all()
    report={'status':'RUNNING','sample_n':len(df),'sources':sources,'input_sha256':hashes,
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'versions':{'python':platform.python_version(),'sklearn':sklearn.__version__},
            'interpretation':'Exploratory temporal replication on previously examined sample; retrospective discount prediction, not misuse.',
            'ratio_above_one':int((df.discount_ratio>1).sum()),'folds':[]}
    for end,stop in [('2026-05-31','2026-06-30'),('2026-06-30','2026-07-25'),('2026-07-25','2026-08-20')]:
        tr=df[df.BusinessDate<=end].copy();te=df[(df.BusinessDate>end)&(df.BusinessDate<=stop)].copy().reset_index(drop=True)
        y=te.has_discount.to_numpy();r=te.discount_ratio.clip(0,1).to_numpy();positive=(tr.has_discount==1)&(tr.discount_ratio>0)
        pos_test=(y==1)&(r>0)
        fold={'train_end':end,'evaluation_end':stop,'train_n':len(tr),'evaluation_n':len(te),
              'positive_train_n':int(positive.sum()),'positive_evaluation_n':int(pos_test.sum()),
              'occurrence_positive_but_zero_ratio':int(((y==1)&(r==0)).sum()),'classification':{},'severity':{}}
        predictions={};models={'context_logistic':logistic(False),'payment_logistic':logistic(),
                               'employee_logistic':logistic(employee=True),'boosted_context_payment':tree()}
        baseline=np.full(len(te),tr.has_discount.mean());fold['classification']['prevalence']=class_metrics(y,baseline)
        private=te[['ticket_key','BusinessDate','LocationId','employee_key','payment_family','has_discount','discount_ratio']].copy()
        for name,m in models.items():
            m.fit(tr,tr.has_discount);p=m.predict_proba(te)[:,1];predictions[name]=p;private[name]=p
            fold['classification'][name]=class_metrics(y,p)
            if name!='context_logistic':
                gain=losses(y,predictions['context_logistic'])-losses(y,p)
                fold['classification'][name]['loss_gain_over_context']={g:block_interval(gain,te[g]) for g in ['LocationId','BusinessDate']}
            if name=='employee_logistic':fold['classification'][name]['unseen_employee_share']=float((~te.employee_key.isin(tr.employee_key)).mean())
            print(end,name,fold['classification'][name]['log_loss'],flush=True)
        # Fractional Bernoulli likelihood using paired weighted binary observations.
        ptr=tr.loc[positive];z=ptr.discount_ratio.clip(0,1).to_numpy();fractional=logistic()
        expanded=pd.concat([ptr,ptr],ignore_index=True)
        fractional.fit(expanded,np.r_[np.ones(len(ptr)),np.zeros(len(ptr))],logisticregression__sample_weight=np.r_[z,1-z])
        reg=tree(True).fit(ptr,z)
        severity={'conditional_mean':np.full(len(te),z.mean()),'fractional_logistic':fractional.predict_proba(te)[:,1],
                  'boosted_conditional':reg.predict(te).clip(0,1)}
        for name,s in severity.items():
            hurdle=predictions['payment_logistic']*s
            fold['severity'][name]={'conditional':ratio_metrics(r[pos_test],s[pos_test]),'hurdle_all':ratio_metrics(r,hurdle)}
            private[name]=s
            gain=(r[pos_test]-severity['conditional_mean'][pos_test])**2-(r[pos_test]-s[pos_test])**2
            fold['severity'][name]['conditional_squared_error_gain']={g:block_interval(gain,te.loc[pos_test,g]) for g in ['LocationId','BusinessDate']}
        # Joint permutation preserves dependence inside each feature group, but not with other groups.
        groups={'payment':['payment_family'],'location':['LocationId'],'channel':['channel_name'],
                'basket':['log_gross','log_lines','TrafficCount'],'clock':['open_hour','day_of_week']}
        fold['permutation_logloss_increase']={};rng=np.random.default_rng(721)
        for name in ['payment_logistic','boosted_context_payment']:
            m=models[name];base=losses(y,predictions[name]).mean();out={}
            for g,cols in groups.items():
                vals=[]
                for _ in range(5):
                    x=te.copy();x[cols]=te.iloc[rng.permutation(len(te))][cols].to_numpy();vals.append(float(losses(y,m.predict_proba(x)[:,1]).mean()-base))
                out[g]={'mean':float(np.mean(vals)),'repetition_range':[min(vals),max(vals)]}
            fold['permutation_logloss_increase'][name]=out
        private.to_pickle(a.output/f'private_predictions_{stop}.pkl')
        report['folds'].append(fold);(a.output/'temporal_models.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    report['status']='PASS';report['runtime_seconds']=time.monotonic()-start
    (a.output/'temporal_models.json').write_text(json.dumps(report,indent=2,allow_nan=False))

if __name__=='__main__':main()
