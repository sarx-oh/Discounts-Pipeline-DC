"""Summarize executed full-data queries with matched-population uncertainty."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd


def interval(df,numerator,denominator):
    # Resample observed location and week clusters jointly. Few weeks limit interpretation.
    loc,ls=pd.factorize(df.LocationId);week,ws=pd.factorize(df.week);rng=np.random.default_rng(619)
    num=df[numerator].to_numpy(float);den=df[denominator].to_numpy(float);draws=[]
    for _ in range(2000):
        w=rng.exponential(size=len(ls))[loc]*rng.exponential(size=len(ws))[week]
        draws.append(np.dot(w,num)/np.dot(w,den))
    return {'estimate':float(num.sum()/den.sum()),'interval95':np.quantile(draws,[.025,.975]).tolist(),'locations':len(ls),'weeks':len(ws),'method':'Crossed location/week multiplier weights; fixed observed matched cells'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('workdir',type=Path);a=ap.parse_args();p=a.workdir;report={'status':'PASS','sources':{},'cash':[],'tips':[],'limitations':'Matched support selects populations. Intervals condition on matched cells; few weeks and shared employees limit inference.'}
    def read(name):
        obj=json.loads((p/(name+'_data.json')).read_text());report['sources'][name]={'statement_id':obj['statement_id'],'pinned_sources':obj['sources'],'request_sha256':hashlib.sha256((p/(name+'_request.json')).read_bytes()).hexdigest()};return obj['rows']
    audit={r['section']:json.loads(r['payload']) for r in read('recording_audit')}
    assert audit['join_counts']=={'joined':2142846,'unique_keys':2142846}
    counts=pd.DataFrame(audit['cohorts']);assert counts.tickets.sum()==2142846
    checks=['occurrence_mismatch','discount_sum_mismatch','tickets_null_tip_components','tickets_null_payment_components','tickets_negative_discount','tickets_null_discount','positive_events_nonpositive_net','comparable_partial_tip']
    report['audit']={c:int(counts[c].sum()) for c in checks};report['audit']['tickets']=int(counts.tickets.sum())
    report['audit']['positive_gratuity_sign_tickets']=int(counts.tickets_positive_gratuity_sign.sum());report['audit']['ratio_above_100_tickets']=int(counts.ratio_above_100.sum())
    x=pd.DataFrame(read('cash_within_employee'))
    for c in x:
        if c!='week':x[c]=pd.to_numeric(x[c])
    for k,g in x.groupby('minimum_per_method'):
        g=g.copy();g['rate_diff']=g.weighted_cash_rate-g.weighted_card_rate;g['ratio_diff']=g.weighted_cash_ratio-g.weighted_card_ratio;n=g.comparable_tickets.sum()
        report['cash'].append({'minimum_per_method':int(k),'eligible_n':int(g.eligible_tickets.sum()),'matched_n':int(n),'coverage':float(n/g.eligible_tickets.sum()),'cash_rate':float(g.weighted_cash_rate.sum()/n),'card_rate':float(g.weighted_card_rate.sum()/n),'frequency_difference':interval(g,'rate_diff','comparable_tickets'),'mean_intensity_difference':interval(g,'ratio_diff','comparable_tickets')})
    sections={r['section']:json.loads(r['payload']) for r in read('tip_account_sensitivity')}
    assert sum(r['tickets'] for r in sections['summary'])==2142846
    report['tip_population_summary']=sections['summary'];x=pd.DataFrame(sections['within_employee_contrasts'])
    for k,g in x.groupby('minimum_account'):
        report['tips'].append({'minimum_final_account':int(k),'eligible_n':int(g.eligible_tickets.sum()),'matched_n':int(g.comparable_tickets.sum()),'coverage':float(g.comparable_tickets.sum()/g.eligible_tickets.sum()),'contrasts':{c:interval(g,c,'comparable_tickets') for c in g if c.startswith('weighted')}})
    (p/'full_population_results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:report[k] for k in ['audit','cash','tips']},indent=2))

if __name__=='__main__':main()
