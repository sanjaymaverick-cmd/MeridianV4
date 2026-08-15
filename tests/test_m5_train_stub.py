"""M5 gates stay real-only; training stub is not live."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "automation"))
sys.path.insert(0, str(ROOT / "src" / "meta_label"))

from gates import evaluate  # noqa: E402
from train import train_lightgbm  # noqa: E402


def test_empty_metrics_fail_closed():
    r = evaluate({})
    assert not r.passed
    assert "n_real_clean" in r.reason


def test_lightgbm_trainer_is_todo():
    with pytest.raises(NotImplementedError):
        train_lightgbm(Path("x.csv"), Path("y.json"))
