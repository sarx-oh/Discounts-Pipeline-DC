-- Dataset: tipos_descuento. Table or bars by scope+ID+name+channel.
-- Same parameters. applications includes zero-amount applications.
-- Positive tickets can be summed WITHIN a type and channel: the ticket key
-- includes date and location. Do NOT sum across types/scopes as a unique
-- ticket count: a ticket can belong to multiple groups.
WITH base AS (
 SELECT *,
  CONCAT(COALESCE(location_name,'Sin nombre'), ' [', CAST(LocationId AS STRING), ']') AS sucursal,
  CONCAT(COALESCE(channel_name,'Sin nombre'), ' [', CAST(RevenueCenterId AS STRING), ']') AS canal
 FROM workspace.applebees_gold.discount_type_daily
), filtrado AS (
 SELECT * FROM base WHERE BusinessDate BETWEEN :p_inicio AND :p_fin
 AND (:p_sucursal='TODAS' OR sucursal=:p_sucursal)
 AND (:p_canal='TODOS' OR canal=:p_canal)
), denominadores AS (
 SELECT RevenueCenterId, SUM(tickets) AS tickets_canal,
  SUM(discounted_tickets) AS tickets_con_descuento_canal
 FROM workspace.applebees_gold.daily_location_channel
 WHERE BusinessDate BETWEEN :p_inicio AND :p_fin
 AND (:p_sucursal='TODAS' OR CONCAT(COALESCE(location_name,'Sin nombre'),' [',CAST(LocationId AS STRING),']')=:p_sucursal)
 AND (:p_canal='TODOS' OR CONCAT(COALESCE(channel_name,'Sin nombre'),' [',CAST(RevenueCenterId AS STRING),']')=:p_canal)
 GROUP BY RevenueCenterId
)
SELECT f.RevenueCenterId, MAX(f.channel_name) AS channel_name,f.canal,
 f.discount_scope,f.DiscountId,f.DiscountName,
 SUM(f.applications) AS aplicaciones,
 SUM(f.positive_applications) AS aplicaciones_positivas,
 SUM(f.positive_discount_tickets) AS tickets_positivos_tipo,
 MAX(d.tickets_canal) AS tickets_canal,
 100.0*TRY_DIVIDE(SUM(f.positive_discount_tickets),MAX(d.tickets_canal)) AS frecuencia_tipo_en_canal_pct,
 SUM(f.recorded_amount) AS importe_registrado,
 SUM(f.amount_on_reconciled_tickets) AS importe_en_conciliados
FROM filtrado f JOIN denominadores d ON f.RevenueCenterId=d.RevenueCenterId
GROUP BY f.RevenueCenterId,f.canal,f.discount_scope,f.DiscountId,f.DiscountName
ORDER BY importe_registrado DESC;
