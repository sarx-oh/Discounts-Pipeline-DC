WITH d AS (SELECT * FROM {{discounts}} WHERE Amount>0),
ticket_counts AS (
 SELECT CheckId,LocationId,BusinessDate,COUNT(*) events,
 COUNT(DISTINCT DiscountId) types, SUM(Amount) total_discount
 FROM d GROUP BY CheckId,LocationId,BusinessDate
), targets AS (
 SELECT d.*, t.events,t.types,t.total_discount
 FROM d JOIN ticket_counts t USING(CheckId,LocationId,BusinessDate)
 WHERE DiscountId IN (518,520,523,65)
), summary AS (
 SELECT DiscountId,DiscountName,discount_scope,
 COUNT(*) target_events,COUNT(DISTINCT struct(CheckId,LocationId,BusinessDate)) target_tickets,
 COUNT(DISTINCT CASE WHEN events>1 THEN struct(CheckId,LocationId,BusinessDate) END) tickets_multiple_events,
 COUNT(DISTINCT CASE WHEN types>1 THEN struct(CheckId,LocationId,BusinessDate) END) tickets_other_type,
 SUM(Amount) target_amount
 FROM targets GROUP BY DiscountId,DiscountName,discount_scope
), pairs AS (
 SELECT t.DiscountId target_id,t.discount_scope target_scope,d.DiscountId other_id,
 d.DiscountName other_name,d.discount_scope other_scope,
 COUNT(DISTINCT struct(t.CheckId,t.LocationId,t.BusinessDate)) tickets,
 COUNT(DISTINCT CASE WHEN t.discount_scope='ticket' OR d.discount_scope='ticket' OR t.item_pos=d.item_pos
 THEN struct(t.CheckId,t.LocationId,t.BusinessDate) END) overlapping_scope_tickets
 FROM targets t JOIN d ON t.CheckId=d.CheckId AND t.LocationId=d.LocationId AND t.BusinessDate=d.BusinessDate
 WHERE t.DiscountId<>d.DiscountId
 GROUP BY t.DiscountId,t.discount_scope,d.DiscountId,d.DiscountName,d.discount_scope
), attribution AS (
 SELECT COUNT(*) positive_events,
 COUNT_IF(d.EmployeeId=m.payment_employee_id) discount_employee_matches_payment,
 COUNT_IF(d.EmployeeId<>m.payment_employee_id) discount_employee_differs_payment,
 COUNT_IF(m.payment_employee_id IS NULL) no_unique_payment_employee
 FROM d JOIN {{ticket_metrics}} m USING(CheckId,LocationId,BusinessDate)
)
SELECT 'target_summary' section,to_json(collect_list(struct(*))) payload FROM summary
UNION ALL SELECT 'pairs',to_json(collect_list(struct(*))) FROM pairs
UNION ALL SELECT 'attribution',to_json(collect_list(struct(*))) FROM attribution
