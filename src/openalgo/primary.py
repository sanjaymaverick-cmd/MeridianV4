"""Causal primary features from a single quote snapshot. No look-ahead."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from engine import Signal
from quotes import Quote
from session import minutes_since_midnight, minutes_to_eod

PRIOR_P = 0.676
PRIOR_BELIEF = 0.251208


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def signal_from_quote(q: Quote, now: datetime | None = None) -> Signal:
    now = now or datetime.now(timezone.utc)
    px = q.ltp if q.ltp > 0 else q.prev_close
    rng = (q.high - q.low) / px if px > 0 else 0.02
    ret = (q.ltp / q.prev_close - 1.0) if q.prev_close > 0 else 0.0
    span = q.high - q.low
    loc = (q.ltp - q.low) / span if span > 0 else 0.5
    # higher in range + modest positive ret → higher primary confidence
    confidence = _clip(0.52 + 0.25 * loc + 0.15 * math.tanh(ret * 25.0), 0.48, 0.78)
    confluence = 73.6 if loc >= 0.55 else 70.4
    atr_pct = _clip(max(rng, abs(ret) * 1.2), 0.008, 0.06)
    return Signal(
        confidence=confidence,
        confluence=confluence,
        p_success=PRIOR_P,
        atr_pct=atr_pct,
        minutes_to_eod=minutes_to_eod(now, q.exchange),
        belief_posterior=PRIOR_BELIEF,
        minutes_since_midnight=minutes_since_midnight(now, q.exchange),
        approx_stop_pct=1.5 * atr_pct,
        symbol=q.symbol,
    )
