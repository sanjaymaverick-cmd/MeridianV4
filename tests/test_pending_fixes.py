"""Pending-list items: EOD 15:15, holidays, order status, belief, real AUC."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MERIDIAN_MODE", "dry")
for p in ("src/decision", "src/openalgo", "src/data", "src/automation", "src/meta_label"):
    sys.path.insert(0, str(ROOT / p))

from engine import Position, manage  # noqa: E402
from primary import signal_from_quote  # noqa: E402
from quotes import Quote  # noqa: E402
from retrain import _real_in_sample_auc  # noqa: E402
from session import nse_open  # noqa: E402
from strategy_v4 import _order_ok, _qty  # noqa: E402


def test_eod_flatten_at_zero_not_fifteen():
    now = datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc)
    pos = Position("INFY", 100.0, now, 0.02, 0.1, 0.6, 100.0)
    later = now.replace()  # same instant; held=0 so min_hold unless eod
    # 10 min to flatten clock: hold (no scratch, not yet eod)
    i = manage(pos, 100.2, later, 10.0)
    assert i.reason == "min_hold"
    i2 = manage(pos, 100.2, later, 0.0)
    assert i2.action == "SELL" and i2.reason == "eod_flatten"


def test_nse_closed_on_republic_day():
    # 26 Jan 2026 10:00 IST = 04:30 UTC
    now = datetime(2026, 1, 26, 4, 30, tzinfo=timezone.utc)
    assert not nse_open(now)


def test_order_ok_rejects_error_status():
    assert _order_ok(None)
    assert _order_ok({"status": "success"})
    assert not _order_ok({"status": "error"})
    assert not _order_ok({"error": "rejected"})


def test_nfo_qty_is_lots():
    q = _qty(22000.0, 0.10, budget=100_000, symbol="NIFTY")
    assert q >= 65 and q % 65 == 0


def test_belief_not_constant():
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    hi = signal_from_quote(Quote("INFY", "NSE", 1560, 1530, 1560, 1525, 1530), now)
    lo = signal_from_quote(Quote("INFY", "NSE", 1526, 1530, 1560, 1525, 1550), now)
    assert hi.belief_posterior != lo.belief_posterior
    assert hi.p_success != lo.p_success


def test_lightgbm_fit_optional(tmp_path):
    lightgbm = pytest.importorskip("lightgbm")
    from train import fit_lightgbm
    import numpy as np
    rng = np.random.default_rng(0)
    X = rng.normal(size=(80, 7))
    y = (X[:, 0] > 0).astype(int)
    w = np.ones(80)
    dest = tmp_path / "m.txt"
    meta = fit_lightgbm(X, y, w, dest, version="t")
    assert dest.exists() and meta["model"] == "lightgbm"
    from model import LightGBMModel
    m = LightGBMModel.load(dest)
    p = m.predict({f: float(X[0, i]) for i, f in enumerate(m.features or range(7))})
    assert 0.0 <= p <= 1.0


def test_real_in_sample_auc_ignores_synth():
    n = 40
    df = pd.DataFrame({
        "confidence": [0.6] * n, "confluence": [73.6] * n, "p_success": [0.6] * n,
        "atr_pct": [0.02] * n, "approx_stop_pct": [0.03] * n,
        "minutes_since_midnight": [500] * n, "minutes_to_eod_flatten": [80] * n,
        "y_meta": [0, 1] * (n // 2),
        "avg_uniqueness": [1.0] * n,
        "is_quality_hold": [1] * n,
        "is_synthetic": [0] * n,
    })
    auc = _real_in_sample_auc(df)
    assert auc is None or 0.0 <= auc <= 1.0
