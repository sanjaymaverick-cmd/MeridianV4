"""Portable meta-prob scorer. JSON artefact only — no sklearn at live time."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTEFACT = ROOT / "research" / "artefacts" / "meta_label_v4.json"

FEATURES = [
    "confidence",
    "confluence",
    "p_success",
    "atr_pct",
    "approx_stop_pct",
    "minutes_since_midnight",
    "minutes_to_eod_flatten",
    # belief_posterior omitted: constant in V3-derived set
]


def load_artefact(path: Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_ARTEFACT
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_artefact_safe(path: Path | None = None) -> dict | None:
    """None if missing or unreadable. Live path must never crash the host."""
    p = Path(path) if path else DEFAULT_ARTEFACT
    if not p.exists():
        return None
    try:
        return load_artefact(p)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def predict_meta_prob(features: Mapping[str, float], art: dict | None = None) -> float:
    art = art or load_artefact()
    names = art["features"]
    mean = art["scaler_mean"]
    scale = art["scaler_scale"]
    coef = art["coef"]
    intercept = float(art["intercept"])
    acc = intercept
    n = min(len(names), len(mean), len(scale), len(coef))
    for i in range(n):
        try:
            raw = float(features.get(names[i], 0.0) or 0.0)
        except (TypeError, ValueError):
            raw = 0.0
        if raw != raw or raw in (float("inf"), float("-inf")):
            raw = 0.0
        s = float(scale[i])
        z = 0.0 if abs(s) < 1e-6 else (raw - float(mean[i])) / s
        acc += float(coef[i]) * z
    return _sigmoid(acc)
