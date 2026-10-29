-- Dataset: casos. Only tickets included in review_cases; this is not all
-- tickets or all tickets with a high absolute monetary tip.
-- At most 100 rows; total_casos_filtrados counts ALL cases before LIMIT.
-- Stored P95 values cover the full Gold period; filters do not recompute them.
-- Interpret tip_pct only for comparable card payments; display the flag.
WITH base AS (
 SELECT *,
  CONCAT(COALESCE(location_name,'Sin nombre'),' [',CAST(LocationId AS STRING),']') AS sucursal,
  CONCAT(COALESCE(channel_name,'Sin nombre'),' [',CAST(RevenueCenterId AS STRING),']') AS canal
 FROM workspace.applebees_gold.review_cases
), filtrado AS (
 SELECT * FROM base WHERE BusinessDate BETWEEN :p_inicio AND :p_fin
 AND (:p_sucursal='TODAS' OR sucursal=:p_sucursal)
 AND (:p_canal='TODOS' OR canal=:p_canal)
)
SELECT CheckId,LocationId,BusinessDate,sucursal,canal,
 grossprice_sum_unvalidated AS gross_registrado,
 discount_total_raw AS descuento_importe,discount_pct AS descuento_pct,
 account_candidate AS cuenta_sin_propina,
 tip_amount_interpreted AS propina_importe,tip_pct AS propina_pct,
 tip_comparable,void_count,void_amount_raw,payment_employee_id,
 account_status,mismatched_item_lines,
 high_discount_and_tip,small_account_high_tip,non_reconciled_case,item_mismatch_case,
 also_large_tip_amount,peer_tickets,discount_p95,tip_pct_p95,tip_amount_p95,
 COUNT(*) OVER () AS total_casos_filtrados
FROM filtrado
ORDER BY small_account_high_tip DESC, tip_amount_interpreted DESC NULLS LAST,
 BusinessDate,LocationId,CheckId
LIMIT 100;
