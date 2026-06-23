# Code Review — PR: feat/system-price-v2

**Branch:** `pr-review/feature-system-price-v2`  
**Arquivo principal:** `pipelines/system_price_v2.py`  
**SQL:** `pipelines/gold_system_price_itapema.sql`  
**Revisor:** AI Builder Challenge  
**Data:** 2026-06-23

---

## Veredicto: CHANGES REQUIRED — não mergear

Este PR tem **bugs que corrompem silenciosamente o output** (fan-out de join,
mistura de fontes incompatíveis, re-run acumula dados) e **um vazamento de
credencial** que deve ser tratado como incidente de segurança antes de qualquer
outra coisa. O dashboard de RM que consumir esta tabela receberá números errados
sem nenhum aviso.

---

## Top 3 issues críticos

### C1 — Fan-out: Mesh e Hosts não são deduplicados antes do join

**Arquivo:** `system_price_v2.py`, `enrich_with_bairro()` (linha ~40) e
`enrich_with_host_features()` (linha ~50)

`Mesh_Ids_Data_Itapema.csv` e `Hosts_ids_Itapema.csv` são **séries temporais
incrementais** — cada entidade (listing / host) tem uma linha por data de captura
(o Mesh tem ~99 snapshots). Fazer `.merge()` direto multiplica cada linha de preço
pelo número de snapshots da entidade, inflando contagem e média.

**Impacto:** `n_amostras` no gold fica ~6× o real; `system_price_avg` é a média
dos preços originais mas com pesos distorcidos. O dashboard exibe números plausíveis
que estão errados.

**Correção:** deduplicar ambas as fontes **antes** do join, mantendo só a linha mais
recente por `airbnb_listing_id` / `owner_id`:

```python
mesh_latest = mesh_df.sort_values("aquisition_date").groupby("airbnb_listing_id").last().reset_index()
hosts_latest = hosts_df.sort_values("host_snapshot_date").groupby("owner_id").last().reset_index()
```

---

### C2 — Credencial em texto claro no código-fonte

**Arquivo:** `system_price_v2.py`, linhas 14–15

```python
DB_USER = "sz_data_edge"
DB_PASSWORD = "Sz!DataEdge2025"
```

As credenciais estão hardcoded e vão entrar no histórico do Git para sempre.
Mesmo que o PR não seja mergeado, o commit já existe no branch.
Adicionalmente, `DB_USER` e `DB_PASSWORD` não são usados em lugar nenhum do
código (DuckDB local não usa autenticação) — provavelmente copilados de outro
contexto. Mas a senha vaza de qualquer forma.

**Ação imediata necessária:** rotar a senha `Sz!DataEdge2025` no serviço onde ela é
usada (warehouse? Metabase?). Não adianta remover do código se o commit já está na
história.

**Correção no código:** remover as constantes; se credenciais forem necessárias no
futuro, usar variáveis de ambiente (`os.environ["DB_PASSWORD"]`) e adicionar
`.env` ao `.gitignore`.

---

### C3 — VivaReal misturado com ADR Airbnb: fontes incompatíveis

**Arquivo:** `system_price_v2.py`, `normalize_vivareal()` (linha ~68) e
`build_stage()` (linha ~80)

O código calcula `vivareal_df["price"] = vivareal_df["rental_price"] / 30` e faz
`pd.concat([short_term[["suburb", "price"]], vivareal_norm])` antes do `AVG(price)`.

Dois problemas:
1. **Fontes incompatíveis:** VivaReal é portal de **venda/aluguel de longa duração**.
   Dividir aluguel mensal por 30 não gera uma diária de short-stay — o perfil de
   imóvel, localização e contrato são diferentes. ADR Airbnb de Meia Praia é
   ~R$699/noite; aluguel mensal de longa duração dividido por 30 é ~R$80–120/noite.
   Misturar puxa a média fortemente para baixo, distorcendo o "system price".
2. **Coluna provavelmente inexistente:** o dataset VivaReal tem `sale_price` e
   `monthly_condo_fee`, mas não `rental_price`. O código vai lançar `KeyError` em
   produção com o CSV real.

**Correção:** remover o bloco de VivaReal do pipeline de ADR. VivaReal é sinal de
custo de aquisição (preço/m²), não de preço de mercado de curto prazo.
Se o objetivo é ter "sinal complementar de mercado", documentar isso como métrica
separada com nome distinto (ex: `rental_yield_proxy`), nunca concatenar na mesma
série de preço.

---

## Bugs adicionais identificados (severidade alta)

### B1 — Re-run acumula dados: INSERT INTO sem TRUNCATE

**Arquivo:** `gold_system_price_itapema.sql`

```sql
CREATE TABLE IF NOT EXISTS gold_system_price_itapema (...);
INSERT INTO gold_system_price_itapema SELECT ...
```

Cada execução do pipeline **acrescenta** novas linhas sem apagar as antigas.
Rodar duas vezes = dois registros por bairro. O DuckDB file cresce sem limite e
o `AVG` no dashboard agrega dados duplicados.

**Correção:** usar `CREATE OR REPLACE TABLE` (DuckDB suporta) ou um `DELETE FROM`
antes do INSERT, ou usar `INSERT OR REPLACE` com chave primária definida.

### B2 — `prices_df["date"]` — coluna não existe no CSV

**Arquivo:** `system_price_v2.py`, `filter_last_quarter()` (linha ~31)

```python
prices_df["date"] = pd.to_datetime(prices_df["date"])
```

O CSV de preços tem a coluna `aquisition_date`, não `date`. Isso lança `KeyError`
na primeira linha do `filter_last_quarter()`. O pipeline nunca roda de verdade com
os dados reais — o autor provavelmente testou com um CSV diferente ou nomeado
manualmente.

**Correção:** `prices_df["aquisition_date"] = pd.to_datetime(prices_df["aquisition_date"])`

### B3 — `hosts_df['owner']` — coluna não existe

**Arquivo:** `system_price_v2.py`, `enrich_with_host_features()` (linha ~51)

```python
print(f"[INFO] hosts carregados: {hosts_df['owner'].head(5).tolist()}")
```

A coluna é `owner_id`, não `owner`. Lança `KeyError` antes de qualquer join.

### B4 — Exception silenciada em load_csvs()

**Arquivo:** `system_price_v2.py`, `load_csvs()` (linha ~22)

```python
except Exception:
    pass
```

Se qualquer CSV falhar (arquivo não encontrado, encoding errado, coluna faltando),
o `except` captura tudo e `load_csvs()` retorna sem valores definidos para todos
os DataFrames. A próxima linha `print(f"[INFO] {len(prices)} linhas...")` lança
`UnboundLocalError: local variable 'prices' referenced before assignment` — mensagem
de erro completamente enganosa que não indica qual arquivo falhou.

**Correção:** remover o try/except ou relançar com mensagem clara:
```python
except FileNotFoundError as e:
    raise RuntimeError(f"CSV não encontrado: {e}") from e
```

### B5 — Limpeza de taxa de limpeza inflaciona ADR

**Arquivo:** `system_price_v2.py`, `build_stage()` (linha ~78)

```python
short_term["price"] = short_term["price"] + short_term["cleaning_fee"].fillna(0)
```

`cleaning_fee` é cobrada **uma vez por reserva**, não por noite. Somá-la ao preço
diário inflaciona o ADR de forma não-linear dependendo do tamanho da estadia.
Se a lógica é refletir custo total para o hóspede, a taxa de limpeza precisa ser
amortizada pela estadia média — que não está disponível no dataset.

**Correção:** remover a soma ou documentar explicitamente como premissa com nome
de coluna separado (`effective_daily_cost_with_cleaning`) para não contaminar o
`system_price_avg`.

### B6 — Normalização de suburb ausente no GROUP BY

**Arquivo:** `gold_system_price_itapema.sql` (linha ~18)

```sql
GROUP BY suburb
```

O campo `suburb` vem do Mesh sem normalização. Variações como `"Meia Praia"`,
`"meia praia"`, `"meia-praia"` geram bairros distintos no gold. O dashboard de RM
vai mostrar o mesmo bairro em múltiplas linhas com amostras fracionadas.

**Correção:** normalizar no Python antes do `con.register("stage", combined_df)`:
```python
combined_df["suburb"] = combined_df["suburb"].str.lower().str.strip()
```
Ou usar `LOWER(TRIM(suburb))` no SQL.

### B7 — `datetime.now()` torna o pipeline não-determinístico

**Arquivo:** `system_price_v2.py`, `filter_last_quarter()` (linha ~29)

```python
today = datetime.now()
cutoff = today - timedelta(days=QUARTER_DAYS)
```

Rodar o pipeline em dias diferentes gera outputs diferentes para o mesmo conjunto
de dados de entrada. Isso impossibilita validação, reproductibilidade e comparação
histórica. Um pipeline de dados deve ter um `reference_date` explícito, recebido
como parâmetro ou extraído da data máxima dos dados.

---

## Resumo de bugs

| ID | Severidade | Descrição | Arquivo |
|----|-----------|-----------|---------|
| C1 | Crítico | Fan-out: Mesh/Hosts não deduplicados, n_amostras ~6× real | system_price_v2.py |
| C2 | Crítico | Credencial hardcoded, precisa rotação imediata | system_price_v2.py |
| C3 | Crítico | VivaReal misturado com ADR (fontes incompatíveis) | system_price_v2.py |
| B1 | Alto | INSERT acumula dados a cada run sem truncate | gold_system_price_itapema.sql |
| B2 | Alto | KeyError: coluna `date` não existe (é `aquisition_date`) | system_price_v2.py |
| B3 | Alto | KeyError: coluna `owner` não existe (é `owner_id`) | system_price_v2.py |
| B4 | Alto | Exception silenciada esconde todo erro de carregamento | system_price_v2.py |
| B5 | Médio | cleaning_fee somada ao ADR infla preço incorretamente | system_price_v2.py |
| B6 | Médio | GROUP BY suburb sem normalização gera duplicatas de bairro | gold_system_price_itapema.sql |
| B7 | Médio | datetime.now() torna output não-determinístico | system_price_v2.py |

---

## Gaps de processo upstream

### G1 — Ausência de spec técnica antes do código

O PR descreve que a spec foi "alinhada com a Anna em 22/04" mas não há documento
commitado que formalize: definição de "system price", regras de join, premissas de
occupancy, fonte primária de bairro. Resultado: ambiguidades viraram decisões de
implementação implícitas no código (VivaReal como "sinal complementar", cleaning_fee
somada ao preço) sem revisão prévia.

**Processo sugerido:** exigir `spec.md` no mesmo PR ou em PR antecedente. Revisão
de especificação é mais barata que revisão de código com bug de negócio.

### G2 — Sem testes automatizados ou validação de schema

O autor menciona "validei batendo o olho no count de linhas". Não há assertions sobre:
- contagem esperada de bairros
- intervalo aceitável de ADR (ex: ADR < R$50 ou > R$5.000 é suspeito)
- ausência de NULLs no campo `bairro` da gold
- idempotência (resultado de 2 runs = resultado de 1 run)

Um bug de fan-out de 6× passa despercebido se a validação é visual. Contagens altas
"parecem ok" quando você não sabe o valor esperado.

### G3 — Checklist de PR não inclui "rodei com os dados reais do repo"

Os bugs B2 e B3 (KeyError em colunas inexistentes) teriam sido detectados se o
pipeline tivesse rodado uma vez com os CSVs do repo. O PR descreve "terminou sem
erro" — sugerindo que o teste local usou dados diferentes ou CSV renomeado.

**Processo sugerido:** adicionar ao template de PR: `[ ] rodei localmente com os
arquivos em `data/` deste repositório (sem renomear)` como bloqueador de merge.

---

## Script para 1:1 com o autor do PR

> Contexto: reunião individual, tom direto mas construtivo. O objetivo não é punir
> — é garantir que a pessoa aprenda os padrões antes de mergear o próximo PR.

---

**Abertura**

"Obrigado por avançar no pipeline System Price — eu sei que você estava com pressão
para entregar antes do sprint review. Eu revisei o PR e tenho alguns pontos importantes
que precisamos resolver antes de mergear. Alguns são correções rápidas, mas um
precisa de ação agora, antes de qualquer outra coisa."

---

**Credencial (C2) — deve ser o primeiro assunto**

"Tem uma senha hardcoded no arquivo Python — `Sz!DataEdge2025`. Independente de ser
ou não a senha de produção, ela está no histórico do Git agora. Precisamos rotar essa
credencial hoje. Você sabe em qual serviço ela é usada? [esperar resposta] Enquanto
a gente conversa sobre o restante, você consegue acionar o time responsável pela
rotação?"

---

**Fan-out (C1) — o bug mais silencioso**

"Olha esse join com o Mesh — você sabia que o arquivo `Mesh_Ids_Data_Itapema.csv`
tem múltiplas linhas por listing? É um snapshot incremental, com uma linha por data
de captura. Quando você faz `.merge()` direto, cada preço é multiplicado pelo número
de snapshots. Isso significa que o `n_amostras` que aparece no gold está provavelmente
6x acima do real. O problema é que o número *parece plausível* — não é um NaN, não
quebra o pipeline. Como você estava validando o output?"

[ouvir a resposta; discutir como detectar sem teste automatizado]

"A correção é simples: antes do join, deduplicar o Mesh mantendo só a última linha
por listing. Posso te mostrar. O importante é entender o padrão: qualquer fonte com
`aquisition_date` ou `snapshot_date` é uma série temporal, não uma tabela de
entidades. Esse cuidado precisa ser o default na hora de escrever qualquer join."

---

**VivaReal (C3)**

"Sobre a parte do VivaReal — entendo a intenção de ter um 'sinal complementar de
mercado'. Mas o VivaReal é preço de venda/aluguel de longa duração. Dividir aluguel
mensal por 30 não vira diária de Airbnb — o perfil de imóvel é diferente, a localização
é diferente, o mercado é diferente. Misturar os dois num mesmo `AVG(price)` puxa o
system price para baixo de forma que não representa nenhum dos dois mercados de verdade.
O que a Anna disse exatamente que queria como 'sinal complementar'? [ouvir] Ok — então
a melhor forma de entregar isso é como uma coluna separada, com nome que deixe claro
a origem, nunca concatenado ao ADR do Airbnb."

---

**Próximos passos acordados**

"Vou colocar todos os pontos como comentários no PR. O que você precisa fazer:
1. Rotar a credencial hoje
2. Corrigir os KeyErrors (B2, B3) — são literais, 2 minutos cada
3. Deduplicar Mesh e Hosts antes do join
4. Remover a parte do VivaReal ou segregar como coluna separada
5. Adicionar `CREATE OR REPLACE TABLE` no SQL

Depois disso, me chama que revejo. E para os próximos PRs: antes de codar, joga
a definição do que você está implementando num `spec.md` e coloca para eu olhar —
é mais fácil ajustar a lógica antes de ter código escrito."

---

*Fim do script*
