# Product Spec — Inteligência Brasil

**Versão:** 0.1 (draft para avaliação)  
**Status:** Proposto  
**Data:** 2026-06-23

---

## 1. Problema

A Seazone toma decisões de expansão de portfólio e define estratégias de precificação
baseadas em análises ad-hoc por mercado. O ciclo atual tem três problemas:

- **Latência:** análise de um mercado novo leva 1–3 semanas de trabalho de analista.
- **Fragmentação:** resultados vivem em planilhas individuais, sem histórico ou
  replicabilidade.
- **Opacidade:** clientes (proprietários) recebem recomendações sem ver os dados de
  mercado que as embasam, reduzindo confiança no produto.

**Impacto estimado:** time de expansão tem capacidade atual de avaliar ~3 mercados/mês.
Com Inteligência Brasil, a meta é 15+ mercados/mês (análise automatizada) e onboarding
de cliente com contexto de mercado já na primeira conversa.

---

## 2. Usuários e casos de uso

| Usuário | Caso de uso principal | Pergunta que precisa responder |
|---|---|---|
| Analista de Expansão | Avaliar novo mercado para entrada | "Vale abrir portfólio em Balneário Camboriú em Q3?" |
| Revenue Manager | Comparar desempenho da carteira vs. mercado | "Nossos imóveis em Itapema estão acima ou abaixo do ADR de mercado?" |
| Gerente de Produto (Price Engine) | Alimentar modelo de precificação com benchmark | "Qual o ADR mediano de 2BR em meia praia na última semana de janeiro?" |
| Proprietário (via CS) | Entender o contexto de mercado do seu imóvel | "Por que meu imóvel está precificado assim?" |

---

## 3. Escopo da versão 1 (MVP — 90 dias)

### 3.1 Mercados cobertos no MVP

- Itapema (SC) — mercado já analisado manualmente, validação imediata possível
- Balneário Camboriú (SC) — segundo maior mercado da carteira
- Florianópolis (SC) — maior mercado em volume

Critério de inclusão de novos mercados no roadmap: ≥ 500 listings ativos rastreados.

### 3.2 Métricas entregues por mercado × bairro × tipo de unidade

| Métrica | Definição | Fonte |
|---|---|---|
| ADR (R$) | Preço médio diário listado, onda de referência semanal | Price_AV scraping |
| RevPAR estimado (R$) | ADR × ocupação estimada | Price_AV + ocupação proxy |
| Ocupação estimada (%) | Proxy via reviews/30d por listing ativo | Details scraping |
| n_listings ativos | Listings com preço observado no período | Price_AV + Mesh |
| ADR p25/p50/p75 | Distribuição de preços no corte | Price_AV |
| Crescimento ADR MoM (%) | Variação da mediana em relação ao mês anterior | Price_AV histórico |
| Custo/m² de mercado (R$) | Mediana de imóveis à venda por bairro | VivaReal scraping |
| ROI estimado (%) | NOI / custo implantação, premissas explícitas | Derivado |

**Filtro de confiabilidade:** cortes com n < 30 listings recebem flag `baixa_amostra`.
Exibidos, nunca silenciados, mas marcados visualmente e excluídos de rankings automáticos.

### 3.3 Granularidades suportadas

- Mercado (cidade)
- Bairro dentro do mercado
- Tipo de unidade: número de dormitórios (1, 2, 3, 4+)
- Janela temporal: últimas 4 semanas (padrão), comparável YoY quando disponível

### 3.4 Interfaces de consumo (MVP)

1. **API REST interna** (FastAPI): endpoints `/market/{city}/summary`, `/market/{city}/suburb/{suburb}`,
   `/market/{city}/roi-estimate` — consumida pelo Price Engine e pelo time de expansão
2. **Dashboard interno** (Metabase sobre DuckDB/Parquet): para analistas e revenue managers
3. **Export CSV/JSON** por mercado: para relatórios de cliente via CS

O que **não** está no MVP: portal público, app mobile, alertas automáticos, integração
com sistemas de CRM.

---

## 4. Arquitetura de dados

### 4.1 Camadas

```
[Bronze]  Raw CSVs / scraping incremental por data de captura
    ↓
[Silver]  Dedup por entidade (listing_id, snapshot mais recente),
          normalização de bairro (NFKD + lower),
          filtro de outliers de preço (< p1 ou > p99 por mercado)
    ↓
[Gold]    Métricas agregadas por corte (bairro × tipo × semana),
          tabelas de ROI por cenário
    ↓
[Serving] API REST + views Metabase
```

### 4.2 Atualização

- **Bronze → Silver:** diário, incremental (append apenas novos snapshots)
- **Silver → Gold:** semanal (toda segunda-feira, usando onda de preço da semana anterior)
- **Gold → Serving:** imediato após gold update (swap de arquivo Parquet ou refresh de view)

### 4.3 Stack técnica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Ingestão | Python + uv, scripts de scraping agendados | Consistência com stack atual da Seazone |
| Processamento | Polars (transformações) + DuckDB (SQL agregações) | Performance em memória, sem cluster |
| Armazenamento | Parquet particionado por mercado × semana | Leitura eficiente por fatia; versionável em S3 |
| Serving API | FastAPI | Leve, tipado, autodoc |
| Dashboard | Metabase (self-hosted) sobre DuckDB | BI sem ETL extra, SQL nativo |
| Orquestração | Prefect (cloud managed) ou cron + shell | Sem over-engineering para MVP |

### 4.4 Modelagem de dados gold (esquema principal)

```sql
-- tabela gold: market_metrics
CREATE TABLE market_metrics (
    city          VARCHAR,
    suburb_norm   VARCHAR,
    bedrooms      INTEGER,
    week_start    DATE,           -- segunda-feira da semana de referência
    n_listings    INTEGER,
    adr_median    DECIMAL(10,2),
    adr_p25       DECIMAL(10,2),
    adr_p75       DECIMAL(10,2),
    revpar_est    DECIMAL(10,2),  -- adr_median * occupancy_est
    occupancy_est DECIMAL(5,4),   -- premissa documentada em metadata
    low_sample    BOOLEAN,        -- n_listings < 30
    updated_at    TIMESTAMP
);
```

---

## 5. Decisões de modelagem e premissas explícitas

### 5.1 Ocupação estimada

O dataset de short-stay não contém reservas reais. A ocupação é **estimada** por proxy:
- Número de reviews por listing nos últimos 30 dias ÷ fator de conversão review/reserva
  (padrão: 1 review ≈ 2.5 reservas, baseado em estudos de mercado AirDNA/AIRDNA; ajustável)
- Alternativa para mercados com dados históricos: razão entre price waves com preço
  preenchido vs. total de datas disponíveis

**Esta premissa é exibida sempre ao lado do número de ocupação.** Usuários podem ver
qual método foi usado para cada mercado.

### 5.2 Custo de implantação

Proxy via preço de venda por m² (VivaReal) × fator 0.65 (premissa: custo de obra ≈ 65%
do valor de mercado do imóvel pronto, cobrindo terreno + construção). Risco: em mercados
de alto valorização, esse fator subestima o custo real. Explicitado no ROI output.

### 5.3 Normalização de bairro cross-source

Bairros entre Airbnb (Mesh) e VivaReal são normalizados via NFKD unicode + lowercase +
strip. Mapeamento manual de aliases (ex: "Meia-Praia" → "meia praia") mantido em
arquivo de configuração versionado por mercado.

### 5.4 O que não estimamos

- Valorização imobiliária futura (premissa = estável)
- Sazonalidade intra-anual além da onda de referência atual (parcialmente mitigado em v2)
- Custos de oportunidade ou tributação específica do investidor

---

## 6. Critérios de aceite (Definition of Done — MVP)

- [ ] API retorna summary de Itapema em < 200ms (p95) com n_listings, adr_median, revpar_est
      por bairro × bedrooms
- [ ] Todos os outputs têm `updated_at` e `source_wave_date` (rastreabilidade)
- [ ] Cortes com n < 30 têm `low_sample: true` no JSON e cor amber no Metabase
- [ ] Pipeline roda incrementalmente: re-processar semana já processada é idempotente
- [ ] Metabase tem 3 dashboards: Resumo de mercado, Comparativo bairros, Estimativa de ROI
- [ ] Documentação de premissas (este spec.md + README de cada pipeline) linkada no dashboard

---

## 7. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Cobertura de price wave < 30% (como em Itapema: 22%) | Alta | Médio | Flag low_sample + documentar como premissa; v2 usa multi-wave |
| Mudança no HTML/API do Airbnb quebra scraping | Média | Alto | Testes de contrato de schema nos CSVs raw; alertas em < 5% cobertura |
| Bairros com nomes diferentes entre fontes geram duplas | Alta | Médio | Tabela de mapeamento manual versionada; validação automática vs. lista canônica |
| ROI subestimado por fator 0.65 desatualizado | Baixa | Alto | Revisão do fator por mercado a cada 6 meses com dado de obra real quando disponível |
| DuckDB em produção não suporta concorrência de escritores | Baixa | Alto | Parquet particionado por semana: cada job escreve em partição separada |

---

## 8. Fora do escopo (v1)

- Dados de Booking.com, VRBO ou outras OTAs
- Análise de sentimento de reviews
- Precificação dinâmica (produto separado)
- Dados de demanda por eventos locais (carnaval, Réveillon)
- Interface de usuário para proprietários finais (via CS por ora)
