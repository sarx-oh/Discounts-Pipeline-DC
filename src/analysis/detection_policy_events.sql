-- Full positive-event evidence on provisional EMP50 combination candidates.
WITH d AS (SELECT * FROM {{discounts}}), selected AS (
 SELECT CheckId,LocationId,BusinessDate FROM d WHERE Amount>0
 GROUP BY ALL HAVING COUNT(DISTINCT DiscountId)>1 AND
 MAX(CASE WHEN DiscountId IN (518,520,523) THEN 1 ELSE 0 END)=1
)
SELECT sha2(concat_ws(':',CAST(d.CheckId AS STRING),CAST(d.LocationId AS STRING),CAST(d.BusinessDate AS STRING)),256) ticket_key,
 d.CheckId,d.LocationId,d.BusinessDate,d.discount_scope,d.item_pos,d.discount_pos,
 d.DiscountId,d.DiscountName,CAST(d.Amount AS DOUBLE) Amount,
 m.channel_name,m.payment_family,CAST(m.grossprice_sum_unvalidated AS DOUBLE) gross,
 CAST(m.discount_total_raw AS DOUBLE) discount_amount,CAST(m.account_candidate AS DOUBLE) final_account,
 m.account_status,m.has_discount,m.void_count
FROM d JOIN selected USING(CheckId,LocationId,BusinessDate)
JOIN {{ticket_metrics}} m USING(CheckId,LocationId,BusinessDate) WHERE d.Amount>0
