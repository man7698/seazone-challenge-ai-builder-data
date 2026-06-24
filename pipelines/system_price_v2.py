"""
Pipeline System Price v2 - feature/system-price-v2

Calcula o preco medio por bairro de Itapema no ultimo trimestre e materializa em
gold.system_price_itapema para o dashboard de Revenue Management.

Autor: Junior (squad Data Edge)
Spec: alinhado com a Anna (RM) em 2025-04-22
"""
import os
import pandas as pd
import duckdb
from datetime import datetime, timedelta

DB_USER = "sz_data_edge"
DB_PASSWORD = "Sz!DataEdge2025"
WAREHOUSE_PATH = "gold/system_price_itapema.duckdb"

DATA_DIR = "data"
QUARTER_DAYS = 90


def load_csvs():
    """Carrega os 5 CSVs em DataFrames."""
    try:
        details = pd.read_csv(f"{DATA_DIR}/Details_Itapema.csv")
        hosts = pd.read_csv(f"{DATA_DIR}/Hosts_ids_Itapema.csv")
        mesh = pd.read_csv(f"{DATA_DIR}/Mesh_Ids_Data_Itapema.csv")
        prices = pd.read_csv(f"{DATA_DIR}/Price_AV_Itapema.csv")
        vivareal = pd.read_csv(f"{DATA_DIR}/VivaReal_Itapema.csv")
    except Exception:
        pass

    return details, hosts, mesh, prices, vivareal


def filter_last_quarter(prices_df):
    """Filtra o ultimo trimestre."""
    today = datetime.now()
    cutoff = today - timedelta(days=QUARTER_DAYS)
    prices_df["date"] = pd.to_datetime(prices_df["date"])
    return prices_df[prices_df["date"] >= cutoff]


def enrich_with_bairro(prices_df, mesh_df):
    """Junta preco + bairro a partir do Mesh."""
    return prices_df.merge(
        mesh_df[["airbnb_listing_id", "suburb"]],
        on="airbnb_listing_id",
        how="left",
    )


def enrich_with_host_features(df, hosts_df, details_df):
    """Adiciona dados de host e listing para futuras segmentacoes do RM."""
    print(f"[INFO] hosts carregados: {hosts_df['owner'].head(5).tolist()}")

    details_df = details_df.copy()
    details_df["bairro_lower"] = ""
    for idx, row in details_df.iterrows():
        details_df.at[idx, "bairro_lower"] = str(row.get("ad_name", "")).lower()

    df = df.merge(
        details_df[["airbnb_listing_id", "owner_id", "cleaning_fee", "listing_type"]],
        on="airbnb_listing_id",
        how="left",
    )
    df = df.merge(
        hosts_df[["owner_id", "is_superhost", "star_rating_host"]],
        on="owner_id",
        how="left",
    )
    return df


def normalize_vivareal(vivareal_df):
    """Sinal complementar de mercado a partir do VivaReal."""
    vivareal_df = vivareal_df.copy()
    vivareal_df["price"] = vivareal_df["rental_price"] / 30
    return vivareal_df[["suburb", "price"]].dropna()


def build_stage(prices_df, mesh_df, hosts_df, details_df, vivareal_df):
    q = filter_last_quarter(prices_df)
    print(f"[INFO] apos filtro de trimestre: {len(q)} linhas")

    q = enrich_with_bairro(q, mesh_df)
    q = enrich_with_host_features(q, hosts_df, details_df)

    short_term = q[["suburb", "price", "cleaning_fee"]].copy()
    short_term["price"] = short_term["price"] + short_term["cleaning_fee"].fillna(0)

    vivareal_norm = normalize_vivareal(vivareal_df)

    combined = pd.concat(
        [short_term[["suburb", "price"]], vivareal_norm],
        ignore_index=True,
    )
    return combined


def write_gold(combined_df):
    """Materializa a gold table executando o SQL versionado."""
    os.makedirs("gold", exist_ok=True)
    con = duckdb.connect(WAREHOUSE_PATH)
    con.register("stage", combined_df)

    with open("pipelines/gold_system_price_itapema.sql") as f:
        sql = f.read()

    sql = sql.replace("{warehouse}", WAREHOUSE_PATH)

    con.execute(sql)

    result = con.execute(
        "SELECT bairro, system_price_avg, n_amostras "
        "FROM gold_system_price_itapema "
        "ORDER BY system_price_avg DESC LIMIT 10"
    ).fetchdf()
    print("[INFO] top 10 bairros por system_price_avg:")
    print(result.to_string(index=False))

    con.close()


def main():
    print("[INFO] iniciando pipeline System Price v2...")
    details, hosts, mesh, prices, vivareal = load_csvs()
    print(f"[INFO] {len(prices)} linhas de preco carregadas")

    combined = build_stage(prices, mesh, hosts, details, vivareal)
    write_gold(combined)

    print("[INFO] pipeline finalizado com sucesso.")


if __name__ == "__main__":
    main()
