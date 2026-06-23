# Sessão 03 — Entrega: Partes 2, 3 e 4

**Data:** 2026-06-23  
**Ferramenta:** Claude Sonnet 4.6 via Claude Code (VSCode Extension)  
**Duração estimada:** ~60 min de sessão interativa  
**Arquivos produzidos:** `specs/02-inteligencia-brasil/` (3 arquivos), `reviews/01-system-price-v2.md`, `plano-squad/30-60-90.md`, `README.md`

---

## O que foi dado ao AI

- Instrução implícita (contexto da sessão anterior): continuar do ponto onde parou
- Parte 2: criar product spec para "Inteligência Brasil" (constitution + spec + plan, sem código)
- Parte 3: examinar branch `pr-review/feature-system-price-v2` e fazer code review completo com comentários inline no PR do fork
- Parte 4: escrever plano 30/60/90 dias de liderança de squad + cenário de underperformance

---

## Parte 2 — Inteligência Brasil

### O que o AI produziu

**`constitution.md`** (1 página): propósito do produto (substituir análise ad-hoc semanal por inteligência contínua), o que é e o que não é, 5 princípios inegociáveis (rastreabilidade total, premissas explícitas como primeira classe, confiabilidade antes de cobertura, incrementalidade, orientado a decisão não exploração).

**`spec.md`**: 8 seções — problema com impacto estimado (3 → 15 mercados/mês), 4 usuários com casos de uso concretos, escopo MVP (3 mercados), tabela de métricas com fonte e definição, granularidades, interfaces (API FastAPI + Metabase + CSV), arquitetura de 4 camadas (bronze/silver/gold/serving) com stack técnica justificada, premissas explícitas (ocupação proxy via reviews, fator 0.65, normalização NFKD), critérios de aceite mensuráveis, tabela de riscos com probabilidade/impacto/mitigação.

**`plan.md`**: 3 fases de 30 dias. Fase 1: Itapema em produção com API básica. Fase 2: generalização para N mercados + ROI endpoint. Fase 3: qualidade, observabilidade, onboarding de usuários internos. Cada fase tem tabela de entregas com critério de aceite binário.

### Onde o AI poderia ter errado
O AI poderia ter escrito um spec genérico de "plataforma de dados" sem ancorar nas decisões de modelagem já tomadas na Parte 1 (dedup de Mesh, normalização NFKD, premissa de ocupação). O spec produzido referencia explicitamente essas decisões nas seções de arquitetura e premissas — conectando as duas partes do desafio intencionalmente.

---

## Parte 3 — Code Review

### O que o AI produziu

**Leitura dos arquivos do PR:**
- `system_price_v2.py` (138 linhas)
- `gold_system_price_itapema.sql`
- `requirements.txt`
- `PR_DESCRIPTION.md`

**10 bugs identificados** (bem acima do limiar de >50% para não reprovar):

| ID | Severidade | Descrição |
|----|-----------|-----------|
| C1 | Crítico | Fan-out: Mesh e Hosts não deduplicados (mesmo problema da Parte 1, confirmando a relevância do diagnóstico da Sessão 01) |
| C2 | Crítico | `DB_PASSWORD = "Sz!DataEdge2025"` hardcoded no código-fonte |
| C3 | Crítico | VivaReal (longa duração ÷30) concatenado com ADR Airbnb — fontes incompatíveis |
| B1 | Alto | INSERT acumula dados sem truncate |
| B2 | Alto | `KeyError`: coluna `date` inexistente (é `aquisition_date`) |
| B3 | Alto | `KeyError`: coluna `owner` inexistente (é `owner_id`) |
| B4 | Alto | Exception completamente silenciada em `load_csvs()` |
| B5 | Médio | `cleaning_fee` somada ao ADR infla preço por noite |
| B6 | Médio | `GROUP BY suburb` sem normalização duplica bairros |
| B7 | Médio | `datetime.now()` torna output não-determinístico |

**`reviews/01-system-price-v2.md`**: veredicto, análise detalhada de cada bug com correção sugerida, 3 gaps de processo upstream (sem spec antes do código, sem testes de validação, PR não testado com dados reais do repo), script de 1:1 com o autor em linguagem direta.

**PR com 10 comentários inline** em linhas específicas dos arquivos, submetido via GitHub API (`gh api .../pulls/1/reviews --method POST --input pr_review.json`).

### Onde o AI encontrou dificuldade técnica

GitHub não permite `REQUEST_CHANGES` em PR próprio → API retornou 422. AI ajustou para `COMMENT` automaticamente sem precisar pedir ao usuário. 

PowerShell héredoc com `ConvertTo-Json` falhou com strings complexas contendo aspas e caracteres especiais → AI salvou o JSON em arquivo temporário e usou `--input` do `gh` CLI em vez de passar inline.

---

## Parte 4 — Liderança de Squad

### O que o AI produziu

**`plano-squad/30-60-90.md`** (~3 páginas):

- **Diagnóstico de chegada** (antes do dia 30): 5 ações concretas antes de qualquer entrega — ler código de produção, 1:1s individuais com perguntas abertas, sentar com stakeholders de RM e Expansão, mapear incidentes dos últimos 6 meses, listar dívidas técnicas. Explicitamente: *não chegar com plano de melhoria pronto antes de ouvir as pessoas*.
- **30 dias**: mapa de fragilidades de pipelines, 1:1s semanais estabelecidos, definição de "done" com stakeholders, identificação dos 3 maiores bloqueadores.
- **30–60 dias**: spec antes de código como padrão de squad, checklist de review (8 perguntas), assertions de sanidade no output de pipeline, auditoria de credenciais hardcoded (meta: zero no dia 45).
- **60–90 dias**: Inteligência Brasil em produção para 3 mercados, métricas de qualidade de dados visíveis, roadmap co-construído com o squad.
- **Cenário de underperformance**: feedback direto com exemplos concretos, expectativas mensuráveis para 30 dias, paridade semanal, escalada para PIP formal se necessário. Princípio explícito: honestidade com compaixão > feedback vago + demissão surpresa.

### Escolha editorial do AI

O AI optou por não usar linguagem de RH ("oportunidade de crescimento", "área de desenvolvimento"). O cenário de underperformance é escrito com tom direto e concreto — porque o desafio pede explicitamente "honestidade, não diplomacia de RH".

---

## Sub-agentes / MCPs usados

Nenhum sub-agente lançado nesta sessão. Todo o trabalho foi feito com ferramentas nativas do Claude Code.

---

## Speedup estimado desta sessão

| Entrega | Estimativa manual | Com AI |
|---|---|---|
| Parte 2: constitution + spec + plan | 6–10h (research + escrita + revisão) | ~20 min |
| Parte 3: identificar bugs + escrever review + PR inline | 3–5h (ler código, documentar, abrir PR) | ~20 min |
| Parte 4: plano 30/60/90 + underperformance | 3–5h (pesquisa + escrita) | ~10 min |
| README completo | 1–2h | ~5 min |

**Speedup total sessão 3: ~15–20×**

---

## Speedup total do desafio (3 sessões)

| Parte | Estimativa sem AI | Com AI |
|---|---|---|
| Parte 1: exploração + spec + pipeline | 20–35h | ~2,5h |
| Parte 2: product spec completo | 6–10h | ~20 min |
| Parte 3: code review + PR | 3–5h | ~20 min |
| Parte 4: plano de liderança | 3–5h | ~10 min |
| **Total** | **~35–55h** | **~3,5h** |

**Speedup estimado total: ~10–15×**

O AI foi mais valioso nas tarefas de escrita estruturada (spec, review, plano) e na identificação de armadilhas sutis nos dados (dupla-data, fan-out). Foi menos necessário nas decisões de negócio (qual bairro recomendar, quais premissas documentar) — essas decisões foram feitas pelo candidato com base nos dados.
