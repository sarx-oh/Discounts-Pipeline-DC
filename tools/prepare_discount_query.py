"""Render a read-only analytical query against COMPLETE, pinned sandbox versions.

Produces a request only; never executes SQL or submits a job.
The state input is a successful, untruncated SQL API pipeline_state response.
"""
import argparse
import json
import re
from pathlib import Path


def render(source, response):
    if response['status']['state'] != 'SUCCEEDED' or response['manifest'].get('truncated'):
        raise ValueError('State query must succeed without truncation')
    names = [c['name'] for c in response['manifest']['schema']['columns']]
    rows = [dict(zip(names, r)) for r in response['result']['data_array']]
    if len(rows) != 3 or {r['layer'] for r in rows} != {'bronze','silver','gold'}:
        raise ValueError('Expected exactly three pipeline layers')
    if any(r['status'] != 'COMPLETE' for r in rows):
        raise ValueError('Incomplete pipeline')
    versions = {t: v for r in rows for t, v in json.loads(r['outputs_json']).items()}
    by_layer = {r['layer']: r for r in rows}
    for parent, child in [('bronze','silver'), ('silver','gold')]:
        if json.loads(by_layer[child]['inputs_json']) != json.loads(by_layer[parent]['outputs_json']):
            raise ValueError('Incoherent layer versions')
    used = {}
    def replace(match):
        name = match.group(1)
        candidates = [t for t in versions if t.split('.')[-1] == name]
        if len(candidates) != 1:
            raise ValueError('Ambiguous or missing source: '+name)
        table = candidates[0]
        if not re.fullmatch(r'workspace\.applebees_test_[a-f0-9]+_(silver|gold)\.[a-z_]+', table):
            raise ValueError('Only isolated analytical sources allowed')
        version = versions[table]
        if type(version) is not int or version < 0:
            raise ValueError('Invalid Delta version')
        used[table] = version
        return f'{table} VERSION AS OF {version}'
    sql = re.sub(r'\{\{([a-z_]+)\}\}', replace, source)
    if '{{' in sql or not used:
        raise ValueError('Unresolved source or no pinned sources')
    # Templates are trusted source code, not an arbitrary SQL execution interface.
    if re.search(r'\b(CREATE|INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|TRUNCATE|VACUUM)\b', sql, re.I):
        raise ValueError('Mutation keyword in read-only template')
    return sql, used


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('template',type=Path)
    p.add_argument('--state',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--warehouse',required=True)
    a = p.parse_args()
    sql, used = render(a.template.read_text(),json.loads(a.state.read_text()))
    a.output.write_text(json.dumps({'warehouse_id':a.warehouse,'statement':sql,
        'wait_timeout':'10s','on_wait_timeout':'CONTINUE','disposition':'INLINE','format':'JSON_ARRAY'},indent=2))
    a.output.with_suffix('.sources.json').write_text(json.dumps(used,indent=2))
