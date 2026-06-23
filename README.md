# Seazone AI Builder Challenge — Entrega

Repositório de entrega do desafio técnico para a vaga de **Senior AI Builder — squad Data Edge** (Seazone).

**Candidato:** Matheus Almeida  
**Fork:** https://github.com/man7698/seazone-challenge-ai-builder-data  
**PR de revisão (Parte 3):** https://github.com/man7698/seazone-challenge-ai-builder-data/pull/1

---

## Estrutura da entrega

```
.
├── specs/
│   ├── 01-bi-itapema/          # Parte 1: spec + plan (commitados ANTES do código)
│   │   ├── spec.md
│   │   └── plan.md
│   └── 02-inteligencia-brasil/ # Parte 2: product spec (sem código)
│       ├── constitution.md
│       ├── spec.md
│       └── plan.md
├── analysis/                   # Parte 1: pipeline de análise
│   ├── pyproject.toml          # uv + polars-lts-cpu + duckdb
│   ├── src/itapema_bi/
│   │   ├── run.py              # orquestrador (entry point)
│   │   ├── load.py             # bronze: leitura dos CSVs
│   │   ├── clean.py            # silver: dedup, normalização
│   │   ├── metrics.py          # gold: ADR/demanda por corte (DuckDB)
│   │   ├── cost.py             # custo/m² via VivaReal
│   │   ├── roi.py              # projeção de ROI 2025-2027
│   │   ├── paths.py            # constantes de path
│   │   └── timing.py           # medição de tempo + pico de RSS real
│   └── output/
│       ├── answers.json        # respostas das 5 questões
│       └── timing_report.md    # eficiência computacional por etapa
├── reviews/
│   └── 01-system-price-v2.md  # Parte 3: code review completo + script de 1:1
├── plano-squad/
│   └── 30-60-90.md            # Parte 4: plano de liderança + cenário de underperformance
├── ai-sessions/               # Exportações das sessões de AI (a preencher pelo candidato)
└── data/                      # Dataset original (não modificado)
```

---

## Parte 1 — BI Itapema: como rodar

**Pré-requisito:** [uv](https://docs.astral.sh/uv/) instalado.  
Em máquinas sem AVX2 (ex: Intel i3 Ivy Bridge), `polars-lts-cpu` é usado automaticamente via `pyproject.toml`.

```bash
cd analysis
uv sync
uv run python -m itapema_bi.run
```

O pipeline escreve resultados em `analysis/output/`. Em Windows, set `PYTHONUTF8=1` se houver erro de encoding.

### Resumo dos resultados (Parte 1)

| Questão | Resposta |
|---|---|
| Perfil de imóvel mais lucrativo | Inteiro (entire_home), 2–3 dormitórios |
| Melhor localização por receita (ADR) | **Meia Praia** — ADR R$699/noite, 483 listings com preço |
| Características que mais correlacionam com ADR | star_rating > n_reviews por bairro (Pearson calculado por corte) |
| Melhor localização para construir o prédio | **Centro** — ROI 2027: 15,3% (Meia Praia tem ADR maior mas custo/m² maior → ROI apenas 6,05%) |
| Projeção de ROI para Centro (50 aptos 2-dorms) | 2025: 6,96% · 2026: 12,95% · 2027: 15,3% |

**Decisão de design chave:** melhor receita ≠ melhor ROI. O pipeline avalia ROI por todos os bairros candidatos confiáveis (n ≥ 10 listings) antes de fixar localização — não assume que o bairro de maior ADR é o mais rentável para construção.

**Premissas documentadas em `specs/01-bi-itapema/spec.md`:**
- Ocupação estimada por banda de demanda (70%/55%/40%) — sem reservas reais no dataset
- Custo de implantação = 65% × preço/m² VivaReal (proxy conservador)
- Onda de preço de referência: 2025-01-20 (filtro por dia truncado, não timestamp exato)

---

## Parte 2 — Inteligência Brasil: onde ler

`specs/02-inteligencia-brasil/`:
- `constitution.md` — por que o produto existe e o que é inegociável
- `spec.md` — escopo MVP, arquitetura de dados, métricas, premissas, riscos, critérios de aceite
- `plan.md` — entrega em 3 fases de 30 dias com DoD por entrega

Sem código — só especificação, conforme requisito.

---

## Parte 3 — Code Review: onde ler

- `reviews/01-system-price-v2.md` — veredicto, 3 issues críticos, 7 bugs adicionais, gaps de processo, script de 1:1
- **PR com comentários inline:** https://github.com/man7698/seazone-challenge-ai-builder-data/pull/1

**Bugs identificados (10 total):**

| ID | Severidade | Descrição |
|----|-----------|-----------|
| C1 | Crítico | Fan-out: Mesh e Hosts não deduplicados — `n_amostras` ~6× real |
| C2 | Crítico | Credencial hardcoded (`DB_PASSWORD`) — rotação imediata necessária |
| C3 | Crítico | VivaReal (longa duração) concatenado com ADR Airbnb (short-stay) — fontes incompatíveis |
| B1 | Alto | INSERT acumula dados a cada run sem truncate |
| B2 | Alto | `KeyError`: coluna `date` não existe (é `aquisition_date`) |
| B3 | Alto | `KeyError`: coluna `owner` não existe (é `owner_id`) |
| B4 | Alto | Exception silenciada em `load_csvs()` esconde todos os erros |
| B5 | Médio | `cleaning_fee` somada ao ADR infla preço incorretamente |
| B6 | Médio | `GROUP BY suburb` sem normalização gera duplicatas de bairro |
| B7 | Médio | `datetime.now()` torna output não-determinístico |

---

## Parte 4 — Liderança de Squad: onde ler

`plano-squad/30-60-90.md`:
- Diagnóstico de chegada (antes de qualquer mudança)
- 30 dias: mapeamento de fragilidades, 1:1s, entendimento de stakeholders
- 30–60 dias: spec antes de código, checklist de review, assertions de sanidade, zero credencial hardcoded
- 60–90 dias: Inteligência Brasil em produção, roadmap co-construído com o squad
- Cenário de underperformance: feedback direto com exemplos concretos, expectativas mensuráveis, sem arrastar 6 meses

---

## Verificação da ordem de commits (Parte 1)

O critério "spec antes de código" é verificável em `git log --reverse`:

```
f409922  specs: spec.md e plan.md da Parte 1 (BI Itapema) antes de qualquer codigo
4e4775a  feat(parte1): pipeline de analise Itapema (uv/Polars/DuckDB) - spec-driven
```

O hash `f409922` (specs) precede `4e4775a` (código) no histórico.

---

## ai-sessions/

Pasta reservada para exportação das sessões de AI usadas no desenvolvimento.  
A ser preenchida pelo candidato conforme instruções do desafio.
