-- Common-support contrasts within employee/location/week/channel and final basket context.
-- Aggregate location/week output supports clustered uncertainty without exporting IDs.
WITH base AS (
 SELECT *,CAST(date_trunc('WEEK',BusinessDate) AS DATE) week,
 CASE WHEN grossprice_sum_unvalidated<15 THEN 0 WHEN grossprice_sum_unvalidated<30 THEN 1
 WHEN grossprice_sum_unvalidated<50 THEN 2 WHEN grossprice_sum_unvalidated<80 THEN 3 ELSE 4 END gross_band,
 CASE WHEN hour(open_local)<11 THEN 0 WHEN hour(open_local)<16 THEN 1 WHEN hour(open_local)<21 THEN 2 ELSE 3 END daypart,
 CASE WHEN item_line_count<=3 THEN 0 WHEN item_line_count<=6 THEN 1 ELSE 2 END line_band
 FROM {{ticket_metrics}}
 WHERE reconciled AND account_candidate>0 AND discount_denominator_valid
 AND negative_payment_records=0 AND payment_employee_id>0
 AND payment_family IN ('SOLO_EFECTIVO','SOLO_TARJETA')
), cells AS (
 SELECT LocationId,week,payment_employee_id,channel_name,gross_band,daypart,line_band,
 COUNT_IF(payment_family='SOLO_EFECTIVO') nc,COUNT_IF(payment_family='SOLO_TARJETA') nk,
 SUM(CASE WHEN payment_family='SOLO_EFECTIVO' THEN has_discount ELSE 0 END) dc,
 SUM(CASE WHEN payment_family='SOLO_TARJETA' THEN has_discount ELSE 0 END) dk,
 SUM(CASE WHEN payment_family='SOLO_EFECTIVO' THEN discount_pct/100 ELSE 0 END) rc,
 SUM(CASE WHEN payment_family='SOLO_TARJETA' THEN discount_pct/100 ELSE 0 END) rk
 FROM base GROUP BY ALL
), thresholds AS (SELECT explode(array(2,5,10)) minimum_per_method)
SELECT LocationId,week,minimum_per_method,SUM(nc+nk) eligible_tickets,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN nc+nk ELSE 0 END) comparable_tickets,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN nc ELSE 0 END) comparable_cash,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN nk ELSE 0 END) comparable_card,
 COUNT_IF(nc>=minimum_per_method AND nk>=minimum_per_method) supported_cells,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN (nc+nk)*dc/nc ELSE 0 END) weighted_cash_rate,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN (nc+nk)*dk/nk ELSE 0 END) weighted_card_rate,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN (nc+nk)*rc/nc ELSE 0 END) weighted_cash_ratio,
 SUM(CASE WHEN nc>=minimum_per_method AND nk>=minimum_per_method THEN (nc+nk)*rk/nk ELSE 0 END) weighted_card_ratio
FROM cells CROSS JOIN thresholds GROUP BY ALL
