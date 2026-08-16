"""Offline normalizer checks. No network."""
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "data"))

from backfill_5y import _norm  # noqa: E402


def test_norm_drops_bad_and_sorts():
    raw = pd.DataFrame({
        "date": [datetime(2024, 1, 3), datetime(2024, 1, 2), datetime(2024, 1, 2)],
        "open": [10, 9, 9],
        "high": [11, 10, 10],
        "low": [9, 8, 8],
        "close": [10.5, 9.5, 9.5],
        "volume": [100, 80, 80],
    })
    out = _norm(raw, "SBIN", "NSE", "jugaad-data")
    assert list(out["date"].dt.date.astype(str)) == ["2024-01-02", "2024-01-03"]
    assert out["symbol"].iloc[0] == "SBIN"
    assert out["exchange"].iloc[0] == "NSE"
    assert out["interval"].iloc[0] == "1d"


def test_norm_drops_zero_close():
    raw = pd.DataFrame({
        "date": [datetime(2024, 1, 2)],
        "open": [1], "high": [1], "low": [1], "close": [0], "volume": [0],
    })
    assert _norm(raw, "X", "NSE", "t").empty
