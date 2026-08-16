"""Meta-label model load interface.

Live path: JSON logistic artefact (no sklearn).
Untrained fallback: p_success passthrough — never promotion-eligible.
LightGBM: stub until training phase.

TODO(training): implement LightGBMModel.load after M5 gates pass on real holds.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Protocol, runtime_checkable

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent
for p in (_HERE, _SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from predict import DEFAULT_ARTEFACT, load_artefact, predict_meta_prob  # noqa: E402

REQUIRED = ("features", "scaler_mean", "scaler_scale", "coef", "intercept")


class ArtefactError(ValueError):
    pass


def validate_artefact(art: dict) -> dict:
    if not isinstance(art, dict):
        raise ArtefactError("artefact is not a dict")
    for k in REQUIRED:
        if k not in art:
            raise ArtefactError(f"missing {k}")
    names = art["features"]
    if not isinstance(names, list) or not names:
        raise ArtefactError("empty features")
    n = len(names)
    for k in ("scaler_mean", "scaler_scale", "coef"):
        if len(art[k]) != n:
            raise ArtefactError(f"{k} length {len(art[k])} != {n}")
    float(art["intercept"])
    float(art.get("threshold", 0.55))
    return art


@runtime_checkable
class MetaLabelModel(Protocol):
    kind: str
    version: str
    trained: bool
    threshold: float
    artefact: Optional[dict]

    def predict(self, features: Mapping[str, float]) -> float: ...


@dataclass
class JsonLogisticModel:
    """Production live scorer. JSON sigmoid only."""
    art: dict
    kind: str = "json_logistic"

    @property
    def version(self) -> str:
        return str(self.art.get("version", "unknown"))

    @property
    def trained(self) -> bool:
        return True

    @property
    def threshold(self) -> float:
        return float(self.art.get("threshold", 0.55))

    @property
    def artefact(self) -> dict:
        return self.art

    def predict(self, features: Mapping[str, float]) -> float:
        p = predict_meta_prob(features, self.art)
        if p != p or p in (float("inf"), float("-inf")):
            return 0.0
        return 0.0 if p < 0.0 else 1.0 if p > 1.0 else p


@dataclass
class UntrainedModel:
    """No artefact. Uses primary p_success. Not promotion-eligible."""
    fallback_key: str = "p_success"
    kind: str = "untrained"
    version: str = "untrained"
    trained: bool = False
    threshold: float = 0.55
    artefact: Optional[dict] = None

    def predict(self, features: Mapping[str, float]) -> float:
        try:
            p = float(features.get(self.fallback_key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if p != p:
            return 0.0
        return 0.0 if p < 0.0 else 1.0 if p > 1.0 else p


@dataclass
class LightGBMModel:
    """Booster file + optional JSON artefact for threshold/features."""
    path: Path
    booster: object = field(default=None, repr=False)
    kind: str = "lightgbm"
    version: str = "lgb"
    trained: bool = True
    threshold: float = 0.55
    artefact: Optional[dict] = field(default=None, repr=False)
    features: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path, art: dict | None = None) -> "LightGBMModel":
        import lightgbm as lgb
        booster = lgb.Booster(model_file=str(path))
        names = list((art or {}).get("features") or [])
        if not names:
            names = list(booster.feature_name() or [])
        return cls(
            path=Path(path), booster=booster, artefact=art,
            version=str((art or {}).get("version", "lgb")),
            threshold=float((art or {}).get("threshold", 0.55)),
            features=names,
        )

    def predict(self, features: Mapping[str, float]) -> float:
        if self.booster is None:
            return 0.0
        names = self.features or list(features.keys())
        row = [float(features.get(n, 0.0) or 0.0) for n in names]
        p = float(self.booster.predict([row])[0])
        if p != p:
            return 0.0
        return 0.0 if p < 0.0 else 1.0 if p > 1.0 else p


def load_model(path: Path | None = None) -> MetaLabelModel:
    """Prefer LightGBM sidecar if present; else JSON logistic. Never raises."""
    p = Path(path) if path else DEFAULT_ARTEFACT
    art = None
    if p.exists():
        try:
            art = validate_artefact(load_artefact(p))
        except (OSError, ValueError, KeyError, TypeError):
            art = None
    lgb_path = p.with_suffix(".txt")
    if lgb_path.exists():
        try:
            return LightGBMModel.load(lgb_path, art)
        except Exception:
            pass
    if art is None:
        return UntrainedModel()
    return JsonLogisticModel(art=art)
