"""mlfinlab-style triple-barrier (AFML ch.3).

Trade-level data has no bar path. We reconstruct a Brownian bridge from
buy→sell, vol-scaled to ATR, then apply first-touch PT / SL / vertical.
When a close series is supplied, use that path instead.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

PT_MULT = 1.0          # +1R take-profit (quality hold)
SL_MULT = 1.0          # −1R stop
VERTICAL_SEC = 1800    # 30m — longer-hold regime
MIN_STEPS = 16
MAX_STEPS = 400
RNG_SEED = 42


def brownian_bridge(p0: float, p1: float, n: int, step_std: float, rng: np.random.Generator) -> np.ndarray:
    """Price path pinned at p0 and p1."""
    if n < 2:
        return np.array([p0, p1], dtype=float)
    z = rng.normal(0.0, step_std, n)
    w = np.cumsum(z)
    t = np.linspace(0.0, 1.0, n)
    w = w - t * w[-1]
    path = (1.0 - t) * p0 + t * p1 + w
    path[0], path[-1] = p0, p1
    return path


def first_touch_r(r_path: np.ndarray, dt_sec: float, pt: float, sl: float, vertical_sec: float) -> tuple[int, float, float]:
    """R-space first touch. label: +1 PT, -1 SL, 0 vertical. r_path starts at 0."""
    max_i = min(len(r_path), max(2, int(np.ceil(vertical_sec / max(dt_sec, 1e-9))) + 1))
    for i in range(1, max_i):
        r = float(r_path[i])
        if r >= pt:
            return 1, i * dt_sec, r
        if r <= -sl:
            return -1, i * dt_sec, r
    last = float(r_path[min(max_i, len(r_path)) - 1])
    return 0, min(vertical_sec, (len(r_path) - 1) * dt_sec), last


def label_trades(
    df: pd.DataFrame,
    pt_mult: float = PT_MULT,
    sl_mult: float = SL_MULT,
    vertical_sec: float = VERTICAL_SEC,
    seed: int = RNG_SEED,
) -> pd.DataFrame:
    """Add tbm_label / tbm_touch_sec / tbm_ret / y_meta.

    Barriers live in R-space (pnl / risk_rupees). Path is a Brownian bridge
    from 0 → realized y_R so the endpoint is honest; first-touch can still
    assign SL if the bridge tags −sl before +pt.
    """
    rng = np.random.default_rng(seed)
    out = df.copy()
    labels, touches, rets = [], [], []

    for r in out.itertuples(index=False):
        hold = max(float(r.hold_sec), 1.0)
        y_r = float(r.y_R) if pd.notna(r.y_R) else 0.0
        n = int(np.clip(hold / 5.0, MIN_STEPS, MAX_STEPS))
        dt = hold / (n - 1)
        # 1σ over vertical window ≈ 1R of residual excursion
        step_std = 1.0 * np.sqrt(dt / vertical_sec)
        r_path = brownian_bridge(0.0, y_r, n, step_std, rng)
        lab, ts, ret = first_touch_r(r_path, dt, pt_mult, sl_mult, vertical_sec)
        labels.append(lab)
        touches.append(ts)
        rets.append(ret)

    out["tbm_label"] = np.asarray(labels, dtype=int)
    out["tbm_touch_sec"] = np.asarray(touches, dtype=float)
    out["tbm_ret"] = np.asarray(rets, dtype=float)
    out["y_meta"] = (out["tbm_label"] == 1).astype(int)
    return out


def apply_on_bars(
    close: pd.Series,
    t0: pd.Timestamp,
    side: int,
    pt: float,
    sl: float,
    vertical: pd.Timedelta,
) -> tuple[int, pd.Timestamp, float]:
    """Path-based TBM when a close series exists. side: +1 long / -1 short."""
    window = close.loc[t0 : t0 + vertical]
    if window.empty:
        return 0, t0, 0.0
    p0 = float(window.iloc[0])
    up, dn = p0 * (1.0 + pt), p0 * (1.0 - sl)
    for ts, px in window.iloc[1:].items():
        px = float(px)
        if side > 0:
            if px >= up:
                return 1, ts, px / p0 - 1.0
            if px <= dn:
                return -1, ts, px / p0 - 1.0
        else:
            if px <= p0 * (1.0 - pt):
                return 1, ts, 1.0 - px / p0
            if px >= p0 * (1.0 + sl):
                return -1, ts, 1.0 - px / p0
    last = float(window.iloc[-1])
    return 0, window.index[-1], side * (last / p0 - 1.0)
