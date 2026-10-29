-- Recorded manager/employee associations; manager opportunity is unobserved on non-discount tickets.
WITH m AS (SELECT * FROM {{ticket_metrics}}), d AS (
 SELECT d.* FROM {{discounts}} d WHERE Amount>0
), pair AS (
 SELECT LocationId,EmployeeId,ManagerId,COUNT(*) events,COUNT(DISTINCT struct(CheckId,LocationId,BusinessDate)) tickets
 FROM d GROUP BY ALL
), employees AS (
 SELECT LocationId,EmployeeId,SUM(events) events,COUNT_IF(ManagerId>0) recorded_managers,
 MAX(events)/SUM(events) largest_pair_share,SUM(CASE WHEN ManagerId=EmployeeId THEN events ELSE 0 END) same_id_events
 FROM pair WHERE EmployeeId>0 GROUP BY ALL HAVING SUM(events)>=30
), concentrations AS (
 SELECT COUNT(*) employee_location_profiles,SUM(events) events,
 COUNT_IF(recorded_managers=1) one_recorded_manager,
 COUNT_IF(largest_pair_share>=.9) largest_pair_at_least_90pct,
 SUM(same_id_events) employee_manager_same_id_events FROM employees
), amounts AS (
 SELECT DiscountId,DiscountName,discount_scope,Amount,COUNT(*) events FROM d GROUP BY ALL
), repetition AS (
 SELECT DiscountId,DiscountName,discount_scope,SUM(events) events,COUNT(*) distinct_amounts,
 max_by(Amount,struct(events,Amount)) most_common_amount,MAX(events)/SUM(events) modal_amount_share
 FROM amounts GROUP BY ALL HAVING SUM(events)>=100
), type_tickets AS (
 SELECT DISTINCT CheckId,LocationId,BusinessDate,DiscountId,DiscountName,discount_scope FROM d
), tips AS (
 SELECT t.DiscountId,t.DiscountName,t.discount_scope,COUNT(*) tickets,
 AVG(m.tip_amount_interpreted) mean_recorded_tip,
 AVG(m.tip_amount_interpreted/m.grossprice_sum_unvalidated) mean_tip_gross_rate,
 AVG(m.tip_amount_interpreted/m.account_candidate) mean_tip_account_rate,
 AVG(m.discount_pct) mean_discount_pct,
 COUNT_IF(m.tip_amount_interpreted=0) zero_recorded_tips,
 COUNT_IF(m.void_count>0) tickets_with_voids
 FROM type_tickets t JOIN m USING(CheckId,LocationId,BusinessDate)
 WHERE m.tip_comparable AND m.negative_payment_records=0 AND m.account_candidate>=5 AND m.discount_denominator_valid
 GROUP BY ALL HAVING COUNT(*)>=100
), voids AS (
 SELECT m.payment_family,m.account_status,m.has_discount,COUNT(*) tickets,
 COUNT_IF(m.void_count>0) tickets_with_voids,SUM(m.void_count) void_events
 FROM m GROUP BY ALL
), example_base AS (
 SELECT m.CheckId,m.LocationId,m.BusinessDate,m.channel_name,m.payment_family,m.account_candidate,
 m.grossprice_sum_unvalidated,m.discount_total_raw,m.tip_amount_interpreted,m.void_count,
 concat_ws('|',sort_array(collect_set(CAST(d.DiscountId AS STRING)))) discount_ids,
 COUNT(DISTINCT d.DiscountId) discount_types,MAX(CASE WHEN d.DiscountId IN (518,520,523) THEN 1 ELSE 0 END) emp50
 FROM m JOIN d USING(CheckId,LocationId,BusinessDate) GROUP BY ALL
), examples AS (
 SELECT * FROM example_base WHERE emp50=1 AND discount_types>1 ORDER BY LocationId,BusinessDate,CheckId LIMIT 10
)
SELECT 'manager_concentration' section,to_json(collect_list(struct(*))) payload FROM concentrations
UNION ALL SELECT 'repeated_amounts',to_json(collect_list(struct(*))) FROM repetition
UNION ALL SELECT 'discount_type_tips',to_json(collect_list(struct(*))) FROM tips
UNION ALL SELECT 'void_context',to_json(collect_list(struct(*))) FROM voids
UNION ALL SELECT 'private_policy_examples',to_json(collect_list(struct(*))) FROM examples
