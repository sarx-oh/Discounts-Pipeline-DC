import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/common'))
from review_contract import validate_review

class ReviewContract(unittest.TestCase):
    def event(self):
        return dict(review_event_id='r1',case_id='c1',reviewed_at='2026-10-27T12:00:00Z',reviewer_id='reviewer',
            decision='INSUFFICIENT_EVIDENCE',reason_code='MAPPING_PENDING',justification='Policy mapping not confirmed',
            policy_version='pending-v1',evidence_snapshot='schema.table@v0')
    def test_signal_cannot_automatically_become_fraud_label(self):
        e=self.event();e['decision']='FRAUD'
        with self.assertRaises(ValueError):validate_review(e,{'c1'},{})
    def test_missing_evidence_and_unknown_case_rejected(self):
        e=self.event();e['evidence_snapshot']=''
        with self.assertRaises(ValueError):validate_review(e,{'c1'},{})
        with self.assertRaises(ValueError):validate_review(self.event(),set(),{})
    def test_correction_preserves_previous_event(self):
        old=self.event();events={'r1':dict(old)};new=self.event()
        new.update(review_event_id='r2',previous_review_event_id='r1',reviewed_at='2026-10-28T12:00:00Z',decision='JUSTIFIED')
        validate_review(new,{'c1'},events);self.assertEqual(events,{'r1':old})
        new['case_id']='c2'
        with self.assertRaises(ValueError):validate_review(new,{'c1','c2'},events)

if __name__=='__main__':unittest.main()
