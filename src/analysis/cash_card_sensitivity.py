# Databricks notebook source
"""Sensitivity to zero-value payment markers, OLO labels and employee-labelled discounts."""
import json,time
from pyspark.sql import functions as F
PREFIX='applebees_test_0eef22876f8b';S=f'workspace.{PREFIX}_silver';G=f'workspace.{PREFIX}_gold'
OUT=dbutils.widgets.get('output_path');V=json.loads(dbutils.widgets.get('input_versions'));PROTECTED=json.loads(dbutils.widgets.get('protected_versions'))
assert OUT.startswith(f'/Volumes/workspace/{PREFIX}_bronze/raw/analysis_cash_card_') and '..' not in OUT
assert set(V)=={G+'.ticket_metrics',S+'.payments',S+'.discounts'}
def versions(tables):return {t:int(spark.sql(f'DESCRIBE HISTORY {t} LIMIT 1').first().version) for t in tables}
assert versions(V)==V
for alias,t in [('m',G+'.ticket_metrics'),('p',S+'.payments'),('d',S+'.discounts')]:spark.read.option('versionAsOf',V[t]).table(t).createOrReplaceTempView(alias)
def q(sql):return spark.sql(sql)
def rows(sql):return [r.asDict(recursive=True) for r in q(sql).collect()]
q('''CREATE OR REPLACE TEMP VIEW pt AS SELECT CheckId,LocationId,BusinessDate,COUNT(*) n,
 SUM(CASE WHEN Amount>0 THEN 1 ELSE 0 END) pn,
 SUM(CASE WHEN Amount<0 THEN 1 ELSE 0 END) neg,
 SUM(CASE WHEN Amount IS NULL THEN 1 ELSE 0 END) nulls,
 SUM(CASE WHEN Amount>0 AND UPPER(TRIM(PayCatName))='CASH' THEN 1 ELSE 0 END) pcash,
 SUM(CASE WHEN Amount>0 AND IsCreditCard=true THEN 1 ELSE 0 END) pcard,
 SUM(CASE WHEN IsCreditCard=true OR UPPER(TRIM(PayCatName)) IN ('OLO-VISA','OLO-MASTERCARD','OLO-DISCOVER','OLO-AMEX') THEN 1 ELSE 0 END) olo_card,
 SUM(CASE WHEN Amount>0 AND (IsCreditCard=true OR UPPER(TRIM(PayCatName)) IN ('OLO-VISA','OLO-MASTERCARD','OLO-DISCOVER','OLO-AMEX')) THEN 1 ELSE 0 END) polo_card
 FROM p GROUP BY ALL''')
q('''CREATE OR REPLACE TEMP VIEW dt AS SELECT CheckId,LocationId,BusinessDate,
 MAX(CASE WHEN Amount>0 AND UPPER(TRIM(DiscountName)) IN ('EMP 50','EMP 50%') THEN 1 ELSE 0 END) emp50,
 MAX(CASE WHEN Amount>0 AND UPPER(TRIM(DiscountName)) LIKE 'EMP %' THEN 1 ELSE 0 END) emp_label
 FROM d GROUP BY ALL''')
q('''CREATE OR REPLACE TEMP VIEW f AS SELECT m.*,
 CASE WHEN pn=0 THEN 'SIN_COBRO_POSITIVO' WHEN pcash=pn THEN 'SOLO_EFECTIVO' WHEN pcard=pn THEN 'SOLO_TARJETA' ELSE 'OTROS_O_MIXTOS' END active_family,
 CASE WHEN payment_family='SOLO_EFECTIVO' THEN 'SOLO_EFECTIVO' WHEN olo_card=n THEN 'SOLO_TARJETA' ELSE 'OTROS_O_MIXTOS' END olo_family,
 CASE WHEN pn=0 THEN 'SIN_COBRO_POSITIVO' WHEN pcash=pn THEN 'SOLO_EFECTIVO' WHEN polo_card=pn THEN 'SOLO_TARJETA' ELSE 'OTROS_O_MIXTOS' END active_olo_family,
 COALESCE(emp50,0) emp50,COALESCE(emp_label,0) emp_label,
 COALESCE(m.reconciled AND m.account_candidate>0 AND pt.neg=0 AND pt.nulls=0 AND pt.pn>0,false) positive_sale
 FROM m LEFT JOIN pt USING(CheckId,LocationId,BusinessDate) LEFT JOIN dt USING(CheckId,LocationId,BusinessDate)''')
report={'status':'RUNNING','input_versions':V,'payment_transition':rows('''SELECT payment_family,active_family,COUNT(*) tickets,SUM(CASE WHEN positive_sale THEN 1 ELSE 0 END) positive_tickets FROM f GROUP BY ALL ORDER BY tickets DESC'''),
'employee_label_codes':rows("SELECT DISTINCT DiscountId,DiscountName FROM d WHERE UPPER(TRIM(DiscountName)) LIKE 'EMP %' ORDER BY DiscountId")}
q('''CREATE OR REPLACE TEMP VIEW variants AS SELECT f.*,scenario,family FROM f
 LATERAL VIEW STACK(6,'primary',payment_family,'positive_payments_only',active_family,'olo_labels',olo_family,
 'positive_payments_and_olo',active_olo_family,'without_emp50',CASE WHEN emp50=0 THEN payment_family END,
 'without_emp_labels',CASE WHEN emp_label=0 THEN payment_family END) v AS scenario,family
 WHERE positive_sale''')
q('''CREATE OR REPLACE TEMP VIEW aggregate_cells AS SELECT scenario,RevenueCenterId,LocationId,BusinessDate,family,
 COUNT(*) n,SUM(has_discount) d,
 SUM(CASE WHEN discount_denominator_valid THEN discount_total_raw ELSE 0 END) discount,
 SUM(CASE WHEN discount_denominator_valid THEN grossprice_sum_unvalidated ELSE 0 END) gross,
 SUM(CASE WHEN discount_denominator_valid THEN 1 ELSE 0 END) valid_n
 FROM variants WHERE family IN ('SOLO_EFECTIVO','SOLO_TARJETA') GROUP BY ALL''')
report['global']=rows('SELECT scenario,family,SUM(n) n,SUM(d) d,SUM(discount) discount,SUM(gross) gross FROM aggregate_cells GROUP BY ALL')
q('''CREATE OR REPLACE TEMP VIEW cells AS SELECT scenario,RevenueCenterId,LocationId,BusinessDate,
 SUM(CASE WHEN family='SOLO_EFECTIVO' THEN n ELSE 0 END) cn,
 SUM(CASE WHEN family='SOLO_TARJETA' THEN n ELSE 0 END) tn,
 SUM(CASE WHEN family='SOLO_EFECTIVO' THEN d ELSE 0 END) cd,
 SUM(CASE WHEN family='SOLO_TARJETA' THEN d ELSE 0 END) td,
 SUM(CASE WHEN family='SOLO_EFECTIVO' THEN discount ELSE 0 END) ca,
 SUM(CASE WHEN family='SOLO_TARJETA' THEN discount ELSE 0 END) ta,
 SUM(CASE WHEN family='SOLO_EFECTIVO' THEN gross ELSE 0 END) cg,
 SUM(CASE WHEN family='SOLO_TARJETA' THEN gross ELSE 0 END) tg,
 SUM(CASE WHEN family='SOLO_EFECTIVO' THEN valid_n ELSE 0 END) cv,
 SUM(CASE WHEN family='SOLO_TARJETA' THEN valid_n ELSE 0 END) tv
 FROM aggregate_cells GROUP BY ALL''')
report['adjusted_frequency']=rows('''SELECT scenario,COUNT(*) cells,SUM(cn) cash_n,SUM(tn) card_n,
 100.0*SUM((cn+tn)*TRY_DIVIDE(cd,cn))/SUM(cn+tn) cash_pct,
 100.0*SUM((cn+tn)*TRY_DIVIDE(td,tn))/SUM(cn+tn) card_pct
 FROM cells WHERE cn>=5 AND tn>=5 GROUP BY scenario''')
report['adjusted_intensity']=rows('''SELECT scenario,COUNT(*) cells,
 100.0*TRY_DIVIDE(SUM((cg+tg)*TRY_DIVIDE(ca,cg)),SUM(cg+tg)) cash_pct,
 100.0*TRY_DIVIDE(SUM((cg+tg)*TRY_DIVIDE(ta,tg)),SUM(cg+tg)) card_pct
 FROM cells WHERE cv>=5 AND tv>=5 AND cg>0 AND tg>0 GROUP BY scenario''')
assert versions(V)==V
report['input_versions_unchanged']=True
report['protected_tables_unchanged']=versions(PROTECTED)==PROTECTED
assert report['protected_tables_unchanged']
report['status']='PASS';dbutils.fs.put(OUT,json.dumps(report,default=str),True)
dbutils.notebook.exit(json.dumps({'status':'PASS','report':OUT}))
