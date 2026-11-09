-- P3. ¿A qué horas pasa? Laborables frente a fines de semana.
-- Porcentaje de estaciones vacías y llenas en cada franja (toda la red).
SELECT CASE WHEN laborable THEN 'laborable' ELSE 'fin de semana' END AS dia,
       franja,
       count(DISTINCT momento)                         AS capturas,
       round(100 * avg((bicis = 0)::INT), 1)           AS pct_vacias,
       round(100 * avg((anclajes_libres = 0)::INT), 1) AS pct_llenas
FROM capturas
GROUP BY laborable, franja ORDER BY laborable DESC, franja;
