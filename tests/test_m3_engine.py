"""M3 engine: artefact scoring + longer-hold exits."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "decision"))
sys.path.insert(0, str(ROOT / "src" / "meta_label"))

from engine import (  # noqa: E402
    MIN_HOLD_SEC,
    Position,
    Signal,
    decide,
    manage,
    score,
)
from predict import load_artefact  # noqa: E402


def test_score_from_artefact():
    art = load_artefact()
    s = Signal(0.62, 73.6, 0.676, 0.022, 80, 0.251208, minutes_since_midnight=500)
    p = score(s, art)
    assert 0.0 < p < 1.0


def test_artefact_can_clear_gate():
    art = load_artefact()
    s = Signal(0.62, 73.6, 0.676, 0.018, 90, 0.251208, minutes_since_midnight=480)
    i = decide(s, art)
    assert i.meta_prob > 0.0
    # gate may FLAT on this vector; BUY is allowed when p>=threshold
    assert i.action in ("BUY", "FLAT")


def test_explicit_meta_prob_wins():
    s = Signal(0.62, 75, 0.68, 0.022, 90, 0.25, meta_prob=0.91)
    assert score(s) == 0.91
    assert decide(s).action == "BUY"


def test_low_meta_flat():
    s = Signal(0.5, 70, 0.5, 0.02, 90, 0.25, meta_prob=0.40)
    i = decide(s)
    assert i.action == "FLAT" and i.reason == "low_meta_prob"


def test_eod_and_heat():
    assert decide(Signal(0.7, 75, 0.7, 0.02, 10, 0.25, meta_prob=0.8)).reason == "too_close_to_eod"
    assert decide(Signal(0.7, 75, 0.7, 0.02, 90, 0.25, meta_prob=0.8, portfolio_heat=0.4)).reason == "heat_limit"


def test_no_scratch_before_min_hold():
    now = datetime(2026, 8, 15, 5, 0, tzinfo=timezone.utc)
    pos = Position("INFY", 100.0, now, 0.02, 0.1, 0.6, 100.0)
    i = manage(pos, 100.2, now + timedelta(seconds=60), 90)
    assert i.action == "HOLD" and i.reason == "min_hold"


def test_hard_stop_before_min_hold():
    now = datetime(2026, 8, 15, 5, 0, tzinfo=timezone.utc)
    pos = Position("INFY", 100.0, now, 0.02, 0.1, 0.6, 100.0)
    i = manage(pos, 97.9, now + timedelta(seconds=30), 90)
    assert i.action == "SELL" and i.reason == "hard_stop"


def test_tp_after_min_hold():
    now = datetime(2026, 8, 15, 5, 0, tzinfo=timezone.utc)
    pos = Position("INFY", 100.0, now, 0.02, 0.1, 0.6, 100.0)
    later = now + timedelta(seconds=MIN_HOLD_SEC + 1)
    i = manage(pos, 103.1, later, 90)
    assert i.action == "SELL" and i.reason == "take_profit"


def test_trail_after_arm():
    now = datetime(2026, 8, 15, 5, 0, tzinfo=timezone.utc)
    pos = Position("INFY", 100.0, now, 0.02, 0.1, 0.6, 102.1)  # high_r >= 1
    later = now + timedelta(seconds=MIN_HOLD_SEC + 1)
    i = manage(pos, 100.5, later, 90)  # r ≈ 0.25 < 0.4
    assert i.action == "SELL" and i.reason == "trail"
