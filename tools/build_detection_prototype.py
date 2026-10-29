"""Build a fresh private offline case-review run from immutable analytical inputs."""
import argparse,hashlib,json,sys,html
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from detection.core import policy_cases,merge_ticket_cases,pilot_sample,stable_id,review_metrics
from deep_enriched_models import load,model
from compare_discount_models import class_metrics,ratio_metrics


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def render_report(run,cases,pilot,summary):
    esc=lambda x:html.escape(str(x))
    sections=[]
    order={'OVERLAPPING_SCOPE':0,'UNKNOWN_SCOPE':1,'DISTINCT_LINES':2}
    chosen={r['case_id']:r for r in pilot['selected']}
    # Show pilot first, then profile investigations and all remaining alerts.
    ordered=sorted(cases,key=lambda c:(c['case_id'] not in chosen,c['unit']!='employee_location',c['case_id']))
    for c in ordered:
        membership=', '.join(chosen.get(c['case_id'],{}).get('arms',[])) or 'Not in pilot'
        details=esc(json.dumps(c,indent=2,ensure_ascii=False))
        sections.append(f'<details id="{esc(c["case_id"])}"><summary>{esc(c["unit"])} | {esc(c["BusinessDate"])} | {esc("; ".join(c["reasons"]))} | {esc(membership)}</summary><pre>{details}</pre></details>')
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Discount review prototype</title><style>body{font:16px system-ui;margin:32px auto;max-width:1100px;background:#f6f8fb;color:#172535}h1{font-size:30px}details{background:white;margin:10px 0;padding:14px;border:1px solid #ccd5df;border-radius:6px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}aside{border-left:4px solid #bc7d22;padding:14px;background:#fff7e7}code{overflow-wrap:anywhere}a{color:#165dac}</style><h1>Discount review prototype</h1><aside>PRIVATE RETROSPECTIVE EVIDENCE — Candidates are not confirmed misuse. Controls are not alerts. Policy mapping and scope remain unconfirmed. No automatic actions.</aside>'''
    doc+=f'<p>Full policy candidates: {summary["full_policy_cases"]:,}. Statistical population: {summary["evaluation_n"]:,} sampled eligible tickets. Profile investigations: {summary["profile_cases"]}. Human reviews: 0 at build time.</p>'
    doc+='<p>Open a case to inspect its exact evidence. Decisions are recorded through the local review CLI, not by editing this report. This is an immutable evidence snapshot; use the CLI for current review status.</p>'
    doc+=f'<p><a href="cases.json">Case data</a> · <a href="pilot.json">Pilot selection</a> · <a href="review_template.json">Decision template</a> · <a href="manifest.json">Provenance</a></p><pre>{esc(json.dumps({"pilot":{k:v for k,v in pilot.items() if k!="selected"},"validation":summary},indent=2))}</pre>'
    doc+=''.join(sections)+'</html>'; (run/'review.html').write_text(doc)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--analysis',type=Path,required=True);ap.add_argument('--policy-events',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--config',type=Path,default=ROOT/'configs/detection_prototype.json');a=ap.parse_args()
    if a.output.exists():raise FileExistsError('Fresh output directory required; never overwrite decisions')
    cfg=json.loads(a.config.read_text());assert not cfg['automatic_actions'] and not cfg['employee_meal_enabled']
    d,sources=load(a.analysis);raw=json.loads(a.policy_events.read_text());assert all(sources[t]==v for t,v in raw['sources'].items())
    original=pd.concat([pd.DataFrame(json.loads((a.analysis.parent/'discount_solution'/f'discount_model_{s}_data.json').read_text())['rows']) for s in ['train','validation','test']]).set_index('ticket_key').sort_index()
    check=d.set_index('ticket_key').sort_index();assert original.index.equals(check.index)
    for c in ['has_discount','discount_ratio','gross','discount_amount']:assert np.allclose(original[c].astype(float),check[c].astype(float),atol=1e-10)
    inputs=[a.policy_events,a.analysis/'employee_weeks_data.json']+[a.analysis/f'enriched_{s}_data.json' for s in ['train_early','train_late','validation','test']]
    code=[Path(__file__),ROOT/'src/detection/core.py',ROOT/'tools/deep_enriched_models.py',ROOT/'tools/compare_discount_models.py',ROOT/'src/common/review_contract.py']
    lineage={'input_sha256':{p.name:digest(p) for p in inputs},'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in code},'config':cfg,'sources':sources}
    snapshot=hashlib.sha256(json.dumps(lineage,sort_keys=True).encode()).hexdigest()
    policy=policy_cases(raw['rows'],cfg,snapshot);assert len(policy)==2135,'Full policy baseline mismatch'
    tr=d[d.BusinessDate<=cfg['train_end']];va=d[(d.BusinessDate>cfg['train_end'])&(d.BusinessDate<=cfg['calibration_end'])];te=d[d.BusinessDate>cfg['calibration_end']].copy().reset_index(drop=True)
    assert tr.BusinessDate.max()<va.BusinessDate.min() and va.BusinessDate.max()<te.BusinessDate.min()
    occurrence=model(enriched=True).fit(tr,tr.has_discount)
    ptr=tr[(tr.has_discount==1)&(tr.discount_ratio>0)];ratio=ptr.discount_ratio.clip(0,1).to_numpy()
    severity=model(enriched=True).fit(pd.concat([ptr,ptr],ignore_index=True),np.r_[np.ones(len(ptr)),np.zeros(len(ptr))],logisticregression__sample_weight=np.r_[ratio,1-ratio])
    vp=severity.predict_proba(va)[:,1];vpositive=(va.has_discount==1)&(va.discount_ratio>0)
    residual=va.discount_ratio.to_numpy()[vpositive]-vp[vpositive];cutoff=float(np.quantile(residual,cfg['severity_residual_quantile']))
    te['expected_occurrence']=occurrence.predict_proba(te)[:,1];te['expected_ratio']=severity.predict_proba(te)[:,1];te['residual']=te.discount_ratio-te.expected_ratio
    te['excess_amount']=te.gross*te.residual
    flagged=te[(te.has_discount==1)&(te.residual>cutoff)]
    stat=[]
    for row in flagged.to_dict('records'):
        stat.append({'case_id':stable_id('ticket',row['ticket_key'],snapshot),'unit':'ticket','ticket_key':row['ticket_key'],'BusinessDate':row['BusinessDate'],'LocationId':row['LocationId'],'evidence_snapshot':snapshot,'detector_version':cfg['version'],'policy_version':cfg['version'],'policy_confirmed':False,'reasons':['HIGH_CONDITIONAL_DISCOUNT'],'status':'UNREVIEWED',
          'model_evidence':{k:float(row[k]) for k in ['gross','discount_amount','discount_ratio','expected_occurrence','expected_ratio','residual','excess_amount']}|{'validation_residual_cutoff':cutoff,'calibration_quantile':cfg['severity_residual_quantile'],'channel':row['channel_name'],'payment_bits':row['payment_bits'],'dominant_product_category':row['dominant_category']},
          'interpretation':'Unusually large conditional discount in the sampled eligible population. Excess amount is not recoverable loss; no fraud probability.'})
    tickets=merge_ticket_cases(policy,stat)
    pilot=pilot_sample(tickets,te.ticket_key,cfg,snapshot)
    # Controls receive evidence records, but no alert reason.
    bykey=te.set_index('ticket_key')
    for selected in pilot['selected']:
        if selected['is_alert']:continue
        r=bykey.loc[selected['ticket_key']]
        tickets.append({'case_id':selected['case_id'],'unit':'ticket','ticket_key':selected['ticket_key'],'BusinessDate':str(r.BusinessDate),'LocationId':str(r.LocationId),'evidence_snapshot':snapshot,'detector_version':cfg['version'],'policy_version':cfg['version'],'policy_confirmed':False,'reasons':['NON_ALERTED_REVIEW_CONTROL'],'status':'UNREVIEWED','observed_discount_amount':float(r.discount_amount),'observed_discount_ratio':float(r.discount_ratio),'interpretation':'Deterministic pseudorandom non-alerted control; NOT an anomaly.'})
    weeks=pd.DataFrame(json.loads((a.analysis/'employee_weeks_data.json').read_text())['rows'])
    for c in ['tickets','discounted','expected_discounted']:weeks[c]=pd.to_numeric(weeks[c])
    assert weeks.tickets.sum()==1001265
    weeks=weeks[(weeks.week>='2026-05-04')&(weeks.week<='2026-08-10')].copy();weeks['excess']=weeks.discounted-weeks.expected_discounted
    group=['employee_key','LocationId'];parts={}
    for name,mask in [('early',weeks.week<='2026-07-13'),('later',weeks.week>='2026-07-27')]:
        parts[name]=weeks[mask].groupby(group).agg(n=('tickets','sum'),excess=('excess','sum'),weeks=('week','nunique'))
    profiles=parts['early'].join(parts['later'],lsuffix='_early',rsuffix='_later',how='inner');profiles['shrunk_gap']=profiles.excess_early/(profiles.n_early+cfg['profile_prior_tickets'])
    qualified=profiles[(profiles.weeks_early>=cfg['profile_min_early_weeks'])&(profiles.n_early>=cfg['profile_min_early_tickets'])&(profiles.weeks_later>=cfg['profile_min_later_weeks'])&(profiles.n_later>=cfg['profile_min_later_tickets'])]
    profile_cases=[]
    for (employee,location),r in qualified[qualified.shrunk_gap>cfg['profile_gap']].iterrows():
        key=employee+':'+str(location);records=weeks[(weeks.employee_key==employee)&(weeks.LocationId==location)].to_dict('records')
        profile_cases.append({'case_id':stable_id('profile',key,snapshot),'unit':'employee_location','BusinessDate':'2026-07-27 to 2026-08-16','LocationId':str(location),'employee_key':employee,'evidence_snapshot':snapshot,'detector_version':cfg['version'],'policy_version':cfg['version'],'policy_confirmed':False,'reasons':['PERSISTENT_PEER_FREQUENCY_CONTEXT'],'status':'UNREVIEWED','early_shrunk_gap':float(r.shrunk_gap),'later_observed_gap':float(r.excess_later/r.n_later),'weekly_evidence':records,'interpretation':'Descriptive peer context with limited coverage; no multiplicity-validated employee anomaly. Separate workload from ticket pilot.'})
    cases=sorted(tickets+profile_cases,key=lambda c:c['case_id']);assert len({c['case_id'] for c in cases})==len(cases)
    allkeys=set(te.ticket_key);assert all(r['ticket_key'] in allkeys for r in pilot['selected'])
    threshold_sensitivity=[]
    for q in cfg['severity_sensitivity_quantiles']:
        c=float(np.quantile(residual,q));threshold_sensitivity.append({'quantile':q,'cutoff':c,'evaluation_candidates':int(((te.has_discount==1)&(te.residual>c)).sum())})
    summary={'status':'PASS','snapshot':snapshot,'full_policy_cases':len(policy),'policy_scope_counts':{k:sum(c['policy_scope_relation']==k for c in policy) for k in ['OVERLAPPING_SCOPE','DISTINCT_LINES','UNKNOWN_SCOPE']},'train_n':len(tr),'calibration_n':len(va),'evaluation_n':len(te),'statistical_candidates':len(stat),'profile_cases':len(profile_cases),'case_records_including_controls':len(cases),'threshold_sensitivity':threshold_sensitivity,'occurrence_prediction':class_metrics(te.has_discount,te.expected_occurrence),'conditional_severity_prediction':ratio_metrics(te.loc[te.has_discount==1,'discount_ratio'],te.loc[te.has_discount==1,'expected_ratio']),'model_predictors':'location, channel, hour, weekday, gross, lines, traffic, product category/diversity/share, detailed payment; no employee identity, tips, discount labels or manager','usefulness':'UNKNOWN: no human reviews yet; predictive accuracy is not misuse detection precision','remote_deployment':False,'zip_modified':False}
    a.output.mkdir(parents=True);write(a.output/'cases.json',cases);write(a.output/'pilot.json',pilot);write(a.output/'summary.json',summary);write(a.output/'manifest.json',lineage|{'snapshot':snapshot,'policy_statement_id':raw['statement_id']});write(a.output/'review_metrics.json',review_metrics(pilot,[]));(a.output/'review_events.jsonl').touch()
    te[['ticket_key','BusinessDate','has_discount','discount_ratio','expected_occurrence','expected_ratio','residual','excess_amount']].to_json(a.output/'private_scored_sample.json',orient='records',indent=2)
    selected_id=pilot['selected'][0]['case_id'];write(a.output/'review_template.json',{'review_event_id':'REPLACE_WITH_NEW_UUID','case_id':selected_id,'reviewed_at':'REPLACE_WITH_ISO_TIMESTAMP_AND_TIMEZONE','reviewer_id':'REPLACE_WITH_ACTUAL_REVIEWER','decision':'INSUFFICIENT_EVIDENCE','reason_code':'REPLACE_WITH_REASON','justification':'REPLACE_WITH_ACTUAL_REVIEW_EVIDENCE','policy_version':cfg['version'],'evidence_snapshot':snapshot,'review_minutes':1.0,'previous_review_event_id':None})
    render_report(a.output,cases,pilot,summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
