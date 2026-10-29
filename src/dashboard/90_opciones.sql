-- Create TWO separate datasets: opciones_sucursal and opciones_canal.
-- Each has ONE option field combining name and ID to distinguish repeated names.
-- String parameters, single selection: TODAS / TODOS are literal sentinel values.
-- Set each widget Fields=opcion from its dedicated dataset and
-- Parameters=p_sucursal or p_canal for each analytical dataset.
SELECT 'TODAS' AS opcion
UNION
SELECT DISTINCT CONCAT(COALESCE(location_name,'Sin nombre'),' [',CAST(LocationId AS STRING),']')
FROM workspace.applebees_gold.daily_location_channel
ORDER BY opcion;

SELECT 'TODOS' AS opcion
UNION
SELECT DISTINCT CONCAT(COALESCE(channel_name,'Sin nombre'),' [',CAST(RevenueCenterId AS STRING),']')
FROM workspace.applebees_gold.daily_location_channel
ORDER BY opcion;
