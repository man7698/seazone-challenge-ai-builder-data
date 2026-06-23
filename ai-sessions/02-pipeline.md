# Sessão 02 — Pipeline: implementação da análise Itapema

**Data:** 2026-06-23  
**Ferramenta:** Claude Sonnet 4.6 via Claude Code (VSCode Extension)  
**Duração estimada:** ~90 min de sessão interativa  
**Arquivos produzidos:** `analysis/` inteiro (pyproject.toml, 8 módulos Python, output/)

---

## O que foi dado ao AI

- spec.md e plan.md já commitados (Sessão 01)
- Instrução: implementar os 6 passos do plan.md usando uv + polars-lts-cpu + DuckDB
- Restrição de ambiente: máquina com Intel i3-3110M (Ivy Bridge, sem AVX2/FMA/BMI2)
- Objetivo: pipeline completo que responde as 5 questões de investimento e escreve `answers.json`

## O que o AI produziu

### Estrutura de módulos
- **`load.py`**: leitura dos 5 CSVs com `null_values` explícitos, `try_parse_dates=True`, `infer_schema_length=5000`, cast explícito de `is_superhost` para boolean
- **`clean.py`**: `normalize_suburb()` via NFKD+lower, `dedup_latest()` por sort+group_by.first(), `price_wave()` com filtro por `dt.date()` (não por timestamp exato)
- **`metrics.py`**: DuckDB SQL sobre DataFrames Polars via replacement scan — ADR por bairro, por dormitórios, cruzamento bairro×dormitórios, demanda por bairro, correlações de Pearson
- **`cost.py`**: custo/m² via VivaReal (having n ≥ 5), taxa de condomínio por bairro, fator 0.65
- **`roi.py`**: dataclass `UnitType`, ramp-up de ocupação por ano (55%/90%/100%), crescimento de ADR (1.0/1.05/1.10), projeção 2025-2027 com NOI/ROI%
- **`run.py`**: orquestrador — avalia ROI por **todos** os bairros candidatos confiáveis (não só o de maior ADR), compara 3 cenários de mix, escolhe por max ROI% 2027
- **`timing.py`**: medição de pico RSS real via thread de sampling psutil (20ms), não tracemalloc (que não captura alocações nativas de Polars/DuckDB)
- **`paths.py`**: constantes de path com criação automática de diretórios

### Resultado do pipeline
```
Melhor localização por receita (H2): meia praia  (ADR R$699/noite)
Melhor localização pra CONSTRUIR o prédio (H4): centro  (ROI 15,3% em 2027)
ROI 2027 por bairro candidato:
  meia praia: 6.05%  |  tabuleiro dos oliveiras: 14.64%
  centro: 15.30%     |  morretes: 4.43%
```

### Insight analítico central (não óbvio)
Meia Praia tem maior ADR → maior receita → mas custo/m² elevado → menor ROI%.  
Centro tem ADR inferior, mas custo/m² similar + área menor (70m² × 50 aptos) → menor investimento → melhor ROI%.  
Este divergência entre Q2 (melhor receita) e Q4 (melhor para construir) é a contribuição analítica mais valiosa da Parte 1.

## Onde o AI errou + correção

| Erro | Correção aplicada |
|---|---|
| `polars` padrão instalado primeiro — crash imediato com "Missing required CPU features: avx2, fma, bmi1, bmi2" na máquina sem AVX2 | AI diagnosticou o erro, removeu `polars` e adicionou `polars-lts-cpu==1.33.1` via `uv remove polars && uv add polars-lts-cpu` |
| Anaconda Python interferindo: `uv run` sem `--python 3.12` detectou `cpython-3.7.6` da Anaconda e tentou ler `pyodbc-4.0.0_unsupported.dist-info` (versão malformada) | Corrigido usando `uv run python -m itapema_bi.run` dentro do projeto (venv com Python correto) |
| Output com caracteres não-ASCII causava `UnicodeEncodeError` no PowerShell cp1252 | Corrigido: `$env:PYTHONUTF8=1` e `$env:PYTHONIOENCODING="utf-8"` antes de rodar |
| Primeiro draft de `run.py` escolhia localização = melhor ADR (Meia Praia) fixo, sem avaliar ROI por bairro | Refatorado: `run.py` itera todos os bairros confiáveis, calcula ROI para cada cenário, escolhe por max ROI% — resultado divergiu de Meia Praia para Centro |
| Dead code em `load.py`: branch `if False else` no draft inicial | Removido com Edit tool imediatamente ao identificar |
| Join de ADR por bairro retornando 1 linha: primeiro teste manual usou `max(aquisition_date)` que retorna timestamp único | Confirmado empiricamente (day-trunc = 780 listings; max timestamp = 1 listing); corrigido via `dt.date()` no clean.py |

## Sub-agentes / MCPs usados

Nenhum sub-agente lançado nesta sessão. Todo o trabalho foi feito diretamente via ferramentas do Claude Code (Edit, Write, Read, Bash, PowerShell).

## Speedup estimado

Implementação manual de 8 módulos Python com DuckDB + Polars + psutil, debug de ambiente Windows, iteração até resultado correto: estimado 12–20h.  
Com AI: ~80 min de implementação iterativa.  
**Speedup: ~10–15×** nesta fase.

---

*Nota: o erro mais sutil desta sessão foi o fan-out de join — identificado na Sessão 01 via exploração, mas precisou de confirmação empírica (contagem antes/depois de dedup_latest) para garantir que estava corrigido no código.*
