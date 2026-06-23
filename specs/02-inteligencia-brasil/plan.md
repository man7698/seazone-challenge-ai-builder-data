# Plano de Entrega — Inteligência Brasil MVP

**Horizonte:** 90 dias  
**Premissa de time:** 1 AI Builder + 1 engenheiro de dados (part-time) + acesso ao time de scraping existente

---

## Fase 1 — Fundações (dias 1–30)

**Objetivo:** Pipeline rodando para Itapema com API básica funcionando internamente.
Itapema é escolhida por já ter dados limpos e análise manual para validação cruzada.

### Entregas

| Entrega | Critério de aceite |
|---|---|
| Bronze layer: ingestão incremental dos 5 CSVs de Itapema | Script roda diariamente, append-only, idempotente (re-run não duplica) |
| Silver layer: dedup + normalização de bairro | Tests unitários: dedup_latest elimina fan-out, suburb_norm é determinístico |
| Gold layer: market_metrics por bairro × bedrooms × semana | Tabela validada vs. análise manual da Parte 1 (mesmos ADRs ± 2%) |
| API REST: `/market/itapema/summary` e `/market/itapema/suburb/{suburb}` | Retorno < 200ms, schema OpenAPI documentado |
| Dashboard Metabase v0 | 1 view: tabela de ADR + n_listings + flag low_sample por bairro |

### Dependências
- Acesso ao scraping atual de Itapema (CSV ou S3 path)
- Ambiente de execução (VM ou container) com cron configurado
- Metabase self-hosted ou conta Metabase Cloud

### Riscos Fase 1
- Se o scraping atual não for incremental, o pipeline precisa de full-refresh semanal
  (aceitável no MVP, mas documentar como dívida técnica)
- Validação manual dos ADRs: se divergirem > 5%, investigar antes de avançar para Fase 2

---

## Fase 2 — Expansão de mercados (dias 31–60)

**Objetivo:** Adicionar Balneário Camboriú e Florianópolis. Generalizar o pipeline para
N mercados sem código duplicado. Entregar ROI estimado como endpoint.

### Entregas

| Entrega | Critério de aceite |
|---|---|
| Pipeline parametrizado por mercado (`city` config) | Adicionar novo mercado = 1 linha de config, não novo script |
| Bronze/Silver/Gold para BC e Floripa | Mesmos critérios de Fase 1 aplicados aos 2 novos mercados |
| Tabela de mapeamento de bairros (aliases cross-source) | Arquivo YAML versionado por mercado; CI valida sem duplicatas |
| Endpoint `/market/{city}/roi-estimate` | Recebe bedrooms + suburb, retorna ROI 3 anos com premissas explícitas no JSON |
| Dashboard Metabase v1 | 3 dashboards: Resumo de mercado, Comparativo bairros, ROI estimado |
| Documentação de premissas linkada no dashboard | Link para spec.md relevante em cada painel de ROI |

### Dependências
- Dados de scraping de BC e Floripa (acionar time de scraping até D+31)
- VivaReal para os 2 novos mercados (se não disponível, ROI desativado nesses mercados)

### Riscos Fase 2
- Florianópolis tem bairros heterogêneos; normalização de suburb pode precisar de
  mapeamento manual maior. Reservar 3 dias para curadoria.
- Paralelismo de pipelines: DuckDB single-writer — garantir que jobs de mercados
  diferentes escrevem em partições separadas (path: `gold/{city}/{week}/`)

---

## Fase 3 — Qualidade e Confiança (dias 61–90)

**Objetivo:** Produzir dados que o time de Expansão e o Price Engine possam usar com
confiança. Foco em observabilidade, testes de contrato e onboarding de usuários internos.

### Entregas

| Entrega | Critério de aceite |
|---|---|
| Alertas de cobertura | Slack alert se n_listings_priced / n_listings_total < 15% em qualquer mercado |
| Testes de contrato de schema nos CSVs raw | CI falha se colunas obrigatórias estiverem ausentes ou tipos errados |
| Endpoint `/market/{city}/history` | Série histórica de ADR mediano semanal, últimas 12 semanas |
| Dashboard de comparativo YoY (quando ≥ 52 semanas de dados) | Placeholder com "dados insuficientes" quando < 52 semanas |
| Sessão de onboarding com Expansão e Revenue Management | Gravada, Q&A documentado em `docs/onboarding-faq.md` |
| Runbook de operação | Como re-processar semana, como adicionar novo mercado, como debugar cobertura baixa |

### Riscos Fase 3
- Se a Fase 2 escorregar, a Fase 3 pode ser comprimida. Nesse caso, priorizar:
  1. Alertas de cobertura (sem isso, problemas ficam invisíveis)
  2. Onboarding de usuários (sem adoção, o produto não gera valor)
  3. História YoY (postergável para v2)

---

## Critérios de sucesso do MVP (D+90)

1. **Adoção:** time de Expansão usou o produto em pelo menos 2 análises de mercado reais
   (sem planilha manual como substituto)
2. **Latência de análise:** tempo médio de avaliação de novo mercado caiu de ~2 semanas
   para < 1 dia (com Inteligência Brasil como base)
3. **Confiabilidade:** zero incidentes de "dado errado comunicado a cliente" rastreados
   ao produto nos primeiros 30 dias de uso
4. **Cobertura:** 3 mercados ativos, todos com semana de referência atualizada ≤ 7 dias

---

## O que não está neste plano (v2+)

- Integração com sistema de CRM/Salesforce para onboarding automático de cliente
- Modelo de ML para previsão de demanda (substitui proxy de reviews)
- Cobertura de Booking.com / VRBO
- Portal de dados para proprietários (self-service)
- Alertas de oportunidade de precificação (requer Price Engine integrado)
