"""Render the exported remote evidence without treating expected failure as success."""
import json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
e=json.loads((r/'evidence/incremental_job.json').read_text())
labels={'initial':'Initial load','repeat':'Unchanged repeat','changed':'New file and correction','failure':'Duplicate rejection','recovery':'Recovery'}
lines=['# Test Job results','',f"Suite status: **{e['status']}**.",'',f"Job: `{e['job_id']}`. Sandbox: `{e['sandbox']}`.",'','| Scenario | Run | Job status | Independent verification |','|---|---|---|---|']
for phase,label in labels.items():
 d=e['phases'].get(phase,{})
 run_label=f"[{d['run_id']}]({d['run_page_url']})" if d.get('run_page_url') else str(d.get('run_id','Pending'))
 lines.append(f"| {label} | {run_label} | {d.get('job_state',{}).get('result_state','Pending')} | {'PASS' if phase in e['completed_phases'] else 'Pending'} |")
lines+=['','The duplicate scenario expects FAILED and downstream UPSTREAM_FAILED. Suite PASS confirms rejection and unchanged data tables, not acceptance of the invalid batch.','',f"Dashboard unchanged after completion: `{e['dashboard_unchanged']}`.",'','Every successful run checks all 25 original table versions. Inputs are synthetic; the 11 GB are not reingested. Reports contain no real tickets.','','## Independent checks','']
for phase,d in e['phases'].items():
 lines += [f"### {labels[phase]}",'']
 lines += ['- '+c for c in d.get('verification',{}).get('checks',[])]
 lines += ['']
attempts=[a for a in e['phases'].get('failure',{}).get('attempts',[]) if a['task_key']=='bronze']
if len(attempts)>1:lines += [f'Observed {len(attempts)} Bronze attempts during duplicate testing. Serverless auto-optimization can retry even with max_retries=0; see [operations](operacion.md).','']
lines+=['## Limitations','','These tests verify functional correctness with fixtures and retain historical regression evidence. They do not measure real-load performance or promote the pipeline to the current dashboard. POS hierarchy and business questions remain documented under [quality](calidad.md).','']
(r/'docs/resultado_job.md').write_text('\n'.join(lines))
