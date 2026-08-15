"""Production guards: NaN ticks, missing artefact, daily roll, Engine wrapper."""
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "decision"))
sys.path.insert(0, str(ROOT / "src" / "meta_label"))

from engine import Engine, Position, RiskState, Signal, decide, manage, score  # noqa: E402
from model import UntrainedModel, load_model  # noqa: E402


def _sig(**kw):
    base = dict(confidence=0.62, confluence=73.6, p_success=0.68, atr_pct=0.02,
                minutes_to_eod=90, belief_posterior=0.25, meta_prob=0.80,
                minutes_since_midnight=480, symbol="INFY")
    base.update(kw)
    return Signal(**base)


def test_nan_meta_falls_through():
    p = score(_sig(meta_prob=float("nan")), art=None)
    assert 0.0 <= p <= 1.0


def test_nan_atr_still_decides():
    i = decide(_sig(atr_pct=float("nan"), meta_prob=0.9))
    assert i.action == "BUY"
    assert 0.008 <= i.stop_pct <= 0.04


def test_untrained_model_via_engine():
    eng = Engine(model=UntrainedModel(), risk=RiskState())
    i = eng.decide(_sig(meta_prob=None, p_success=0.40))
    assert i.action == "FLAT" and i.reason == "low_meta_prob"


def test_engine_uses_json_model():
    eng = Engine(model=load_model())
    i = eng.decide(_sig(meta_prob=0.91))
    assert i.action == "BUY"


def test_manage_bad_price_holds():
    now = datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc)
    pos = Position("INFY", 100.0, now, 0.02, 0.1, 0.6, 100.0)
    i = manage(pos, 0.0, now, 90)
    assert i.action == "HOLD" and i.reason == "bad_price"


def test_daily_roll_resets_pnl():
    r = RiskState(daily_pnl=-400.0, pnl_date="2026-08-17")
    assert r.roll_day("2026-08-18") is True
    assert r.daily_pnl == 0.0 and r.pnl_date == "2026-08-18"
    assert r.roll_day("2026-08-18") is False
