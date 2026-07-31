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
COMPANIES_DIR = DATA_DIR / "companies"
REPORTS_DIR = DATA_DIR / "reports"

IBOVESPA_JSON = UNIVERSE_DIR / "ibovespa.json"
CADASTRO_CSV = CVM_CACHE_DIR / "cad_cia_aberta.csv"

BRAPI_API_KEY = os.getenv("BRAPI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

HTTP_TIMEOUT = 60.0
DOWNLOAD_SLEEP_S = 0.35
USER_AGENT = "decifra-invest-agent/0.1 (+https://github.com/rudahfonseca-beep/decifra-invest-agent; research)"

# Default years for CVM document sync
DEFAULT_FINANCIAL_YEARS = list(range(2020, 2027))
DEFAULT_NOTICE_YEARS = list(range(2023, 2027))

CVM_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
CVM_CADASTRO_URL = f"{CVM_BASE}/CAD/DADOS/cad_cia_aberta.csv"
CVM_DFP_ZIP = f"{CVM_BASE}/DOC/DFP/DADOS/dfp_cia_aberta_{{year}}.zip"
CVM_ITR_ZIP = f"{CVM_BASE}/DOC/ITR/DADOS/itr_cia_aberta_{{year}}.zip"
CVM_IPE_ZIP = f"{CVM_BASE}/DOC/IPE/DADOS/ipe_cia_aberta_{{year}}.zip"
CVM_FATO_ZIP = f"{CVM_BASE}/DOC/FATO_RELEVANTE/DADOS/fato_relevante_cia_aberta_{{year}}.zip"
CVM_FATO_CSV = f"{CVM_BASE}/DOC/FATO_RELEVANTE/DADOS/fato_relevante_cia_aberta_{{year}}.csv"

B3_IBOV_PORTFOLIO_URL = (
    "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"
)


def ensure_dirs() -> None:
    for path in (DATA_DIR, UNIVERSE_DIR, CACHE_DIR, CVM_CACHE_DIR, COMPANIES_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
