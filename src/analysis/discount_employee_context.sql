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
), coverage AS (
 SELECT (SELECT COUNT(*) FROM eligible) eligible_tickets,
 (SELECT COUNT(DISTINCT payment_employee_id) FROM eligible) eligible_employees,
 (SELECT SUM(n) FROM scored) comparable_tickets,
 (SELECT COUNT(*) FROM scored) comparable_cells,
 (SELECT COUNT(*) FROM employee) employee_location_profiles,
 (SELECT COUNT(*) FROM employee WHERE weeks>=4 AND tickets>=200) stable_support_profiles
), high AS (
 SELECT * FROM employee WHERE weeks>=4 AND tickets>=200 ORDER BY excess_count DESC LIMIT 30
), ordinary AS (
 SELECT * FROM employee WHERE weeks>=4 AND tickets>=200
 AND ABS(try_divide(discounted-expected_discounted,tickets))<=0.02
 ORDER BY tickets DESC LIMIT 30
), distribution AS (
 SELECT COUNT(*) profiles,
 COUNT_IF(weeks>=4 AND tickets>=200 AND excess_count/tickets>0.10) above_10pp,
 COUNT_IF(weeks>=4 AND tickets>=200 AND ABS(excess_count/tickets)<=0.02) within_2pp
 FROM employee
)
SELECT 'coverage' section,to_json(collect_list(struct(*))) payload FROM coverage
UNION ALL SELECT 'high_review_candidates',to_json(collect_list(struct(*))) FROM high
UNION ALL SELECT 'compatible_with_peer_frequency',to_json(collect_list(struct(*))) FROM ordinary
UNION ALL SELECT 'distribution',to_json(collect_list(struct(*))) FROM distribution
