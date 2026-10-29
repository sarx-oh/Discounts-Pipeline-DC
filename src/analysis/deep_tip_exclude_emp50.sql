-- Recorded gratuity only; cash zeros do not measure actual cash tipping.
WITH p AS (
 SELECT CheckId,LocationId,BusinessDate,COUNT(*) payment_rows,
 COUNT_IF(Gratuity IS NULL) missing_tip_rows,COUNT_IF(Gratuity>0) positive_tip_rows,
 MAX(CASE WHEN UPPER(PayCatName)='CASH' THEN 1 ELSE 0 END) cash,
 MAX(CASE WHEN IsCreditCard THEN 1 ELSE 0 END) card,
 MAX(CASE WHEN NOT COALESCE(IsCreditCard,false) AND COALESCE(UPPER(PayCatName),'UNKNOWN')<>'CASH' THEN 1 ELSE 0 END) other
 FROM {{payments}} GROUP BY CheckId,LocationId,BusinessDate
), base AS (
 SELECT m.*,p.missing_tip_rows,p.positive_tip_rows,
 concat(COALESCE(p.cash,0),COALESCE(p.card,0),COALESCE(p.other,0)) payment_bits,
 CAST(date_trunc('WEEK',m.BusinessDate) AS DATE) week,
 CASE WHEN p.missing_tip_rows=0 AND p.positive_tip_rows=0 AND m.gratuity_raw<=0 THEN -m.gratuity_raw END recorded_tip,
 CASE WHEN m.grossprice_sum_unvalidated<15 THEN 0 WHEN m.grossprice_sum_unvalidated<30 THEN 1
 WHEN m.grossprice_sum_unvalidated<50 THEN 2 WHEN m.grossprice_sum_unvalidated<80 THEN 3 ELSE 4 END gross_band
 FROM {{ticket_metrics}} m LEFT JOIN p USING(CheckId,LocationId,BusinessDate)
 WHERE NOT EXISTS (SELECT 1 FROM {{discounts}} d WHERE d.CheckId=m.CheckId AND d.LocationId=m.LocationId AND d.BusinessDate=m.BusinessDate AND d.Amount>0 AND d.DiscountId IN (518,520,523))
), summary AS (
 SELECT payment_bits,channel_name,account_status,has_discount,
 COUNT(*) tickets,COUNT(recorded_tip) tip_observed_tickets,
 COUNT_IF(recorded_tip=0) zero_recorded_tip_tickets,COUNT_IF(recorded_tip>0) positive_recorded_tip_tickets,
 COUNT_IF(missing_tip_rows>0) partial_tip_tickets,
 SUM(recorded_tip) tip_amount,SUM(CASE WHEN recorded_tip IS NOT NULL THEN grossprice_sum_unvalidated END) gross_same_tip_population,
 SUM(CASE WHEN recorded_tip IS NOT NULL THEN account_candidate END) account_same_tip_population,
 AVG(CASE WHEN grossprice_sum_unvalidated>0 THEN recorded_tip/grossprice_sum_unvalidated END) mean_tip_gross_rate,
 AVG(CASE WHEN account_candidate>0 THEN recorded_tip/account_candidate END) mean_tip_account_rate,
 COUNT_IF(account_candidate<=0) nonpositive_accounts,
 COUNT_IF(discount_pct>=99.99) fully_discounted_tickets
 FROM base GROUP BY ALL
), thresholds AS (SELECT explode(array(0,5,10,20)) minimum_account), cells AS (
 SELECT minimum_account,LocationId,week,payment_employee_id,channel_name,gross_band,
 COUNT_IF(has_discount=1) nd,COUNT_IF(has_discount=0) nn,
 SUM(CASE WHEN has_discount=1 THEN recorded_tip ELSE 0 END) td,
 SUM(CASE WHEN has_discount=0 THEN recorded_tip ELSE 0 END) tn,
 SUM(CASE WHEN has_discount=1 THEN recorded_tip/grossprice_sum_unvalidated ELSE 0 END) gd,
 SUM(CASE WHEN has_discount=0 THEN recorded_tip/grossprice_sum_unvalidated ELSE 0 END) gn,
 SUM(CASE WHEN has_discount=1 THEN recorded_tip/account_candidate ELSE 0 END) ad,
 SUM(CASE WHEN has_discount=0 THEN recorded_tip/account_candidate ELSE 0 END) an
 FROM base CROSS JOIN thresholds WHERE account_candidate>=minimum_account AND payment_bits='010' AND reconciled AND account_candidate>0
 AND discount_denominator_valid AND negative_payment_records=0 AND recorded_tip IS NOT NULL
 AND payment_employee_id>0
 GROUP BY ALL
), contrasts AS (
 SELECT minimum_account,LocationId,week,SUM(nd+nn) eligible_tickets,
 SUM(CASE WHEN nd>=2 AND nn>=2 THEN nd+nn ELSE 0 END) comparable_tickets,
 SUM(CASE WHEN nd>=2 AND nn>=2 THEN (nd+nn)*(td/nd-tn/nn) ELSE 0 END) weighted_amount_difference,
 SUM(CASE WHEN nd>=2 AND nn>=2 THEN (nd+nn)*(gd/nd-gn/nn) ELSE 0 END) weighted_gross_rate_difference,
 SUM(CASE WHEN nd>=2 AND nn>=2 THEN (nd+nn)*(ad/nd-an/nn) ELSE 0 END) weighted_account_rate_difference
 FROM cells GROUP BY ALL
)
SELECT 'summary' section,to_json(collect_list(struct(*))) payload FROM summary
UNION ALL SELECT 'within_employee_contrasts',to_json(collect_list(struct(*))) FROM contrasts
