"""Offline M2/M3 unit checks — no network."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "meta_label"))

from purged_cv import purged_kfold
from triple_barrier import first_touch_r, label_trades
from uniqueness import average_uniqueness


def test_first_touch_pt():
    path = np.array([0.0, 0.4, 1.1, 1.2])
    lab, ts, ret = first_touch_r(path, dt_sec=10.0, pt=1.0, sl=1.0, vertical_sec=100.0)
    assert lab == 1 and ret >= 1.0


def test_first_touch_sl_before_pt():
    path = np.array([0.0, -1.1, 2.0])
    lab, _, _ = first_touch_r(path, 10.0, 1.0, 1.0, 100.0)
    assert lab == -1


def test_label_trades_endpoint_pt():
    df = pd.DataFrame({
        "buy_price": [100.0], "sell_price": [103.0], "hold_sec": [600.0],
        "atr_pct": [0.02], "y_R": [1.6],
    })
    out = label_trades(df, seed=0)
    assert out.y_meta.iloc[0] in (0, 1)
    assert out.tbm_label.iloc[0] in (-1, 0, 1)


def test_purged_no_overlap():
    n = 20
    t0 = pd.date_range("2026-08-14 09:00", periods=n, freq="10min")
    t1 = t0 + pd.Timedelta("5min")
    splits = list(purged_kfold(pd.Series(t0), pd.Series(t1), n_splits=4,
                               embargo=pd.Timedelta("1min")))
    assert len(splits) >= 3
    for tr, te in splits:
        assert len(set(tr) & set(te)) == 0


def test_uniqueness_positive():
    t0 = pd.Series(pd.date_range("2026-08-14 09:00", periods=8, freq="2min"))
    t1 = t0 + pd.Timedelta("10min")
    u = average_uniqueness(t0, t1)
    assert len(u) == 8 and (u > 0).all() and (u <= 1).all()
