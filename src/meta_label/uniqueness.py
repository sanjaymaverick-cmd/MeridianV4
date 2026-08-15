"""Average uniqueness + sequential bootstrap (AFML ch.4)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def average_uniqueness(t0: pd.Series, t1: pd.Series) -> np.ndarray:
    """u_i = mean_t 1/concurrency_t over the event's life."""
    t0v = pd.to_datetime(t0).to_numpy()
    t1v = pd.to_datetime(t1).to_numpy()
    n = len(t0v)
    if n == 0:
        return np.array([])
    # concurrency at each event start (sufficient for trade-level data)
    conc = np.ones(n, dtype=float)
    for i in range(n):
        conc[i] = max(1.0, float(np.sum((t0v <= t0v[i]) & (t1v > t0v[i]))))
    # refine: mean inverse concurrency over [t0, t1] using other starts as grid
    u = np.empty(n, dtype=float)
    for i in range(n):
        inside = (t0v >= t0v[i]) & (t0v <= t1v[i])
        if not inside.any():
            u[i] = 1.0 / conc[i]
        else:
            u[i] = float(np.mean(1.0 / conc[inside]))
    return u


def sequential_bootstrap(
    uniqueness: np.ndarray,
    n_samples: int | None = None,
    seed: int = 42,
) -> np.ndarray:
    """Draw indices ∝ uniqueness (with replacement)."""
    u = np.asarray(uniqueness, dtype=float)
    u = np.clip(u, 1e-12, None)
    n_samples = n_samples or len(u)
    p = u / u.sum()
    rng = np.random.default_rng(seed)
    return rng.choice(len(u), size=n_samples, replace=True, p=p)
