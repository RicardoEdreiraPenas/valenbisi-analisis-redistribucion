-- P5. ¿Cómo redistribuir? Necesidad de cada estación al final de la noche (00-06, laborables).
-- Objetivos (supuesto del análisis, no de Valenbisi):
--   * Estaciones que tienden a vaciarse: subir al 30 % de su capacidad. No más, porque por la
--     mañana reciben llegadas y a mediodía rondan el 60-70 %: hay que dejarles anclajes libres.
--   * Estaciones que tienden a llenarse: bajar al 70 %, para que quien vuelve de noche pueda anclar.
-- Requiere la tabla `estaciones` de 02_ranking.sql.
CREATE OR REPLACE TABLE necesidad AS
SELECT e.estacion_id, e.nombre, e.latitud, e.longitud, e.capacidad, e.grupo,
       round(ef.bicis_medias, 1) AS bicis_noche,
       CASE WHEN e.grupo = 'tiende a vaciarse'
                THEN greatest(0, round(0.30 * e.capacidad - ef.bicis_medias))
            WHEN e.grupo = 'tiende a llenarse'
                THEN -greatest(0, round(ef.bicis_medias - 0.70 * e.capacidad))
            ELSE 0 END AS bicis_a_mover   -- positivo: necesita bicis; negativo: le sobran
FROM estaciones e
JOIN estacion_franja ef ON ef.estacion_id = e.estacion_id AND ef.laborable AND ef.franja = '00-06'
WHERE e.grupo <> 'equilibrada';

SELECT grupo, count(*) AS estaciones, sum(abs(bicis_a_mover)) AS bicis
FROM necesidad GROUP BY ALL;

-- Distancias en línea recta entre estaciones que dan y que reciben (fórmula del haversine, metros).
CREATE OR REPLACE TABLE distancias AS
SELECT o.estacion_id AS origen, d.estacion_id AS destino,
       round(2 * 6371000 * asin(sqrt(
           pow(sin(radians(d.latitud - o.latitud) / 2), 2) +
           cos(radians(o.latitud)) * cos(radians(d.latitud)) *
           pow(sin(radians(d.longitud - o.longitud) / 2), 2)))) AS metros
FROM necesidad o, necesidad d
WHERE o.bicis_a_mover < 0 AND d.bicis_a_mover > 0;
