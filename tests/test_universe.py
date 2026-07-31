from __future__ import annotations

import base64
import json

from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.universe.ibovespa import _b3_payload


def test_normalize_ticker():
    assert normalize_ticker("petr4.sa") == "PETR4"
    assert normalize_ticker(" VALE3 ") == "VALE3"


def test_normalize_cnpj():
    assert normalize_cnpj("33.000.167/0001-01") == "33000167000101"
    assert len(normalize_cnpj("123")) == 14


def test_b3_payload_is_base64_json():
    token = _b3_payload(1, 120)
    data = json.loads(base64.b64decode(token).decode("utf-8"))
    assert data["index"] == "IBOV"
    assert data["pageSize"] == 120
