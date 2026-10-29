# Databricks notebook source
"""Prepare an isolated analytical/review base. No scoring policy is deployed."""
import json,re
from pyspark.sql import functions as F

cfg=json.loads(dbutils.widgets.get('config'))
schema=cfg['output_schema']
assert re.fullmatch(r'workspace\.applebees_test_[a-f0-9]{12}_discount_review',schema)
assert cfg['output_path'].startswith('/Volumes/workspace/applebees_test_0eef22876f8b_bronze/raw/discount_review_')
assert '..' not in cfg['output_path']
versions=cfg['sources'];protected=cfg['protected_tables']
def current(tables):
    return {t:int(spark.sql(f'DESCRIBE HISTORY {t} LIMIT 1').first().version) for t in tables}
before=current(protected)
source_before=current(versions)
assert source_before==versions
for alias in ['ticket_metrics','discounts','employee_ticket_activity']:
    table=next(t for t in versions if t.endswith('.'+alias))
    assert re.fullmatch(r'workspace\.applebees_test_0eef22876f8b_(silver|gold)\.[a-z_]+',table)
    spark.read.option('versionAsOf',versions[table]).table(table).createOrReplaceTempView(alias)
assert not spark.catalog.databaseExists(schema),'Fresh output schema required'
spark.sql(f'CREATE SCHEMA {schema}')
report={'status':'RUNNING','schema':schema,'sources':versions,'protected_before':before,'tables':{}}
K=['CheckId','LocationId','BusinessDate']
def save(name,df,keys):
    assert re.fullmatch('[a-z_]+',name)
    assert df.groupBy(*keys).count().filter('count>1').limit(1).count()==0,name
    df.createOrReplaceTempView('new_review_output')
    spark.sql(f'CREATE TABLE {schema}.{name} USING DELTA AS SELECT * FROM new_review_output')
    report['tables'][name]={'rows':spark.table(schema+'.'+name).count(),'version':current([schema+'.'+name])[schema+'.'+name]}

features=spark.sql('''SELECT *,
 CASE WHEN BusinessDate<DATE'2026-07-01' THEN 'train' WHEN BusinessDate<DATE'2026-07-26' THEN 'validation' ELSE 'test' END temporal_split,
 reconciled AND account_candidate>0 AND discount_denominator_valid AND negative_payment_records=0 AS model_eligible,
 hour(open_local) open_hour,dayofweek(BusinessDate) day_of_week,
 'payment_employee_id records participation, not confirmed authorization' AS attribution_caveat
 FROM ticket_metrics''')
save('ticket_features',features,K)
assert report['tables']['ticket_features']['rows']==spark.table('ticket_metrics').count()

events=spark.sql('''SELECT *,concat_ws(':',CAST(CheckId AS STRING),CAST(LocationId AS STRING),CAST(BusinessDate AS STRING),
 discount_scope,COALESCE(CAST(item_pos AS STRING),'ticket'),CAST(discount_pos AS STRING)) event_key,
 CASE WHEN DiscountId IN (518,520,523) THEN 'EMP50_LABEL_CANDIDATE'
 WHEN DiscountId=65 THEN 'MIT_MEAL_UNCONFIRMED_MAPPING' ELSE 'OTHER' END policy_mapping
 FROM discounts''')
save('discount_events',events,['event_key'])
events.createOrReplaceTempView('review_events')
cases=spark.sql('''WITH counts AS (
 SELECT CheckId,LocationId,BusinessDate,COUNT(*) positive_events,COUNT(DISTINCT DiscountId) types,
 sort_array(collect_set(DiscountId)) discount_ids,SUM(Amount) total_positive_discount
 FROM review_events WHERE Amount>0 GROUP BY CheckId,LocationId,BusinessDate
), candidates AS (
 SELECT e.*,c.positive_events,c.types,c.discount_ids,c.total_positive_discount
 FROM review_events e JOIN counts c USING(CheckId,LocationId,BusinessDate)
 WHERE Amount>0 AND DiscountId IN (518,520,523) AND c.types>1
)
SELECT sha2(concat('emp50-cooccurrence-v1:',event_key),256) case_id,*,
 'EMP50_OTHER_POSITIVE_DISCOUNT' rule_id,'1' rule_version,
 'REQUIRES_POLICY_MAPPING_AND_SCOPE_CONFIRMATION' evidence_status,
 'CANDIDATE_NOT_CONFIRMED_VIOLATION' interpretation
 FROM candidates''')
save('policy_review_candidates',cases,['case_id'])

weekly=spark.sql('''SELECT CAST(date_trunc('WEEK',m.BusinessDate) AS DATE) week,
 m.payment_employee_id EmployeeId,m.LocationId,m.channel_name,m.payment_family,
 COUNT(*) tickets,SUM(m.has_discount) discounted_tickets,SUM(m.discount_total_raw) discount_amount,
 SUM(CASE WHEN m.discount_denominator_valid THEN m.discount_total_raw ELSE 0 END) intensity_numerator,
 SUM(CASE WHEN m.discount_denominator_valid THEN m.grossprice_sum_unvalidated ELSE 0 END) intensity_denominator,
 COUNT_IF(m.reconciled AND m.account_candidate>0) positive_reconciled_tickets,
 COUNT_IF(NOT m.reconciled) nonreconciled_tickets,
 MIN(m.BusinessDate) first_date,MAX(m.BusinessDate) last_date
 FROM ticket_metrics m
 GROUP BY CAST(date_trunc('WEEK',m.BusinessDate) AS DATE),m.payment_employee_id,m.LocationId,m.channel_name,m.payment_family''')
save('employee_weekly',weekly,['week','EmployeeId','LocationId','channel_name','payment_family'])
assert weekly.agg(F.sum('tickets')).first()[0]==report['tables']['ticket_features']['rows']

# A schema contract only: an empty event log, no external reviewer assignments.
log=spark.createDataFrame([],'''review_event_id STRING,case_id STRING,reviewed_at TIMESTAMP,
 reviewer_id STRING,decision STRING,reason_code STRING,justification STRING,
 policy_version STRING,evidence_snapshot STRING,previous_review_event_id STRING''')
save('review_decision_log',log,['review_event_id'])
report['protected_after']=current(protected)
report['source_after']=current(versions)
assert report['protected_after']==before and report['source_after']==versions
report['positive_discount_events']=spark.table('discounts').filter('Amount>0').count()
report['distinct_candidate_tickets']=cases.select(*K).distinct().count()
report['status']='PASS'
dbutils.fs.put(cfg['output_path'],json.dumps(report,default=str),False)
dbutils.notebook.exit(json.dumps(report,default=str))
