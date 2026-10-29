-- Execute the three queries separately in SQL Editor.
-- Read-only: does not rebuild layers or query the raw volume.
SELECT table_name, column_name, data_type
FROM workspace.information_schema.columns
WHERE table_schema = 'applebees_gold'
ORDER BY table_name, ordinal_position;

SELECT COUNT(*) AS tickets, COUNT(DISTINCT LocationId) AS sucursales,
 COUNT(DISTINCT BusinessDate) AS dias, MIN(BusinessDate) AS inicio,
 MAX(BusinessDate) AS fin,
 SUM(has_discount) AS tickets_con_descuento,
 SUM(CASE WHEN void_count > 0 THEN 1 ELSE 0 END) AS tickets_con_anulacion,
 SUM(CASE WHEN NOT assessable THEN 1 ELSE 0 END) AS incompletos,
 SUM(CASE WHEN assessable AND NOT reconciled THEN 1 ELSE 0 END) AS no_conciliados,
 SUM(mismatched_item_lines) AS lineas_discrepantes,
 SUM(CASE WHEN reconciled THEN net_sales_candidate ELSE 0 END) AS venta_neta_conciliada,
 SUM(CASE WHEN reconciled THEN discount_total_raw ELSE 0 END) AS descuentos_conciliados
FROM workspace.applebees_gold.ticket_metrics;

SELECT SUM(tickets) AS tickets, SUM(discounted_tickets) AS tickets_con_descuento,
 SUM(tickets_with_voids) AS tickets_con_anulacion,
 SUM(incomplete_tickets) AS incompletos,
 SUM(non_reconciled_tickets) AS no_conciliados,
 SUM(mismatched_item_lines) AS lineas_discrepantes,
 SUM(net_sales_reconciled) AS venta_neta_conciliada,
 SUM(discounts_reconciled) AS descuentos_conciliados
FROM workspace.applebees_gold.daily_location_channel;
