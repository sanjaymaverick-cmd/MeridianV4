#!/usr/bin/env python3
"""LightGBM trainer. Live still falls back to JSON logistic if no booster."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = [
    "confidence", "confluence", "p_success", "atr_pct",
    "approx_stop_pct", "minutes_since_midnight", "minutes_to_eod_flatten",
]


def fit_lightgbm(X, y, w, dest: Path, version: str = "lgb",
                 features: list[str] | None = None) -> dict:
    import lightgbm as lgb
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dtrain = lgb.Dataset(np.asarray(X, dtype=float), label=np.asarray(y),
                         weight=np.asarray(w, dtype=float))
    params = {
        "objective": "binary",
        "metric": "auc",
        "verbosity": -1,
        "num_leaves": 15,
        "min_data_in_leaf": 12,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "seed": 42,
    }
    booster = lgb.train(params, dtrain, num_boost_round=80)
    model_path = dest if dest.suffix == ".txt" else dest.with_suffix(".txt")
    booster.save_model(str(model_path))
    p = booster.predict(np.asarray(X, dtype=float))
    from sklearn.metrics import roc_auc_score
    auc = None
    if len(np.unique(y)) >= 2:
        auc = float(roc_auc_score(y, p))
    meta = {
        "model": "lightgbm",
        "version": version,
        "ts": datetime.now(timezone.utc).isoformat(),
        "features": list(features or FEATURES),
        "threshold": 0.55,
        "booster": str(model_path).replace("\\", "/"),
        "in_sample": {"n": int(len(y)), "pos": int(np.asarray(y).sum()), "auc": auc},
    }
    model_path.with_suffix(".lgb.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def train_lightgbm(labeled_csv: Path, dest: Path) -> dict:
    df = pd.read_csv(labeled_csv)
    if "y_meta" not in df.columns:
        raise ValueError("labeled csv needs y_meta")
    X = df[FEATURES].fillna(0).to_numpy(dtype=float)
    y = df["y_meta"].to_numpy()
    if "avg_uniqueness" in df.columns:
        w = np.clip(df["avg_uniqueness"].to_numpy(), 1e-6, None)
    else:
        w = np.ones(len(df))
    return fit_lightgbm(X, y, w, dest)


if __name__ == "__main__":
    raise SystemExit("use: from train import train_lightgbm / automation.retrain")
