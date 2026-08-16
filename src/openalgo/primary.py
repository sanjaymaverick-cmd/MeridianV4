"""Causal primary features from a single quote snapshot. No look-ahead."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from engine import Signal
from quotes import Quote
from session import minutes_since_midnight, minutes_to_eod

def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _regime(loc: float, atr_pct: float) -> int:
    """0=calm-low, 1=stress, 2=calm-high. Causal on this bar only."""
    if atr_pct >= 0.03:
        return 1
    return 2 if loc >= 0.55 else 0


def signal_from_quote(q: Quote, now: datetime | None = None) -> Signal:
    now = now or datetime.now(timezone.utc)
    px = q.ltp if q.ltp > 0 else q.prev_close
    rng = (q.high - q.low) / px if px > 0 else 0.02
    ret = (q.ltp / q.prev_close - 1.0) if q.prev_close > 0 else 0.0
    span = q.high - q.low
    loc = (q.ltp - q.low) / span if span > 0 else 0.5
    confidence = _clip(0.52 + 0.25 * loc + 0.15 * math.tanh(ret * 25.0), 0.48, 0.78)
    confluence = 73.6 if loc >= 0.55 else 70.4
    atr_pct = _clip(max(rng, abs(ret) * 1.2), 0.008, 0.06)
    belief = _clip(0.18 + 0.28 * loc - 0.12 * (atr_pct / 0.04), 0.08, 0.55)
    p_success = _clip(0.52 + 0.18 * loc + 0.10 * math.tanh(ret * 25.0) - 0.08 * (atr_pct / 0.04),
                      0.45, 0.72)
    return Signal(
        confidence=confidence,
        confluence=confluence,
        p_success=p_success,
        atr_pct=atr_pct,
        minutes_to_eod=minutes_to_eod(now, q.exchange),
        belief_posterior=belief,
        minutes_since_midnight=minutes_since_midnight(now, q.exchange),
        approx_stop_pct=1.5 * atr_pct,
        symbol=q.symbol,
    )
