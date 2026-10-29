-- Existing residue 0 sample enriched for retrospective investigation.
-- Reserved residue 19 is intentionally excluded from this exploration.
WITH m AS (
 SELECT * FROM {{ticket_metrics}}
 WHERE reconciled AND account_candidate>0 AND discount_denominator_valid
 AND negative_payment_records=0 AND pmod(xxhash64(CheckId,LocationId,BusinessDate),20)=0
 AND {{period_filter}}
), p AS (
 SELECT p.CheckId,p.LocationId,p.BusinessDate,
 COUNT_IF(p.Gratuity IS NULL) missing_tip_rows,COUNT_IF(p.Gratuity>0) positive_tip_rows,
 MAX(CASE WHEN UPPER(p.PayCatName)='CASH' THEN 1 ELSE 0 END) cash,
 MAX(CASE WHEN p.IsCreditCard THEN 1 ELSE 0 END) card,
 MAX(CASE WHEN NOT COALESCE(p.IsCreditCard,false) AND COALESCE(UPPER(p.PayCatName),'UNKNOWN')<>'CASH' THEN 1 ELSE 0 END) other,
 MAX(CASE WHEN p.Amount>0 AND UPPER(p.PayCatName)='CASH' THEN 1 ELSE 0 END) positive_cash,
 MAX(CASE WHEN p.Amount>0 AND p.IsCreditCard THEN 1 ELSE 0 END) positive_card
 FROM {{payments}} p JOIN m USING(CheckId,LocationId,BusinessDate) GROUP BY ALL
), cats AS (
 SELECT i.CheckId,i.LocationId,i.BusinessDate,COALESCE(i.ItemMajorCatName,'UNKNOWN') category,
 SUM(i.GrossPrice) gross_category,COUNT(*) category_lines
 FROM {{items_sold}} i JOIN m USING(CheckId,LocationId,BusinessDate) GROUP BY ALL
), products AS (
 SELECT CheckId,LocationId,BusinessDate,COUNT(*) category_count,
 max_by(category,struct(gross_category,category)) dominant_category,
 MAX(gross_category) dominant_category_gross
 FROM cats GROUP BY ALL
), disc AS (
 SELECT d.CheckId,d.LocationId,d.BusinessDate,
 COUNT_IF(d.Amount>0) positive_discount_events,COUNT(DISTINCT CASE WHEN d.Amount>0 THEN d.DiscountId END) discount_types,
 concat_ws('|',sort_array(collect_set(CASE WHEN d.Amount>0 THEN CAST(d.DiscountId AS STRING) END))) discount_ids,
 MAX(CASE WHEN d.Amount>0 AND d.DiscountId IN (518,520,523) THEN 1 ELSE 0 END) emp50_present,
 COUNT(DISTINCT CASE WHEN d.Amount>0 AND d.ManagerId>0 THEN d.ManagerId END) manager_count,
 sha2(concat('deep-manager:',CAST(MAX(CASE WHEN d.Amount>0 AND d.ManagerId>0 THEN d.ManagerId END) AS STRING)),256) candidate_manager_key
 FROM {{discounts}} d JOIN m USING(CheckId,LocationId,BusinessDate) GROUP BY ALL
)
SELECT sha2(concat_ws(':',CAST(m.CheckId AS STRING),CAST(m.LocationId AS STRING),CAST(m.BusinessDate AS STRING)),256) ticket_key,
 m.BusinessDate,m.LocationId,COALESCE(m.channel_name,'UNKNOWN') channel_name,m.payment_family,
 sha2(concat('applebees-review-v1:',CAST(m.payment_employee_id AS STRING)),256) employee_key,
 hour(m.open_local) open_hour,dayofweek(m.BusinessDate) day_of_week,
 m.TrafficCount,m.item_line_count,CAST(m.grossprice_sum_unvalidated AS DOUBLE) gross,
 m.has_discount,CAST(m.discount_total_raw AS DOUBLE) discount_amount,CAST(m.discount_pct/100 AS DOUBLE) discount_ratio,
 m.mismatched_item_lines,m.unassessable_item_lines,
 CAST(m.account_candidate AS DOUBLE) final_account,CAST(m.net_sales_candidate AS DOUBLE) net_sales,
 CAST(m.gratuity_raw AS DOUBLE) gratuity_raw,p.missing_tip_rows,p.positive_tip_rows,
 concat(p.cash,p.card,p.other) payment_bits,p.positive_cash,p.positive_card,
 products.category_count,products.dominant_category,
 CAST(products.dominant_category_gross/m.grossprice_sum_unvalidated AS DOUBLE) dominant_category_share,
 m.void_count,COALESCE(disc.positive_discount_events,0) positive_discount_events,
 COALESCE(disc.discount_types,0) discount_types,disc.discount_ids,COALESCE(disc.emp50_present,0) emp50_present,
 COALESCE(disc.manager_count,0) manager_count,
 CASE WHEN disc.manager_count=1 THEN disc.candidate_manager_key END unique_manager_key
FROM m LEFT JOIN p USING(CheckId,LocationId,BusinessDate)
LEFT JOIN products USING(CheckId,LocationId,BusinessDate)
LEFT JOIN disc USING(CheckId,LocationId,BusinessDate)
