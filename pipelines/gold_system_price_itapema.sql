-- gold.system_price_itapema
-- Media do System Price por bairro de Itapema no ultimo trimestre.
-- Consumido pelo dashboard de Revenue Management (RM).
--
-- Autor: Junior (squad Data Edge)
-- Spec: alinhado com Anna (RM) em 2025-04-22

CREATE TABLE IF NOT EXISTS gold_system_price_itapema (
    bairro VARCHAR,
    system_price_avg DOUBLE,
    n_amostras INTEGER
);

INSERT INTO gold_system_price_itapema
SELECT
    suburb AS bairro,
    AVG(price) AS system_price_avg,
    COUNT(*) AS n_amostras
FROM stage
GROUP BY suburb
ORDER BY system_price_avg DESC;
