-- P1. ¿Son fiables los datos?
-- Capturas recogidas frente a las esperadas (una cada 15 minutos = 96 al día).
SELECT count(DISTINCT momento)                                   AS capturas,
       min(momento)                                              AS primera,
       max(momento)                                              AS ultima,
       round(epoch(max(momento) - min(momento)) / 900)           AS capturas_esperadas,
       round(100 * count(DISTINCT momento)
             / (epoch(max(momento) - min(momento)) / 900), 1)    AS pct_cobertura,
       count(DISTINCT estacion_id)                               AS estaciones,
       count(*)                                                  AS lecturas
FROM capturas_todas;

-- Capturas por franja y tipo de día: cuántas observaciones respaldan cada cifra.
SELECT laborable, franja, count(DISTINCT momento) AS capturas
FROM capturas_todas GROUP BY ALL ORDER BY ALL;

-- Estaciones que no se actualizan (más de 2 h entre la captura y la fuente).
SELECT estacion_id, nombre,
       count(*)                       AS capturas_desfasadas,
       max(bicis)                     AS max_bicis,
       max(anclajes_libres)           AS max_libres,
       max(actualizado_fuente)        AS ultima_actualizacion_fuente
FROM capturas_todas
WHERE momento - actualizado_fuente > INTERVAL 2 HOUR
GROUP BY ALL;

-- Anclajes averiados: bicis + libres < capacidad.
SELECT round(100 * avg((bicis + anclajes_libres < capacidad)::INT), 1) AS pct_lecturas_con_averia,
       round(avg(capacidad - bicis - anclajes_libres), 2)              AS anclajes_averiados_medios
FROM capturas;
