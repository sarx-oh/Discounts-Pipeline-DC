-- Dataset: propinas. Compare sensitivity to account size by channel.
-- Mean of per-ticket percentages, NOT a monetary-weighted tip rate.
-- Medians come from filtered tickets, not daily medians.
-- The account>=5 cutoff is exploratory; do not remove small accounts from the model.
WITH base AS (
 SELECT *,
  CONCAT(COALESCE(location_name,'Sin nombre'),' [',CAST(LocationId AS STRING),']') AS sucursal,
  CONCAT(COALESCE(channel_name,'Sin nombre'),' [',CAST(RevenueCenterId AS STRING),']') AS canal
 FROM workspace.applebees_gold.ticket_metrics
), filtrado AS (
 SELECT * FROM base WHERE BusinessDate BETWEEN :p_inicio AND :p_fin
 AND (:p_sucursal='TODAS' OR sucursal=:p_sucursal)
 AND (:p_canal='TODOS' OR canal=:p_canal)
 AND tip_comparable
)
SELECT RevenueCenterId,MAX(channel_name) AS channel_name,canal,
 COUNT(*) AS tickets_comparables,
 AVG(tip_pct) AS media_propina_pct,
 PERCENTILE_APPROX(tip_pct,0.5) AS mediana_propina_pct,
 SUM(CASE WHEN account_candidate>=5 THEN 1 ELSE 0 END) AS tickets_cuenta_al_menos_5,
 AVG(CASE WHEN account_candidate>=5 THEN tip_pct END) AS media_propina_pct_cuenta_al_menos_5,
 PERCENTILE_APPROX(CASE WHEN account_candidate>=5 THEN tip_pct END,0.5) AS mediana_propina_pct_cuenta_al_menos_5,
 AVG(tip_amount_interpreted) AS media_importe_propina
FROM filtrado GROUP BY RevenueCenterId,canal;
