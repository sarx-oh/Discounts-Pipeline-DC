SELECT CASE WHEN BusinessDate<DATE'2026-07-01' THEN 'train'
 WHEN BusinessDate<DATE'2026-07-26' THEN 'validation' ELSE 'test' END temporal_split,
 COUNT(*) all_tickets,
 COUNT_IF(reconciled AND account_candidate>0 AND discount_denominator_valid AND negative_payment_records=0) eligible,
 COUNT_IF(reconciled AND account_candidate>0 AND discount_denominator_valid AND negative_payment_records=0 AND has_discount=1) eligible_discounted,
 COUNT_IF(reconciled AND account_candidate<=0) nonpositive_reconciled,
 COUNT_IF(NOT reconciled) nonreconciled,
 MIN(BusinessDate) first_date,MAX(BusinessDate) last_date
FROM {{ticket_metrics}}
GROUP BY CASE WHEN BusinessDate<DATE'2026-07-01' THEN 'train'
 WHEN BusinessDate<DATE'2026-07-26' THEN 'validation' ELSE 'test' END
