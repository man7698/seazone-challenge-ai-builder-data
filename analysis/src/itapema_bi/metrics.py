"""Camada gold: metricas de ADR/demanda por corte (bairro, dormitorios x tipo),
calculadas em SQL (DuckDB) sobre os DataFrames Polars ja limpos - join e window
function ficam mais legiveis em SQL do que encadeados em Polars puro.

Aplica o filtro de confiabilidade estatistica definido em spec.md SS2: cortes com
menos de RELIABILITY_MIN listings com preco observado sao marcados, nunca usados
como base de decisao principal.
"""

import duckdb
import polars as pl

RELIABILITY_MIN = 10


def revenue_by_suburb(price_wave: pl.DataFrame, mesh_latest: pl.DataFrame) -> pl.DataFrame:
    return duckdb.sql(
        """
        select
            m.suburb_norm as suburb,
            count(distinct p.airbnb_listing_id) as n_listings_priced,
            round(avg(p.price), 0) as adr_brl,
            round(median(p.price), 0) as median_adr_brl,
            (count(distinct p.airbnb_listing_id) >= $reliability_min) as reliable
        from price_wave p
        join mesh_latest m on m.airbnb_listing_id = p.airbnb_listing_id
        group by 1
        order by adr_brl desc
        """,
        params={"reliability_min": RELIABILITY_MIN},
    ).pl()


def revenue_by_bedrooms_type(price_wave: pl.DataFrame, details: pl.DataFrame) -> pl.DataFrame:
    return duckdb.sql(
        """
        select
            d.listing_type,
            d.number_of_bedrooms,
            count(distinct p.airbnb_listing_id) as n_listings_priced,
            round(avg(p.price), 0) as adr_brl,
            round(avg(d.number_of_reviews), 1) as avg_reviews,
            round(avg(d.star_rating), 2) as avg_star_rating,
            (count(distinct p.airbnb_listing_id) >= $reliability_min) as reliable
        from price_wave p
        join details d on d.airbnb_listing_id = p.airbnb_listing_id
        group by 1, 2
        order by adr_brl desc
        """,
        params={"reliability_min": RELIABILITY_MIN},
    ).pl()


def revenue_by_suburb_bedrooms(price_wave: pl.DataFrame, details: pl.DataFrame, mesh_latest: pl.DataFrame) -> pl.DataFrame:
    """Corte cruzado bairro x dormitorios - amostra menor, usado so para o
    bairro escolhido (Meia Praia) ao desenhar o mix de unidades do predio."""
    return duckdb.sql(
        """
        select
            m.suburb_norm as suburb,
            d.number_of_bedrooms,
            count(distinct p.airbnb_listing_id) as n_listings_priced,
            round(avg(p.price), 0) as adr_brl,
            (count(distinct p.airbnb_listing_id) >= $reliability_min) as reliable
        from price_wave p
        join details d on d.airbnb_listing_id = p.airbnb_listing_id
        join mesh_latest m on m.airbnb_listing_id = p.airbnb_listing_id
        group by 1, 2
        order by 1, 2
        """,
        params={"reliability_min": RELIABILITY_MIN},
    ).pl()


def demand_by_suburb(details: pl.DataFrame, mesh_latest: pl.DataFrame, hosts_latest: pl.DataFrame) -> pl.DataFrame:
    return duckdb.sql(
        """
        select
            m.suburb_norm as suburb,
            count(*) as n_listings_total,
            round(avg(d.number_of_reviews), 1) as avg_reviews,
            round(avg(coalesce(h.is_superhost, false)::int), 2) as pct_superhost,
            round(avg(d.star_rating), 2) as avg_star_rating
        from details d
        join mesh_latest m on m.airbnb_listing_id = d.airbnb_listing_id
        left join hosts_latest h on h.owner_id = d.owner_id
        group by 1
        order by n_listings_total desc
        """
    ).pl()


def adr_correlations_by_suburb(price_wave: pl.DataFrame, details: pl.DataFrame, mesh_latest: pl.DataFrame) -> pl.DataFrame:
    joined = duckdb.sql(
        """
        select m.suburb_norm as suburb, p.price, d.star_rating, d.number_of_reviews
        from price_wave p
        join details d on d.airbnb_listing_id = p.airbnb_listing_id
        join mesh_latest m on m.airbnb_listing_id = p.airbnb_listing_id
        """
    ).pl()

    rows = []
    for suburb, group in joined.group_by("suburb"):
        if group.height < RELIABILITY_MIN:
            continue
        corr_rating = group.select(pl.corr("price", "star_rating")).item()
        corr_reviews = group.select(pl.corr("price", "number_of_reviews")).item()
        rows.append(
            {
                "suburb": suburb[0] if isinstance(suburb, tuple) else suburb,
                "n": group.height,
                "corr_price_star_rating": corr_rating,
                "corr_price_number_of_reviews": corr_reviews,
            }
        )
    return pl.DataFrame(rows).sort("n", descending=True)
