#!/usr/bin/env python3
"""M3 – Meridian Decision Engine.

Pure Python. OpenAlgo-ready. Scores meta_prob from the M2 JSON artefact.
Longer-hold: no scratch exits; hard stop always; TP / trail after MIN_HOLD.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ML = Path(__file__).resolve().parents[1] / "meta_label"
if str(_ML) not in sys.path:
    sys.path.insert(0, str(_ML))

from predict import DEFAULT_ARTEFACT, load_artefact, predict_meta_prob  # noqa: E402

# --- Gates (aggressive once cleared) ---
MIN_META_PROB = 0.55
MAX_HEAT = 0.35
MAX_MINUTES_TO_EOD = 30
MIN_HOLD_SEC = 300
MAX_SIZE = 0.25
TP_R = 1.5
TRAIL_ARM_R = 1.0
TRAIL_GIVEBACK_R = 0.4
EOD_FLATTEN_MIN = 15
STOP_ATR_MULT = 1.5
STOP_PCT_MIN, STOP_PCT_MAX = 0.008, 0.04


@dataclass
class Signal:
    confidence: float
    confluence: float
    p_success: float
    atr_pct: float
    minutes_to_eod: float
    belief_posterior: float
    meta_prob: Optional[float] = None
    portfolio_heat: float = 0.0
    minutes_since_midnight: float = 540.0
    approx_stop_pct: Optional[float] = None
    symbol: str = ""


@dataclass
class Intent:
    action: str          # BUY | SELL | HOLD | FLAT
    size_pct: float
    stop_pct: float
    reason: str
    meta_prob: float = 0.0


@dataclass
class Position:
    symbol: str
    entry_price: float
    entry_ts: datetime
    stop_pct: float
    size_pct: float
    meta_prob: float
    high_since_entry: float
    qty: float = 0.0


def _artefact_or_none(path: Optional[Path] = None) -> Optional[dict]:
    p = Path(path) if path else DEFAULT_ARTEFACT
    if not p.exists():
        return None
    return load_artefact(p)


def score(sig: Signal, art: Optional[dict] = None) -> float:
    """meta_prob: explicit > artefact > primary p_success."""
    if sig.meta_prob is not None:
        return float(sig.meta_prob)
    art = art if art is not None else _artefact_or_none()
    if art is None:
        return float(sig.p_success)
    stop = sig.approx_stop_pct if sig.approx_stop_pct is not None else STOP_ATR_MULT * sig.atr_pct
    return predict_meta_prob(
        {
            "confidence": sig.confidence,
            "confluence": sig.confluence,
            "p_success": sig.p_success,
            "atr_pct": sig.atr_pct,
            "approx_stop_pct": stop,
            "minutes_since_midnight": sig.minutes_since_midnight,
            "minutes_to_eod_flatten": sig.minutes_to_eod,
            "belief_posterior": sig.belief_posterior,
        },
        art,
    )


def decide(sig: Signal, art: Optional[dict] = None) -> Intent:
    if sig.minutes_to_eod < MAX_MINUTES_TO_EOD:
        return Intent("FLAT", 0.0, 0.0, "too_close_to_eod")
    if sig.portfolio_heat >= MAX_HEAT:
        return Intent("FLAT", 0.0, 0.0, "heat_limit")

    p = score(sig, art)
    thr = float((art or _artefact_or_none() or {}).get("threshold", MIN_META_PROB))
    if p < thr:
        return Intent("FLAT", 0.0, 0.0, "low_meta_prob", meta_prob=p)

    edge = p - 0.5
    size = max(0.0, min(MAX_SIZE, edge * 1.5 * (1.0 - sig.portfolio_heat)))
    if size <= 0.0:
        return Intent("FLAT", 0.0, 0.0, "zero_size", meta_prob=p)
    stop = max(STOP_PCT_MIN, min(STOP_PCT_MAX, STOP_ATR_MULT * sig.atr_pct))
    return Intent("BUY", size, stop, "passed_gates", meta_prob=p)


def _r_multiple(pos: Position, px: float) -> float:
    if pos.entry_price <= 0 or pos.stop_pct <= 0:
        return 0.0
    return (px / pos.entry_price - 1.0) / pos.stop_pct


def manage(pos: Position, last_price: float, now: datetime, minutes_to_eod: float) -> Intent:
    """Longer-hold exit. Hard stop always. No scratch before MIN_HOLD_SEC."""
    pos.high_since_entry = max(pos.high_since_entry, last_price)
    r = _r_multiple(pos, last_price)
    high_r = _r_multiple(pos, pos.high_since_entry)
    held = (now - pos.entry_ts).total_seconds()

    if r <= -1.0:
        return Intent("SELL", 0.0, pos.stop_pct, "hard_stop", meta_prob=pos.meta_prob)
    if minutes_to_eod < EOD_FLATTEN_MIN:
        return Intent("SELL", 0.0, pos.stop_pct, "eod_flatten", meta_prob=pos.meta_prob)
    if held < MIN_HOLD_SEC:
        return Intent("HOLD", pos.size_pct, pos.stop_pct, "min_hold", meta_prob=pos.meta_prob)
    if r >= TP_R:
        return Intent("SELL", 0.0, pos.stop_pct, "take_profit", meta_prob=pos.meta_prob)
    if high_r >= TRAIL_ARM_R and r <= TRAIL_GIVEBACK_R:
        return Intent("SELL", 0.0, pos.stop_pct, "trail", meta_prob=pos.meta_prob)
    return Intent("HOLD", pos.size_pct, pos.stop_pct, "hold_quality", meta_prob=pos.meta_prob)


if __name__ == "__main__":
    art = _artefact_or_none()
    # early-session / higher-conf vector tends to clear 0.55 on current artefact
    s = Signal(0.62, 73.6, 0.676, 0.022, 80, 0.251208,
               minutes_since_midnight=500, portfolio_heat=0.1)
    print("decide", decide(s, art))
    s2 = Signal(0.55, 70, 0.55, 0.03, 10, 0.25)
    print("eod   ", decide(s2, art))
    now = datetime.now(timezone.utc)
    pos = Position("INFY", 1500.0, now, 0.02, 0.1, 0.61, 1500.0)
    print("hold  ", manage(pos, 1505.0, now, 90))
    print("stop  ", manage(pos, 1465.0, now, 90))
