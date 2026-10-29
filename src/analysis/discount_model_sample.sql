-- Deterministic approximately 5% sample; target prevalence is not resampled.
-- Predictors describe the ticket context. Discount fields below are targets only.
-- Employee key supports grouped diagnostics, not a predictor of misconduct.
SELECT sha2(concat_ws(':',CAST(CheckId AS STRING),CAST(LocationId AS STRING),CAST(BusinessDate AS STRING)),256) ticket_key,
 BusinessDate,
 CASE WHEN BusinessDate<DATE'2026-07-01' THEN 'train'
      WHEN BusinessDate<DATE'2026-07-26' THEN 'validation' ELSE 'test' END temporal_split,
 LocationId,COALESCE(channel_name,'UNKNOWN') channel_name,
 COALESCE(payment_family,'UNKNOWN') payment_family,
 sha2(concat('applebees-review-v1:',CAST(payment_employee_id AS STRING)),256) employee_key,
 hour(open_local) open_hour,dayofweek(BusinessDate) day_of_week,
 TrafficCount,item_line_count,CAST(grossprice_sum_unvalidated AS DOUBLE) gross,
 has_discount,CAST(discount_total_raw AS DOUBLE) discount_amount,
 CAST(discount_pct/100.0 AS DOUBLE) discount_ratio,
 mismatched_item_lines,unassessable_item_lines
FROM {{ticket_metrics}}
WHERE reconciled AND account_candidate>0 AND discount_denominator_valid
 AND negative_payment_records=0
 AND pmod(xxhash64(CheckId,LocationId,BusinessDate),20)=0
