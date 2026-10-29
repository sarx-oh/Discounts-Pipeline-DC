-- Dataset: evolucion. One row per date and channel after location filtering.
-- Line chart: BusinessDate / frecuencia_descuento_pct / canal.
-- Use MAX of the percentage while retaining date+channel (one row per group).
-- Do not regroup these rates by month or across channels: change GROUP BY
-- in SQL and recompute SUM(numerator)/SUM(denominator).
WITH base AS (
 SELECT *,
  CONCAT(COALESCE(location_name,'Sin nombre'), ' [', CAST(LocationId AS STRING), ']') AS sucursal,
  CONCAT(COALESCE(channel_name,'Sin nombre'), ' [', CAST(RevenueCenterId AS STRING), ']') AS canal
 FROM workspace.applebees_gold.daily_location_channel
), filtrado AS (
 SELECT * FROM base WHERE BusinessDate BETWEEN :p_inicio AND :p_fin
 AND (:p_sucursal='TODAS' OR sucursal=:p_sucursal)
 AND (:p_canal='TODOS' OR canal=:p_canal)
)
SELECT BusinessDate, RevenueCenterId, MAX(channel_name) AS channel_name, canal,
 SUM(tickets) AS tickets, SUM(discounted_tickets) AS tickets_con_descuento,
 100.0*TRY_DIVIDE(SUM(discounted_tickets),SUM(tickets)) AS frecuencia_descuento_pct,
 SUM(net_sales_reconciled) AS venta_neta_conciliada,
 SUM(discounts_reconciled) AS descuento_conciliado,
 SUM(tickets_with_voids) AS tickets_con_anulacion,
 100.0*TRY_DIVIDE(SUM(tickets_with_voids),SUM(tickets)) AS frecuencia_anulacion_pct
FROM filtrado GROUP BY BusinessDate,RevenueCenterId,canal
ORDER BY BusinessDate,RevenueCenterId;
