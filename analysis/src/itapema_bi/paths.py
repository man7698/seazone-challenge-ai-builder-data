from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ANALYSIS_ROOT.parent

RAW_DIR = REPO_ROOT / "data"
SILVER_DIR = ANALYSIS_ROOT / "data" / "silver"
GOLD_DIR = ANALYSIS_ROOT / "data" / "gold"
OUTPUT_DIR = ANALYSIS_ROOT / "output"

DETAILS_CSV = RAW_DIR / "Details_Itapema.csv"
HOSTS_CSV = RAW_DIR / "Hosts_ids_Itapema.csv"
MESH_CSV = RAW_DIR / "Mesh_Ids_Data_Itapema.csv"
PRICE_CSV = RAW_DIR / "Price_AV_Itapema.csv"
VIVAREAL_CSV = RAW_DIR / "VivaReal_Itapema.csv"

PRICE_WAVE_REFERENCE = "2025-01-20"

for d in (SILVER_DIR, GOLD_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)
