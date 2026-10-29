import ast,importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/common'))
from pipeline_support import load_config,plan_files,merge_sql,adoptable_files
from thresholds import snapshot_key
class Contracts(unittest.TestCase):
 def test_files_detect_changed_and_keep_missing_explicit(self):
  self.assertEqual(plan_files({'a':(1,2),'b':(2,3)},{'a':(1,2)}),['b'])
  self.assertEqual(plan_files({'a':(1,3)},{'a':(1,2)}),['a'])
  with self.assertRaises(ValueError):plan_files({}, {'a':(1,2)})
 def test_adoption_rejects_modified_source(self):
  with self.assertRaises(ValueError):adoptable_files({'a':(1,5000)},[{'path':'a','first_ingest':1,'null_ingests':0}])
 def test_upserts_do_not_delete_omitted_tickets(self):
  self.assertNotIn('THEN DELETE',merge_sql('t','s',['Id','ItemsSold'],['Id']))
 def test_snapshot_reuse_is_order_independent(self):
  self.assertEqual(snapshot_key({'a':0,'b':1},'code','cfg'),snapshot_key({'b':1,'a':0},'code','cfg'))
 def test_changed_input_code_or_config_invalidates_snapshot(self):
  key=snapshot_key({'a':0},'code','cfg')
  for args in [({'a':1},'code','cfg'),({'a':0},'new','cfg'),({'a':0},'code','new')]:self.assertNotEqual(key,snapshot_key(*args))
 def test_job_requires_serial_success(self):
  j=json.loads((ROOT/'resources/jobs/incremental_job.json').read_text());self.assertEqual(j['max_concurrent_runs'],1)
  for i,t in enumerate(j['tasks']):
   self.assertEqual(t['run_if'],'ALL_SUCCESS');self.assertEqual(t.get('depends_on',[]),[{'task_key':j['tasks'][i-1]['task_key']}] if i else [])
 def test_original_reference_retained(self):
  c=load_config()['original'];self.assertEqual(c['tickets'],2142846);self.assertEqual(c['net_sales_reconciled'],'84292048.6000')
 def test_notebooks_are_clean_and_parse(self):
  for p in (ROOT/'src').rglob('*.ipynb'):
   for c in json.loads(p.read_text())['cells']:
    if c['cell_type']=='code':
     ast.parse(''.join(c['source']));self.assertEqual(c['outputs'],[]);self.assertIsNone(c['execution_count'])
 def test_volume_guard_rejects_original_or_parent_paths(self):
  tree=ast.parse((ROOT/'src/common/runtime.py').read_text())
  f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='safe_path')
  ns={'BASE':'/Volumes/workspace/applebees_test_x_bronze/raw'}
  exec(compile(ast.Module(body=[f],type_ignores=[]),'guard','exec'),ns)
  for path in ['/Volumes/workspace/applebees_eda/raw/a.json',ns['BASE']+'/../a.json']:
   with self.assertRaises(AssertionError):ns['safe_path'](path)
  self.assertEqual(ns['safe_path']('dbfs:'+ns['BASE']+'/a.json'),ns['BASE']+'/a.json')
if __name__=='__main__':unittest.main()
