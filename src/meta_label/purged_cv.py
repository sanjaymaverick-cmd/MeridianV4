"""Purged / combinatorial purged K-fold + embargo (AFML ch.7)."""
from __future__ import annotations

from itertools import combinations
from typing import Iterator

import numpy as np
import pandas as pd


def _overlap_mask(t0: np.ndarray, t1: np.ndarray, te_start, te_end, embargo) -> np.ndarray:
    """True where event [t0, t1] overlaps [te_start, te_end + embargo]."""
    te_end_emb = te_end + embargo
    return (t0 < te_end_emb) & (t1 > te_start)


def purged_kfold(
    t0: pd.Series,
    t1: pd.Series,
    n_splits: int = 4,
    embargo: pd.Timedelta = pd.Timedelta("5min"),
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Contiguous time folds; train purged of test-overlapping events."""
    n = len(t0)
    if n < n_splits + 1:
        raise ValueError(f"need >{n_splits} events, got {n}")
    order = np.argsort(pd.to_datetime(t0).to_numpy())
    folds = np.array_split(order, n_splits)
    t0v = pd.to_datetime(t0).to_numpy()
    t1v = pd.to_datetime(t1).to_numpy()
    embargo = pd.Timedelta(embargo).to_timedelta64()

    for k, te in enumerate(folds):
        te_start = t0v[te].min()
        te_end = t1v[te].max()
        tr_mask = np.ones(n, dtype=bool)
        tr_mask[te] = False
        tr_mask &= ~_overlap_mask(t0v, t1v, te_start, te_end, embargo)
        tr = np.flatnonzero(tr_mask)
        if len(tr) == 0 or len(te) == 0:
            continue
        yield tr, np.sort(te)


def combinatorial_purged_kfold(
    t0: pd.Series,
    t1: pd.Series,
    n_groups: int = 6,
    n_test_groups: int = 2,
    embargo: pd.Timedelta = pd.Timedelta("5min"),
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """All C(n_groups, n_test_groups) purged splits (CPCV)."""
    n = len(t0)
    if n < n_groups:
        raise ValueError(f"need >={n_groups} events, got {n}")
    order = np.argsort(pd.to_datetime(t0).to_numpy())
    groups = np.array_split(order, n_groups)
    t0v = pd.to_datetime(t0).to_numpy()
    t1v = pd.to_datetime(t1).to_numpy()
    embargo = pd.Timedelta(embargo).to_timedelta64()

    for combo in combinations(range(n_groups), n_test_groups):
        te = np.concatenate([groups[i] for i in combo])
        te_start = t0v[te].min()
        te_end = t1v[te].max()
        tr_mask = np.ones(n, dtype=bool)
        tr_mask[te] = False
        tr_mask &= ~_overlap_mask(t0v, t1v, te_start, te_end, embargo)
        tr = np.flatnonzero(tr_mask)
        if len(tr) == 0 or len(te) == 0:
            continue
        yield tr, np.sort(te)
