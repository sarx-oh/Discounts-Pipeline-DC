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
), employee AS (
 SELECT sha2(concat('applebees-review-v1:',CAST(payment_employee_id AS STRING)),256) employee_key,
 LocationId,COUNT(*) comparable_cells,COUNT(DISTINCT week) weeks,SUM(n) tickets,
 SUM(y) discounted,SUM(expected) expected_discounted,SUM(amount) amount,SUM(expected_amount) expected_amount,
 SUM(y)-SUM(expected) excess_count,SUM(amount)-SUM(expected_amount) excess_amount,
 SUM(CASE WHEN try_divide(y,n)>try_divide(peer_y,peer_n)+0.10 THEN 1 ELSE 0 END) cells_above_10pp,
 MIN(week) first_week,MAX(week) last_week
 FROM scored GROUP BY payment_employee_id,LocationId
), flagged AS (
 SELECT * FROM employee WHERE weeks>=4 AND tickets>=200 AND excess_count/tickets>0.10
), trends AS (
 SELECT *,try_divide(y,n)-try_divide(peer_y,peer_n) excess_rate,
 LAG(week) OVER w previous_week,LAG(n) OVER w previous_n,
 LAG(try_divide(y,n)-try_divide(peer_y,peer_n)) OVER w previous_excess_rate
 FROM scored WHERE week BETWEEN DATE'2026-05-04' AND DATE'2026-08-10'
 WINDOW w AS (PARTITION BY payment_employee_id,LocationId,channel_name,payment_family ORDER BY week)
), changes AS (
 SELECT sha2(concat('applebees-review-v1:',CAST(payment_employee_id AS STRING)),256) employee_key,
 LocationId,channel_name,payment_family,week,n,y,peer_n,excess_rate,previous_excess_rate,
 excess_rate-previous_excess_rate excess_rate_change
 FROM trends WHERE datediff(week,previous_week)=7 AND excess_rate-previous_excess_rate>0.15
), mix AS (
 SELECT d.DiscountId,d.DiscountName,d.discount_scope,
 COUNT(*) events,COUNT(DISTINCT struct(d.CheckId,d.LocationId,d.BusinessDate)) tickets,
 SUM(d.Amount) amount
 FROM {{discounts}} d JOIN flagged f ON d.LocationId=f.LocationId
 AND sha2(concat('applebees-review-v1:',CAST(d.EmployeeId AS STRING)),256)=f.employee_key
 WHERE d.Amount>0 GROUP BY d.DiscountId,d.DiscountName,d.discount_scope
), change_summary AS (
 SELECT COUNT(*) jumps,COUNT(DISTINCT employee_key) employees,
 COUNT(DISTINCT LocationId) locations FROM changes
), top_changes AS (SELECT * FROM changes ORDER BY excess_rate_change DESC LIMIT 30)
SELECT 'flagged_profiles' section,to_json(collect_list(struct(*))) payload FROM flagged
UNION ALL SELECT 'flagged_discount_mix',to_json(collect_list(struct(*))) FROM mix
UNION ALL SELECT 'temporal_jumps',to_json(collect_list(struct(*))) FROM change_summary
UNION ALL SELECT 'largest_jumps',to_json(collect_list(struct(*))) FROM top_changes
