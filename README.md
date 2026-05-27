# seazone-challenge-data-coordenator

Repositório base do desafio técnico para a vaga de **Coordenador de Dados — squad Data Edge** (Seazone).

A descrição completa do desafio está no PDF enviado por e-mail. Este repositório serve como ponto de partida: contém o dataset que você vai usar nas Partes 1 e 2 e a branch com o PR sintético para a Parte 3.

## Conteúdo

### Branch `main`
- `data/` — amostras reais de Itapema (Airbnb + VivaReal), ~20 MB total
  - `Details_Itapema.csv` — detalhe de cada listing Airbnb (4.5k linhas)
  - `Hosts_ids_Itapema.csv` — perfis dos hosts (4.4k linhas)
  - `Mesh_Ids_Data_Itapema.csv` — geolocalização e bairro de cada listing (4.4k linhas)
  - `Price_AV_Itapema.csv` — preço por noite, por dia, por listing (118k linhas)
  - `VivaReal_Itapema.csv` — listings de aluguel/venda no VivaReal (8.3k linhas)

### Branch `pr-review/feature-system-price-v2`
Contém o PR sintético que você deve revisar na Parte 3:

- `pipelines/system_price_v2.py` — pipeline em Python
- `pipelines/gold_system_price_itapema.sql` — SQL da gold table
- `pipelines/requirements.txt`
- `PR_DESCRIPTION.md` — mensagem do "Júnior" abrindo o PR

> **Não modifique essa branch.** Faça fork do repositório, abra o PR de revisão a partir do seu fork (base: `main` do seu fork; compare: `pr-review/feature-system-price-v2` do seu fork) e deixe seus comentários inline.

## Setup sugerido

Python 3.11+, gerenciador de pacotes à sua escolha (uv/pip/poetry). O código da branch do PR usa `pandas` e `duckdb` — você pode rodar tudo localmente sem precisar de banco externo.

```bash
pip install -r pipelines/requirements.txt
python pipelines/system_price_v2.py
```

Para as Partes 1 e 2 você escolhe sua stack — não precisa seguir a do PR.

## Entrega

Conforme o PDF: 1 repositório público no seu GitHub com a estrutura indicada e link enviado por e-mail respondendo à thread do processo.
