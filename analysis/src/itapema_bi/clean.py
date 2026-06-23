"""Camada silver: deduplicacao das fontes incrementais (Mesh, Hosts), normalizacao
de bairro entre fontes, e filtro da onda de aquisicao de preco de referencia.

Ver specs/01-bi-itapema/spec.md SS5.1 e SS5.2 para o raciocinio por tras de cada
decisao aqui - este modulo so implementa o que ja foi justificado na spec.
"""

import unicodedata

import polars as pl

from itapema_bi.paths import PRICE_WAVE_REFERENCE


def normalize_suburb(col: str) -> pl.Expr:
    """lower + remove acentos, para cruzar bairro entre Airbnb (Mesh) e VivaReal
    sem o "Meia Praia" vs "meia praia" vs "Alto Sao Bento" vs "Alto São Bento"."""
    return (
        pl.col(col)
        .cast(pl.Utf8)
        .map_elements(
            lambda s: "".join(
                c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
            ).lower().strip()
            if s is not None
            else None,
            return_dtype=pl.Utf8,
        )
    )


def dedup_latest(df: pl.DataFrame, id_col: str, date_col: str) -> pl.DataFrame:
    """Mantem so a linha mais recente por id_col, ordenando por date_col.

    Mesh_Ids_Data_Itapema.csv e Hosts_ids_Itapema.csv sao series temporais
    incrementais (99 datas de aquisicao no caso do Mesh), nao 1 linha por
    entidade - um join direto sem isso causa fan-out (visto na exploracao:
    contagem de listings por bairro multiplicada por ~6x via join com Hosts).
    """
    return (
        df.sort(date_col, descending=True)
        .group_by(id_col)
        .first()
    )


def mesh_latest_normalized(mesh: pl.DataFrame) -> pl.DataFrame:
    deduped = dedup_latest(mesh, "airbnb_listing_id", "aquisition_date")
    return deduped.with_columns(normalize_suburb("suburb").alias("suburb_norm"))


def hosts_latest(hosts: pl.DataFrame) -> pl.DataFrame:
    return dedup_latest(hosts, "owner_id", "host_snapshot_date")


def vivareal_normalized(vivareal: pl.DataFrame) -> pl.DataFrame:
    return vivareal.with_columns(normalize_suburb("suburb").alias("suburb_norm"))


def price_wave(price: pl.DataFrame, reference_day: str = PRICE_WAVE_REFERENCE) -> pl.DataFrame:
    """Filtra Price_AV pela onda de aquisicao do dia de referencia.

    O timestamp de aquisicao e quase-unico por listing dentro do dia (cada
    listing foi raspado em um segundo diferente) - por isso o filtro e por
    DIA truncado, nunca por igualdade exata de timestamp (isso filtraria 1
    listing so). Ver spec.md SS5.1.
    """
    return price.filter(pl.col("aquisition_date").dt.date() == pl.lit(reference_day).str.to_date())
