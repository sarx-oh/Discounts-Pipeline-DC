"""Pure case and pilot contracts. Candidates are not confirmed misuse."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime


def stable_id(kind, key, snapshot):
    """Return a deterministic SHA256 identifier scoped to kind, key and evidence snapshot."""
    return hashlib.sha256(f'{kind}:{key}:{snapshot}'.encode()).hexdigest()


def line_overlap(a,b):
    """Classify discount scope overlap; missing item positions remain UNKNOWN_SCOPE."""
    if a['discount_scope']=='ticket' or b['discount_scope']=='ticket':return 'OVERLAPPING_SCOPE'
    if a['discount_scope']!='item' or b['discount_scope']!='item':return 'UNKNOWN_SCOPE'
    if a.get('item_pos') is None or b.get('item_pos') is None:return 'UNKNOWN_SCOPE'
    return 'OVERLAPPING_SCOPE' if str(a['item_pos'])==str(b['item_pos']) else 'DISTINCT_LINES'


def policy_cases(events,config,snapshot):
    """Group positive discount events into provisional ticket cases; policy IDs alone do not prove a breach."""
    groups=defaultdict(list)
    for event in events:
        if event.get('Amount') is not None and float(event['Amount'])>0:groups[event['ticket_key']].append(event)
    cases=[];targets=set(config['policy_ids'])
    for key,rows in sorted(groups.items()):
        types={int(r['DiscountId']) for r in rows}
        if len(types)<2 or not (types&targets):continue
        relations={line_overlap(a,b) for a in rows if int(a['DiscountId']) in targets for b in rows if int(a['DiscountId'])!=int(b['DiscountId'])}
        relation='OVERLAPPING_SCOPE' if 'OVERLAPPING_SCOPE' in relations else 'UNKNOWN_SCOPE' if 'UNKNOWN_SCOPE' in relations else 'DISTINCT_LINES'
        r=rows[0]
        cases.append({'case_id':stable_id('ticket',key,snapshot),'unit':'ticket','ticket_key':key,
          'BusinessDate':str(r['BusinessDate']),'LocationId':str(r['LocationId']),
          'evidence_snapshot':snapshot,'detector_version':config['version'],'reasons':['POLICY_COMBINATION_CANDIDATE'],
          'policy_version':config['version'],'policy_confirmed':bool(config['policy_mapping_confirmed'] and config['policy_scope_confirmed']),
          'policy_scope_relation':relation,'policy_evidence':sorted(rows,key=lambda e:(int(e['DiscountId']),str(e.get('item_pos')),str(e.get('discount_pos')))),
          'status':'UNREVIEWED','interpretation':'Mapping, equivalence, scope and exceptions require confirmation. Not a confirmed breach.'})
    return cases


def merge_ticket_cases(policy,statistical):
    """Deduplicate by snapshot-specific case ID while retaining both rule and model reasons."""
    merged={r['case_id']:dict(r) for r in policy}
    for r in statistical:
        if r['case_id'] not in merged:merged[r['case_id']]=dict(r)
        else:
            target=merged[r['case_id']]
            assert target['ticket_key']==r['ticket_key'] and target['evidence_snapshot']==r['evidence_snapshot']
            target['reasons']=sorted(set(target['reasons']+r['reasons']))
            target['model_evidence']=r['model_evidence']
    return sorted(merged.values(),key=lambda c:c['case_id'])


def pilot_sample(cases,universe,config,snapshot):
    """Ticket-only A/B pilot, same universe, controls sampled outside both queues."""
    universe=set(universe);tickets=[c for c in cases if c['unit']=='ticket' and c['ticket_key'] in universe]
    bykey={c['ticket_key']:c for c in tickets};assert len(bykey)==len(tickets)
    def order(key):return stable_id('pilot',config['pilot_seed']+key,snapshot)
    policy=[c for c in tickets if 'POLICY_COMBINATION_CANDIDATE' in c['reasons']]
    policy.sort(key=lambda c:({'OVERLAPPING_SCOPE':0,'UNKNOWN_SCOPE':1,'DISTINCT_LINES':2}[c['policy_scope_relation']],order(c['ticket_key'])))
    stat=[c for c in tickets if 'HIGH_CONDITIONAL_DISCOUNT' in c['reasons']]
    stat.sort(key=lambda c:(-c['model_evidence']['excess_amount'],order(c['ticket_key'])))
    cap=config['pilot_arm_capacity'];A=[c['ticket_key'] for c in policy[:cap]]
    # Keep policy-first priorities fixed; fill remaining capacity with new statistical cases.
    B=(A+[c['ticket_key'] for c in stat if c['ticket_key'] not in set(A)])[:cap]
    remaining=sorted(universe-set(bykey),key=order);controls=remaining[:config['pilot_control_capacity']]
    selected=[]
    for key in sorted(set(A+B+controls),key=order):
        membership=[name for name,keys in [('A_POLICY',A),('B_POLICY_PLUS_CONTEXT',B),('CONTROL',controls)] if key in keys]
        selected.append({'ticket_key':key,'case_id':stable_id('ticket',key,snapshot),'arms':membership,'is_alert':key not in controls,
            'selection_probability':len(controls)/len(remaining) if key in controls else 1.,
            'selection_probability_scope':'randomized control stratum' if key in controls else 'deterministic selected top-list; NOT population inclusion probability'})
    return {'snapshot':snapshot,'common_universe_n':len(universe),'available_policy_candidates':len(policy),'available_statistical_candidates':len(stat),
      'arm_A_n':len(A),'arm_B_n':len(B),'control_n':len(controls),'nonalerted_pool_n':len(remaining),
      'unique_review_tickets':len(selected),'selected':selected,'comparison':'Both arms use the same sampled late-period ticket universe; profiles excluded.'}


def validate_case_review(event,case,existing,validate_review):
    """Validate snapshot, policy and correction linkage before accepting a timed human decision. Raises ValueError on invalid evidence."""
    validate_review(event,{case['case_id']},existing)
    if event['evidence_snapshot']!=case['evidence_snapshot']:raise ValueError('Evidence snapshot mismatch')
    if event['policy_version']!=case['policy_version']:raise ValueError('Policy version mismatch')
    previous=[e for e in existing.values() if e['case_id']==case['case_id']]
    latest=max(previous,key=lambda e:datetime.fromisoformat(e['reviewed_at'].replace('Z','+00:00'))) if previous else None
    if latest and event.get('previous_review_event_id')!=latest['review_event_id']:raise ValueError('Correction must reference latest case decision')
    if event['decision']=='CONFIRMED_POLICY_BREACH' and not case.get('policy_confirmed',False):raise ValueError('Policy mapping/scope not confirmed; a model flag cannot confirm a breach')
    minutes=event.get('review_minutes')
    if not isinstance(minutes,(int,float)) or isinstance(minutes,bool) or not 0<minutes<10000:raise ValueError('Positive review_minutes required')
    return dict(event)


def review_metrics(pilot,events):
    """Summarize latest decisions per pilot arm. Unreviewed rates remain None, not zero; arms may share tickets."""
    latest={}
    for event in events:
        k=event['case_id']
        if k not in latest or datetime.fromisoformat(event['reviewed_at'].replace('Z','+00:00'))>datetime.fromisoformat(latest[k]['reviewed_at'].replace('Z','+00:00')):latest[k]=event
    result={}
    for arm in ['A_POLICY','B_POLICY_PLUS_CONTEXT','CONTROL']:
        selected=[r for r in pilot['selected'] if arm in r['arms']];reviewed=[latest[r['case_id']] for r in selected if r['case_id'] in latest];n=len(reviewed)
        result[arm]={'selected':len(selected),'reviewed':n,'review_coverage':n/len(selected) if selected else None,
          'confirmed_breach_share':sum(r['decision']=='CONFIRMED_POLICY_BREACH' for r in reviewed)/n if n else None,
          'justified_share':sum(r['decision']=='JUSTIFIED' for r in reviewed)/n if n else None,
          'insufficient_evidence_share':sum(r['decision']=='INSUFFICIENT_EVIDENCE' for r in reviewed)/n if n else None,
          'data_issue_share':sum(r['decision']=='DATA_ISSUE' for r in reviewed)/n if n else None,
          'mean_review_minutes':sum(r['review_minutes'] for r in reviewed)/n if n else None}
    return {'status':'AWAITING_HUMAN_REVIEW' if not events else 'PARTIAL_OR_COMPLETED_REVIEW','arms':result,'limitation':'No recall estimate or misuse probability. Metrics among reviewed cases include unresolved decisions; incomplete coverage can bias comparisons.'}
