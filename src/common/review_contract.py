"""Validation contract used by the local review CLI, not a deployed Databricks workflow.

A case is a signal. Only a documented human decision can confirm a policy breach.
"""
from datetime import datetime

DECISIONS={'JUSTIFIED','CONFIRMED_POLICY_BREACH','DATA_ISSUE','INSUFFICIENT_EVIDENCE'}

def validate_review(event,case_ids,existing_events):
    """Validate a review event against known cases and previous events; reject malformed or conflicting decisions."""
    required=['review_event_id','case_id','reviewed_at','reviewer_id','decision','reason_code',
              'justification','policy_version','evidence_snapshot']
    if any(not isinstance(event.get(k),str) or not event[k].strip() for k in required):
        raise ValueError('Review requires identity, timestamp, reason, policy and evidence')
    if event['review_event_id'] in existing_events:
        raise ValueError('Review events are append-only with unique IDs')
    if event['case_id'] not in case_ids:raise ValueError('Unknown case')
    if event['decision'] not in DECISIONS:raise ValueError('Invalid review decision')
    timestamp=datetime.fromisoformat(event['reviewed_at'].replace('Z','+00:00'))
    if timestamp.tzinfo is None:raise ValueError('Timestamp needs timezone')
    previous=event.get('previous_review_event_id')
    if previous:
        parent=existing_events.get(previous)
        if not parent or parent['case_id']!=event['case_id']:raise ValueError('Invalid preceding review')
        parent_time=datetime.fromisoformat(parent['reviewed_at'].replace('Z','+00:00'))
        if timestamp<=parent_time:raise ValueError('Review correction must be later')
    return dict(event)
