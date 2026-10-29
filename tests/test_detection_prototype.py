"""Behavioral contracts for candidate safety, scope, sampling and review history."""
import sys,unittest,json,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'src/common'))
from detection.core import policy_cases,line_overlap,merge_ticket_cases,pilot_sample,review_metrics,validate_case_review
from review_contract import validate_review

CFG={'policy_ids':[518,520,523],'version':'test-v1','policy_mapping_confirmed':False,'policy_scope_confirmed':False,'pilot_arm_capacity':2,'pilot_control_capacity':2,'pilot_seed':'test'}
def event(id=523,amount=1,line=0,scope='item',key='ticket'):
 return {'ticket_key':key,'DiscountId':id,'Amount':amount,'item_pos':line,'discount_scope':scope,'discount_pos':0,'BusinessDate':'2026-08-01','LocationId':1}
def decision(case,**changes):
 e={'review_event_id':'r1','case_id':case['case_id'],'reviewed_at':'2026-10-28T12:00:00-06:00','reviewer_id':'synthetic-reviewer','decision':'INSUFFICIENT_EVIDENCE','reason_code':'MAPPING','justification':'Synthetic test only','policy_version':'test-v1','evidence_snapshot':'snapshot','review_minutes':2};e.update(changes);return e
class DetectionTests(unittest.TestCase):
 def test_zero_and_negative_do_not_activate(self):
  self.assertEqual(policy_cases([event(),event(93,0),event(2,-4)],CFG,'snapshot'),[])
 def test_same_type_repetition_not_combination(self):
  self.assertEqual(policy_cases([event(),event(line=2)],CFG,'snapshot'),[])
 def test_distinct_lines_not_overlap(self):
  c=policy_cases([event(),event(93,line=2)],CFG,'snapshot')[0];self.assertEqual(c['policy_scope_relation'],'DISTINCT_LINES');self.assertFalse(c['policy_confirmed'])
 def test_ticket_scope_overlaps(self):
  self.assertEqual(line_overlap(event(),event(93,scope='ticket',line=None)),'OVERLAPPING_SCOPE')
 def test_unknown_position_not_distinct(self):
  self.assertEqual(line_overlap(event(line=None),event(93,line=2)),'UNKNOWN_SCOPE')
 def test_same_line_overlap(self):
  self.assertEqual(line_overlap(event(),event(93)),'OVERLAPPING_SCOPE')
 def test_stable_deduplicated_case(self):
  a=policy_cases([event(),event(93)],CFG,'snapshot');b=dict(a[0]);b['reasons']=['HIGH_CONDITIONAL_DISCOUNT'];b['model_evidence']={'excess_amount':3}
  merged=merge_ticket_cases(a,[b]);self.assertEqual(len(merged),1);self.assertEqual(len(merged[0]['reasons']),2)
  self.assertEqual(a,policy_cases([event(93),event()],CFG,'snapshot'))
 def test_pilot_controls_and_common_universe(self):
  cases=policy_cases([event(),event(93),event(key='outside'),event(93,key='outside')],CFG,'snapshot')
  p=pilot_sample(cases,['ticket','c1','c2','c3'],CFG,'snapshot');self.assertEqual(p,pilot_sample(cases,list(reversed(['ticket','c1','c2','c3'])),CFG,'snapshot'))
  self.assertEqual(p['arm_A_n'],1);self.assertEqual(p['control_n'],2);self.assertEqual(len({r['case_id'] for r in p['selected']}),len(p['selected']))
  self.assertTrue(all(not r['is_alert'] for r in p['selected'] if 'CONTROL' in r['arms']));self.assertNotIn('outside',[r['ticket_key'] for r in p['selected']])
 def test_empty_reviews_are_unknown(self):
  p=pilot_sample([],['c1'],CFG,'snapshot');m=review_metrics(p,[]);self.assertIsNone(m['arms']['CONTROL']['confirmed_breach_share'])
 def test_unconfirmed_breach_rejected(self):
  c=policy_cases([event(),event(93)],CFG,'snapshot')[0]
  with self.assertRaises(ValueError):validate_case_review(decision(c,decision='CONFIRMED_POLICY_BREACH'),c,{},validate_review)
 def test_snapshot_mismatch_rejected(self):
  c=policy_cases([event(),event(93)],CFG,'snapshot')[0]
  with self.assertRaises(ValueError):validate_case_review(decision(c,evidence_snapshot='wrong'),c,{},validate_review)
 def test_correction_latest_and_no_duplicate(self):
  c=policy_cases([event(),event(93)],CFG,'snapshot')[0];e=decision(c);validate_case_review(e,c,{},validate_review)
  with self.assertRaises(ValueError):validate_case_review(e,c,{'r1':e},validate_review)
  with self.assertRaises(ValueError):validate_case_review(decision(c,review_event_id='r2',reviewed_at='2026-10-28T13:00:00-06:00'),c,{'r1':e},validate_review)
  corrected=decision(c,review_event_id='r2',reviewed_at='2026-10-28T13:00:00-06:00',previous_review_event_id='r1',decision='JUSTIFIED');validate_case_review(corrected,c,{'r1':e},validate_review)
 def test_unresolved_in_reviewed_denominator(self):
  c=policy_cases([event(),event(93)],CFG,'snapshot')[0];p=pilot_sample([c],['ticket'],CFG,'snapshot');m=review_metrics(p,[decision(c)])
  self.assertEqual(m['arms']['A_POLICY']['insufficient_evidence_share'],1);self.assertEqual(m['arms']['A_POLICY']['confirmed_breach_share'],0)
 def test_timing_required(self):
  c=policy_cases([event(),event(93)],CFG,'snapshot')[0]
  with self.assertRaises(ValueError):validate_case_review(decision(c,review_minutes=0),c,{},validate_review)
class ReviewCLITests(unittest.TestCase):
 def test_append_and_correct_in_synthetic_temporary_run(self):
  c=policy_cases([event(),event(93)],CFG,'snapshot')[0]
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);(d/'cases.json').write_text(json.dumps([c]));(d/'pilot.json').write_text(json.dumps(pilot_sample([c],['ticket'],CFG,'snapshot')));(d/'review_events.jsonl').touch()
   first=decision(c);(d/'event.json').write_text(json.dumps(first))
   command=[sys.executable,str(ROOT/'tools/detection_review.py'),str(d),'record',str(d/'event.json')]
   run=subprocess.run(command,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr)
   duplicate=subprocess.run(command,capture_output=True,text=True);self.assertNotEqual(duplicate.returncode,0)
   second=decision(c,review_event_id='r2',reviewed_at='2026-10-28T13:00:00-06:00',previous_review_event_id='r1',decision='JUSTIFIED');(d/'event.json').write_text(json.dumps(second))
   run=subprocess.run(command,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr)
   lines=(d/'review_events.jsonl').read_text().splitlines();self.assertEqual(len(lines),2);self.assertEqual(json.loads(lines[0]),first)
   metrics=json.loads(run.stdout);self.assertEqual(metrics['arms']['A_POLICY']['justified_share'],1)

if __name__=='__main__':unittest.main()
