"""M5 gates + registry. Retrain uses tmp paths via monkeypatch in one test."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "automation"))

from gates import evaluate  # noqa: E402
from registry import latest, promote, register  # noqa: E402


def test_current_real_fails_gates():
    # today's real set: 157 clean, ~16 quality, ~1 y_meta pos
    r = evaluate({
        "n_real": 157,
        "n_real_quality": 16,
        "n_real_y_meta_pos": 1,
        "purged_auc": None,
        "cpcv_auc": None,
        "in_sample_auc": 0.67,
        "n_synth_in_eval": 0,
    })
    assert not r.passed
    names = {c.name: c.ok for c in r.checks}
    assert names["n_real_clean"] is True
    assert names["n_real_quality"] is False
    assert names["n_real_y_meta_pos"] is False
    assert names["eval_real_only"] is True


def test_synth_in_eval_blocks():
    r = evaluate({
        "n_real": 200, "n_real_quality": 80, "n_real_y_meta_pos": 40,
        "purged_auc": 0.62, "cpcv_auc": 0.60, "in_sample_auc": 0.70,
        "n_synth_in_eval": 400,
    })
    assert not r.passed
    assert any(c.name == "eval_real_only" and not c.ok for c in r.checks)


def test_passing_metrics():
    r = evaluate({
        "n_real": 120, "n_real_quality": 40, "n_real_y_meta_pos": 20,
        "purged_auc": 0.58, "cpcv_auc": 0.57, "in_sample_auc": 0.66,
        "n_synth_in_eval": 0,
    })
    assert r.passed


def test_registry_roundtrip(tmp_path, monkeypatch):
    import registry as reg
    monkeypatch.setattr(reg, "INDEX", tmp_path / "index.jsonl")
    monkeypatch.setattr(reg, "REG_DIR", tmp_path)
    cand = tmp_path / "cand.json"
    live = tmp_path / "live.json"
    cand.write_text(json.dumps({"version": "x"}), encoding="utf-8")
    register(cand, "candidate", {"n_real": 1}, {"passed": False})
    promote(cand, live)
    register(cand, "rejected", {"n_real": 1}, {"passed": False})
    assert live.exists()
    assert latest("candidate")["status"] == "candidate"
    assert latest()["status"] == "rejected"
