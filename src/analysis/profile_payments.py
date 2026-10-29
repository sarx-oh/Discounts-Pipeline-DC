# Databricks notebook source
"""Read-only profile of the original-data sandbox; aggregate report only."""
import json
from pyspark.sql import functions as F
PREFIX='applebees_test_0eef22876f8b'
assert PREFIX.startswith('applebees_test_')
OUT=dbutils.widgets.get('output_path')
assert OUT.startswith(f'/Volumes/workspace/{PREFIX}_bronze/raw/analysis_cash_card_') and '..' not in OUT
S=f'workspace.{PREFIX}_silver';G=f'workspace.{PREFIX}_gold'
state=spark.table(f'workspace.{PREFIX}_bronze.pipeline_state').collect()
assert len(state)==3 and all(x.status=='COMPLETE' for x in state)
versions={t:v for row in state for t,v in json.loads(row.outputs_json).items()}
required=[G+'.ticket_metrics',S+'.payments',S+'.discounts']
for t in required:assert int(spark.sql(f'DESCRIBE HISTORY {t} LIMIT 1').first().version)==versions[t]
report={'status':'RUNNING','versions':{t:versions[t] for t in required},'prefix':PREFIX}
for alias,t in [('metrics',required[0]),('payments',required[1]),('discounts',required[2])]:
 df=spark.read.option('versionAsOf',versions[t]).table(t);df.createOrReplaceTempView(alias);report[alias+'_schema']=df.schema.jsonValue()
def q(sql):return [r.asDict(recursive=True) for r in spark.sql(sql).collect()]
report['payment_labels']=q('''SELECT PayCatName,IsCreditCard,COUNT(*) records,
 SUM(CASE WHEN Amount<0 THEN 1 ELSE 0 END) negative_records,
 SUM(CASE WHEN Amount=0 THEN 1 ELSE 0 END) zero_records,
 SUM(CASE WHEN Amount IS NULL THEN 1 ELSE 0 END) null_amount_records,
 SUM(Amount) amount_sum,SUM(Gratuity) gratuity_sum,
 SUM(CASE WHEN Gratuity>0 THEN 1 ELSE 0 END) positive_gratuity_records
 FROM payments GROUP BY PayCatName,IsCreditCard ORDER BY records DESC''')
report['families']=q('''SELECT payment_family,account_status,COUNT(*) tickets,SUM(has_discount) discounted,
 SUM(CASE WHEN negative_payment_records>0 THEN 1 ELSE 0 END) negative_payment_tickets
 FROM metrics GROUP BY payment_family,account_status ORDER BY tickets DESC''')
report['totals']=q('''SELECT COUNT(*) tickets,COUNT(DISTINCT BusinessDate) days,COUNT(DISTINCT LocationId) locations,
 MIN(BusinessDate) first_date,MAX(BusinessDate) last_date,SUM(has_discount) discounted,
 SUM(CASE WHEN reconciled THEN net_sales_candidate ELSE 0 END) net_sales,
 SUM(CASE WHEN reconciled THEN discount_total_raw ELSE 0 END) discounts FROM metrics''')[0]
report['status']='PASS'
dbutils.fs.put(OUT,json.dumps(report,default=str),True)
dbutils.notebook.exit(json.dumps({'status':'PASS','report':OUT}))
