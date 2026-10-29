-- Descriptive comparison with same-week peers; not a prospective prediction.
WITH eligible AS (
 SELECT *,CAST(date_trunc('WEEK',BusinessDate) AS DATE) week
 FROM {{ticket_metrics}}
 WHERE reconciled AND account_candidate>0 AND payment_employee_id>0
 AND negative_payment_records=0 AND discount_denominator_valid
), cells AS (
 SELECT payment_employee_id,LocationId,channel_name,payment_family,week,
 COUNT(*) n,SUM(has_discount) y,SUM(discount_total_raw) amount,
 SUM(grossprice_sum_unvalidated) gross,COUNT(DISTINCT BusinessDate) active_days
 FROM eligible GROUP BY payment_employee_id,LocationId,channel_name,payment_family,week
), peers AS (
 SELECT *,(SUM(n) OVER w) - n peer_n,(SUM(y) OVER w) - y peer_y,
 (SUM(amount) OVER w) - amount peer_amount,(SUM(gross) OVER w) - gross peer_gross
 FROM cells WINDOW w AS (PARTITION BY LocationId,channel_name,payment_family,week)
), scored AS (
 SELECT *,n*try_divide(peer_y,peer_n) expected,
 gross*try_divide(peer_amount,peer_gross) expected_amount
 FROM peers WHERE n>=30 AND peer_n>=100
)
SELECT sha2(concat('applebees-review-v1:',CAST(payment_employee_id AS STRING)),256) employee_key,
 LocationId,week,SUM(n) tickets,SUM(y) discounted,SUM(expected) expected_discounted,
 COUNT(*) supported_cells,SUM(amount) discount_amount,SUM(expected_amount) expected_discount_amount
 FROM scored GROUP BY payment_employee_id,LocationId,week
