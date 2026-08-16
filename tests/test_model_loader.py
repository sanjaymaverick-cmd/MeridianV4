"""Meta-label load interface. Offline. No training."""
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "meta_label"))

from model import (  # noqa: E402
    JsonLogisticModel,
    LightGBMModel,
    UntrainedModel,
    load_model,
    validate_artefact,
)
from predict import load_artefact, load_artefact_safe, predict_meta_prob  # noqa: E402


def test_live_artefact_loads_and_scores():
    m = load_model()
    assert m.trained and m.kind == "json_logistic"
    assert 0.0 < m.threshold < 1.0
    p = m.predict({
        "confidence": 0.62, "confluence": 73.6, "p_success": 0.676,
        "atr_pct": 0.022, "approx_stop_pct": 0.033,
        "minutes_since_midnight": 500, "minutes_to_eod_flatten": 80,
    })
    assert 0.0 < p < 1.0
    art = load_artefact()
    assert abs(p - predict_meta_prob({
        "confidence": 0.62, "confluence": 73.6, "p_success": 0.676,
        "atr_pct": 0.022, "approx_stop_pct": 0.033,
        "minutes_since_midnight": 500, "minutes_to_eod_flatten": 80,
    }, art)) < 1e-12


def test_missing_artefact_is_untrained(tmp_path):
    m = load_model(tmp_path / "nope.json")
    assert isinstance(m, UntrainedModel) and not m.trained
    assert m.predict({"p_success": 0.67}) == 0.67
    assert load_artefact_safe(tmp_path / "nope.json") is None


def test_corrupt_artefact_is_untrained(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not-json", encoding="utf-8")
    assert isinstance(load_model(p), UntrainedModel)
    p.write_text(json.dumps({"features": []}), encoding="utf-8")
    assert isinstance(load_model(p), UntrainedModel)


def test_validate_rejects_length_mismatch():
    art = load_artefact()
    bad = dict(art)
    bad["coef"] = art["coef"][:-1]
    with pytest.raises(Exception):
        validate_artefact(bad)
    assert isinstance(validate_artefact(art), dict)
    assert isinstance(load_model(), JsonLogisticModel)


def test_lightgbm_without_booster_is_zero():
    m = LightGBMModel(path=Path("unused.txt"), booster=None, trained=False)
    assert m.predict({"p_success": 0.6}) == 0.0
