-- Vista base: todas las capturas de la rama `datos`.
-- {{DATOS}} se sustituye por la carpeta de datos (por defecto, datos/).
-- Se excluye la estación 70: informa 0 bicis y 0 anclajes libres en todas las
-- capturas y la fuente no la actualiza desde el 17 de septiembre de 2026 (ver 01_cobertura.sql).
CREATE OR REPLACE VIEW capturas_todas AS
SELECT *,
       dayofweek(momento) NOT IN (0, 6) AS laborable,
       CASE
           WHEN hour(momento) < 6  THEN '00-06'
           WHEN hour(momento) < 10 THEN '06-10'
           WHEN hour(momento) < 14 THEN '10-14'
           WHEN hour(momento) < 17 THEN '14-17'
           WHEN hour(momento) < 21 THEN '17-21'
           ELSE '21-24'
       END AS franja
FROM read_csv('{{DATOS}}/*/*.csv.gz', header = true, columns = {
    'momento': 'TIMESTAMP', 'estacion_id': 'INTEGER', 'nombre': 'VARCHAR',
    'direccion': 'VARCHAR', 'latitud': 'DOUBLE', 'longitud': 'DOUBLE',
    'bicis': 'INTEGER', 'anclajes_libres': 'INTEGER', 'capacidad': 'INTEGER',
    'abierta': 'BOOLEAN', 'actualizado_fuente': 'TIMESTAMP'});

CREATE OR REPLACE VIEW capturas AS
SELECT * FROM capturas_todas
WHERE abierta AND estacion_id <> 70;

-- Una fila por estación, laborable/fin de semana y franja horaria.
-- Las franjas se ponderan igual en los promedios por estación, porque la
-- cobertura de capturas no es uniforme a lo largo del día.
CREATE OR REPLACE TABLE estacion_franja AS
SELECT estacion_id,
       any_value(nombre)            AS nombre,
       any_value(latitud)           AS latitud,
       any_value(longitud)          AS longitud,
       max(capacidad)               AS capacidad,
       laborable, franja,
       count(*)                     AS capturas,
       avg((bicis = 0)::INT)        AS pct_vacia,
       avg((anclajes_libres = 0)::INT) AS pct_llena,
       avg(bicis)                   AS bicis_medias,
       avg(bicis / capacidad)       AS ocupacion
FROM capturas
GROUP BY estacion_id, laborable, franja;
