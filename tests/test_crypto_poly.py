"""Crypto 24h session + Polymarket parse. Offline except optional live skip."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys

os.environ.setdefault("MERIDIAN_MODE", "dry")
ROOT = Path(__file__).resolve().parents[1]
for p in ("src/openalgo", "src/data", "src/decision"):
    sys.path.insert(0, str(ROOT / p))

from polymarket import _parse_list, register_exchange  # noqa: E402
from session import is_24h, minutes_to_eod  # noqa: E402
from strategy_v4 import EXCHANGE, _qty  # noqa: E402


def test_crypto_and_poly_are_24h():
    now = datetime(2026, 8, 16, 18, 0, tzinfo=timezone.utc)  # Sunday evening
    assert is_24h("DELTA") and is_24h("POLY") and is_24h("CRYPTO")
    assert minutes_to_eod(now, "DELTA") == 999.0
    assert minutes_to_eod(now, "POLY") == 999.0
    assert not is_24h("NSE")


def test_crypto_map_and_qty():
    assert EXCHANGE["BTCUSDT"] == "DELTA"
    assert EXCHANGE["ETHUSDT"] == "DELTA"
    q = _qty(60000.0, 0.10, budget=100_000, symbol="BTCUSDT")
    assert q >= 0.001


def test_parse_clob_token_json():
    assert _parse_list('["aa","bb"]') == ["aa", "bb"]
    assert _parse_list(["aa"]) == ["aa"]


def test_register_poly_symbols():
    ex = {}
    register_exchange(ex, [{"symbol": "PM_TEST", "token_id": "1"}])
    assert ex["PM_TEST"] == "POLY"


def test_poly_catalog_roundtrip(tmp_path):
    from polymarket import load_catalog, save_catalog
    p = tmp_path / "catalog.json"
    save_catalog([{"symbol": "PM_X", "token_id": "9", "price": 0.4}], p)
    got = load_catalog(p)
    assert got[0]["symbol"] == "PM_X"
    assert json.loads(p.read_text())[0]["token_id"] == "9"
