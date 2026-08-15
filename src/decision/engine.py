#!/usr/bin/env python3
"""M3 – Meridian Decision Engine.

Pure Python. OpenAlgo-ready. Scores meta_prob from the M2 JSON artefact.
Longer-hold: no scratch exits; hard stop always; TP / trail after MIN_HOLD.

Never raises into the host: bad ticks / missing artefact → FLAT or HOLD.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

KILL_NAME = "KILL"

_SRC = Path(__file__).resolve().parents[1]
_ML = _SRC / "meta_label"
for p in (_ML, _SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from predict import DEFAULT_ARTEFACT, load_artefact_safe, predict_meta_prob  # noqa: E402

try:
    from settings import (
        COOLDOWN_SEC,
        DAILY_LOSS_LIMIT,
        EOD_FLATTEN_MIN,
        LIVE_BUDGET,
        MAX_HEAT,
        MAX_MINUTES_TO_EOD,
        MAX_POS_LIVE,
        MAX_POS_PAPER,
        MAX_SIZE,
        MAX_SIZE_LIVE,
        MIN_HOLD_SEC,
        MIN_META_PROB,
        PAPER_BUDGET,
        STOP_ATR_MULT,
        STOP_PCT_MAX,
        STOP_PCT_MIN,
        TP_R,
        TRAIL_ARM_R,
        TRAIL_GIVEBACK_R,
    )
except ImportError:  # pragma: no cover
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
    COOLDOWN_SEC = 600
    DAILY_LOSS_LIMIT = -5000.0
    MAX_SIZE_LIVE = 0.10
    MAX_POS_PAPER = 3
    MAX_POS_LIVE = 2
    LIVE_BUDGET = 25_000.0
    PAPER_BUDGET = 100_000.0


def _finite(x, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if math.isnan(v) or math.isinf(v):
        return default
    return v


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _utc(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


@dataclass
class RiskState:
    daily_pnl: float = 0.0
    daily_loss_limit: float = DAILY_LOSS_LIMIT
    killed: bool = False
    cooldown_until: dict = field(default_factory=dict)
    cooldown_sec: float = COOLDOWN_SEC
    live: bool = False
    n_open: int = 0
    pnl_date: str = ""  # IST calendar day YYYY-MM-DD

    def in_cooldown(self, symbol: str, now: datetime) -> bool:
        until = self.cooldown_until.get(symbol)
        return until is not None and now < until

    def arm_cooldown(self, symbol: str, now: datetime) -> None:
        self.cooldown_until[symbol] = now + timedelta(seconds=self.cooldown_sec)

    def roll_day(self, ist_date: str) -> bool:
        """Reset daily_pnl on IST date change. Returns True if rolled."""
        if not ist_date:
            return False
        if self.pnl_date and self.pnl_date != ist_date:
            self.daily_pnl = 0.0
            self.pnl_date = ist_date
            return True
        if not self.pnl_date:
            self.pnl_date = ist_date
        return False


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
    return load_artefact_safe(p)


def _flat(reason: str, p: float = 0.0) -> Intent:
    return Intent("FLAT", 0.0, 0.0, reason, meta_prob=p)


def score(sig: Signal, art: Optional[dict] = None) -> float:
    """meta_prob: explicit > artefact > primary p_success. Always in [0, 1]."""
    if sig.meta_prob is not None:
        p = _finite(sig.meta_prob, float("nan"))
        if p == p:
            return _clip(p, 0.0, 1.0)
    art = art if art is not None else _artefact_or_none()
    if art is None:
        return _clip(_finite(sig.p_success, 0.5), 0.0, 1.0)
    stop = sig.approx_stop_pct if sig.approx_stop_pct is not None else STOP_ATR_MULT * _finite(sig.atr_pct)
    try:
        p = predict_meta_prob(
            {
                "confidence": _finite(sig.confidence),
                "confluence": _finite(sig.confluence),
                "p_success": _finite(sig.p_success),
                "atr_pct": _finite(sig.atr_pct),
                "approx_stop_pct": _finite(stop),
                "minutes_since_midnight": _finite(sig.minutes_since_midnight, 540.0),
                "minutes_to_eod_flatten": _finite(sig.minutes_to_eod),
                "belief_posterior": _finite(sig.belief_posterior),
            },
            art,
        )
        return _clip(_finite(p, _finite(sig.p_success, 0.5)), 0.0, 1.0)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return _clip(_finite(sig.p_success, 0.5), 0.0, 1.0)


def decide(sig: Signal, art: Optional[dict] = None,
           risk: Optional[RiskState] = None,
           now: Optional[datetime] = None) -> Intent:
    now = _utc(now)
    risk = risk or RiskState()
    if risk.killed:
        return _flat("kill_switch")
    if _finite(risk.daily_pnl) <= _finite(risk.daily_loss_limit, DAILY_LOSS_LIMIT):
        return _flat("daily_loss")
    if risk.in_cooldown(sig.symbol, now):
        return _flat("cooldown")
    cap = MAX_POS_LIVE if risk.live else MAX_POS_PAPER
    if risk.n_open >= cap:
        return _flat("max_positions")
    if _finite(sig.minutes_to_eod, 999.0) < MAX_MINUTES_TO_EOD:
        return _flat("too_close_to_eod")
    if _finite(sig.portfolio_heat) >= MAX_HEAT:
        return _flat("heat_limit")

    p = score(sig, art)
    thr = _finite((art or _artefact_or_none() or {}).get("threshold", MIN_META_PROB), MIN_META_PROB)
    if p < thr:
        return _flat("low_meta_prob", p)

    edge = p - 0.5
    size_cap = MAX_SIZE_LIVE if risk.live else MAX_SIZE
    heat = _clip(_finite(sig.portfolio_heat), 0.0, 1.0)
    size = _clip(edge * 1.5 * (1.0 - heat), 0.0, size_cap)
    if size <= 0.0:
        return _flat("zero_size", p)
    atr = _finite(sig.atr_pct, 0.0)
    if atr <= 0.0:
        atr = STOP_PCT_MIN / STOP_ATR_MULT
    stop = _clip(STOP_ATR_MULT * atr, STOP_PCT_MIN, STOP_PCT_MAX)
    return Intent("BUY", size, stop, "passed_gates", meta_prob=p)


def _r_multiple(pos: Position, px: float) -> float:
    if pos.entry_price <= 0 or pos.stop_pct <= 0:
        return 0.0
    return (px / pos.entry_price - 1.0) / pos.stop_pct


def manage(pos: Position, last_price: float, now: datetime, minutes_to_eod: float) -> Intent:
    """Longer-hold exit. Hard stop always. No scratch before MIN_HOLD_SEC."""
    px = _finite(last_price, 0.0)
    if px <= 0.0:
        return Intent("HOLD", pos.size_pct, pos.stop_pct, "bad_price", meta_prob=pos.meta_prob)
    now = _utc(now)
    entry = pos.entry_ts
    if entry.tzinfo is None:
        entry = entry.replace(tzinfo=timezone.utc)
    pos.high_since_entry = max(_finite(pos.high_since_entry, px), px)
    r = _r_multiple(pos, px)
    high_r = _r_multiple(pos, pos.high_since_entry)
    held = max(0.0, (now - entry).total_seconds())

    if r <= -1.0:
        return Intent("SELL", 0.0, pos.stop_pct, "hard_stop", meta_prob=pos.meta_prob)
    if _finite(minutes_to_eod, 999.0) < EOD_FLATTEN_MIN:
        return Intent("SELL", 0.0, pos.stop_pct, "eod_flatten", meta_prob=pos.meta_prob)
    if held < MIN_HOLD_SEC:
        return Intent("HOLD", pos.size_pct, pos.stop_pct, "min_hold", meta_prob=pos.meta_prob)
    if r >= TP_R:
        return Intent("SELL", 0.0, pos.stop_pct, "take_profit", meta_prob=pos.meta_prob)
    if high_r >= TRAIL_ARM_R and r <= TRAIL_GIVEBACK_R:
        return Intent("SELL", 0.0, pos.stop_pct, "trail", meta_prob=pos.meta_prob)
    return Intent("HOLD", pos.size_pct, pos.stop_pct, "hold_quality", meta_prob=pos.meta_prob)


class Engine:
    """Stateful wrapper. Same gates as decide/manage. Safe if artefact missing."""

    def __init__(self, art: Optional[dict] = None, risk: Optional[RiskState] = None,
                 model=None):
        if model is not None:
            self.art = model.artefact
            self.model = model
        else:
            self.art = art if art is not None else _artefact_or_none()
            self.model = None
        self.risk = risk or RiskState()

    def score(self, sig: Signal) -> float:
        if self.model is not None and sig.meta_prob is None:
            return self.model.predict({
                "confidence": _finite(sig.confidence),
                "confluence": _finite(sig.confluence),
                "p_success": _finite(sig.p_success),
                "atr_pct": _finite(sig.atr_pct),
                "approx_stop_pct": _finite(
                    sig.approx_stop_pct if sig.approx_stop_pct is not None
                    else STOP_ATR_MULT * _finite(sig.atr_pct)
                ),
                "minutes_since_midnight": _finite(sig.minutes_since_midnight, 540.0),
                "minutes_to_eod_flatten": _finite(sig.minutes_to_eod),
                "belief_posterior": _finite(sig.belief_posterior),
            })
        return score(sig, self.art)

    def decide(self, sig: Signal, now: Optional[datetime] = None) -> Intent:
        if self.model is not None and sig.meta_prob is None:
            old = sig.meta_prob
            sig.meta_prob = self.score(sig)
            try:
                return decide(sig, self.art, self.risk, now)
            finally:
                sig.meta_prob = old
        return decide(sig, self.art, self.risk, now)

    def manage(self, pos: Position, last_price: float, now: datetime,
               minutes_to_eod: float) -> Intent:
        return manage(pos, last_price, now, minutes_to_eod)


if __name__ == "__main__":
    art = _artefact_or_none()
    s = Signal(0.62, 73.6, 0.676, 0.022, 80, 0.251208,
               minutes_since_midnight=500, portfolio_heat=0.1)
    print("decide", decide(s, art))
    s2 = Signal(0.55, 70, 0.55, 0.03, 10, 0.25)
    print("eod   ", decide(s2, art))
    now = datetime.now(timezone.utc)
    pos = Position("INFY", 1500.0, now, 0.02, 0.1, 0.61, 1500.0)
    print("hold  ", manage(pos, 1505.0, now, 90))
    print("stop  ", manage(pos, 1465.0, now, 90))
