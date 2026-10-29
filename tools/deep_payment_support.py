"""Exploratory within-employee payment support and model-standardized contrasts.

Existing 5% sample only. Counterfactual feature substitutions are descriptive model
contrasts, not causal interventions. No private employee keys are exported.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from compare_discount_models import prepare
from deep_temporal_models import logistic,block_interval
from deep_model_diagnostics import crossed_interval


def main():
    p=argparse.ArgumentParser();p.add_argument('inputs',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    df=pd.concat([prepare(json.loads((a.inputs/f'discount_model_{s}_data.json').read_text())['rows']) for s in ['train','validation','test']],ignore_index=True)
    sources=[json.loads((a.inputs/f'discount_model_{s}_data.json').read_text())['sources'] for s in ['train','validation','test']]
    assert all(v==sources[0] for v in sources) and df.ticket_key.is_unique
    # Empty strings arise from concat of missing payment employee; do not treat them as an employee.
    invalid={hashlib.sha256(b'applebees-review-v1:').hexdigest(),'', 'UNKNOWN'}
    df['employee_key']=df.employee_key.fillna('UNKNOWN').astype(str)
    df['week']=pd.to_datetime(df.BusinessDate).dt.to_period('W-SUN').astype(str)
    pure=df[df.payment_family.isin(['SOLO_EFECTIVO','SOLO_TARJETA']) & ~df.employee_key.isin(invalid)].copy()
    report={'status':'PASS','scope':'Previously examined deterministic 5% sample; exploratory, not full-population or causal evidence',
            'sources':sources[0], 'input_sha256':{s:hashlib.sha256((a.inputs/f'discount_model_{s}_data.json').read_bytes()).hexdigest() for s in ['train','validation','test']}, 'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'sample_n':len(df),'pure_attributed_n':len(pure),'invalid_employee_n':int(df.employee_key.isin(invalid).sum()),'stratified':[],'model_contrasts':[]}
    for dims in [['LocationId','channel_name','week'],['LocationId','employee_key','channel_name','week']]:
        cells=pure.groupby(dims+['payment_family']).has_discount.agg(['size','sum']).unstack('payment_family').fillna(0)
        for minimum in [1,2,5]:
            nc=cells[('size','SOLO_EFECTIVO')];nk=cells[('size','SOLO_TARJETA')];support=(nc>=minimum)&(nk>=minimum)
            sub=cells.loc[support];w=(nc+nk)[support]
            rc=sub[('sum','SOLO_EFECTIVO')]/nc[support];rk=sub[('sum','SOLO_TARJETA')]/nk[support]
            report['stratified'].append({'dimensions':dims,'minimum_per_method':minimum,'supported_cells':int(support.sum()),
                'supported_tickets':int(w.sum()),'coverage':float(w.sum()/len(pure)),
                'cash_rate':float(np.average(rc,weights=w)),'card_rate':float(np.average(rk,weights=w)),
                'difference_pp':float(100*np.average(rc-rk,weights=w))})
    for end,stop in [('2026-05-31','2026-06-30'),('2026-06-30','2026-07-25'),('2026-07-25','2026-08-20')]:
        tr=df[df.BusinessDate<=end].copy();te=pure[(pure.BusinessDate>end)&(pure.BusinessDate<=stop)].copy()
        # Require both instruments observed in training for the same employee/location/channel.
        dims=['employee_key','LocationId','channel_name'];trainpure=tr[tr.payment_family.isin(['SOLO_EFECTIVO','SOLO_TARJETA']) & ~tr.employee_key.isin(invalid)]
        support=trainpure.groupby(dims).payment_family.nunique();keys=support[support==2].reset_index()[dims]
        test=te.merge(keys,on=dims,how='inner').reset_index(drop=True)
        fold={'train_end':end,'evaluation_end':stop,'eligible_pure_attributed':len(te),'supported_evaluation':len(test),
            'support_coverage':len(test)/len(te),'models':{}}
        for employee in [False,True]:
            m=logistic(employee=employee).fit(tr,tr.has_discount)
            cash=test.copy();card=test.copy();cash['payment_family']='SOLO_EFECTIVO';card['payment_family']='SOLO_TARJETA'
            pc=m.predict_proba(cash)[:,1];pk=m.predict_proba(card)[:,1]
            result={'cash_standardized_rate':float(pc.mean()),'card_standardized_rate':float(pk.mean()),
                    'difference_pp':crossed_interval(100*(pc-pk),test)}
            names=m[0].get_feature_names_out();coef=dict(zip(names,m[-1].coef_[0]));
            result['cash_vs_card_conditional_odds_ratio']=float(np.exp(coef['cat__payment_family_SOLO_EFECTIVO']-coef['cat__payment_family_SOLO_TARJETA']))
            result['uncertainty_limit']='Interval resamples evaluation composition only; model coefficients fixed. It omits estimation uncertainty and is not an inferential effect interval.'
            fold['models']['with_employee' if employee else 'without_employee']=result
        report['model_contrasts'].append(fold)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
