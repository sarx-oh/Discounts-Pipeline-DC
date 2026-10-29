-- Dataset: canales. Horizontal frequency bars; table with n/N and intensity.
-- Same four parameters as 01_panorama. Connect all to the same global filter.
-- Frequency: tickets with any positive discount / ALL tickets in the channel.
-- Intensity: discount / gross, both restricted to reconciled tickets with valid denominators.
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
SELECT RevenueCenterId, MAX(channel_name) AS channel_name, canal,
 SUM(tickets) AS tickets, SUM(discounted_tickets) AS tickets_con_descuento,
 100.0*TRY_DIVIDE(SUM(discounted_tickets),SUM(tickets)) AS frecuencia_descuento_pct,
 SUM(discount_ratio_tickets) AS tickets_cohorte_intensidad,
 SUM(valid_discount_sum) AS descuento_cohorte_valida,
 SUM(valid_gross_sum) AS gross_cohorte_valida,
 100.0*TRY_DIVIDE(SUM(valid_discount_sum),SUM(valid_gross_sum)) AS intensidad_descuento_pct,
 SUM(discounts_reconciled) AS descuento_conciliado,
 SUM(net_sales_reconciled) AS venta_neta_conciliada
FROM filtrado GROUP BY RevenueCenterId,canal
ORDER BY frecuencia_descuento_pct DESC;
