"""Carga bronze: le os 5 CSVs originais com Polars, schema explicito nas colunas
que o pipeline usa (ids, datas, preco, bairro). Colunas de texto livre (descricao,
amenities como string JSON) ficam Utf8 sem parsing - fora de escopo (spec.md SS7).
"""

import polars as pl

from itapema_bi.paths import DETAILS_CSV, HOSTS_CSV, MESH_CSV, PRICE_CSV, VIVAREAL_CSV

NULL_VALUES = ["<NA>", "NA", "nan", "NaN", ""]


def read_details() -> pl.DataFrame:
    df = pl.read_csv(DETAILS_CSV, null_values=NULL_VALUES, try_parse_dates=True, infer_schema_length=5000)
    return df.with_columns(
        pl.col("airbnb_listing_id").cast(pl.Int64),
        pl.col("owner_id").cast(pl.Int64),
        pl.col("number_of_bedrooms").cast(pl.Int64),
        pl.col("number_of_reviews").cast(pl.Int64),
        pl.col("star_rating").cast(pl.Float64),
        pl.col("listing_type").cast(pl.Utf8).str.to_lowercase(),
    )


def read_hosts() -> pl.DataFrame:
    df = pl.read_csv(HOSTS_CSV, null_values=NULL_VALUES, try_parse_dates=True, infer_schema_length=5000)
    return df.with_columns(
        pl.col("owner_id").cast(pl.Int64),
        pl.col("is_superhost").cast(pl.Utf8).str.to_lowercase() == "true",
    )


def read_mesh() -> pl.DataFrame:
    df = pl.read_csv(MESH_CSV, null_values=NULL_VALUES, try_parse_dates=True, infer_schema_length=5000)
    return df.with_columns(
        pl.col("airbnb_listing_id").cast(pl.Int64),
        pl.col("suburb").cast(pl.Utf8),
    )


def read_price() -> pl.DataFrame:
    df = pl.read_csv(PRICE_CSV, null_values=NULL_VALUES, try_parse_dates=True, infer_schema_length=5000)
    return df.with_columns(
        pl.col("airbnb_listing_id").cast(pl.Int64),
        pl.col("price").cast(pl.Float64),
    )


def read_vivareal() -> pl.DataFrame:
    df = pl.read_csv(VIVAREAL_CSV, null_values=NULL_VALUES, try_parse_dates=True, infer_schema_length=5000)
    return df.with_columns(
        pl.col("listing_id").cast(pl.Int64),
        pl.col("sale_price").cast(pl.Float64),
        pl.col("usable_area").cast(pl.Float64),
        pl.col("bedrooms").cast(pl.Int64, strict=False),
        pl.col("business_types").cast(pl.Utf8),
        pl.col("suburb").cast(pl.Utf8),
    )
