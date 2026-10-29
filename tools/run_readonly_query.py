"""Submit or resume a prepared read-only SQL request; persist IDs and all chunks.

Only accepts SQL produced by prepare_discount_query.py with pinned sandbox sources.
No cloud tables, notebooks, jobs or dashboard objects are created or modified.
"""
import argparse,json,re,subprocess,time
from pathlib import Path

def call(args,profile):
    r=subprocess.run(['databricks',*args,'-p',profile,'-o','json'],capture_output=True,text=True)
    if r.returncode:raise RuntimeError(r.stderr)
    return json.loads(r.stdout)

def main():
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('--profile',default='applebees');a=p.parse_args()
    req=json.loads(a.request.read_text());sql=req['statement']
    if re.search(r'\b(CREATE|INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|TRUNCATE|VACUUM)\b',sql,re.I):raise ValueError('Mutation SQL rejected')
    sources=json.loads(a.request.with_suffix('.sources.json').read_text())
    if not sources:raise ValueError('Missing pinned source manifest')
    for table,version in sources.items():
        if not re.fullmatch(r'workspace\.applebees_test_[a-f0-9]+_(silver|gold)\.[a-z_]+',table):raise ValueError(table)
        if f'{table} VERSION AS OF {version}' not in sql:raise ValueError('Source not pinned')
    out=a.request.with_name(a.request.stem.removesuffix('_request')+'_response.json')
    if out.exists():
        result=json.loads(out.read_text())
    else:
        result=call(['api','post','/api/2.0/sql/statements','--json','@'+str(a.request)],a.profile)
        out.write_text(json.dumps(result,indent=2))
    statement=result['statement_id']
    while result['status']['state'] in ('PENDING','RUNNING'):
        print(statement,result['status']['state'],flush=True);time.sleep(10)
        result=call(['api','get','/api/2.0/sql/statements/'+statement],a.profile)
        out.write_text(json.dumps(result,indent=2))
    if result['status']['state']!='SUCCEEDED':raise RuntimeError(result['status'])
    if result['manifest'].get('truncated'):raise RuntimeError('Truncated result: narrow query or use remote notebook')
    chunk=result.get('result',{});rows=chunk.get('data_array',[])
    while chunk.get('next_chunk_internal_link'):
        chunk=call(['api','get',chunk['next_chunk_internal_link']],a.profile);rows.extend(chunk.get('data_array',[]))
    if len(rows)!=result['manifest']['total_row_count']:raise RuntimeError('Missing rows')
    columns=[c['name'] for c in result['manifest']['schema']['columns']]
    data={'statement_id':statement,'sources':sources,'rows':[dict(zip(columns,r)) for r in rows]}
    out.with_name(out.stem.removesuffix('_response')+'_data.json').write_text(json.dumps(data,indent=2))
    print('SUCCEEDED',statement,len(rows),'rows',flush=True)

if __name__=='__main__':main()
