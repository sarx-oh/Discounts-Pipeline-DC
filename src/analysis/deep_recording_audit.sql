-- Full-snapshot recording audit; no exclusions or private identifiers in output.
WITH p AS (
 SELECT CheckId,LocationId,BusinessDate,COUNT(*) n_payments,
 COUNT_IF(Amount IS NULL) null_amounts,COUNT_IF(Gratuity IS NULL) null_tips,
 COUNT_IF(Amount<0) negative_amounts,COUNT_IF(Gratuity>0) positive_gratuities,
 COUNT_IF(Gratuity<0) negative_gratuities,COUNT_IF(Gratuity=0) zero_gratuities,
 SUM(Gratuity) gratuity_sum,
 MAX(CASE WHEN UPPER(PayCatName)='CASH' THEN 1 ELSE 0 END) cash_present,
 MAX(CASE WHEN IsCreditCard THEN 1 ELSE 0 END) card_present,
 MAX(CASE WHEN NOT COALESCE(IsCreditCard,false) AND COALESCE(UPPER(PayCatName),'UNKNOWN')<>'CASH' THEN 1 ELSE 0 END) other_present
 FROM {{payments}} GROUP BY CheckId,LocationId,BusinessDate
), d AS (
 SELECT CheckId,LocationId,BusinessDate,COUNT(*) n_events,
 COUNT_IF(Amount>0) positive_events,COUNT_IF(Amount<0) negative_events,
 COUNT_IF(Amount=0) zero_events,COUNT_IF(Amount IS NULL) null_discounts,
 SUM(Amount) net_discount,SUM(CASE WHEN Amount>0 THEN Amount ELSE 0 END) positive_discount
 FROM {{discounts}} GROUP BY CheckId,LocationId,BusinessDate
), joined AS (
 SELECT m.*,p.n_payments,p.null_amounts,p.null_tips,p.positive_gratuities,p.negative_gratuities,
 p.zero_gratuities,p.cash_present,p.card_present,p.other_present,
 d.n_events,d.positive_events,d.negative_events,d.zero_events,d.null_discounts,d.net_discount,d.positive_discount
 FROM {{ticket_metrics}} m LEFT JOIN p USING(CheckId,LocationId,BusinessDate)
 LEFT JOIN d USING(CheckId,LocationId,BusinessDate)
), cohorts AS (
 SELECT account_status,payment_family,cash_present,card_present,other_present,
 COUNT(*) tickets,SUM(has_discount) discounted,
 COUNT_IF(null_tips>0) tickets_null_tip_components,
 COUNT_IF(null_amounts>0) tickets_null_payment_components,
 COUNT_IF(positive_gratuities>0) tickets_positive_gratuity_sign,
 COUNT_IF(negative_gratuities>0) tickets_negative_gratuity_sign,
 COUNT_IF(negative_events>0) tickets_negative_discount,
 COUNT_IF(null_discounts>0) tickets_null_discount,
 COUNT_IF(positive_events>0 AND net_discount<=0) positive_events_nonpositive_net,
 COUNT_IF(discount_denominator_valid AND discount_pct>=99.99) fully_discounted,
 COUNT_IF(discount_pct>100) ratio_above_100,
 COUNT_IF(has_discount<>CASE WHEN positive_events>0 THEN 1 ELSE 0 END) occurrence_mismatch,
 COUNT_IF(ABS(discount_total_raw-COALESCE(net_discount,0))>.02) discount_sum_mismatch,
 COUNT_IF(tip_comparable AND null_tips>0) comparable_partial_tip,
 COUNT_IF(payment_employee_id IS NULL) unattributed_tickets,
 SUM(gratuity_raw) gratuity_raw_sum,SUM(discount_total_raw) discount_sum
 FROM joined GROUP BY ALL
), labels AS (
 SELECT PayCatName,IsCreditCard,COUNT(*) records,COUNT_IF(Amount IS NULL) null_amount,
 COUNT_IF(Gratuity IS NULL) null_gratuity,COUNT_IF(Gratuity=0) zero_gratuity,
 COUNT_IF(Gratuity<0) negative_gratuity,COUNT_IF(Gratuity>0) positive_gratuity,
 COUNT_IF(Amount<0) negative_payment,SUM(Gratuity) gratuity_sum
 FROM {{payments}} GROUP BY ALL
)
SELECT 'cohorts' section,to_json(collect_list(struct(*))) payload FROM cohorts
UNION ALL SELECT 'payment_labels',to_json(collect_list(struct(*))) FROM labels
UNION ALL SELECT 'join_counts',to_json(named_struct('joined',COUNT(*),'unique_keys',COUNT(DISTINCT struct(CheckId,LocationId,BusinessDate)))) FROM joined
