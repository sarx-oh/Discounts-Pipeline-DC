WITH m AS (SELECT * FROM {{ticket_metrics}}),
weekly AS (
 SELECT CAST(date_trunc('WEEK',BusinessDate) AS DATE) week,channel_name,payment_family,
 COUNT(*) all_tickets,COUNT_IF(reconciled AND account_candidate>0) positive_tickets,
 COUNT_IF(reconciled AND account_candidate>0 AND has_discount=1) discounted_positive,
 SUM(CASE WHEN reconciled AND account_candidate>0 THEN discount_total_raw ELSE 0 END) discount_amount,
 SUM(CASE WHEN reconciled AND account_candidate>0 AND discount_denominator_valid THEN discount_total_raw ELSE 0 END) intensity_numerator,
 SUM(CASE WHEN reconciled AND account_candidate>0 AND discount_denominator_valid THEN grossprice_sum_unvalidated ELSE 0 END) intensity_denominator,
 COUNT(DISTINCT BusinessDate) days
 FROM m GROUP BY CAST(date_trunc('WEEK',BusinessDate) AS DATE),channel_name,payment_family
), types AS (
 SELECT CAST(date_trunc('WEEK',BusinessDate) AS DATE) week,DiscountId,DiscountName,discount_scope,
 COUNT(*) events,COUNT(DISTINCT struct(CheckId,LocationId,BusinessDate)) tickets,SUM(Amount) amount
 FROM {{discounts}} WHERE Amount>0
 GROUP BY CAST(date_trunc('WEEK',BusinessDate) AS DATE),DiscountId,DiscountName,discount_scope
)
SELECT 'weekly' section,to_json(collect_list(struct(*))) payload FROM weekly
UNION ALL SELECT 'types',to_json(collect_list(struct(*))) FROM types
