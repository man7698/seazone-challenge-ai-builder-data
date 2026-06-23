"""Orquestrador da Parte 1 (BI Itapema). Roda os passos 1-6 de
specs/01-bi-itapema/plan.md em sequencia, medindo tempo e pico de memoria reais
por etapa, e escreve as tabelas gold + um resumo em analysis/output/.
"""

import json

import polars as pl

from itapema_bi import clean, cost, load, metrics, roi
from itapema_bi.paths import GOLD_DIR, OUTPUT_DIR
from itapema_bi.timing import measure, summary_markdown

TARGET_BEDROOM_MIX_SCENARIOS = {
    "100pct_2q": {2: 50},
    "100pct_3q": {3: 50},
    "mix_50_50": {2: 25, 3: 25},
}
TOTAL_UNITS = 50


def pick_target_suburb(rev_suburb: pl.DataFrame) -> str:
    reliable = rev_suburb.filter(pl.col("reliable"))
    return reliable.sort("adr_brl", descending=True).row(0, named=True)["suburb"]


def estimate_adr(
    suburb_bedrooms: pl.DataFrame,
    bedrooms_global: pl.DataFrame,
    target_suburb: str,
    bedrooms: int,
    suburb_adr: float,
    global_adr: float,
) -> float:
    """ADR para (bairro-alvo, dormitorios). Usa o corte cruzado se confiavel
    (n>=10), senao escala o ADR global por dormitorios pelo premio de preco do
    bairro-alvo sobre a media geral - documentado em spec.md SS5 (sem isso, um
    corte cruzado bairro x dormitorios fica sem amostra suficiente)."""
    row = suburb_bedrooms.filter(
        (pl.col("suburb") == target_suburb) & (pl.col("number_of_bedrooms") == bedrooms) & pl.col("reliable")
    )
    if row.height > 0:
        return row.row(0, named=True)["adr_brl"]

    global_row = bedrooms_global.filter(pl.col("number_of_bedrooms") == bedrooms)
    global_bed_adr = global_row.row(0, named=True)["adr_brl"] if global_row.height > 0 else global_adr
    suburb_premium = suburb_adr / global_adr
    return round(global_bed_adr * suburb_premium, 0)


def build_units(bedrooms_mix: dict, adr_by_bed: dict, cost_by_bed: dict, condo_fee: float) -> list[roi.UnitType]:
    units = []
    for bedrooms, count in bedrooms_mix.items():
        units.append(
            roi.UnitType(
                bedrooms=bedrooms,
                count=count,
                adr_brl=adr_by_bed[bedrooms],
                area_m2=roi.UNIT_AREA_M2[bedrooms],
                cost_per_m2_brl=cost_by_bed[bedrooms],
                condo_fee_monthly_brl=condo_fee,
            )
        )
    return units


def main():
    with measure("passo1_carga_bronze"):
        details = load.read_details()
        hosts = load.read_hosts()
        mesh = load.read_mesh()
        price = load.read_price()
        vivareal = load.read_vivareal()

    with measure("passo1_limpeza_silver"):
        mesh_latest = clean.mesh_latest_normalized(mesh)
        hosts_latest = clean.hosts_latest(hosts)
        vivareal_norm = clean.vivareal_normalized(vivareal)
        price_wave = clean.price_wave(price)

    with measure("passo2_metricas_por_corte"):
        rev_suburb = metrics.revenue_by_suburb(price_wave, mesh_latest)
        rev_bedrooms = metrics.revenue_by_bedrooms_type(price_wave, details)
        rev_suburb_bedrooms = metrics.revenue_by_suburb_bedrooms(price_wave, details, mesh_latest)
        demand_suburb = metrics.demand_by_suburb(details, mesh_latest, hosts_latest)
        correlations = metrics.adr_correlations_by_suburb(price_wave, details, mesh_latest)

    with measure("passo3_cruzamento_custo_vivareal"):
        cost_suburb_bedrooms = cost.cost_by_suburb_bedrooms(vivareal_norm)
        condo_fee_suburb = cost.condo_fee_by_suburb(vivareal_norm)

    with measure("passo4_decisao_localizacao_perfil"):
        best_revenue_suburb = pick_target_suburb(rev_suburb)
        global_adr = price_wave.select(pl.col("price").mean()).item()
        reviews_p33 = demand_suburb.select(pl.col("avg_reviews").quantile(0.33)).item()
        reviews_p66 = demand_suburb.select(pl.col("avg_reviews").quantile(0.66)).item()
        bedrooms_global_adr = rev_bedrooms.group_by("number_of_bedrooms").agg(pl.col("adr_brl").mean())

        # "Melhor localizacao por receita" (H2) pode nao ser o melhor lugar pra
        # CONSTRUIR (H4): m2 mais caro no bairro mais badalado pode comer o
        # retorno. Avaliamos ROI por bairro candidato (amostra confiavel) antes
        # de fixar onde o predio vai - nao assumimos que sao o mesmo lugar.
        candidate_suburbs = rev_suburb.filter(pl.col("reliable")).get_column("suburb").to_list()
        suburb_roi_candidates = {}
        for suburb in candidate_suburbs:
            suburb_adr = rev_suburb.filter(pl.col("suburb") == suburb).row(0, named=True)["adr_brl"]
            adr_by_bed = {
                b: estimate_adr(rev_suburb_bedrooms, bedrooms_global_adr, suburb, b, suburb_adr, global_adr)
                for b in (2, 3)
            }
            cost_by_bed = {}
            for b in (2, 3):
                row = cost_suburb_bedrooms.filter((pl.col("suburb") == suburb) & (pl.col("bedrooms") == b))
                cost_by_bed[b] = (
                    row.row(0, named=True)["avg_price_per_m2_brl"]
                    if row.height > 0
                    else cost_suburb_bedrooms.select(pl.col("avg_price_per_m2_brl").mean()).item()
                )
            condo_row = condo_fee_suburb.filter(pl.col("suburb") == suburb)
            condo_fee = (
                condo_row.row(0, named=True)["avg_condo_fee_brl"]
                if condo_row.height > 0
                else condo_fee_suburb.select(pl.col("avg_condo_fee_brl").mean()).item()
            )
            demand_row = demand_suburb.filter(pl.col("suburb") == suburb).row(0, named=True)
            n_priced = rev_suburb.filter(pl.col("suburb") == suburb).row(0, named=True)["n_listings_priced"]
            base_occupancy = roi.occupancy_band(n_priced, demand_row["avg_reviews"], reviews_p33, reviews_p66)

            scenario_results = {}
            for name, mix in TARGET_BEDROOM_MIX_SCENARIOS.items():
                units = build_units(mix, adr_by_bed, cost_by_bed, condo_fee)
                scenario_results[name] = roi.project_roi(units, base_occupancy)
            best_scenario = max(scenario_results, key=lambda k: scenario_results[k][-1]["roi_pct"])

            suburb_roi_candidates[suburb] = {
                "adr_by_bed": adr_by_bed,
                "cost_by_bed": cost_by_bed,
                "condo_fee": condo_fee,
                "base_occupancy": base_occupancy,
                "best_scenario": best_scenario,
                "best_scenario_roi_2027_pct": scenario_results[best_scenario][-1]["roi_pct"],
                "scenario_results": scenario_results,
            }

        build_suburb = max(suburb_roi_candidates, key=lambda s: suburb_roi_candidates[s]["best_scenario_roi_2027_pct"])
        chosen = suburb_roi_candidates[build_suburb]

    with measure("passo5_projecao_roi"):
        final_mix = TARGET_BEDROOM_MIX_SCENARIOS[chosen["best_scenario"]]
        final_units = build_units(final_mix, chosen["adr_by_bed"], chosen["cost_by_bed"], chosen["condo_fee"])
        roi_projection = roi.project_roi(final_units, chosen["base_occupancy"])

    with measure("passo6_consolidacao_outputs"):
        rev_suburb.write_parquet(GOLD_DIR / "revenue_by_suburb.parquet")
        rev_bedrooms.write_parquet(GOLD_DIR / "revenue_by_bedrooms_type.parquet")
        cost_suburb_bedrooms.write_parquet(GOLD_DIR / "cost_by_suburb_bedrooms.parquet")

        answers = {
            "best_revenue_suburb": best_revenue_suburb,
            "build_suburb": build_suburb,
            "build_suburb_equals_best_revenue_suburb": build_suburb == best_revenue_suburb,
            "base_occupancy_assumption": chosen["base_occupancy"],
            "bedroom_mix_scenarios_2027_roi_pct": {
                k: v[-1]["roi_pct"] for k, v in chosen["scenario_results"].items()
            },
            "chosen_mix": chosen["best_scenario"],
            "adr_by_bedrooms_brl": chosen["adr_by_bed"],
            "roi_projection": roi_projection,
            "roi_by_candidate_suburb_2027_pct": {
                s: c["best_scenario_roi_2027_pct"] for s, c in suburb_roi_candidates.items()
            },
        }
        with open(OUTPUT_DIR / "answers.json", "w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)

        with open(OUTPUT_DIR / "timing_report.md", "w", encoding="utf-8") as f:
            f.write("# Eficiencia computacional - Parte 1\n\n")
            f.write(summary_markdown())

    print("\n=== RESUMO ===")
    print(f"Melhor localizacao por receita (H2): {best_revenue_suburb}")
    print(f"Melhor localizacao pra CONSTRUIR o predio (H4, por ROI): {build_suburb}")
    if build_suburb != best_revenue_suburb:
        print("  -> divergem: o bairro de maior receita tem custo/m2 alto demais pra compensar no ROI.")
    print(f"Ocupacao-base assumida: {chosen['base_occupancy']:.0%}")
    print(f"Mix de unidades escolhido: {chosen['best_scenario']} -> {final_mix}")
    print(f"ROI projetado: {roi_projection}")
    print(f"ROI 2027 por bairro candidato: {answers['roi_by_candidate_suburb_2027_pct']}")
    print(f"\nSaida completa em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
