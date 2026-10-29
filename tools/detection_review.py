"""Inspect cases, append actual human decisions, and calculate review metrics.

Never edits case evidence. Uses an exclusive file lock for append-only decisions.
"""
import argparse,json,sys,fcntl,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'src/common'))
from detection.core import validate_case_review,review_metrics
from review_contract import validate_review

def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);sub=p.add_subparsers(dest='action',required=True)
    show=sub.add_parser('show');show.add_argument('case_id');add=sub.add_parser('record');add.add_argument('event_file',type=Path);sub.add_parser('metrics');a=p.parse_args()
    cases={c['case_id']:c for c in json.loads((a.run/'cases.json').read_text())}
    if a.action=='show':print(json.dumps(cases[a.case_id],indent=2));return
    log=a.run/'review_events.jsonl'
    with log.open('a+') as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX if a.action=='record' else fcntl.LOCK_SH);stream.seek(0)
        events=[json.loads(line) for line in stream if line.strip()];existing={e['review_event_id']:e for e in events}
        if len(existing)!=len(events):raise ValueError('Duplicate review IDs in log')
        if a.action=='record':
            event=json.loads(a.event_file.read_text());case=cases.get(event.get('case_id'))
            if case is None:raise ValueError('Unknown case')
            for key in ['review_event_id','reviewed_at','reviewer_id','reason_code','justification']:
                if str(event.get(key,'')).startswith('REPLACE_'):raise ValueError('Unfilled review template')
            event=validate_case_review(event,case,existing,validate_review);stream.seek(0,2);stream.write(json.dumps(event,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno());events.append(event)
        result=review_metrics(json.loads((a.run/'pilot.json').read_text()),events)
        fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
