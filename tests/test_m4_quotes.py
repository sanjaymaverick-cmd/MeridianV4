"""M4 quote poll + session + primary. No OpenAlgo."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sys

os.environ["MERIDIAN_MODE"] = "dry"
ROOT = Path(__file__).resolve().parents[1]
os.environ["MERIDIAN_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT / "src" / "openalgo"))
sys.path.insert(0, str(ROOT / "src" / "decision"))

from primary import signal_from_quote  # noqa: E402
from quotes import DryFeed, Quote  # noqa: E402
from session import minutes_to_eod, nse_open  # noqa: E402
from strategy_v4 import Host, poll_once  # noqa: E402


def test_session_ist():
    # 10:00 IST = 04:30 UTC
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)  # Tue
    assert nse_open(now)
    m = minutes_to_eod(now, "NSE")
    assert 300 < m < 320  # flatten 15:15 IST
    assert minutes_to_eod(now, "DELTA") == 999.0
    sat = datetime(2026, 8, 15, 4, 30, tzinfo=timezone.utc)
    assert not nse_open(sat)


def test_primary_causal_bounds():
    q = Quote("INFY", "NSE", ltp=1550, open=1530, high=1560, low=1525, prev_close=1530)
    s = signal_from_quote(q, datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc))
    assert 0.48 <= s.confidence <= 0.78
    assert s.confluence in (70.4, 73.6)
    assert 0.008 <= s.atr_pct <= 0.06
    assert s.symbol == "INFY"


def test_poll_once_dry():
    feed = DryFeed()
    feed.push(Quote("INFY", "NSE", 1500, 1490, 1510, 1485, 1492))
    h = Host(persist=False)
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    intents = poll_once(h, feed, ["INFY"], now)
    assert len(intents) == 1
    assert intents[0].action in ("BUY", "FLAT")
