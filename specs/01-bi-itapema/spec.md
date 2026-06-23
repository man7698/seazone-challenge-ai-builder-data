# Spec — BI Itapema (Parte 1)

## 1. Pergunta de negócio

A Seazone precisa decidir se investe em Itapema (SC) e, em caso positivo, como projetar
um prédio de 50 apartamentos para maximizar retorno. As perguntas do desafio (`melhor
perfil`, `melhor localização`, `melhores características`, projeto do prédio, ROI 25/26/27)
são deliberadamente abertas — esta seção fixa as definições operacionais que vamos usar,
para que a resposta seja reproduzível e não dependa de interpretação implícita.

## 2. Definições operacionais

- **"Melhor"** = maior receita projetada por apartamento por ano, com um filtro de
  confiabilidade estatística: qualquer corte (bairro, tipo, dormitórios) com menos de
  **10 listings com preço observado** é tratado como ruído e reportado separadamente,
  nunca como recomendação principal. Justificativa: bairros como Sertãozinho/Várzea têm
  ADR aparente altíssimo mas amostra de 3 listings — não é sinal, é variância.
- **"Perfil de imóvel"** = combinação (tipo de listing × nº de dormitórios), porque é a
  variável que mais explica ADR nos dados (ver §5) e é a decisão que o investidor
  efetivamente controla na planta.
- **"Localização"** = bairro (`suburb`), usando `Mesh_Ids_Data_Itapema.csv` como fonte —
  é a única fonte com lat/lon próprio por listing e atualização incremental; é mais
  confiável que inferir localização do texto do anúncio.
- **"Receita"** = não existe dado de reserva/ocupação real no dataset (`Price_AV` é preço
  de calendário, não preço pago). Receita é estimada como `ADR observado × ocupação
  estimada × 365`, com ocupação estimada por um proxy de demanda (ver §5.3). Isso é uma
  premissa, não um fato — está marcada como tal no relatório.

## 3. Hipóteses por pergunta

| # | Pergunta | Hipótese de trabalho | Como será testada |
|---|----------|----------------------|--------------------|
| H1 | Melhor perfil de imóvel | Apartamentos de 2–3 dormitórios maximizam receita/apto: ADR sobe com dormitórios, mas demanda (reviews, nº de listings ativos) cai em imóveis de 4+ dormitórios — nicho menor, ocupação mais incerta | ADR médio + nº de listings + reviews médios, agrupado por `number_of_bedrooms` × `listing_type`, restrito a listings com `Price_AV` |
| H2 | Melhor localização (receita) | Meia Praia é a melhor localização por volume×preço combinados (maior ADR entre bairros com amostra robusta, maior nº de listings ativos, maior % superhost) — não necessariamente o ADR unitário mais alto | ADR médio + mediana + n por `suburb` (bairro mais recente por listing, deduplicado), filtrado por n≥10 |
| H3 | Características/razões das melhores receitas | Receita correlaciona com: nº de dormitórios, bairro, e sinais de qualidade de operação (`star_rating`, `is_superhost`, `number_of_reviews`) mais do que com amenidades pontuais | Correlação simples (Pearson/Spearman) entre ADR e `star_rating`/`number_of_reviews`/`is_superhost`, por bairro |
| H4 | Prédio de 50 apartamentos | Construir em Meia Praia, mix de 2–3 dormitórios (sem unidades de 1 dormitório nem 4+, que têm pior relação demanda/ADR no recorte de dados) | Cálculo de receita projetada por mix de unidades vs. mix alternativo (100% 2Q, 100% 3Q, 50/50) |
| H5 | ROI 2025/26/27 | ROI positivo mas com ramp-up: ano 1 com ocupação reduzida (prédio novo, sem histórico/reviews), estabilizando a partir do ano 2 | NOI projetado / investimento total, com curva de ocupação documentada como premissa explícita (não como dado) |

## 4. Métricas que materializam a resposta

- `adr_brl`: preço médio de diária observado em `Price_AV`, na "onda" de aquisição mais
  recente (2025-01-20, ver §5.1), por corte (bairro / dormitórios / tipo).
- `n_listings_priced`: nº de listings distintos com preço observado no corte — usado como
  filtro de confiabilidade (§2).
- `demand_proxy`: `avg(number_of_reviews)` e `pct_superhost` por corte, como sinal de
  demanda histórica (não temos data de reserva, reviews é o proxy disponível).
- `revenue_per_unit_brl_year`: `adr_brl × occupancy_assumption × 365`.
- `roi_pct`: `(receita_anual_total − opex_anual_total) / investimento_total`, por ano
  (2025, 2026, 2027), com premissas de crescimento de ADR e curva de ocupação.

## 5. Decisões de modelagem

### 5.1 Qual snapshot de `Price_AV` usar (a armadilha da dupla data)

`Price_AV_Itapema.csv` tem 3 "ondas" de aquisição (2025-01-06, 2025-01-07, 2025-01-20),
todas cobrindo a **mesma janela de estadia** (2025-01-06 a 2025-04-20 — alta temporada de
verão em SC). Tratar isso como "preço atual" único, ou pior, usar
`max(aquisition_date)` direto, é um erro: o timestamp de aquisição é quase único por
listing dentro do próprio dia (cada listing foi raspado em um segundo diferente), então
`max()` sem truncar por dia filtra **1 único listing**, não a onda inteira.

**Decisão:** usar `date_trunc('day', aquisition_date) = '2025-01-20'` como onda de
referência para ADR "atual" — é a mais recente das 3, logo a mais próxima da data real de
check-in para a maior parte da janela de estadia (preços de calendário tendem a se ajustar
conforme a data se aproxima). As outras duas ondas (01-06, 01-07) são usadas só para
estudar variação de preço por antecedência de reserva (insight secundário, não a métrica
principal).

### 5.2 Bairro: qual fonte e como deduplicar

`Mesh_Ids_Data_Itapema.csv` é incremental (99 datas de aquisição, 2021-10 a 2026-05) — não
é 1 linha por listing, é uma série temporal. **Decisão:** pegar a linha de
`aquisition_date` mais recente por `airbnb_listing_id` (`row_number() over (partition by
airbnb_listing_id order by aquisition_date desc) = 1`) antes de qualquer agregação por
bairro. O mesmo problema existe em `Hosts_ids_Itapema.csv` (4.440 linhas, 3.057
`owner_id` distintos) — qualquer join com Hosts precisa do mesmo tratamento, senão infla
contagens por fan-out (latimos isso na exploração: um join ingênuo multiplicou a contagem
de Meia Praia por ~6x).

Nomes de bairro têm grafia inconsistente entre fontes (`Meia Praia` / `Meia praia` / `meia
praia` no VivaReal; `Alto Sao Bento` sem acento no Mesh vs. `Alto São Bento` com acento no
VivaReal). **Decisão:** normalizar (`lower + strip de acentos`) antes de cruzar bairro
entre Airbnb e VivaReal — sem isso, o cruzamento de custo (VivaReal) com receita (Airbnb)
por bairro fica subestimado.

### 5.3 Receita: proxy de ocupação (premissa explícita, não dado)

O dataset não tem reservas/ocupação real — `Price_AV` é preço de calendário (disponível +
indisponível misturados, não dá pra saber se o preço listado correspondeu a uma venda).
**Decisão:** usar uma curva de ocupação por bandas de demanda relativa, calibrada com
benchmark de mercado para short-stay litoral SC em alta temporada (premissa documentada,
não medida):

- Bairros/perfis com `n_listings_priced ≥ 50` e `avg_reviews` no terço superior →
  ocupação alta-temporada assumida 70%.
- Demanda média → 55%.
- Demanda baixa ou amostra pequena → 40% (conservador, reflete incerteza).

Essa curva é o maior risco de modelagem do projeto (ver §6) e é tratada como tal — toda
tabela de receita/ROI no relatório mostra também o ADR puro (dado observado) ao lado da
receita estimada (modelo), pra não confundir as duas coisas.

### 5.4 Custo de implantação (para ROI)

Não há dado de custo de construção no dataset. **Decisão:** usar preço/m² de venda do
VivaReal por bairro/dormitórios como proxy de valor de mercado do imóvel pronto, e aplicar
um fator de 65% sobre esse valor como proxy de custo de implantação (terreno + obra),
premissa conservadora documentada — não é uma estimativa de orçamento de obra real.

### 5.5 Stack técnico

- **uv + pyproject.toml** para dependências (sem requirements.txt solto).
- **Polars** para wrangling (schemas tipados, performance em CSVs de até ~118k linhas
  como `Price_AV`).
- **DuckDB** para joins/agregações relacionais (dedup por `row_number()`, agregações por
  corte) — mais natural em SQL do que em Polars puro para este tipo de pergunta.
- Sem Jupyter, sem pandas (exceto se algo específico do DuckDB exigir, a justificar
  inline no código se acontecer).

## 6. Riscos e limitações

1. **Cobertura de preço baixa**: só ~1.005 dos 4.441 listings do Details (~22%) têm preço
   em `Price_AV`. Toda métrica de ADR/receita é sobre esse subconjunto, não sobre o
   mercado total de Itapema — isso é dito explicitamente em todo output.
2. **Ocupação é premissa, não dado** (§5.3) — é o maior risco de viés do projeto. Sensibilidade
   do ROI a essa premissa é reportada (cenário otimista/conservador).
3. **Custo de implantação é proxy de mercado, não orçamento de obra** (§5.4).
4. **Sazonalidade**: a janela de estadia coberta (jan-abr) é alta temporada de verão em
   SC. Não há dado de baixa temporada — qualquer extrapolação para ROI anual (2025-2027)
   assume uma curva de sazonalidade documentada como premissa, não inferida do dataset.
5. **Amostra pequena em cortes finos** (bairro × dormitórios simultâneo) — reportado mas
   não usado como base de decisão sozinho.

## 7. Fora de escopo

- Modelo de elasticidade de preço (quanto a receita mudaria se o ADR fosse diferente).
- Comparação com outras cidades (o desafio é só Itapema).
- Dashboard interativo (Streamlit/Lovable) — pode ser entregue como bônus, não bloqueia a
  entrega principal.
