-- P4. ¿Dónde? Ocupación media por franja de los dos grupos de estaciones (laborables).
-- Requiere la tabla `estaciones` de 02_ranking.sql.
SELECT e.grupo, ef.franja,
       count(*)                       AS estaciones,
       round(100 * avg(ef.ocupacion)) AS ocupacion_media
FROM estacion_franja ef JOIN estaciones e USING (estacion_id)
WHERE ef.laborable
GROUP BY ALL ORDER BY ALL;

-- Posición media de cada grupo (para situarlos en el mapa).
SELECT grupo, count(*) AS estaciones,
       round(avg(latitud), 4) AS latitud_media, round(avg(longitud), 4) AS longitud_media
FROM estaciones GROUP BY ALL ORDER BY ALL;
