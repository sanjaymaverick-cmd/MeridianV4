"""Cooldown, daily loss, kill, live cap, state, rollback."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "decision"))
sys.path.insert(0, str(ROOT / "src" / "openalgo"))
sys.path.insert(0, str(ROOT / "src" / "automation"))

from engine import RiskState, Signal, decide  # noqa: E402
from registry import promote, rollback  # noqa: E402
from state import dump, load  # noqa: E402
from engine import Position  # noqa: E402


def _sig(**kw):
    base = dict(confidence=0.62, confluence=73.6, p_success=0.68, atr_pct=0.02,
                minutes_to_eod=90, belief_posterior=0.25, meta_prob=0.80,
                minutes_since_midnight=480, symbol="INFY")
    base.update(kw)
    return Signal(**base)


def test_kill_and_daily_loss():
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    assert decide(_sig(), risk=RiskState(killed=True), now=now).reason == "kill_switch"
    assert decide(_sig(), risk=RiskState(daily_pnl=-6000), now=now).reason == "daily_loss"


def test_cooldown_and_max_pos():
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    r = RiskState()
    r.arm_cooldown("INFY", now)
    assert decide(_sig(), risk=r, now=now).reason == "cooldown"
    r2 = RiskState(n_open=3)
    assert decide(_sig(), risk=r2, now=now).reason == "max_positions"


def test_live_size_cap():
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    i = decide(_sig(meta_prob=0.90), risk=RiskState(live=True), now=now)
    assert i.action == "BUY" and i.size_pct <= 0.10


def test_state_roundtrip(tmp_path):
    now = datetime(2026, 8, 18, 4, 30, tzinfo=timezone.utc)
    pos = {"INFY": Position("INFY", 1500.0, now, 0.02, 0.1, 0.6, 1500.0, 2.0)}
    risk = RiskState(daily_pnl=-10.0)
    p = tmp_path / "state.json"
    dump(pos, risk, p)
    pos2, risk2 = load(p)
    assert "INFY" in pos2 and risk2.daily_pnl == -10.0


def test_rollback(tmp_path, monkeypatch):
    import registry as reg
    monkeypatch.setattr(reg, "INDEX", tmp_path / "index.jsonl")
    monkeypatch.setattr(reg, "REG_DIR", tmp_path)
    live = tmp_path / "meta.json"
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"v":1}', encoding="utf-8")
    b.write_text('{"v":2}', encoding="utf-8")
    promote(a, live)
    promote(b, live)
    assert json.loads(live.read_text())["v"] == 2
    rollback(live)
    assert json.loads(live.read_text())["v"] == 1
