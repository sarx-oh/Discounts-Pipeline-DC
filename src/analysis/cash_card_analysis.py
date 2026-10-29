# Databricks notebook source
"""Discount association analysis on pinned sandbox snapshots, no production writes."""
import json,re,time,traceback
from decimal import Decimal
from pyspark.sql import functions as F
PREFIX='applebees_test_0eef22876f8b'
OUT=dbutils.widgets.get('output_path');DEST=dbutils.widgets.get('output_schema')
VERSIONS=json.loads(dbutils.widgets.get('input_versions'))
assert re.fullmatch(r'workspace\.applebees_test_0eef22876f8b_analysis_[a-f0-9]{12}',DEST)
assert OUT.startswith(f'/Volumes/workspace/{PREFIX}_bronze/raw/analysis_cash_card_') and '..' not in OUT
S=f'workspace.{PREFIX}_silver';G=f'workspace.{PREFIX}_gold'
assert set(VERSIONS)=={G+'.ticket_metrics',S+'.payments',S+'.discounts'}
report={'status':'RUNNING','input_versions':VERSIONS,'output_schema':DEST,'checks':[],'tables':{}}
start=time.monotonic()
def persist(stage):
 report['stage']=stage;report['seconds']=round(time.monotonic()-start,2)
 dbutils.fs.put(OUT,json.dumps(report,default=str),True)
def q(sql):return spark.sql(sql)
def rows(sql):return [x.asDict(recursive=True) for x in q(sql).collect()]
def check(label,ok):
 assert ok,label
 report['checks'].append(label)
def publish(name,df):
 assert re.fullmatch('[a-z_]+',name)
 t=DEST+'.'+name;df.write.format('delta').mode('error').saveAsTable(t)
 report['tables'][name]={'name':t,'version':int(q(f'DESCRIBE HISTORY {t} LIMIT 1').first().version)}
 spark.read.option('versionAsOf',report['tables'][name]['version']).table(t).createOrReplaceTempView(name)
def current_versions(tables):return {t:int(q(f'DESCRIBE HISTORY {t} LIMIT 1').first().version) for t in tables}
groups={'bronze':['checks_raw','locations_raw','items_raw','revenue_centers_raw','employees_raw'],
'silver':['checks','dim_locations','dim_items','dim_revenue_centers','dim_employees','items_sold','payments','discounts','taxes','voids','item_quality','ticket_quality','reference_quality'],
'gold':['ticket_metrics','daily_location_channel','discount_type_daily','employee_ticket_activity','employee_activity_daily','review_thresholds','review_cases']}
protected=['workspace.applebees_'+layer+'.'+name for layer,names in groups.items() for name in names]
try:
 report['protected_before']=current_versions(protected)
 check('input_versions_current_before',current_versions(VERSIONS)==VERSIONS)
 for alias,t in [('m',G+'.ticket_metrics'),('p',S+'.payments'),('d',S+'.discounts')]:spark.read.option('versionAsOf',VERSIONS[t]).table(t).createOrReplaceTempView(alias)
 check('original_ticket_count',q('SELECT COUNT(*) FROM m').first()[0]==2142846)
 check('source_ticket_key_unique',q('SELECT CheckId,LocationId,BusinessDate FROM m GROUP BY ALL HAVING COUNT(*)>1 LIMIT 1').count()==0)
 q(f'CREATE SCHEMA {DEST}')
 persist('payment_classification')
 q('''CREATE OR REPLACE TEMP VIEW payment_rows AS SELECT *,
 CASE WHEN IsCreditCard=true AND UPPER(TRIM(PayCatName))='CASH' THEN 'CONFLICTO'
      WHEN IsCreditCard=true THEN 'TARJETA'
      WHEN UPPER(TRIM(PayCatName))='CASH' THEN 'EFECTIVO' ELSE 'OTRO' END instrument,
 UPPER(TRIM(PayCatName)) IN ('OLO-VISA','OLO-MASTERCARD','OLO-DISCOVER','OLO-AMEX') olo_card_label
 FROM p''')
 q('''CREATE OR REPLACE TEMP VIEW payment_ticket AS SELECT CheckId,LocationId,BusinessDate,
 COUNT(*) records,SUM(CASE WHEN instrument='EFECTIVO' THEN 1 ELSE 0 END) cash_n,
 SUM(CASE WHEN instrument='TARJETA' THEN 1 ELSE 0 END) card_n,
 SUM(CASE WHEN instrument='OTRO' THEN 1 ELSE 0 END) other_n,
 SUM(CASE WHEN instrument='CONFLICTO' THEN 1 ELSE 0 END) conflict_n,
 SUM(CASE WHEN instrument='TARJETA' OR olo_card_label THEN 1 ELSE 0 END) card_label_n,
 SUM(CASE WHEN Amount<0 THEN 1 ELSE 0 END) neg_n,
 SUM(CASE WHEN Amount>0 THEN 1 ELSE 0 END) pos_n,
 SUM(CASE WHEN Amount=0 THEN 1 ELSE 0 END) zero_n,
 SUM(CASE WHEN Amount IS NULL THEN 1 ELSE 0 END) null_amount_n
 FROM payment_rows GROUP BY CheckId,LocationId,BusinessDate''')
 q('''CREATE OR REPLACE TEMP VIEW features AS SELECT m.*,
 CASE WHEN p.records IS NULL THEN 'SIN_PAGOS' WHEN conflict_n>0 THEN 'CONFLICTO'
 WHEN cash_n=records THEN 'SOLO_EFECTIVO' WHEN card_n=records THEN 'SOLO_TARJETA'
 WHEN cash_n>0 AND card_n>0 AND other_n=0 THEN 'MIXTO_EFECTIVO_TARJETA'
 WHEN cash_n>0 AND card_n>0 THEN 'MIXTO_EFECTIVO_TARJETA_OTRO'
 WHEN cash_n>0 THEN 'MIXTO_EFECTIVO_OTRO' WHEN card_n>0 THEN 'MIXTO_TARJETA_OTRO' ELSE 'SOLO_OTROS' END family,
 CASE WHEN p.records IS NULL THEN 'SIN_PAGOS' WHEN conflict_n>0 THEN 'CONFLICTO'
 WHEN cash_n=records THEN 'SOLO_EFECTIVO' WHEN card_label_n=records THEN 'SOLO_TARJETA'
 ELSE 'OTROS_O_MIXTOS' END family_olo_sensitivity,
 COALESCE(reconciled AND account_candidate>0 AND neg_n=0 AND null_amount_n=0 AND pos_n>0,false) positive_sale,
 COALESCE(reconciled AND account_candidate>0 AND neg_n=0 AND null_amount_n=0 AND pos_n>0
 AND mismatched_item_lines=0 AND unassessable_item_lines=0,false) strict_sale,
 COALESCE(reconciled AND discount_denominator_valid,false) intensity_valid,
 COALESCE(neg_n,0) neg_n,COALESCE(pos_n,0) pos_n,COALESCE(zero_n,0) zero_n,COALESCE(null_amount_n,0) null_amount_n
 FROM m LEFT JOIN payment_ticket p USING(CheckId,LocationId,BusinessDate)''')
 check('feature_join_preserves_tickets',q('SELECT COUNT(*) FROM features').first()[0]==2142846)
 report['classification_audit']=rows('''SELECT payment_family,family,COUNT(*) tickets FROM features GROUP BY ALL ORDER BY tickets DESC''')
 check('no_cash_card_flag_conflicts',q("SELECT COUNT(*) FROM features WHERE family='CONFLICTO'").first()[0]==0)
 check('existing_pure_families_preserved',q("SELECT COUNT(*) FROM features WHERE (payment_family IN ('SOLO_EFECTIVO','SOLO_TARJETA') OR family IN ('SOLO_EFECTIVO','SOLO_TARJETA')) AND NOT (payment_family <=> family)").first()[0]==0)
 report['quality_by_family']=rows('''SELECT family,account_status,COUNT(*) tickets,SUM(has_discount) discounted,
 SUM(CASE WHEN neg_n>0 THEN 1 ELSE 0 END) negative_payment_tickets,
 SUM(CASE WHEN pos_n=0 AND zero_n>0 THEN 1 ELSE 0 END) no_positive_payment_tickets,
 SUM(CASE WHEN mismatched_item_lines>0 THEN 1 ELSE 0 END) mismatch_tickets
 FROM features GROUP BY ALL ORDER BY tickets DESC''')
 report['negative_payments']=rows('''SELECT PayCatName,IsCreditCard,COUNT(*) records,SUM(Amount) amount FROM p WHERE Amount<0 GROUP BY ALL ORDER BY records DESC''')
 # Additive daily aggregates permit all rates to be reconstructed as ratios of sums.
 sums=['COUNT(*) n','SUM(has_discount) d',
 'SUM(CASE WHEN neg_n>0 THEN 1 ELSE 0 END) negative_tickets',
 'SUM(CASE WHEN pos_n=0 AND zero_n>0 THEN 1 ELSE 0 END) zero_only_tickets',
 'SUM(CASE WHEN has_discount=1 AND discount_total_raw<=0 THEN 1 ELSE 0 END) positive_application_nonpositive_net']
 for cohort,pred in [('all','true'),('positive','positive_sale'),('strict','strict_sale')]:
  sums.extend([f'SUM(CASE WHEN {pred} THEN 1 ELSE 0 END) {cohort}_n',f'SUM(CASE WHEN {pred} THEN has_discount ELSE 0 END) {cohort}_d',
  f'SUM(CASE WHEN {pred} AND intensity_valid THEN 1 ELSE 0 END) {cohort}_valid_n',
  f'SUM(CASE WHEN {pred} AND intensity_valid THEN discount_total_raw ELSE 0 END) {cohort}_discount',
  f'SUM(CASE WHEN {pred} AND intensity_valid THEN grossprice_sum_unvalidated ELSE 0 END) {cohort}_gross'])
 publish('daily_payment_summary',q('SELECT BusinessDate,LocationId,MAX(location_name) location_name,RevenueCenterId,MAX(channel_name) channel_name,family,'+','.join(sums)+' FROM features GROUP BY BusinessDate,LocationId,RevenueCenterId,family'))
 aggregate_columns=['n','d','negative_tickets','zero_only_tickets','positive_application_nonpositive_net']+[c+'_'+m for c in ['all','positive','strict'] for m in ['n','d','valid_n','discount','gross']]
 def summarize(dims):
  select=','.join(dims)+(',' if dims else '')+','.join(f'SUM({c}) {c}' for c in aggregate_columns)
  return rows('SELECT '+select+' FROM daily_payment_summary'+(' GROUP BY '+','.join(dims) if dims else ''))
 report['global']=summarize(['family']);report['channel']=summarize(['RevenueCenterId','channel_name','family'])
 report['daily']=summarize(['BusinessDate','family']);report['location']=summarize(['LocationId','location_name','family'])
 check('summary_ticket_total',sum(x['n'] for x in report['global'])==2142846)
 check('summary_discounted_total',sum(x['d'] for x in report['global'])==268580)
 report['olo_sensitivity']=rows('''SELECT family_olo_sensitivity family,RevenueCenterId,MAX(channel_name) channel_name,
 COUNT(*) n,SUM(has_discount) d,SUM(CASE WHEN positive_sale THEN 1 ELSE 0 END) positive_n,
 SUM(CASE WHEN positive_sale THEN has_discount ELSE 0 END) positive_d,
 SUM(CASE WHEN positive_sale AND intensity_valid THEN discount_total_raw ELSE 0 END) positive_discount,
 SUM(CASE WHEN positive_sale AND intensity_valid THEN grossprice_sum_unvalidated ELSE 0 END) positive_gross
 FROM features GROUP BY family_olo_sensitivity,RevenueCenterId''')
 persist('standardization')
 # Common-support cells; same pooled ticket weights for both frequency estimates,
 # and same pooled gross weights for both intensity estimates. No p-values or causal claims.
 adjustment=[];coverage=[]
 for level,dims in [('canal',['RevenueCenterId']),('canal_sucursal',['RevenueCenterId','LocationId']),('canal_sucursal_fecha',['RevenueCenterId','LocationId','BusinessDate'])]:
  dimsql=','.join(dims)
  for cohort in ['all','positive','strict']:
   metrics=['n','d','valid_n','discount','gross']
   cols=','.join(f"SUM(CASE WHEN family='{family}' THEN {cohort}_{metric} ELSE 0 END) {alias}_{metric}" for alias,family in [('cash','SOLO_EFECTIVO'),('card','SOLO_TARJETA')] for metric in metrics)
   q('CREATE OR REPLACE TEMP VIEW cells AS SELECT '+dimsql+','+cols+" FROM daily_payment_summary WHERE family IN ('SOLO_EFECTIVO','SOLO_TARJETA') GROUP BY "+dimsql)
   for minimum in [1,5,20]:
    for outcome,numerator,denominator,ncol in [('frequency','d','n','n'),('intensity','discount','gross','valid_n')]:
     condition=f'cash_{ncol}>={minimum} AND card_{ncol}>={minimum} AND cash_{denominator}>0 AND card_{denominator}>0'
     weight=f'(cash_{denominator}+card_{denominator})'
     eligible='SELECT * FROM cells WHERE '+condition
     # Include total scope AND each channel. NULL channel is retained as its own stratum.
     for scope,group in [('total',''),('canal',' GROUP BY RevenueCenterId')]:
      key='RevenueCenterId,' if group else 'CAST(NULL AS BIGINT) RevenueCenterId,'
      query=f'''SELECT {key}COUNT(*) cells,SUM(cash_n) cash_tickets,SUM(card_n) card_tickets,
       SUM({weight}) weight_sum,
       100.0*TRY_DIVIDE(SUM({weight}*TRY_DIVIDE(cash_{numerator},cash_{denominator})),SUM({weight})) cash_standardized_pct,
       100.0*TRY_DIVIDE(SUM({weight}*TRY_DIVIDE(card_{numerator},card_{denominator})),SUM({weight})) card_standardized_pct,
       100.0*TRY_DIVIDE(SUM(cash_{numerator}),SUM(cash_{denominator})) cash_matched_raw_pct,
       100.0*TRY_DIVIDE(SUM(card_{numerator}),SUM(card_{denominator})) card_matched_raw_pct
       FROM ({eligible}) {group}'''
      for row in rows(query):row.update(level=level,cohort=cohort,minimum=minimum,outcome=outcome,scope=scope);adjustment.append(row)
   coverage.extend([dict(row,level=level,cohort=cohort) for row in rows('SELECT RevenueCenterId,SUM(cash_n) cash_n,SUM(card_n) card_n,COUNT(*) strata FROM cells GROUP BY RevenueCenterId')])
 report['adjustment']=adjustment;report['coverage_denominators']=coverage
 # Save compact analysis outputs without copying ticket-level data.
 schema='RevenueCenterId LONG,cells LONG,cash_tickets LONG,card_tickets LONG,weight_sum DOUBLE,cash_standardized_pct DOUBLE,card_standardized_pct DOUBLE,cash_matched_raw_pct DOUBLE,card_matched_raw_pct DOUBLE,level STRING,cohort STRING,minimum INT,outcome STRING,scope STRING'
 names=[x.strip().split()[0] for x in schema.split(',')];numeric=set(names[4:9])
 publish('standardized_comparison',spark.createDataFrame([tuple(float(r[n]) if n in numeric and r.get(n) is not None else r.get(n) for n in names) for r in adjustment],schema))
 persist('discount_types')
 # Discount types overlap: distinct tickets within each type, never summed as unique tickets.
 report['discount_types']=rows('''SELECT f.family,d.discount_scope,d.DiscountId,d.DiscountName,
 COUNT(*) applications,COUNT(DISTINCT struct(d.CheckId,d.LocationId,d.BusinessDate)) tickets,SUM(d.Amount) amount
 FROM d JOIN features f USING(CheckId,LocationId,BusinessDate)
 WHERE f.positive_sale AND f.family IN ('SOLO_EFECTIVO','SOLO_TARJETA') AND d.Amount>0
 GROUP BY ALL ORDER BY amount DESC''')
 report['zero_account_discounts']=rows('''SELECT f.family,d.DiscountId,d.DiscountName,COUNT(*) applications,
 COUNT(DISTINCT struct(d.CheckId,d.LocationId,d.BusinessDate)) tickets,SUM(d.Amount) amount
 FROM d JOIN features f USING(CheckId,LocationId,BusinessDate)
 WHERE f.reconciled AND f.account_candidate<=0 AND f.family='SOLO_EFECTIVO' AND d.Amount>0
 GROUP BY ALL ORDER BY amount DESC''')
 # Summary of recorded gratuity only; never interpret cash zero as no tips.
 report['gratuity_observation']=rows('''SELECT family,COUNT(*) tickets,SUM(gratuity_raw) recorded_gratuity,
 SUM(CASE WHEN gratuity_raw<>0 THEN 1 ELSE 0 END) nonzero_gratuity_tickets FROM features GROUP BY family''')
 check('input_versions_unchanged',current_versions(VERSIONS)==VERSIONS)
 report['protected_after']=current_versions(protected)
 check('protected_25_tables_unchanged',report['protected_after']==report['protected_before'])
 report['status']='PASS';persist('complete')
except Exception as error:
 report.update(status='FAIL',error=str(error),traceback=traceback.format_exc());persist('failed');raise
dbutils.notebook.exit(json.dumps({'status':report['status'],'report':OUT,'schema':DEST}))
