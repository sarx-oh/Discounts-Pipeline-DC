"""Prepare/collect read-only receipt evidence for a fixed private review pilot."""
import argparse,json,re,hashlib,html
from pathlib import Path
from prepare_discount_query import render
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','collect']);p.add_argument('--run',type=Path,required=True);p.add_argument('--state',type=Path);p.add_argument('--warehouse');a=p.parse_args()
pilot=json.loads((a.run/'pilot.json').read_text());keys=sorted(x['ticket_key'] for x in pilot['selected']);assert len(keys)==len(set(keys)) and all(re.fullmatch('[0-9a-f]{64}',k) for k in keys)
request=a.run/'pilot_receipts_request.json'
if a.action=='prepare':
 s=(ROOT/'src/analysis/detection_pilot_receipts.sql').read_text().replace('{{ticket_filter}}',','.join("'"+k+"'" for k in keys));sql,sources=render(s,json.loads(a.state.read_text()));obj={'warehouse_id':a.warehouse,'statement':sql,'wait_timeout':'10s','on_wait_timeout':'CONTINUE','disposition':'INLINE','format':'JSON_ARRAY'}
 for path,value in [(request,obj),(request.with_suffix('.sources.json'),sources)]:
  if path.exists():assert json.loads(path.read_text())==value,'Immutable request mismatch'
  else:path.write_text(json.dumps(value,indent=2))
 print(request)
else:
 raw=json.loads((a.run/'pilot_receipts_data.json').read_text());manifest=json.loads((a.run/'manifest.json').read_text());assert all(manifest['sources'][k]==v for k,v in raw['sources'].items())
 assert len(raw['rows'])==len(keys) and {r['ticket_key'] for r in raw['rows']}==set(keys)
 records={}
 for row in raw['rows']:
  row=dict(row)
  for c in ['lines','discounts','payments']:row[c]=json.loads(row.pop(c+'_json') or '[]')
  records[row['ticket_key']]=row
 evidence={'snapshot':pilot['snapshot'],'statement_id':raw['statement_id'],'sources':raw['sources'],'records':records}
 dest=a.run/'receipt_evidence.json'
 if dest.exists():assert json.loads(dest.read_text())==evidence
 else:dest.write_text(json.dumps(evidence,indent=2))
 esc=lambda x:html.escape(str(x))
 body=['<!doctype html><html lang="en"><meta charset="utf-8"><title>Pilot receipt evidence</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:16px}details{margin:12px 0}summary{cursor:pointer}</style><h1>Private pilot receipt evidence</h1><p>Version-pinned POS records. A recorded employee/manager is not proof of authorization. <a href="review.html">Return to review cases</a>.</p>']
 for selected in pilot['selected']:
  key=selected['ticket_key'];body.append(f'<details id="{key}"><summary>{esc(selected["case_id"][:16])} — {esc(", ".join(selected["arms"]))}</summary><pre>{esc(json.dumps(records[key],indent=2))}</pre></details>')
 (a.run/'receipts.html').write_text(''.join(body)+'</html>')
 report=a.run/'review.html';text=report.read_text();marker='<h1>Discount review prototype</h1>';link='<p><a href="receipts.html">Open supporting receipts for all pilot tickets</a></p>'
 if link not in text:report.write_text(text.replace(marker,marker+link))
 print('Verified receipt coverage:',len(records),'tickets')
