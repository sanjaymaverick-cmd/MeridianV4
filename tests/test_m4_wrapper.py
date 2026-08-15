"""M4 dry wrapper + paper sink. No OpenAlgo import."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sys

os.environ["MERIDIAN_MODE"] = "dry"
ROOT = Path(__file__).resolve().parents[1]
os.environ["MERIDIAN_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT / "src" / "openalgo"))
sys.path.insert(0, str(ROOT / "src" / "decision"))

from paper_sink import append_close, close_to_row  # noqa: E402
from strategy_v4 import dry_demo  # noqa: E402


def test_dry_demo_enters_and_exits():
    actions = dry_demo()
    assert actions[0] in ("BUY", "FLAT")
    if actions[0] == "BUY":
        assert actions[1] == "min_hold"
        assert actions[2] in ("take_profit", "trail", "hold_quality")


def test_sink_flags_real_not_synth(tmp_path):
    dest = tmp_path / "closes.csv"
    append_close({
        "symbol": "INFY", "buy_price": 100, "sell_price": 102,
        "buy_time": "2026-08-15T04:00:00", "sell_time": "2026-08-15T04:10:00",
        "hold_sec": 600, "honest_pnl": 8.0, "qty": 4, "risk_rupees": 6.0,
        "atr_pct": 0.02, "confidence": 0.6, "confluence": 73.6,
        "p_success": 0.67, "minutes_to_eod_flatten": 80,
        "belief_posterior": 0.25, "meta_prob": 0.6,
    }, dest)
    text = dest.read_text(encoding="utf-8")
    assert "INFY" in text and ",0," in text or text.strip().endswith(",0")
    row = close_to_row({"hold_sec": 600, "honest_pnl": 8, "risk_rupees": 6,
                        "symbol": "INFY", "confidence": 0.6, "confluence": 73.6,
                        "p_success": 0.67, "atr_pct": 0.02})
    assert row["is_quality_hold"] == 1 and row["is_synthetic"] == 0
    assert row["y_binary"] == 1
