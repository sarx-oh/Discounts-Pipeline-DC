import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/common'))
from pipeline_support import PipelineContext, load_config, require_isolated_destination

spec=importlib.util.spec_from_file_location('prepare_query',ROOT/'tools/prepare_discount_query.py')
query=importlib.util.module_from_spec(spec);spec.loader.exec_module(query)

class Safety(unittest.TestCase):
    def test_original_destination_rejected_before_spark(self):
        # None makes any accidental Spark call fail, independently of the guard.
        with self.assertRaisesRegex(ValueError,'sandbox'):
            PipelineContext(None,load_config(),'bronze')

    def test_mixed_schemas_and_original_volume_rejected(self):
        prefix='applebees_test_012345abcdef'
        cfg={'catalog':'workspace','schemas':{x:prefix+'_'+x for x in ['bronze','silver','gold']},
             'base_path':f'/Volumes/workspace/{prefix}_bronze/raw'}
        require_isolated_destination(cfg)
        for field,value in [('base_path','/Volumes/workspace/applebees_eda/raw'),('catalog','other')]:
            changed=copy.deepcopy(cfg);changed[field]=value
            with self.assertRaises(ValueError):require_isolated_destination(changed)
        cfg['schemas']['gold']='applebees_gold'
        with self.assertRaises(ValueError):require_isolated_destination(cfg)

    def state(self):
        b={'workspace.applebees_test_012345abcdef_bronze.checks_raw':0}
        s={'workspace.applebees_test_012345abcdef_silver.discounts':1}
        g={'workspace.applebees_test_012345abcdef_gold.ticket_metrics':9}
        rows=[['bronze','COMPLETE','{}',json.dumps(b)],['silver','COMPLETE',json.dumps(b),json.dumps(s)],['gold','COMPLETE',json.dumps(s),json.dumps(g)]]
        return {'status':{'state':'SUCCEEDED'},'manifest':{'schema':{'columns':[{'name':c} for c in ['layer','status','inputs_json','outputs_json']]}},'result':{'data_array':rows}}

    def test_queries_pin_sources_and_reject_incomplete_or_incoherent_state(self):
        sql,versions=query.render('SELECT * FROM {{discounts}}',self.state())
        self.assertIn('VERSION AS OF 1',sql);self.assertEqual(len(versions),1)
        state=self.state();state['result']['data_array'][0][1]='RUNNING'
        with self.assertRaises(ValueError):query.render('SELECT * FROM {{discounts}}',state)
        state=self.state();state['result']['data_array'][2][2]='{}'
        with self.assertRaises(ValueError):query.render('SELECT * FROM {{discounts}}',state)

    def test_mutating_query_rejected(self):
        with self.assertRaises(ValueError):query.render('DELETE FROM {{discounts}}',self.state())

if __name__=='__main__':unittest.main()
