-- Dataset: panorama. One row for KPI cards and the quality table.
-- Parameters: p_inicio DATE=2026-04-28; p_fin DATE=2026-08-20;
-- p_sucursal STRING=TODAS; p_canal STRING=TODOS (single selection).
-- For location/channel choices, run each SELECT in 90_opciones.sql
-- as a separate dataset. Bind global filters to the parameters.
-- Percentages use 0..100: numeric format plus % suffix; do not multiply by 100 again.
WITH base AS (
 SELECT *,
  CONCAT(COALESCE(location_name,'Sin nombre'), ' [', CAST(LocationId AS STRING), ']') AS sucursal,
  CONCAT(COALESCE(channel_name,'Sin nombre'), ' [', CAST(RevenueCenterId AS STRING), ']') AS canal
 FROM workspace.applebees_gold.daily_location_channel
), filtrado AS (
 SELECT * FROM base
 WHERE BusinessDate BETWEEN :p_inicio AND :p_fin
  AND (:p_sucursal = 'TODAS' OR sucursal = :p_sucursal)
  AND (:p_canal = 'TODOS' OR canal = :p_canal)
)
SELECT MIN(BusinessDate) AS inicio_observado, MAX(BusinessDate) AS fin_observado,
 COUNT(DISTINCT BusinessDate) AS dias_observados,
 COUNT(DISTINCT LocationId) AS sucursales,
 COALESCE(SUM(tickets),0) AS tickets,
 COALESCE(SUM(discounted_tickets),0) AS tickets_con_descuento,
 100.0 * TRY_DIVIDE(SUM(discounted_tickets),SUM(tickets)) AS frecuencia_descuento_pct,
 COALESCE(SUM(tickets_with_voids),0) AS tickets_con_anulacion,
 100.0 * TRY_DIVIDE(SUM(tickets_with_voids),SUM(tickets)) AS frecuencia_anulacion_pct,
 COALESCE(SUM(incomplete_tickets),0) AS tickets_incompletos,
 100.0 * TRY_DIVIDE(SUM(incomplete_tickets),SUM(tickets)) AS incompletos_pct,
 COALESCE(SUM(non_reconciled_tickets),0) AS tickets_no_conciliados,
 COALESCE(SUM(reconciled_tickets),0) AS tickets_conciliados,
 COALESCE(SUM(mismatched_item_lines),0) AS lineas_discrepantes,
 COALESCE(SUM(tickets_with_item_mismatches),0) AS tickets_con_lineas_discrepantes,
 SUM(net_sales_reconciled) AS venta_neta_conciliada,
 SUM(discounts_reconciled) AS descuento_conciliado,
 SUM(discount_ratio_tickets) AS tickets_cohorte_intensidad,
 SUM(valid_discount_sum) AS descuento_cohorte_valida,
 SUM(valid_gross_sum) AS gross_cohorte_valida,
 100.0 * TRY_DIVIDE(SUM(valid_discount_sum),SUM(valid_gross_sum)) AS intensidad_descuento_pct
FROM filtrado;
