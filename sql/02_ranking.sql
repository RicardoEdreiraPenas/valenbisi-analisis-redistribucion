-- P2. ¿Qué estaciones pasan más tiempo vacías (0 bicis) o llenas (0 anclajes libres)?
-- Días laborables, con las seis franjas ponderadas por igual.
CREATE OR REPLACE TABLE estaciones AS
SELECT estacion_id,
       any_value(nombre)    AS nombre,
       any_value(latitud)   AS latitud,
       any_value(longitud)  AS longitud,
       any_value(capacidad) AS capacidad,
       avg(pct_vacia)       AS pct_vacia,
       avg(pct_llena)       AS pct_llena,
       avg(ocupacion)       AS ocupacion,
       CASE WHEN avg(pct_vacia) >= 0.30 THEN 'tiende a vaciarse'
            WHEN avg(pct_llena) >= 0.20 THEN 'tiende a llenarse'
            ELSE 'equilibrada' END AS grupo
FROM estacion_franja
WHERE laborable
GROUP BY estacion_id;

SELECT nombre, capacidad, round(100 * pct_vacia) AS pct_tiempo_vacia
FROM estaciones ORDER BY pct_vacia DESC LIMIT 10;

SELECT nombre, capacidad, round(100 * pct_llena) AS pct_tiempo_llena
FROM estaciones ORDER BY pct_llena DESC LIMIT 10;

SELECT grupo, count(*) AS estaciones FROM estaciones GROUP BY ALL ORDER BY ALL;
