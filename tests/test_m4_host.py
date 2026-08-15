"""M4 host + failed-order bookkeeping. No OpenAlgo."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sys

os.environ["MERIDIAN_MODE"] = "dry"
ROOT = Path(__file__).resolve().parents[1]
os.environ["MERIDIAN_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT / "src" / "openalgo"))
sys.path.insert(0, str(ROOT / "src" / "decision"))
sys.path.insert(0, str(ROOT / "src" / "meta_label"))

from engine import Signal  # noqa: E402
from quotes import DryFeed, Quote  # noqa: E402
from strategy_v4 import Host, poll_once  # noqa: E402


def test_host_survives_missing_artefact(monkeypatch, tmp_path):
    import predict as pred
    monkeypatch.setattr(pred, "DEFAULT_ARTEFACT", tmp_path / "gone.json")
    import model as mdl
    monkeypatch.setattr(mdl, "DEFAULT_ARTEFACT", tmp_path / "gone.json")
    h = Host(persist=False)
    assert h.art is None
    assert h.model is None or not h.model.trained
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    i = h.on_signal(Signal(0.62, 73.6, 0.68, 0.02, 90, 0.25, meta_prob=0.9,
                           minutes_since_midnight=480, symbol="INFY"), 1500.0, now)
    assert i.action in ("BUY", "FLAT")


def test_failed_buy_does_not_book():
    h = Host(persist=False)
    h._send = lambda *a, **k: False  # type: ignore
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    i = h.on_signal(Signal(0.62, 73.6, 0.68, 0.02, 90, 0.25, meta_prob=0.9,
                           minutes_since_midnight=480, symbol="INFY"), 1500.0, now)
    assert "INFY" not in h.pos
    assert i.reason in ("order_fail", "low_meta_prob", "passed_gates") or i.action == "FLAT"


def test_poll_quote_exception_empty():
    class Boom:
        def fetch(self, pairs):
            raise RuntimeError("down")

    h = Host(persist=False)
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    assert poll_once(h, Boom(), ["INFY"], now) == []


def test_poll_dry_still_works():
    feed = DryFeed()
    feed.push(Quote("INFY", "NSE", 1500, 1490, 1510, 1485, 1492))
    h = Host(persist=False)
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    out = poll_once(h, feed, ["INFY"], now)
    assert len(out) == 1
    assert out[0].action in ("BUY", "FLAT")
