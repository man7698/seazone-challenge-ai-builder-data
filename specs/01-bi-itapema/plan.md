# Plan — BI Itapema (Parte 1)

Pré-condição: este plano e o `spec.md` são commitados antes de qualquer código de
análise (`analysis/`). Verificável em `git log --reverse`.

## Passo 0 — Setup do projeto

- `analysis/` com `uv init`, `pyproject.toml` (Polars, DuckDB, sem requirements.txt).
- Sem Jupyter em lugar nenhum.

Depende de: nada. Bloqueia: todos os passos abaixo.

## Passo 1 — Camada de carga e limpeza (bronze → silver)

- Carregar os 5 CSVs com Polars (schema explícito, não inferência cega — os IDs são
  inteiros de 18-19 dígitos, e datas vêm em formatos distintos por arquivo).
- Deduplicar `Mesh_Ids_Data_Itapema.csv` por `airbnb_listing_id` (linha mais recente por
  `aquisition_date`) → `mesh_latest`.
- Deduplicar `Hosts_ids_Itapema.csv` por `owner_id` (linha mais recente) → `hosts_latest`.
- Normalizar `suburb` (lower + strip de acento) em `mesh_latest` e em `VivaReal`.
- Filtrar `Price_AV_Itapema.csv` pela onda `date_trunc('day', aquisition_date) =
  '2025-01-20'` → `price_wave_latest` (ADR "atual"). Manter as outras 2 ondas separadas
  para a análise secundária de variação de preço por antecedência.

Depende de: Passo 0. Saída: tabelas silver em Parquet local (`analysis/data/silver/`).

## Passo 2 — Métricas por corte (H1, H2, H3)

- Join `price_wave_latest` × `Details` × `mesh_latest` × `hosts_latest`.
- Agregações por bairro, por (`listing_type` × `number_of_bedrooms`), com `n_listings`,
  `adr` (média e mediana), `avg_reviews`, `pct_superhost`, `avg_star_rating`.
- Aplicar o filtro de confiabilidade (`n_listings_priced ≥ 10`) e reportar separadamente
  os cortes abaixo do filtro.
- Correlação ADR × (`star_rating`, `number_of_reviews`, `is_superhost`) por bairro (H3).

Depende de: Passo 1. Saída: tabela "gold" `revenue_by_cut.parquet` + tabela de
correlações.

## Passo 3 — Cruzamento de custo (VivaReal) por bairro/dormitórios

- Normalizar `suburb` e cruzar com a tabela do Passo 2.
- Calcular preço/m² médio por bairro × dormitórios (`sale_price / usable_area`).

Depende de: Passo 1. Pode rodar em paralelo ao Passo 2.

## Passo 4 — Decisão de localização e perfil (H1, H2, H4)

- A partir das tabelas dos Passos 2 e 3, decidir bairro e mix de dormitórios para o
  prédio de 50 apartamentos, com justificativa quantitativa (não só a maior média —
  considerar volume/confiabilidade, ver spec §2).
- Simular 3 cenários de mix de unidades (100% 2Q, 100% 3Q, mix 50/50) e comparar receita
  projetada agregada do prédio.

Depende de: Passos 2 e 3.

## Passo 5 — ROI 2025/2026/2027 (H5)

- Aplicar a curva de ocupação por banda de demanda (spec §5.3) ao mix escolhido no Passo
  4.
- Calcular investimento total (custo de implantação, spec §5.4, × 50 unidades).
- Projetar receita, opex (condomínio, taxa de gestão assumida e documentada, manutenção)
  e ROI por ano, com:
  - Ano 1 (2025): ocupação reduzida (ramp-up, prédio novo sem reviews/histórico).
  - Ano 2 (2026): ocupação estabilizada.
  - Ano 3 (2027): ocupação estabilizada + crescimento de ADR assumido (premissa de
    mercado, documentada).
- Reportar cenário base + sensibilidade (otimista/conservador na ocupação).

Depende de: Passo 4.

## Passo 6 — Consolidação e narrativa

- Script único que roda os passos 1-5 e emite as tabelas finais + tempo de execução e
  pico de memória por etapa (eficiência computacional, exigido no PDF).
- Resumo das respostas às 5 perguntas do desafio, com números e justificativa, pronto
  para entrar no relatório PDF.

Depende de: Passos 1-5.

## Riscos de execução

- Se o join Details × Price_AV restante de listings priced ficar muito pequeno por
  bairro/dormitório simultâneo (cortes finos), reportar com `n` explícito em vez de
  omitir — silêncio sobre amostra pequena é pior do que mostrar o número baixo.
- Encoding dos CSVs (acentos) — validar leitura com Polars antes de qualquer agregação
  textual (bairro, listing_type).
