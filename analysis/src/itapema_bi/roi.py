"""Simulacao do predio de 50 apartamentos e projecao de ROI 2025/2026/2027.

Todas as premissas numericas deste modulo sao explicitas e documentadas em
spec.md SS5.3/SS5.4 - nao sao inferidas do dataset (o dataset nao tem ocupacao
real nem orcamento de obra). O relatorio final mostra ADR observado ao lado da
receita estimada para nao confundir dado com modelo.
"""

from dataclasses import dataclass

# Ocupacao em alta temporada por banda de demanda (spec.md SS5.3)
OCCUPANCY_HIGH_DEMAND = 0.70
OCCUPANCY_MID_DEMAND = 0.55
OCCUPANCY_LOW_DEMAND = 0.40

# Predio novo: sem reviews/historico no lancamento -> ramp-up de ocupacao.
# Multiplicador aplicado sobre a ocupacao estabilizada da banda de demanda do bairro.
YEAR_OCCUPANCY_RAMP = {2025: 0.55, 2026: 0.90, 2027: 1.00}

# Crescimento nominal de ADR ano a ano (premissa de mercado, nao medida).
YEAR_ADR_GROWTH = {2025: 1.00, 2026: 1.05, 2027: 1.10}

MANAGEMENT_FEE_PCT = 0.20  # taxa de gestao (Seazone) sobre receita
MAINTENANCE_PCT = 0.05  # manutencao sobre receita

# Areas-alvo de projeto para o predio novo (premissa de produto, menor que a
# media do mercado de revenda para otimizar economics de short-stay).
UNIT_AREA_M2 = {2: 70.0, 3: 95.0}


def occupancy_band(n_listings_priced: int, avg_reviews: float, reviews_p33: float, reviews_p66: float) -> float:
    if n_listings_priced >= 50 and avg_reviews >= reviews_p66:
        return OCCUPANCY_HIGH_DEMAND
    if n_listings_priced >= 10 and avg_reviews >= reviews_p33:
        return OCCUPANCY_MID_DEMAND
    return OCCUPANCY_LOW_DEMAND


@dataclass
class UnitType:
    bedrooms: int
    count: int
    adr_brl: float
    area_m2: float
    cost_per_m2_brl: float
    condo_fee_monthly_brl: float


def annual_revenue_brl(unit: UnitType, year: int, base_occupancy: float) -> float:
    adr = unit.adr_brl * YEAR_ADR_GROWTH[year]
    occupancy = base_occupancy * YEAR_OCCUPANCY_RAMP[year]
    return adr * occupancy * 365 * unit.count


def annual_opex_brl(unit: UnitType, revenue: float) -> float:
    condo = unit.condo_fee_monthly_brl * 12 * unit.count
    management = revenue * MANAGEMENT_FEE_PCT
    maintenance = revenue * MAINTENANCE_PCT
    return condo + management + maintenance


def implementation_cost_brl(unit: UnitType) -> float:
    from itapema_bi.cost import IMPLEMENTATION_COST_FACTOR

    return unit.cost_per_m2_brl * unit.area_m2 * IMPLEMENTATION_COST_FACTOR * unit.count


def project_roi(units: list[UnitType], base_occupancy: float, years=(2025, 2026, 2027)) -> list[dict]:
    investment_total = sum(implementation_cost_brl(u) for u in units)
    rows = []
    for year in years:
        unit_revenues = [annual_revenue_brl(u, year, base_occupancy) for u in units]
        revenue = sum(unit_revenues)
        opex = sum(annual_opex_brl(u, r) for u, r in zip(units, unit_revenues))
        noi = revenue - opex
        rows.append(
            {
                "year": year,
                "revenue_brl": round(revenue, 0),
                "opex_brl": round(opex, 0),
                "noi_brl": round(noi, 0),
                "investment_brl": round(investment_total, 0),
                "roi_pct": round(100 * noi / investment_total, 2),
            }
        )
    return rows
