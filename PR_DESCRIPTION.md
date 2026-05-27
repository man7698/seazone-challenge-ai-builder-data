# feat: pipeline System Price v2 — média por bairro Itapema (último trimestre)

## O que mudou

Implementação do pipeline que calcula o System Price médio por bairro de Itapema no último trimestre. A saída expõe uma tabela `gold_system_price_itapema` consumida pelo dashboard de RM.

Segui o spec combinado com a Anna no dia 22/04:

- Fonte primária: `Price_AV_Itapema` (preço por noite, por dia)
- Bairro a partir do `Mesh_Ids_Data_Itapema`
- Enriqueço com `Details_Itapema` e `Hosts_ids_Itapema` para permitir segmentações futuras (superhost, tipo de listing)
- Sinal complementar de mercado a partir do `VivaReal_Itapema`
- Período: últimos 90 dias (1 trimestre)
- Granularidade da gold: 1 linha por bairro

## Como rodar

```bash
pip install -r pipelines/requirements.txt
python pipelines/system_price_v2.py
```

A saída fica em `gold/system_price_itapema.duckdb`. O próprio script imprime o top 10 ao final.

## Validação

- Joins parecem ok, validei batendo o olho no count de linhas no log
- Rodei localmente, terminou sem erro
- VivaReal entra como sinal complementar de mercado (média ponderada do aluguel mensal)

## Próximos passos

- Schedular via Airflow (separar em PR)
- Adicionar segmentação por `is_superhost` quando o dashboard pedir
