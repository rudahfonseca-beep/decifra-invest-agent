from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DECIFRA_DATA_DIR", PROJECT_ROOT / "data")).resolve()

UNIVERSE_DIR = DATA_DIR / "universe"
CACHE_DIR = DATA_DIR / "cache"
CVM_CACHE_DIR = CACHE_DIR / "cvm"
ANBIMA_CACHE_DIR = CACHE_DIR / "anbima"
MARKET_CACHE_DIR = CACHE_DIR / "market"
COMPANIES_DIR = DATA_DIR / "companies"
REPORTS_DIR = DATA_DIR / "reports"
VALUATIONS_DIR = DATA_DIR / "valuations"
FUNDS_DIR = DATA_DIR / "funds"
ENTITIES_JSON = UNIVERSE_DIR / "entities.json"

IBOVESPA_JSON = UNIVERSE_DIR / "ibovespa.json"
CADASTRO_CSV = CVM_CACHE_DIR / "cad_cia_aberta.csv"
B3_SHARES_JSON = UNIVERSE_DIR / "b3_shares.json"
B3_BALCAO_JSON = UNIVERSE_DIR / "b3_balcao_bonds.json"

BRAPI_API_KEY = os.getenv("BRAPI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

HTTP_TIMEOUT = 60.0
DOWNLOAD_SLEEP_S = 0.35
USER_AGENT = "decifra-invest-agent/0.1 (+https://github.com/rudahfonseca-beep/decifra-invest-agent; research)"

# Default years for CVM document sync
DEFAULT_FINANCIAL_YEARS = list(range(2020, 2027))
# Include 2020+ so fato relevante / IPE cache can match financial year coverage (IMP-003).
DEFAULT_NOTICE_YEARS = list(range(2020, 2027))

CVM_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
CVM_CADASTRO_URL = f"{CVM_BASE}/CAD/DADOS/cad_cia_aberta.csv"
CVM_DFP_ZIP = f"{CVM_BASE}/DOC/DFP/DADOS/dfp_cia_aberta_{{year}}.zip"
CVM_ITR_ZIP = f"{CVM_BASE}/DOC/ITR/DADOS/itr_cia_aberta_{{year}}.zip"
CVM_IPE_ZIP = f"{CVM_BASE}/DOC/IPE/DADOS/ipe_cia_aberta_{{year}}.zip"
CVM_FRE_ZIP = f"{CVM_BASE}/DOC/FRE/DADOS/fre_cia_aberta_{{year}}.zip"
CVM_FATO_ZIP = f"{CVM_BASE}/DOC/FATO_RELEVANTE/DADOS/fato_relevante_cia_aberta_{{year}}.zip"
CVM_FATO_CSV = f"{CVM_BASE}/DOC/FATO_RELEVANTE/DADOS/fato_relevante_cia_aberta_{{year}}.csv"

# CVM Funds (FI)
CVM_FUNDS_BASE = "https://dados.cvm.gov.br/dados/FI"
CVM_INF_DIARIO_ZIP = f"{CVM_FUNDS_BASE}/DOC/INF_DIARIO/DADOS/inf_diario_fi_{{yyyymm}}.zip"
CVM_CDA_ZIP = f"{CVM_FUNDS_BASE}/DOC/CDA/DADOS/cda_fi_{{yyyymm}}.zip"

DEFAULT_FRE_YEARS = list(range(2022, 2027))

B3_IBOV_PORTFOLIO_URL = (
    "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"
)

# --- Valuation defaults ---------------------------------------------------
# These are static, research-grade proxies (not a live macro feed). Override
# per-run via CLI flags / Streamlit inputs, or globally via the env vars
# below. See docs/workflows/valuation.md for how each default is derived.
CORPORATE_TAX_RATE_DEFAULT = float(os.getenv("DECIFRA_TAX_RATE", "0.34"))
FINANCIAL_TAX_RATE_DEFAULT = float(os.getenv("DECIFRA_FINANCIAL_TAX_RATE", "0.45"))
RISK_FREE_RATE_DEFAULT = float(os.getenv("DECIFRA_RISK_FREE_RATE", "0.07"))
EQUITY_RISK_PREMIUM_DEFAULT = float(os.getenv("DECIFRA_EQUITY_RISK_PREMIUM", "0.045"))
COUNTRY_RISK_PREMIUM_DEFAULT = float(os.getenv("DECIFRA_COUNTRY_RISK_PREMIUM", "0.025"))
TERMINAL_GROWTH_DEFAULT = float(os.getenv("DECIFRA_TERMINAL_GROWTH", "0.035"))
DEFAULT_FORECAST_YEARS = int(os.getenv("DECIFRA_FORECAST_YEARS", "5"))
BETA_LOOKBACK_YEARS = int(os.getenv("DECIFRA_BETA_LOOKBACK_YEARS", "3"))
DEFAULT_BETA = float(os.getenv("DECIFRA_DEFAULT_BETA", "1.0"))
IBOVESPA_INDEX_TICKER = "^BVSP"
MARKET_DATA_CACHE_HOURS = float(os.getenv("DECIFRA_MARKET_DATA_CACHE_HOURS", "24"))


def ensure_dirs() -> None:
    for path in (
        DATA_DIR,
        UNIVERSE_DIR,
        CACHE_DIR,
        CVM_CACHE_DIR,
        ANBIMA_CACHE_DIR,
        MARKET_CACHE_DIR,
        COMPANIES_DIR,
        REPORTS_DIR,
        VALUATIONS_DIR,
        FUNDS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
