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
    "belief_posterior",
]


def load_artefact(path: Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_ARTEFACT
    with open(p, encoding="utf-8") as f:
        return json.load(f)


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
    for i, name in enumerate(names):
        raw = float(features.get(name, 0.0) or 0.0)
        z = (raw - mean[i]) / (scale[i] if scale[i] else 1.0)
        acc += coef[i] * z
    return _sigmoid(acc)
