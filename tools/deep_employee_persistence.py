"""Descriptive shrinkage and temporal persistence of full-data peer deviations.

Sign-test/BY results are sensitivity diagnostics: weekly signs need not be
independent. They do not validate misconduct labels or calibrated alert thresholds.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from statsmodels.stats.multitest import multipletests
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args()
raw=json.loads((a.workdir/'employee_weeks_data.json').read_text());d=pd.DataFrame(raw['rows'])
for c in ['tickets','discounted','expected_discounted','supported_cells','discount_amount','expected_discount_amount']:d[c]=pd.to_numeric(d[c])
assert d[['employee_key','LocationId','week']].duplicated().sum()==0 and d.tickets.sum()==1001265
# Drop first/last partial calendar weeks and the week spanning July 25 selection cutoff.
d=d[(d.week>='2026-05-04')&(d.week<='2026-08-10')].copy();d['excess']=d.discounted-d.expected_discounted
parts={}
for name,mask in [('early',d.week<='2026-07-13'),('later',d.week>='2026-07-27')]:
 g=d[mask].groupby(['employee_key','LocationId']).agg(n=('tickets','sum'),excess=('excess','sum'),weeks=('week','nunique'),positive_weeks=('excess',lambda x:int((x>0).sum())))
 g['difference']=g.excess/g.n
 # Prior centered on peers with fixed equivalent support, explicitly sensitivity choices.
 for strength in [100,500]:g[f'shrunk_{strength}']=g.excess/(g.n+strength)
 parts[name]=g
matched=parts['early'].join(parts['later'],lsuffix='_early',rsuffix='_later',how='inner')
qualified=matched[(matched.weeks_early>=8)&(matched.weeks_later>=2)&(matched.n_early>=500)&(matched.n_later>=100)]
summary={'status':'PASS','source_statement_id':raw['statement_id'],'sources':raw['sources'],'supported_tickets_original':1001265,'eligible_attributed_tickets_original':2062794,'coverage_original':1001265/2062794,'qualified_profiles':len(qualified),'qualification':'at least 8 early weeks/500 tickets and 2 later weeks/100 tickets; complete weeks only; transition week excluded','selection':[],'multiplicity':{}}
for strength in [0,100,500]:
 col='difference_early' if strength==0 else f'shrunk_{strength}_early';chosen=qualified[qualified[col]>.10]
 summary['selection'].append({'prior_equivalent_tickets':strength,'early_above_10pp':len(chosen),'later_above_10pp':int((chosen.difference_later>.10).sum()),'later_positive':int((chosen.difference_later>0).sum()),'mean_later_difference_pp':float(100*chosen.difference_later.mean()) if len(chosen) else None})
early=parts['early'].query('weeks>=8 and n>=500').copy()
early['p']= [binomtest(int(r.positive_weeks),int(r.weeks),.5,alternative='greater').pvalue for r in early.itertuples()]
reject,q,_,_=multipletests(early.p,alpha=.05,method='fdr_by');early['q']=q
summary['multiplicity']={'profiles_tested':len(early),'raw_p_below_05':int((early.p<.05).sum()),'BY_below_05':int(reject.sum()),'diagnostic_only':'Positive weekly excess sign test; independence of weeks unverified. BY addresses cross-profile dependence, not serial dependence inside a profile.'}
summary['rank_correlation_early_later']=float(qualified.difference_early.corr(qualified.difference_later,method='spearman'))
qualified.to_pickle(a.workdir/'private_employee_persistence.pkl');(a.workdir/'employee_persistence.json').write_text(json.dumps(summary,indent=2,allow_nan=False));print(json.dumps(summary,indent=2))
