# Sessão 01 — Discovery: exploração dos dados e armadilhas

**Data:** 2026-06-23  
**Ferramenta:** Claude Sonnet 4.6 via Claude Code (VSCode Extension)  
**Duração estimada:** ~45 min de sessão interativa  
**Arquivos produzidos:** `specs/01-bi-itapema/spec.md`, `specs/01-bi-itapema/plan.md`

---

## O que foi dado ao AI

- PDF do desafio completo (4 partes)
- Pergunta inicial: "tenho esse desafio pra fazer, consegue me ajudar??"
- Perguntas de clarificação respondidas: setup do ambiente (nada feito ainda), por onde começar (Parte 1), sessões de AI (candidato exporta depois)
- Acesso ao repositório forkeado com os 5 CSVs em `data/`

## O que o AI produziu

### Exploração inicial dos dados
O AI leu os 5 CSVs e identificou:
- **Mesh e Hosts são séries temporais** (não 1:1): Mesh tem 99 datas de aquisição distintas; join direto causa fan-out ~6×
- **Price_AV: armadilha da dupla-data**: `max(aquisition_date)` retorna 1 listing (timestamp quase único por listing por dia); filtro correto é `date_trunc('day', aquisition_date)`
- **Incompatibilidade de nomes de bairro**: "Meia Praia" vs "meia praia" vs "Alto São Bento" vs "Alto Sao Bento" entre Airbnb (Mesh) e VivaReal
- **Cobertura limitada**: apenas 22% dos listings têm preço na onda de referência — documentado como risco, não ignorado

### spec.md produzido (antes de qualquer código)
Seções: definição operacional de "melhor" (≥10 listings), seleção da onda de preço (§5.1), dedup incremental (§5.2), bandas de ocupação como premissa (§5.3), proxy de custo via VivaReal (§5.4), stack técnica (§5.5), 6 riscos explícitos.

### plan.md produzido (antes de qualquer código)
6 passos com dependências explícitas: bronze → silver → métricas por corte (paralelo ao cruzamento de custo) → decisão de localização → ROI → consolidação.

## Onde o AI errou + correção

| Erro | Correção aplicada |
|---|---|
| Primeira tentativa de instalar `gh` CLI via `winget` — MSI travou aguardando elevação UAC (processo interativo não disponível) | AI identificou o travamento, matou o processo `msiexec` (PID 11416) e instalou via zip portátil extraído em `%LOCALAPPDATA%\Programs\gh-cli\bin\` |
| Ambiente Python: AI tentou usar `python` no terminal mas só existia o stub da Microsoft Store | Corrigido: uso exclusivo de `uv` para gerenciar Python; nunca chamar `python` diretamente no PATH do sistema |
| PATH do `gh` não persistia entre chamadas de PowerShell | Cada comando passou a prefixar `$env:PATH = [System.Environment]::GetEnvironmentVariable(...)` explicitamente |

## Speedup estimado

Exploração manual dos 5 CSVs + identificação das armadilhas (dupla-data, fan-out, normalização): estimado 6–10h de trabalho manual.  
Com AI: ~25 min de leitura e análise dos arquivos.  
**Speedup: ~15–20×** nesta fase.

---

*Nota: esta sessão identificou as armadilhas que definiram todas as decisões de implementação subsequentes. Sem esse diagnóstico correto, o pipeline produziria números silenciosamente errados.*
