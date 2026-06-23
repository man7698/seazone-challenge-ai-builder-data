"""Custo de implantacao via proxy de mercado (VivaReal), por bairro x dormitorios.

Ver spec.md SS5.4: nao ha orcamento de obra no dataset, entao usamos preco/m2 de
venda como proxy de valor de mercado do imovel pronto, e aplicamos
IMPLEMENTATION_COST_FACTOR sobre esse valor como proxy conservador de custo de
implantacao (terreno + obra). E premissa, nao orcamento real - tratado como
risco explicito no relatorio.
"""

import duckdb
import polars as pl

IMPLEMENTATION_COST_FACTOR = 0.65


def cost_by_suburb_bedrooms(vivareal_norm: pl.DataFrame) -> pl.DataFrame:
    return duckdb.sql(
        """
        select
            suburb_norm as suburb,
            bedrooms,
            count(*) as n_listings,
            round(avg(sale_price), 0) as avg_sale_price_brl,
            round(avg(usable_area), 0) as avg_usable_area_m2,
            round(avg(sale_price / usable_area), 0) as avg_price_per_m2_brl
        from vivareal_norm
        where business_types ilike 'venda' and usable_area > 0 and sale_price > 0
        group by 1, 2
        having count(*) >= 5
        order by 1, 2
        """
    ).pl()


def implementation_cost_per_unit(cost_row: dict, target_area_m2: float) -> float:
    return cost_row["avg_price_per_m2_brl"] * target_area_m2 * IMPLEMENTATION_COST_FACTOR


def condo_fee_by_suburb(vivareal_norm: pl.DataFrame) -> pl.DataFrame:
    return duckdb.sql(
        """
        select suburb_norm as suburb, round(avg(monthly_condo_fee), 0) as avg_condo_fee_brl
        from vivareal_norm
        where business_types ilike 'venda' and monthly_condo_fee > 0
        group by 1
        order by 1
        """
    ).pl()
